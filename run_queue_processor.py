"""
Run Queue Processor
===================

Background process to write queued 1-minute candles to database.
Run this in a separate terminal while the dashboard is running.

Usage:
    python run_queue_processor.py
"""

import logging
from realtime_market_breadth.services.file_queue_logger import process_queue_files

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('queue_processor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Queue Processor Started")
    logger.info("This process will:")
    logger.info("  - Monitor candle_queue/ directory for pickle files")
    logger.info("  - Write queued candles to database in batches")
    logger.info("  - Run continuously until stopped (Ctrl+C)")
    logger.info("="*60)
    
    try:
        process_queue_files(queue_dir="candle_queue", batch_size=5000)
    except KeyboardInterrupt:
        logger.info("\nQueue processor stopped by user")
    except Exception as e:
        logger.error(f"Queue processor failed: {e}", exc_info=True)
