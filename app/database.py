"""
Database initialisation.
The SQLAlchemy instance is created here and imported by the rest of the app.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Bind the SQLAlchemy instance to *app* and create all tables."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
