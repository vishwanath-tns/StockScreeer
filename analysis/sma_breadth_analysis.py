"""
SMA Breadth Analysis Module
===========================

Comprehensive analysis of percentage of stocks above various SMAs (5,10,20,50,100,150,200).
Includes peak/trough detection and market turn prediction.

Features:
- Calculate and store all SMAs (5, 10, 20, 50, 100, 150, 200)
- Compute % of stocks above/below each SMA for Nifty 50 and Nifty 500
- Detect peaks and troughs in percentage data
- Analyze which SMA predicts market turns

Author: Stock Screener Project
Date: 2025-12-07
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

# ============================================================================
# Database Connection
# ============================================================================

def get_engine(database: str = 'marketdata'):
    """Create SQLAlchemy engine for database connection."""
    url = URL.create(
        drivername='mysql+pymysql',
        username=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        database=database,
        query={'charset': 'utf8mb4'}
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


# ============================================================================
# SMA Periods Configuration
# ============================================================================

SMA_PERIODS = [5, 10, 20, 50, 100, 150, 200]
SMA_COLUMNS = {p: f'sma_{p}' for p in SMA_PERIODS}

# Nifty 50 symbols (without .NS suffix for internal use)
NIFTY_50_SYMBOLS = [
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
    'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE',
    'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC',
    'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT',
    'M&M', 'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC',
    'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
    'SUNPHARMA', 'TCS', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL',
    'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
]


# ============================================================================
# Step 1: Check and Add Missing SMA Columns
# ============================================================================

def check_sma_columns(engine) -> Dict[int, bool]:
    """Check which SMA columns exist in yfinance_daily_ma table."""
    with engine.connect() as conn:
        result = conn.execute(text("DESCRIBE yfinance_daily_ma"))
        existing_cols = {row[0] for row in result}
    
    status = {}
    for period in SMA_PERIODS:
        col_name = SMA_COLUMNS[period]
        status[period] = col_name in existing_cols
    
    return status


def add_missing_sma_columns(engine, progress_cb=None) -> List[int]:
    """Add missing SMA columns to yfinance_daily_ma table."""
    status = check_sma_columns(engine)
    missing = [p for p, exists in status.items() if not exists]
    
    if not missing:
        if progress_cb:
            progress_cb("All SMA columns already exist")
        return []
    
    with engine.begin() as conn:
        for period in missing:
            col_name = SMA_COLUMNS[period]
            if progress_cb:
                progress_cb(f"Adding column {col_name}...")
            conn.execute(text(f"""
                ALTER TABLE yfinance_daily_ma 
                ADD COLUMN {col_name} DECIMAL(15,4) NULL AFTER close
            """))
    
    return missing


def calculate_missing_smas(engine, progress_cb=None, batch_size: int = 50) -> int:
    """Calculate missing SMA values using data from yfinance_daily_ma itself (continuous data)."""
    status = check_sma_columns(engine)
    missing = [p for p, exists in status.items() if not exists]
    
    if missing:
        add_missing_sma_columns(engine, progress_cb)
    
    # Get all symbols from yfinance_daily_ma (which has continuous data)
    with engine.connect() as conn:
        symbols = conn.execute(text("""
            SELECT DISTINCT symbol FROM yfinance_daily_ma
        """)).fetchall()
        symbols = [s[0] for s in symbols]
    
    total = len(symbols)
    updated = 0
    
    if progress_cb:
        progress_cb(f"Calculating SMAs for {total} symbols using continuous data...")
    
    # Periods that might need calculation (10, 20, 100)
    periods_to_calc = [10, 20, 100]
    
    for i, symbol in enumerate(symbols):
        if progress_cb and i % 50 == 0:
            progress_cb(f"Processing {i+1}/{total}: {symbol}")
        
        with engine.begin() as conn:
            # Get price data from yfinance_daily_ma (this has continuous dates)
            df = pd.read_sql(text("""
                SELECT date, close FROM yfinance_daily_ma
                WHERE symbol = :symbol
                ORDER BY date
            """), conn, params={'symbol': symbol})
            
            if df.empty or len(df) < max(periods_to_calc):
                continue
            
            # Calculate only the missing SMAs (10, 20, 100)
            for period in periods_to_calc:
                col_name = SMA_COLUMNS[period]
                df[col_name] = df['close'].rolling(window=period, min_periods=period).mean()
            
            # Update table - batch update for efficiency
            for idx, row in df.iterrows():
                updates = {}
                for period in periods_to_calc:
                    col_name = SMA_COLUMNS[period]
                    if pd.notna(row.get(col_name)):
                        updates[col_name] = float(row[col_name])
                
                if updates:
                    set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    updates['symbol'] = symbol
                    updates['date'] = row['date']
                    conn.execute(text(f"""
                        UPDATE yfinance_daily_ma
                        SET {set_clause}
                        WHERE symbol = :symbol AND date = :date
                    """), updates)
            
            updated += 1
    
    if progress_cb:
        progress_cb(f"Completed! Updated {updated} symbols")
    
    return updated


# ============================================================================
# Step 2: Calculate Percentage of Stocks Above/Below SMA
# ============================================================================

@dataclass
class SMABreadthResult:
    """Result of SMA breadth calculation for a single date."""
    date: datetime
    index_name: str
    sma_period: int
    total_stocks: int
    above_count: int
    below_count: int
    pct_above: float
    pct_below: float


def get_nifty500_symbols(engine) -> List[str]:
    """Get Nifty 500 symbols from database."""
    try:
        # Try importing from utilities
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
        return [f"{s}.NS" for s in NIFTY_500_STOCKS]
    except ImportError:
        # Fallback: get from database
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT symbol FROM yfinance_daily_quotes
                WHERE timeframe = 'daily' AND symbol LIKE '%.NS'
            """))
            return [r[0] for r in result]


def calculate_sma_breadth(
    engine,
    index_name: str = 'NIFTY 500',
    sma_period: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    progress_cb=None
) -> pd.DataFrame:
    """
    Calculate percentage of stocks above/below a specific SMA.
    
    Args:
        engine: SQLAlchemy engine
        index_name: 'NIFTY 50' or 'NIFTY 500'
        sma_period: SMA period (5, 10, 20, 50, 100, 150, 200)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        DataFrame with columns: date, total, above, below, pct_above, pct_below
    """
    sma_col = SMA_COLUMNS.get(sma_period)
    if not sma_col:
        raise ValueError(f"Invalid SMA period: {sma_period}. Valid: {SMA_PERIODS}")
    
    # Get symbol list based on index
    if index_name == 'NIFTY 50':
        symbols = [f"{s}.NS" for s in NIFTY_50_SYMBOLS]
    else:
        symbols = get_nifty500_symbols(engine)
    
    if progress_cb:
        progress_cb(f"Calculating {index_name} breadth for SMA {sma_period}...")
    
    # Build query
    symbol_list = "', '".join(symbols)
    
    query = f"""
        SELECT 
            date,
            COUNT(*) as total_stocks,
            SUM(CASE WHEN close > {sma_col} THEN 1 ELSE 0 END) as above_count,
            SUM(CASE WHEN close < {sma_col} THEN 1 ELSE 0 END) as below_count,
            SUM(CASE WHEN close = {sma_col} THEN 1 ELSE 0 END) as equal_count,
            ROUND(SUM(CASE WHEN close > {sma_col} THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_above,
            ROUND(SUM(CASE WHEN close < {sma_col} THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_below
        FROM yfinance_daily_ma
        WHERE symbol IN ('{symbol_list}')
        AND {sma_col} IS NOT NULL
    """
    
    params = {}
    if start_date:
        query += " AND date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND date <= :end_date"
        params['end_date'] = end_date
    
    query += " GROUP BY date ORDER BY date"
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params if params else None)
    
    df['date'] = pd.to_datetime(df['date'])
    df['index_name'] = index_name
    df['sma_period'] = sma_period
    
    if progress_cb:
        progress_cb(f"Found {len(df)} days of data")
    
    return df


def calculate_all_sma_breadth(
    engine,
    index_name: str = 'NIFTY 500',
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    progress_cb=None
) -> pd.DataFrame:
    """Calculate breadth for all SMA periods."""
    all_results = []
    
    for period in SMA_PERIODS:
        if progress_cb:
            progress_cb(f"Processing SMA {period}...")
        
        df = calculate_sma_breadth(
            engine, index_name, period, start_date, end_date
        )
        all_results.append(df)
    
    combined = pd.concat(all_results, ignore_index=True)
    return combined


# ============================================================================
# Step 3: Store Results in Database
# ============================================================================

def ensure_breadth_table(engine):
    """Create table for storing SMA breadth data."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sma_breadth_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE NOT NULL,
                index_name VARCHAR(20) NOT NULL,
                sma_period INT NOT NULL,
                total_stocks INT,
                above_count INT,
                below_count INT,
                pct_above DECIMAL(5,2),
                pct_below DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY idx_date_index_sma (date, index_name, sma_period)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))


def store_breadth_data(engine, df: pd.DataFrame, progress_cb=None):
    """Store breadth data in database."""
    ensure_breadth_table(engine)
    
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO sma_breadth_data 
                (date, index_name, sma_period, total_stocks, above_count, below_count, pct_above, pct_below)
                VALUES (:date, :index_name, :sma_period, :total, :above, :below, :pct_above, :pct_below)
                ON DUPLICATE KEY UPDATE
                    total_stocks = VALUES(total_stocks),
                    above_count = VALUES(above_count),
                    below_count = VALUES(below_count),
                    pct_above = VALUES(pct_above),
                    pct_below = VALUES(pct_below)
            """), {
                'date': row['date'],
                'index_name': row['index_name'],
                'sma_period': row['sma_period'],
                'total': row['total_stocks'],
                'above': row['above_count'],
                'below': row['below_count'],
                'pct_above': row['pct_above'],
                'pct_below': row['pct_below']
            })
    
    if progress_cb:
        progress_cb(f"Stored {len(df)} records")


def load_breadth_data(
    engine,
    index_name: str = 'NIFTY 500',
    sma_period: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """Load stored breadth data from database."""
    query = "SELECT * FROM sma_breadth_data WHERE index_name = :index_name"
    params = {'index_name': index_name}
    
    if sma_period:
        query += " AND sma_period = :sma_period"
        params['sma_period'] = sma_period
    if start_date:
        query += " AND date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND date <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY date, sma_period"
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    
    df['date'] = pd.to_datetime(df['date'])
    return df


# ============================================================================
# Step 4: Peak and Trough Detection
# ============================================================================

def detect_peaks_troughs(
    df: pd.DataFrame,
    column: str = 'pct_above',
    window: int = 5,
    threshold: float = 10.0
) -> pd.DataFrame:
    """
    Detect peaks and troughs in percentage data.
    
    Args:
        df: DataFrame with date and percentage columns
        column: Column to analyze
        window: Rolling window for local extrema detection
        threshold: Minimum distance between consecutive peaks/troughs
    
    Returns:
        DataFrame with peak and trough markers
    """
    df = df.copy()
    values = df[column].values
    
    # Find local maxima (peaks) and minima (troughs)
    peaks = []
    troughs = []
    
    for i in range(window, len(values) - window):
        # Check if this is a local maximum
        if all(values[i] >= values[i-j] for j in range(1, window+1)) and \
           all(values[i] >= values[i+j] for j in range(1, window+1)):
            peaks.append(i)
        
        # Check if this is a local minimum
        if all(values[i] <= values[i-j] for j in range(1, window+1)) and \
           all(values[i] <= values[i+j] for j in range(1, window+1)):
            troughs.append(i)
    
    # Mark peaks and troughs
    df['is_peak'] = False
    df['is_trough'] = False
    
    df.iloc[peaks, df.columns.get_loc('is_peak')] = True
    df.iloc[troughs, df.columns.get_loc('is_trough')] = True
    
    # Filter by threshold (significant peaks/troughs)
    significant_peaks = []
    significant_troughs = []
    
    # Filter peaks: only keep if value > threshold above surrounding
    for idx in peaks:
        if values[idx] >= threshold:
            significant_peaks.append(idx)
    
    # Filter troughs: only keep if value < (100 - threshold)
    for idx in troughs:
        if values[idx] <= (100 - threshold):
            significant_troughs.append(idx)
    
    df['is_significant_peak'] = False
    df['is_significant_trough'] = False
    
    if significant_peaks:
        df.iloc[significant_peaks, df.columns.get_loc('is_significant_peak')] = True
    if significant_troughs:
        df.iloc[significant_troughs, df.columns.get_loc('is_significant_trough')] = True
    
    return df


def get_peaks_troughs_summary(
    engine,
    index_name: str = 'NIFTY 500',
    sma_period: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Get summary of peaks and troughs for analysis."""
    df = load_breadth_data(engine, index_name, sma_period, start_date, end_date)
    
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    df = detect_peaks_troughs(df, 'pct_above')
    
    peaks_df = df[df['is_significant_peak']][['date', 'pct_above', 'pct_below']]
    troughs_df = df[df['is_significant_trough']][['date', 'pct_above', 'pct_below']]
    
    return peaks_df, troughs_df


# ============================================================================
# Step 5: Market Turn Prediction Analysis
# ============================================================================

def analyze_predictive_power(
    engine,
    index_name: str = 'NIFTY 500',
    forward_days: List[int] = [5, 10, 20, 50],
    progress_cb=None
) -> pd.DataFrame:
    """
    Analyze which SMA period best predicts market turns.
    
    Tests correlation between:
    - Peaks in % above SMA -> subsequent market decline
    - Troughs in % above SMA -> subsequent market rally
    """
    results = []
    
    # Load Nifty index data - prefer Yahoo Finance for complete data
    nifty_df = get_nifty_index_data(engine, use_yahoo=True)
    
    if nifty_df is None or nifty_df.empty:
        if progress_cb:
            progress_cb("No Nifty index data found")
        return pd.DataFrame()
    
    nifty_df['date'] = pd.to_datetime(nifty_df['date'])
    nifty_df = nifty_df.set_index('date')
    
    # Calculate forward returns
    for days in forward_days:
        nifty_df[f'fwd_{days}d_ret'] = nifty_df['close'].pct_change(days).shift(-days) * 100
    
    for sma_period in SMA_PERIODS:
        if progress_cb:
            progress_cb(f"Analyzing SMA {sma_period}...")
        
        breadth_df = load_breadth_data(engine, index_name, sma_period)
        if breadth_df.empty:
            continue
        
        breadth_df = detect_peaks_troughs(breadth_df, 'pct_above')
        
        # Get peaks and troughs
        peaks = breadth_df[breadth_df['is_significant_peak']].copy()
        troughs = breadth_df[breadth_df['is_significant_trough']].copy()
        
        for days in forward_days:
            col = f'fwd_{days}d_ret'
            
            # Match peaks with forward returns
            if not peaks.empty:
                peaks_matched = peaks.set_index('date').join(nifty_df[[col]], how='left')
                avg_ret_after_peak = peaks_matched[col].mean()
                pct_negative = (peaks_matched[col] < 0).mean() * 100 if len(peaks_matched) > 0 else 0
            else:
                avg_ret_after_peak = None
                pct_negative = None
            
            # Match troughs with forward returns
            if not troughs.empty:
                troughs_matched = troughs.set_index('date').join(nifty_df[[col]], how='left')
                avg_ret_after_trough = troughs_matched[col].mean()
                pct_positive = (troughs_matched[col] > 0).mean() * 100 if len(troughs_matched) > 0 else 0
            else:
                avg_ret_after_trough = None
                pct_positive = None
            
            results.append({
                'sma_period': sma_period,
                'forward_days': days,
                'term': 'short' if days <= 10 else 'medium' if days <= 30 else 'long',
                'num_peaks': len(peaks),
                'num_troughs': len(troughs),
                'avg_ret_after_peak': avg_ret_after_peak,
                'pct_decline_after_peak': pct_negative,
                'avg_ret_after_trough': avg_ret_after_trough,
                'pct_rally_after_trough': pct_positive
            })
    
    return pd.DataFrame(results)


# ============================================================================
# Step 6: Get Nifty Index Data for Visualization
# ============================================================================

def get_nifty_index_data(
    engine,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    use_yahoo: bool = True
) -> pd.DataFrame:
    """
    Get Nifty 50 index price data.
    
    Args:
        engine: SQLAlchemy engine
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        use_yahoo: If True, download fresh data from Yahoo Finance (recommended)
    
    Returns:
        DataFrame with date, open, high, low, close columns
    """
    if use_yahoo:
        try:
            import yfinance as yf
            
            # Download from Yahoo Finance
            start = start_date or '2024-01-01'
            end = end_date or datetime.now().strftime('%Y-%m-%d')
            
            nifty = yf.download('^NSEI', start=start, end=end, progress=False)
            
            if not nifty.empty:
                df = nifty.reset_index()
                # Handle multi-level columns from yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
                else:
                    df.columns = [col.lower() for col in df.columns]
                
                df = df.rename(columns={'date': 'date'})
                df['date'] = pd.to_datetime(df['date'])
                
                return df[['date', 'open', 'high', 'low', 'close']]
        except Exception as e:
            print(f"Yahoo Finance download failed: {e}, falling back to database")
    
    # Fallback to database
    query = """
        SELECT trade_date as date, open, high, low, close
        FROM indices_daily
        WHERE index_name = 'NIFTY 50'
    """
    params = {}
    
    if start_date:
        query += " AND trade_date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND trade_date <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY trade_date"
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params if params else None)
    
    df['date'] = pd.to_datetime(df['date'])
    return df


# ============================================================================
# Verification Functions
# ============================================================================

def verify_data_availability(engine) -> Dict:
    """Verify data availability for SMA analysis."""
    result = {
        'yfinance_daily_ma': {},
        'yfinance_daily_quotes': {},
        'indices_daily': {},
        'sma_columns': {},
        'nifty_symbols': {}
    }
    
    with engine.connect() as conn:
        # Check yfinance_daily_ma
        r = conn.execute(text("""
            SELECT COUNT(*) as cnt, MIN(date) as min_date, MAX(date) as max_date,
                   COUNT(DISTINCT symbol) as symbols
            FROM yfinance_daily_ma
        """)).fetchone()
        result['yfinance_daily_ma'] = {
            'rows': r[0], 'min_date': str(r[1]), 'max_date': str(r[2]), 'symbols': r[3]
        }
        
        # Check yfinance_daily_quotes
        r = conn.execute(text("""
            SELECT COUNT(*) as cnt, MIN(date) as min_date, MAX(date) as max_date,
                   COUNT(DISTINCT symbol) as symbols
            FROM yfinance_daily_quotes WHERE timeframe = 'daily'
        """)).fetchone()
        result['yfinance_daily_quotes'] = {
            'rows': r[0], 'min_date': str(r[1]), 'max_date': str(r[2]), 'symbols': r[3]
        }
        
        # Check indices_daily
        r = conn.execute(text("""
            SELECT COUNT(*) as cnt, MIN(trade_date) as min_date, MAX(trade_date) as max_date
            FROM indices_daily WHERE index_name = 'NIFTY 50'
        """)).fetchone()
        result['indices_daily'] = {
            'rows': r[0], 'min_date': str(r[1]), 'max_date': str(r[2])
        }
    
    # Check SMA columns
    result['sma_columns'] = check_sma_columns(engine)
    
    # Check Nifty symbol counts
    nifty50_available = []
    nifty50_missing = []
    
    with engine.connect() as conn:
        for symbol in NIFTY_50_SYMBOLS:
            r = conn.execute(text("""
                SELECT COUNT(*) FROM yfinance_daily_ma WHERE symbol = :sym
            """), {'sym': f"{symbol}.NS"}).fetchone()
            if r[0] > 0:
                nifty50_available.append(symbol)
            else:
                nifty50_missing.append(symbol)
    
    result['nifty_symbols'] = {
        'nifty50_available': len(nifty50_available),
        'nifty50_missing': nifty50_missing[:10]  # First 10 missing
    }
    
    return result


# ============================================================================
# Main Functions for CLI
# ============================================================================

def run_full_calculation(engine, index_name: str = 'NIFTY 500', progress_cb=None):
    """Run full SMA breadth calculation and store results."""
    if progress_cb:
        progress_cb("=" * 50)
        progress_cb(f"Running SMA Breadth Analysis for {index_name}")
        progress_cb("=" * 50)
    
    # Step 1: Ensure all SMA columns exist
    if progress_cb:
        progress_cb("\n[1/4] Checking SMA columns...")
    status = check_sma_columns(engine)
    missing = [p for p, exists in status.items() if not exists]
    if missing:
        if progress_cb:
            progress_cb(f"Missing columns: {missing}")
        add_missing_sma_columns(engine, progress_cb)
    else:
        if progress_cb:
            progress_cb("All SMA columns present: " + ", ".join([f"sma_{p}" for p in SMA_PERIODS]))
    
    # Step 2: Calculate breadth for all SMAs
    if progress_cb:
        progress_cb("\n[2/4] Calculating SMA breadth...")
    breadth_df = calculate_all_sma_breadth(engine, index_name, progress_cb=progress_cb)
    
    if progress_cb:
        progress_cb(f"Calculated {len(breadth_df)} data points")
    
    # Step 3: Store results
    if progress_cb:
        progress_cb("\n[3/4] Storing results...")
    store_breadth_data(engine, breadth_df, progress_cb)
    
    # Step 4: Verify
    if progress_cb:
        progress_cb("\n[4/4] Verification...")
        loaded = load_breadth_data(engine, index_name)
        progress_cb(f"Verified: {len(loaded)} records in database")
        
        # Show sample
        progress_cb("\nSample data (last 5 days, SMA 50):")
        sample = loaded[loaded['sma_period'] == 50].tail(5)
        for _, row in sample.iterrows():
            progress_cb(f"  {row['date'].date()}: {row['pct_above']:.1f}% above SMA 50")
    
    return breadth_df


if __name__ == '__main__':
    print("SMA Breadth Analysis Module")
    print("=" * 50)
    
    engine = get_engine()
    
    # Verify data availability
    print("\n[1] Verifying data availability...")
    info = verify_data_availability(engine)
    
    print(f"\nyfinance_daily_ma: {info['yfinance_daily_ma']['rows']:,} rows")
    print(f"  Date range: {info['yfinance_daily_ma']['min_date']} to {info['yfinance_daily_ma']['max_date']}")
    print(f"  Symbols: {info['yfinance_daily_ma']['symbols']}")
    
    print(f"\nSMA columns status:")
    for period, exists in info['sma_columns'].items():
        status = "✅" if exists else "❌"
        print(f"  sma_{period}: {status}")
    
    print(f"\nNifty 50 symbols: {info['nifty_symbols']['nifty50_available']}/50 available")
    if info['nifty_symbols']['nifty50_missing']:
        print(f"  Missing: {info['nifty_symbols']['nifty50_missing']}")
    
    # Run calculation for NIFTY 500
    print("\n" + "=" * 50)
    run_full_calculation(engine, 'NIFTY 500', print)
    
    # Also for NIFTY 50
    print("\n" + "=" * 50)
    run_full_calculation(engine, 'NIFTY 50', print)
    
    print("\n✅ Done!")
