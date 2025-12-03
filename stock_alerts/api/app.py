"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..infrastructure.config import Config, get_config
from ..infrastructure.database import Database, get_database, init_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Stock Alert API...")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Stock Alert API...")
    
    db = get_database()
    db.close()


def create_app(config: Optional[Config] = None) -> FastAPI:
    """Create FastAPI application."""
    config = config or get_config()
    
    app = FastAPI(
        title="Stock Alert System API",
        description="REST API for managing stock price alerts",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    from .routes import alerts, users, symbols, health
    
    app.include_router(health.router, tags=["Health"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])
    app.include_router(symbols.router, prefix="/api/v1", tags=["Symbols"])
    
    return app


# Create default app instance
app = create_app()
