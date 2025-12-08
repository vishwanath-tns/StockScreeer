"""
Intraday Data Fetcher
=====================
High-performance parallel data fetcher for Nifty 50 intraday data.
Fetches 5-minute candles from Yahoo Finance with intelligent caching.

For SMA calculations:
- SMA 10: Needs 10 bars = 50 minutes of data
- SMA 20: Needs 20 bars = 100 minutes  
- SMA 50: Needs 50 bars = 250 minutes (~1 trading day)
- SMA 200: Needs 200 bars = 1000 minutes (~3 trading days)

We fetch last 5 trading days to ensure enough history for SMA 200.
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
from urllib.parse import quote_plus
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


class IntradayDataFetcher:
    """
    High-performance data fetcher for Nifty 50 intraday data.
    
    Features:
    - Parallel downloading using ThreadPoolExecutor
    - Database caching for historical data
    - Smart delta updates (only fetch what's needed)
    - Memory-efficient data structures
    """
    
    # Nifty 50 constituents (as of Dec 2024) with Yahoo Finance symbols
    NIFTY_50_SYMBOLS = [
        'ADANIENT.NS', 'ADANIPORTS.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AXISBANK.NS',
        'BAJAJ-AUTO.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BEL.NS', 'BPCL.NS',
        'BHARTIARTL.NS', 'BRITANNIA.NS', 'CIPLA.NS', 'COALINDIA.NS', 'DRREDDY.NS',
        'EICHERMOT.NS', 'GRASIM.NS', 'HCLTECH.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS',
        'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'INDUSINDBK.NS',
        'INFY.NS', 'ITC.NS', 'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LT.NS',
        'M&M.NS', 'MARUTI.NS', 'NESTLEIND.NS', 'NTPC.NS', 'ONGC.NS',
        'POWERGRID.NS', 'RELIANCE.NS', 'SBILIFE.NS', 'SHRIRAMFIN.NS', 'SBIN.NS',
        'SUNPHARMA.NS', 'TATACONSUM.NS', 'TMPV.NS', 'TATASTEEL.NS', 'TCS.NS',
        'TECHM.NS', 'TITAN.NS', 'TRENT.NS', 'ULTRACEMCO.NS', 'WIPRO.NS'
    ]
    
    # Nifty 50 Index symbol
    NIFTY_INDEX_SYMBOL = '^NSEI'
    
    # Trading hours (IST)
    MARKET_OPEN = (9, 15)   # 9:15 AM
    MARKET_CLOSE = (15, 30)  # 3:30 PM
    
    # Data requirements
    BARS_NEEDED_FOR_SMA200 = 200
    TRADING_BARS_PER_DAY = 75  # 9:15 to 15:30 = 375 mins / 5 = 75 bars
    DAYS_TO_FETCH = 5  # Enough for SMA 200
    
    def __init__(self, use_cache: bool = True, max_workers: int = 10):
        """
        Initialize the data fetcher.
        
        Args:
            use_cache: Whether to use database cache
            max_workers: Number of parallel download threads
        """
        self.use_cache = use_cache
        self.max_workers = max_workers
        self.engine = self._create_engine() if use_cache else None
        
        # In-memory cache
        self._stock_data_cache: Dict[str, pd.DataFrame] = {}
        self._index_data_cache: Optional[pd.DataFrame] = None
        self._cache_timestamp: Optional[datetime] = None
        
        # Track if initial full load has been done
        self._initial_load_done: bool = False
        
    def _create_engine(self):
        """Create SQLAlchemy engine."""
        try:
            pwd = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
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
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            return None
    
    def _is_market_hours(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now()
        # Check if weekday
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        current_time = (now.hour, now.minute)
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE
    
    def _get_date_range(self) -> Tuple[str, str]:
        """Get date range for data fetch (last N trading days)."""
        end_date = date.today()
        # Go back enough days to get DAYS_TO_FETCH trading days
        start_date = end_date - timedelta(days=self.DAYS_TO_FETCH + 4)  # Extra buffer for weekends
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def fetch_nifty_index(self, force_refresh: bool = False, max_retries: int = 3) -> pd.DataFrame:
        """
        Fetch Nifty 50 index 5-minute data with retry logic.
        
        Args:
            force_refresh: Force download even if cache is fresh
            max_retries: Maximum number of retry attempts on failure
            
        Returns:
            DataFrame with datetime index and OHLCV columns
        """
        # Check cache first (return cached data if fresh)
        if not force_refresh and self._index_data_cache is not None:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < 300:  # 5 minutes cache
                logger.info("Returning cached index data")
                return self._index_data_cache
        
        # If we have cached data and hit rate limit, return cached data
        start_date, end_date = self._get_date_range()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching Nifty index data from {start_date} to {end_date} (attempt {attempt + 1})")
                
                ticker = yf.Ticker(self.NIFTY_INDEX_SYMBOL)
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval='5m',
                    prepost=False
                )
                
                if df.empty:
                    logger.warning("No Nifty index data returned")
                    # Return cached data if available
                    if self._index_data_cache is not None:
                        logger.info("Returning stale cached data")
                        return self._index_data_cache
                    return pd.DataFrame()
                
                # Standardize columns
                df = df.rename(columns={
                    'Open': 'open', 'High': 'high', 'Low': 'low',
                    'Close': 'close', 'Volume': 'volume'
                })
                
                # Keep only needed columns
                df = df[['open', 'high', 'low', 'close', 'volume']].copy()
                
                # Convert timezone to IST if needed
                if df.index.tz is not None:
                    df.index = df.index.tz_convert('Asia/Kolkata').tz_localize(None)
                
                # Filter to market hours
                df = df.between_time('09:15', '15:30')
                
                # Update cache
                self._index_data_cache = df
                self._cache_timestamp = datetime.now()
                
                logger.info(f"Fetched {len(df)} Nifty index bars")
                return df
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'rate' in error_msg or 'too many' in error_msg or '429' in error_msg:
                    # Rate limited - wait and retry
                    wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry...")
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error fetching Nifty index: {e}")
                    # Return cached data if available
                    if self._index_data_cache is not None:
                        logger.info("Returning stale cached data due to error")
                        return self._index_data_cache
                    if attempt < max_retries - 1:
                        continue
                    return pd.DataFrame()
        
        # All retries failed - return cached data if available
        if self._index_data_cache is not None:
            logger.info("All retries failed, returning stale cached data")
            return self._index_data_cache
        return pd.DataFrame()
    
    def check_db_has_history(self, min_days: int = 3) -> bool:
        """
        Check if database has sufficient historical data for SMA calculations.
        
        Args:
            min_days: Minimum number of trading days required
            
        Returns:
            True if DB has enough data, False otherwise
        """
        if not self.engine:
            return False
        
        try:
            with self.engine.connect() as conn:
                # Check how many trading days of 5min data exist
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT DATE(datetime)) as days,
                           MIN(datetime) as min_dt,
                           MAX(datetime) as max_dt
                    FROM yfinance_intraday_quotes
                    WHERE timeframe = '5m'
                      AND datetime >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                """))
                row = result.fetchone()
                
                if row and row[0] >= min_days:
                    logger.info(f"DB has {row[0]} days of data ({row[1]} to {row[2]})")
                    return True
                    
                logger.info(f"DB has only {row[0] if row else 0} days - need full fetch")
                return False
                
        except Exception as e:
            logger.warning(f"Error checking DB history: {e}")
            return False
    
    def fetch_latest_only(self, max_retries: int = 3) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Fetch only the latest/current candles for incremental update.
        Uses period='1d' to get only today's data (much faster than 5d).
        
        Returns:
            Tuple of (index_df, stock_data_dict) with latest data only
        """
        logger.info("Fetching latest data only (incremental update)...")
        
        # Fetch index - only today
        index_df = pd.DataFrame()
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(self.NIFTY_INDEX_SYMBOL)
                df = ticker.history(period='1d', interval='5m', prepost=False)
                
                if not df.empty:
                    df = df.rename(columns={
                        'Open': 'open', 'High': 'high', 'Low': 'low',
                        'Close': 'close', 'Volume': 'volume'
                    })
                    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
                    
                    if df.index.tz is not None:
                        df.index = df.index.tz_convert('Asia/Kolkata').tz_localize(None)
                    
                    df = df.between_time('09:15', '15:30')
                    index_df = df
                    break
                    
            except Exception as e:
                if 'rate' in str(e).lower() or '429' in str(e):
                    time.sleep((attempt + 1) * 2)
                    continue
                logger.warning(f"Error fetching latest index: {e}")
                break
        
        # Batch download stocks - only today
        stock_data = {}
        try:
            data = yf.download(
                self.NIFTY_50_SYMBOLS,
                period='1d',
                interval='5m',
                group_by='ticker',
                progress=False,
                threads=True
            )
            
            if not data.empty:
                for symbol in self.NIFTY_50_SYMBOLS:
                    try:
                        if symbol in data.columns.get_level_values(0):
                            df = data[symbol].copy()
                            df = df.rename(columns={
                                'Open': 'open', 'High': 'high', 'Low': 'low',
                                'Close': 'close', 'Volume': 'volume'
                            })
                            
                            # Handle column case variations
                            df.columns = df.columns.str.lower()
                            
                            if 'close' in df.columns and not df['close'].dropna().empty:
                                df = df[['open', 'high', 'low', 'close', 'volume']].copy()
                                
                                if df.index.tz is not None:
                                    df.index = df.index.tz_convert('Asia/Kolkata').tz_localize(None)
                                
                                df = df.between_time('09:15', '15:30')
                                df = df.dropna(subset=['close'])
                                
                                if not df.empty:
                                    stock_data[symbol] = df
                    except Exception as e:
                        logger.debug(f"Error processing {symbol}: {e}")
                        
        except Exception as e:
            logger.warning(f"Error batch downloading stocks: {e}")
        
        logger.info(f"Latest fetch: {len(index_df)} index bars, {len(stock_data)} stocks")
        return index_df, stock_data
    
    def merge_data(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge old and new data, keeping unique timestamps.
        New data takes precedence for overlapping timestamps.
        
        Args:
            old_df: Existing historical data
            new_df: New data to merge
            
        Returns:
            Merged DataFrame with updated data
        """
        if old_df.empty:
            return new_df
        if new_df.empty:
            return old_df
        
        # Combine and keep latest for duplicates
        combined = pd.concat([old_df, new_df])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        
        return combined
    
    def update_cache_incremental(self, latest_index: pd.DataFrame, 
                                  latest_stocks: Dict[str, pd.DataFrame]) -> None:
        """
        Update in-memory cache with incremental data.
        
        Args:
            latest_index: Latest index data
            latest_stocks: Dict of latest stock data
        """
        # Update index cache
        if not latest_index.empty:
            if self._index_data_cache is not None:
                self._index_data_cache = self.merge_data(self._index_data_cache, latest_index)
            else:
                self._index_data_cache = latest_index
        
        # Update stock cache
        for symbol, df in latest_stocks.items():
            if not df.empty:
                if symbol in self._stock_data_cache:
                    self._stock_data_cache[symbol] = self.merge_data(
                        self._stock_data_cache[symbol], df
                    )
                else:
                    self._stock_data_cache[symbol] = df
        
        self._cache_timestamp = datetime.now()
        logger.info(f"Cache updated: {len(self._index_data_cache)} index bars, "
                   f"{len(self._stock_data_cache)} stocks")
    
    def get_cached_data(self) -> Tuple[Optional[pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        Get currently cached data.
        
        Returns:
            Tuple of (index_df, stock_data_dict)
        """
        return self._index_data_cache, self._stock_data_cache
    
    def is_initial_load_done(self) -> bool:
        """Check if initial full load has been completed."""
        return self._initial_load_done and self._index_data_cache is not None
    
    def mark_initial_load_done(self):
        """Mark that initial full load is complete."""
        self._initial_load_done = True
        logger.info("Initial load marked as complete")

    def _fetch_single_stock(self, symbol: str, start_date: str, end_date: str) -> Tuple[str, pd.DataFrame]:
        """Fetch data for a single stock (used in parallel execution)."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval='5m',
                prepost=False
            )
            
            if df.empty:
                return symbol, pd.DataFrame()
            
            # Standardize columns
            df = df.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low',
                'Close': 'close', 'Volume': 'volume'
            })
            
            df = df[['open', 'high', 'low', 'close', 'volume']].copy()
            
            # Convert timezone
            if df.index.tz is not None:
                df.index = df.index.tz_convert('Asia/Kolkata').tz_localize(None)
            
            # Filter to market hours
            df = df.between_time('09:15', '15:30')
            
            return symbol, df
            
        except Exception as e:
            logger.warning(f"Error fetching {symbol}: {e}")
            return symbol, pd.DataFrame()
    
    def fetch_all_stocks(self, 
                         force_refresh: bool = False,
                         progress_callback=None) -> Dict[str, pd.DataFrame]:
        """
        Fetch 5-minute data for all Nifty 50 stocks in parallel.
        
        Args:
            force_refresh: Force download even if cache is fresh
            progress_callback: Optional callback(current, total, symbol) for progress
            
        Returns:
            Dict mapping symbol to DataFrame
        """
        # Check cache freshness
        if not force_refresh and self._stock_data_cache:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < 300:  # 5 minutes cache
                logger.info("Using cached stock data")
                return self._stock_data_cache
        
        start_date, end_date = self._get_date_range()
        results = {}
        
        logger.info(f"Fetching data for {len(self.NIFTY_50_SYMBOLS)} stocks in parallel")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._fetch_single_stock, symbol, start_date, end_date): symbol 
                for symbol in self.NIFTY_50_SYMBOLS
            }
            
            completed = 0
            for future in as_completed(futures):
                symbol, df = future.result()
                if not df.empty:
                    results[symbol] = df
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(self.NIFTY_50_SYMBOLS), symbol)
        
        elapsed = time.time() - start_time
        logger.info(f"Fetched {len(results)} stocks in {elapsed:.2f}s")
        
        # Update cache
        self._stock_data_cache = results
        self._cache_timestamp = datetime.now()
        
        return results
    
    def fetch_from_database(self, 
                           symbols: List[str] = None,
                           days_back: int = 5) -> Dict[str, pd.DataFrame]:
        """
        Fetch data from database cache (faster than Yahoo Finance).
        
        Args:
            symbols: List of symbols (default: Nifty 50)
            days_back: Number of days of data to fetch
            
        Returns:
            Dict mapping symbol to DataFrame
        """
        if not self.engine:
            logger.warning("Database not available, using Yahoo Finance")
            return self.fetch_all_stocks()
        
        symbols = symbols or [s.replace('.NS', '') for s in self.NIFTY_50_SYMBOLS]
        start_date = (date.today() - timedelta(days=days_back + 2)).strftime('%Y-%m-%d')
        
        results = {}
        
        try:
            with self.engine.connect() as conn:
                for symbol in symbols:
                    query = text("""
                        SELECT datetime, open, high, low, close, volume
                        FROM yfinance_intraday_quotes
                        WHERE symbol = :symbol
                          AND timeframe = '5m'
                          AND datetime >= :start_date
                        ORDER BY datetime
                    """)
                    
                    df = pd.read_sql(query, conn, params={
                        'symbol': symbol,
                        'start_date': start_date
                    })
                    
                    if not df.empty:
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        df.set_index('datetime', inplace=True)
                        results[symbol + '.NS'] = df
            
            logger.info(f"Loaded {len(results)} stocks from database")
            return results
            
        except Exception as e:
            logger.error(f"Database fetch error: {e}")
            return self.fetch_all_stocks()
    
    def get_latest_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the most recent data."""
        if self._index_data_cache is not None and not self._index_data_cache.empty:
            return self._index_data_cache.index[-1].to_pydatetime()
        return None
    
    def get_cache_info(self) -> Dict:
        """Get information about the current cache state."""
        return {
            'stocks_cached': len(self._stock_data_cache),
            'index_cached': self._index_data_cache is not None,
            'cache_timestamp': self._cache_timestamp,
            'cache_age_seconds': (datetime.now() - self._cache_timestamp).total_seconds() if self._cache_timestamp else None
        }


# Quick test
if __name__ == "__main__":
    fetcher = IntradayDataFetcher(use_cache=True, max_workers=10)
    
    # Test index fetch
    print("Fetching Nifty index...")
    index_df = fetcher.fetch_nifty_index()
    print(f"Index data: {len(index_df)} bars")
    if not index_df.empty:
        print(f"  Date range: {index_df.index[0]} to {index_df.index[-1]}")
        print(index_df.tail())
    
    # Test stock fetch
    print("\nFetching Nifty 50 stocks...")
    def progress(current, total, symbol):
        print(f"  {current}/{total}: {symbol}", end='\r')
    
    stocks = fetcher.fetch_all_stocks(progress_callback=progress)
    print(f"\nFetched {len(stocks)} stocks")
    
    for symbol, df in list(stocks.items())[:3]:
        print(f"  {symbol}: {len(df)} bars")
