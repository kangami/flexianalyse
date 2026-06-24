"""Celery application factory."""
from celery import Celery
import os


def _create_worker_app():
    """Minimal Flask app for standalone Celery worker processes."""
    from flask import Flask
    from config.settings import configure_app
    from config.extensions import db

    app = Flask(__name__)
    configure_app(app)
    db.init_app(app)

    with app.app_context():
        import models  # noqa: F401 — ensure all models are registered

    return app


def make_celery(app=None):
    if app is None:
        app = _create_worker_app()

    celery = Celery('flexianalyse')
    celery.config_from_object('config.celery_config')

    # Explicitly include task modules (full dotted paths)
    celery.conf.include = [
        'ai.agents.office_manager.ingestion.tasks',
    ]

    # Wrap every task call inside a Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    return celery


celery_app = make_celery()