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
