"""
Configuration Flask et authentification
"""
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration d'authentification
class AuthConfig:
    JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    DATABASE_PATH = 'flexianalyse_users.db'
    
    @classmethod
    def is_google_configured(cls):
        return bool(cls.GOOGLE_CLIENT_ID and cls.GOOGLE_CLIENT_SECRET)
    
    @classmethod
    def get_google_client_id(cls):
        """Retourne le Google Client ID"""
        return cls.GOOGLE_CLIENT_ID

# Configuration des modèles IA
class AIConfig:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    
    DEFAULT_MODEL = "gpt-3.5-turbo"
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    OLLAMA_MODELS = ["llama3.2", "llama3"]
    MISTRAL_MODEL = "mistral-medium-2505"

# Configuration Flask
class FlaskConfig:
    CORS_ORIGINS = [
        "http://flexianalyse.com", 
        "http://localhost:5173", 
        "https://flexianalyse.com"
    ]
    
    @classmethod
    def validate_env_vars(cls):
        """Valide que les variables d'environnement critiques sont présentes"""
        missing = []
        
        if not AIConfig.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        
        if AuthConfig.is_google_configured():
            print("✅ Google OAuth configuré")
        else:
            print("⚠️ Google OAuth non configuré (GOOGLE_CLIENT_ID/SECRET manquants)")
        
        if missing:
            raise ValueError(f"Variables d'environnement manquantes: {', '.join(missing)}")
        
        return True

