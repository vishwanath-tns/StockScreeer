"""User API endpoints."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr

from ..auth import AuthUser, get_current_user, create_access_token, require_admin
from ...services.user_service import UserService

router = APIRouter()


# ==================== Pydantic Models ====================

class UserLogin(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserRegister(BaseModel):
    """Registration request model."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    max_alerts: int
    is_active: bool
    is_admin: bool


class ApiKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = Field(default=['alerts:read', 'alerts:write'])
    expires_days: Optional[int] = Field(None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    """API key response (after creation, includes raw key)."""
    id: str
    name: str
    prefix: str
    key: Optional[str] = None  # Only returned on creation
    permissions: List[str]
    expires_at: Optional[str]
    created_at: str


# ==================== Endpoints ====================

@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Authenticate and get access token."""
    service = UserService()
    
    user = service.authenticate(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    token = create_access_token(user.id, user.username, user.is_admin)
    
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister):
    """Register a new user."""
    service = UserService()
    
    # Check if username exists
    if service.get_user_by_username(data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    # Check if email exists
    if service.get_user_by_email(data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    user = service.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        max_alerts=user.max_alerts,
        is_active=user.is_active,
        is_admin=user.is_admin,
    )


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    """Get current user information."""
    service = UserService()
    
    user_data = service.get_user(user.user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        id=user_data.id,
        username=user_data.username,
        email=user_data.email,
        max_alerts=user_data.max_alerts,
        is_active=user_data.is_active,
        is_admin=user_data.is_admin,
    )


# ==================== API Key Management ====================

@router.post("/users/me/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    user: AuthUser = Depends(get_current_user),
):
    """Create a new API key."""
    service = UserService()
    
    result = service.create_api_key(
        user_id=user.user_id,
        name=data.name,
        permissions=data.permissions,
        expires_days=data.expires_days,
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create API key (limit reached?)",
        )
    
    api_key, raw_key = result
    
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        key=raw_key,  # Only returned here!
        permissions=api_key.permissions,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        created_at=api_key.created_at.isoformat(),
    )


@router.get("/users/me/api-keys")
async def list_api_keys(user: AuthUser = Depends(get_current_user)):
    """List all API keys for current user."""
    service = UserService()
    
    keys = service.get_user_api_keys(user.user_id)
    
    return [
        {
            'id': k['id'],
            'name': k['name'],
            'prefix': k['prefix'],
            'permissions': k.get('permissions', []),
            'is_active': k['is_active'],
            'expires_at': k['expires_at'].isoformat() if k.get('expires_at') else None,
            'created_at': k['created_at'].isoformat() if k.get('created_at') else None,
            'last_used_at': k['last_used_at'].isoformat() if k.get('last_used_at') else None,
        }
        for k in keys
    ]


@router.delete("/users/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """Revoke an API key."""
    service = UserService()
    
    if not service.revoke_api_key(key_id, user.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
