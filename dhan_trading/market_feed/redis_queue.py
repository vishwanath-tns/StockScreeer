"""
Redis Queue Manager
===================
Manages Redis queues for tick data transfer between services.
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict
import time

try:
    import redis
except ImportError:
    redis = None
    print("WARNING: redis package not installed. Run: pip install redis")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.feed_config import FeedConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """Ticker packet data structure."""
    security_id: int
    exchange_segment: int
    ltp: float
    ltt: int  # EPOCH timestamp
    received_at: float  # Python timestamp
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
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
    received_at: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, data: str) -> 'QuoteData':
        return cls(**json.loads(data))


@dataclass
class FullPacketData:
    """Full packet data structure with market depth."""
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
    depth: List[Dict]  # 5 levels of market depth
    received_at: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, data: str) -> 'FullPacketData':
        return cls(**json.loads(data))


class RedisQueueManager:
    """
    Manages Redis queues for market data.
    
    Uses Redis Lists for FIFO queue behavior with LPUSH/BRPOP pattern.
    """
    
    def __init__(self, config: Optional[FeedConfig] = None):
        if redis is None:
            raise ImportError("redis package required. Install with: pip install redis")
        
        self.config = config or FeedConfig()
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    @property
    def redis_client(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                password=self.config.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
        return self._redis
    
    def connect(self) -> bool:
        """Test and establish Redis connection."""
        try:
            self.redis_client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.config.REDIS_HOST}:{self.config.REDIS_PORT}")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
            self._redis = None
            self._connected = False
            logger.info("Disconnected from Redis")
    
    # ========== Producer Methods (Feed Service) ==========
    
    def push_tick(self, tick: TickData) -> bool:
        """Push tick data to queue."""
        try:
            self.redis_client.lpush(self.config.TICK_QUEUE, tick.to_json())
            return True
        except Exception as e:
            logger.error(f"Failed to push tick: {e}")
            return False
    
    def push_quote(self, quote: QuoteData) -> bool:
        """Push quote data to queue."""
        try:
            self.redis_client.lpush(self.config.QUOTE_QUEUE, quote.to_json())
            return True
        except Exception as e:
            logger.error(f"Failed to push quote: {e}")
            return False
    
    def push_full_packet(self, packet: FullPacketData) -> bool:
        """Push full packet to queue."""
        try:
            self.redis_client.lpush(self.config.FULL_QUEUE, packet.to_json())
            return True
        except Exception as e:
            logger.error(f"Failed to push full packet: {e}")
            return False
    
    def push_batch(self, queue_name: str, items: List[str]) -> int:
        """Push batch of items to queue."""
        if not items:
            return 0
        try:
            return self.redis_client.lpush(queue_name, *items)
        except Exception as e:
            logger.error(f"Failed to push batch: {e}")
            return 0
    
    # ========== Consumer Methods (DB Writer Service) ==========
    
    def pop_tick(self, timeout: int = 1) -> Optional[TickData]:
        """Pop tick from queue (blocking)."""
        try:
            result = self.redis_client.brpop(self.config.TICK_QUEUE, timeout=timeout)
            if result:
                _, data = result
                return TickData.from_json(data)
            return None
        except Exception as e:
            logger.error(f"Failed to pop tick: {e}")
            return None
    
    def pop_quote(self, timeout: int = 1) -> Optional[QuoteData]:
        """Pop quote from queue (blocking)."""
        try:
            result = self.redis_client.brpop(self.config.QUOTE_QUEUE, timeout=timeout)
            if result:
                _, data = result
                return QuoteData.from_json(data)
            return None
        except Exception as e:
            logger.error(f"Failed to pop quote: {e}")
            return None
    
    def pop_quotes_batch(self, batch_size: int = 100, timeout: int = 1) -> List[QuoteData]:
        """Pop multiple quotes from queue."""
        quotes = []
        
        # First pop with blocking
        quote = self.pop_quote(timeout=timeout)
        if quote:
            quotes.append(quote)
            
            # Then pop remaining without blocking
            pipe = self.redis_client.pipeline()
            for _ in range(batch_size - 1):
                pipe.rpop(self.config.QUOTE_QUEUE)
            
            results = pipe.execute()
            for data in results:
                if data:
                    try:
                        quotes.append(QuoteData.from_json(data))
                    except:
                        pass
        
        return quotes
    
    def pop_full_packet(self, timeout: int = 1) -> Optional[FullPacketData]:
        """Pop full packet from queue (blocking)."""
        try:
            result = self.redis_client.brpop(self.config.FULL_QUEUE, timeout=timeout)
            if result:
                _, data = result
                return FullPacketData.from_json(data)
            return None
        except Exception as e:
            logger.error(f"Failed to pop full packet: {e}")
            return None
    
    # ========== Queue Stats ==========
    
    def get_queue_lengths(self) -> Dict[str, int]:
        """Get lengths of all queues."""
        return {
            'ticks': self.redis_client.llen(self.config.TICK_QUEUE),
            'quotes': self.redis_client.llen(self.config.QUOTE_QUEUE),
            'full': self.redis_client.llen(self.config.FULL_QUEUE),
        }
    
    def clear_queues(self):
        """Clear all queues."""
        self.redis_client.delete(
            self.config.TICK_QUEUE,
            self.config.QUOTE_QUEUE,
            self.config.FULL_QUEUE
        )
        logger.info("Cleared all feed queues")
    
    # ========== Latest Price Cache ==========
    
    def set_latest_price(self, security_id: int, data: Dict):
        """Set latest price in Redis hash."""
        key = f"dhan:latest:{security_id}"
        self.redis_client.hset(key, mapping=data)
        self.redis_client.expire(key, 86400)  # Expire after 24h
    
    def get_latest_price(self, security_id: int) -> Optional[Dict]:
        """Get latest price from Redis hash."""
        key = f"dhan:latest:{security_id}"
        data = self.redis_client.hgetall(key)
        return data if data else None
    
    def get_all_latest_prices(self, security_ids: List[int]) -> Dict[int, Dict]:
        """Get latest prices for multiple securities."""
        result = {}
        pipe = self.redis_client.pipeline()
        
        for sid in security_ids:
            pipe.hgetall(f"dhan:latest:{sid}")
        
        responses = pipe.execute()
        for sid, data in zip(security_ids, responses):
            if data:
                result[sid] = data
        
        return result


def test_redis_connection():
    """Test Redis connection."""
    print("\n" + "="*50)
    print("Testing Redis Connection")
    print("="*50)
    
    manager = RedisQueueManager()
    
    if manager.connect():
        print("✅ Redis connection successful")
        
        # Test push/pop
        test_tick = TickData(
            security_id=12345,
            exchange_segment=2,
            ltp=25000.50,
            ltt=int(time.time()),
            received_at=time.time()
        )
        
        manager.push_tick(test_tick)
        print(f"✅ Pushed test tick: {test_tick}")
        
        # Pop it back
        popped = manager.pop_tick(timeout=1)
        if popped:
            print(f"✅ Popped test tick: {popped}")
        
        # Show queue lengths
        lengths = manager.get_queue_lengths()
        print(f"\nQueue lengths: {lengths}")
        
        manager.disconnect()
    else:
        print("❌ Redis connection failed!")
        print("   Make sure Redis is running: redis-server")


if __name__ == "__main__":
    test_redis_connection()
