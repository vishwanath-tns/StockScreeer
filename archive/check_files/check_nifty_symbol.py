from sync_bhav_gui import engine
import pandas as pd
from sqlalchemy import text

eng = engine()

# Check what symbols we have
query = text("SELECT DISTINCT symbol FROM yfinance_daily_quotes ORDER BY symbol LIMIT 20")
df = pd.read_sql(query, eng)
print("First 20 symbols in yfinance_daily_quotes:")
print(df)

# Check if NIFTY exists
query2 = text("SELECT COUNT(*) as count FROM yfinance_daily_quotes WHERE symbol LIKE '%NIFTY%'")
df2 = pd.read_sql(query2, eng)
print(f"\n\nRecords with 'NIFTY' in symbol: {df2['count'][0]}")

# Check for specific variations
for symbol in ['NIFTY', 'NIFTY50', '^NSEI', 'NSEI', 'NIFTY.NS']:
    query3 = text(f"SELECT COUNT(*) as count FROM yfinance_daily_quotes WHERE symbol = '{symbol}'")
    df3 = pd.read_sql(query3, eng)
    print(f"Symbol '{symbol}': {df3['count'][0]} records")

eng.dispose()
