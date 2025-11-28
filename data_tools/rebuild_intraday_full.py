"""
Complete Intraday Data Rebuild Script
======================================

This script will:
1. Clear all existing intraday data
2. Download 1-minute data for all Nifty 500 stocks + Nifty index
3. Recalculate advance-decline metrics
4. Store everything in the database

Usage:
    python rebuild_intraday_full.py --days 7
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import argparse
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


def create_db_engine():
    """Create SQLAlchemy engine"""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        database=os.getenv('MYSQL_DB', 'marketdata'),
        query={"charset": "utf8mb4"}
    )
    
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600, echo=False)


def clear_intraday_data(engine):
    """Clear existing intraday data"""
    print("\n" + "=" * 70)
    print("🗑️  STEP 1: CLEARING EXISTING DATA")
    print("=" * 70)
    
    with engine.begin() as conn:
        # Clear candles
        result = conn.execute(text("DELETE FROM intraday_1min_candles"))
        print(f"✅ Deleted {result.rowcount} candles from intraday_1min_candles")
        
        # Clear advance-decline
        result = conn.execute(text("DELETE FROM intraday_advance_decline"))
        print(f"✅ Deleted {result.rowcount} records from intraday_advance_decline")


def get_symbols(engine) -> List[str]:
    """Get all active Yahoo symbols"""
    query = text("""
        SELECT yahoo_symbol 
        FROM nse_yahoo_symbol_map 
        WHERE is_active = 1 
        ORDER BY yahoo_symbol
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        symbols = [row[0] for row in result]
    
    # Add Nifty index
    symbols.append('^NSEI')
    
    return symbols


def get_previous_close_cache(engine, symbols: List[str]) -> Dict[str, float]:
    """Get previous close prices for all symbols"""
    print("\n📊 Loading previous close prices from database...")
    
    # Remove ^NSEI from query (it's not in the quotes table with that symbol)
    stock_symbols = [s for s in symbols if s != '^NSEI']
    
    if not stock_symbols:
        return {}
    
    placeholders = ','.join([':s' + str(i) for i in range(len(stock_symbols))])
    query = text(f"""
        SELECT symbol, close
        FROM yfinance_daily_quotes
        WHERE symbol IN ({placeholders})
          AND date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE())
    """)
    
    params = {f's{i}': symbol for i, symbol in enumerate(stock_symbols)}
    
    cache = {}
    with engine.connect() as conn:
        result = conn.execute(query, params)
        for row in result:
            # Map back to Yahoo symbol format
            symbol_base = row[0]
            yahoo_symbol = symbol_base + '.NS' if not symbol_base.startswith('^') else symbol_base
            cache[yahoo_symbol] = float(row[1])
    
    # Get Nifty previous close separately
    nifty_query = text("""
        SELECT close
        FROM yfinance_daily_quotes
        WHERE symbol = 'NIFTY'
          AND date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE())
        LIMIT 1
    """)
    
    with engine.connect() as conn:
        result = conn.execute(nifty_query)
        row = result.fetchone()
        if row:
            cache['^NSEI'] = float(row[0])
    
    print(f"✅ Loaded {len(cache)} previous close prices")
    return cache


def download_symbol_data(symbol: str, days: int, prev_close_cache: Dict[str, float]) -> Optional[pd.DataFrame]:
    """Download 1-min data for a single symbol"""
    try:
        ticker = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval='1m',
            actions=False,
            auto_adjust=True
        )
        
        if df.empty:
            return None
        
        # Reset index
        df.reset_index(inplace=True)
        
        # Rename columns
        df.rename(columns={
            'Datetime': 'candle_timestamp',
            'Open': 'open_price',
            'High': 'high_price',
            'Low': 'low_price',
            'Close': 'close_price',
            'Volume': 'volume'
        }, inplace=True)
        
        # Add metadata
        display_symbol = 'NIFTY' if symbol == '^NSEI' else symbol
        df['symbol'] = display_symbol
        df['poll_time'] = datetime.now()
        df['trade_date'] = df['candle_timestamp'].dt.date
        
        # Set prev_close from cache
        prev_close = prev_close_cache.get(symbol)
        df['prev_close'] = prev_close if prev_close else df['close_price'].shift(1)
        
        return df[['poll_time', 'trade_date', 'symbol', 'candle_timestamp',
                   'open_price', 'high_price', 'low_price', 'close_price',
                   'volume', 'prev_close']]
    
    except Exception as e:
        logger.error(f"Failed to download {symbol}: {e}")
        return None


def download_all_symbols(engine, symbols: List[str], days: int, workers: int = 10) -> pd.DataFrame:
    """Download data for all symbols in parallel"""
    print("\n" + "=" * 70)
    print("📥 STEP 2: DOWNLOADING 1-MINUTE DATA FROM YAHOO FINANCE")
    print("=" * 70)
    print(f"Symbols: {len(symbols)}")
    print(f"Days: {days}")
    print(f"Workers: {workers}")
    print("-" * 70)
    
    # Get previous close cache
    prev_close_cache = get_previous_close_cache(engine, symbols)
    
    all_candles = []
    completed = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_symbol = {
            executor.submit(download_symbol_data, symbol, days, prev_close_cache): symbol
            for symbol in symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            completed += 1
            
            try:
                df = future.result()
                if df is not None and not df.empty:
                    all_candles.append(df)
                    print(f"[{completed}/{len(symbols)}] ✅ {symbol}: {len(df)} candles")
                else:
                    failed += 1
                    print(f"[{completed}/{len(symbols)}] ⚠️  {symbol}: No data")
            except Exception as e:
                failed += 1
                print(f"[{completed}/{len(symbols)}] ❌ {symbol}: {e}")
    
    if not all_candles:
        print("\n❌ No data downloaded!")
        return pd.DataFrame()
    
    # Combine all dataframes
    combined = pd.concat(all_candles, ignore_index=True)
    
    print("\n" + "=" * 70)
    print(f"✅ Downloaded {len(combined)} total candles")
    print(f"   Success: {len(symbols) - failed} symbols")
    print(f"   Failed: {failed} symbols")
    print(f"   Date range: {combined['trade_date'].min()} to {combined['trade_date'].max()}")
    print("=" * 70)
    
    return combined


def store_candles(engine, df: pd.DataFrame):
    """Store candles to database"""
    print("\n" + "=" * 70)
    print("💾 STEP 3: STORING CANDLES TO DATABASE")
    print("=" * 70)
    
    if df.empty:
        print("❌ No candles to store")
        return
    
    print(f"Storing {len(df)} candles...")
    
    # Create temp table
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TEMPORARY TABLE tmp_candles LIKE intraday_1min_candles
        """))
    
    # Bulk insert to temp
    df.to_sql(
        name='tmp_candles',
        con=engine,
        if_exists='append',
        index=False,
        method='multi',
        chunksize=5000
    )
    
    # Upsert to main table
    with engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO intraday_1min_candles
            (poll_time, trade_date, symbol, candle_timestamp,
             open_price, high_price, low_price, close_price, volume, prev_close)
            SELECT *
            FROM tmp_candles
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                volume = VALUES(volume)
        """))
        
        print(f"✅ Stored {result.rowcount} candles to intraday_1min_candles")


def calculate_advance_decline(engine, df: pd.DataFrame):
    """Calculate and store advance-decline data"""
    print("\n" + "=" * 70)
    print("📊 STEP 4: CALCULATING ADVANCE-DECLINE METRICS")
    print("=" * 70)
    
    if df.empty:
        print("❌ No data to process")
        return
    
    # Group by poll_time (assuming each poll_time represents a snapshot)
    # For downloaded data, we'll group by candle_timestamp rounded to 5-minute intervals
    df_copy = df.copy()
    df_copy['rounded_time'] = df_copy['candle_timestamp'].dt.floor('5T')
    
    records = []
    
    for (trade_date, poll_time), group in df_copy.groupby(['trade_date', 'rounded_time']):
        # Calculate advances/declines/unchanged
        group_clean = group.dropna(subset=['close_price', 'prev_close'])
        
        if len(group_clean) == 0:
            continue
        
        advances = len(group_clean[group_clean['close_price'] > group_clean['prev_close']])
        declines = len(group_clean[group_clean['close_price'] < group_clean['prev_close']])
        unchanged = len(group_clean[group_clean['close_price'] == group_clean['prev_close']])
        total = len(group_clean)
        
        if total == 0:
            continue
        
        adv_pct = (advances / total * 100) if total > 0 else 0
        decl_pct = (declines / total * 100) if total > 0 else 0
        adv_decl_ratio = (advances / declines) if declines > 0 else None
        adv_decl_diff = advances - declines
        
        # Market sentiment
        if adv_pct >= 70:
            sentiment = 'STRONGLY_BULLISH'
        elif adv_pct >= 60:
            sentiment = 'BULLISH'
        elif adv_pct >= 55:
            sentiment = 'SLIGHTLY_BULLISH'
        elif adv_pct >= 45:
            sentiment = 'NEUTRAL'
        elif adv_pct >= 40:
            sentiment = 'SLIGHTLY_BEARISH'
        elif adv_pct >= 30:
            sentiment = 'BEARISH'
        else:
            sentiment = 'STRONGLY_BEARISH'
        
        records.append({
            'poll_time': poll_time,
            'trade_date': trade_date,
            'advances': advances,
            'declines': declines,
            'unchanged': unchanged,
            'total_stocks': total,
            'adv_pct': adv_pct,
            'decl_pct': decl_pct,
            'adv_decl_ratio': adv_decl_ratio,
            'adv_decl_diff': adv_decl_diff,
            'market_sentiment': sentiment
        })
    
    if not records:
        print("❌ No advance-decline data calculated")
        return
    
    print(f"Calculated {len(records)} advance-decline snapshots")
    
    # Store to database
    adv_decl_df = pd.DataFrame(records)
    
    with engine.begin() as conn:
        for _, row in adv_decl_df.iterrows():
            conn.execute(text("""
                INSERT INTO intraday_advance_decline
                (poll_time, trade_date, advances, declines, unchanged,
                 total_stocks, adv_pct, decl_pct, adv_decl_ratio,
                 adv_decl_diff, market_sentiment)
                VALUES
                (:poll_time, :trade_date, :advances, :declines, :unchanged,
                 :total_stocks, :adv_pct, :decl_pct, :adv_decl_ratio,
                 :adv_decl_diff, :market_sentiment)
            """), row.to_dict())
    
    print(f"✅ Stored {len(records)} advance-decline snapshots")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Rebuild intraday data from Yahoo Finance')
    parser.add_argument('--days', type=int, default=7, help='Number of days to download (max 7 for 1m)')
    parser.add_argument('--workers', type=int, default=10, help='Parallel workers')
    parser.add_argument('--no-clear', action='store_true', help='Do not clear existing data')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔄 COMPLETE INTRADAY DATA REBUILD")
    print("=" * 70)
    print(f"Days: {args.days}")
    print(f"Workers: {args.workers}")
    print(f"Clear existing: {not args.no_clear}")
    print("=" * 70)
    
    # Create engine
    engine = create_db_engine()
    
    # Step 1: Clear existing data
    if not args.no_clear:
        clear_intraday_data(engine)
    
    # Get symbols
    symbols = get_symbols(engine)
    print(f"\n📋 Loaded {len(symbols)} symbols (including Nifty index)")
    
    # Step 2: Download all data
    df = download_all_symbols(engine, symbols, args.days, args.workers)
    
    if df.empty:
        print("\n❌ No data downloaded. Exiting.")
        sys.exit(1)
    
    # Step 3: Store candles
    store_candles(engine, df)
    
    # Step 4: Calculate advance-decline
    calculate_advance_decline(engine, df)
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE! INTRADAY DATA REBUILD FINISHED")
    print("=" * 70)
    print("\n💡 You can now view the data:")
    print("   python intraday_adv_decl_viewer.py")


if __name__ == "__main__":
    main()
