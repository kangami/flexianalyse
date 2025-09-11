from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from config.settings import configure_app
from routes import register_routes

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    configure_app(app)
    
    # CORS
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://flexianalyse.com", 
                "http://localhost:5173", 
                "https://flexianalyse.com"
            ]
        }
    })
    
    # Enregistrement des routes
    register_routes(app)
    
    return app

def main():
    app = create_app()
    
    print("🚀 Starting Enhanced AI backend on http://0.0.0.0:5000")
    print("📋 Available models: GPT-3.5-Turbo, GPT-4o, GPT-5, Mistral, Llama3")
    print("🎯 Default model: GPT-3.5-Turbo")
    print("✨ Features: Système d'agents AI, Vector stores, Recherche intelligente")
    
    app.run(debug=False, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()