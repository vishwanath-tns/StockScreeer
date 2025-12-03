"""User service - authentication and user management."""

import logging
import hashlib
import secrets
import uuid
from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy import text

from ..core.models import User, ApiKey
from ..infrastructure.database import Database, get_database

logger = logging.getLogger(__name__)


class UserService:
    """Service for user authentication and management."""
    
    def __init__(self, database: Optional[Database] = None):
        self.db = database or get_database()
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        max_alerts: int = 50,
        is_admin: bool = False,
    ) -> Optional[User]:
        """Create a new user."""
        password_hash = self._hash_password(password)
        
        engine = self.db.get_sync_engine()
        
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, max_alerts, is_admin, created_at)
                    VALUES (:username, :email, :password_hash, :max_alerts, :is_admin, NOW())
                """), {
                    'username': username.lower(),
                    'email': email.lower(),
                    'password_hash': password_hash,
                    'max_alerts': max_alerts,
                    'is_admin': is_admin,
                })
                
                result = conn.execute(text("SELECT LAST_INSERT_ID()"))
                user_id = result.scalar()
            
            logger.info(f"Created user {username} (ID: {user_id})")
            return self.get_user(user_id)
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM users WHERE id = :id
            """), {'id': user_id})
            
            row = result.fetchone()
            if row:
                return self._row_to_user(row._mapping)
        
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM users WHERE username = :username
            """), {'username': username.lower()})
            
            row = result.fetchone()
            if row:
                return self._row_to_user(row._mapping)
        
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM users WHERE email = :email
            """), {'email': email.lower()})
            
            row = result.fetchone()
            if row:
                return self._row_to_user(row._mapping)
        
        return None
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password."""
        user = self.get_user_by_username(username)
        
        if not user:
            return None
        
        if not self._verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        self._update_last_login(user.id)
        
        return user
    
    def _update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        engine = self.db.get_sync_engine()
        
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE users SET last_login_at = NOW() WHERE id = :id
            """), {'id': user_id})
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt or fallback."""
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            # Fallback to SHA-256 (not recommended for production)
            return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ImportError:
            # Fallback verification
            return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    def _row_to_user(self, row: dict) -> User:
        """Convert database row to User object."""
        import json
        
        notification_settings = row.get('notification_settings')
        if isinstance(notification_settings, str):
            notification_settings = json.loads(notification_settings)
        
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            password_hash=row['password_hash'],
            max_alerts=row.get('max_alerts', 50),
            max_api_keys=row.get('max_api_keys', 5),
            is_active=bool(row.get('is_active', True)),
            is_admin=bool(row.get('is_admin', False)),
            notification_settings=notification_settings or {},
            created_at=row['created_at'],
            last_login_at=row.get('last_login_at'),
        )
    
    # ==================== API Key Management ====================
    
    def create_api_key(
        self,
        user_id: int,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_days: Optional[int] = None,
    ) -> Optional[tuple]:
        """
        Create a new API key for a user.
        
        Returns tuple of (ApiKey, raw_key) - raw_key is only shown once!
        """
        import json
        
        # Check user's API key limit
        user = self.get_user(user_id)
        if not user:
            return None
        
        existing_count = self._count_user_api_keys(user_id)
        if existing_count >= user.max_api_keys:
            logger.warning(f"User {user_id} at API key limit")
            return None
        
        # Generate key
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]
        key_id = str(uuid.uuid4())
        
        if permissions is None:
            permissions = ['alerts:read', 'alerts:write']
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        engine = self.db.get_sync_engine()
        
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO api_keys (id, user_id, name, key_hash, prefix, permissions, expires_at, created_at)
                    VALUES (:id, :user_id, :name, :key_hash, :prefix, :permissions, :expires_at, NOW())
                """), {
                    'id': key_id,
                    'user_id': user_id,
                    'name': name,
                    'key_hash': key_hash,
                    'prefix': prefix,
                    'permissions': json.dumps(permissions),
                    'expires_at': expires_at,
                })
            
            api_key = ApiKey(
                id=key_id,
                user_id=user_id,
                name=name,
                key_hash=key_hash,
                prefix=prefix,
                permissions=permissions,
                expires_at=expires_at,
            )
            
            logger.info(f"Created API key {prefix}... for user {user_id}")
            return (api_key, raw_key)
            
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return None
    
    def verify_api_key(self, raw_key: str) -> Optional[tuple]:
        """
        Verify API key and return (user_id, permissions).
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM api_keys 
                WHERE key_hash = :key_hash AND is_active = TRUE
            """), {'key_hash': key_hash})
            
            row = result.fetchone()
            if not row:
                return None
            
            row = row._mapping
            
            # Check expiration
            if row.get('expires_at') and row['expires_at'] < datetime.now():
                return None
            
            # Update last used
            conn.execute(text("""
                UPDATE api_keys SET last_used_at = NOW() WHERE id = :id
            """), {'id': row['id']})
            
            import json
            permissions = row.get('permissions')
            if isinstance(permissions, str):
                permissions = json.loads(permissions)
            
            return (row['user_id'], permissions or [])
    
    def get_user_api_keys(self, user_id: int) -> List[dict]:
        """Get all API keys for a user (without key values)."""
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, prefix, permissions, is_active, expires_at, created_at, last_used_at
                FROM api_keys WHERE user_id = :user_id
            """), {'user_id': user_id})
            
            return [dict(row._mapping) for row in result]
    
    def revoke_api_key(self, key_id: str, user_id: int) -> bool:
        """Revoke (deactivate) an API key."""
        engine = self.db.get_sync_engine()
        
        with engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE api_keys SET is_active = FALSE 
                WHERE id = :id AND user_id = :user_id
            """), {'id': key_id, 'user_id': user_id})
            
            return result.rowcount > 0
    
    def _count_user_api_keys(self, user_id: int) -> int:
        """Count active API keys for a user."""
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM api_keys 
                WHERE user_id = :user_id AND is_active = TRUE
            """), {'user_id': user_id})
            
            return result.scalar() or 0
