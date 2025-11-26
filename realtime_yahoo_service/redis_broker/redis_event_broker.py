"""
Redis Event Broker Implementation
==================================

Production-ready Redis Pub/Sub broker with connection pooling and reconnection.
"""

import asyncio
import logging
import time
from typing import Callable, Optional, Any, Dict
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    from redis.asyncio.connection import ConnectionPool
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
except ImportError:
    redis = None
    ConnectionPool = None
    RedisError = Exception
    RedisConnectionError = Exception

from .base_broker import (
    IEventBroker,
    BrokerError,
    PublishError,
    SubscriptionError,
    ConnectionError,
)

# Import serializer - handle both package and standalone imports
try:
    from serialization.base_serializer import IMessageSerializer
except ImportError:
    from ..serialization.base_serializer import IMessageSerializer

logger = logging.getLogger(__name__)


class RedisEventBroker(IEventBroker):
    """
    Redis-based event broker with connection pooling and automatic reconnection
    
    Features:
    - Connection pooling for publish operations
    - Dedicated pubsub connection for subscriptions
    - Automatic reconnection with exponential backoff
    - Health checks with latency monitoring
    - Graceful shutdown
    """
    
    def __init__(
        self,
        redis_url: str,
        serializer: IMessageSerializer,
        max_connections: int = 50,
        max_reconnect_attempts: int = 10,
        reconnect_base_delay: float = 1.0,
        health_check_interval: float = 30.0,
    ):
        """
        Initialize Redis event broker
        
        Args:
            redis_url: Redis connection URL (redis://host:port/db)
            serializer: Message serializer instance
            max_connections: Maximum connections in pool
            max_reconnect_attempts: Max reconnection attempts before giving up
            reconnect_base_delay: Base delay for exponential backoff (seconds)
            health_check_interval: Interval between health checks (seconds)
        """
        if redis is None:
            raise ImportError("redis package not installed. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.serializer = serializer
        self.max_connections = max_connections
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay
        self.health_check_interval = health_check_interval
        
        # Connection components
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        
        # Subscription tracking
        self._subscriptions: Dict[str, Callable[[str, bytes], None]] = {}
        self._subscription_task: Optional[asyncio.Task] = None
        
        # Connection state
        self._connected = False
        self._reconnecting = False
        self._shutdown = False
        
        # Health monitoring
        self._last_health_check: Optional[dict] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        logger.info(f"RedisEventBroker initialized: {redis_url} (max_conn={max_connections})")
    
    async def connect(self) -> None:
        """Establish connection to Redis"""
        try:
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=False,  # We handle binary data
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            
            # Create pubsub connection
            self._pubsub = self._client.pubsub()
            
            self._connected = True
            logger.info("Connected to Redis successfully")
            
            # Start health check background task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Redis connection failed: {e}") from e
    
    async def disconnect(self) -> None:
        """Close connection to Redis"""
        self._shutdown = True
        logger.info("Shutting down Redis broker...")
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Cancel subscription task
        if self._subscription_task:
            self._subscription_task.cancel()
            try:
                await self._subscription_task
            except asyncio.CancelledError:
                pass
        
        # Close pubsub
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
            except Exception as e:
                logger.warning(f"Error closing pubsub: {e}")
        
        # Close client
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"Error closing client: {e}")
        
        # Close pool
        if self._pool:
            try:
                await self._pool.disconnect()
            except Exception as e:
                logger.warning(f"Error closing pool: {e}")
        
        self._connected = False
        logger.info("Redis broker shutdown complete")
    
    async def publish(self, channel: str, message: bytes) -> None:
        """
        Publish a message to a Redis channel
        
        Args:
            channel: Channel name
            message: Serialized message bytes
        """
        if not self._connected or not self._client:
            raise PublishError("Not connected to Redis")
        
        try:
            await self._client.publish(channel, message)
            logger.debug(f"Published message to channel: {channel} ({len(message)} bytes)")
        except RedisError as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            raise PublishError(f"Publish failed: {e}") from e
    
    async def subscribe(
        self,
        channel: str,
        callback: Callable[[str, bytes], None],
    ) -> None:
        """
        Subscribe to a Redis channel
        
        Args:
            channel: Channel name to subscribe to
            callback: Function to call when message received
        """
        if not self._connected or not self._pubsub:
            raise SubscriptionError("Not connected to Redis")
        
        try:
            # Add to subscriptions dict
            self._subscriptions[channel] = callback
            
            # Subscribe to channel
            await self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")
            
            # Start subscription listener if not running
            if self._subscription_task is None or self._subscription_task.done():
                self._subscription_task = asyncio.create_task(self._subscription_listener())
            
        except RedisError as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            raise SubscriptionError(f"Subscription failed: {e}") from e
    
    async def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribe from a Redis channel
        
        Args:
            channel: Channel name to unsubscribe from
        """
        if channel in self._subscriptions:
            del self._subscriptions[channel]
        
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(channel)
                logger.info(f"Unsubscribed from channel: {channel}")
            except RedisError as e:
                logger.warning(f"Error unsubscribing from {channel}: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to Redis"""
        return self._connected and self._client is not None
    
    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on Redis connection
        
        Returns:
            Dictionary with health status
        """
        if not self._connected or not self._client:
            return {
                'healthy': False,
                'connected': False,
                'latency_ms': None,
                'error': 'Not connected',
            }
        
        try:
            start = time.perf_counter()
            await self._client.ping()
            latency = (time.perf_counter() - start) * 1000
            
            return {
                'healthy': True,
                'connected': True,
                'latency_ms': round(latency, 2),
                'error': None,
            }
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return {
                'healthy': False,
                'connected': False,
                'latency_ms': None,
                'error': str(e),
            }
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    async def _subscription_listener(self) -> None:
        """Background task to listen for pubsub messages"""
        logger.info("Subscription listener started")
        
        try:
            while not self._shutdown and self._pubsub:
                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                    
                    if message and message['type'] == 'message':
                        channel = message['channel'].decode('utf-8')
                        data = message['data']
                        
                        # Call registered callback
                        callback = self._subscriptions.get(channel)
                        if callback:
                            try:
                                # Call callback (can be sync or async)
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(channel, data)
                                else:
                                    callback(channel, data)
                            except Exception as e:
                                logger.error(f"Error in callback for {channel}: {e}")
                        else:
                            logger.warning(f"Received message for unregistered channel: {channel}")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in subscription listener: {e}")
                    await asyncio.sleep(1)
        
        finally:
            logger.info("Subscription listener stopped")
    
    async def _health_check_loop(self) -> None:
        """Background task to periodically check connection health"""
        logger.info("Health check loop started")
        
        try:
            while not self._shutdown:
                self._last_health_check = await self.health_check()
                
                if not self._last_health_check['healthy']:
                    logger.warning("Health check failed, attempting reconnection...")
                    asyncio.create_task(self._reconnect())
                
                await asyncio.sleep(self.health_check_interval)
        
        except asyncio.CancelledError:
            logger.info("Health check loop cancelled")
        except Exception as e:
            logger.error(f"Error in health check loop: {e}")
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff"""
        if self._reconnecting:
            return  # Already reconnecting
        
        self._reconnecting = True
        attempt = 0
        
        while attempt < self.max_reconnect_attempts and not self._shutdown:
            attempt += 1
            delay = self.reconnect_base_delay * (2 ** (attempt - 1))
            
            logger.info(f"Reconnection attempt {attempt}/{self.max_reconnect_attempts} (delay={delay}s)")
            
            try:
                # Close existing connections
                if self._client:
                    await self._client.close()
                
                # Reconnect
                await self.connect()
                
                # Resubscribe to channels
                if self._subscriptions:
                    logger.info(f"Resubscribing to {len(self._subscriptions)} channels...")
                    for channel in list(self._subscriptions.keys()):
                        await self._pubsub.subscribe(channel)
                
                logger.info("Reconnection successful")
                self._reconnecting = False
                return
            
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt} failed: {e}")
                await asyncio.sleep(delay)
        
        logger.critical(f"Failed to reconnect after {attempt} attempts")
        self._reconnecting = False
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get broker statistics
        
        Returns:
            Dictionary with broker stats
        """
        return {
            'connected': self._connected,
            'reconnecting': self._reconnecting,
            'active_subscriptions': len(self._subscriptions),
            'channels': list(self._subscriptions.keys()),
            'last_health_check': self._last_health_check,
            'serializer': self.serializer.get_format_name(),
        }


# Convenience function to create Redis broker
def create_redis_broker(
    redis_url: str,
    serializer: IMessageSerializer,
    **kwargs
) -> RedisEventBroker:
    """
    Create a Redis event broker instance
    
    Args:
        redis_url: Redis connection URL
        serializer: Message serializer
        **kwargs: Additional broker configuration
    
    Returns:
        RedisEventBroker instance
    """
    return RedisEventBroker(redis_url, serializer, **kwargs)
