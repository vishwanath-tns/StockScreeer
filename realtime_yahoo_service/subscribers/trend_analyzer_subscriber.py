"""
Trend Analyzer Subscriber - Computes technical indicators and trend analysis
"""

import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone
from collections import deque

from .base_subscriber import BaseSubscriber
from events.event_models import CandleDataEvent, TrendAnalysisEvent


logger = logging.getLogger(__name__)


class TrendAnalyzerSubscriber(BaseSubscriber):
    """
    Subscriber that analyzes price trends and computes technical indicators.
    
    Maintains a rolling window of candle data for each symbol and computes:
    - Moving averages (SMA)
    - Trend direction and strength
    - Support/resistance levels
    - Price momentum
    
    Publishes TrendAnalysisEvent to 'market.trend' channel.
    """
    
    def __init__(
        self,
        subscriber_id: str,
        broker,
        serializer,
        window_size: int = 50,
        publish_interval: float = 60.0,  # Publish every 60 seconds
        sma_periods: Optional[List[int]] = None,
        **kwargs
    ):
        """
        Initialize trend analyzer subscriber.
        
        Args:
            subscriber_id: Unique identifier for this subscriber
            broker: Message broker instance
            serializer: Serializer instance
            window_size: Number of candles to keep in memory per symbol
            publish_interval: Seconds between trend analysis publications
            sma_periods: List of SMA periods to compute (default: [20, 50])
            **kwargs: Additional arguments for BaseSubscriber
        """
        super().__init__(
            subscriber_id=subscriber_id,
            broker=broker,
            serializer=serializer,
            channels=['market.candle'],
            **kwargs
        )
        
        self._window_size = window_size
        self._publish_interval = publish_interval
        self._sma_periods = sma_periods or [20, 50]
        
        # Store rolling window of candles per symbol
        # {symbol: deque([CandleDataEvent, ...])}
        self._candle_history: Dict[str, deque] = {}
        
        # Background task for periodic publishing
        self._publish_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the subscriber and background tasks"""
        await super().start()
        
        # Start periodic trend publishing task
        self._publish_task = asyncio.create_task(self._periodic_publish())
        logger.info("Started periodic trend analysis publishing")
    
    async def stop(self):
        """Stop the subscriber and background tasks"""
        # Cancel periodic publishing task
        if self._publish_task and not self._publish_task.done():
            self._publish_task.cancel()
            try:
                await self._publish_task
            except asyncio.CancelledError:
                pass
        
        await super().stop()
        logger.info("Stopped trend analyzer subscriber")
    
    async def on_message(self, channel: str, data: bytes):
        """
        Process incoming candle data messages.
        
        Args:
            channel: Channel name
            data: Serialized message data
        """
        try:
            # Deserialize message
            message = self.serializer.deserialize(data)
            
            if channel == 'market.candle':
                await self._handle_candle_data(message)
            
            self._stats['total_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing message on {channel}: {e}")
            self._stats['total_errors'] = self._stats.get('total_errors', 0) + 1
    
    async def _handle_candle_data(self, message: dict):
        """
        Handle candle data event and update history.
        
        Args:
            message: Deserialized CandleDataEvent
        """
        try:
            event = CandleDataEvent(**message)
            symbol = event.symbol
            
            # Initialize history for new symbol
            if symbol not in self._candle_history:
                self._candle_history[symbol] = deque(maxlen=self._window_size)
            
            # Add candle to history
            self._candle_history[symbol].append(event)
            
            logger.debug(
                f"Updated candle history for {symbol}: "
                f"{len(self._candle_history[symbol])} candles"
            )
            
        except Exception as e:
            logger.error(f"Error handling candle data: {e}")
    
    def compute_sma(self, prices: List[float], period: int) -> Optional[float]:
        """
        Compute Simple Moving Average.
        
        Args:
            prices: List of prices
            period: SMA period
            
        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        return sum(prices[-period:]) / period
    
    def compute_trend_strength(self, prices: List[float]) -> float:
        """
        Compute trend strength based on price momentum.
        
        Args:
            prices: List of prices
            
        Returns:
            Trend strength score (-1.0 to 1.0)
        """
        if len(prices) < 2:
            return 0.0
        
        # Simple momentum: compare recent prices to older prices
        recent_avg = sum(prices[-5:]) / min(5, len(prices[-5:]))
        older_avg = sum(prices[:5]) / min(5, len(prices[:5]))
        
        if older_avg == 0:
            return 0.0
        
        # Percentage change, capped at ±100%
        pct_change = (recent_avg - older_avg) / older_avg
        return max(-1.0, min(1.0, pct_change))
    
    def analyze_symbol(self, symbol: str) -> Optional[dict]:
        """
        Perform trend analysis for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Trend analysis dict or None if insufficient data
        """
        if symbol not in self._candle_history:
            return None
        
        candles = list(self._candle_history[symbol])
        if len(candles) < 2:
            return None
        
        prices = [c.close_price for c in candles]
        
        # Compute SMAs
        smas = {}
        for period in self._sma_periods:
            sma = self.compute_sma(prices, period)
            if sma is not None:
                smas[f'sma_{period}'] = sma
        
        # Determine trend direction
        trend_strength = self.compute_trend_strength(prices)
        if trend_strength > 0.05:
            trend_direction = 'BULLISH'
        elif trend_strength < -0.05:
            trend_direction = 'BEARISH'
        else:
            trend_direction = 'NEUTRAL'
        
        # Latest candle
        latest = candles[-1]
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'latest_price': latest.close_price,
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'smas': smas,
            'candle_count': len(candles),
        }
    
    async def _periodic_publish(self):
        """Periodically publish trend analysis for all tracked symbols"""
        while self._running:
            try:
                await asyncio.sleep(self._publish_interval)
                
                if not self._candle_history:
                    continue
                
                # Analyze all symbols
                analyses = []
                for symbol in list(self._candle_history.keys()):
                    analysis = self.analyze_symbol(symbol)
                    if analysis:
                        analyses.append(analysis)
                
                if analyses:
                    # Publish trend analysis event
                    event = TrendAnalysisEvent(
                        timestamp=datetime.now(timezone.utc),
                        analyses=analyses,
                        total_symbols=len(analyses),
                    )
                    
                    serialized = self.serializer.serialize(event.model_dump())
                    await self.broker.publish('market.trend', serialized)
                    
                    logger.info(
                        f"Published trend analysis for {len(analyses)} symbols"
                    )
                    
                    self._stats['trends_published'] = self._stats.get('trends_published', 0) + 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic trend publishing: {e}")
    
    def get_stats(self) -> dict:
        """Get subscriber statistics including current trends"""
        stats = super().get_stats()
        stats.update({
            'symbols_tracked': len(self._candle_history),
            'trends_published': self._stats.get('trends_published', 0),
            'window_size': self._window_size,
            'sma_periods': self._sma_periods,
        })
        return stats
