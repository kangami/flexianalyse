# auth.py - Version moderne avec Google Identity Services
import os
import jwt
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from google.oauth2 import id_token
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# Configuration
DATABASE_PATH = 'flexianalyse_users.db'
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

def init_database():
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Table des utilisateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            provider TEXT DEFAULT 'email',
            google_id TEXT,
            password_hash TEXT,
            picture_url TEXT,
            plan TEXT DEFAULT 'free',
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Ajouter la colonne plan si elle n'existe pas (pour les bases existantes)
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN plan TEXT DEFAULT "free"')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà
    
    # Ajouter la colonne phone si elle n'existe pas
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN phone TEXT')
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà
    
    # Table pour les emails marketing
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marketing_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            provider TEXT DEFAULT 'email',
            source TEXT DEFAULT 'flexianalyse_signup',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_subscribed BOOLEAN DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Base de données initialisée")

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

def save_marketing_email(email, name, provider):
    """Sauvegarde l'email pour le marketing"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO marketing_emails (email, name, provider, created_at)
            VALUES (?, ?, ?, ?)
        ''', (email, name, provider, datetime.utcnow()))
        
        conn.commit()
        conn.close()
        logger.info(f"Email sauvegardé pour marketing: {email}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde email marketing: {str(e)}")

def auth_login():
    """Authentification par email/password"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email et mot de passe requis'}), 400
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    
    if user and user[5] and check_password_hash(user[5], password):
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                      (datetime.utcnow(), user[0]))
        
        # S'assurer que l'utilisateur a un plan
        cursor.execute('UPDATE users SET plan = ? WHERE id = ? AND (plan IS NULL OR plan = "")', ('free', user[0]))
        
        conn.commit()
        
        # Récupérer le plan, le téléphone et la photo de l'utilisateur
        cursor.execute('SELECT plan, phone, picture_url FROM users WHERE id = ?', (user[0],))
        plan_result = cursor.fetchone()
        user_plan = plan_result[0] if plan_result and plan_result[0] else 'free'
        user_phone = plan_result[1] if plan_result and len(plan_result) > 1 else None
        user_picture = plan_result[2] if plan_result and len(plan_result) > 2 else None
        
        user_data = {
            'id': user[0],
            'email': user[1],
            'name': user[2] or email.split('@')[0],
            'provider': 'email',
            'plan': user_plan,
            'phone': user_phone,
            'picture_url': user_picture
        }
        
        token = create_jwt_token(user_data)
        save_marketing_email(email, user_data['name'], 'email')
        
        conn.close()
        
        return jsonify({
            'token': token,
            'user': user_data
        }), 200
    
    conn.close()
    return jsonify({'error': 'Email ou mot de passe incorrect'}), 401

def auth_register():
    """Inscription par email/password"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', email.split('@')[0] if email else '')
    
    if not email or not password:
        return jsonify({'error': 'Email et mot de passe requis'}), 400
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Un compte existe déjà avec cet email'}), 409
    
    password_hash = generate_password_hash(password)
    phone = data.get('phone')
    cursor.execute('''
        INSERT INTO users (email, name, provider, password_hash, plan, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (email, name, 'email', password_hash, 'free', phone, datetime.utcnow()))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    user_data = {
        'id': user_id,
        'email': email,
        'name': name,
        'provider': 'email',
        'plan': 'free',
        'phone': phone
    }
    
    token = create_jwt_token(user_data)
    save_marketing_email(email, name, 'email')
    
    return jsonify({
        'token': token,
        'user': user_data
    }), 201

def auth_google():
    """Authentification Google moderne avec token verification"""
    logger.info("=== REQUÊTE GOOGLE REÇUE ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    if not client_id:
        logger.error("GOOGLE_CLIENT_ID manquant")
        return jsonify({'error': 'Google OAuth non configuré'}), 500
    
    data = request.get_json()
    logger.info(f"Data reçue: {data}")
    if not data:
        return jsonify({'error': 'Token Google requis'}), 400
        
    google_token = data.get('token')
    if not google_token:
        return jsonify({'error': 'Token Google manquant'}), 400
    
    try:
        # Vérifier le token avec Google
        logger.info("Vérification du token Google...")
        idinfo = id_token.verify_oauth2_token(
            google_token, 
            Request(), 
            client_id
        )
        
        # Extraire les informations utilisateur
        google_id = idinfo["sub"]
        email = idinfo["email"]
        name = idinfo.get("name", email.split('@')[0])
        picture_url = idinfo.get("picture", "")
        
        logger.info(f"Token Google valide pour: {email}")
        
        # Sauvegarder/récupérer l'utilisateur
        logger.info("Ouverture de la connexion SQLite...")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        logger.info("Connexion SQLite ouverte.")
        
        cursor.execute('SELECT * FROM users WHERE email = ? OR google_id = ?', (email, google_id))
        user = cursor.fetchone()
        logger.info(f"Utilisateur trouvé: {user}")
        
        if user:
            # Utilisateur existant
            cursor.execute('''
                UPDATE users SET 
                    last_login = ?, 
                    google_id = ?, 
                    name = COALESCE(NULLIF(?, ''), name),
                    picture_url = COALESCE(NULLIF(?, ''), picture_url)
                WHERE id = ?
            ''', (datetime.utcnow(), google_id, name, picture_url, user[0]))
            user_id = user[0]
            final_name = user[2] or name
        else:
            # Nouvel utilisateur
            cursor.execute('''
                INSERT INTO users (email, name, provider, google_id, picture_url, plan, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (email, name, 'google', google_id, picture_url, 'free', datetime.utcnow(), datetime.utcnow()))
            user_id = cursor.lastrowid
            final_name = name
        
        # S'assurer que tous les utilisateurs ont un plan
        cursor.execute('UPDATE users SET plan = ? WHERE id = ? AND (plan IS NULL OR plan = "")', ('free', user_id))
        
        conn.commit()
        
        # Récupérer le plan de l'utilisateur
        cursor.execute('SELECT plan FROM users WHERE id = ?', (user_id,))
        plan_result = cursor.fetchone()
        user_plan = plan_result[0] if plan_result and plan_result[0] else 'free'
        
        conn.close()
        
        user_data = {
            'id': user_id,
            'email': email,
            'name': final_name,
            'provider': 'google',
            'picture_url': picture_url,
            'plan': user_plan
        }
        
        token = create_jwt_token(user_data)
        logger.info("Token JWT créé.")

        save_marketing_email(email, final_name, 'google')
        logger.info("Email marketing sauvegardé.")
        
        logger.info(f"Authentification Google réussie pour: {email}")
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user_data
        }), 200
        
    except ValueError as e:
        logger.error(f"Token Google invalide: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Token Google invalide'
        }), 400
    except Exception as e:
        logger.error(f"Erreur lors de l'authentification Google: {str(e)}", exc_info=True) 
        return jsonify({
            'success': False,
            'error': 'Erreur lors de l\'authentification Google'
        }), 500

def auth_verify():
    """Vérification du token JWT"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Token manquant'}), 401
    
    token = auth_header.replace('Bearer ', '')
    payload = verify_jwt_token(token)
    
    if not payload:
        return jsonify({'error': 'Token invalide'}), 401
    
    # Récupérer les informations complètes de l'utilisateur depuis la base de données
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, email, name, provider, picture_url, plan, phone FROM users WHERE id = ?', (payload['user_id'],))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    
    # S'assurer que l'utilisateur a un plan
    user_plan = user[5] if user[5] else 'free'
    
    return jsonify({'user': {
        'id': user[0],
        'email': user[1],
        'name': user[2] or user[1].split('@')[0],
        'provider': user[3] or 'email',
        'picture_url': user[4],
        'plan': user_plan,
        'phone': user[6]
    }}), 200

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