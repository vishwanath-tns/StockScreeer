"""
Base Subscriber Interface
==========================

Abstract base class for event subscribers with isolated database connections.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class ISubscriber(ABC):
    """Abstract interface for event subscribers"""
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start the subscriber
        
        Raises:
            SubscriberError: If start fails
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the subscriber gracefully
        """
        pass
    
    @abstractmethod
    async def on_message(self, channel: str, data: bytes) -> None:
        """
        Handle incoming message
        
        Args:
            channel: Channel name
            data: Message payload (serialized)
        
        Raises:
            SubscriberError: If message handling fails
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
        Get subscriber statistics
        
        Returns:
            Dictionary with statistics
        """
        pass


class BaseSubscriber(ISubscriber):
    """
    Base subscriber implementation with common functionality
    
    Features:
    - Isolated database connection pool per subscriber
    - Automatic reconnection on connection loss
    - Message processing with error handling
    - DLQ integration for failed messages
    - Statistics tracking
    - Health checks
    """
    
    def __init__(
        self,
        subscriber_id: str,
        broker,  # IEventBroker
        serializer,  # IMessageSerializer
        channels: List[str],
        db_url: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 3600,
        dlq_manager = None,  # Optional DLQManager
    ):
        """
        Initialize base subscriber
        
        Args:
            subscriber_id: Unique subscriber identifier
            broker: Event broker instance
            serializer: Message serializer
            channels: List of channels to subscribe to
            db_url: Database connection URL (optional)
            pool_size: Database connection pool size
            max_overflow: Maximum overflow connections
            pool_recycle: Pool recycle time in seconds
            dlq_manager: Dead letter queue manager (optional)
        """
        self.subscriber_id = subscriber_id
        self.broker = broker
        self.serializer = serializer
        self.channels = channels
        self.dlq_manager = dlq_manager
        
        # Database connection (optional)
        self._db_engine: Optional[AsyncEngine] = None
        self._session_maker = None
        
        if db_url:
            self._db_engine = create_async_engine(
                db_url,
                poolclass=NullPool if 'sqlite' in db_url else None,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,
                echo=False,
            )
            self._session_maker = sessionmaker(
                self._db_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        
        # State tracking
        self._running = False
        self._shutdown = False
        self._start_time: Optional[float] = None
        
        # Statistics
        self._stats = {
            'total_received': 0,
            'total_processed': 0,
            'total_errors': 0,
            'last_message_time': None,
            'last_error': None,
            'last_error_time': None,
            'messages_per_channel': {},
        }
        
        # Health status
        self._health_status = {
            'status': 'stopped',  # stopped, starting, healthy, degraded, unhealthy
            'last_check': None,
            'error_count': 0,
        }
        
        logger.info(
            f"BaseSubscriber initialized: id={subscriber_id}, "
            f"channels={channels}, db={'yes' if db_url else 'no'}"
        )
    
    async def start(self) -> None:
        """Start the subscriber"""
        if self._running:
            logger.warning(f"Subscriber {self.subscriber_id} already running")
            return
        
        logger.info(f"Starting subscriber: {self.subscriber_id}")
        
        try:
            self._health_status['status'] = 'starting'
            
            # Subscribe to channels
            for channel in self.channels:
                await self.broker.subscribe(channel, self._handle_message)
                logger.info(f"Subscribed to channel: {channel}")
            
            self._running = True
            self._shutdown = False
            self._start_time = time.time()
            
            self._health_status['status'] = 'healthy'
            logger.info(f"Subscriber started: {self.subscriber_id}")
        
        except Exception as e:
            self._health_status['status'] = 'unhealthy'
            logger.error(f"Failed to start subscriber {self.subscriber_id}: {e}")
            raise SubscriberError(f"Start failed: {e}") from e
    
    async def stop(self) -> None:
        """Stop the subscriber gracefully"""
        if not self._running:
            return
        
        logger.info(f"Stopping subscriber: {self.subscriber_id}")
        self._shutdown = True
        self._running = False
        
        # Unsubscribe from channels
        for channel in self.channels:
            try:
                await self.broker.unsubscribe(channel)
                logger.info(f"Unsubscribed from channel: {channel}")
            except Exception as e:
                logger.error(f"Error unsubscribing from {channel}: {e}")
        
        # Close database connections
        if self._db_engine:
            await self._db_engine.dispose()
            logger.info("Database connections closed")
        
        self._health_status['status'] = 'stopped'
        logger.info(f"Subscriber stopped: {self.subscriber_id}")
    
    async def on_message(self, channel: str, data: bytes) -> None:
        """
        Handle incoming message (override in subclass)
        
        Args:
            channel: Channel name
            data: Deserialized message data
        """
        raise NotImplementedError("Subclass must implement on_message()")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        uptime = time.time() - self._start_time if self._start_time else 0
        
        # Check database connection if available
        db_healthy = True
        if self._db_engine:
            try:
                async with self._db_engine.connect() as conn:
                    await conn.execute("SELECT 1")
            except Exception as e:
                db_healthy = False
                logger.error(f"Database health check failed: {e}")
        
        health = {
            'subscriber_id': self.subscriber_id,
            'status': self._health_status['status'],
            'running': self._running,
            'uptime_seconds': round(uptime, 2),
            'error_count': self._health_status['error_count'],
            'last_message_time': self._stats['last_message_time'],
            'total_received': self._stats['total_received'],
            'total_processed': self._stats['total_processed'],
            'total_errors': self._stats['total_errors'],
            'db_healthy': db_healthy,
        }
        
        self._health_status['last_check'] = time.time()
        
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """Get subscriber statistics"""
        uptime = time.time() - self._start_time if self._start_time else 0
        
        return {
            'subscriber_id': self.subscriber_id,
            'running': self._running,
            'status': self._health_status['status'],
            'uptime_seconds': round(uptime, 2),
            'total_received': self._stats['total_received'],
            'total_processed': self._stats['total_processed'],
            'total_errors': self._stats['total_errors'],
            'success_rate': self._calculate_success_rate(),
            'last_message_time': self._stats['last_message_time'],
            'last_error': self._stats['last_error'],
            'last_error_time': self._stats['last_error_time'],
            'messages_per_channel': self._stats['messages_per_channel'].copy(),
        }
    
    # ========================================================================
    # Protected Methods
    # ========================================================================
    
    async def _handle_message(self, channel: str, data: bytes) -> None:
        """
        Internal message handler with error handling and DLQ
        
        Args:
            channel: Channel name
            data: Serialized message data
        """
        if self._shutdown:
            return
        
        try:
            # Update statistics
            self._stats['total_received'] += 1
            self._stats['last_message_time'] = time.time()
            
            if channel not in self._stats['messages_per_channel']:
                self._stats['messages_per_channel'][channel] = 0
            self._stats['messages_per_channel'][channel] += 1
            
            # Deserialize message
            try:
                message_data = self.serializer.deserialize(data)
            except Exception as e:
                logger.error(f"Failed to deserialize message from {channel}: {e}")
                self._record_error(f"Deserialization error: {e}")
                
                # Send to DLQ
                if self.dlq_manager:
                    await self.dlq_manager.add_failed_message(
                        channel=channel,
                        payload=data,
                        error_type="DeserializationError",
                        error_message=str(e),
                        subscriber_id=self.subscriber_id,
                    )
                return
            
            # Process message
            try:
                await self.on_message(channel, message_data)
                
                # Update success statistics
                self._stats['total_processed'] += 1
                
                # Reset error count on success
                if self._health_status['error_count'] > 0:
                    self._health_status['error_count'] = max(
                        0, self._health_status['error_count'] - 1
                    )
                
                # Update health status
                if self._health_status['status'] != 'healthy':
                    self._health_status['status'] = 'healthy'
            
            except Exception as e:
                logger.error(f"Error processing message from {channel}: {e}")
                self._record_error(f"Processing error: {e}")
                
                # Send to DLQ
                if self.dlq_manager:
                    await self.dlq_manager.add_failed_message(
                        channel=channel,
                        payload=data,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        subscriber_id=self.subscriber_id,
                    )
        
        except Exception as e:
            logger.error(f"Unexpected error in message handler: {e}")
            self._record_error(f"Handler error: {e}")
    
    @asynccontextmanager
    async def get_db_session(self):
        """
        Get a database session context manager
        
        Usage:
            async with subscriber.get_db_session() as session:
                # Use session
                result = await session.execute(query)
        
        Yields:
            AsyncSession: Database session
        """
        if not self._session_maker:
            raise SubscriberError("Database not configured")
        
        session = self._session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def _record_error(self, error_message: str) -> None:
        """Record error in statistics"""
        self._stats['total_errors'] += 1
        self._stats['last_error'] = error_message
        self._stats['last_error_time'] = time.time()
        self._health_status['error_count'] += 1
        
        # Update health status based on error count
        if self._health_status['error_count'] > 10:
            self._health_status['status'] = 'unhealthy'
        elif self._health_status['error_count'] > 3:
            self._health_status['status'] = 'degraded'
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self._stats['total_received']
        if total == 0:
            return 100.0
        return round((self._stats['total_processed'] / total) * 100, 2)


class SubscriberError(Exception):
    """Base exception for subscriber errors"""
    pass
