"""Enumerations for the Stock Alert System."""

from enum import Enum, auto


class AlertType(str, Enum):
    """Type of alert to monitor."""
    PRICE = "price"
    VOLUME = "volume"
    TECHNICAL = "technical"
    CUSTOM = "custom"  # For external scanner integration


class AlertCondition(str, Enum):
    """Specific condition to trigger alert."""
    # Price conditions
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_BETWEEN = "price_between"
    PRICE_CROSSES_ABOVE = "price_crosses_above"
    PRICE_CROSSES_BELOW = "price_crosses_below"
    PCT_CHANGE_UP = "pct_change_up"
    PCT_CHANGE_DOWN = "pct_change_down"
    
    # Volume conditions
    VOLUME_ABOVE = "volume_above"
    VOLUME_SPIKE = "volume_spike"  # vs average
    
    # Technical conditions
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    MACD_BULLISH_CROSS = "macd_bullish_cross"
    MACD_BEARISH_CROSS = "macd_bearish_cross"
    SMA_CROSS_ABOVE = "sma_cross_above"
    SMA_CROSS_BELOW = "sma_cross_below"
    BOLLINGER_UPPER = "bollinger_upper"
    BOLLINGER_LOWER = "bollinger_lower"
    HIGH_52W = "52w_high"
    LOW_52W = "52w_low"
    
    # Custom conditions (external scanners)
    SCANNER_SIGNAL = "scanner_signal"


class AlertStatus(str, Enum):
    """Current status of an alert."""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    PAUSED = "paused"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AssetType(str, Enum):
    """Type of asset being monitored."""
    NSE_EQUITY = "nse_equity"       # .NS suffix
    BSE_EQUITY = "bse_equity"       # .BO suffix
    NSE_INDEX = "nse_index"         # ^NSEI, ^NSEBANK
    COMMODITY = "commodity"         # GC=F, CL=F, SI=F
    CRYPTO = "crypto"               # BTC-USD, ETH-USD
    FOREX = "forex"                 # USDINR=X


class NotificationChannel(str, Enum):
    """Channels for sending notifications."""
    DESKTOP = "desktop"             # Windows toast notification
    SOUND = "sound"                 # Audio alert
    EMAIL = "email"                 # Email notification (future)
    WEBHOOK = "webhook"             # External webhook call
    TELEGRAM = "telegram"           # Telegram bot (future)
    SMS = "sms"                     # SMS notification (future)


class EventType(str, Enum):
    """Types of events in the system."""
    # Price events
    PRICE_UPDATE = "price_update"
    PRICE_BATCH_UPDATE = "price_batch_update"
    
    # Alert events  
    ALERT_CREATED = "alert_created"
    ALERT_UPDATED = "alert_updated"
    ALERT_DELETED = "alert_deleted"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_EXPIRED = "alert_expired"
    
    # System events
    WORKER_STARTED = "worker_started"
    WORKER_STOPPED = "worker_stopped"
    WORKER_ERROR = "worker_error"
    
    # User events
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"


class Priority(str, Enum):
    """Alert priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
