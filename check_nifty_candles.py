from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

eng = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    f"?charset=utf8mb4"
)

conn = eng.connect()
yesterday = (datetime.now() - timedelta(days=2)).date()

# Check NIFTY candles
result = conn.execute(text("""
    SELECT COUNT(*), MIN(candle_timestamp), MAX(candle_timestamp),
           MIN(trade_date), MAX(trade_date)
    FROM intraday_1min_candles
    WHERE symbol = 'NIFTY' AND trade_date >= :yesterday
"""), {'yesterday': yesterday})

row = result.fetchone()
print(f"NIFTY candles count: {row[0]}")
print(f"Timestamp range: {row[1]} to {row[2]}")
print(f"Trade date range: {row[3]} to {row[4]}")

# Check sample data
result2 = conn.execute(text("""
    SELECT candle_timestamp, open_price, high_price, low_price, close_price, trade_date
    FROM intraday_1min_candles
    WHERE symbol = 'NIFTY' AND trade_date >= :yesterday
    ORDER BY candle_timestamp
    LIMIT 10
"""), {'yesterday': yesterday})

print("\nSample NIFTY candles:")
for row in result2:
    print(f"  {row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]} | Date:{row[5]}")

# Check A/D poll times
result3 = conn.execute(text("""
    SELECT COUNT(*), MIN(poll_time), MAX(poll_time)
    FROM intraday_advance_decline
    WHERE trade_date >= :yesterday
"""), {'yesterday': yesterday})

row3 = result3.fetchone()
print(f"\nA/D snapshots count: {row3[0]}")
print(f"Poll time range: {row3[1]} to {row3[2]}")

conn.close()
