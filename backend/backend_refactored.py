"""
Backend principal refactorisé - Point d'entrée simplifié
Ce fichier importe tous les modules et configure l'application Flask
"""
import os
import logging
from flask import Flask, request, jsonify, Response, stream_with_context
from flask.helpers import make_response
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime

# Imports des modules refactorisés
from config.models import MODEL_CONFIG, DEFAULT_MODEL, MISTRAL_MODEL, OLLAMA_MODELS
from config import AuthConfig, FlaskConfig
from utils.file_utils import extract_text_from_docx, extract_text_from_pdf
from utils.translations import translations
from services.api_clients import (
    call_openai_api, call_mistral_api, call_ollama_api, 
    stream_response, openai_client, get_model_config
)
from services.analysis_service import analyze_file_content, save_file_description
from services.search_service import perform_online_search, search_serpapi, rerank_documents_with_llm
from services.vector_store_service import (
    vector_stores, embeddings, get_vector_store, 
    create_vector_store, add_documents_to_vector_store
)
from auth import register_auth_routes, init_database

# Imports LangChain
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import Dict, List, Optional, Any
import aiocache
import asyncio

# Load environment variables
load_dotenv()

# Debug: Vérifier le chargement des variables d'environnement
print(f"GOOGLE_CLIENT_ID chargé: {os.getenv('GOOGLE_CLIENT_ID')[:20] + '...' if os.getenv('GOOGLE_CLIENT_ID') else 'NON CHARGÉ'}")
print(f"OPENAI_API_KEY chargé: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": ["http://flexianalyse.com", "http://localhost:5173", "https://flexianalyse.com"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "Session-ID"]
}})

# Ajouter un handler pour les requêtes OPTIONS (CORS preflight)
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,Session-ID")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        return response

# Cache setup
cache = aiocache.SimpleMemoryCache()

# Description file path
DESCRIPTIONS_FILE = os.path.join(os.path.dirname(__file__), "file_descriptions.json")
if not os.path.exists(DESCRIPTIONS_FILE):
    with open(DESCRIPTIONS_FILE, 'w') as f:
        import json
        json.dump([], f)

# Validation de la configuration
try:
    FlaskConfig.validate_env_vars()
    logger.info("✅ Configuration validée")
except ValueError as e:
    logger.error(f"❌ Erreur de configuration: {e}")

# Initialisation de la base de données d'authentification
init_database()

# Enregistrement des routes d'authentification
register_auth_routes(app)

# NOTE: Les routes principales (@app.route) restent dans ce fichier pour l'instant
# mais utilisent les services modulaires importés ci-dessus.
# À terme, elles pourront être déplacées dans routes/file_routes.py, routes/query_routes.py, etc.

# Import des fonctions restantes depuis l'ancien backend.py
# (Ces fonctions seront progressivement déplacées dans les modules appropriés)
# Pour l'instant, on garde le backend.py original et on crée ce fichier comme référence

if __name__ == "__main__":
    print("🚀 Starting Enhanced AI backend on http://0.0.0.0:5000")
    print(f"📋 Available models: {', '.join(MODEL_CONFIG.keys())}")
    print(f"🎯 Default model: {DEFAULT_MODEL}")
    print("📡 Endpoints:")
    print("   GET  /models - List all available models")
    print("   POST /models/<model_id>/test - Test specific model")
    print("   POST /upload - Upload files for analysis")
    print("   POST /query - Query with selected model")
    print("   POST /index-directory - Index directory files")
    print("🔐 Authentication endpoints:")
    print("   POST /auth/login - Email/password login")
    print("   POST /auth/register - User registration")
    print("   GET  /auth/google - Google OAuth")
    print("   GET  /auth/verify - Verify JWT token")
    print("   POST /marketing/subscribe - Save marketing emails")
    print("   GET  /health - Health check")
    print("   GET  /users/me - Current user info")
    print("✨ New features:")
    print("   • Complete authentication system")
    print("   • Google OAuth integration")
    print("   • Marketing email capture")
    print("   • JWT-based sessions")
    print("   • SQLite database")
    if AuthConfig.is_google_configured():
        print("   • ✅ Google OAuth configured")
    else:
        print("   • ⚠️  Google OAuth NOT configured")
    app.run(debug=False, host='0.0.0.0', port=5000)


