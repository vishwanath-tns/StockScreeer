"""
Redis Publisher
===============
Publishes market data to Redis using Pub/Sub (real-time) and Streams (persistent).

Architecture:
- Pub/Sub: Fire-and-forget, real-time delivery to all connected subscribers
- Streams: Persistent, allows late subscribers to catch up, supports consumer groups

Channels:
- dhan:ticks       - Ticker packets (LTP only)
- dhan:quotes      - Quote packets (full trade data)
- dhan:depth       - Full packets with market depth

Streams:
- dhan:ticks:stream
- dhan:quotes:stream
- dhan:depth:stream
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

try:
    import redis
except ImportError:
    redis = None
    print("WARNING: redis package not installed. Run: pip install redis")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.feed_config import FeedConfig

logger = logging.getLogger(__name__)


# Channel names
CHANNEL_TICKS = "dhan:ticks"
CHANNEL_QUOTES = "dhan:quotes"
CHANNEL_DEPTH = "dhan:depth"

# Stream names
STREAM_TICKS = "dhan:ticks:stream"
STREAM_QUOTES = "dhan:quotes:stream"
STREAM_DEPTH = "dhan:depth:stream"

# Stream max length (rolling window)
STREAM_MAX_LEN = 100000  # Keep last 100k entries per stream


@dataclass
class TickData:
    """Ticker packet data structure."""
    security_id: int
    exchange_segment: int
    ltp: float
    ltt: int  # EPOCH timestamp
    received_at: float = 0.0  # Python timestamp
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TickData':
        return cls(**data)
    
    @classmethod
    def from_json(cls, data: str) -> 'TickData':
        return cls(**json.loads(data))


@dataclass
class QuoteData:
    """Quote packet data structure."""
    security_id: int
    exchange_segment: int
    ltp: float
    ltq: int
    ltt: int
    atp: float
    volume: int
    total_sell_qty: int
    total_buy_qty: int
    day_open: float
    day_close: float
    day_high: float
    day_low: float
    open_interest: Optional[int] = None
    prev_close: Optional[float] = None
    received_at: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QuoteData':
        return cls(**data)
    
    @classmethod
    def from_json(cls, data: str) -> 'QuoteData':
        return cls(**json.loads(data))


@dataclass
class DepthData:
    """Full packet with market depth."""
    security_id: int
    exchange_segment: int
    ltp: float
    ltq: int
    ltt: int
    atp: float
    volume: int
    total_sell_qty: int
    total_buy_qty: int
    open_interest: int
    oi_high: int
    oi_low: int
    day_open: float
    day_close: float
    day_high: float
    day_low: float
    bid_prices: list  # 5 bid prices
    bid_qtys: list    # 5 bid quantities
    ask_prices: list  # 5 ask prices
    ask_qtys: list    # 5 ask quantities
    received_at: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DepthData':
        return cls(**data)
    
    @classmethod
    def from_json(cls, data: str) -> 'DepthData':
        return cls(**json.loads(data))


class RedisPublisher:
    """
    Publishes market data to Redis.
    
    Uses both Pub/Sub (for real-time) and Streams (for persistence).
    """
    
    def __init__(self, config: Optional[FeedConfig] = None):
        """
        Initialize publisher.
        
        Args:
            config: FeedConfig with Redis settings
        """
        if redis is None:
            raise ImportError("redis package required: pip install redis")
        
        self.config = config or FeedConfig()
        self._client: Optional[redis.Redis] = None
        self._connected = False
        
        # Stats
        self._stats = {
            'ticks_published': 0,
            'quotes_published': 0,
            'depth_published': 0,
            'errors': 0,
            'last_publish_time': None
        }
    
    def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self._client = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                decode_responses=True,  # Auto-decode to strings
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.config.REDIS_HOST}:{self.config.REDIS_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            self._client.close()
            self._connected = False
            logger.info("Disconnected from Redis")
    
    def publish_tick(self, tick: TickData) -> bool:
        """
        Publish tick data.
        
        Args:
            tick: TickData object
        
        Returns:
            True if published successfully
        """
        if not self._connected:
            return False
        
        try:
            tick.received_at = datetime.now().timestamp()
            data = tick.to_json()
            
            # Pub/Sub - real-time
            self._client.publish(CHANNEL_TICKS, data)
            
            # Stream - persistent (with max length to prevent unbounded growth)
            self._client.xadd(
                STREAM_TICKS, 
                tick.to_dict(),
                maxlen=STREAM_MAX_LEN,
                approximate=True
            )
            
            self._stats['ticks_published'] += 1
            self._stats['last_publish_time'] = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish tick: {e}")
            self._stats['errors'] += 1
            return False
    
    def publish_quote(self, quote: QuoteData) -> bool:
        """
        Publish quote data.
        
        Args:
            quote: QuoteData object
        
        Returns:
            True if published successfully
        """
        if not self._connected:
            return False
        
        try:
            quote.received_at = datetime.now().timestamp()
            data = quote.to_json()
            
            # Pub/Sub - real-time
            num_subscribers = self._client.publish(CHANNEL_QUOTES, data)
            
            # Stream - persistent
            # Convert to flat dict for Redis Stream (no nested objects)
            stream_data = {
                'security_id': str(quote.security_id),
                'exchange_segment': str(quote.exchange_segment),
                'ltp': str(quote.ltp),
                'ltq': str(quote.ltq),
                'ltt': str(quote.ltt),
                'atp': str(quote.atp),
                'volume': str(quote.volume),
                'total_sell_qty': str(quote.total_sell_qty),
                'total_buy_qty': str(quote.total_buy_qty),
                'day_open': str(quote.day_open),
                'day_close': str(quote.day_close),
                'day_high': str(quote.day_high),
                'day_low': str(quote.day_low),
                'open_interest': str(quote.open_interest or 0),
                'received_at': str(quote.received_at)
            }
            
            self._client.xadd(
                STREAM_QUOTES,
                stream_data,
                maxlen=STREAM_MAX_LEN,
                approximate=True
            )
            
            self._stats['quotes_published'] += 1
            self._stats['last_publish_time'] = datetime.now()
            
            # Log periodically
            if self._stats['quotes_published'] % 100 == 0:
                logger.info(f"Published {self._stats['quotes_published']} quotes, "
                           f"{num_subscribers} subscribers")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish quote: {e}")
            self._stats['errors'] += 1
            return False
    
    def publish_depth(self, depth: DepthData) -> bool:
        """
        Publish market depth data.
        
        Args:
            depth: DepthData object
        
        Returns:
            True if published successfully
        """
        if not self._connected:
            return False
        
        try:
            depth.received_at = datetime.now().timestamp()
            data = depth.to_json()
            
            # Pub/Sub - real-time
            self._client.publish(CHANNEL_DEPTH, data)
            
            # Stream - persistent (store JSON as single field for complex data)
            self._client.xadd(
                STREAM_DEPTH,
                {'data': data},
                maxlen=STREAM_MAX_LEN,
                approximate=True
            )
            
            self._stats['depth_published'] += 1
            self._stats['last_publish_time'] = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish depth: {e}")
            self._stats['errors'] += 1
            return False
    
    def get_stats(self) -> Dict:
        """Get publisher statistics."""
        return {
            **self._stats,
            'connected': self._connected
        }
    
    def get_subscriber_count(self, channel: str = CHANNEL_QUOTES) -> int:
        """Get number of subscribers to a channel."""
        if not self._connected:
            return 0
        try:
            result = self._client.pubsub_numsub(channel)
            return result[0][1] if result else 0
        except:
            return 0


if __name__ == "__main__":
    # Test publisher
    import time
    
    logging.basicConfig(level=logging.INFO)
    
    publisher = RedisPublisher()
    if publisher.connect():
        print("Publisher connected!")
        
        # Publish test quotes
        for i in range(5):
            quote = QuoteData(
                security_id=49543,
                exchange_segment=2,
                ltp=25900.0 + i,
                ltq=75,
                ltt=int(time.time()),
                atp=25930.0,
                volume=1000000 + i * 1000,
                total_sell_qty=500000,
                total_buy_qty=500000,
                day_open=25950.0,
                day_close=26000.0,
                day_high=26050.0,
                day_low=25850.0,
                open_interest=16000000
            )
            
            publisher.publish_quote(quote)
            print(f"Published quote {i+1}: LTP={quote.ltp}")
            time.sleep(0.5)
        
        print(f"\nStats: {publisher.get_stats()}")
        publisher.disconnect()
    else:
        print("Failed to connect!")
