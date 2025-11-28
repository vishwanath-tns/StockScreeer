"""
Download Nifty Index Intraday Data
===================================

Downloads 1-minute (or 5-minute) candle data for Nifty index from Yahoo Finance
and stores it in the same intraday_1min_candles table used by real-time system.

Usage:
    python download_nifty_intraday.py              # Download today's 1-min data
    python download_nifty_intraday.py --days 7     # Download last 7 days
    python download_nifty_intraday.py --interval 5m --days 30  # 5-min data for 30 days
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import Optional
import argparse
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import logging

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
    
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def download_nifty_intraday(days: int = 1, interval: str = '1m') -> pd.DataFrame:
    """
    Download Nifty index intraday data from Yahoo Finance
    
    Args:
        days: Number of days to download (max 7 for 1m, 60 for 5m)
        interval: Candle interval ('1m', '5m', '15m', '30m', '60m')
    
    Returns:
        DataFrame with OHLCV data
    """
    symbol = '^NSEI'  # Nifty 50 index symbol on Yahoo Finance
    
    # Validate interval and days
    if interval == '1m' and days > 7:
        logger.warning(f"Yahoo Finance limits 1m data to 7 days. Setting days=7")
        days = 7
    elif interval == '5m' and days > 60:
        logger.warning(f"Yahoo Finance limits 5m data to 60 days. Setting days=60")
        days = 60
    
    logger.info(f"Downloading {days} days of {interval} data for Nifty 50...")
    
    try:
        # Download data
        ticker = yf.Ticker(symbol)
        
        # For intraday data, use start/end dates instead of period
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
            logger.error("No data received from Yahoo Finance")
            return pd.DataFrame()
        
        # Reset index to get datetime as column
        df.reset_index(inplace=True)
        
        # Rename columns to match our schema
        df.rename(columns={
            'Datetime': 'candle_timestamp',
            'Open': 'open_price',
            'High': 'high_price',
            'Low': 'low_price',
            'Close': 'close_price',
            'Volume': 'volume'
        }, inplace=True)
        
        # Add metadata columns
        df['symbol'] = 'NIFTY'
        df['poll_time'] = datetime.now()
        df['trade_date'] = df['candle_timestamp'].dt.date
        
        # Add prev_close (previous candle's close for now)
        df['prev_close'] = df['close_price'].shift(1)
        
        # For first candle of each day, get actual previous day close
        df['date_changed'] = df['trade_date'] != df['trade_date'].shift(1)
        
        logger.info(f"Downloaded {len(df)} candles from {df['candle_timestamp'].min()} to {df['candle_timestamp'].max()}")
        
        return df[['poll_time', 'trade_date', 'symbol', 'candle_timestamp', 
                   'open_price', 'high_price', 'low_price', 'close_price', 
                   'volume', 'prev_close']]
    
    except Exception as e:
        logger.error(f"Failed to download data: {e}")
        return pd.DataFrame()


def get_previous_day_close(engine, trade_date: date) -> Optional[float]:
    """
    Get previous trading day's close from yfinance_daily_quotes
    
    Args:
        engine: SQLAlchemy engine
        trade_date: Current trade date
    
    Returns:
        Previous close price or None
    """
    query = text("""
        SELECT close
        FROM yfinance_daily_quotes
        WHERE symbol = 'NIFTY'
          AND date < :trade_date
        ORDER BY date DESC
        LIMIT 1
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'trade_date': trade_date})
            row = result.fetchone()
            return float(row[0]) if row else None
    except Exception as e:
        logger.warning(f"Could not fetch previous close for {trade_date}: {e}")
        return None


def fix_previous_close(df: pd.DataFrame, engine) -> pd.DataFrame:
    """
    Fix prev_close for first candle of each day using actual previous day close
    
    Args:
        df: DataFrame with candle data
        engine: SQLAlchemy engine
    
    Returns:
        DataFrame with corrected prev_close
    """
    df = df.copy()
    
    # Group by trade_date
    for trade_date in df['trade_date'].unique():
        # Get previous day's close from database
        prev_close = get_previous_day_close(engine, trade_date)
        
        if prev_close is not None:
            # Set prev_close for all candles of this date
            mask = df['trade_date'] == trade_date
            df.loc[mask, 'prev_close'] = prev_close
            logger.info(f"Set prev_close={prev_close:.2f} for {trade_date}")
        else:
            logger.warning(f"Could not find previous close for {trade_date}")
    
    return df


def store_to_database(df: pd.DataFrame, engine) -> int:
    """
    Store candle data to intraday_1min_candles table
    
    Args:
        df: DataFrame with candle data
        engine: SQLAlchemy engine
    
    Returns:
        Number of records inserted/updated
    """
    if df.empty:
        logger.warning("No data to store")
        return 0
    
    try:
        # First insert into temp table
        logger.info("Creating temporary table...")
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_nifty_candles LIKE intraday_1min_candles
            """))
        
        # Bulk insert into temp table using engine
        logger.info(f"Inserting {len(df)} rows into temp table...")
        df.to_sql(
            name='tmp_nifty_candles',
            con=engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        # Upsert from temp to main table
        logger.info("Upserting from temp to main table...")
        with engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO intraday_1min_candles
                (poll_time, trade_date, symbol, candle_timestamp,
                 open_price, high_price, low_price, close_price, volume, prev_close)
                SELECT 
                    poll_time, trade_date, symbol, candle_timestamp,
                    open_price, high_price, low_price, close_price, volume, prev_close
                FROM tmp_nifty_candles
                ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    prev_close = VALUES(prev_close),
                    poll_time = VALUES(poll_time)
            """))
            
            rows_affected = result.rowcount
            logger.info(f"✅ Stored {rows_affected} candles to database")
            
            return rows_affected
    
    except Exception as e:
        logger.error(f"Failed to store data: {e}")
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Download Nifty index intraday data from Yahoo Finance'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of days to download (default: 1, max: 7 for 1m, 60 for 5m)'
    )
    parser.add_argument(
        '--interval',
        type=str,
        default='1m',
        choices=['1m', '5m', '15m', '30m', '60m'],
        help='Candle interval (default: 1m)'
    )
    parser.add_argument(
        '--no-fix-prev-close',
        action='store_true',
        help='Do not fix previous close from database'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Nifty Index Intraday Data Downloader")
    print("=" * 70)
    print(f"Interval: {args.interval}")
    print(f"Days: {args.days}")
    print("-" * 70)
    
    # Create engine
    engine = create_db_engine()
    
    # Download data
    df = download_nifty_intraday(days=args.days, interval=args.interval)
    
    if df.empty:
        print("❌ No data downloaded. Exiting.")
        sys.exit(1)
    
    print(f"\n✅ Downloaded {len(df)} candles")
    print(f"   Date range: {df['trade_date'].min()} to {df['trade_date'].max()}")
    print(f"   Time range: {df['candle_timestamp'].min()} to {df['candle_timestamp'].max()}")
    
    # Fix previous close
    if not args.no_fix_prev_close:
        print("\n🔧 Fixing previous close from database...")
        df = fix_previous_close(df, engine)
    
    # Store to database
    print("\n💾 Storing to database...")
    rows = store_to_database(df, engine)
    
    print("\n" + "=" * 70)
    print(f"✅ SUCCESS: {rows} candles stored in intraday_1min_candles table")
    print("=" * 70)
    
    # Show summary
    print("\nSummary by date:")
    summary = df.groupby('trade_date').agg({
        'candle_timestamp': 'count',
        'open_price': 'first',
        'close_price': 'last',
        'high_price': 'max',
        'low_price': 'min'
    }).rename(columns={'candle_timestamp': 'candles'})
    
    print(summary.to_string())
    
    print("\n💡 You can now view this data in the offline viewer:")
    print("   python intraday_adv_decl_viewer.py")


if __name__ == "__main__":
    main()
