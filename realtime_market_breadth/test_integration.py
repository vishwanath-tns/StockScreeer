"""
Integration Test: Real-Time Data Fetcher + Calculator
======================================================

Tests the complete flow:
1. Fetch 1-minute candles from Yahoo Finance
2. Extract LTP and previous close
3. Calculate advance-decline breadth
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.realtime_data_fetcher import RealTimeDataFetcher
from core.realtime_adv_decl_calculator import IntradayAdvDeclCalculator
from core.market_hours_monitor import MarketHoursMonitor
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_integration(test_symbols=None):
    """
    Integration test for real-time system
    
    Args:
        test_symbols: List of symbols to test (defaults to small set)
    """
    # Default test symbols
    if test_symbols is None:
        test_symbols = [
            'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 
            'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS',
            'WIPRO.NS', 'LT.NS', 'AXISBANK.NS', 'MARUTI.NS'
        ]
    
    print("=" * 80)
    print("REAL-TIME ADVANCE-DECLINE SYSTEM - INTEGRATION TEST")
    print("=" * 80)
    
    # Check market status
    monitor = MarketHoursMonitor()
    status = monitor.get_market_status()
    
    print(f"\n📅 Market Status:")
    print(f"   Current Time: {status['timestamp'].strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"   Is Trading Day: {'✅ Yes' if status['is_trading_day'] else '❌ No'}")
    print(f"   Is Market Open: {'✅ Yes' if status['is_open'] else '❌ No'}")
    print(f"   Status: {status['status_text']}")
    
    if not status['is_open']:
        if 'time_to_open' in status:
            hours, remainder = divmod(status['time_to_open'].seconds, 3600)
            minutes = remainder // 60
            print(f"   Time to Open: {hours}h {minutes}m")
        print(f"\n⚠️  Market is currently closed")
        print(f"   Yahoo Finance 1-min data may be stale or unavailable")
        print(f"   Proceeding with test anyway (will use last available data)...\n")
    
    # Initialize fetcher and calculator
    print(f"\n🔧 Initializing components...")
    fetcher = RealTimeDataFetcher(batch_size=6, calls_per_minute=20)
    calculator = IntradayAdvDeclCalculator()
    
    print(f"   ✅ Data Fetcher: batch_size=6, rate_limit=20 calls/min")
    print(f"   ✅ Calculator: In-memory cache initialized")
    
    # Fetch data
    print(f"\n📡 Fetching real-time data for {len(test_symbols)} symbols...")
    print(f"   Using 1-minute candles from Yahoo Finance")
    print(f"   This will take ~{len(test_symbols) / 6 * 3:.0f} seconds due to rate limiting...\n")
    
    start_time = time.time()
    data = fetcher.fetch_realtime_data(test_symbols)
    fetch_time = time.time() - start_time
    
    print(f"\n✅ Fetch completed in {fetch_time:.2f} seconds")
    print(f"   Got data for {len(data)}/{len(test_symbols)} symbols")
    
    if not data:
        print("\n❌ No data received. Test failed.")
        return False
    
    # Update calculator
    print(f"\n🧮 Updating calculator with fetched data...")
    updated = calculator.update_batch(data)
    print(f"   ✅ Updated {updated} stocks in calculator")
    
    # Calculate breadth
    print(f"\n📊 Calculating market breadth metrics...")
    breadth = calculator.calculate_breadth()
    
    print("\n" + "=" * 80)
    print("MARKET BREADTH SUMMARY")
    print("=" * 80)
    print(f"Total Stocks: {breadth['total_stocks']}")
    print(f"Advances:     {breadth['advances']:3d} ({breadth['adv_pct']:6.2f}%) {'🟢' * min(int(breadth['adv_pct'] / 10), 10)}")
    print(f"Declines:     {breadth['declines']:3d} ({breadth['decl_pct']:6.2f}%) {'🔴' * min(int(breadth['decl_pct'] / 10), 10)}")
    print(f"Unchanged:    {breadth['unchanged']:3d} ({breadth['unch_pct']:6.2f}%) {'⚪' * min(int(breadth['unch_pct'] / 10), 10)}")
    print(f"\nA/D Ratio:       {breadth['adv_decl_ratio'] if breadth['adv_decl_ratio'] else 'N/A'}")
    print(f"A/D Difference:  {breadth['adv_decl_diff']:+d}")
    print(f"\nMarket Sentiment: {breadth['market_sentiment']}")
    print(f"Last Update:     {breadth['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Update Count:    {breadth['update_count']}")
    
    # Show individual stocks
    print("\n" + "=" * 80)
    print("INDIVIDUAL STOCK DETAILS")
    print("=" * 80)
    print(f"{'Symbol':<15} {'LTP':>10} {'Prev Close':>10} {'Change':>10} {'Change%':>10} {'Status':>12}")
    print("-" * 80)
    
    for symbol in sorted(data.keys()):
        stock = calculator.get_stock_status(symbol)
        if stock:
            status_emoji = {
                'ADVANCE': '🟢',
                'DECLINE': '🔴',
                'UNCHANGED': '⚪'
            }.get(stock.status, '')
            
            print(f"{symbol:<15} ₹{stock.ltp:>9.2f} ₹{stock.prev_close:>9.2f} "
                  f"₹{stock.change:>9.2f} {stock.change_pct:>9.2f}% "
                  f"{status_emoji} {stock.status}")
    
    # Show top movers
    print("\n" + "=" * 80)
    print("TOP GAINERS")
    print("=" * 80)
    for i, stock in enumerate(calculator.get_top_gainers(5), 1):
        print(f"{i}. {stock.symbol:<15} ₹{stock.ltp:.2f} ({stock.change_pct:+.2f}%)")
    
    print("\n" + "=" * 80)
    print("TOP LOSERS")
    print("=" * 80)
    for i, stock in enumerate(calculator.get_top_losers(5), 1):
        print(f"{i}. {stock.symbol:<15} ₹{stock.ltp:.2f} ({stock.change_pct:+.2f}%)")
    
    # Cache info
    print("\n" + "=" * 80)
    print("CACHE INFORMATION")
    print("=" * 80)
    cache_info = calculator.get_cache_info()
    for key, value in cache_info.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 80)
    print("✅ INTEGRATION TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test real-time advance-decline system')
    parser.add_argument('--large', action='store_true', 
                       help='Test with larger set of symbols (50 stocks)')
    args = parser.parse_args()
    
    if args.large:
        # Test with larger set
        from available_stocks_list import AVAILABLE_STOCKS
        test_symbols = [s for s in AVAILABLE_STOCKS[:50]]
        print(f"\n🔬 Running LARGE TEST with {len(test_symbols)} symbols")
    else:
        test_symbols = None
    
    success = test_integration(test_symbols)
    sys.exit(0 if success else 1)
