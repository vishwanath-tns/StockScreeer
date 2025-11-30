#!/usr/bin/env python3
"""
Historical Bollinger Bands Backfill (Yahoo Finance Data)

One-time script to compute and store historical BB indicators for all stocks
and indices using Yahoo Finance daily data from yfinance_daily_quotes table.

Usage:
    python bollinger/backfill_historical_bb.py

Options:
    --start-date    Start date for backfill (default: 2020-01-01)
    --end-date      End date for backfill (default: today)
    --symbols       Comma-separated list of symbols (default: all)
    --batch-size    Symbols per batch (default: 50)
    --workers       Parallel workers (default: 4)
    --indices-only  Only process indices (symbols starting with ^)
    --stocks-only   Only process stocks (exclude indices)
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BackfillStats:
    """Statistics from backfill run."""
    total_symbols: int = 0
    symbols_processed: int = 0
    symbols_failed: int = 0
    total_records: int = 0
    records_inserted: int = 0
    start_time: datetime = None
    end_time: datetime = None
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_sec(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def records_per_sec(self) -> float:
        if self.duration_sec > 0:
            return self.records_inserted / self.duration_sec
        return 0.0


class HistoricalBBBackfill:
    """
    Backfill historical Bollinger Bands data.
    
    Computes BB indicators for all trading days in the specified range
    and stores them in stock_bollinger_daily table.
    """
    
    def __init__(self, engine: Engine):
        self.engine = engine
        
    def get_engine(self) -> Engine:
        """Get database engine from environment variables."""
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_DB', 'stockdata')
        
        conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        return create_engine(conn_str, pool_pre_ping=True, pool_size=10)
    
    def ensure_tables(self):
        """Create tables if they don't exist."""
        from bollinger.services.daily_bb_compute import create_bb_tables
        create_bb_tables(self.engine)
        logger.info("BB tables verified/created")
    
    def get_all_symbols(self, indices_only: bool = False, stocks_only: bool = False) -> List[str]:
        """Get all unique symbols from Yahoo Finance data (stocks + indices)."""
        if indices_only:
            query = """
                SELECT DISTINCT symbol 
                FROM yfinance_daily_quotes 
                WHERE symbol LIKE '^%%'
                ORDER BY symbol
            """
        elif stocks_only:
            query = """
                SELECT DISTINCT symbol 
                FROM yfinance_daily_quotes 
                WHERE symbol NOT LIKE '^%%'
                ORDER BY symbol
            """
        else:
            # Get indices first, then stocks
            query = """
                SELECT DISTINCT symbol 
                FROM yfinance_daily_quotes 
                ORDER BY 
                    CASE WHEN symbol LIKE '^%%' THEN 0 ELSE 1 END,
                    symbol
            """
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [row[0] for row in result]
    
    def get_symbol_date_range(self, symbol: str) -> Tuple[date, date]:
        """Get the date range available for a symbol."""
        query = """
            SELECT MIN(date), MAX(date)
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"symbol": symbol}).fetchone()
            if result and result[0] and result[1]:
                return result[0], result[1]
            return None, None
    
    def get_existing_dates(self, symbol: str) -> set:
        """Get dates already computed for a symbol."""
        query = """
            SELECT trade_date FROM stock_bollinger_daily
            WHERE symbol = :symbol
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"symbol": symbol})
            return {row[0] for row in result}
    
    def fetch_ohlc_history(self, symbol: str, 
                           start_date: date, 
                           end_date: date) -> pd.DataFrame:
        """Fetch complete OHLC history for a symbol from Yahoo Finance data."""
        # Add buffer for BB calculation (need 20+ days before start_date)
        buffer_start = start_date - timedelta(days=60)
        
        query = """
            SELECT date as trade_date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol
              AND date BETWEEN :start_date AND :end_date
            ORDER BY date ASC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(
                text(query),
                conn,
                params={
                    'symbol': symbol,
                    'start_date': buffer_start,
                    'end_date': end_date
                }
            )
        
        return df
    
    def calculate_bb_series(self, df: pd.DataFrame, 
                            period: int = 20, 
                            std_dev: float = 2.0) -> pd.DataFrame:
        """
        Calculate Bollinger Bands for entire series.
        
        Returns DataFrame with BB indicators for each date.
        """
        if len(df) < period:
            return pd.DataFrame()
        
        # Calculate SMA (middle band)
        df['middle_band'] = df['close'].rolling(window=period).mean()
        
        # Calculate standard deviation
        df['std'] = df['close'].rolling(window=period).std()
        
        # Calculate bands
        df['upper_band'] = df['middle_band'] + (std_dev * df['std'])
        df['lower_band'] = df['middle_band'] - (std_dev * df['std'])
        
        # Calculate %b = (close - lower) / (upper - lower)
        df['percent_b'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
        
        # Calculate Bandwidth = (upper - lower) / middle * 100
        df['bandwidth'] = ((df['upper_band'] - df['lower_band']) / df['middle_band']) * 100
        
        # Calculate bandwidth percentile over 126-day rolling window
        df['bandwidth_percentile'] = df['bandwidth'].rolling(window=126, min_periods=20).apply(
            lambda x: (x.values < x.values[-1]).sum() / len(x) * 100 if len(x) > 0 else 50
        )
        
        # Detect squeeze (bottom 10% of bandwidth)
        df['is_squeeze'] = df['bandwidth_percentile'] <= 10
        
        # Detect bulge (top 10% of bandwidth)  
        df['is_bulge'] = df['bandwidth_percentile'] >= 90
        
        # Count consecutive squeeze days
        df['squeeze_days'] = 0
        squeeze_count = 0
        for i in range(len(df)):
            if df.iloc[i]['is_squeeze']:
                squeeze_count += 1
            else:
                squeeze_count = 0
            df.iloc[i, df.columns.get_loc('squeeze_days')] = squeeze_count
        
        # Classify trend based on %b (rolling 5-day average)
        df['pb_avg'] = df['percent_b'].rolling(window=5).mean()
        
        def classify_trend(pb_avg):
            if pd.isna(pb_avg):
                return 'neutral', 50.0
            if pb_avg > 0.7:
                return 'uptrend', min((pb_avg - 0.5) * 200, 100)
            elif pb_avg < 0.3:
                return 'downtrend', min((0.5 - pb_avg) * 200, 100)
            else:
                return 'neutral', 50 - abs(pb_avg - 0.5) * 100
        
        trends = df['pb_avg'].apply(lambda x: classify_trend(x))
        df['trend'] = trends.apply(lambda x: x[0])
        df['trend_strength'] = trends.apply(lambda x: x[1])
        
        # Count consecutive trend days
        df['trend_days'] = 0
        trend_count = 0
        last_trend = None
        for i in range(len(df)):
            current_trend = df.iloc[i]['trend']
            if current_trend == last_trend and current_trend != 'neutral':
                trend_count += 1
            else:
                trend_count = 1
            df.iloc[i, df.columns.get_loc('trend_days')] = trend_count
            last_trend = current_trend
        
        # Distance from middle band
        df['distance_from_middle'] = ((df['close'] - df['middle_band']) / df['middle_band']) * 100
        
        # SMA 20 (same as middle)
        df['sma_20'] = df['middle_band']
        
        # Drop buffer rows and NaN rows
        df = df.dropna(subset=['middle_band', 'percent_b', 'bandwidth'])
        
        return df
    
    def process_symbol(self, symbol: str, 
                       start_date: date, 
                       end_date: date,
                       skip_existing: bool = True) -> Tuple[int, Optional[str]]:
        """
        Process a single symbol: fetch data, calculate BB, store results.
        
        Returns: (records_inserted, error_message or None)
        """
        try:
            # Check existing dates if skipping
            existing_dates = set()
            if skip_existing:
                existing_dates = self.get_existing_dates(symbol)
            
            # Fetch OHLC data
            df = self.fetch_ohlc_history(symbol, start_date, end_date)
            
            if df.empty or len(df) < 30:
                return 0, f"Insufficient data ({len(df)} rows)"
            
            # Calculate BB series
            bb_df = self.calculate_bb_series(df)
            
            if bb_df.empty:
                return 0, "BB calculation failed"
            
            # Filter to requested date range
            bb_df = bb_df[bb_df['trade_date'] >= start_date]
            bb_df = bb_df[bb_df['trade_date'] <= end_date]
            
            # Skip existing dates
            if skip_existing and existing_dates:
                bb_df = bb_df[~bb_df['trade_date'].isin(existing_dates)]
            
            if bb_df.empty:
                return 0, None  # All dates already exist
            
            # Prepare for insert
            bb_df['symbol'] = symbol
            
            # Select columns for insert
            columns = [
                'symbol', 'trade_date', 'close', 'upper_band', 'middle_band',
                'lower_band', 'percent_b', 'bandwidth', 'bandwidth_percentile',
                'is_squeeze', 'is_bulge', 'squeeze_days', 'trend', 
                'trend_strength', 'trend_days', 'sma_20', 'distance_from_middle'
            ]
            
            insert_df = bb_df[columns].copy()
            
            # Insert to database
            with self.engine.begin() as conn:
                insert_df.to_sql(
                    'stock_bollinger_daily',
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=500
                )
            
            return len(insert_df), None
            
        except Exception as e:
            return 0, str(e)
    
    def run(self,
            start_date: date,
            end_date: date,
            symbols: Optional[List[str]] = None,
            batch_size: int = 50,
            max_workers: int = 4,
            skip_existing: bool = True,
            indices_only: bool = False,
            stocks_only: bool = False,
            progress_callback: Optional[callable] = None) -> BackfillStats:
        """
        Run the historical backfill.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            symbols: List of symbols (None = all)
            batch_size: Symbols per batch for progress reporting
            max_workers: Parallel workers
            skip_existing: Skip dates already in database
            indices_only: Only process indices (symbols starting with ^)
            stocks_only: Only process stocks (exclude indices)
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            BackfillStats with results
        """
        stats = BackfillStats()
        stats.start_time = datetime.now()
        
        # Ensure tables exist
        self.ensure_tables()
        
        # Get symbols
        if symbols is None:
            symbols = self.get_all_symbols(indices_only=indices_only, stocks_only=stocks_only)
        
        stats.total_symbols = len(symbols)
        
        symbol_type = "indices" if indices_only else ("stocks" if stocks_only else "symbols (stocks + indices)")
        logger.info(f"Starting backfill for {stats.total_symbols} {symbol_type} from {start_date} to {end_date}")
        
        if progress_callback:
            progress_callback(0, stats.total_symbols, f"Starting backfill for {stats.total_symbols} {symbol_type}...")
        
        # Process symbols in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.process_symbol, symbol, start_date, end_date, skip_existing
                ): symbol for symbol in symbols
            }
            
            for i, future in enumerate(as_completed(futures)):
                symbol = futures[future]
                
                try:
                    records, error = future.result()
                    
                    if error:
                        stats.symbols_failed += 1
                        stats.errors.append(f"{symbol}: {error}")
                        logger.warning(f"Failed {symbol}: {error}")
                    else:
                        stats.symbols_processed += 1
                        stats.records_inserted += records
                        
                except Exception as e:
                    stats.symbols_failed += 1
                    stats.errors.append(f"{symbol}: {str(e)}")
                    logger.error(f"Error processing {symbol}: {e}")
                
                # Progress update
                if (i + 1) % 10 == 0 or (i + 1) == stats.total_symbols:
                    pct = int((i + 1) / stats.total_symbols * 100)
                    msg = f"Processed {i+1}/{stats.total_symbols} symbols ({stats.records_inserted:,} records)"
                    logger.info(msg)
                    if progress_callback:
                        progress_callback(i + 1, stats.total_symbols, msg)
        
        stats.end_time = datetime.now()
        
        logger.info(f"Backfill complete: {stats.symbols_processed} symbols, "
                   f"{stats.records_inserted:,} records in {stats.duration_sec:.1f}s "
                   f"({stats.records_per_sec:.0f} records/sec)")
        
        return stats


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Backfill historical Bollinger Bands data (Yahoo Finance)")
    parser.add_argument('--start-date', type=str, default='2020-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='End date (YYYY-MM-DD, default: today)')
    parser.add_argument('--symbols', type=str, default=None,
                       help='Comma-separated list of symbols')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Symbols per batch')
    parser.add_argument('--workers', type=int, default=4,
                       help='Parallel workers')
    parser.add_argument('--no-skip-existing', action='store_true',
                       help='Recalculate existing dates')
    parser.add_argument('--indices-only', action='store_true',
                       help='Only process indices (symbols starting with ^)')
    parser.add_argument('--stocks-only', action='store_true',
                       help='Only process stocks (exclude indices)')
    
    args = parser.parse_args()
    
    # Validate mutually exclusive options
    if args.indices_only and args.stocks_only:
        print("Error: --indices-only and --stocks-only are mutually exclusive")
        return
    
    # Parse dates
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date() if args.end_date else date.today()
    
    # Parse symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]  # Don't uppercase - indices have ^
    
    # Get engine
    from urllib.parse import quote_plus
    
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    database = os.getenv('MYSQL_DB', 'stockdata')
    
    # URL-encode password to handle special characters like @
    encoded_password = quote_plus(password)
    conn_str = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
    engine = create_engine(conn_str, pool_pre_ping=True, pool_size=10)
    
    # Run backfill
    backfill = HistoricalBBBackfill(engine)
    
    def progress(current, total, message):
        pct = int(current / total * 100) if total > 0 else 0
        print(f"\r[{pct:3d}%] {message}", end='', flush=True)
    
    # Determine symbol type label
    symbol_type = "Indices only" if args.indices_only else ("Stocks only" if args.stocks_only else "All (stocks + indices)")
    
    print("=" * 60)
    print("BOLLINGER BANDS HISTORICAL BACKFILL (Yahoo Finance Data)")
    print("=" * 60)
    print(f"Data Source: yfinance_daily_quotes table")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Symbols: {symbol_type if symbols is None else len(symbols)}")
    print(f"Workers: {args.workers}")
    print(f"Skip Existing: {not args.no_skip_existing}")
    print("=" * 60)
    print()
    
    stats = backfill.run(
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        batch_size=args.batch_size,
        max_workers=args.workers,
        skip_existing=not args.no_skip_existing,
        indices_only=args.indices_only,
        stocks_only=args.stocks_only,
        progress_callback=progress
    )
    
    print()
    print()
    print("=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Symbols Processed: {stats.symbols_processed}/{stats.total_symbols}")
    print(f"Symbols Failed: {stats.symbols_failed}")
    print(f"Records Inserted: {stats.records_inserted:,}")
    print(f"Duration: {stats.duration_sec:.1f} seconds")
    print(f"Speed: {stats.records_per_sec:.0f} records/second")
    
    if stats.errors:
        print()
        print(f"Errors ({len(stats.errors)}):")
        for err in stats.errors[:20]:  # Show first 20
            print(f"  - {err}")
        if len(stats.errors) > 20:
            print(f"  ... and {len(stats.errors) - 20} more")
    
    return stats


if __name__ == "__main__":
    main()
