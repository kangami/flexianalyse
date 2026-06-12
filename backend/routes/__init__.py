from controllers import api_bp, register_all
from auth import gdrive_auth_bp, sharepoint_auth_bp
from controllers.mcp_controller import mcp_bp


def register_routes(app):
    """Enregistre les blueprints — anciennes + nouvelles routes MVC."""
    register_all()  # Enregistre les routes de l'API v2
    # Nouvelles routes MVC (api/v2)
    app.register_blueprint(api_bp)
    # OAuth routes for connectors (/auth/google_drive, /auth/sharepoint)
    app.register_blueprint(gdrive_auth_bp)
    app.register_blueprint(sharepoint_auth_bp)
    app.register_blueprint(mcp_bp)  # Routes spécifiques aux MCP (ex: /mcp/drive/files)


