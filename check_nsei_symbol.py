"""Check for ^NSEI symbol candles"""
from sqlalchemy import create_engine, text
from datetime import date
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Create engine
password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
eng = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    f"?charset=utf8mb4"
)

conn = eng.connect()
today = date.today()

# Check ^NSEI candles
result = conn.execute(text("""
    SELECT COUNT(*), MIN(candle_timestamp), MAX(candle_timestamp)
    FROM intraday_1min_candles
    WHERE symbol = '^NSEI' AND trade_date = :today
"""), {'today': today})

row = result.fetchone()
count, min_time, max_time = row[0], row[1], row[2]

print(f"Candles for ^NSEI today ({today}):")
print(f"  Count: {count}")
print(f"  First: {min_time}")
print(f"  Last: {max_time}")

if count > 0:
    print("\n✅ SUCCESS: ^NSEI candles ARE being stored!")
    print("   Issue: Code queries for 'NIFTY' but stores as '^NSEI'")
    
    # Show sample
    result2 = conn.execute(text("""
        SELECT candle_timestamp, open_price, high_price, low_price, close_price
        FROM intraday_1min_candles
        WHERE symbol = '^NSEI' AND trade_date = :today
        ORDER BY candle_timestamp
        LIMIT 5
    """), {'today': today})
    
    print("\n  First 5 candles:")
    for row in result2:
        print(f"    {row[0]} | O:{row[1]:.2f} H:{row[2]:.2f} L:{row[3]:.2f} C:{row[4]:.2f}")
else:
    print("\n❌ NO ^NSEI candles either!")

conn.close()
