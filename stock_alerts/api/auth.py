"""Authentication utilities for API."""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    import jwt
except ImportError:
    jwt = None

from ..infrastructure.config import get_config
from ..services.user_service import UserService

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated user context."""
    
    def __init__(
        self,
        user_id: int,
        username: str,
        is_admin: bool = False,
        permissions: Optional[list] = None,
        auth_type: str = "jwt",
    ):
        self.user_id = user_id
        self.username = username
        self.is_admin = is_admin
        self.permissions = permissions or []
        self.auth_type = auth_type
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.is_admin:
            return True
        return permission in self.permissions


def create_access_token(user_id: int, username: str, is_admin: bool = False) -> str:
    """Create JWT access token."""
    if jwt is None:
        raise RuntimeError("PyJWT not installed")
    
    config = get_config()
    
    payload = {
        'sub': str(user_id),
        'username': username,
        'is_admin': is_admin,
        'exp': datetime.utcnow() + timedelta(minutes=config.jwt_expire_minutes),
        'iat': datetime.utcnow(),
    }
    
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    if jwt is None:
        return None
    
    config = get_config()
    
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> AuthUser:
    """
    Get current authenticated user.
    
    Supports both JWT tokens and API keys.
    """
    # Try API key first
    if x_api_key:
        user_service = UserService()
        result = user_service.verify_api_key(x_api_key)
        
        if result:
            user_id, permissions = result
            user = user_service.get_user(user_id)
            
            if user and user.is_active:
                return AuthUser(
                    user_id=user.id,
                    username=user.username,
                    is_admin=user.is_admin,
                    permissions=permissions,
                    auth_type="api_key",
                )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Try JWT token
    if credentials:
        payload = decode_access_token(credentials.credentials)
        
        if payload:
            return AuthUser(
                user_id=int(payload['sub']),
                username=payload['username'],
                is_admin=payload.get('is_admin', False),
                auth_type="jwt",
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[AuthUser]:
    """Get current user if authenticated, otherwise None."""
    try:
        return await get_current_user(credentials, x_api_key)
    except HTTPException:
        return None


def require_permission(permission: str):
    """Dependency to require a specific permission."""
    async def check_permission(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )
        return user
    
    return check_permission


def require_admin():
    """Dependency to require admin access."""
    async def check_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return user
    
    return check_admin
