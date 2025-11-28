"""
Delete and refetch today's NIFTY (^NSEI) intraday data from Yahoo Finance.
"""

from sqlalchemy import create_engine, text
from datetime import date, datetime, timedelta
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
import yfinance as yf
import pandas as pd
import pytz

load_dotenv()

# Database connection
password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
eng = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    f"?charset=utf8mb4"
)

today = date.today()
ist = pytz.timezone('Asia/Kolkata')

print(f"Refetching NIFTY data for {today}")
print("=" * 80)

with eng.begin() as conn:
    # Step 1: Check existing data
    result = conn.execute(text("""
        SELECT COUNT(*), MIN(candle_timestamp), MAX(candle_timestamp)
        FROM intraday_1min_candles
        WHERE symbol = '^NSEI' AND trade_date = :today
    """), {'today': today})
    
    row = result.fetchone()
    old_count = row[0]
    old_min = row[1]
    old_max = row[2]
    
    print(f"\n📊 Existing data for ^NSEI:")
    print(f"   Count: {old_count}")
    print(f"   Range: {old_min} to {old_max}")
    
    # Step 2: Delete today's data
    if old_count > 0:
        result = conn.execute(text("""
            DELETE FROM intraday_1min_candles
            WHERE symbol = '^NSEI' AND trade_date >= DATE_SUB(:today, INTERVAL 1 DAY)
        """), {'today': today})
        print(f"\n🗑️  Deleted candles for last 2 days")
    else:
        print("\n⚠️  No existing data to delete")
    
    # Step 3: Fetch fresh data from Yahoo Finance
    print(f"\n📥 Fetching fresh 2-day data from Yahoo Finance...")
    
    try:
        ticker = yf.Ticker('^NSEI')
        
        # Calculate start and end times for last 2 days of 1-min data
        # Yahoo Finance 1m data is available for up to 7 days
        end_time = datetime.now(ist)
        start_time = end_time - timedelta(days=2)
        
        # Fetch 1-minute data with explicit start and end
        hist = ticker.history(start=start_time, end=end_time, interval='1m')
        
        if hist.empty:
            print("❌ No data returned from Yahoo Finance (market might be closed)")
        else:
            print(f"✅ Fetched {len(hist)} candles from Yahoo Finance")
            
            # Get previous close for today
            result = conn.execute(text("""
                SELECT close
                FROM yfinance_indices_daily_quotes
                WHERE symbol = '^NSEI'
                ORDER BY date DESC
                LIMIT 1
            """))
            prev_close_row = result.fetchone()
            prev_close = float(prev_close_row[0]) if prev_close_row else None
            
            print(f"   Previous close: {prev_close:.2f}" if prev_close else "   Previous close: Not found")
            
            # Prepare candles for insertion
            candles_to_insert = []
            current_time = datetime.now(ist)
            
            for timestamp, row in hist.iterrows():
                # Convert timestamp to IST
                if timestamp.tzinfo is None:
                    candle_time = ist.localize(timestamp.to_pydatetime())
                else:
                    candle_time = timestamp.astimezone(ist)
                
                # Insert candles from yesterday and today
                candle_date = candle_time.date()
                if candle_date >= today - timedelta(days=1):  # Yesterday and today
                    candles_to_insert.append({
                        'poll_time': current_time,
                        'trade_date': candle_date,
                        'symbol': '^NSEI',
                        'candle_timestamp': candle_time,
                        'open_price': float(row['Open']) if not pd.isna(row['Open']) else None,
                        'high_price': float(row['High']) if not pd.isna(row['High']) else None,
                        'low_price': float(row['Low']) if not pd.isna(row['Low']) else None,
                        'close_price': float(row['Close']) if not pd.isna(row['Close']) else None,
                        'volume': int(row['Volume']) if not pd.isna(row['Volume']) else 0,
                        'prev_close': prev_close
                    })
            
            # Step 4: Insert new candles
            if candles_to_insert:
                print(f"\n💾 Inserting {len(candles_to_insert)} candles into database...")
                
                # Batch insert
                conn.execute(text("""
                    INSERT INTO intraday_1min_candles 
                    (poll_time, trade_date, symbol, candle_timestamp, 
                     open_price, high_price, low_price, close_price, volume, prev_close)
                    VALUES 
                    (:poll_time, :trade_date, :symbol, :candle_timestamp,
                     :open_price, :high_price, :low_price, :close_price, :volume, :prev_close)
                    ON DUPLICATE KEY UPDATE
                        open_price = VALUES(open_price),
                        high_price = VALUES(high_price),
                        low_price = VALUES(low_price),
                        close_price = VALUES(close_price),
                        volume = VALUES(volume),
                        poll_time = VALUES(poll_time)
                """), candles_to_insert)
                
                print(f"✅ Successfully inserted {len(candles_to_insert)} candles")
                
                # Show sample
                print(f"\n📈 Sample candles (first 5):")
                for i, candle in enumerate(candles_to_insert[:5]):
                    print(f"   {candle['candle_timestamp']} | "
                          f"O:{candle['open_price']:.2f} "
                          f"H:{candle['high_price']:.2f} "
                          f"L:{candle['low_price']:.2f} "
                          f"C:{candle['close_price']:.2f}")
                
                if len(candles_to_insert) > 5:
                    print(f"   ... and {len(candles_to_insert) - 5} more")
            else:
                print("\n⚠️  No candles to insert (might be before market open)")
    
    except Exception as e:
        print(f"\n❌ Error fetching data: {e}")
        raise

print("\n" + "=" * 80)
print("✅ Done! NIFTY data has been refreshed for today.")
print("   Restart the dashboard to see the updated chart.")
