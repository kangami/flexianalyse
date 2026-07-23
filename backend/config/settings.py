"""
Configuration de l'application Flask.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def configure_app(app):
    """Configure l'application Flask avec les variables d'environnement."""
    app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'dev-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max upload
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    host = os.getenv('PG_HOST', 'localhost')
    port = os.getenv('PG_PORT', '5432')
    dbname = os.getenv('PG_DATABASE', 'flexianalyse')
    user = os.getenv('PG_USER', 'postgres')
    password = os.getenv('PG_PASSWORD', '')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Postgres managé (Render) coupe les connexions inactives : pendant un long
    # crawl/embedding la connexion reste idle et meurt → 'SSL SYSCALL error: EOF
    # detected' au commit suivant. pool_pre_ping teste/renouvelle la connexion
    # avant chaque usage ; pool_recycle la recycle avant le timeout idle serveur.
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
