"""
Dhan Market Feed Service
========================
Real-time market data feed via Dhan WebSocket.

Architecture:
1. WebSocket Feed Service - Connects to Dhan, pushes data to Redis
2. Database Writer Service - Consumes from Redis, writes to MySQL

Usage:
    # Start the service from command line:
    python -m dhan_trading.market_feed.launcher --mode quote --force
    
    # Or programmatically:
    from dhan_trading.market_feed import MarketFeedLauncher, FeedMode
    launcher = MarketFeedLauncher(feed_mode=FeedMode.QUOTE)
    launcher.start()
"""

__version__ = "0.1.0"

from .feed_config import (
    FeedConfig, 
    FeedMode, 
    ExchangeSegment, 
    FeedRequestCode,
    FeedResponseCode
)
from .tick_models import create_tick_tables
from .redis_queue import RedisQueueManager, TickData, QuoteData, FullPacketData
from .feed_service import DhanFeedService, BinaryParser
from .db_writer import DatabaseWriter, TickArchiver
from .instrument_selector import InstrumentSelector
from .launcher import MarketFeedLauncher

__all__ = [
    # Config
    'FeedConfig',
    'FeedMode',
    'ExchangeSegment',
    'FeedRequestCode',
    'FeedResponseCode',
    # Models
    'create_tick_tables',
    # Queue
    'RedisQueueManager',
    'TickData',
    'QuoteData',
    'FullPacketData',
    # Services
    'DhanFeedService',
    'BinaryParser',
    'DatabaseWriter',
    'TickArchiver',
    'InstrumentSelector',
    'MarketFeedLauncher',
]
