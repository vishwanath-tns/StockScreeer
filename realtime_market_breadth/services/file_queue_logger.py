"""
File-Based Queue Logger for 1-Minute Candles
=============================================

Uses pickle files as a fast queue to avoid blocking real-time dashboard.
Separate background process reads queue and writes to database.
"""

import pickle
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class FileQueueLogger:
    """
    Fast file-based queue for 1-minute candle data.
    Writes are instant (pickle to disk), database writes happen separately.
    """
    
    def __init__(self, queue_dir: str = "candle_queue"):
        """
        Initialize file queue logger
        
        Args:
            queue_dir: Directory to store queue files
        """
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(exist_ok=True)
        self.candles_queued = 0
        
        logger.info(f"FileQueueLogger initialized. Queue dir: {self.queue_dir}")
    
    def queue_candles(self, poll_time: datetime, candles_data: List[Dict]) -> bool:
        """
        Queue candles to file (instant operation)
        
        Args:
            poll_time: When this data was polled
            candles_data: List of candle dicts with symbol, OHLCV, prev_close, etc.
            
        Returns:
            True if successful
        """
        try:
            # Create filename with timestamp
            timestamp = poll_time.strftime('%Y%m%d_%H%M%S')
            filename = self.queue_dir / f"candles_{timestamp}.pkl"
            
            # Write to pickle file (fast)
            data = {
                'poll_time': poll_time,
                'trade_date': poll_time.date(),
                'candles': candles_data,
                'count': len(candles_data)
            }
            
            with open(filename, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            self.candles_queued += len(candles_data)
            logger.info(f"Queued {len(candles_data)} candles to {filename.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue candles: {e}", exc_info=True)
            return False
    
    def get_queue_size(self) -> int:
        """Get number of pending queue files"""
        try:
            return len(list(self.queue_dir.glob("candles_*.pkl")))
        except:
            return 0
    
    def get_stats(self) -> Dict:
        """Get queue statistics"""
        return {
            'candles_queued': self.candles_queued,
            'pending_files': self.get_queue_size(),
            'queue_dir': str(self.queue_dir)
        }


def process_queue_files(queue_dir: str = "candle_queue", batch_size: int = 5000):
    """
    Background process to read queue files and write to database.
    Run this separately: python -c "from file_queue_logger import process_queue_files; process_queue_files()"
    
    Args:
        queue_dir: Directory containing queue files
        batch_size: Number of candles to write per database transaction
    """
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    
    load_dotenv()
    
    # Setup database
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        database=os.getenv('MYSQL_DB', 'marketdata'),
        query={"charset": "utf8mb4"},
    )
    
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
    queue_path = Path(queue_dir)
    
    logger.info(f"Queue processor started. Monitoring: {queue_path}")
    
    total_written = 0
    total_files = 0
    
    while True:
        try:
            # Get all queue files
            queue_files = sorted(queue_path.glob("candles_*.pkl"))
            
            if not queue_files:
                logger.info(f"Queue empty. Total written: {total_written} candles from {total_files} files")
                time.sleep(10)  # Wait 10 seconds before checking again
                continue
            
            logger.info(f"Processing {len(queue_files)} queue files...")
            
            for queue_file in queue_files:
                try:
                    # Read queue file
                    with open(queue_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    candles = data['candles']
                    poll_time = data['poll_time']
                    trade_date = data['trade_date']
                    
                    logger.info(f"Processing {queue_file.name}: {len(candles)} candles")
                    
                    # Write in batches
                    for i in range(0, len(candles), batch_size):
                        batch = candles[i:i+batch_size]
                        
                        # Prepare batch data
                        batch_records = []
                        for candle_info in batch:
                            symbol = candle_info['symbol']
                            prev_close = candle_info['prev_close']
                            
                            for candle in candle_info['candles']:
                                batch_records.append({
                                    'poll_time': poll_time,
                                    'trade_date': trade_date,
                                    'symbol': symbol,
                                    'candle_timestamp': candle['timestamp'],
                                    'open_price': candle['open'],
                                    'high_price': candle['high'],
                                    'low_price': candle['low'],
                                    'close_price': candle['ltp'],
                                    'volume': candle.get('volume', 0),
                                    'prev_close': prev_close
                                })
                        
                        # Batch insert
                        if batch_records:
                            with engine.begin() as conn:
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
                                
                                conn.execute(sql, batch_records)
                            
                            total_written += len(batch_records)
                            logger.info(f"  Wrote batch of {len(batch_records)} candles")
                    
                    # Delete processed file
                    queue_file.unlink()
                    total_files += 1
                    logger.info(f"✅ Completed {queue_file.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to process {queue_file}: {e}", exc_info=True)
                    # Move failed file to error directory
                    error_dir = queue_path / "errors"
                    error_dir.mkdir(exist_ok=True)
                    queue_file.rename(error_dir / queue_file.name)
            
        except KeyboardInterrupt:
            logger.info("Queue processor stopped by user")
            break
        except Exception as e:
            logger.error(f"Queue processor error: {e}", exc_info=True)
            time.sleep(5)
    
    engine.dispose()
    logger.info(f"Queue processor finished. Total: {total_written} candles from {total_files} files")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run queue processor
    print("Starting queue processor... Press Ctrl+C to stop")
    process_queue_files()
