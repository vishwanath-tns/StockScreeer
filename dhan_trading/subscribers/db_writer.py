"""
Database Writer Subscriber
==========================
Subscribes to Redis and writes market data to MySQL database.

This is a standalone service - separate from the feed publisher.

Usage:
    python -m dhan_trading.subscribers.db_writer
"""
import os
import sys
import signal
import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus
from collections import defaultdict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from dhan_trading.market_feed.redis_subscriber import (
    RedisSubscriber, CHANNEL_QUOTES, CHANNEL_TICKS, CHANNEL_DEPTH
)
from dhan_trading.market_feed.redis_publisher import QuoteData, TickData, DepthData
from dhan_trading.market_feed.tick_models import create_tick_tables

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseWriterSubscriber(RedisSubscriber):
    """
    Subscribes to Redis and writes quotes to MySQL.
    
    Features:
    - Batch writes for efficiency
    - Keeps only latest quote per instrument (for dhan_quotes)
    - Handles reconnection
    """
    
    def __init__(self, db_url: str, batch_size: int = 50, flush_interval: float = 1.0):
        """
        Initialize DB writer.
        
        Args:
            db_url: SQLAlchemy database URL
            batch_size: Max quotes to batch before writing
            flush_interval: Max seconds between flushes
        """
        super().__init__()
        
        self.db_url = db_url
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Database
        self._engine = None
        self._session_factory = None
        
        # Buffer for batching - only keep latest per instrument
        self._quote_buffer: Dict[int, QuoteData] = {}
        self._buffer_lock = threading.Lock()
        self._last_flush_time = time.time()
        
        # Stats
        self._db_stats = {
            'quotes_written': 0,
            'batches_written': 0,
            'errors': 0
        }
        
        # Background flush thread
        self._flush_thread: Optional[threading.Thread] = None
        self._flush_running = False
    
    def connect_db(self) -> bool:
        """Connect to database."""
        try:
            self._engine = create_engine(
                self.db_url,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            self._session_factory = sessionmaker(bind=self._engine)
            
            # Test connection
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def setup_tables(self):
        """Ensure database tables exist."""
        logger.info("Setting up database tables...")
        create_tick_tables()
        logger.info("Database tables ready")
    
    def on_quote(self, quote: QuoteData):
        """Handle incoming quote - buffer for batch write."""
        with self._buffer_lock:
            # Only keep latest quote per security_id
            self._quote_buffer[quote.security_id] = quote
            
            # Flush if buffer is full
            if len(self._quote_buffer) >= self.batch_size:
                self._flush_buffer()
    
    def _flush_buffer(self):
        """Flush buffered quotes to database."""
        with self._buffer_lock:
            if not self._quote_buffer:
                return
            
            quotes_to_write = list(self._quote_buffer.values())
            self._quote_buffer.clear()
        
        self._write_quotes(quotes_to_write)
        self._last_flush_time = time.time()
    
    def _write_quotes(self, quotes: List[QuoteData]):
        """Write quotes to database."""
        if not quotes:
            return
        
        try:
            session = self._session_factory()
            
            # Build upsert SQL
            sql = text("""
                INSERT INTO dhan_quotes (
                    exchange_segment, security_id, ltp, ltq, ltt, 
                    atp, volume, total_sell_qty, total_buy_qty,
                    day_open, day_close, day_high, day_low,
                    open_interest
                ) VALUES (
                    :exchange_segment, :security_id, :ltp, :ltq, :ltt,
                    :atp, :volume, :total_sell_qty, :total_buy_qty,
                    :day_open, :day_close, :day_high, :day_low,
                    :open_interest
                )
            """)
            
            for quote in quotes:
                params = {
                    'exchange_segment': quote.exchange_segment,
                    'security_id': quote.security_id,
                    'ltp': quote.ltp,
                    'ltq': quote.ltq,
                    'ltt': quote.ltt,
                    'atp': quote.atp,
                    'volume': quote.volume,
                    'total_sell_qty': quote.total_sell_qty,
                    'total_buy_qty': quote.total_buy_qty,
                    'day_open': quote.day_open,
                    'day_close': quote.day_close,
                    'day_high': quote.day_high,
                    'day_low': quote.day_low,
                    'open_interest': quote.open_interest or 0
                }
                session.execute(sql, params)
            
            session.commit()
            
            self._db_stats['quotes_written'] += len(quotes)
            self._db_stats['batches_written'] += 1
            
            logger.info(f"Wrote {len(quotes)} quotes to database "
                       f"(total: {self._db_stats['quotes_written']})")
            
        except Exception as e:
            logger.error(f"Database write error: {e}")
            self._db_stats['errors'] += 1
            session.rollback()
        finally:
            session.close()
    
    def _flush_loop(self):
        """Background thread to periodically flush buffer."""
        while self._flush_running:
            time.sleep(0.5)  # Check every 500ms
            
            now = time.time()
            if now - self._last_flush_time >= self.flush_interval:
                self._flush_buffer()
    
    def start(self):
        """Start the subscriber with background flush."""
        # Connect to database first
        if not self.connect_db():
            raise RuntimeError("Failed to connect to database")
        
        # Setup tables
        self.setup_tables()
        
        # Connect to Redis
        if not self.connect():
            raise RuntimeError("Failed to connect to Redis")
        
        # Subscribe to quotes channel
        self.subscribe([CHANNEL_QUOTES])
        
        # Start background flush thread
        self._flush_running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        
        logger.info("=" * 60)
        logger.info("Database Writer Subscriber is RUNNING")
        logger.info(f"  Batch Size: {self.batch_size}")
        logger.info(f"  Flush Interval: {self.flush_interval}s")
        logger.info("  Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # Run the subscriber (blocking)
        self.run(blocking=True)
    
    def stop(self):
        """Stop the subscriber."""
        logger.info("Stopping DB Writer...")
        
        # Stop flush thread
        self._flush_running = False
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=2)
        
        # Final flush
        self._flush_buffer()
        
        # Print stats
        logger.info("=" * 60)
        logger.info("Final Statistics:")
        logger.info(f"  Quotes Written: {self._db_stats['quotes_written']}")
        logger.info(f"  Batches Written: {self._db_stats['batches_written']}")
        logger.info(f"  Errors: {self._db_stats['errors']}")
        logger.info("=" * 60)
        
        # Disconnect
        super().stop()
        
        if self._engine:
            self._engine.dispose()
        
        logger.info("DB Writer stopped")
    
    def get_db_stats(self) -> Dict:
        """Get database writer statistics."""
        return {
            **self.get_stats(),
            **self._db_stats
        }


def build_db_url() -> str:
    """Build database URL from environment variables."""
    password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
    return (
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
        f"{password}@"
        f"{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"dhan_trading?charset=utf8mb4"
    )


def main():
    """Run the database writer subscriber."""
    print("=" * 60)
    print("Database Writer Subscriber")
    print("=" * 60)
    print()
    
    db_url = build_db_url()
    
    writer = DatabaseWriterSubscriber(
        db_url=db_url,
        batch_size=50,
        flush_interval=1.0
    )
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n")
        writer.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        writer.start()
    except Exception as e:
        logger.error(f"Error: {e}")
        writer.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
