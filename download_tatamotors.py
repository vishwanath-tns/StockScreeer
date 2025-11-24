"""
Download TATAMOTORS data using new symbol TMCV.NS
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv()

def create_db_engine():
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        database=os.getenv('MYSQL_DB', 'marketdata'),
        query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True)

def download_tatamotors():
    print("=" * 80)
    print("DOWNLOADING TATAMOTORS DATA (TMCV.NS)")
    print("=" * 80)
    
    engine = create_db_engine()
    
    # Get previous close for TATAMOTORS
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT close
            FROM yfinance_daily_quotes
            WHERE symbol = 'TATAMOTORS'
              AND date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE())
            LIMIT 1
        """))
        row = result.fetchone()
        prev_close = float(row[0]) if row else None
    
    print(f"\nPrevious close for TATAMOTORS: ₹{prev_close:.2f}" if prev_close else "\nNo previous close found")
    
    # Download 1-minute data for last 7 days
    print("\nDownloading 1-minute data from Yahoo Finance...")
    
    ticker = yf.Ticker('TMCV.NS')
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    try:
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval='1m',
            actions=False,
            auto_adjust=True
        )
        
        if df.empty:
            print("❌ No data returned from Yahoo Finance")
            return False
        
        print(f"✅ Downloaded {len(df)} candles")
        
        # Prepare data
        df.reset_index(inplace=True)
        df.rename(columns={
            'Datetime': 'candle_timestamp',
            'Open': 'open_price',
            'High': 'high_price',
            'Low': 'low_price',
            'Close': 'close_price',
            'Volume': 'volume'
        }, inplace=True)
        
        df['symbol'] = 'TATAMOTORS'  # Store as TATAMOTORS for consistency
        df['poll_time'] = datetime.now()
        df['trade_date'] = df['candle_timestamp'].dt.date
        df['prev_close'] = prev_close
        
        df = df[['poll_time', 'trade_date', 'symbol', 'candle_timestamp',
                 'open_price', 'high_price', 'low_price', 'close_price', 
                 'volume', 'prev_close']]
        
        print(f"\nData breakdown:")
        print(f"  Date range: {df['trade_date'].min()} to {df['trade_date'].max()}")
        print(f"  Trading days: {df['trade_date'].nunique()}")
        print(f"  Candles per day: {len(df) / df['trade_date'].nunique():.0f}")
        
        # Store to database
        print("\n💾 Storing to database...")
        
        with engine.begin() as conn:
            # Create temp table
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_tatamotors LIKE intraday_1min_candles
            """))
        
        # Bulk insert to temp
        df.to_sql(
            name='tmp_tatamotors',
            con=engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        # Upsert to main table
        with engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO intraday_1min_candles
                (poll_time, trade_date, symbol, candle_timestamp,
                 open_price, high_price, low_price, close_price, volume, prev_close)
                SELECT 
                    poll_time, trade_date, symbol, candle_timestamp,
                    open_price, high_price, low_price, close_price, volume, prev_close
                FROM tmp_tatamotors
                ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    prev_close = VALUES(prev_close)
            """))
            
            rows = result.rowcount
            print(f"✅ Stored {rows} candles to database")
        
        # Verify
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM intraday_1min_candles 
                WHERE symbol = 'TATAMOTORS'
            """))
            total = result.scalar()
            print(f"\n✅ Total TATAMOTORS candles in database: {total:,}")
        
        print("\n" + "=" * 80)
        print("✅ TATAMOTORS DATA SUCCESSFULLY ADDED!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error downloading data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        engine.dispose()

if __name__ == "__main__":
    download_tatamotors()
