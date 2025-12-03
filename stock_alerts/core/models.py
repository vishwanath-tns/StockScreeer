"""Domain models for the Stock Alert System."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
import uuid

from .enums import AlertType, AlertCondition, AlertStatus, AssetType, NotificationChannel, Priority


@dataclass
class PriceData:
    """Real-time price data for a symbol."""
    symbol: str
    yahoo_symbol: str
    asset_type: AssetType
    price: float
    prev_close: float
    open_price: float
    high: float
    low: float
    volume: int
    change: float
    change_pct: float
    timestamp: datetime
    
    # Optional technical data (computed by worker)
    rsi_14: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    avg_volume_20d: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'symbol': self.symbol,
            'yahoo_symbol': self.yahoo_symbol,
            'asset_type': self.asset_type.value,
            'price': self.price,
            'prev_close': self.prev_close,
            'open_price': self.open_price,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'change': self.change,
            'change_pct': self.change_pct,
            'timestamp': self.timestamp.isoformat(),
            'rsi_14': self.rsi_14,
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'sma_200': self.sma_200,
            'macd': self.macd,
            'macd_signal': self.macd_signal,
            'bb_upper': self.bb_upper,
            'bb_lower': self.bb_lower,
            'high_52w': self.high_52w,
            'low_52w': self.low_52w,
            'avg_volume_20d': self.avg_volume_20d,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceData':
        """Create from dictionary."""
        data = data.copy()
        data['asset_type'] = AssetType(data['asset_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class Alert:
    """Price alert configuration."""
    id: str
    user_id: int
    symbol: str
    yahoo_symbol: str
    asset_type: AssetType
    alert_type: AlertType
    condition: AlertCondition
    
    # Condition parameters
    target_value: float
    target_value_2: Optional[float] = None  # For BETWEEN conditions
    
    # Configuration
    status: AlertStatus = AlertStatus.ACTIVE
    priority: Priority = Priority.NORMAL
    notification_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.DESKTOP])
    webhook_url: Optional[str] = None
    
    # Trigger settings
    trigger_once: bool = True  # If False, can trigger multiple times
    cooldown_minutes: int = 60  # Minimum time between repeated triggers
    expires_at: Optional[datetime] = None
    
    # Metadata
    source: str = "manual"  # manual, api, scanner
    source_id: Optional[str] = None  # Reference to external scanner/API
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    
    # Previous state for crossing conditions
    previous_price: Optional[float] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'symbol': self.symbol,
            'yahoo_symbol': self.yahoo_symbol,
            'asset_type': self.asset_type.value,
            'alert_type': self.alert_type.value,
            'condition': self.condition.value,
            'target_value': self.target_value,
            'target_value_2': self.target_value_2,
            'status': self.status.value,
            'priority': self.priority.value,
            'notification_channels': [nc.value for nc in self.notification_channels],
            'webhook_url': self.webhook_url,
            'trigger_once': self.trigger_once,
            'cooldown_minutes': self.cooldown_minutes,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'source': self.source,
            'source_id': self.source_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_triggered_at': self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            'trigger_count': self.trigger_count,
            'previous_price': self.previous_price,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create from dictionary."""
        data = data.copy()
        data['asset_type'] = AssetType(data['asset_type'])
        data['alert_type'] = AlertType(data['alert_type'])
        data['condition'] = AlertCondition(data['condition'])
        data['status'] = AlertStatus(data['status'])
        data['priority'] = Priority(data['priority'])
        data['notification_channels'] = [NotificationChannel(nc) for nc in data['notification_channels']]
        
        # Parse datetime fields
        for dt_field in ['expires_at', 'created_at', 'updated_at', 'last_triggered_at']:
            if data.get(dt_field):
                data[dt_field] = datetime.fromisoformat(data[dt_field])
        
        return cls(**data)
    
    def should_trigger_again(self) -> bool:
        """Check if alert can trigger again based on cooldown."""
        if self.trigger_once and self.trigger_count > 0:
            return False
        
        if self.last_triggered_at:
            from datetime import timedelta
            cooldown = timedelta(minutes=self.cooldown_minutes)
            if datetime.now() - self.last_triggered_at < cooldown:
                return False
        
        return True
    
    def is_expired(self) -> bool:
        """Check if alert has expired."""
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        return False


@dataclass
class User:
    """User account for the alert system."""
    id: int
    username: str
    email: str
    password_hash: str
    
    # Limits
    max_alerts: int = 50
    max_api_keys: int = 5
    
    # Settings
    is_active: bool = True
    is_admin: bool = False
    notification_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None


@dataclass
class ApiKey:
    """API key for external integrations."""
    id: str
    user_id: int
    name: str
    key_hash: str
    prefix: str  # First 8 chars for identification
    
    # Permissions
    permissions: List[str] = field(default_factory=lambda: ['alerts:read', 'alerts:write'])
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    # Status
    is_active: bool = True
    expires_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None


@dataclass
class AlertHistory:
    """Historical record of triggered alerts."""
    id: str
    alert_id: str
    user_id: int
    symbol: str
    condition: AlertCondition
    
    # Values at trigger time
    target_value: float
    actual_value: float
    
    # Notification results
    notifications_sent: List[str] = field(default_factory=list)
    notification_results: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamp
    triggered_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class WatchlistItem:
    """Item in a user's watchlist."""
    id: str
    user_id: int
    watchlist_name: str
    symbol: str
    yahoo_symbol: str
    asset_type: AssetType
    sort_order: int = 0
    notes: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class Event:
    """Event for the event bus."""
    type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "system"
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        import json
        return json.dumps({
            'type': self.type,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'event_id': self.event_id,
            'source': self.source,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Deserialize from JSON string."""
        import json
        data = json.loads(json_str)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
