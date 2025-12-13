#!/usr/bin/env python3
"""
Run daily historical data download for all stocks.
Downloads 20 years of daily OHLCV data from Dhan API.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dhan_trading.data_manager.historical_downloader import HistoricalDownloader
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_download.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main download function."""
    logger.info("=" * 60)
    logger.info("Starting daily historical data download")
    logger.info("=" * 60)
    
    downloader = HistoricalDownloader()
    
    # Get current stats
    stats = downloader.get_download_stats()
    logger.info(f"Current stats: {stats}")
    
    # First ensure all security IDs are populated
    missing_ids = downloader.get_missing_security_ids()
    if missing_ids:
        logger.info(f"Found {len(missing_ids)} symbols without security ID, looking up...")
        updated = downloader.lookup_security_ids_from_instruments()
        logger.info(f"Updated {updated} security IDs")
    
    # Download all daily data (20 years)
    logger.info("Starting download of 20 years daily data for all stocks...")
    downloader.download_all_daily(years=20, log_cb=logger.info)
    
    logger.info("=" * 60)
    logger.info("Download complete!")
    logger.info("=" * 60)
    
    # Final stats
    final_stats = downloader.get_download_stats()
    logger.info(f"Final stats: {final_stats}")
    
    return total_downloaded


if __name__ == "__main__":
    main()
