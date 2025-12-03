"""Redis client for caching and pub/sub messaging."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime, timedelta

# Sync Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Async Redis  
try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    try:
        # redis-py 4.x has async support built-in
        from redis import asyncio as aioredis
        AIOREDIS_AVAILABLE = True
    except ImportError:
        AIOREDIS_AVAILABLE = False

from .config import Config, get_config

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for caching and pub/sub."""
    
    # Key prefixes
    PREFIX_ALERTS = "alerts:"
    PREFIX_PRICES = "prices:"
    PREFIX_SYMBOLS = "symbols:"
    PREFIX_SESSIONS = "sessions:"
    PREFIX_CACHE = "cache:"
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._sync_client = None
        self._async_client = None
        self._pubsub = None
        self._subscriptions: Dict[str, List[Callable]] = {}
    
    # ==================== Sync Operations ====================
    
    def get_sync_client(self):
        """Get synchronous Redis client."""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available. Install redis package.")
        
        if self._sync_client is None:
            self._sync_client = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                db=self.config.redis.db,
                password=self.config.redis.password,
                decode_responses=True,
            )
        return self._sync_client
    
    def ping(self) -> bool:
        """Test Redis connection."""
        try:
            client = self.get_sync_client()
            return client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value with optional TTL (seconds)."""
        client = self.get_sync_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return client.set(key, value, ex=ttl)
    
    def get(self, key: str) -> Optional[str]:
        """Get a value."""
        client = self.get_sync_client()
        return client.get(key)
    
    def get_json(self, key: str) -> Optional[Any]:
        """Get and parse JSON value."""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    def delete(self, *keys: str) -> int:
        """Delete keys."""
        client = self.get_sync_client()
        return client.delete(*keys)
    
    def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        client = self.get_sync_client()
        return client.keys(pattern)
    
    def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel."""
        client = self.get_sync_client()
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        return client.publish(channel, message)
    
    # ==================== Async Operations ====================
    
    async def get_async_client(self):
        """Get async Redis client."""
        if not AIOREDIS_AVAILABLE:
            raise RuntimeError("Async Redis not available. Install aioredis or redis>=4.0.")
        
        if self._async_client is None:
            self._async_client = await aioredis.from_url(
                self.config.redis.url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._async_client
    
    async def async_ping(self) -> bool:
        """Test async Redis connection."""
        try:
            client = await self.get_async_client()
            return await client.ping()
        except Exception as e:
            logger.error(f"Async Redis ping failed: {e}")
            return False
    
    async def async_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Async set value."""
        client = await self.get_async_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await client.set(key, value, ex=ttl)
    
    async def async_get(self, key: str) -> Optional[str]:
        """Async get value."""
        client = await self.get_async_client()
        return await client.get(key)
    
    async def async_get_json(self, key: str) -> Optional[Any]:
        """Async get and parse JSON."""
        value = await self.async_get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def async_delete(self, *keys: str) -> int:
        """Async delete keys."""
        client = await self.get_async_client()
        return await client.delete(*keys)
    
    async def async_publish(self, channel: str, message: Any) -> int:
        """Async publish message."""
        client = await self.get_async_client()
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        return await client.publish(channel, message)
    
    async def async_subscribe(self, channel: str, callback: Callable[[str, Any], Awaitable[None]]):
        """Subscribe to channel with async callback."""
        client = await self.get_async_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(callback)
        
        # Start listener task
        asyncio.create_task(self._async_listener(pubsub, channel))
    
    async def _async_listener(self, pubsub, channel: str):
        """Listen for messages on channel."""
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data']
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                    
                    # Call all callbacks for this channel
                    for callback in self._subscriptions.get(channel, []):
                        try:
                            await callback(channel, data)
                        except Exception as e:
                            logger.error(f"Callback error on {channel}: {e}")
        except asyncio.CancelledError:
            await pubsub.unsubscribe(channel)
        except Exception as e:
            logger.error(f"Listener error on {channel}: {e}")
    
    # ==================== Alert-Specific Operations ====================
    
    def cache_price(self, yahoo_symbol: str, price_data: Dict[str, Any], ttl: int = 60):
        """Cache latest price data."""
        key = f"{self.PREFIX_PRICES}latest:{yahoo_symbol}"
        self.set(key, price_data, ttl=ttl)
    
    def get_cached_price(self, yahoo_symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached price data."""
        key = f"{self.PREFIX_PRICES}latest:{yahoo_symbol}"
        return self.get_json(key)
    
    def add_monitored_symbol(self, yahoo_symbol: str, asset_type: str):
        """Add symbol to monitored set."""
        key = f"{self.PREFIX_SYMBOLS}monitored:{asset_type}"
        client = self.get_sync_client()
        client.sadd(key, yahoo_symbol)
    
    def remove_monitored_symbol(self, yahoo_symbol: str, asset_type: str):
        """Remove symbol from monitored set."""
        key = f"{self.PREFIX_SYMBOLS}monitored:{asset_type}"
        client = self.get_sync_client()
        client.srem(key, yahoo_symbol)
    
    def get_monitored_symbols(self, asset_type: str) -> List[str]:
        """Get all monitored symbols for asset type."""
        key = f"{self.PREFIX_SYMBOLS}monitored:{asset_type}"
        client = self.get_sync_client()
        return list(client.smembers(key))
    
    def cache_symbol_alerts(self, yahoo_symbol: str, alert_ids: List[str], ttl: int = 300):
        """Cache alert IDs for a symbol."""
        key = f"{self.PREFIX_ALERTS}symbol:{yahoo_symbol}"
        self.set(key, alert_ids, ttl=ttl)
    
    def get_symbol_alerts(self, yahoo_symbol: str) -> List[str]:
        """Get cached alert IDs for symbol."""
        key = f"{self.PREFIX_ALERTS}symbol:{yahoo_symbol}"
        return self.get_json(key) or []
    
    def invalidate_symbol_alerts(self, yahoo_symbol: str):
        """Invalidate alert cache for symbol."""
        key = f"{self.PREFIX_ALERTS}symbol:{yahoo_symbol}"
        self.delete(key)
    
    # ==================== Cleanup ====================
    
    def close(self):
        """Close all connections."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
    
    async def async_close(self):
        """Close async connections."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None


# Module-level singleton
_redis: Optional[RedisClient] = None


def get_redis() -> RedisClient:
    """Get or create Redis client singleton."""
    global _redis
    if _redis is None:
        _redis = RedisClient()
    return _redis
