# auth.py - Version moderne avec Google Identity Services
import os
import jwt
import json
import logging
from datetime import datetime, timedelta
from flask import request, jsonify

from werkzeug.security import generate_password_hash, check_password_hash
from google.oauth2 import id_token
from google.auth.transport.requests import Request
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency
    psycopg = None
from services.aws_persistence import aws_persistence_service

logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', '')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '1536'))

_firebase_initialized = False

def _get_pg_connection():
    database_url = os.getenv('DATABASE_URL', DATABASE_URL)
    if psycopg is None:
        raise RuntimeError("psycopg is required for PostgreSQL persistence")
    if not database_url:
        raise ValueError("DATABASE_URL is required for PostgreSQL persistence")
    return psycopg.connect(database_url)

def _ensure_user_context(conn, user_id, email, name):
    """Ensure the user has an organization membership and an active plan."""
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT o.id::text
        FROM organizations o
        JOIN user_organizations uo ON uo.organization_id = o.id
        WHERE uo.user_id = %s
        ORDER BY uo.joined_at ASC
        LIMIT 1
        ''',
        (user_id,)
    )
    row = cursor.fetchone()

    if row:
        organization_id = row[0]
    else:
        org_name = f"{(name or email.split('@')[0])}'s Organization"
        cursor.execute(
            '''
            INSERT INTO organizations (name, owner_user_id)
            VALUES (%s, %s)
            RETURNING id::text
            ''',
            (org_name, user_id)
        )
        organization_id = cursor.fetchone()[0]

        cursor.execute(
            '''
            INSERT INTO user_organizations (user_id, organization_id, role)
            VALUES (%s, %s, 'owner')
            ON CONFLICT (user_id, organization_id) DO NOTHING
            ''',
            (user_id, organization_id)
        )

    cursor.execute(
        '''
        SELECT plan_code
        FROM plans
        WHERE organization_id = %s
          AND status IN ('active', 'trialing')
        ORDER BY started_at DESC
        LIMIT 1
        ''',
        (organization_id,)
    )
    plan_row = cursor.fetchone()
    if plan_row:
        plan_code = plan_row[0]
    else:
        cursor.execute(
            '''
            INSERT INTO plans (organization_id, plan_code, status)
            VALUES (%s, 'free', 'active')
            RETURNING plan_code
            ''',
            (organization_id,)
        )
        plan_code = cursor.fetchone()[0]

    cursor.execute(
        '''
        INSERT INTO licenses (organization_id, license_key, seats_total, seats_used, status)
        VALUES (%s, %s, 1, 1, 'active')
        ON CONFLICT (organization_id, license_key) DO NOTHING
        ''',
        (organization_id, f"LIC-{organization_id[:8]}-FREE")
    )

    return organization_id, plan_code

def init_firebase_admin():
    """Initialise Firebase Admin SDK si la configuration est disponible."""
    global _firebase_initialized

    if _firebase_initialized:
        return True

    if firebase_admin._apps:
        _firebase_initialized = True
        return True

    service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
    service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')

    try:
        cred = None
        if service_account_json:
            try:
                cred = credentials.Certificate(json.loads(service_account_json))
            except Exception as json_exc:
                logger.warning(f"FIREBASE_SERVICE_ACCOUNT_JSON invalide, tentative de fallback vers le fichier: {str(json_exc)}")

        if cred is None and service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)

        if cred is None:
            logger.warning("Firebase Admin non configuré: FIREBASE_SERVICE_ACCOUNT_PATH ou FIREBASE_SERVICE_ACCOUNT_JSON manquant")
            return False

        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin initialisé avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur initialisation Firebase Admin: {str(e)}")
        return False

def init_database():
    """Initialise la base PostgreSQL (Phase 2)."""
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
                cursor.execute('CREATE EXTENSION IF NOT EXISTS vector')

                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        firebase_uid TEXT UNIQUE,
                        email TEXT UNIQUE NOT NULL,
                        name TEXT,
                        provider TEXT DEFAULT 'email',
                        phone TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now(),
                        last_login_at TIMESTAMPTZ
                    )
                    '''
                )

                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS organizations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name TEXT NOT NULL,
                        owner_user_id UUID REFERENCES users(id),
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now()
                    )
                    '''
                )

                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS user_organizations (
                        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                        organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                        role TEXT NOT NULL DEFAULT 'member',
                        joined_at TIMESTAMPTZ DEFAULT now(),
                        PRIMARY KEY (user_id, organization_id)
                    )
                    '''
                )

                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS plans (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                        plan_code TEXT NOT NULL DEFAULT 'free',
                        status TEXT NOT NULL DEFAULT 'active',
                        started_at TIMESTAMPTZ DEFAULT now(),
                        ends_at TIMESTAMPTZ,
                        limits_json JSONB DEFAULT '{}'::jsonb
                    )
                    '''
                )

                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS licenses (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                        license_key TEXT NOT NULL,
                        seats_total INT NOT NULL DEFAULT 1,
                        seats_used INT NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'active',
                        expires_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT now(),
                        UNIQUE (organization_id, license_key)
                    )
                    '''
                )

                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS documents (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
                        uploaded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                        file_name TEXT NOT NULL,
                        mime_type TEXT,
                        size_bytes BIGINT,
                        s3_bucket TEXT,
                        s3_key TEXT,
                        etag TEXT,
                        status TEXT DEFAULT 'uploaded',
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ DEFAULT now(),
                        processed_at TIMESTAMPTZ
                    )
                    '''
                )

                cursor.execute(
                    f'''
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                        organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                        chunk_index INT NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector({EMBEDDING_DIMENSION}) NOT NULL,
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        created_at TIMESTAMPTZ DEFAULT now()
                    )
                    '''
                )

                cursor.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS marketing_emails (
                        email TEXT PRIMARY KEY,
                        name TEXT,
                        provider TEXT DEFAULT 'email',
                        source TEXT DEFAULT 'flexianalyse_signup',
                        created_at TIMESTAMPTZ DEFAULT now(),
                        is_subscribed BOOLEAN DEFAULT true
                    )
                    '''
                )

            conn.commit()

        logger.info("PostgreSQL schema initialized successfully")
    except Exception as e:
        logger.error(f"Erreur initialisation base PostgreSQL: {str(e)}")
        raise

def create_jwt_token(user_data):
    """Crée un token JWT pour l'utilisateur"""
    payload = {
        'user_id': user_data['id'],
        'email': user_data['email'],
        'name': user_data['name'],
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """Vérifie un token JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_firebase_token(token):
    """Vérifie un Firebase ID token."""
    if not init_firebase_admin():
        return None

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.warning(f"Token Firebase invalide: {str(e)}")
        return None

def get_or_create_firebase_user(firebase_payload):
    """Récupère ou crée un utilisateur PostgreSQL à partir d'un token Firebase."""

    email = firebase_payload.get('email')
    firebase_uid = firebase_payload.get('uid')
    name = firebase_payload.get('name') or (email.split('@')[0] if email else 'User')
    provider = 'google' if any(identity.endswith('google.com') for identity in firebase_payload.get('firebase', {}).get('sign_in_provider', '').split(',')) else 'email'

    if not email:
        return None

    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    SELECT id::text, email, name, provider, phone
                    FROM users
                    WHERE firebase_uid = %s OR email = %s
                    LIMIT 1
                    ''',
                    (firebase_uid, email)
                )
                user = cursor.fetchone()

                if user:
                    user_id = user[0]
                    cursor.execute(
                        '''
                        UPDATE users
                        SET name = COALESCE(NULLIF(%s, ''), name),
                            provider = COALESCE(NULLIF(%s, ''), provider),
                            firebase_uid = COALESCE(NULLIF(%s, ''), firebase_uid),
                            updated_at = now(),
                            last_login_at = now()
                        WHERE id = %s::uuid
                        ''',
                        (name, provider, firebase_uid, user_id)
                    )
                else:
                    cursor.execute(
                        '''
                        INSERT INTO users (email, name, provider, firebase_uid, created_at, updated_at, last_login_at)
                        VALUES (%s, %s, %s, %s, now(), now(), now())
                        RETURNING id::text
                        ''',
                        (email, name, provider, firebase_uid)
                    )
                    user_id = cursor.fetchone()[0]

                cursor.execute(
                    '''
                    SELECT id::text, email, COALESCE(name, email), COALESCE(provider, %s), phone
                    FROM users
                    WHERE id = %s::uuid
                    ''',
                    (provider, user_id)
                )
                saved_user = cursor.fetchone()

                if not saved_user:
                    return None

                organization_id, plan_code = _ensure_user_context(
                    conn,
                    saved_user[0],
                    saved_user[1],
                    saved_user[2],
                )

            conn.commit()

        user_data = {
            'id': saved_user[0],
            'email': saved_user[1],
            'name': saved_user[2] or saved_user[1].split('@')[0],
            'provider': saved_user[3] or provider,
            'plan': plan_code or 'free',
            'phone': saved_user[4],
            'firebase_uid': firebase_uid,
            'organization_id': organization_id,
        }

        aws_persistence_service.persist_user_profile(user_data, firebase_payload)
        return user_data
    except Exception as exc:
        logger.error(f"Erreur lors de la synchronisation utilisateur PostgreSQL: {str(exc)}")
        return None

def verify_auth_token(token):
    """Vérifie un token Firebase puis JWT en fallback."""
    firebase_payload = verify_firebase_token(token)
    if firebase_payload:
        user = get_or_create_firebase_user(firebase_payload)
        if not user:
            return None
        return {
            'auth_type': 'firebase',
            'user': user,
            'payload': firebase_payload,
        }

    jwt_payload = verify_jwt_token(token)
    if jwt_payload:
        return {
            'auth_type': 'jwt',
            'user': {
                'id': jwt_payload['user_id'],
                'email': jwt_payload['email'],
                'name': jwt_payload['name'],
            },
            'payload': jwt_payload,
        }

    return None

def save_marketing_email(email, name, provider):
    """Sauvegarde l'email pour le marketing"""
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO marketing_emails (email, name, provider, created_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (email)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        provider = EXCLUDED.provider,
                        created_at = now(),
                        is_subscribed = true
                    ''',
                    (email, name, provider)
                )
            conn.commit()
        logger.info(f"Email sauvegardé pour marketing: {email}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde email marketing: {str(e)}")

def auth_login():
    """Legacy endpoint disabled: Firebase Authentication is required."""
    return jsonify({
        'error': 'Deprecated endpoint. Use Firebase Authentication from frontend and call /auth/verify.'
    }), 410

def auth_register():
    """Legacy endpoint disabled: Firebase Authentication is required."""
    return jsonify({
        'error': 'Deprecated endpoint. Registration is handled by Firebase Authentication.'
    }), 410

def auth_google():
    """Legacy endpoint disabled: Firebase Authentication is required."""
    return jsonify({
        'error': 'Deprecated endpoint. Use Firebase Google Sign-In on frontend and send Firebase ID token to backend.'
    }), 410

def auth_verify():

    """Vérification du token Firebase ou JWT"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Token manquant'}), 401
     
    token = auth_header.replace('Bearer ', '')
    auth_result = verify_auth_token(token)

    if not auth_result:
        return jsonify({'error': 'Token invalide'}), 401

    if auth_result['auth_type'] == 'firebase':
        return jsonify({'user': auth_result['user']}), 200

    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    SELECT
                        u.id::text,
                        u.email,
                        COALESCE(u.name, u.email),
                        COALESCE(u.provider, 'email'),
                        u.phone,
                        COALESCE(p.plan_code, 'free')
                    FROM users u
                    LEFT JOIN user_organizations uo ON uo.user_id = u.id
                    LEFT JOIN plans p
                      ON p.organization_id = uo.organization_id
                     AND p.status IN ('active', 'trialing')
                    WHERE u.id::text = %s OR u.email = %s
                    ORDER BY p.started_at DESC NULLS LAST
                    LIMIT 1
                    ''',
                    (str(auth_result['payload'].get('user_id', '')), auth_result['payload'].get('email', ''))
                )
                user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404

        return jsonify({'user': {
            'id': user[0],
            'email': user[1],
            'name': user[2] or user[1].split('@')[0],
            'provider': user[3] or 'email',
            'plan': user[5] or 'free',
            'phone': user[4]
        }}), 200
    except Exception as exc:
        logger.error(f"Erreur lecture utilisateur PostgreSQL: {str(exc)}")
        return jsonify({'error': 'Erreur serveur'}), 500

def marketing_subscribe():
    """Endpoint pour sauvegarder les emails marketing"""
    data = request.get_json()
    email = data.get('email')
    name = data.get('name', '')
    provider = data.get('provider', 'email')
    
    if not email:
        return jsonify({'error': 'Email requis'}), 400
    
    save_marketing_email(email, name, provider)
    return jsonify({'message': 'Email sauvegardé avec succès'}), 200

def get_google_config():
    """Endpoint pour récupérer la configuration Google côté frontend"""
    # Récupérer directement depuis os.getenv pour éviter les problèmes de contexte
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    return jsonify({
        'client_id': client_id,
        'configured': bool(client_id)
    }), 200

def debug_google_vars():
    """Debug: vérifier les variables Google dans le contexte auth"""
    import os
    return jsonify({
        'GOOGLE_CLIENT_ID_in_auth': os.getenv('GOOGLE_CLIENT_ID'),
        'GOOGLE_CLIENT_ID_variable': GOOGLE_CLIENT_ID,
        'both_equal': os.getenv('GOOGLE_CLIENT_ID') == GOOGLE_CLIENT_ID,
        'configured_check': bool(GOOGLE_CLIENT_ID)
    }), 200

def register_auth_routes(app):
    """Enregistre toutes les routes d'authentification"""
    
    @app.route('/auth/login', methods=['POST'])
    def route_auth_login():
        return auth_login()
    
    @app.route('/auth/register', methods=['POST'])
    def route_auth_register():
        return auth_register()
    
    # NOUVELLE route Google moderne
    @app.route('/auth/google', methods=['POST'])
    def route_auth_google():
        return auth_google()
    
    @app.route('/auth/verify', methods=['GET'])
    def route_auth_verify():
        return auth_verify()
    
    @app.route('/marketing/subscribe', methods=['POST'])
    def route_marketing_subscribe():
        return marketing_subscribe()
    
    # Configuration Google pour le frontend
    @app.route('/auth/google/config', methods=['GET'])
    def route_google_config():
        return get_google_config()
    
    @app.route('/auth/debug', methods=['GET'])
    def route_debug():
        return debug_google_vars()
    
    logger.info("Routes d'authentification modernes enregistrées")