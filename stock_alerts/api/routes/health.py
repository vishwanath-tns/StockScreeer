"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

from ..infrastructure.database import get_database
from ..infrastructure.redis_client import get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "stock-alert-api",
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependency status."""
    status_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "dependencies": {},
    }
    
    # Check database
    try:
        db = get_database()
        db_ok = db.check_connection()
        status_data["dependencies"]["database"] = {
            "status": "healthy" if db_ok else "unhealthy",
        }
    except Exception as e:
        status_data["dependencies"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        status_data["status"] = "degraded"
    
    # Check Redis
    try:
        redis = get_redis()
        redis_ok = redis.ping()
        status_data["dependencies"]["redis"] = {
            "status": "healthy" if redis_ok else "unhealthy",
        }
    except Exception as e:
        status_data["dependencies"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        status_data["status"] = "degraded"
    
    return status_data


@router.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Stock Alert System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
