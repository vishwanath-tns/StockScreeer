"""MySQL database connection and operations."""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, Text, Enum as SQLEnum, JSON
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

# Optional async support
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

from .config import Config, get_config

logger = logging.getLogger(__name__)


# SQL Schema for alerts_db
SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    max_alerts INT DEFAULT 50,
    max_api_keys INT DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    notification_settings JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    prefix VARCHAR(8) NOT NULL,
    permissions JSON,
    rate_limit_per_minute INT DEFAULT 60,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_prefix (prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Price Alerts table
CREATE TABLE IF NOT EXISTS price_alerts (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    yahoo_symbol VARCHAR(50) NOT NULL,
    asset_type ENUM('nse_equity', 'bse_equity', 'nse_index', 'commodity', 'crypto', 'forex') NOT NULL,
    alert_type ENUM('price', 'volume', 'technical', 'custom') NOT NULL,
    `condition` VARCHAR(50) NOT NULL,
    target_value DECIMAL(20, 4) NOT NULL,
    target_value_2 DECIMAL(20, 4),
    status ENUM('active', 'triggered', 'paused', 'expired', 'cancelled') DEFAULT 'active',
    priority ENUM('low', 'normal', 'high', 'critical') DEFAULT 'normal',
    notification_channels JSON,
    webhook_url VARCHAR(500),
    trigger_once BOOLEAN DEFAULT TRUE,
    cooldown_minutes INT DEFAULT 60,
    expires_at DATETIME,
    source VARCHAR(50) DEFAULT 'manual',
    source_id VARCHAR(100),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_triggered_at DATETIME,
    trigger_count INT DEFAULT 0,
    previous_price DECIMAL(20, 4),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_symbol (symbol),
    INDEX idx_yahoo_symbol (yahoo_symbol),
    INDEX idx_status (status),
    INDEX idx_asset_type (asset_type),
    INDEX idx_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Alert History table
CREATE TABLE IF NOT EXISTS alert_history (
    id VARCHAR(36) PRIMARY KEY,
    alert_id VARCHAR(36) NOT NULL,
    user_id INT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    `condition` VARCHAR(50) NOT NULL,
    target_value DECIMAL(20, 4) NOT NULL,
    actual_value DECIMAL(20, 4) NOT NULL,
    notifications_sent JSON,
    notification_results JSON,
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_alert_id (alert_id),
    INDEX idx_user_id (user_id),
    INDEX idx_triggered_at (triggered_at),
    INDEX idx_user_triggered (user_id, triggered_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Watchlists table
CREATE TABLE IF NOT EXISTS watchlists (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    watchlist_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    yahoo_symbol VARCHAR(50) NOT NULL,
    asset_type ENUM('nse_equity', 'bse_equity', 'nse_index', 'commodity', 'crypto', 'forex') NOT NULL,
    sort_order INT DEFAULT 0,
    notes TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_watchlist_symbol (user_id, watchlist_name, symbol),
    INDEX idx_user_watchlist (user_id, watchlist_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Symbol cache table (for quick lookups)
CREATE TABLE IF NOT EXISTS symbol_cache (
    yahoo_symbol VARCHAR(50) PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    asset_type ENUM('nse_equity', 'bse_equity', 'nse_index', 'commodity', 'crypto', 'forex') NOT NULL,
    exchange VARCHAR(50),
    currency VARCHAR(10),
    last_price DECIMAL(20, 4),
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_asset_type (asset_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- System settings table
CREATE TABLE IF NOT EXISTS system_settings (
    `key` VARCHAR(100) PRIMARY KEY,
    `value` TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create default admin user (password: admin123 - CHANGE THIS!)
INSERT IGNORE INTO users (username, email, password_hash, is_admin, max_alerts, max_api_keys)
VALUES ('admin', 'admin@localhost', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4jKzKKPj0H1.3vPC', TRUE, 1000, 100);
"""


class Database:
    """Database connection manager."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._sync_engine: Optional[Engine] = None
        self._async_engine = None
        
    def get_sync_engine(self) -> Engine:
        """Get synchronous SQLAlchemy engine."""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.config.database.sync_url,
                pool_size=self.config.database.pool_size,
                pool_recycle=self.config.database.pool_recycle,
                pool_pre_ping=True,
                echo=self.config.api_debug,
            )
        return self._sync_engine
    
    def get_async_engine(self):
        """Get async SQLAlchemy engine."""
        if not ASYNC_AVAILABLE:
            raise RuntimeError("Async SQLAlchemy not available. Install aiomysql.")
        
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.config.database.async_url,
                pool_size=self.config.database.pool_size,
                pool_recycle=self.config.database.pool_recycle,
                pool_pre_ping=True,
                echo=self.config.api_debug,
            )
        return self._async_engine
    
    def init_schema(self):
        """Initialize database schema."""
        engine = self.get_sync_engine()
        
        # Split and execute each statement
        statements = [s.strip() for s in SCHEMA_SQL.split(';') if s.strip()]
        
        with engine.begin() as conn:
            for statement in statements:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    # Ignore "table exists" errors, log others
                    if 'already exists' not in str(e).lower():
                        logger.warning(f"Schema statement warning: {e}")
        
        logger.info("Database schema initialized")
    
    def check_connection(self) -> bool:
        """Test database connection."""
        try:
            engine = self.get_sync_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    @asynccontextmanager
    async def async_session(self):
        """Get async database session."""
        engine = self.get_async_engine()
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    def close(self):
        """Close all connections."""
        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None
        
        if self._async_engine:
            # For async engine, use sync_engine.dispose() or handle in async context
            pass


# Module-level singleton
_database: Optional[Database] = None


def get_database() -> Database:
    """Get or create database singleton."""
    global _database
    if _database is None:
        _database = Database()
    return _database


def init_database():
    """Initialize database with schema."""
    db = get_database()
    db.init_schema()
    return db
