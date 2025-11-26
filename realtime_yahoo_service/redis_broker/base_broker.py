"""
Base Event Broker Interface
============================

Abstract interface for event brokers (Redis, In-Memory, etc.)
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Any
import logging

logger = logging.getLogger(__name__)


class IEventBroker(ABC):
    """Abstract interface for event brokers"""
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the broker
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the broker
        """
        pass
    
    @abstractmethod
    async def publish(self, channel: str, message: bytes) -> None:
        """
        Publish a message to a channel
        
        Args:
            channel: Channel name (e.g., 'candle_data', 'market_breadth')
            message: Serialized message bytes
            
        Raises:
            PublishError: If publish fails
        """
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        channel: str,
        callback: Callable[[str, bytes], None],
    ) -> None:
        """
        Subscribe to a channel with a callback
        
        Args:
            channel: Channel name to subscribe to
            callback: Function to call when message received (channel, message)
            
        Raises:
            SubscriptionError: If subscription fails
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribe from a channel
        
        Args:
            channel: Channel name to unsubscribe from
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if broker is connected
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on broker connection
        
        Returns:
            Dictionary with health status:
            {
                'healthy': bool,
                'connected': bool,
                'latency_ms': float,
                'error': Optional[str]
            }
        """
        pass


class BrokerError(Exception):
    """Base exception for broker errors"""
    pass


class PublishError(BrokerError):
    """Exception raised when publish fails"""
    pass


class SubscriptionError(BrokerError):
    """Exception raised when subscription fails"""
    pass


class ConnectionError(BrokerError):
    """Exception raised when connection fails"""
    pass
