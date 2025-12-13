"""
Test parallel intraday download.
"""
from dhan_trading.data_manager.historical_downloader import HistoricalDownloader
import time

def main():
    print("=" * 60)
    print("Testing Parallel Intraday Download")
    print("=" * 60)
    
    dl = HistoricalDownloader()
    
    # Get stocks
    stocks = dl.get_stocks_to_download()
    stocks = stocks[stocks['security_id'].notna()]
    print(f"\nTotal stocks available: {len(stocks)}")
    
    # Test with first 5 stocks, 1 year data, 2 workers
    print("\n--- Test: 5 stocks, 1 year, 2 workers ---")
    
    # Override the progress for test
    dl.progress.total_stocks = 5
    
    start = time.time()
    
    # Use built-in parallel method
    dl.download_all_intraday(
        years=1,  # Just 1 year for quick test
        chunk_days=90,
        max_workers=2,  # 2 parallel threads
        log_cb=print
    )
    
    elapsed = time.time() - start
    print(f"\n⏱️ Total time: {elapsed:.1f} seconds")
    print(f"📊 Records: {dl.progress.total_candles:,}")

if __name__ == "__main__":
    main()
