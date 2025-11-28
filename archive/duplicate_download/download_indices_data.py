"""
Download daily quotes for indices using nse_yahoo_symbol_map table
"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
import yfinance as yf
from datetime import datetime, timedelta

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

engine = create_db_engine()

print("=" * 80)
print("DOWNLOADING INDEX DATA")
print("=" * 80)

# Get indices from mapping table
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('NIFTY', 'BANKNIFTY', 'SENSEX')
          AND is_active = 1
    """))
    indices = {row[0]: row[1] for row in result}

print(f"\nFound {len(indices)} indices to download:")
for nse, yahoo in indices.items():
    print(f"  {nse:<15} -> {yahoo}")

# Get latest date in yfinance_daily_quotes
with engine.connect() as conn:
    result = conn.execute(text("SELECT MAX(date) FROM yfinance_daily_quotes"))
    latest_date = result.scalar()
    print(f"\nLatest date in database: {latest_date}")

# Download from day after latest date
if latest_date:
    start_date = latest_date + timedelta(days=1)
else:
    start_date = datetime.now().date() - timedelta(days=30)

end_date = datetime.now().date()

print(f"Downloading from {start_date} to {end_date}")
print("\n" + "-" * 80)

# Download each index
for nse_symbol, yahoo_symbol in indices.items():
    print(f"\n📥 Downloading {nse_symbol} ({yahoo_symbol})...")
    
    try:
        # Download data
        ticker = yf.Ticker(yahoo_symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            print(f"  ⚠️  No data available for {nse_symbol}")
            continue
        
        # Prepare for database
        df = df.reset_index()
        df['symbol'] = yahoo_symbol
        df.columns = df.columns.str.lower()
        
        # Rename Date column if needed
        if 'date' not in df.columns and 'index' in df.columns:
            df.rename(columns={'index': 'date'}, inplace=True)
        
        # Insert into database
        with engine.begin() as conn:
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO yfinance_daily_quotes 
                    (symbol, date, open, high, low, close, volume)
                    VALUES (:symbol, :date, :open, :high, :low, :close, :volume)
                    ON DUPLICATE KEY UPDATE
                    open = VALUES(open),
                    high = VALUES(high),
                    low = VALUES(low),
                    close = VALUES(close),
                    volume = VALUES(volume)
                """), {
                    'symbol': yahoo_symbol,
                    'date': row['date'].date(),
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': int(row['volume'])
                })
        
        print(f"  ✅ Downloaded {len(df)} quotes for {nse_symbol}")
        
    except Exception as e:
        print(f"  ❌ Error downloading {nse_symbol}: {e}")

print("\n" + "=" * 80)
print("✅ INDEX DATA DOWNLOAD COMPLETE")
print("=" * 80)

# Verify
with engine.connect() as conn:
    print("\n📊 Quote counts by symbol:")
    result = conn.execute(text("""
        SELECT symbol, COUNT(*) as cnt, MAX(date) as latest
        FROM yfinance_daily_quotes
        WHERE symbol IN ('^NSEI', '^NSEBANK', '^BSESN')
        GROUP BY symbol
        ORDER BY symbol
    """))
    
    for symbol, count, latest in result:
        print(f"  {symbol:<15} {count:>6} quotes (latest: {latest})")
