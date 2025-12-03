"""
Sync missing Nifty 500 symbols to Yahoo Finance database
Downloads historical data for all symbols missing Dec 2, 2025 data
"""
import sys
sys.path.insert(0, '.')

from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import pandas as pd
import time

load_dotenv()

url = URL.create(
    drivername='mysql+pymysql',
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DB', 'marketdata'),
    query={'charset': 'utf8mb4'},
)
engine = create_engine(url)

# Get symbols that need syncing (missing Dec 2 data)
yahoo_symbols = [f'{s}.NS' for s in NIFTY_500_STOCKS]
yahoo_symbols_set = set(yahoo_symbols)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT DISTINCT symbol 
        FROM yfinance_daily_quotes 
        WHERE date = '2025-12-02'
    """))
    symbols_with_dec2 = set(row[0] for row in result.fetchall())

missing_symbols = sorted(yahoo_symbols_set - symbols_with_dec2)
print(f"=" * 70)
print(f"NIFTY 500 DATA SYNC")
print(f"=" * 70)
print(f"Total Nifty 500 symbols: {len(yahoo_symbols)}")
print(f"Symbols with Dec 2 data: {len(symbols_with_dec2)}")
print(f"Symbols to download: {len(missing_symbols)}")
print(f"=" * 70)

if not missing_symbols:
    print("✅ All symbols already have Dec 2 data!")
    sys.exit(0)

# Download in batches
batch_size = 50
total_downloaded = 0
total_failed = 0
failed_symbols = []

start_time = datetime.now()
end_date = datetime.now()
start_date = end_date - timedelta(days=5*365)  # 5 years of history

for i in range(0, len(missing_symbols), batch_size):
    batch = missing_symbols[i:i+batch_size]
    batch_num = i // batch_size + 1
    total_batches = (len(missing_symbols) + batch_size - 1) // batch_size
    
    print(f"\n📦 Batch {batch_num}/{total_batches}: Downloading {len(batch)} symbols...")
    
    for symbol in batch:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date + timedelta(days=1), auto_adjust=False)
            
            if df.empty:
                print(f"   ⚠️ {symbol}: No data returned")
                failed_symbols.append(symbol)
                total_failed += 1
                continue
            
            # Prepare data for insertion
            df = df.reset_index()
            df['symbol'] = symbol
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Adj Close': 'adj_close'
            })
            
            # Select only needed columns
            cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']
            df = df[cols]
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['timeframe'] = 'Daily'
            df['source'] = 'Yahoo Finance'
            
            # Insert into database (upsert)
            with engine.begin() as conn:
                for _, row in df.iterrows():
                    conn.execute(text("""
                        INSERT INTO yfinance_daily_quotes 
                        (symbol, date, open, high, low, close, volume, adj_close, timeframe, source)
                        VALUES (:symbol, :date, :open, :high, :low, :close, :volume, :adj_close, :timeframe, :source)
                        ON DUPLICATE KEY UPDATE
                        open = VALUES(open), high = VALUES(high), low = VALUES(low),
                        close = VALUES(close), volume = VALUES(volume), adj_close = VALUES(adj_close),
                        updated_at = CURRENT_TIMESTAMP
                    """), {
                        'symbol': row['symbol'],
                        'date': row['date'],
                        'open': float(row['open']) if pd.notna(row['open']) else None,
                        'high': float(row['high']) if pd.notna(row['high']) else None,
                        'low': float(row['low']) if pd.notna(row['low']) else None,
                        'close': float(row['close']) if pd.notna(row['close']) else None,
                        'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                        'adj_close': float(row['adj_close']) if pd.notna(row['adj_close']) else None,
                        'timeframe': row['timeframe'],
                        'source': row['source']
                    })
            
            total_downloaded += 1
            print(f"   ✅ {symbol}: {len(df)} records")
            
        except Exception as e:
            print(f"   ❌ {symbol}: {str(e)[:50]}")
            failed_symbols.append(symbol)
            total_failed += 1
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    # Progress update
    elapsed = (datetime.now() - start_time).total_seconds()
    rate = total_downloaded / elapsed if elapsed > 0 else 0
    print(f"   Progress: {total_downloaded}/{len(missing_symbols)} downloaded, {total_failed} failed, {rate:.1f} symbols/sec")

# Final summary
print(f"\n" + "=" * 70)
print("DOWNLOAD COMPLETE")
print("=" * 70)
print(f"✅ Successfully downloaded: {total_downloaded}")
print(f"❌ Failed: {total_failed}")
if failed_symbols:
    print(f"\nFailed symbols:")
    for s in failed_symbols[:20]:
        print(f"   {s}")
    if len(failed_symbols) > 20:
        print(f"   ... and {len(failed_symbols) - 20} more")

elapsed = (datetime.now() - start_time).total_seconds()
print(f"\nTotal time: {elapsed/60:.1f} minutes")
