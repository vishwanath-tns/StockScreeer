"""
Quick test to verify the Nifty 500 import works correctly in the dashboard context
"""

import sys
import os

# Add parent directory to path (same as dashboard does)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from nifty500_stocks_list import NIFTY_500_STOCKS
    print(f"✅ Successfully imported NIFTY_500_STOCKS")
    print(f"   Total symbols: {len(NIFTY_500_STOCKS)}")
    
    # Simulate what the dashboard does
    yahoo_symbols = [f"{symbol}.NS" for symbol in NIFTY_500_STOCKS]
    if '^NSEI' not in yahoo_symbols:
        yahoo_symbols.append('^NSEI')
    
    print(f"\n✅ Dashboard would load: {len(yahoo_symbols)} symbols")
    print(f"   Expected: 501 (500 Nifty stocks + NIFTY index)")
    
    if len(yahoo_symbols) == 501:
        print(f"\n🎉 SUCCESS! The dashboard should load all 500 Nifty stocks!")
    else:
        print(f"\n⚠️ WARNING! Expected 501 but got {len(yahoo_symbols)}")
        
except ImportError as e:
    print(f"❌ Failed to import NIFTY_500_STOCKS: {e}")
    print(f"   Make sure nifty500_stocks_list.py exists in the same directory")
