"""Alert evaluator worker - evaluates alerts against price updates."""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict

from .base_worker import BaseWorker
from ..core.enums import AlertStatus, EventType, AssetType
from ..core.models import Alert, PriceData, AlertHistory
from ..core.evaluators import CompositeAlertEvaluator
from ..events.events import Event, PriceUpdateEvent, AlertTriggeredEvent
from ..events.event_bus import EventBus, get_event_bus
from ..infrastructure.redis_client import RedisClient, get_redis
from ..infrastructure.database import Database, get_database
from ..infrastructure.config import Config, get_config

from sqlalchemy import text

logger = logging.getLogger(__name__)


class AlertEvaluatorWorker(BaseWorker):
    """
    Evaluates alerts against price updates.
    
    Listens for PRICE_UPDATE events and checks if any alerts should trigger.
    Uses Redis cache for symbol->alerts mapping.
    Publishes ALERT_TRIGGERED events when conditions are met.
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        redis_client: Optional[RedisClient] = None,
        database: Optional[Database] = None,
        **kwargs
    ):
        super().__init__(name="AlertEvaluatorWorker", config=config, **kwargs)
        self.redis = redis_client or get_redis()
        self.db = database or get_database()
        
        self.evaluator = CompositeAlertEvaluator()
        
        # Cache of alerts by yahoo_symbol
        self._alerts_cache: Dict[str, List[Alert]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_refresh = datetime.min
        
        # Price update queue
        self._price_queue: asyncio.Queue = asyncio.Queue()
        
        # Stats
        self._alerts_evaluated = 0
        self._alerts_triggered = 0
    
    async def on_start(self):
        """Subscribe to price update events."""
        # Subscribe to price updates
        self.event_bus.subscribe(EventType.PRICE_UPDATE, self._on_price_update)
        
        # Also listen for alert changes to invalidate cache
        self.event_bus.subscribe(EventType.ALERT_CREATED, self._on_alert_change)
        self.event_bus.subscribe(EventType.ALERT_UPDATED, self._on_alert_change)
        self.event_bus.subscribe(EventType.ALERT_DELETED, self._on_alert_change)
        
        # Initial cache load
        await self._refresh_alerts_cache()
        
        logger.info("Alert evaluator subscribed to price updates")
    
    async def _on_price_update(self, event: Event):
        """Handle incoming price update event."""
        await self._price_queue.put(event)
    
    async def _on_alert_change(self, event: Event):
        """Handle alert change events - invalidate cache."""
        yahoo_symbol = event.payload.get('yahoo_symbol')
        if yahoo_symbol and yahoo_symbol in self._alerts_cache:
            del self._alerts_cache[yahoo_symbol]
            logger.debug(f"Invalidated cache for {yahoo_symbol}")
    
    async def run(self):
        """Process price updates from queue."""
        try:
            # Get price update from queue with timeout
            event = await asyncio.wait_for(
                self._price_queue.get(),
                timeout=1.0
            )
            
            # Process the price update
            await self._process_price_update(event)
            
        except asyncio.TimeoutError:
            # No updates in queue, do maintenance
            await self._maybe_refresh_cache()
    
    async def _process_price_update(self, event: Event):
        """Evaluate alerts for a price update."""
        yahoo_symbol = event.payload.get('yahoo_symbol')
        if not yahoo_symbol:
            return
        
        # Get alerts for this symbol
        alerts = await self._get_alerts_for_symbol(yahoo_symbol)
        if not alerts:
            return
        
        # Build PriceData from event
        try:
            price_data = PriceData(
                symbol=event.payload['symbol'],
                yahoo_symbol=yahoo_symbol,
                asset_type=AssetType(event.payload['asset_type']),
                price=event.payload['price'],
                prev_close=event.payload['prev_close'],
                open_price=event.payload['open_price'],
                high=event.payload['high'],
                low=event.payload['low'],
                volume=event.payload['volume'],
                change=event.payload['change'],
                change_pct=event.payload['change_pct'],
                timestamp=datetime.fromisoformat(event.timestamp.isoformat()),
                rsi_14=event.payload.get('rsi_14'),
                sma_20=event.payload.get('sma_20'),
                sma_50=event.payload.get('sma_50'),
                high_52w=event.payload.get('high_52w'),
                low_52w=event.payload.get('low_52w'),
            )
        except Exception as e:
            logger.error(f"Error building PriceData: {e}")
            return
        
        # Evaluate each alert
        for alert in alerts:
            self._alerts_evaluated += 1
            
            # Skip if not active or can't trigger
            if alert.status != AlertStatus.ACTIVE:
                continue
            if not alert.should_trigger_again():
                continue
            if alert.is_expired():
                await self._expire_alert(alert)
                continue
            
            # Evaluate
            triggered, message = self.evaluator.evaluate(alert, price_data)
            
            if triggered and message:
                await self._trigger_alert(alert, price_data, message)
            
            # Update previous price for crossing conditions
            alert.previous_price = price_data.price
    
    async def _get_alerts_for_symbol(self, yahoo_symbol: str) -> List[Alert]:
        """Get alerts for a symbol from cache or DB."""
        # Check cache
        if yahoo_symbol in self._alerts_cache:
            return self._alerts_cache[yahoo_symbol]
        
        # Load from database
        alerts = await self._load_alerts_for_symbol(yahoo_symbol)
        
        # Cache the result
        self._alerts_cache[yahoo_symbol] = alerts
        
        return alerts
    
    async def _load_alerts_for_symbol(self, yahoo_symbol: str) -> List[Alert]:
        """Load alerts from database."""
        try:
            engine = self.db.get_sync_engine()
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM price_alerts 
                    WHERE yahoo_symbol = :symbol 
                    AND status = 'active'
                """), {'symbol': yahoo_symbol})
                
                alerts = []
                for row in result:
                    try:
                        alert = self._row_to_alert(row._mapping)
                        alerts.append(alert)
                    except Exception as e:
                        logger.error(f"Error parsing alert: {e}")
                
                return alerts
                
        except Exception as e:
            logger.error(f"Error loading alerts for {yahoo_symbol}: {e}")
            return []
    
    def _row_to_alert(self, row: dict) -> Alert:
        """Convert database row to Alert object."""
        import json
        
        notification_channels = row.get('notification_channels')
        if isinstance(notification_channels, str):
            notification_channels = json.loads(notification_channels)
        
        from ..core.enums import NotificationChannel, AlertCondition
        
        return Alert(
            id=row['id'],
            user_id=row['user_id'],
            symbol=row['symbol'],
            yahoo_symbol=row['yahoo_symbol'],
            asset_type=AssetType(row['asset_type']),
            alert_type=row['alert_type'],
            condition=AlertCondition(row['condition']),
            target_value=float(row['target_value']),
            target_value_2=float(row['target_value_2']) if row.get('target_value_2') else None,
            status=AlertStatus(row['status']),
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
    
    async def _trigger_alert(self, alert: Alert, price_data: PriceData, message: str):
        """Handle alert trigger."""
        self._alerts_triggered += 1
        logger.info(f"ALERT TRIGGERED: {message}")
        
        # Update alert in database
        await self._update_alert_triggered(alert, price_data.price)
        
        # Record in history
        await self._record_alert_history(alert, price_data)
        
        # Publish triggered event
        event = AlertTriggeredEvent(
            alert_id=alert.id,
            user_id=alert.user_id,
            symbol=alert.symbol,
            condition=alert.condition,
            target_value=alert.target_value,
            actual_value=price_data.price,
            message=message,
            notification_channels=alert.notification_channels,
            webhook_url=alert.webhook_url,
            priority=alert.priority.value,
        )
        
        await self.event_bus.publish_async(event)
    
    async def _update_alert_triggered(self, alert: Alert, price: float):
        """Update alert status after trigger."""
        try:
            engine = self.db.get_sync_engine()
            
            new_status = 'triggered' if alert.trigger_once else 'active'
            
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE price_alerts 
                    SET status = :status,
                        last_triggered_at = NOW(),
                        trigger_count = trigger_count + 1,
                        previous_price = :price
                    WHERE id = :id
                """), {
                    'status': new_status,
                    'price': price,
                    'id': alert.id,
                })
            
            # Update local cache
            alert.status = AlertStatus(new_status)
            alert.last_triggered_at = datetime.now()
            alert.trigger_count += 1
            alert.previous_price = price
            
        except Exception as e:
            logger.error(f"Error updating alert {alert.id}: {e}")
    
    async def _record_alert_history(self, alert: Alert, price_data: PriceData):
        """Record triggered alert in history."""
        try:
            import uuid
            engine = self.db.get_sync_engine()
            
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO alert_history 
                    (id, alert_id, user_id, symbol, `condition`, target_value, actual_value, triggered_at)
                    VALUES (:id, :alert_id, :user_id, :symbol, :condition, :target, :actual, NOW())
                """), {
                    'id': str(uuid.uuid4()),
                    'alert_id': alert.id,
                    'user_id': alert.user_id,
                    'symbol': alert.symbol,
                    'condition': alert.condition.value,
                    'target': alert.target_value,
                    'actual': price_data.price,
                })
                
        except Exception as e:
            logger.error(f"Error recording alert history: {e}")
    
    async def _expire_alert(self, alert: Alert):
        """Mark alert as expired."""
        try:
            engine = self.db.get_sync_engine()
            
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE price_alerts SET status = 'expired' WHERE id = :id
                """), {'id': alert.id})
            
            # Invalidate cache
            if alert.yahoo_symbol in self._alerts_cache:
                del self._alerts_cache[alert.yahoo_symbol]
            
            logger.info(f"Alert {alert.id} expired")
            
        except Exception as e:
            logger.error(f"Error expiring alert: {e}")
    
    async def _maybe_refresh_cache(self):
        """Refresh cache if needed."""
        elapsed = (datetime.now() - self._last_cache_refresh).total_seconds()
        if elapsed > self._cache_ttl:
            await self._refresh_alerts_cache()
    
    async def _refresh_alerts_cache(self):
        """Refresh the entire alerts cache."""
        self._alerts_cache.clear()
        self._last_cache_refresh = datetime.now()
        logger.debug("Cleared alerts cache")
    
    async def on_stop(self):
        """Cleanup on stop."""
        logger.info(
            f"Alert evaluator stats: "
            f"{self._alerts_evaluated} evaluated, "
            f"{self._alerts_triggered} triggered"
        )
