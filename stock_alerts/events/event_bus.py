"""Event bus for pub/sub messaging."""

import asyncio
import json
import logging
from typing import Dict, List, Callable, Any, Optional, Awaitable
from datetime import datetime
from collections import defaultdict

from ..core.enums import EventType
from ..infrastructure.redis_client import RedisClient, get_redis
from ..infrastructure.config import Config, get_config
from .events import Event

logger = logging.getLogger(__name__)


# Type for event handlers
EventHandler = Callable[[Event], Awaitable[None]]
SyncEventHandler = Callable[[Event], None]


class EventBus:
    """
    Event bus using Redis pub/sub for distributed messaging.
    
    Supports both sync and async handlers.
    """
    
    def __init__(self, config: Optional[Config] = None, redis_client: Optional[RedisClient] = None):
        self.config = config or get_config()
        self.redis = redis_client or get_redis()
        
        # Local handlers (in-process)
        self._async_handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._sync_handlers: Dict[EventType, List[SyncEventHandler]] = defaultdict(list)
        
        # Channel mappings
        self._channel_map = {
            EventType.PRICE_UPDATE: self.config.redis.price_channel,
            EventType.PRICE_BATCH_UPDATE: self.config.redis.price_channel,
            EventType.ALERT_TRIGGERED: self.config.redis.alert_channel,
            EventType.ALERT_CREATED: self.config.redis.alert_channel,
            EventType.ALERT_UPDATED: self.config.redis.alert_channel,
            EventType.ALERT_DELETED: self.config.redis.alert_channel,
            EventType.WORKER_STARTED: self.config.redis.system_channel,
            EventType.WORKER_STOPPED: self.config.redis.system_channel,
            EventType.WORKER_ERROR: self.config.redis.system_channel,
        }
        
        # Subscriber tasks
        self._subscriber_tasks: List[asyncio.Task] = []
        self._running = False
    
    # ==================== Handler Registration ====================
    
    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe async handler to event type."""
        self._async_handlers[event_type].append(handler)
        logger.debug(f"Subscribed async handler to {event_type.value}")
    
    def subscribe_sync(self, event_type: EventType, handler: SyncEventHandler):
        """Subscribe sync handler to event type."""
        self._sync_handlers[event_type].append(handler)
        logger.debug(f"Subscribed sync handler to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Unsubscribe handler from event type."""
        if handler in self._async_handlers[event_type]:
            self._async_handlers[event_type].remove(handler)
        if handler in self._sync_handlers[event_type]:
            self._sync_handlers[event_type].remove(handler)
    
    def subscribe_all(self, handler: EventHandler):
        """Subscribe handler to all event types."""
        for event_type in EventType:
            self.subscribe(event_type, handler)
    
    # ==================== Publishing ====================
    
    def publish(self, event: Event):
        """Publish event synchronously (local + Redis)."""
        # Dispatch to local handlers
        self._dispatch_local_sync(event)
        
        # Publish to Redis channel
        channel = self._channel_map.get(event.event_type, self.config.redis.system_channel)
        try:
            self.redis.publish(channel, event.to_json())
            logger.debug(f"Published {event.event_type.value} to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
    
    async def publish_async(self, event: Event):
        """Publish event asynchronously."""
        # Dispatch to local handlers
        await self._dispatch_local_async(event)
        
        # Publish to Redis channel
        channel = self._channel_map.get(event.event_type, self.config.redis.system_channel)
        try:
            await self.redis.async_publish(channel, event.to_json())
            logger.debug(f"Published {event.event_type.value} to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
    
    def publish_local(self, event: Event):
        """Publish event to local handlers only (no Redis)."""
        self._dispatch_local_sync(event)
    
    async def publish_local_async(self, event: Event):
        """Publish event to local async handlers only."""
        await self._dispatch_local_async(event)
    
    # ==================== Local Dispatch ====================
    
    def _dispatch_local_sync(self, event: Event):
        """Dispatch to local sync handlers."""
        handlers = self._sync_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Sync handler error for {event.event_type.value}: {e}")
    
    async def _dispatch_local_async(self, event: Event):
        """Dispatch to local async handlers."""
        handlers = self._async_handlers.get(event.event_type, [])
        if not handlers:
            return
        
        # Run all handlers concurrently
        tasks = [self._safe_call(handler, event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_call(self, handler: EventHandler, event: Event):
        """Safely call handler with error catching."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Async handler error for {event.event_type.value}: {e}")
    
    # ==================== Redis Subscription ====================
    
    async def start_listening(self):
        """Start listening to Redis channels."""
        if self._running:
            return
        
        self._running = True
        
        # Subscribe to all channels
        channels = set(self._channel_map.values())
        for channel in channels:
            task = asyncio.create_task(self._listen_channel(channel))
            self._subscriber_tasks.append(task)
        
        logger.info(f"Started listening to {len(channels)} Redis channels")
    
    async def _listen_channel(self, channel: str):
        """Listen to a single Redis channel."""
        try:
            client = await self.redis.get_async_client()
            pubsub = client.pubsub()
            await pubsub.subscribe(channel)
            
            logger.debug(f"Subscribed to Redis channel: {channel}")
            
            async for message in pubsub.listen():
                if not self._running:
                    break
                
                if message['type'] != 'message':
                    continue
                
                try:
                    event = Event.from_json(message['data'])
                    await self._dispatch_local_async(event)
                except Exception as e:
                    logger.error(f"Error processing message on {channel}: {e}")
            
            await pubsub.unsubscribe(channel)
            
        except asyncio.CancelledError:
            logger.debug(f"Channel listener cancelled: {channel}")
        except Exception as e:
            logger.error(f"Channel listener error on {channel}: {e}")
    
    async def stop_listening(self):
        """Stop listening to Redis channels."""
        self._running = False
        
        # Cancel all subscriber tasks
        for task in self._subscriber_tasks:
            task.cancel()
        
        if self._subscriber_tasks:
            await asyncio.gather(*self._subscriber_tasks, return_exceptions=True)
        
        self._subscriber_tasks.clear()
        logger.info("Stopped listening to Redis channels")
    
    # ==================== Convenience Methods ====================
    
    def on_price_update(self, handler: EventHandler):
        """Decorator for price update handlers."""
        self.subscribe(EventType.PRICE_UPDATE, handler)
        return handler
    
    def on_alert_triggered(self, handler: EventHandler):
        """Decorator for alert triggered handlers."""
        self.subscribe(EventType.ALERT_TRIGGERED, handler)
        return handler
    
    def on_system_event(self, handler: EventHandler):
        """Subscribe to all system events."""
        for event_type in [EventType.WORKER_STARTED, EventType.WORKER_STOPPED, EventType.WORKER_ERROR]:
            self.subscribe(event_type, handler)
        return handler


# Module-level singleton
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create event bus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus():
    """Reset event bus (for testing)."""
    global _event_bus
    _event_bus = None
