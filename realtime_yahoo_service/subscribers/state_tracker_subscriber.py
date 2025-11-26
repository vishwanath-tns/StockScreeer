"""
State Tracker Subscriber
=========================

Subscriber that tracks latest market state in memory.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_subscriber import BaseSubscriber, SubscriberError
from events.event_models import CandleDataEvent, FetchStatusEvent

logger = logging.getLogger(__name__)


class StateTrackerSubscriber(BaseSubscriber):
    """
    Subscriber that maintains latest market state in memory
    
    Features:
    - Tracks latest candle data per symbol
    - Tracks publisher health status
    - Provides snapshot API for external queries
    - In-memory only (no database)
    """
    
    def __init__(
        self,
        subscriber_id: str,
        broker,
        serializer,
        **kwargs
    ):
        """
        Initialize state tracker subscriber
        
        Args:
            subscriber_id: Unique subscriber identifier
            broker: Event broker instance
            serializer: Message serializer
            **kwargs: Additional arguments for BaseSubscriber
        """
        super().__init__(
            subscriber_id=subscriber_id,
            broker=broker,
            serializer=serializer,
            channels=['market.candle', 'market.status'],
            **kwargs
        )
        
        # State storage
        self._symbol_state: Dict[str, CandleDataEvent] = {}
        self._publisher_status: Dict[str, FetchStatusEvent] = {}
        
        logger.info("StateTrackerSubscriber initialized")
    
    async def on_message(self, channel: str, data: Dict[str, Any]) -> None:
        """
        Handle incoming message
        
        Args:
            channel: Channel name
            data: Deserialized message data
        """
        try:
            if channel == 'market.candle':
                await self._handle_candle_data(data)
            elif channel == 'market.status':
                await self._handle_status(data)
        
        except Exception as e:
            logger.error(f"Error handling message from {channel}: {e}")
            raise SubscriberError(f"Message handling failed: {e}") from e
    
    async def _handle_candle_data(self, data: Dict[str, Any]) -> None:
        """Handle candle data event"""
        event = CandleDataEvent(**data)
        
        # Update symbol state
        self._symbol_state[event.symbol] = event
        
        logger.debug(f"Updated state for {event.symbol}: close={event.close_price}")
    
    async def _handle_status(self, data: Dict[str, Any]) -> None:
        """Handle fetch status event"""
        event = FetchStatusEvent(**data)
        
        # Update publisher status
        self._publisher_status[event.publisher_id] = event
        
        logger.debug(f"Updated status for {event.publisher_id}: {event.status}")
    
    def get_symbol_state(self, symbol: str) -> Optional[CandleDataEvent]:
        """
        Get latest state for a symbol
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Latest CandleDataEvent or None
        """
        return self._symbol_state.get(symbol)
    
    def get_all_symbols(self) -> Dict[str, CandleDataEvent]:
        """
        Get state for all symbols
        
        Returns:
            Dictionary mapping symbol to CandleDataEvent
        """
        return self._symbol_state.copy()
    
    def get_publisher_status(self, publisher_id: str) -> Optional[FetchStatusEvent]:
        """
        Get status for a publisher
        
        Args:
            publisher_id: Publisher identifier
        
        Returns:
            Latest FetchStatusEvent or None
        """
        return self._publisher_status.get(publisher_id)
    
    def get_all_publishers(self) -> Dict[str, FetchStatusEvent]:
        """
        Get status for all publishers
        
        Returns:
            Dictionary mapping publisher_id to FetchStatusEvent
        """
        return self._publisher_status.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics including state counts"""
        stats = super().get_stats()
        stats.update({
            'symbols_tracked': len(self._symbol_state),
            'publishers_tracked': len(self._publisher_status),
        })
        return stats
