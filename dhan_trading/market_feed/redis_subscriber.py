"""
Redis Subscriber Base Class
===========================
Base class for all market data subscribers.

Provides:
- Pub/Sub subscription for real-time data
- Stream reading for historical data / catch-up
- Automatic reconnection
- Message parsing

Usage:
    class MyVisualizer(RedisSubscriber):
        def on_quote(self, quote: QuoteData):
            # Handle quote data
            print(f"LTP: {quote.ltp}")
    
    visualizer = MyVisualizer()
    visualizer.subscribe([CHANNEL_QUOTES])
    visualizer.run()  # Blocking
"""
import os
import sys
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

try:
    import redis
except ImportError:
    redis = None
    print("WARNING: redis package not installed. Run: pip install redis")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.feed_config import FeedConfig
from dhan_trading.market_feed.redis_publisher import (
    CHANNEL_TICKS, CHANNEL_QUOTES, CHANNEL_DEPTH,
    STREAM_TICKS, STREAM_QUOTES, STREAM_DEPTH,
    TickData, QuoteData, DepthData
)

logger = logging.getLogger(__name__)


class RedisSubscriber(ABC):
    """
    Base class for Redis pub/sub subscribers.
    
    Subclasses should implement:
    - on_tick(tick: TickData) - for tick data
    - on_quote(quote: QuoteData) - for quote data
    - on_depth(depth: DepthData) - for market depth data
    """
    
    def __init__(self, config: Optional[FeedConfig] = None):
        """
        Initialize subscriber.
        
        Args:
            config: FeedConfig with Redis settings
        """
        if redis is None:
            raise ImportError("redis package required: pip install redis")
        
        self.config = config or FeedConfig()
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Subscribed channels
        self._channels: List[str] = []
        
        # Stats
        self._stats = {
            'messages_received': 0,
            'ticks_received': 0,
            'quotes_received': 0,
            'depth_received': 0,
            'errors': 0,
            'last_message_time': None
        }
    
    def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self._client = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info(f"Subscriber connected to Redis at {self.config.REDIS_HOST}:{self.config.REDIS_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Redis."""
        self._running = False
        
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except:
                pass
        
        if self._client:
            self._client.close()
        
        self._connected = False
        logger.info("Subscriber disconnected from Redis")
    
    def subscribe(self, channels: List[str]) -> bool:
        """
        Subscribe to channels.
        
        Args:
            channels: List of channel names (e.g., [CHANNEL_QUOTES])
        
        Returns:
            True if subscribed successfully
        """
        if not self._connected:
            if not self.connect():
                return False
        
        try:
            self._pubsub = self._client.pubsub()
            self._pubsub.subscribe(*channels)
            self._channels = channels
            logger.info(f"Subscribed to channels: {channels}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            return False
    
    def _handle_message(self, message: Dict):
        """Handle incoming pub/sub message."""
        if message['type'] != 'message':
            return
        
        channel = message['channel']
        data = message['data']
        
        self._stats['messages_received'] += 1
        self._stats['last_message_time'] = datetime.now()
        
        try:
            if channel == CHANNEL_TICKS:
                tick = TickData.from_json(data)
                self._stats['ticks_received'] += 1
                self.on_tick(tick)
                
            elif channel == CHANNEL_QUOTES:
                quote = QuoteData.from_json(data)
                self._stats['quotes_received'] += 1
                self.on_quote(quote)
                
            elif channel == CHANNEL_DEPTH:
                depth = DepthData.from_json(data)
                self._stats['depth_received'] += 1
                self.on_depth(depth)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self._stats['errors'] += 1
    
    def run(self, blocking: bool = True):
        """
        Start receiving messages.
        
        Args:
            blocking: If True, blocks until stop() is called
        """
        if not self._pubsub:
            logger.error("Not subscribed to any channels")
            return
        
        self._running = True
        logger.info("Subscriber started listening...")
        
        if blocking:
            self._listen_loop()
        else:
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
    
    def _listen_loop(self):
        """Main listen loop."""
        while self._running:
            try:
                message = self._pubsub.get_message(timeout=1.0)
                if message:
                    self._handle_message(message)
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                self._stats['errors'] += 1
                time.sleep(1)  # Back off on error
        
        logger.info("Subscriber listen loop ended")
    
    def stop(self):
        """Stop receiving messages."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self.disconnect()
    
    def get_stats(self) -> Dict:
        """Get subscriber statistics."""
        return {
            **self._stats,
            'connected': self._connected,
            'channels': self._channels
        }
    
    # =========================================================================
    # Stream methods for historical data / catch-up
    # =========================================================================
    
    def read_stream(self, stream: str, 
                   start_id: str = "0",
                   count: int = 100) -> List[Dict]:
        """
        Read from a Redis stream.
        
        Args:
            stream: Stream name
            start_id: Start from this ID (0 = beginning, $ = new only)
            count: Number of entries to read
        
        Returns:
            List of entries
        """
        if not self._connected:
            return []
        
        try:
            entries = self._client.xrange(stream, min=start_id, count=count)
            return [
                {'id': entry_id, 'data': data}
                for entry_id, data in entries
            ]
        except Exception as e:
            logger.error(f"Error reading stream: {e}")
            return []
    
    def read_stream_latest(self, stream: str, count: int = 10) -> List[Dict]:
        """
        Read latest entries from a stream.
        
        Args:
            stream: Stream name
            count: Number of latest entries
        
        Returns:
            List of entries (newest first)
        """
        if not self._connected:
            return []
        
        try:
            entries = self._client.xrevrange(stream, count=count)
            return [
                {'id': entry_id, 'data': data}
                for entry_id, data in entries
            ]
        except Exception as e:
            logger.error(f"Error reading stream: {e}")
            return []
    
    def get_stream_length(self, stream: str) -> int:
        """Get number of entries in a stream."""
        if not self._connected:
            return 0
        try:
            return self._client.xlen(stream)
        except:
            return 0
    
    # =========================================================================
    # Abstract methods - implement in subclasses
    # =========================================================================
    
    def on_tick(self, tick: TickData):
        """
        Handle tick data. Override in subclass.
        
        Args:
            tick: TickData object
        """
        pass  # Default: do nothing
    
    def on_quote(self, quote: QuoteData):
        """
        Handle quote data. Override in subclass.
        
        Args:
            quote: QuoteData object
        """
        pass  # Default: do nothing
    
    def on_depth(self, depth: DepthData):
        """
        Handle market depth data. Override in subclass.
        
        Args:
            depth: DepthData object
        """
        pass  # Default: do nothing


class SimpleQuoteSubscriber(RedisSubscriber):
    """Simple subscriber that prints quotes to console."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._instrument_names: Dict[int, str] = {}
    
    def set_instrument_names(self, names: Dict[int, str]):
        """Set mapping from security_id to name."""
        self._instrument_names = names
    
    def on_quote(self, quote: QuoteData):
        """Print quote to console."""
        name = self._instrument_names.get(quote.security_id, str(quote.security_id))
        change = quote.ltp - quote.day_close if quote.day_close else 0
        change_pct = (change / quote.day_close * 100) if quote.day_close else 0
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"{name}: LTP={quote.ltp:.2f} "
              f"({change:+.2f} / {change_pct:+.2f}%) "
              f"Vol={quote.volume:,}")


if __name__ == "__main__":
    import signal
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("Simple Quote Subscriber")
    print("=" * 60)
    print("Subscribing to quote channel...")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    subscriber = SimpleQuoteSubscriber()
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nStopping subscriber...")
        subscriber.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Set instrument names (example)
    subscriber.set_instrument_names({
        49543: "NIFTY DEC FUT",
        49229: "NIFTY JAN FUT"
    })
    
    if subscriber.connect():
        subscriber.subscribe([CHANNEL_QUOTES])
        subscriber.run(blocking=True)
    else:
        print("Failed to connect to Redis!")
