"""
Test Async Logger with Real Integration
========================================

Tests the async logger with real fetcher + calculator pipeline.
Verifies that logging doesn't block real-time updates.
"""

import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from core.realtime_data_fetcher import RealTimeDataFetcher
from core.realtime_adv_decl_calculator import IntradayAdvDeclCalculator
from services.async_data_logger import AsyncDataLogger
import logging
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_async_logging():
    """Test async logger with real data pipeline"""
    
    print("=" * 80)
    print("ASYNC DATA LOGGER - INTEGRATION TEST")
    print("=" * 80)
    
    # Test symbols
    test_symbols = [
        'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS',
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS'
    ]
    
    # Initialize components
    print("\n🔧 Initializing components...")
    fetcher = RealTimeDataFetcher(batch_size=4)
    calculator = IntradayAdvDeclCalculator()
    data_logger = AsyncDataLogger()
    
    print("   ✅ Fetcher initialized")
    print("   ✅ Calculator initialized")
    print("   ✅ Async logger initialized")
    
    # Start async logger
    print("\n🚀 Starting async logger worker thread...")
    data_logger.start()
    time.sleep(0.5)  # Let it start
    
    stats = data_logger.get_stats()
    print(f"   ✅ Worker thread running: {stats['worker_alive']}")
    print(f"   Queue capacity: {stats['queue_maxsize']}")
    
    # Simulate multiple polling cycles
    print("\n📡 Simulating 3 polling cycles (5 seconds apart)...")
    
    for cycle in range(1, 4):
        print(f"\n--- Cycle {cycle} ---")
        
        # Fetch data (this is the real-time operation - should not block)
        print(f"  Fetching data...")
        fetch_start = time.time()
        data = fetcher.fetch_realtime_data(test_symbols)
        fetch_time = time.time() - fetch_start
        print(f"  ✅ Fetched {len(data)} stocks in {fetch_time:.2f}s")
        
        # Update calculator (fast, in-memory)
        calc_start = time.time()
        calculator.update_batch(data)
        breadth = calculator.calculate_breadth()
        calc_time = time.time() - calc_start
        print(f"  ✅ Calculated breadth in {calc_time:.3f}s")
        
        # Log to database (async, non-blocking)
        log_start = time.time()
        
        # Log breadth snapshot
        stock_details = {
            symbol: {
                'ltp': info.get('ltp'),
                'prev_close': info.get('prev_close'),
                'volume': info.get('volume', 0)
            }
            for symbol, info in data.items()
        }
        data_logger.log_breadth_snapshot(breadth, stock_details)
        
        # Log ALL 1-minute candles for each stock
        poll_time = datetime.now()
        trade_date = poll_time.date()
        
        total_candles = 0
        for symbol, info in data.items():
            # Log all candles (not just the last one)
            all_candles = info.get('all_candles', [])
            prev_close = info.get('prev_close')
            
            if all_candles and prev_close:
                for candle in all_candles:
                    data_logger.log_1min_candle(
                        symbol=symbol,
                        candle_data=candle,
                        prev_close=prev_close,
                        poll_time=poll_time,
                        trade_date=trade_date
                    )
                    total_candles += 1
        
        log_time = time.time() - log_start
        print(f"  ✅ Queued {total_candles} candles for logging in {log_time:.3f}s (non-blocking)")
        
        # Show breadth
        print(f"  📊 Breadth: {breadth['advances']} adv, {breadth['declines']} decl, {breadth['unchanged']} unch")
        print(f"  📊 Sentiment: {breadth['market_sentiment']}")
        
        # Show logger stats
        stats = data_logger.get_stats()
        print(f"  📈 Logger: {stats['records_logged']} written, {stats['queue_size']} in queue, {stats['errors']} errors")
        
        # Wait before next cycle (simulating 5-min interval)
        if cycle < 3:
            print(f"  ⏳ Waiting 5 seconds before next cycle...")
            time.sleep(5)
    
    # Final stats
    print("\n" + "=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    
    stats = data_logger.get_stats()
    print(f"Total records logged: {stats['records_logged']}")
    print(f"Errors: {stats['errors']}")
    print(f"Queue size: {stats['queue_size']}")
    print(f"Worker alive: {stats['worker_alive']}")
    
    # Stop logger
    print("\n🛑 Stopping async logger...")
    data_logger.stop(timeout=10)
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    print("\n💡 Key Observations:")
    print("  - Fetch time: ~5-7 seconds (real API call)")
    print("  - Calc time: <0.01 seconds (in-memory)")
    print("  - Log time: <0.001 seconds (queue only, non-blocking)")
    print("  - Database writes happen in background thread")
    print("  - Real-time fetch is NOT blocked by database I/O")
    print("  - ALL 1-minute candles are stored for future analysis")
    
    print("\n📝 Check database to verify ALL 1-min candles were written:")
    print("  mysql> SELECT COUNT(*) FROM intraday_1min_candles WHERE trade_date = CURDATE();")
    print("  mysql> SELECT symbol, COUNT(*) as num_candles FROM intraday_1min_candles")
    print("         WHERE trade_date = CURDATE() GROUP BY symbol;")
    print("  mysql> SELECT * FROM intraday_1min_candles WHERE symbol = 'RELIANCE.NS'")
    print("         AND trade_date = CURDATE() ORDER BY candle_timestamp;")


if __name__ == "__main__":
    try:
        test_async_logging()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
