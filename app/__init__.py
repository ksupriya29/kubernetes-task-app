"""
Flask application factory.
"""
import os

from flask import Flask

from .config import config_by_name
from .database import init_db
from .routes import main_bp


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: One of 'development', 'testing', 'production', or 'default'.
                     Falls back to the ``FLASK_ENV`` environment variable, then
                     'default' (DevelopmentConfig / SQLite).
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_by_name[config_name])

    # Initialise extensions
    init_db(app)

    # Register blueprints
    app.register_blueprint(main_bp)

    return app
