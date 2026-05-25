from controllers import api_bp


def register_routes(app):
    """Enregistre les blueprints — anciennes + nouvelles routes MVC."""
    # Nouvelles routes MVC (api/v2)
    app.register_blueprint(api_bp)


