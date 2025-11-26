"""
Market Breadth Subscriber
==========================

Subscriber that computes market breadth statistics.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from collections import defaultdict

from .base_subscriber import BaseSubscriber, SubscriberError
from events.event_models import CandleDataEvent, MarketBreadthEvent

logger = logging.getLogger(__name__)


class MarketBreadthSubscriber(BaseSubscriber):
    """
    Subscriber that computes and publishes market breadth statistics
    
    Features:
    - Tracks advances, declines, unchanged
    - Computes A/D ratio and sentiment score
    - Aggregates by index (NIFTY50, NIFTY500, etc.)
    - Publishes MarketBreadthEvent periodically
    """
    
    def __init__(
        self,
        subscriber_id: str,
        broker,
        serializer,
        index_name: str = 'NIFTY500',
        publish_interval: float = 60.0,
        **kwargs
    ):
        """
        Initialize market breadth subscriber
        
        Args:
            subscriber_id: Unique subscriber identifier
            broker: Event broker instance
            serializer: Message serializer
            index_name: Index identifier (e.g., 'NIFTY50', 'NIFTY500')
            publish_interval: Interval to publish breadth stats (seconds)
            **kwargs: Additional arguments for BaseSubscriber
        """
        super().__init__(
            subscriber_id=subscriber_id,
            broker=broker,
            serializer=serializer,
            channels=['market.candle'],
            **kwargs
        )
        
        self.index_name = index_name
        self.publish_interval = publish_interval
        
        # Breadth tracking
        self._symbol_prices: Dict[str, Dict[str, float]] = {}  # symbol -> {prev_close, close}
        self._trade_date: str = ''
        
        logger.info(
            f"MarketBreadthSubscriber initialized: index={index_name}, "
            f"interval={publish_interval}s"
        )
    
    async def on_message(self, channel: str, data: Dict[str, Any]) -> None:
        """
        Handle incoming candle data message
        
        Args:
            channel: Channel name
            data: Deserialized message data
        """
        try:
            event = CandleDataEvent(**data)
            
            # Update symbol prices
            self._symbol_prices[event.symbol] = {
                'prev_close': event.prev_close,
                'close': event.close_price,
            }
            
            # Update trade date
            if not self._trade_date:
                self._trade_date = event.trade_date
            
            logger.debug(f"Updated breadth data for {event.symbol}")
        
        except Exception as e:
            logger.error(f"Error handling candle data: {e}")
            raise SubscriberError(f"Message handling failed: {e}") from e
    
    def compute_breadth(self) -> MarketBreadthEvent:
        """
        Compute market breadth statistics
        
        Returns:
            MarketBreadthEvent with computed stats
        """
        advances = 0
        declines = 0
        unchanged = 0
        pct_changes = []
        
        for symbol, prices in self._symbol_prices.items():
            prev_close = prices['prev_close']
            close = prices['close']
            
            if close > prev_close:
                advances += 1
            elif close < prev_close:
                declines += 1
            else:
                unchanged += 1
            
            # Calculate percentage change
            if prev_close > 0:
                pct_change = ((close - prev_close) / prev_close) * 100
                pct_changes.append(pct_change)
        
        total_stocks = len(self._symbol_prices)
        
        # A/D ratio
        ad_ratio = advances / declines if declines > 0 else (advances if advances > 0 else 1.0)
        
        # Sentiment score (-1.0 to 1.0)
        # Formula: (advances - declines) / total_stocks
        sentiment_score = (advances - declines) / total_stocks if total_stocks > 0 else 0.0
        
        # Average percentage change
        avg_pct_change = sum(pct_changes) / len(pct_changes) if pct_changes else 0.0
        
        # Create event
        event = MarketBreadthEvent(
            index_name=self.index_name,
            trade_date=self._trade_date or datetime.now(timezone.utc).date().isoformat(),
            timestamp=int(datetime.now(timezone.utc).timestamp()),
            advances=advances,
            declines=declines,
            unchanged=unchanged,
            total_stocks=total_stocks,
            ad_ratio=round(ad_ratio, 3),
            sentiment_score=round(sentiment_score, 3),
            avg_pct_change=round(avg_pct_change, 2),
            data_source='yahoo_finance',
        )
        
        return event
    
    async def publish_breadth(self) -> None:
        """Compute and publish market breadth event"""
        if not self._symbol_prices:
            logger.warning("No symbol data available for breadth calculation")
            return
        
        try:
            # Compute breadth
            event = self.compute_breadth()
            
            # Serialize and publish
            if hasattr(event, 'model_dump'):
                data = self.serializer.serialize(event.model_dump())
            else:
                data = self.serializer.serialize(event)
            
            await self.broker.publish('market.breadth', data)
            
            logger.info(
                f"Published market breadth: {self.index_name}, "
                f"ADV={event.advances}, DEC={event.declines}, "
                f"sentiment={event.sentiment_score}"
            )
        
        except Exception as e:
            logger.error(f"Failed to publish breadth: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics including breadth data"""
        stats = super().get_stats()
        
        # Add current breadth snapshot
        if self._symbol_prices:
            breadth = self.compute_breadth()
            stats.update({
                'current_breadth': {
                    'advances': breadth.advances,
                    'declines': breadth.declines,
                    'unchanged': breadth.unchanged,
                    'ad_ratio': breadth.ad_ratio,
                    'sentiment_score': breadth.sentiment_score,
                }
            })
        
        return stats
