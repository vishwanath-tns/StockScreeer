"""
Test historical data availability for .NS indices
"""
import yfinance as yf
from datetime import datetime, timedelta

# Test problematic indices
test_symbols = [
    'NIFTY_LARGEMID250.NS',
    'NIFTY_CONSR_DURBL.NS',
    'NIFTY_CPSE.NS',
    'NIFTY_OIL_AND_GAS.NS',
    'NIFTY_HEALTHCARE.NS',
    'NIFTY_MOBILITY.NS',
    'NIFTY_HOUSING.NS',
    'NIFTY100_EQL_WGT.NS',
    'NIFTY200MOMENTM30.NS',
    'NIFTY100_ESG.NS'
]

print("=" * 100)
print("TESTING .NS INDICES HISTORICAL DATA AVAILABILITY")
print("=" * 100)

for symbol in test_symbols:
    print(f"\n📊 {symbol}")
    print("-" * 80)
    
    ticker = yf.Ticker(symbol)
    
    # Try different periods
    for period in ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']:
        try:
            hist = ticker.history(period=period)
            if not hist.empty:
                print(f"  {period:6s} → {len(hist):4d} records | {hist.index[0].date()} to {hist.index[-1].date()}")
                if period == '5y' or period == 'max':
                    break  # Found good data, no need to test further
            else:
                print(f"  {period:6s} → No data")
        except Exception as e:
            print(f"  {period:6s} → Error: {str(e)[:50]}")

print("\n" + "=" * 100)
print("✅ Test Complete")
print("=" * 100)
