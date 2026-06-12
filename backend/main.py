from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from config.settings import configure_app
from config.extensions import db, migrate
from routes import register_routes

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    configure_app(app)
    
    # Flask-SQLAlchemy + Flask-Migrate
    db.init_app(app)
    migrate.init_app(app, db)

    # Import all models so Flask-Migrate can detect them
    with app.app_context():
        import models  # noqa: F401

    # CORS
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://flexianalyse.com", 
                "http://localhost:5173", 
                "https://flexianalyse.com"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Session-ID", "X-Organization-Id", "X-User-Id"]
        }
    })

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify({"ok": True})
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Session-ID, X-Organization-Id, X-User-Id"
            return response, 200
    
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