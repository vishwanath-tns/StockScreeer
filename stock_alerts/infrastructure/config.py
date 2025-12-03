"""Configuration management for Stock Alert System."""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    """MySQL database configuration."""
    host: str = "localhost"
    port: int = 3306
    database: str = "alerts_db"
    user: str = "root"
    password: str = ""
    charset: str = "utf8mb4"
    pool_size: int = 5
    pool_recycle: int = 3600
    
    @property
    def sync_url(self) -> str:
        """SQLAlchemy sync connection URL."""
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.password) if self.password else ""
        return f"mysql+pymysql://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
    
    @property
    def async_url(self) -> str:
        """SQLAlchemy async connection URL."""
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.password) if self.password else ""
        return f"mysql+aiomysql://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"


@dataclass
class RedisConfig:
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    # Channel names for pub/sub
    price_channel: str = "alerts:prices"
    alert_channel: str = "alerts:triggered"
    system_channel: str = "alerts:system"
    
    @property
    def url(self) -> str:
        """Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class YahooFinanceConfig:
    """Yahoo Finance API configuration."""
    # Batch sizes for different asset types
    nse_batch_size: int = 50
    bse_batch_size: int = 50
    commodity_batch_size: int = 20
    crypto_batch_size: int = 20
    
    # Polling intervals (seconds)
    market_hours_interval: int = 5
    off_hours_interval: int = 60
    
    # Rate limiting
    requests_per_minute: int = 100
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass  
class NotificationConfig:
    """Notification settings."""
    # Desktop notifications
    desktop_enabled: bool = True
    desktop_duration: int = 5000  # milliseconds
    
    # Sound alerts
    sound_enabled: bool = True
    sound_file: Optional[str] = None  # Path to custom sound
    
    # Webhook settings
    webhook_timeout: int = 10  # seconds
    webhook_retries: int = 3


@dataclass
class Config:
    """Main configuration class."""
    # Component configs
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    yahoo: YahooFinanceConfig = field(default_factory=YahooFinanceConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    
    # JWT settings
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    
    # Worker settings
    price_monitor_workers: int = 1
    alert_evaluator_workers: int = 2
    notification_workers: int = 2
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        config = cls()
        
        # Database config
        config.database = DatabaseConfig(
            host=os.getenv('ALERTS_DB_HOST', os.getenv('MYSQL_HOST', 'localhost')),
            port=int(os.getenv('ALERTS_DB_PORT', os.getenv('MYSQL_PORT', '3306'))),
            database=os.getenv('ALERTS_DB_NAME', 'alerts_db'),
            user=os.getenv('ALERTS_DB_USER', os.getenv('MYSQL_USER', 'root')),
            password=os.getenv('ALERTS_DB_PASSWORD', os.getenv('MYSQL_PASSWORD', '')),
        )
        
        # Redis config
        config.redis = RedisConfig(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
        )
        
        # Yahoo Finance config
        config.yahoo = YahooFinanceConfig(
            market_hours_interval=int(os.getenv('PRICE_INTERVAL_MARKET', '5')),
            off_hours_interval=int(os.getenv('PRICE_INTERVAL_OFF', '60')),
        )
        
        # Notification config
        config.notification = NotificationConfig(
            desktop_enabled=os.getenv('DESKTOP_NOTIFICATIONS', 'true').lower() == 'true',
            sound_enabled=os.getenv('SOUND_ALERTS', 'true').lower() == 'true',
            sound_file=os.getenv('ALERT_SOUND_FILE'),
        )
        
        # API config
        config.api_host = os.getenv('API_HOST', '0.0.0.0')
        config.api_port = int(os.getenv('API_PORT', '8000'))
        config.api_debug = os.getenv('API_DEBUG', 'false').lower() == 'true'
        
        # JWT config
        config.jwt_secret = os.getenv('JWT_SECRET', config.jwt_secret)
        
        # Logging
        config.log_level = os.getenv('LOG_LEVEL', 'INFO')
        config.log_file = os.getenv('LOG_FILE')
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for debugging, hides passwords)."""
        return {
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'database': self.database.database,
                'user': self.database.user,
                'password': '***' if self.database.password else None,
            },
            'redis': {
                'host': self.redis.host,
                'port': self.redis.port,
                'db': self.redis.db,
            },
            'api': {
                'host': self.api_host,
                'port': self.api_port,
            },
            'log_level': self.log_level,
        }


# Singleton instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create configuration singleton."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config():
    """Reset configuration (for testing)."""
    global _config
    _config = None
