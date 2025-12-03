"""FastAPI REST API for Stock Alert System."""

from .app import create_app, app
from .routes import alerts, users, symbols, health

__all__ = ['create_app', 'app']
