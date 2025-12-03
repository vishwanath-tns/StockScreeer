"""Alert service - CRUD operations for alerts."""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import text

from ..core.enums import AlertStatus, AssetType, AlertType, AlertCondition, NotificationChannel, Priority
from ..core.models import Alert
from ..events.events import AlertCreatedEvent, AlertUpdatedEvent, AlertDeletedEvent
from ..events.event_bus import EventBus, get_event_bus
from ..infrastructure.database import Database, get_database
from ..infrastructure.redis_client import RedisClient, get_redis
from ..workers.price_monitor import get_yahoo_symbol

logger = logging.getLogger(__name__)


class AlertService:
    """Service for alert CRUD operations."""
    
    def __init__(
        self,
        database: Optional[Database] = None,
        redis: Optional[RedisClient] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.db = database or get_database()
        self.redis = redis or get_redis()
        self.event_bus = event_bus or get_event_bus()
    
    def create_alert(
        self,
        user_id: int,
        symbol: str,
        asset_type: AssetType,
        alert_type: AlertType,
        condition: AlertCondition,
        target_value: float,
        target_value_2: Optional[float] = None,
        priority: Priority = Priority.NORMAL,
        notification_channels: Optional[List[NotificationChannel]] = None,
        webhook_url: Optional[str] = None,
        trigger_once: bool = True,
        cooldown_minutes: int = 60,
        expires_at: Optional[datetime] = None,
        notes: Optional[str] = None,
        source: str = "manual",
        source_id: Optional[str] = None,
    ) -> Alert:
        """Create a new alert."""
        
        # Generate Yahoo symbol
        yahoo_symbol = get_yahoo_symbol(symbol, asset_type)
        
        # Default notification channels
        if notification_channels is None:
            notification_channels = [NotificationChannel.DESKTOP]
        
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            id=alert_id,
            user_id=user_id,
            symbol=symbol.upper(),
            yahoo_symbol=yahoo_symbol,
            asset_type=asset_type,
            alert_type=alert_type,
            condition=condition,
            target_value=target_value,
            target_value_2=target_value_2,
            status=AlertStatus.ACTIVE,
            priority=priority,
            notification_channels=notification_channels,
            webhook_url=webhook_url,
            trigger_once=trigger_once,
            cooldown_minutes=cooldown_minutes,
            expires_at=expires_at,
            source=source,
            source_id=source_id,
            notes=notes,
        )
        
        # Save to database
        self._save_alert(alert)
        
        # Add to monitoring
        self.redis.add_monitored_symbol(yahoo_symbol, asset_type.value)
        
        # Invalidate cache
        self.redis.invalidate_symbol_alerts(yahoo_symbol)
        
        # Publish event
        event = AlertCreatedEvent(
            alert_id=alert.id,
            user_id=user_id,
            symbol=symbol,
            yahoo_symbol=yahoo_symbol,
            asset_type=asset_type,
            condition=condition,
            target_value=target_value,
            source=source,
        )
        self.event_bus.publish(event)
        
        logger.info(f"Created alert {alert_id} for {symbol} ({condition.value})")
        return alert
    
    def _save_alert(self, alert: Alert):
        """Save alert to database."""
        import json
        
        engine = self.db.get_sync_engine()
        
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO price_alerts (
                    id, user_id, symbol, yahoo_symbol, asset_type, alert_type,
                    `condition`, target_value, target_value_2, status, priority,
                    notification_channels, webhook_url, trigger_once, cooldown_minutes,
                    expires_at, source, source_id, notes, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :symbol, :yahoo_symbol, :asset_type, :alert_type,
                    :condition, :target_value, :target_value_2, :status, :priority,
                    :notification_channels, :webhook_url, :trigger_once, :cooldown_minutes,
                    :expires_at, :source, :source_id, :notes, NOW(), NOW()
                )
            """), {
                'id': alert.id,
                'user_id': alert.user_id,
                'symbol': alert.symbol,
                'yahoo_symbol': alert.yahoo_symbol,
                'asset_type': alert.asset_type.value,
                'alert_type': alert.alert_type.value,
                'condition': alert.condition.value,
                'target_value': alert.target_value,
                'target_value_2': alert.target_value_2,
                'status': alert.status.value,
                'priority': alert.priority.value,
                'notification_channels': json.dumps([nc.value for nc in alert.notification_channels]),
                'webhook_url': alert.webhook_url,
                'trigger_once': alert.trigger_once,
                'cooldown_minutes': alert.cooldown_minutes,
                'expires_at': alert.expires_at,
                'source': alert.source,
                'source_id': alert.source_id,
                'notes': alert.notes,
            })
    
    def get_alert(self, alert_id: str, user_id: Optional[int] = None) -> Optional[Alert]:
        """Get alert by ID."""
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            if user_id:
                result = conn.execute(text("""
                    SELECT * FROM price_alerts WHERE id = :id AND user_id = :user_id
                """), {'id': alert_id, 'user_id': user_id})
            else:
                result = conn.execute(text("""
                    SELECT * FROM price_alerts WHERE id = :id
                """), {'id': alert_id})
            
            row = result.fetchone()
            if row:
                return self._row_to_alert(row._mapping)
        
        return None
    
    def get_user_alerts(
        self,
        user_id: int,
        status: Optional[AlertStatus] = None,
        asset_type: Optional[AssetType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Alert]:
        """Get alerts for a user."""
        engine = self.db.get_sync_engine()
        
        query = "SELECT * FROM price_alerts WHERE user_id = :user_id"
        params = {'user_id': user_id}
        
        if status:
            query += " AND status = :status"
            params['status'] = status.value
        
        if asset_type:
            query += " AND asset_type = :asset_type"
            params['asset_type'] = asset_type.value
        
        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [self._row_to_alert(row._mapping) for row in result]
    
    def update_alert(
        self,
        alert_id: str,
        user_id: int,
        **updates
    ) -> Optional[Alert]:
        """Update an alert."""
        # Get existing alert
        alert = self.get_alert(alert_id, user_id)
        if not alert:
            return None
        
        # Build update query
        allowed_fields = {
            'target_value', 'target_value_2', 'status', 'priority',
            'notification_channels', 'webhook_url', 'trigger_once',
            'cooldown_minutes', 'expires_at', 'notes', 'trigger_count',
            'last_triggered_at'
        }
        
        set_clauses = []
        params = {'id': alert_id, 'user_id': user_id}
        
        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            
            if field == 'status':
                value = value.value if isinstance(value, AlertStatus) else value
            elif field == 'priority':
                value = value.value if isinstance(value, Priority) else value
            elif field == 'notification_channels':
                import json
                value = json.dumps([nc.value if isinstance(nc, NotificationChannel) else nc for nc in value])
            
            set_clauses.append(f"`{field}` = :{field}")
            params[field] = value
        
        if not set_clauses:
            return alert
        
        set_clauses.append("updated_at = NOW()")
        
        engine = self.db.get_sync_engine()
        
        with engine.begin() as conn:
            conn.execute(text(f"""
                UPDATE price_alerts 
                SET {', '.join(set_clauses)}
                WHERE id = :id AND user_id = :user_id
            """), params)
        
        # Invalidate cache
        self.redis.invalidate_symbol_alerts(alert.yahoo_symbol)
        
        # Publish event
        event = AlertUpdatedEvent(
            alert_id=alert_id,
            user_id=user_id,
            changes=updates,
        )
        self.event_bus.publish(event)
        
        return self.get_alert(alert_id, user_id)
    
    def delete_alert(self, alert_id: str, user_id: int) -> bool:
        """Delete an alert."""
        alert = self.get_alert(alert_id, user_id)
        if not alert:
            return False
        
        engine = self.db.get_sync_engine()
        
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM price_alerts WHERE id = :id AND user_id = :user_id
            """), {'id': alert_id, 'user_id': user_id})
        
        # Invalidate cache
        self.redis.invalidate_symbol_alerts(alert.yahoo_symbol)
        
        # Check if any other alerts exist for this symbol
        remaining = self._count_symbol_alerts(alert.yahoo_symbol)
        if remaining == 0:
            self.redis.remove_monitored_symbol(alert.yahoo_symbol, alert.asset_type.value)
        
        # Publish event
        event = AlertDeletedEvent(
            alert_id=alert_id,
            user_id=user_id,
            symbol=alert.symbol,
            yahoo_symbol=alert.yahoo_symbol,
        )
        self.event_bus.publish(event)
        
        logger.info(f"Deleted alert {alert_id}")
        return True
    
    def _count_symbol_alerts(self, yahoo_symbol: str) -> int:
        """Count active alerts for a symbol."""
        engine = self.db.get_sync_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM price_alerts 
                WHERE yahoo_symbol = :symbol AND status = 'active'
            """), {'symbol': yahoo_symbol})
            
            return result.scalar() or 0
    
    def pause_alert(self, alert_id: str, user_id: int) -> bool:
        """Pause an alert."""
        result = self.update_alert(alert_id, user_id, status=AlertStatus.PAUSED)
        return result is not None
    
    def resume_alert(self, alert_id: str, user_id: int) -> bool:
        """Resume a paused alert."""
        result = self.update_alert(alert_id, user_id, status=AlertStatus.ACTIVE)
        return result is not None
    
    def _row_to_alert(self, row: dict) -> Alert:
        """Convert database row to Alert object."""
        import json
        
        notification_channels = row.get('notification_channels')
        if isinstance(notification_channels, str):
            notification_channels = json.loads(notification_channels)
        
        return Alert(
            id=row['id'],
            user_id=row['user_id'],
            symbol=row['symbol'],
            yahoo_symbol=row['yahoo_symbol'],
            asset_type=AssetType(row['asset_type']),
            alert_type=AlertType(row['alert_type']),
            condition=AlertCondition(row['condition']),
            target_value=float(row['target_value']),
            target_value_2=float(row['target_value_2']) if row.get('target_value_2') else None,
            status=AlertStatus(row['status']),
            priority=Priority(row['priority']),
            notification_channels=[NotificationChannel(nc) for nc in (notification_channels or ['desktop'])],
            webhook_url=row.get('webhook_url'),
            trigger_once=bool(row.get('trigger_once', True)),
            cooldown_minutes=row.get('cooldown_minutes', 60),
            expires_at=row.get('expires_at'),
            source=row.get('source', 'manual'),
            source_id=row.get('source_id'),
            notes=row.get('notes'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_triggered_at=row.get('last_triggered_at'),
            trigger_count=row.get('trigger_count', 0),
            previous_price=float(row['previous_price']) if row.get('previous_price') else None,
        )
    
    def get_alert_history(
        self,
        user_id: int,
        alert_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get alert trigger history."""
        engine = self.db.get_sync_engine()
        
        query = "SELECT * FROM alert_history WHERE user_id = :user_id"
        params = {'user_id': user_id, 'limit': limit}
        
        if alert_id:
            query += " AND alert_id = :alert_id"
            params['alert_id'] = alert_id
        
        query += " ORDER BY triggered_at DESC LIMIT :limit"
        
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [dict(row._mapping) for row in result]
