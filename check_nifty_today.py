"""Check NIFTY intraday data for today"""
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Create engine with URL-encoded password (handles special characters like @@)
password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
eng = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    f"?charset=utf8mb4"
)

conn = eng.connect()
today = date.today()

print(f"Checking NIFTY data for {today}...")
print("=" * 80)

# Check if NIFTY has any candles today
result = conn.execute(text("""
    SELECT COUNT(*), MIN(candle_timestamp), MAX(candle_timestamp)
    FROM intraday_1min_candles
    WHERE symbol = 'NIFTY' AND trade_date = :today
"""), {'today': today})

row = result.fetchone()
count, min_time, max_time = row[0], row[1], row[2]

print(f"\n📊 NIFTY Candles Today ({today}):")
print(f"   Count: {count}")
print(f"   First candle: {min_time}")
print(f"   Last candle: {max_time}")

if count == 0:
    print("\n❌ NO NIFTY CANDLES FOUND FOR TODAY!")
    print("\nPossible reasons:")
    print("1. Market hasn't opened yet (opens 9:15 AM)")
    print("2. No refresh has been done yet today")
    print("3. NIFTY is missing prev_close (candles not queued)")
    print("4. Candle processor not running")
else:
    print(f"\n✅ NIFTY has {count} candles stored for today")
    
    # Show sample candles
    result2 = conn.execute(text("""
        SELECT candle_timestamp, open_price, high_price, low_price, close_price, volume
        FROM intraday_1min_candles
        WHERE symbol = 'NIFTY' AND trade_date = :today
        ORDER BY candle_timestamp
        LIMIT 10
    """), {'today': today})
    
    print("\n📈 First 10 candles:")
    for row in result2:
        print(f"   {row[0]} | O:{row[1]:.2f} H:{row[2]:.2f} L:{row[3]:.2f} C:{row[4]:.2f} V:{row[5]}")

# Check A/D data for today
result3 = conn.execute(text("""
    SELECT COUNT(*), MIN(poll_time), MAX(poll_time)
    FROM intraday_advance_decline
    WHERE trade_date = :today
"""), {'today': today})

row3 = result3.fetchone()
ad_count, ad_min, ad_max = row3[0], row3[1], row3[2]

print(f"\n📊 Advance-Decline Snapshots Today:")
print(f"   Count: {ad_count}")
print(f"   First: {ad_min}")
print(f"   Last: {ad_max}")

if ad_count > 0 and count == 0:
    print("\n⚠️ WARNING: A/D data exists but NO NIFTY candles!")
    print("   This confirms NIFTY candles are not being stored.")

# Check if ^NSEI has prev_close in yfinance_indices_daily_quotes
result4 = conn.execute(text("""
    SELECT date, close
    FROM yfinance_indices_daily_quotes
    WHERE symbol = '^NSEI'
    ORDER BY date DESC
    LIMIT 5
"""))

print(f"\n📊 ^NSEI Previous Close History:")
rows = result4.fetchall()
if rows:
    for row in rows:
        print(f"   {row[0]}: {row[1]:.2f}")
    
    yesterday = rows[0][0]
    if yesterday < today:
        print(f"\n✅ ^NSEI has prev_close data (latest: {yesterday})")
    else:
        print(f"\n⚠️ ^NSEI prev_close might not be available for today's calculation")
else:
    print("   ❌ NO ^NSEI DATA FOUND in yfinance_indices_daily_quotes!")
    print("   This is why NIFTY candles can't be stored!")

conn.close()

print("\n" + "=" * 80)
print("\nDiagnosis:")
if count == 0 and ad_count > 0:
    print("❌ Issue confirmed: NIFTY candles NOT being stored despite fetches happening")
    if not rows:
        print("   Root cause: ^NSEI missing from yfinance_indices_daily_quotes")
        print("   Fix: Run download script to populate ^NSEI historical data")
    else:
        print("   Root cause: Unknown - need to check real-time logs")
elif count == 0 and ad_count == 0:
    print("ℹ️ No data today yet - app hasn't been run or market not open")
else:
    print("✅ NIFTY data is being stored correctly!")
