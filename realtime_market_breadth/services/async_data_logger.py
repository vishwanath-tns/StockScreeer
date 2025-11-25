"""
Asynchronous Data Logger
=========================

Non-blocking background process for storing intraday data to database.
Uses queue-based architecture to prevent blocking real-time fetches.
"""

import queue
import threading
import time
from datetime import datetime
from typing import Dict, Optional
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class AsyncDataLogger:
    """
    Asynchronous logger that stores data in background thread.
    Real-time fetch sends data to queue and returns immediately.
    Separate thread processes queue and writes to database.
    """
    
    def __init__(self, db_url: Optional[str] = None, queue_size: int = 50000):
        """
        Initialize async logger
        
        Args:
            db_url: Database connection URL (uses env vars if not provided)
            queue_size: Maximum queue size (default 50000 for ~510 stocks × 100 candles)
        """
        self.queue = queue.Queue(maxsize=queue_size)
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.records_logged = 0
        self.errors = 0
        self.batch_size = 1000  # Process 1000 candles per batch
        self.candle_batch = []  # Buffer for batch inserts
        
        # Database connection
        if db_url is None:
            db_url = self._get_db_url_from_env()
        
        self.engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        logger.info(f"AsyncDataLogger initialized with queue size {queue_size}")
    
    def _get_db_url_from_env(self) -> str:
        """Build database URL from environment variables using URL.create"""
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = int(os.getenv('MYSQL_PORT', 3306))
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_DB', 'marketdata')
        
        url = URL.create(
            drivername="mysql+pymysql",
            username=user,
            password=password,
            host=host,
            port=port,
            database=database,
            query={"charset": "utf8mb4"}
        )
        
        return url
    
    def start(self):
        """Start background worker thread"""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            logger.warning("Worker thread already running")
            return
        
        self.stop_event.clear()
        self.worker_thread = threading.Thread(
            target=self._worker,
            name="AsyncDataLogger-Worker",
            daemon=True
        )
        self.worker_thread.start()
        logger.info("Background worker thread started")
    
    def stop(self, timeout: int = 30):
        """
        Stop background worker thread gracefully
        
        Args:
            timeout: Maximum seconds to wait for queue to drain
        """
        logger.info("Stopping background worker...")
        self.stop_event.set()
        
        if self.worker_thread is not None:
            self.worker_thread.join(timeout=timeout)
            if self.worker_thread.is_alive():
                logger.warning(f"Worker thread did not stop within {timeout}s")
            else:
                logger.info("Worker thread stopped successfully")
        
        # Flush any remaining candles
        if self.candle_batch:
            logger.info(f"Flushing {len(self.candle_batch)} remaining candles...")
            self._flush_candle_batch()
        
        logger.info(f"Total records logged: {self.records_logged}, Errors: {self.errors}")
    
    def log_breadth_snapshot(self, breadth_data: Dict, stock_details: Dict[str, Dict]):
        """
        Log market breadth snapshot (non-blocking)
        
        Args:
            breadth_data: Dict from calculator.calculate_breadth()
            stock_details: Dict with symbol -> StockStatus info
        """
        try:
            record = {
                'type': 'breadth_snapshot',
                'timestamp': datetime.now(),
                'data': breadth_data,
                'stock_details': stock_details
            }
            self.queue.put_nowait(record)
            logger.debug("Breadth snapshot queued for logging")
        except queue.Full:
            logger.error("Queue full! Dropping breadth snapshot")
            self.errors += 1
    
    def log_stock_update(self, symbol: str, ltp: float, prev_close: float, 
                        change_pct: float, volume: int, timestamp: datetime):
        """
        Log individual stock update (non-blocking)
        
        Args:
            symbol: Stock symbol
            ltp: Last traded price
            prev_close: Previous close
            change_pct: Change percentage
            volume: Trading volume
            timestamp: Update timestamp
        """
        try:
            record = {
                'type': 'stock_update',
                'timestamp': datetime.now(),
                'symbol': symbol,
                'ltp': ltp,
                'prev_close': prev_close,
                'change_pct': change_pct,
                'volume': volume,
                'data_timestamp': timestamp
            }
            self.queue.put_nowait(record)
        except queue.Full:
            logger.warning(f"Queue full! Dropping stock update for {symbol}")
            self.errors += 1
    
    def log_1min_candle(self, symbol: str, candle_data: Dict, prev_close: float, 
                        poll_time: datetime, trade_date):
        """
        Log raw 1-minute candle data (non-blocking)
        
        Args:
            symbol: Stock symbol
            candle_data: Dict with OHLCV data from fetcher
            prev_close: Previous day close
            poll_time: When this data was polled
            trade_date: Trading date
        """
        try:
            record = {
                'type': '1min_candle',
                'poll_time': poll_time,
                'trade_date': trade_date,
                'symbol': symbol,
                'candle_data': candle_data,
                'prev_close': prev_close
            }
            self.queue.put_nowait(record)
        except queue.Full:
            logger.warning(f"Queue full! Dropping 1-min candle for {symbol}")
            self.errors += 1
    
    def _worker(self):
        """Background worker that processes queue and writes to database"""
        logger.info("Worker thread started, processing queue...")
        
        while not self.stop_event.is_set() or not self.queue.empty():
            try:
                # Get record from queue with timeout
                try:
                    record = self.queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process record
                record_type = record.get('type')
                
                if record_type == 'breadth_snapshot':
                    self._write_breadth_snapshot(record)
                elif record_type == 'stock_update':
                    self._write_stock_update(record)
                elif record_type == '1min_candle':
                    self._write_1min_candle(record)
                else:
                    logger.warning(f"Unknown record type: {record_type}")
                
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing record: {e}", exc_info=True)
                self.errors += 1
        
        logger.info("Worker thread exiting")
    
    def _write_breadth_snapshot(self, record: Dict):
        """Write breadth snapshot to database"""
        try:
            breadth = record['data']
            timestamp = record['timestamp']
            
            # Extract data
            poll_time = timestamp
            trade_date = timestamp.date()
            advances = breadth.get('advances', 0)
            declines = breadth.get('declines', 0)
            unchanged = breadth.get('unchanged', 0)
            total_stocks = breadth.get('total_stocks', 0)
            adv_pct = breadth.get('adv_pct', 0.0)
            decl_pct = breadth.get('decl_pct', 0.0)
            adv_decl_ratio = breadth.get('adv_decl_ratio')
            adv_decl_diff = breadth.get('adv_decl_diff', 0)
            sentiment = breadth.get('market_sentiment', '')
            
            # Skip invalid data with zero advances or declines
            if advances == 0 or declines == 0:
                logger.debug(f"Skipping breadth snapshot with zeros: A={advances}, D={declines}")
                return
            
            # Insert into database
            with self.engine.begin() as conn:
                sql = text("""
                    INSERT INTO intraday_advance_decline 
                    (poll_time, trade_date, advances, declines, unchanged, 
                     total_stocks, adv_pct, decl_pct, adv_decl_ratio, 
                     adv_decl_diff, market_sentiment)
                    VALUES 
                    (:poll_time, :trade_date, :advances, :declines, :unchanged,
                     :total_stocks, :adv_pct, :decl_pct, :adv_decl_ratio,
                     :adv_decl_diff, :market_sentiment)
                """)
                
                conn.execute(sql, {
                    'poll_time': poll_time,
                    'trade_date': trade_date,
                    'advances': advances,
                    'declines': declines,
                    'unchanged': unchanged,
                    'total_stocks': total_stocks,
                    'adv_pct': adv_pct,
                    'decl_pct': decl_pct,
                    'adv_decl_ratio': adv_decl_ratio,
                    'adv_decl_diff': adv_decl_diff,
                    'market_sentiment': sentiment
                })
            
            self.records_logged += 1
            logger.debug(f"Breadth snapshot written: {advances} adv, {declines} decl at {poll_time}")
            
        except Exception as e:
            logger.error(f"Failed to write breadth snapshot: {e}", exc_info=True)
    def _write_stock_update(self, record: Dict):
        """Write individual stock update to database"""
        try:
            with self.engine.begin() as conn:
                sql = text("""
                    INSERT INTO intraday_stock_prices
                    (poll_time, trade_date, symbol, ltp, prev_close, 
                     change_pct, volume, data_timestamp)
                    VALUES
                    (:poll_time, :trade_date, :symbol, :ltp, :prev_close,
                     :change_pct, :volume, :data_timestamp)
                """)
                
                conn.execute(sql, {
                    'poll_time': record['timestamp'],
                    'trade_date': record['timestamp'].date(),
                    'symbol': record['symbol'],
                    'ltp': record['ltp'],
                    'prev_close': record['prev_close'],
                    'change_pct': record['change_pct'],
                    'volume': record['volume'],
                    'data_timestamp': record['data_timestamp']
                })
            
            self.records_logged += 1
            
        except Exception as e:
            logger.error(f"Failed to write stock update for {record.get('symbol')}: {e}")
            self.errors += 1
    
    def _write_1min_candle(self, record: Dict):
        """Buffer 1-minute candle for batch writing"""
        try:
            candle = record['candle_data']
            
            # Add to batch buffer
            self.candle_batch.append({
                'poll_time': record['poll_time'],
                'trade_date': record['trade_date'],
                'symbol': record['symbol'],
                'candle_timestamp': candle.get('timestamp'),
                'open_price': candle.get('open'),
                'high_price': candle.get('high'),
                'low_price': candle.get('low'),
                'close_price': candle.get('ltp'),
                'volume': candle.get('volume', 0),
                'prev_close': record['prev_close']
            })
            
            # Flush batch when it reaches batch_size
            if len(self.candle_batch) >= self.batch_size:
                self._flush_candle_batch()
            
        except Exception as e:
            logger.error(f"Failed to buffer 1-min candle for {record.get('symbol')}: {e}")
            self.errors += 1
    
    def _flush_candle_batch(self):
        """Flush buffered candles to database in a single transaction"""
        if not self.candle_batch:
            return
        
        try:
            with self.engine.begin() as conn:
                sql = text("""
                    INSERT INTO intraday_1min_candles
                    (poll_time, trade_date, symbol, candle_timestamp,
                     open_price, high_price, low_price, close_price, volume, prev_close)
                    VALUES
                    (:poll_time, :trade_date, :symbol, :candle_timestamp,
                     :open_price, :high_price, :low_price, :close_price, :volume, :prev_close)
                    ON DUPLICATE KEY UPDATE
                        open_price = VALUES(open_price),
                        high_price = VALUES(high_price),
                        low_price = VALUES(low_price),
                        close_price = VALUES(close_price),
                        volume = VALUES(volume)
                """)
                
                # Batch insert all candles
                conn.execute(sql, self.candle_batch)
            
            batch_count = len(self.candle_batch)
            self.records_logged += batch_count
            logger.info(f"Flushed {batch_count} candles to database")
            self.candle_batch = []  # Clear buffer
            
        except Exception as e:
            logger.error(f"Failed to flush candle batch: {e}", exc_info=True)
            self.errors += len(self.candle_batch)
            self.candle_batch = []  # Clear to avoid retry loop
    
    def get_stats(self) -> Dict:
        """
        Get logger statistics
        
        Returns:
            Dict with queue size, records logged, errors, etc.
        """
        return {
            'queue_size': self.queue.qsize(),
            'queue_maxsize': self.queue.maxsize,
            'records_logged': self.records_logged,
            'errors': self.errors,
            'worker_alive': self.worker_thread.is_alive() if self.worker_thread else False
        }
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


if __name__ == "__main__":
    # Test the async logger
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Async Data Logger - Test")
    print("=" * 70)
    
    # Create logger
    logger_instance = AsyncDataLogger()
    
    # Start worker
    logger_instance.start()
    
    print("\n✅ Worker thread started")
    
    # Simulate breadth snapshots
    print("\n📊 Simulating breadth snapshots...")
    for i in range(5):
        breadth_data = {
            'advances': 250 + i * 10,
            'declines': 200 - i * 5,
            'unchanged': 50,
            'total_stocks': 500,
            'adv_pct': (250 + i * 10) / 500 * 100,
            'decl_pct': (200 - i * 5) / 500 * 100,
            'adv_decl_ratio': (250 + i * 10) / (200 - i * 5),
            'adv_decl_diff': (250 + i * 10) - (200 - i * 5),
            'market_sentiment': 'BULLISH'
        }
        
        logger_instance.log_breadth_snapshot(breadth_data, {})
        print(f"  Snapshot {i+1} queued")
        time.sleep(0.1)
    
    # Check stats
    print("\n📈 Logger stats:")
    stats = logger_instance.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Wait for queue to drain
    print("\n⏳ Waiting for queue to drain...")
    time.sleep(3)
    
    # Final stats
    print("\n📈 Final stats:")
    stats = logger_instance.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Stop worker
    print("\n🛑 Stopping worker...")
    logger_instance.stop()
    
    print("\n✅ Test complete")
    print("=" * 70)
