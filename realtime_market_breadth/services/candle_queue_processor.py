"""
Candle Queue Processor - Separate Process
==========================================

Runs as a separate process to write 1-minute candles to database.
Uses multiprocessing.Queue for fast inter-process communication.
"""

import multiprocessing as mp
import time
import logging
from datetime import datetime
from typing import Dict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CandleQueueProcessor:
    """Process candles from queue and write to database in batches"""
    
    def __init__(self, queue: mp.Queue, batch_size: int = 1000):
        """
        Initialize processor
        
        Args:
            queue: Multiprocessing queue to read from
            batch_size: Number of candles to batch before writing
        """
        self.queue = queue
        self.batch_size = batch_size
        self.batch = []
        self.records_written = 0
        self.errors = 0
        self.engine = self._create_engine()
        
    def _create_engine(self):
        """Create database engine"""
        url = URL.create(
            drivername="mysql+pymysql",
            username=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            host=os.getenv('MYSQL_HOST', '127.0.0.1'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            database=os.getenv('MYSQL_DB', 'marketdata'),
            query={"charset": "utf8mb4"},
        )
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=5)
    
    def process_forever(self):
        """Main processing loop - runs until poison pill received"""
        logger.info("Candle queue processor started")
        
        while True:
            try:
                # Get candle from queue (blocking, timeout 5s)
                candle = self.queue.get(timeout=5)
                
                # Check for poison pill (shutdown signal)
                if candle is None:
                    logger.info("Received shutdown signal")
                    self._flush_batch()
                    break
                
                # Add to batch
                self.batch.append(candle)
                
                # Flush if batch is full
                if len(self.batch) >= self.batch_size:
                    self._flush_batch()
                    
            except mp.queues.Empty:
                # No data for 5 seconds, flush what we have
                if self.batch:
                    self._flush_batch()
                continue
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self._flush_batch()
                break
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                self.errors += 1
        
        logger.info(f"Processor stopped. Total written: {self.records_written}, Errors: {self.errors}")
    
    def _flush_batch(self):
        """Write batch to database"""
        if not self.batch:
            return
        
        try:
            start_time = time.time()
            
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
                
                conn.execute(sql, self.batch)
            
            elapsed = time.time() - start_time
            batch_size = len(self.batch)
            self.records_written += batch_size
            
            logger.info(f"✅ Wrote {batch_size} candles to DB in {elapsed:.2f}s "
                       f"(Total: {self.records_written})")
            
            self.batch = []
            
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}", exc_info=True)
            self.errors += len(self.batch)
            self.batch = []


def run_processor(queue: mp.Queue, batch_size: int = 1000):
    """Entry point for multiprocessing"""
    processor = CandleQueueProcessor(queue, batch_size)
    processor.process_forever()


if __name__ == "__main__":
    # For testing
    import multiprocessing as mp
    test_queue = mp.Queue()
    run_processor(test_queue)
