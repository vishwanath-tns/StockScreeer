from ranking.db.schema import get_ranking_engine
from sqlalchemy import text

e = get_ranking_engine()
conn = e.connect()

# Check Nifty data
r = conn.execute(text("SELECT date, close FROM yfinance_daily_quotes WHERE symbol = '^NSEI' ORDER BY date DESC LIMIT 5")).fetchall()
print("Nifty data (^NSEI):")
for row in r:
    print(f"  {row[0]}: {row[1]}")

# Check if empty
r2 = conn.execute(text("SELECT COUNT(*) FROM yfinance_daily_quotes WHERE symbol = '^NSEI'")).fetchone()
print(f"\nTotal Nifty records: {r2[0]}")
