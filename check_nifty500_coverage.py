"""
Check Nifty 500 coverage in yfinance_daily_quotes
"""
from sync_bhav_gui import engine
from nifty500_stocks_list import NIFTY_500_STOCKS
import pandas as pd
from sqlalchemy import text

eng = engine()

# Check overall coverage
symbols_str = ','.join([f"'{s}'" for s in NIFTY_500_STOCKS])

query = f"""
SELECT 
    COUNT(DISTINCT symbol) as symbols_with_data,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM yfinance_daily_quotes 
WHERE symbol IN ({symbols_str})
"""

result = pd.read_sql(query, eng)
print("=" * 70)
print("Nifty 500 Coverage Analysis")
print("=" * 70)
print(f"\nTotal Nifty 500 stocks in list: {len(NIFTY_500_STOCKS)}")
print(f"Stocks with data in yfinance_daily_quotes: {result['symbols_with_data'][0]}")
print(f"Missing from database: {len(NIFTY_500_STOCKS) - result['symbols_with_data'][0]}")
print(f"Date range: {result['earliest_date'][0]} to {result['latest_date'][0]}")

# Check which symbols are missing
query2 = f"""
SELECT DISTINCT symbol 
FROM yfinance_daily_quotes 
WHERE symbol IN ({symbols_str})
ORDER BY symbol
"""
found_symbols = pd.read_sql(query2, eng)
found_set = set(found_symbols['symbol'].tolist())
nifty500_set = set(NIFTY_500_STOCKS)
missing_symbols = nifty500_set - found_set

print(f"\n\n📊 Missing Symbols ({len(missing_symbols)} symbols):")
print("-" * 70)
missing_list = sorted(list(missing_symbols))
for i in range(0, len(missing_list), 10):
    print(', '.join(missing_list[i:i+10]))

# Check data availability for a recent date
print("\n\n📅 Data availability for 2025-11-21:")
print("-" * 70)
query3 = f"""
SELECT COUNT(*) as count
FROM yfinance_daily_quotes 
WHERE symbol IN ({symbols_str})
    AND date = '2025-11-21'
    AND close IS NOT NULL
"""
recent_count = pd.read_sql(query3, eng)
print(f"Stocks with data on 2025-11-21: {recent_count['count'][0]}")

# Sample some symbols with data
print("\n\n✅ Sample symbols WITH data (first 20):")
print("-" * 70)
print(', '.join(sorted(list(found_set))[:20]))

print("\n\n❌ Sample symbols WITHOUT data (first 20):")
print("-" * 70)
print(', '.join(missing_list[:20]))

eng.dispose()
