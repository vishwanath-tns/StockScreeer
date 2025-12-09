"""
Database Writer Service
Consumes tick data from Redis queue and writes to MySQL database.
Supports batching for efficient database writes.
"""

import time
import threading
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from .redis_queue import RedisQueueManager, QuoteData
from .tick_models import create_tick_tables
from .feed_config import FeedConfig

logger = logging.getLogger(__name__)


class DatabaseWriter:
    """
    Writes tick data from Redis queue to MySQL database.
    
    Features:
    - Batch writes for efficiency
    - Upsert to handle duplicates
    - Automatic archiving of old data
    - Reconnection handling
    """
    
    def __init__(
        self,
        db_url: str,
        redis_manager: Optional[RedisQueueManager] = None,
        batch_size: int = 100,
        batch_timeout: float = 1.0,
        max_retries: int = 3
    ):
        """
        Initialize database writer.
        
        Args:
            db_url: SQLAlchemy database URL
            redis_manager: RedisQueueManager instance (creates one if not provided)
            batch_size: Number of ticks to batch before writing
            batch_timeout: Max seconds to wait before flushing batch
            max_retries: Number of retries on database error
        """
        self.db_url = db_url
        self.redis_manager = redis_manager or RedisQueueManager()
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_retries = max_retries
        
        self._engine = None
        self._session_factory = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Statistics
        self._stats = {
            'ticks_received': 0,
            'ticks_written': 0,
            'batches_written': 0,
            'errors': 0,
            'last_write_time': None
        }
        
        # Buffer for batching
        self._buffer: List[QuoteData] = []
        self._buffer_lock = threading.Lock()
        self._last_flush_time = time.time()
        
    def connect(self) -> bool:
        """Connect to database and setup tables."""
        try:
            self._engine = create_engine(
                self.db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=5,
                max_overflow=10
            )
            
            self._session_factory = sessionmaker(bind=self._engine)
            
            # Setup tables if they don't exist
            create_tick_tables()
            
            logger.info("Database writer connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def _get_session(self) -> Session:
        """Get a new database session."""
        return self._session_factory()
    
    def _flush_buffer(self, force: bool = False) -> int:
        """
        Flush buffered ticks to database.
        
        Args:
            force: Force flush even if batch size not reached
            
        Returns:
            Number of ticks written
        """
        with self._buffer_lock:
            # Check if we should flush
            if not self._buffer:
                return 0
            
            time_since_flush = time.time() - self._last_flush_time
            should_flush = (
                force or
                len(self._buffer) >= self.batch_size or
                time_since_flush >= self.batch_timeout
            )
            
            if not should_flush:
                return 0
            
            # Copy and clear buffer
            ticks_to_write = self._buffer.copy()
            self._buffer.clear()
            self._last_flush_time = time.time()
        
        if not ticks_to_write:
            return 0
        
        # Write to database with retries
        for attempt in range(self.max_retries):
            try:
                written = self._write_batch(ticks_to_write)
                self._stats['ticks_written'] += written
                self._stats['batches_written'] += 1
                self._stats['last_write_time'] = datetime.now()
                return written
                
            except Exception as e:
                logger.error(f"Database write error (attempt {attempt + 1}): {e}")
                self._stats['errors'] += 1
                
                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to write {len(ticks_to_write)} ticks after {self.max_retries} attempts")
                    return 0
        
        return 0
    
    def _write_batch(self, quotes: List[QuoteData]) -> int:
        """
        Write a batch of quotes to database using upsert.
        
        Args:
            quotes: List of QuoteData objects
            
        Returns:
            Number of records written
        """
        if not quotes:
            return 0
        
        session = self._get_session()
        try:
            # Group quotes by security_id for efficient upsert
            # Keep only the latest quote for each instrument
            latest_quotes: Dict[tuple, QuoteData] = {}
            for quote in quotes:
                key = (quote.exchange_segment, quote.security_id)
                existing = latest_quotes.get(key)
                if existing is None or quote.ltt >= existing.ltt:
                    latest_quotes[key] = quote
            
            # Build upsert SQL for MySQL - use dhan_quotes table
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
            
            # Prepare parameters from QuoteData objects
            params = []
            for quote in latest_quotes.values():
                params.append({
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
                })
            
            # Execute batch
            for p in params:
                session.execute(sql, p)
            
            session.commit()
            logger.debug(f"Wrote {len(params)} quotes to database")
            return len(params)
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def _add_to_buffer(self, quote: QuoteData):
        """Add a quote to the buffer."""
        with self._buffer_lock:
            self._buffer.append(quote)
            self._stats['ticks_received'] += 1
    
    def _worker_loop(self):
        """Main worker loop that consumes from Redis and writes to DB."""
        logger.info("Database writer worker started")
        
        # Connect to Redis if not already connected
        if not self.redis_manager._connected:
            if not self.redis_manager.connect():
                logger.error("Failed to connect to Redis")
                return
        
        while self._running:
            try:
                # Pop quotes from queue (blocking with timeout)
                quotes = self.redis_manager.pop_quotes_batch(
                    batch_size=self.batch_size,
                    timeout=int(self.batch_timeout)
                )
                
                if quotes:
                    for quote in quotes:
                        self._add_to_buffer(quote)
                
                # Flush buffer if needed
                self._flush_buffer()
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                self._stats['errors'] += 1
                time.sleep(0.1)
        
        # Final flush on shutdown
        self._flush_buffer(force=True)
        logger.info("Database writer worker stopped")
    
    def start(self):
        """Start the database writer in a background thread."""
        if self._running:
            logger.warning("Database writer already running")
            return
        
        if not self._engine:
            if not self.connect():
                raise RuntimeError("Failed to connect to database")
        
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info("Database writer started")
    
    def stop(self, timeout: float = 5.0):
        """Stop the database writer gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping database writer...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("Database writer thread did not stop in time")
        
        logger.info("Database writer stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get writer statistics."""
        return self._stats.copy()
    
    def is_running(self) -> bool:
        """Check if writer is running."""
        return self._running


class TickArchiver:
    """
    Archives old tick data from tick_data to tick_data_archive.
    Should be run periodically (e.g., end of day).
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self._engine = None
    
    def connect(self):
        """Connect to database."""
        self._engine = create_engine(self.db_url, pool_pre_ping=True)
    
    def archive_day(self, date: datetime) -> int:
        """
        Archive all tick data for a specific date.
        
        Args:
            date: Date to archive
            
        Returns:
            Number of records archived
        """
        if not self._engine:
            self.connect()
        
        date_str = date.strftime('%Y-%m-%d')
        
        with self._engine.begin() as conn:
            # Copy to archive
            insert_sql = text("""
                INSERT INTO tick_data_archive 
                    (exchange_segment, security_id, ltp, ltq, ltt, atp, volume,
                     total_sell_qty, total_buy_qty, open_price, close_price,
                     high_price, low_price, oi, oi_day_high, oi_day_low,
                     trade_date, created_at)
                SELECT 
                    exchange_segment, security_id, ltp, ltq, ltt, atp, volume,
                    total_sell_qty, total_buy_qty, open_price, close_price,
                    high_price, low_price, oi, oi_day_high, oi_day_low,
                    DATE(updated_at), updated_at
                FROM tick_data
                WHERE DATE(updated_at) = :date
            """)
            
            result = conn.execute(insert_sql, {'date': date_str})
            archived = result.rowcount
            
            # Delete from main table
            delete_sql = text("""
                DELETE FROM tick_data WHERE DATE(updated_at) = :date
            """)
            conn.execute(delete_sql, {'date': date_str})
            
            logger.info(f"Archived {archived} tick records for {date_str}")
            return archived


if __name__ == "__main__":
    # Test database writer
    import os
    from dotenv import load_dotenv
    from urllib.parse import quote_plus
    
    load_dotenv()
    
    logging.basicConfig(level=logging.DEBUG)
    
    # Database URL - URL-encode password for special characters
    password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
    db_url = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
        f"{password}@"
        f"{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"dhan_trading?charset=utf8mb4"
    )
    
    # Create Redis manager and writer
    redis_manager = RedisQueueManager()
    if redis_manager.connect():
        writer = DatabaseWriter(db_url, redis_manager)
        
        if writer.connect():
            print("Database writer connected!")
            print(f"Stats: {writer.get_stats()}")
        else:
            print("Failed to connect writer")
    else:
        print("Failed to connect to Redis")
