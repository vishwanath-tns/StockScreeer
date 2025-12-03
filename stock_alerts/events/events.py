"""Event definitions for the pub/sub system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import json

from ..core.enums import EventType, AlertCondition, AssetType, NotificationChannel


@dataclass
class Event:
    """Base event class."""
    event_type: EventType
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            'event_type': self.event_type.value,
            'payload': self.payload,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        data['event_type'] = EventType(data['event_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'event_type': self.event_type.value,
            'payload': self.payload,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
        }


@dataclass
class PriceUpdateEvent(Event):
    """Event for price updates."""
    
    def __init__(
        self,
        symbol: str,
        yahoo_symbol: str,
        asset_type: AssetType,
        price: float,
        prev_close: float,
        change: float,
        change_pct: float,
        volume: int,
        high: float,
        low: float,
        open_price: float,
        timestamp: Optional[datetime] = None,
        **extra_data
    ):
        payload = {
            'symbol': symbol,
            'yahoo_symbol': yahoo_symbol,
            'asset_type': asset_type.value,
            'price': price,
            'prev_close': prev_close,
            'change': change,
            'change_pct': change_pct,
            'volume': volume,
            'high': high,
            'low': low,
            'open_price': open_price,
            **extra_data,
        }
        super().__init__(
            event_type=EventType.PRICE_UPDATE,
            payload=payload,
            timestamp=timestamp or datetime.now(),
            source="price_monitor",
        )
    
    @property
    def symbol(self) -> str:
        return self.payload['symbol']
    
    @property
    def yahoo_symbol(self) -> str:
        return self.payload['yahoo_symbol']
    
    @property
    def price(self) -> float:
        return self.payload['price']
    
    @property
    def change_pct(self) -> float:
        return self.payload['change_pct']


@dataclass
class PriceBatchUpdateEvent(Event):
    """Event for batch price updates."""
    
    def __init__(
        self,
        asset_type: AssetType,
        prices: List[Dict[str, Any]],
        timestamp: Optional[datetime] = None,
    ):
        payload = {
            'asset_type': asset_type.value,
            'prices': prices,
            'count': len(prices),
        }
        super().__init__(
            event_type=EventType.PRICE_BATCH_UPDATE,
            payload=payload,
            timestamp=timestamp or datetime.now(),
            source="price_monitor",
        )
    
    @property
    def prices(self) -> List[Dict[str, Any]]:
        return self.payload['prices']


@dataclass
class AlertTriggeredEvent(Event):
    """Event when an alert is triggered."""
    
    def __init__(
        self,
        alert_id: str,
        user_id: int,
        symbol: str,
        condition: AlertCondition,
        target_value: float,
        actual_value: float,
        message: str,
        notification_channels: List[NotificationChannel],
        webhook_url: Optional[str] = None,
        priority: str = "normal",
        timestamp: Optional[datetime] = None,
    ):
        payload = {
            'alert_id': alert_id,
            'user_id': user_id,
            'symbol': symbol,
            'condition': condition.value,
            'target_value': target_value,
            'actual_value': actual_value,
            'message': message,
            'notification_channels': [nc.value for nc in notification_channels],
            'webhook_url': webhook_url,
            'priority': priority,
        }
        super().__init__(
            event_type=EventType.ALERT_TRIGGERED,
            payload=payload,
            timestamp=timestamp or datetime.now(),
            source="alert_evaluator",
        )
    
    @property
    def alert_id(self) -> str:
        return self.payload['alert_id']
    
    @property
    def user_id(self) -> int:
        return self.payload['user_id']
    
    @property
    def message(self) -> str:
        return self.payload['message']
    
    @property
    def notification_channels(self) -> List[str]:
        return self.payload['notification_channels']


@dataclass
class AlertCreatedEvent(Event):
    """Event when a new alert is created."""
    
    def __init__(
        self,
        alert_id: str,
        user_id: int,
        symbol: str,
        yahoo_symbol: str,
        asset_type: AssetType,
        condition: AlertCondition,
        target_value: float,
        source: str = "manual",
        timestamp: Optional[datetime] = None,
    ):
        payload = {
            'alert_id': alert_id,
            'user_id': user_id,
            'symbol': symbol,
            'yahoo_symbol': yahoo_symbol,
            'asset_type': asset_type.value,
            'condition': condition.value,
            'target_value': target_value,
        }
        super().__init__(
            event_type=EventType.ALERT_CREATED,
            payload=payload,
            timestamp=timestamp or datetime.now(),
            source=source,
        )


@dataclass
class AlertUpdatedEvent(Event):
    """Event when an alert is updated."""
    
    def __init__(
        self,
        alert_id: str,
        user_id: int,
        changes: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ):
        payload = {
            'alert_id': alert_id,
            'user_id': user_id,
            'changes': changes,
        }
        super().__init__(
            event_type=EventType.ALERT_UPDATED,
            payload=payload,
            timestamp=timestamp or datetime.now(),
            source="api",
        )


@dataclass
class AlertDeletedEvent(Event):
    """Event when an alert is deleted."""
    
    def __init__(
        self,
        alert_id: str,
        user_id: int,
        symbol: str,
        yahoo_symbol: str,
        timestamp: Optional[datetime] = None,
    ):
        payload = {
            'alert_id': alert_id,
            'user_id': user_id,
            'symbol': symbol,
            'yahoo_symbol': yahoo_symbol,
        }
        super().__init__(
            event_type=EventType.ALERT_DELETED,
            payload=payload,
            timestamp=timestamp or datetime.now(),
            source="api",
        )


@dataclass
class SystemEvent(Event):
    """System status events."""
    
    def __init__(
        self,
        event_type: EventType,
        worker_name: str,
        status: str,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        payload = {
            'worker_name': worker_name,
            'status': status,
            'message': message,
            'details': details or {},
        }
        super().__init__(
            event_type=event_type,
            payload=payload,
            timestamp=timestamp or datetime.now(),
            source="system",
        )
    
    @classmethod
    def worker_started(cls, worker_name: str, details: Optional[Dict] = None):
        return cls(
            event_type=EventType.WORKER_STARTED,
            worker_name=worker_name,
            status="started",
            message=f"{worker_name} started",
            details=details,
        )
    
    @classmethod
    def worker_stopped(cls, worker_name: str, reason: str = ""):
        return cls(
            event_type=EventType.WORKER_STOPPED,
            worker_name=worker_name,
            status="stopped",
            message=f"{worker_name} stopped: {reason}",
        )
    
    @classmethod
    def worker_error(cls, worker_name: str, error: str, details: Optional[Dict] = None):
        return cls(
            event_type=EventType.WORKER_ERROR,
            worker_name=worker_name,
            status="error",
            message=error,
            details=details,
        )
