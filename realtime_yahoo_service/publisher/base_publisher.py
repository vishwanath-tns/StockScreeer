"""
Base Publisher Interface
========================

Abstract base class for event publishers with rate limiting and health checks.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class IPublisher(ABC):
    """Abstract interface for event publishers"""
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start the publisher
        
        Raises:
            PublisherError: If start fails
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the publisher gracefully
        """
        pass
    
    @abstractmethod
    async def publish_event(self, event: Any) -> None:
        """
        Publish a single event
        
        Args:
            event: Event to publish
            
        Raises:
            PublisherError: If publish fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check
        
        Returns:
            Dictionary with health status
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get publisher statistics
        
        Returns:
            Dictionary with statistics
        """
        pass


class RateLimiter:
    """
    Token bucket rate limiter for API calls
    
    Uses token bucket algorithm for smooth rate limiting.
    """
    
    def __init__(self, rate: int, per_seconds: float = 60.0):
        """
        Initialize rate limiter
        
        Args:
            rate: Number of requests allowed
            per_seconds: Time period in seconds (default: 60s = 1 minute)
        """
        self.rate = rate
        self.per_seconds = per_seconds
        self.tokens = float(rate)
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        
        # Calculate token refill rate per second
        self.refill_rate = rate / per_seconds
    
    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens (blocks if not available)
        
        Args:
            tokens: Number of tokens to acquire
        """
        async with self.lock:
            while True:
                # Refill tokens based on time elapsed
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(
                    self.rate,
                    self.tokens + elapsed * self.refill_rate
                )
                self.last_update = now
                
                # Check if enough tokens available
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate
                
                # Release lock and wait
                await asyncio.sleep(wait_time)
    
    def get_available_tokens(self) -> float:
        """Get current number of available tokens"""
        now = time.time()
        elapsed = now - self.last_update
        return min(
            self.rate,
            self.tokens + elapsed * self.refill_rate
        )


class BasePublisher(IPublisher):
    """
    Base publisher implementation with common functionality
    
    Features:
    - Rate limiting with token bucket
    - Health checks with status tracking
    - Statistics tracking
    - Graceful shutdown
    - Error handling
    """
    
    def __init__(
        self,
        publisher_id: str,
        broker,  # IEventBroker
        serializer,  # IMessageSerializer
        rate_limit: int = 20,
        rate_limit_period: float = 60.0,
        publish_interval: float = 5.0,
    ):
        """
        Initialize base publisher
        
        Args:
            publisher_id: Unique publisher identifier
            broker: Event broker instance
            serializer: Message serializer
            rate_limit: Maximum requests per period
            rate_limit_period: Rate limit period in seconds
            publish_interval: Interval between publish cycles (seconds)
        """
        self.publisher_id = publisher_id
        self.broker = broker
        self.serializer = serializer
        self.publish_interval = publish_interval
        
        # Rate limiter
        self.rate_limiter = RateLimiter(rate_limit, rate_limit_period)
        
        # State tracking
        self._running = False
        self._shutdown = False
        self._publish_task: Optional[asyncio.Task] = None
        self._start_time: Optional[float] = None
        
        # Statistics
        self._stats = {
            'total_published': 0,
            'total_errors': 0,
            'last_publish_time': None,
            'last_error': None,
            'last_error_time': None,
        }
        
        # Health status
        self._health_status = {
            'status': 'stopped',  # stopped, starting, healthy, degraded, unhealthy
            'last_check': None,
            'error_count': 0,
        }
        
        logger.info(
            f"BasePublisher initialized: id={publisher_id}, "
            f"rate_limit={rate_limit}/{rate_limit_period}s"
        )
    
    async def start(self) -> None:
        """Start the publisher"""
        if self._running:
            logger.warning(f"Publisher {self.publisher_id} already running")
            return
        
        logger.info(f"Starting publisher: {self.publisher_id}")
        
        try:
            self._health_status['status'] = 'starting'
            
            # Start publish loop
            self._running = True
            self._shutdown = False
            self._start_time = time.time()
            self._publish_task = asyncio.create_task(self._publish_loop())
            
            self._health_status['status'] = 'healthy'
            logger.info(f"Publisher started: {self.publisher_id}")
        
        except Exception as e:
            self._health_status['status'] = 'unhealthy'
            logger.error(f"Failed to start publisher {self.publisher_id}: {e}")
            raise PublisherError(f"Start failed: {e}") from e
    
    async def stop(self) -> None:
        """Stop the publisher gracefully"""
        if not self._running:
            return
        
        logger.info(f"Stopping publisher: {self.publisher_id}")
        self._shutdown = True
        self._running = False
        
        # Cancel publish task
        if self._publish_task:
            self._publish_task.cancel()
            try:
                await self._publish_task
            except asyncio.CancelledError:
                pass
        
        self._health_status['status'] = 'stopped'
        logger.info(f"Publisher stopped: {self.publisher_id}")
    
    async def publish_event(self, event: Any) -> None:
        """
        Publish a single event
        
        Args:
            event: Event to publish
        """
        if not self._running:
            raise PublisherError("Publisher not running")
        
        try:
            # Rate limiting
            await self.rate_limiter.acquire()
            
            # Serialize event
            if hasattr(event, 'model_dump'):
                # Pydantic model
                data = self.serializer.serialize(event.model_dump())
            else:
                data = self.serializer.serialize(event)
            
            # Determine channel from event type
            channel = self._get_channel_for_event(event)
            
            # Publish to broker
            await self.broker.publish(channel, data)
            
            # Update statistics
            self._stats['total_published'] += 1
            self._stats['last_publish_time'] = time.time()
            
            logger.debug(
                f"Published event to {channel}: "
                f"{len(data)} bytes, type={type(event).__name__}"
            )
        
        except Exception as e:
            self._stats['total_errors'] += 1
            self._stats['last_error'] = str(e)
            self._stats['last_error_time'] = time.time()
            self._health_status['error_count'] += 1
            
            # Update health status
            if self._health_status['error_count'] > 10:
                self._health_status['status'] = 'unhealthy'
            elif self._health_status['error_count'] > 3:
                self._health_status['status'] = 'degraded'
            
            logger.error(f"Failed to publish event: {e}")
            raise PublisherError(f"Publish failed: {e}") from e
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        uptime = time.time() - self._start_time if self._start_time else 0
        
        health = {
            'publisher_id': self.publisher_id,
            'status': self._health_status['status'],
            'running': self._running,
            'uptime_seconds': round(uptime, 2),
            'error_count': self._health_status['error_count'],
            'last_publish_time': self._stats['last_publish_time'],
            'total_published': self._stats['total_published'],
            'total_errors': self._stats['total_errors'],
            'rate_limit_tokens': round(self.rate_limiter.get_available_tokens(), 2),
        }
        
        self._health_status['last_check'] = time.time()
        
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics"""
        uptime = time.time() - self._start_time if self._start_time else 0
        
        return {
            'publisher_id': self.publisher_id,
            'running': self._running,
            'status': self._health_status['status'],
            'uptime_seconds': round(uptime, 2),
            'total_published': self._stats['total_published'],
            'total_errors': self._stats['total_errors'],
            'success_rate': self._calculate_success_rate(),
            'last_publish_time': self._stats['last_publish_time'],
            'last_error': self._stats['last_error'],
            'last_error_time': self._stats['last_error_time'],
            'rate_limit_tokens': round(self.rate_limiter.get_available_tokens(), 2),
        }
    
    # ========================================================================
    # Protected Methods (Override in subclasses)
    # ========================================================================
    
    async def _publish_loop(self) -> None:
        """
        Main publish loop (override in subclass)
        
        This is the main loop that runs continuously and calls
        the fetch and publish logic.
        """
        logger.info(f"Publish loop started: {self.publisher_id}")
        
        try:
            while not self._shutdown:
                try:
                    # Call subclass implementation
                    await self._fetch_and_publish()
                    
                    # Reset error count on success
                    if self._health_status['error_count'] > 0:
                        self._health_status['error_count'] = max(
                            0, self._health_status['error_count'] - 1
                        )
                    
                    # Update health status
                    if self._health_status['status'] != 'healthy':
                        self._health_status['status'] = 'healthy'
                
                except Exception as e:
                    logger.error(f"Error in publish loop: {e}")
                    self._stats['total_errors'] += 1
                    self._health_status['error_count'] += 1
                
                # Wait before next cycle
                await asyncio.sleep(self.publish_interval)
        
        except asyncio.CancelledError:
            logger.info(f"Publish loop cancelled: {self.publisher_id}")
        except Exception as e:
            logger.error(f"Publish loop crashed: {e}")
            self._health_status['status'] = 'unhealthy'
    
    async def _fetch_and_publish(self) -> None:
        """
        Fetch data and publish events (override in subclass)
        
        Subclasses should implement this method to:
        1. Fetch data from source (API, database, etc.)
        2. Transform to event models
        3. Call publish_event() for each event
        """
        raise NotImplementedError("Subclass must implement _fetch_and_publish()")
    
    def _get_channel_for_event(self, event: Any) -> str:
        """
        Determine channel name from event type (override in subclass)
        
        Args:
            event: Event object
        
        Returns:
            Channel name
        """
        # Default: use event class name
        event_type = type(event).__name__.lower()
        return event_type.replace('event', '').replace('_', '.')
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self._stats['total_published'] + self._stats['total_errors']
        if total == 0:
            return 100.0
        return round((self._stats['total_published'] / total) * 100, 2)


class PublisherError(Exception):
    """Base exception for publisher errors"""
    pass
