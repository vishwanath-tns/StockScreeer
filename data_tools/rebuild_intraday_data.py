"""
Rebuild Intraday Data from Yahoo Finance
=========================================

Complete rebuild of intraday data:
1. Clear all existing intraday data
2. Download 1-minute data for all Nifty 500 stocks + Nifty index
3. Recalculate advance-decline snapshots
4. Store everything in database

Usage:
    python rebuild_intraday_data.py --days 7
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
from tqdm import tqdm

# Add path for imports
sys.path.insert(0, os.path.dirname(__file__))
from load_verified_symbols import get_verified_yahoo_symbols

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
    
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=10, max_overflow=20)


def clear_intraday_tables(engine):
    """Clear all existing intraday data"""
    print("\n" + "="*70)
    print("🗑️  CLEARING EXISTING INTRADAY DATA")
    print("="*70)
    
    # First get counts to show progress
    with engine.connect() as conn:
        count1 = conn.execute(text("SELECT COUNT(*) FROM intraday_1min_candles")).scalar()
        count2 = conn.execute(text("SELECT COUNT(*) FROM intraday_advance_decline")).scalar()
    
    print(f"📊 Found {count1:,} candles and {count2:,} A/D snapshots to delete...")
    
    with engine.begin() as conn:
        # Use TRUNCATE for faster clearing (resets auto-increment and doesn't log each row)
        print("🗑️  Truncating intraday_1min_candles...", end='', flush=True)
        conn.execute(text("TRUNCATE TABLE intraday_1min_candles"))
        print(f" ✅ Cleared table (was {count1:,} rows)")
        logger.info(f"Truncated intraday_1min_candles (was {count1} rows)")
        
        # Clear advance-decline snapshots
        print("🗑️  Truncating intraday_advance_decline...", end='', flush=True)
        conn.execute(text("TRUNCATE TABLE intraday_advance_decline"))
        print(f" ✅ Cleared table (was {count2:,} rows)")
        logger.info(f"Truncated intraday_advance_decline (was {count2} rows)")
    
    print(f"\n✅ Successfully cleared all intraday data!")
    print("="*70)


def get_previous_close_map(engine, symbols: List[str]) -> Dict[str, float]:
    """
    Get previous close prices for all symbols from yfinance_daily_quotes
    
    Returns:
        Dict mapping symbol -> prev_close
    """
    logger.info("Loading previous close prices from database...")
    
    # Convert to IN clause
    symbol_list = ','.join([f"'{s}'" for s in symbols])
    
    query = text(f"""
        SELECT symbol, close
        FROM yfinance_daily_quotes
        WHERE symbol IN ({symbol_list})
          AND date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE())
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        prev_close_map = {row[0]: float(row[1]) for row in result}
    
    logger.info(f"Loaded previous close for {len(prev_close_map)} symbols")
    return prev_close_map


def download_symbol_data(symbol: str, days: int, interval: str = '1m') -> Optional[pd.DataFrame]:
    """
    Download intraday data for a single symbol
    
    Args:
        symbol: Yahoo symbol
        days: Number of days to download
        interval: Candle interval
    
    Returns:
        DataFrame with OHLCV data or None if failed
    """
    try:
        ticker = yf.Ticker(symbol)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval=interval,
            actions=False,
            auto_adjust=True
        )
        
        if df.empty:
            return None
        
        # Reset index to get datetime as column
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
        df['symbol'] = symbol.replace('.NS', '') if symbol != '^NSEI' else 'NIFTY'
        df['poll_time'] = datetime.now()
        df['trade_date'] = df['candle_timestamp'].dt.date
        
        return df[['poll_time', 'trade_date', 'symbol', 'candle_timestamp', 
                   'open_price', 'high_price', 'low_price', 'close_price', 'volume']]
    
    except Exception as e:
        logger.error(f"Failed to download {symbol}: {e}")
        return None


def download_all_symbols(symbols: List[str], days: int, max_workers: int = 10) -> pd.DataFrame:
    """
    Download intraday data for all symbols in parallel
    
    Args:
        symbols: List of Yahoo symbols
        days: Number of days to download
        max_workers: Number of parallel downloads
    
    Returns:
        Combined DataFrame with all candles
    """
    print(f"\n📥 Downloading {len(symbols)} symbols ({days} days, {max_workers} workers)...")
    
    all_dfs = []
    failed_symbols = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {
            executor.submit(download_symbol_data, symbol, days): symbol
            for symbol in symbols
        }
        
        # Process as completed with progress bar
        with tqdm(total=len(symbols), desc="Downloading") as pbar:
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    df = future.result()
                    if df is not None and len(df) > 0:
                        all_dfs.append(df)
                    else:
                        failed_symbols.append(symbol)
                except Exception as e:
                    logger.error(f"Exception for {symbol}: {e}")
                    failed_symbols.append(symbol)
                finally:
                    pbar.update(1)
    
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"✅ Downloaded {len(combined_df)} total candles from {len(all_dfs)} symbols")
        
        if failed_symbols:
            logger.warning(f"⚠️  Failed to download {len(failed_symbols)} symbols: {failed_symbols[:10]}...")
        
        return combined_df
    else:
        logger.error("No data downloaded!")
        return pd.DataFrame()


def add_previous_close(df: pd.DataFrame, prev_close_map: Dict[str, float]) -> pd.DataFrame:
    """
    Add prev_close column to dataframe
    
    Args:
        df: DataFrame with candle data
        prev_close_map: Dict mapping symbol -> prev_close
    
    Returns:
        DataFrame with prev_close column added
    """
    logger.info("Adding previous close prices...")
    
    df = df.copy()
    df['prev_close'] = df['symbol'].map(prev_close_map)
    
    # Count how many have prev_close
    has_prev_close = df['prev_close'].notna().sum()
    logger.info(f"Added prev_close to {has_prev_close}/{len(df)} candles")
    
    return df


def store_candles_bulk(df: pd.DataFrame, engine) -> int:
    """
    Store all candles to database in bulk
    
    Args:
        df: DataFrame with candle data
        engine: SQLAlchemy engine
    
    Returns:
        Number of rows inserted
    """
    if df.empty:
        return 0
    
    print("\n💾 Storing candles to database...")
    
    try:
        # Create temp table
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_bulk_candles LIKE intraday_1min_candles
            """))
        
        # Bulk insert into temp
        logger.info(f"Inserting {len(df)} candles into temp table...")
        df.to_sql(
            name='tmp_bulk_candles',
            con=engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=5000
        )
        
        # Upsert to main table
        logger.info("Upserting to main table...")
        with engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO intraday_1min_candles
                (poll_time, trade_date, symbol, candle_timestamp,
                 open_price, high_price, low_price, close_price, volume, prev_close)
                SELECT 
                    poll_time, trade_date, symbol, candle_timestamp,
                    open_price, high_price, low_price, close_price, volume, prev_close
                FROM tmp_bulk_candles
                ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    prev_close = VALUES(prev_close)
            """))
            
            rows = result.rowcount
            logger.info(f"✅ Stored {rows} candles")
            return rows
    
    except Exception as e:
        logger.error(f"Failed to store candles: {e}")
        raise


def calculate_advance_decline_snapshots(engine):
    """
    Calculate advance-decline snapshots from stored 1-minute candles
    Group by poll_time to recreate the snapshots
    """
    print("\n📊 Calculating advance-decline snapshots...")
    
    query = text("""
        SELECT 
            trade_date,
            candle_timestamp as poll_time,
            COUNT(*) as total_stocks,
            SUM(CASE WHEN close_price > prev_close THEN 1 ELSE 0 END) as advances,
            SUM(CASE WHEN close_price < prev_close THEN 1 ELSE 0 END) as declines,
            SUM(CASE WHEN close_price = prev_close THEN 1 ELSE 0 END) as unchanged
        FROM intraday_1min_candles
        WHERE prev_close IS NOT NULL
          AND symbol != 'NIFTY'
        GROUP BY trade_date, candle_timestamp
        ORDER BY trade_date, candle_timestamp
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        snapshots = result.fetchall()
    
    if not snapshots:
        logger.warning("No snapshots calculated (no data?)")
        return 0
    
    logger.info(f"Calculated {len(snapshots)} advance-decline snapshots")
    
    # Prepare data for insert
    snapshot_data = []
    for row in snapshots:
        trade_date, poll_time, total, adv, decl, unch = row
        
        adv_pct = (adv / total * 100) if total > 0 else 0
        decl_pct = (decl / total * 100) if total > 0 else 0
        ratio = (adv / decl) if decl > 0 else None
        diff = adv - decl
        
        # Determine sentiment
        if adv_pct >= 70:
            sentiment = 'VERY BULLISH'
        elif adv_pct >= 60:
            sentiment = 'BULLISH'
        elif adv_pct >= 55:
            sentiment = 'SLIGHTLY BULLISH'
        elif adv_pct <= 30:
            sentiment = 'VERY BEARISH'
        elif adv_pct <= 40:
            sentiment = 'BEARISH'
        elif adv_pct <= 45:
            sentiment = 'SLIGHTLY BEARISH'
        else:
            sentiment = 'NEUTRAL'
        
        snapshot_data.append({
            'poll_time': poll_time,
            'trade_date': trade_date,
            'advances': adv,
            'declines': decl,
            'unchanged': unch,
            'total_stocks': total,
            'adv_pct': round(adv_pct, 2),
            'decl_pct': round(decl_pct, 2),
            'adv_decl_ratio': round(ratio, 4) if ratio else None,
            'adv_decl_diff': diff,
            'market_sentiment': sentiment
        })
    
    # Bulk insert snapshots
    logger.info(f"Inserting {len(snapshot_data)} snapshots...")
    
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO intraday_advance_decline
                (poll_time, trade_date, advances, declines, unchanged, 
                 total_stocks, adv_pct, decl_pct, adv_decl_ratio, 
                 adv_decl_diff, market_sentiment)
                VALUES 
                (:poll_time, :trade_date, :advances, :declines, :unchanged,
                 :total_stocks, :adv_pct, :decl_pct, :adv_decl_ratio,
                 :adv_decl_diff, :market_sentiment)
            """),
            snapshot_data
        )
    
    logger.info(f"✅ Stored {len(snapshot_data)} advance-decline snapshots")
    return len(snapshot_data)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Rebuild intraday data from Yahoo Finance'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to download (default: 7, max: 7 for 1m data)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=10,
        help='Number of parallel download workers (default: 10)'
    )
    parser.add_argument(
        '--skip-clear',
        action='store_true',
        help='Skip clearing existing data (append mode)'
    )
    
    args = parser.parse_args()
    
    if args.days > 7:
        print("⚠️  Yahoo Finance limits 1-minute data to 7 days. Setting days=7")
        args.days = 7
    
    print("="*70)
    print("🔄 REBUILD INTRADAY DATA FROM YAHOO FINANCE")
    print("="*70)
    print(f"Days to download: {args.days}")
    print(f"Parallel workers: {args.workers}")
    print(f"Clear existing: {not args.skip_clear}")
    print("="*70)
    
    # Create engine
    engine = create_db_engine()
    
    # Step 1: Clear existing data
    if not args.skip_clear:
        clear_intraday_tables(engine)
    else:
        print("\n⚠️  Skipping clear (append mode)")
    
    # Step 2: Get symbols
    print("\n📋 Loading symbols...")
    stock_symbols = get_verified_yahoo_symbols()
    all_symbols = ['^NSEI'] + stock_symbols  # Add Nifty index
    print(f"✅ Loaded {len(stock_symbols)} stocks + Nifty index")
    
    # Step 3: Get previous close map
    prev_close_map = get_previous_close_map(engine, ['NIFTY'] + [s.replace('.NS', '') for s in stock_symbols])
    
    # Step 4: Download all data
    df = download_all_symbols(all_symbols, args.days, args.workers)
    
    if df.empty:
        print("❌ No data downloaded. Exiting.")
        sys.exit(1)
    
    # Step 5: Add previous close
    df = add_previous_close(df, prev_close_map)
    
    # Step 6: Store candles
    candle_count = store_candles_bulk(df, engine)
    
    # Step 7: Calculate advance-decline snapshots
    snapshot_count = calculate_advance_decline_snapshots(engine)
    
    # Summary
    print("\n" + "="*70)
    print("✅ REBUILD COMPLETE!")
    print("="*70)
    print(f"Candles stored:        {candle_count:,}")
    print(f"A/D snapshots:         {snapshot_count:,}")
    print(f"Symbols downloaded:    {len(df['symbol'].unique()):,}")
    print(f"Date range:            {df['trade_date'].min()} to {df['trade_date'].max()}")
    print("="*70)
    print("\n💡 You can now view the data:")
    print("   python intraday_adv_decl_viewer.py")
    print("="*70)


if __name__ == "__main__":
    main()
