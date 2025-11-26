"""
In-Memory Event Broker Implementation
======================================

Lightweight in-memory broker for local development and testing.
No external dependencies required.
"""

import asyncio
import logging
import time
from typing import Callable, Optional, Any, Dict, List
from collections import defaultdict

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


class InMemoryBroker(IEventBroker):
    """
    In-memory event broker for local development and testing
    
    Features:
    - No external dependencies (no Redis required)
    - Synchronous message delivery within same process
    - Channel-based pub/sub pattern
    - Message history for debugging
    - Statistics tracking
    
    Limitations:
    - Single process only (no distributed systems)
    - Messages not persisted (lost on restart)
    - No network communication
    
    Use Cases:
    - Local development without Redis
    - Unit/integration testing
    - CI/CD pipelines
    - Demos and prototyping
    """
    
    def __init__(
        self,
        serializer: IMessageSerializer,
        max_message_history: int = 1000,
        enable_history: bool = True,
    ):
        """
        Initialize in-memory broker
        
        Args:
            serializer: Message serializer instance
            max_message_history: Maximum messages to keep in history
            enable_history: Whether to track message history
        """
        self.serializer = serializer
        self.max_message_history = max_message_history
        self.enable_history = enable_history
        
        # Subscription tracking: {channel: [callbacks]}
        self._subscriptions: Dict[str, List[Callable[[str, bytes], None]]] = defaultdict(list)
        
        # Message history: {channel: [(timestamp, message)]}
        self._message_history: Dict[str, List[tuple[float, bytes]]] = defaultdict(list)
        
        # Statistics
        self._stats = {
            'total_published': 0,
            'total_delivered': 0,
            'messages_by_channel': defaultdict(int),
            'start_time': time.time(),
        }
        
        # Connection state
        self._connected = False
        
        logger.info("InMemoryBroker initialized (no external dependencies)")
    
    async def connect(self) -> None:
        """Establish connection (no-op for in-memory broker)"""
        self._connected = True
        self._stats['start_time'] = time.time()
        logger.info("InMemoryBroker connected (ready)")
    
    async def disconnect(self) -> None:
        """Close connection (cleanup for in-memory broker)"""
        logger.info("InMemoryBroker shutting down...")
        
        # Clear subscriptions
        self._subscriptions.clear()
        
        # Optionally clear history
        if not self.enable_history:
            self._message_history.clear()
        
        self._connected = False
        logger.info("InMemoryBroker shutdown complete")
    
    async def publish(self, channel: str, message: bytes) -> None:
        """
        Publish a message to a channel
        
        Args:
            channel: Channel name
            message: Serialized message bytes
        """
        if not self._connected:
            raise PublishError("Broker not connected")
        
        try:
            # Update statistics
            self._stats['total_published'] += 1
            self._stats['messages_by_channel'][channel] += 1
            
            # Store in history
            if self.enable_history:
                history = self._message_history[channel]
                history.append((time.time(), message))
                
                # Trim history if needed
                if len(history) > self.max_message_history:
                    history.pop(0)
            
            # Deliver to all subscribers
            callbacks = self._subscriptions.get(channel, [])
            delivered = 0
            
            for callback in callbacks:
                try:
                    # Call callback (can be sync or async)
                    if asyncio.iscoroutinefunction(callback):
                        await callback(channel, message)
                    else:
                        callback(channel, message)
                    delivered += 1
                except Exception as e:
                    logger.error(f"Error in callback for {channel}: {e}")
            
            self._stats['total_delivered'] += delivered
            
            logger.debug(
                f"Published to {channel}: {len(message)} bytes "
                f"-> {delivered} subscriber(s)"
            )
        
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            raise PublishError(f"Publish failed: {e}") from e
    
    async def subscribe(
        self,
        channel: str,
        callback: Callable[[str, bytes], None],
    ) -> None:
        """
        Subscribe to a channel
        
        Args:
            channel: Channel name to subscribe to
            callback: Function to call when message received
        """
        if not self._connected:
            raise SubscriptionError("Broker not connected")
        
        try:
            # Add callback to subscriptions
            if callback not in self._subscriptions[channel]:
                self._subscriptions[channel].append(callback)
                logger.info(
                    f"Subscribed to {channel} "
                    f"(total subscribers: {len(self._subscriptions[channel])})"
                )
            else:
                logger.warning(f"Callback already subscribed to {channel}")
        
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            raise SubscriptionError(f"Subscription failed: {e}") from e
    
    async def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribe from a channel (removes all callbacks)
        
        Args:
            channel: Channel name to unsubscribe from
        """
        if channel in self._subscriptions:
            count = len(self._subscriptions[channel])
            del self._subscriptions[channel]
            logger.info(f"Unsubscribed from {channel} ({count} callback(s) removed)")
        else:
            logger.warning(f"Not subscribed to {channel}")
    
    async def unsubscribe_callback(
        self,
        channel: str,
        callback: Callable[[str, bytes], None],
    ) -> None:
        """
        Unsubscribe a specific callback from a channel
        
        Args:
            channel: Channel name
            callback: Callback to remove
        """
        if channel in self._subscriptions:
            if callback in self._subscriptions[channel]:
                self._subscriptions[channel].remove(callback)
                logger.info(f"Removed callback from {channel}")
                
                # Clean up empty channel
                if not self._subscriptions[channel]:
                    del self._subscriptions[channel]
            else:
                logger.warning(f"Callback not found in {channel}")
        else:
            logger.warning(f"Not subscribed to {channel}")
    
    def is_connected(self) -> bool:
        """Check if broker is connected"""
        return self._connected
    
    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on broker
        
        Returns:
            Dictionary with health status
        """
        if not self._connected:
            return {
                'healthy': False,
                'connected': False,
                'latency_ms': None,
                'error': 'Not connected',
            }
        
        # In-memory broker is always healthy when connected
        return {
            'healthy': True,
            'connected': True,
            'latency_ms': 0.0,  # No network latency
            'error': None,
        }
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get broker statistics
        
        Returns:
            Dictionary with broker stats
        """
        uptime = time.time() - self._stats['start_time'] if self._connected else 0
        
        return {
            'connected': self._connected,
            'type': 'in-memory',
            'total_published': self._stats['total_published'],
            'total_delivered': self._stats['total_delivered'],
            'active_channels': len(self._subscriptions),
            'channels': list(self._subscriptions.keys()),
            'messages_by_channel': dict(self._stats['messages_by_channel']),
            'total_subscribers': sum(
                len(callbacks) for callbacks in self._subscriptions.values()
            ),
            'uptime_seconds': round(uptime, 2),
            'serializer': self.serializer.get_format_name(),
        }
    
    def get_message_history(
        self,
        channel: str,
        limit: Optional[int] = None,
    ) -> List[tuple[float, bytes]]:
        """
        Get message history for a channel
        
        Args:
            channel: Channel name
            limit: Maximum number of messages to return (most recent)
        
        Returns:
            List of (timestamp, message) tuples
        """
        if not self.enable_history:
            logger.warning("Message history is disabled")
            return []
        
        history = self._message_history.get(channel, [])
        
        if limit:
            return history[-limit:]
        return history
    
    def clear_history(self, channel: Optional[str] = None) -> None:
        """
        Clear message history
        
        Args:
            channel: Specific channel to clear, or None to clear all
        """
        if channel:
            if channel in self._message_history:
                count = len(self._message_history[channel])
                self._message_history[channel].clear()
                logger.info(f"Cleared {count} messages from {channel} history")
        else:
            total = sum(len(msgs) for msgs in self._message_history.values())
            self._message_history.clear()
            logger.info(f"Cleared all message history ({total} messages)")
    
    def get_subscribers(self, channel: str) -> int:
        """
        Get number of subscribers for a channel
        
        Args:
            channel: Channel name
        
        Returns:
            Number of subscribers
        """
        return len(self._subscriptions.get(channel, []))


# Convenience function to create in-memory broker
def create_inmemory_broker(
    serializer: IMessageSerializer,
    **kwargs
) -> InMemoryBroker:
    """
    Create an in-memory event broker instance
    
    Args:
        serializer: Message serializer
        **kwargs: Additional broker configuration
    
    Returns:
        InMemoryBroker instance
    """
    return InMemoryBroker(serializer, **kwargs)
