import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from config.settings import configure_app
from config.extensions import db, migrate
from routes import register_routes
from celery_app import make_celery
from admin import init_admin

load_dotenv()


def mount_legacy_ai_routes(app):
    """Mount the old AI/RAG routes on the app created by this entry point."""
    from legacy_ai_routes import app as legacy_app

    existing_rules = {
        (rule.rule, tuple(sorted(rule.methods - {"HEAD", "OPTIONS"})))
        for rule in app.url_map.iter_rules()
    }

    for rule in legacy_app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue

        methods = tuple(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        rule_key = (rule.rule, methods)
        if rule_key in existing_rules:
            continue

        app.add_url_rule(
            rule.rule,
            endpoint=f"legacy_ai.{rule.endpoint}",
            view_func=legacy_app.view_functions[rule.endpoint],
            methods=list(methods),
            defaults=rule.defaults,
            strict_slashes=rule.strict_slashes,
        )
        existing_rules.add(rule_key)


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

    # CORS — origines autorisées (le domaine du frontend Vercel via FRONTEND_URL)
    allowed_origins = [
        "http://flexianalyse.com",
        "http://localhost:5173",
        "https://flexianalyse.com",
    ]
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url and frontend_url not in allowed_origins:
        allowed_origins.append(frontend_url)

    CORS(app, resources={
        r"/*": {
            "origins": allowed_origins,
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
    #mount_legacy_ai_routes(app)
    
    # Celery avec contexte Flask
    celery = make_celery(app)
    app.celery = celery

    # Initialiser Flask-Admin
    init_admin(app)

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
