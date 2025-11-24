"""
Nifty 500 Advance-Decline Calculator
====================================

Module for calculating daily advance/decline counts for Nifty 500 stocks
from Yahoo Finance data.

Features:
- Calculates advances, declines, unchanged counts
- Prevents duplicate entries
- Batch processing for date ranges
- Progress tracking
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'database': os.getenv('MYSQL_DB', 'marketdata'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '')
}


def get_db_engine():
    """Create and return SQLAlchemy engine"""
    url = URL.create(
        drivername="mysql+pymysql",
        username=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def get_nifty500_symbols() -> List[str]:
    """
    Get list of all available stock symbols from Yahoo Finance data
    
    Returns:
        List of stock symbols (all stocks with data, not limited to Nifty 500)
    """
    try:
        from available_stocks_list import AVAILABLE_STOCKS
        logger.info(f"Loaded {len(AVAILABLE_STOCKS)} stocks from available_stocks_list.py")
        return AVAILABLE_STOCKS
    except ImportError:
        logger.warning("Could not import AVAILABLE_STOCKS, querying database")
        # Fallback: query from database
        engine = get_db_engine()
        query = text("""
            SELECT DISTINCT symbol 
            FROM yfinance_daily_quotes 
            WHERE symbol != 'NIFTY'
                AND close IS NOT NULL
            ORDER BY symbol
        """)
        df = pd.read_sql(query, engine)
        logger.info(f"Queried {len(df)} stocks from database")
        return df['symbol'].tolist()


def is_date_computed(trade_date: date, engine) -> bool:
    """
    Check if advance/decline has already been computed for a date
    
    Args:
        trade_date: Date to check
        engine: SQLAlchemy engine
        
    Returns:
        True if already computed, False otherwise
    """
    query = text("""
        SELECT COUNT(*) as count 
        FROM nifty500_advance_decline 
        WHERE trade_date = :trade_date
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'trade_date': trade_date}).fetchone()
        return result[0] > 0


def compute_advance_decline_for_date(
    trade_date: date,
    symbols: List[str],
    engine,
    force_update: bool = False
) -> Optional[Dict]:
    """
    Compute advance/decline/unchanged counts for a specific date
    
    Args:
        trade_date: Date to compute for
        symbols: List of Nifty 500 symbols
        engine: SQLAlchemy engine
        force_update: If True, update even if already exists
        
    Returns:
        Dict with counts or None if no data
    """
    # Check if already computed
    if not force_update and is_date_computed(trade_date, engine):
        logger.info(f"  {trade_date}: Already computed, skipping")
        return None
    
    # Build query to get price changes for all symbols on the date
    # We need current close and previous close
    symbols_placeholder = ','.join([f"'{s}'" for s in symbols[:500]])  # Limit to 500
    
    query = f"""
        WITH daily_data AS (
            SELECT 
                symbol,
                date,
                close,
                LAG(close) OVER (PARTITION BY symbol ORDER BY date) as prev_close
            FROM yfinance_daily_quotes
            WHERE symbol IN ({symbols_placeholder})
                AND date <= :trade_date
                AND close IS NOT NULL
        )
        SELECT 
            symbol,
            close,
            prev_close,
            CASE 
                WHEN prev_close IS NULL THEN 'UNKNOWN'
                WHEN close > prev_close THEN 'ADVANCE'
                WHEN close < prev_close THEN 'DECLINE'
                ELSE 'UNCHANGED'
            END as movement
        FROM daily_data
        WHERE date = :trade_date
            AND prev_close IS NOT NULL
    """
    
    try:
        df = pd.read_sql(text(query), engine, params={'trade_date': trade_date})
        
        if df.empty:
            logger.warning(f"  {trade_date}: No data found")
            return None
        
        # Count movements
        advances = len(df[df['movement'] == 'ADVANCE'])
        declines = len(df[df['movement'] == 'DECLINE'])
        unchanged = len(df[df['movement'] == 'UNCHANGED'])
        total = len(df)
        
        # Calculate percentages and ratios
        advance_pct = (advances / total * 100) if total > 0 else 0
        decline_pct = (declines / total * 100) if total > 0 else 0
        unchanged_pct = (unchanged / total * 100) if total > 0 else 0
        ad_ratio = (advances / declines) if declines > 0 else 0
        ad_diff = advances - declines
        
        result = {
            'trade_date': trade_date,
            'advances': advances,
            'declines': declines,
            'unchanged': unchanged,
            'total_stocks': total,
            'advance_pct': round(advance_pct, 2),
            'decline_pct': round(decline_pct, 2),
            'unchanged_pct': round(unchanged_pct, 2),
            'advance_decline_ratio': round(ad_ratio, 4),
            'advance_decline_diff': ad_diff
        }
        
        logger.info(
            f"  {trade_date}: A={advances} D={declines} U={unchanged} "
            f"Total={total} ({advance_pct:.1f}% advance)"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"  {trade_date}: Error computing - {e}")
        return None


def save_advance_decline(data: Dict, engine, force_update: bool = False):
    """
    Save advance/decline data to database
    
    Args:
        data: Dictionary with advance/decline counts
        engine: SQLAlchemy engine
        force_update: If True, use REPLACE instead of INSERT IGNORE
    """
    if force_update:
        query = text("""
            REPLACE INTO nifty500_advance_decline 
            (trade_date, advances, declines, unchanged, total_stocks,
             advance_pct, decline_pct, unchanged_pct, 
             advance_decline_ratio, advance_decline_diff)
            VALUES 
            (:trade_date, :advances, :declines, :unchanged, :total_stocks,
             :advance_pct, :decline_pct, :unchanged_pct,
             :advance_decline_ratio, :advance_decline_diff)
        """)
    else:
        query = text("""
            INSERT IGNORE INTO nifty500_advance_decline 
            (trade_date, advances, declines, unchanged, total_stocks,
             advance_pct, decline_pct, unchanged_pct, 
             advance_decline_ratio, advance_decline_diff)
            VALUES 
            (:trade_date, :advances, :declines, :unchanged, :total_stocks,
             :advance_pct, :decline_pct, :unchanged_pct,
             :advance_decline_ratio, :advance_decline_diff)
        """)
    
    with engine.connect() as conn:
        conn.execute(query, data)
        conn.commit()


def compute_date_range(
    start_date: date,
    end_date: date,
    force_update: bool = False,
    progress_callback=None
) -> Dict[str, int]:
    """
    Compute advance/decline for a date range
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        force_update: If True, recompute existing dates
        progress_callback: Optional callback function(current, total, message)
        
    Returns:
        Dictionary with statistics
    """
    engine = get_db_engine()
    symbols = get_nifty500_symbols()
    
    logger.info(f"Computing advance/decline from {start_date} to {end_date}")
    logger.info(f"Using {len(symbols)} stocks from Yahoo Finance data")
    
    # Get all dates in range that have data
    query = text("""
        SELECT DISTINCT date 
        FROM yfinance_daily_quotes 
        WHERE symbol IN :symbols
            AND date BETWEEN :start_date AND :end_date
        ORDER BY date
    """)
    
    with engine.connect() as conn:
        # Convert symbols list to tuple for SQL IN clause
        result = conn.execute(
            text("""
                SELECT DISTINCT date 
                FROM yfinance_daily_quotes 
                WHERE date BETWEEN :start_date AND :end_date
                ORDER BY date
            """),
            {'start_date': start_date, 'end_date': end_date}
        )
        dates = [row[0] for row in result]
    
    if not dates:
        logger.warning("No dates found in range")
        return {'processed': 0, 'new': 0, 'updated': 0, 'skipped': 0, 'failed': 0}
    
    logger.info(f"Found {len(dates)} trading days in range")
    
    stats = {'processed': 0, 'new': 0, 'updated': 0, 'skipped': 0, 'failed': 0}
    
    for i, trade_date in enumerate(dates):
        if progress_callback:
            progress_callback(i + 1, len(dates), f"Processing {trade_date}")
        
        try:
            # Compute
            result = compute_advance_decline_for_date(
                trade_date, symbols, engine, force_update
            )
            
            if result is None:
                stats['skipped'] += 1
            else:
                # Save to database
                save_advance_decline(result, engine, force_update)
                if force_update:
                    stats['updated'] += 1
                else:
                    stats['new'] += 1
            
            stats['processed'] += 1
            
        except Exception as e:
            logger.error(f"Failed to process {trade_date}: {e}")
            stats['failed'] += 1
    
    logger.info(
        f"Completed: {stats['processed']} processed, "
        f"{stats['new']} new, {stats['updated']} updated, "
        f"{stats['skipped']} skipped, {stats['failed']} failed"
    )
    
    return stats


def compute_last_n_days(days: int = 180, force_update: bool = False) -> Dict[str, int]:
    """
    Compute advance/decline for last N days
    
    Args:
        days: Number of days to go back
        force_update: If True, recompute existing dates
        
    Returns:
        Statistics dictionary
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return compute_date_range(start_date, end_date, force_update)


def get_advance_decline_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """
    Retrieve advance/decline data from database
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Optional limit on number of records
        
    Returns:
        DataFrame with advance/decline data
    """
    engine = get_db_engine()
    
    query = """
        SELECT 
            trade_date,
            advances,
            declines,
            unchanged,
            total_stocks,
            advance_pct,
            decline_pct,
            unchanged_pct,
            advance_decline_ratio,
            advance_decline_diff,
            computed_at
        FROM nifty500_advance_decline
        WHERE 1=1
    """
    
    params = {}
    
    if start_date:
        query += " AND trade_date >= :start_date"
        params['start_date'] = start_date
    
    if end_date:
        query += " AND trade_date <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY trade_date ASC"  # Changed to ASC for chronological order
    
    if limit:
        query += f" LIMIT {limit}"
    
    df = pd.read_sql(text(query), engine, params=params)
    return df


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Compute Nifty 500 advance/decline counts'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=180,
        help='Number of days to compute (default: 180)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recompute existing dates'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Nifty 500 Advance-Decline Calculator")
    print("=" * 60)
    
    if args.start_date and args.end_date:
        start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        stats = compute_date_range(start, end, args.force)
    else:
        stats = compute_last_n_days(args.days, args.force)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Processed: {stats['processed']}")
    print(f"  New entries: {stats['new']}")
    print(f"  Updated: {stats['updated']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")
    print("=" * 60)
