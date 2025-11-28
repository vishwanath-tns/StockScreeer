"""
Get stocks that actually have Yahoo Finance data
"""
from sync_bhav_gui import engine
import pandas as pd
from sqlalchemy import text

eng = engine()

# Get all stocks with recent data (exclude NIFTY index itself)
query = text("""
SELECT 
    symbol,
    COUNT(*) as data_points,
    MIN(date) as first_date,
    MAX(date) as latest_date
FROM yfinance_daily_quotes 
WHERE symbol != 'NIFTY'
    AND close IS NOT NULL
GROUP BY symbol
HAVING COUNT(*) > 100  -- At least 100 days of data
    AND MAX(date) >= '2025-11-01'  -- Recent data available
ORDER BY data_points DESC
""")

df = pd.read_sql(query, eng)

print("=" * 70)
print("Stocks with Yahoo Finance Data (Nov 2025)")
print("=" * 70)
print(f"\nTotal stocks with data: {len(df)}")
print(f"Data points range: {df['data_points'].min()} to {df['data_points'].max()}")
print(f"\nFirst 50 stocks (most data):")
print(df.head(50)[['symbol', 'data_points', 'latest_date']])

# Save to file
with open('available_stocks_list.py', 'w') as f:
    f.write('"""\n')
    f.write('Stocks Available in Yahoo Finance Database\n')
    f.write('=' * 50 + '\n')
    f.write(f'Total stocks: {len(df)}\n')
    f.write(f'Generated: 2025-11-24\n')
    f.write('These stocks have at least 100 days of data and recent updates.\n')
    f.write('"""\n\n')
    f.write('AVAILABLE_STOCKS = [\n')
    
    symbols = df['symbol'].tolist()
    for i in range(0, len(symbols), 10):
        batch = symbols[i:i+10]
        f.write('    ')
        f.write(', '.join([f"'{s}'" for s in batch]))
        f.write(',\n')
    
    f.write(']\n')

print(f"\n✅ Created 'available_stocks_list.py' with {len(df)} stocks")

eng.dispose()
