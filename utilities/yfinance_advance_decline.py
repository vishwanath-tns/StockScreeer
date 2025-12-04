#!/usr/bin/env python3
"""
Yahoo Finance Advance/Decline Calculator and Storage
=====================================================
Calculates daily advance/decline statistics from Yahoo Finance daily quotes
and stores them in the marketdata database.

Features:
- Calculates advances, declines, unchanged counts for each trading day
- Computes A/D ratio and net advance/decline
- Stores historical data in yfinance_advance_decline table
- Can be run standalone or integrated with Daily Data Wizard

Usage:
    python utilities/yfinance_advance_decline.py              # Calculate all historical data
    python utilities/yfinance_advance_decline.py --days 30    # Last 30 days only
    python utilities/yfinance_advance_decline.py --update     # Update only missing dates
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
except ImportError:
    NIFTY_500_STOCKS = None


def get_engine():
    """Create database engine with proper password handling."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        database="marketdata"
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def create_advance_decline_table(engine):
    """Create the yfinance_advance_decline table if it doesn't exist."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS yfinance_advance_decline (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trade_date DATE NOT NULL UNIQUE,
        advances INT NOT NULL DEFAULT 0,
        declines INT NOT NULL DEFAULT 0,
        unchanged INT NOT NULL DEFAULT 0,
        total_stocks INT NOT NULL DEFAULT 0,
        net_advance_decline INT NOT NULL DEFAULT 0,
        ad_ratio DECIMAL(10, 4) DEFAULT NULL,
        advance_percent DECIMAL(6, 2) DEFAULT NULL,
        decline_percent DECIMAL(6, 2) DEFAULT NULL,
        
        -- Distribution buckets for gains
        gain_0_1 INT DEFAULT 0,
        gain_1_2 INT DEFAULT 0,
        gain_2_3 INT DEFAULT 0,
        gain_3_5 INT DEFAULT 0,
        gain_5_plus INT DEFAULT 0,
        
        -- Distribution buckets for losses
        loss_0_1 INT DEFAULT 0,
        loss_1_2 INT DEFAULT 0,
        loss_2_3 INT DEFAULT 0,
        loss_3_5 INT DEFAULT 0,
        loss_5_plus INT DEFAULT 0,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        INDEX idx_trade_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()
    print("✅ Table yfinance_advance_decline created/verified")


def get_yahoo_symbols() -> List[str]:
    """Get list of Yahoo Finance symbols for Nifty 500 stocks."""
    if NIFTY_500_STOCKS:
        return [f"{s}.NS" for s in NIFTY_500_STOCKS]
    
    # Fallback: try to get from database
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT symbol FROM yfinance_daily_quotes 
            WHERE symbol LIKE '%.NS' 
            ORDER BY symbol
        """))
        symbols = [row[0] for row in result.fetchall()]
    
    return symbols if symbols else []


def get_daily_quotes_for_date_range(engine, start_date: str, end_date: str, filter_nifty500: bool = True) -> pd.DataFrame:
    """
    Fetch daily quotes from database for date range.
    
    Args:
        engine: Database engine
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)  
        filter_nifty500: If True, filter to only Nifty 500 symbols
    """
    query = """
        SELECT symbol, date as trade_date, open, close as close_price
        FROM yfinance_daily_quotes
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date, symbol
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={
            'start_date': start_date,
            'end_date': end_date
        })
    
    # Filter to Nifty 500 if requested
    if filter_nifty500:
        symbols = get_yahoo_symbols()
        if symbols:
            df = df[df['symbol'].isin(symbols)]
    
    return df


def get_all_trading_dates(engine) -> List[str]:
    """Get all unique trading dates from the daily quotes table."""
    query = """
        SELECT DISTINCT date 
        FROM yfinance_daily_quotes 
        ORDER BY date
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        dates = [row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]) 
                 for row in result.fetchall()]
    
    return dates


def get_existing_ad_dates(engine) -> set:
    """Get dates already calculated in advance_decline table."""
    query = "SELECT trade_date FROM yfinance_advance_decline"
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        dates = {row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]) 
                 for row in result.fetchall()}
    
    return dates


def calculate_advance_decline_for_date(df_today: pd.DataFrame, df_prev: pd.DataFrame) -> Dict:
    """
    Calculate advance/decline statistics for a single date.
    
    Args:
        df_today: DataFrame with today's data (symbol, close_price)
        df_prev: DataFrame with previous day's data (symbol, close_price)
    
    Returns:
        Dictionary with all statistics
    """
    # Merge today's close with previous day's close
    merged = df_today.merge(
        df_prev[['symbol', 'close_price']], 
        on='symbol', 
        suffixes=('', '_prev')
    )
    
    if merged.empty:
        return None
    
    # Calculate percentage change
    merged['pct_change'] = ((merged['close_price'] - merged['close_price_prev']) / 
                            merged['close_price_prev']) * 100
    
    # Count advances, declines, unchanged (using 0.01% threshold)
    advances = (merged['pct_change'] > 0.01).sum()
    declines = (merged['pct_change'] < -0.01).sum()
    unchanged = ((merged['pct_change'] >= -0.01) & (merged['pct_change'] <= 0.01)).sum()
    total = len(merged)
    
    # Calculate distribution buckets
    distribution = {
        'gain_0_1': ((merged['pct_change'] > 0.01) & (merged['pct_change'] <= 1)).sum(),
        'gain_1_2': ((merged['pct_change'] > 1) & (merged['pct_change'] <= 2)).sum(),
        'gain_2_3': ((merged['pct_change'] > 2) & (merged['pct_change'] <= 3)).sum(),
        'gain_3_5': ((merged['pct_change'] > 3) & (merged['pct_change'] <= 5)).sum(),
        'gain_5_plus': (merged['pct_change'] > 5).sum(),
        'loss_0_1': ((merged['pct_change'] < -0.01) & (merged['pct_change'] >= -1)).sum(),
        'loss_1_2': ((merged['pct_change'] < -1) & (merged['pct_change'] >= -2)).sum(),
        'loss_2_3': ((merged['pct_change'] < -2) & (merged['pct_change'] >= -3)).sum(),
        'loss_3_5': ((merged['pct_change'] < -3) & (merged['pct_change'] >= -5)).sum(),
        'loss_5_plus': (merged['pct_change'] < -5).sum(),
    }
    
    # Calculate ratios
    ad_ratio = advances / declines if declines > 0 else None
    net_ad = advances - declines
    advance_pct = (advances / total * 100) if total > 0 else 0
    decline_pct = (declines / total * 100) if total > 0 else 0
    
    return {
        'advances': int(advances),
        'declines': int(declines),
        'unchanged': int(unchanged),
        'total_stocks': int(total),
        'net_advance_decline': int(net_ad),
        'ad_ratio': round(ad_ratio, 4) if ad_ratio else None,
        'advance_percent': round(advance_pct, 2),
        'decline_percent': round(decline_pct, 2),
        **{k: int(v) for k, v in distribution.items()}
    }


def insert_advance_decline_record(engine, trade_date: str, stats: Dict):
    """Insert or update advance/decline record for a date."""
    insert_sql = """
        INSERT INTO yfinance_advance_decline (
            trade_date, advances, declines, unchanged, total_stocks,
            net_advance_decline, ad_ratio, advance_percent, decline_percent,
            gain_0_1, gain_1_2, gain_2_3, gain_3_5, gain_5_plus,
            loss_0_1, loss_1_2, loss_2_3, loss_3_5, loss_5_plus
        ) VALUES (
            :trade_date, :advances, :declines, :unchanged, :total_stocks,
            :net_advance_decline, :ad_ratio, :advance_percent, :decline_percent,
            :gain_0_1, :gain_1_2, :gain_2_3, :gain_3_5, :gain_5_plus,
            :loss_0_1, :loss_1_2, :loss_2_3, :loss_3_5, :loss_5_plus
        )
        ON DUPLICATE KEY UPDATE
            advances = VALUES(advances),
            declines = VALUES(declines),
            unchanged = VALUES(unchanged),
            total_stocks = VALUES(total_stocks),
            net_advance_decline = VALUES(net_advance_decline),
            ad_ratio = VALUES(ad_ratio),
            advance_percent = VALUES(advance_percent),
            decline_percent = VALUES(decline_percent),
            gain_0_1 = VALUES(gain_0_1),
            gain_1_2 = VALUES(gain_1_2),
            gain_2_3 = VALUES(gain_2_3),
            gain_3_5 = VALUES(gain_3_5),
            gain_5_plus = VALUES(gain_5_plus),
            loss_0_1 = VALUES(loss_0_1),
            loss_1_2 = VALUES(loss_1_2),
            loss_2_3 = VALUES(loss_2_3),
            loss_3_5 = VALUES(loss_3_5),
            loss_5_plus = VALUES(loss_5_plus)
    """
    
    with engine.connect() as conn:
        conn.execute(text(insert_sql), {'trade_date': trade_date, **stats})
        conn.commit()


def calculate_all_historical(engine, update_only: bool = False, days: int = None):
    """
    Calculate advance/decline for all historical dates.
    
    Args:
        engine: Database engine
        update_only: If True, only calculate missing dates
        days: If provided, only calculate last N days
    """
    print("\n📊 Calculating Historical Advance/Decline Data")
    print("=" * 60)
    
    # Get all trading dates
    all_dates = get_all_trading_dates(engine)
    print(f"📅 Total trading dates in database: {len(all_dates)}")
    
    if not all_dates:
        print("❌ No trading dates found in yfinance_daily_quotes")
        return
    
    # Filter dates if needed
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        all_dates = [d for d in all_dates if d >= cutoff]
        print(f"📅 Filtered to last {days} days: {len(all_dates)} dates")
    
    # Get existing dates if update_only
    if update_only:
        existing = get_existing_ad_dates(engine)
        dates_to_process = [d for d in all_dates if d not in existing]
        print(f"📅 Dates already calculated: {len(existing)}")
        print(f"📅 Dates to calculate: {len(dates_to_process)}")
    else:
        dates_to_process = all_dates
    
    if not dates_to_process:
        print("✅ All dates already calculated!")
        return
    
    # Need at least 2 dates to calculate A/D (need previous day)
    if len(all_dates) < 2:
        print("❌ Need at least 2 trading days to calculate A/D")
        return
    
    # Get date range for efficient data loading
    min_date = min(dates_to_process)
    max_date = max(dates_to_process)
    
    # Load data for the range (plus one day before for prev close)
    min_date_idx = all_dates.index(min_date) if min_date in all_dates else 0
    if min_date_idx > 0:
        data_start = all_dates[min_date_idx - 1]
    else:
        data_start = min_date
    
    print(f"\n📥 Loading data from {data_start} to {max_date}...")
    df_all = get_daily_quotes_for_date_range(engine, data_start, max_date)
    print(f"📊 Loaded {len(df_all):,} records")
    
    # Convert trade_date to string for consistent comparison
    df_all['trade_date_str'] = df_all['trade_date'].astype(str)
    
    # Process each date
    processed = 0
    errors = 0
    
    for i, date in enumerate(dates_to_process):
        try:
            # Find previous trading day
            date_idx = all_dates.index(date) if date in all_dates else -1
            if date_idx <= 0:
                continue  # Skip first date (no previous)
            
            prev_date = all_dates[date_idx - 1]
            
            # Get data for current and previous date
            df_today = df_all[df_all['trade_date_str'] == date][['symbol', 'close_price']].copy()
            df_prev = df_all[df_all['trade_date_str'] == prev_date][['symbol', 'close_price']].copy()
            
            if df_today.empty or df_prev.empty:
                continue
            
            # Calculate statistics
            stats = calculate_advance_decline_for_date(df_today, df_prev)
            
            if stats:
                insert_advance_decline_record(engine, date, stats)
                processed += 1
                
                # Progress indicator
                if processed % 50 == 0 or i == len(dates_to_process) - 1:
                    print(f"  ✅ Processed {processed}/{len(dates_to_process)} dates... "
                          f"[{date}: A={stats['advances']}, D={stats['declines']}]")
        
        except Exception as e:
            errors += 1
            print(f"  ❌ Error processing {date}: {e}")
    
    print(f"\n{'=' * 60}")
    print(f"✅ Completed! Processed: {processed}, Errors: {errors}")


def update_latest(engine, date: str = None):
    """
    Update A/D data for a specific date (called by Daily Data Wizard).
    
    Args:
        engine: Database engine
        date: Date to update (YYYY-MM-DD). If None, updates today.
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    all_dates = get_all_trading_dates(engine)
    
    if date not in all_dates:
        print(f"⚠️ Date {date} not found in trading dates")
        return False
    
    date_idx = all_dates.index(date)
    if date_idx == 0:
        print(f"⚠️ Cannot calculate A/D for first date (no previous day)")
        return False
    
    prev_date = all_dates[date_idx - 1]
    
    # Load data for both dates
    df_all = get_daily_quotes_for_date_range(engine, prev_date, date)
    df_all['trade_date_str'] = df_all['trade_date'].astype(str)
    
    df_today = df_all[df_all['trade_date_str'] == date][['symbol', 'close_price']].copy()
    df_prev = df_all[df_all['trade_date_str'] == prev_date][['symbol', 'close_price']].copy()
    
    stats = calculate_advance_decline_for_date(df_today, df_prev)
    
    if stats:
        insert_advance_decline_record(engine, date, stats)
        print(f"✅ Updated A/D for {date}: Advances={stats['advances']}, "
              f"Declines={stats['declines']}, Ratio={stats['ad_ratio']}")
        return True
    
    return False


def display_summary(engine, days: int = 10):
    """Display recent A/D data summary."""
    query = """
        SELECT trade_date, advances, declines, unchanged, total_stocks,
               ad_ratio, advance_percent, decline_percent, net_advance_decline
        FROM yfinance_advance_decline
        ORDER BY trade_date DESC
        LIMIT :days
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={'days': days})
    
    if df.empty:
        print("No A/D data found")
        return
    
    print(f"\n📊 Recent Advance/Decline Summary (Last {days} days)")
    print("=" * 100)
    print(f"{'Date':<12} {'Advances':>10} {'Declines':>10} {'Unchanged':>10} "
          f"{'Total':>8} {'A/D Ratio':>10} {'Net A/D':>10}")
    print("-" * 100)
    
    for _, row in df.iterrows():
        date_str = row['trade_date'].strftime('%Y-%m-%d') if hasattr(row['trade_date'], 'strftime') else str(row['trade_date'])
        ratio_str = f"{row['ad_ratio']:.2f}" if row['ad_ratio'] else "N/A"
        print(f"{date_str:<12} {row['advances']:>10} {row['declines']:>10} {row['unchanged']:>10} "
              f"{row['total_stocks']:>8} {ratio_str:>10} {row['net_advance_decline']:>10}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate Yahoo Finance Advance/Decline data')
    parser.add_argument('--update', action='store_true', help='Only update missing dates')
    parser.add_argument('--days', type=int, help='Calculate only last N days')
    parser.add_argument('--date', type=str, help='Update specific date (YYYY-MM-DD)')
    parser.add_argument('--summary', action='store_true', help='Show recent summary')
    
    args = parser.parse_args()
    
    print("🚀 Yahoo Finance Advance/Decline Calculator")
    print("=" * 60)
    
    engine = get_engine()
    
    # Create table if needed
    create_advance_decline_table(engine)
    
    if args.summary:
        display_summary(engine)
    elif args.date:
        update_latest(engine, args.date)
    else:
        calculate_all_historical(engine, update_only=args.update, days=args.days)
        display_summary(engine)


if __name__ == "__main__":
    main()
