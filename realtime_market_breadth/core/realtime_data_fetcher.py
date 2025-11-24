"""
Real-Time Data Fetcher
======================

Fetches 1-minute candle data from Yahoo Finance.
Gets the most recent candle's close price as LTP (Last Traded Price).
Includes rate limiting and error handling.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
from typing import List, Dict, Optional, Tuple
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def rate_limit(calls_per_minute=20):
    """
    Decorator to limit API calls
    
    Args:
        calls_per_minute: Maximum calls allowed per minute
    """
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait_time = min_interval - elapsed
            if wait_time > 0:
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator


class RealTimeDataFetcher:
    """Fetch real-time (1-min candle) data from Yahoo Finance"""
    
    def __init__(self, batch_size=50, max_retries=3, calls_per_minute=20):
        """
        Initialize fetcher
        
        Args:
            batch_size: Number of symbols to fetch per API call
            max_retries: Maximum retry attempts for failed requests
            calls_per_minute: Rate limit for API calls
        """
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.calls_per_minute = calls_per_minute
        self.failed_symbols = {}  # Track failed symbols and retry count
        self.prev_close_cache = {}  # Cache for previous close prices (loaded once)
        self.cache_loaded = False
        
    @rate_limit(calls_per_minute=20)
    def _fetch_batch_1min(self, symbols: List[str]) -> pd.DataFrame:
        """
        Fetch 1-minute data for a batch of symbols
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            DataFrame with 1-minute candles
        """
        try:
            # Fetch last 5 minutes of 1-minute data
            data = yf.download(
                symbols,
                period="1d",
                interval="1m",
                progress=False,
                group_by='ticker',
                auto_adjust=False,
                threads=True
            )
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching batch of {len(symbols)} symbols: {e}")
            return pd.DataFrame()
    
    def extract_ltp_from_1min_candles(self, data: pd.DataFrame, symbols: List[str]) -> Dict[str, Dict]:
        """
        Extract Last Traded Price (LTP) and ALL candles from 1-min data
        
        Args:
            data: DataFrame with 1-minute candle data
            symbols: List of symbols
            
        Returns:
            Dict with symbol -> {ltp, timestamp, prev_close, volume, all_candles: [...]}
        """
        results = {}
        
        if data.empty:
            return results
        
        # Handle single symbol case
        if len(symbols) == 1:
            symbol = symbols[0]
            if not data.empty and 'Close' in data.columns:
                # Get the most recent candle for LTP
                last_candle = data.iloc[-1]
                
                # Extract all candles
                all_candles = []
                for idx, row in data.iterrows():
                    if pd.notna(row['Close']):
                        all_candles.append({
                            'timestamp': idx,
                            'open': float(row['Open']) if pd.notna(row['Open']) else None,
                            'high': float(row['High']) if pd.notna(row['High']) else None,
                            'low': float(row['Low']) if pd.notna(row['Low']) else None,
                            'ltp': float(row['Close']) if pd.notna(row['Close']) else None,
                            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                        })
                
                results[symbol] = {
                    'ltp': float(last_candle['Close']) if pd.notna(last_candle['Close']) else None,
                    'open': float(last_candle['Open']) if pd.notna(last_candle['Open']) else None,
                    'high': float(last_candle['High']) if pd.notna(last_candle['High']) else None,
                    'low': float(last_candle['Low']) if pd.notna(last_candle['Low']) else None,
                    'volume': int(last_candle['Volume']) if pd.notna(last_candle['Volume']) else 0,
                    'timestamp': data.index[-1] if len(data.index) > 0 else datetime.now(),
                    'all_candles': all_candles  # All 1-min candles
                }
        else:
            # Handle multiple symbols
            for symbol in symbols:
                try:
                    if symbol in data.columns.get_level_values(0):
                        symbol_data = data[symbol]
                        
                        if not symbol_data.empty and 'Close' in symbol_data.columns:
                            # Get the most recent candle for LTP
                            last_candle = symbol_data.iloc[-1]
                            
                            # Extract all candles
                            all_candles = []
                            for idx, row in symbol_data.iterrows():
                                if pd.notna(row['Close']):
                                    all_candles.append({
                                        'timestamp': idx,
                                        'open': float(row['Open']) if pd.notna(row['Open']) else None,
                                        'high': float(row['High']) if pd.notna(row['High']) else None,
                                        'low': float(row['Low']) if pd.notna(row['Low']) else None,
                                        'ltp': float(row['Close']) if pd.notna(row['Close']) else None,
                                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                                    })
                            
                            results[symbol] = {
                                'ltp': float(last_candle['Close']) if pd.notna(last_candle['Close']) else None,
                                'open': float(last_candle['Open']) if pd.notna(last_candle['Open']) else None,
                                'high': float(last_candle['High']) if pd.notna(last_candle['High']) else None,
                                'low': float(last_candle['Low']) if pd.notna(last_candle['Low']) else None,
                                'volume': int(last_candle['Volume']) if pd.notna(last_candle['Volume']) else 0,
                                'timestamp': symbol_data.index[-1] if len(symbol_data.index) > 0 else datetime.now(),
                                'all_candles': all_candles  # All 1-min candles
                            }
                
                except Exception as e:
                    logger.warning(f"Error extracting LTP for {symbol}: {e}")
                    continue
        
        return results
    
    def load_previous_close_cache(self, symbols: List[str]) -> None:
        """
        Load previous close prices from database ONCE at startup and cache them.
        
        Args:
            symbols: List of stock symbols to load prev close for
        """
        if self.cache_loaded:
            logger.info("Previous close cache already loaded, skipping")
            return
        
        logger.info(f"Loading previous close prices from database for {len(symbols)} symbols...")
        self.prev_close_cache = self.fetch_previous_close(symbols)
        self.cache_loaded = True
        logger.info(f"✅ Cached previous close for {len(self.prev_close_cache)} symbols")
    
    def fetch_previous_close(self, symbols: List[str]) -> Dict[str, float]:
        """
        Fetch previous day's close price from database (yfinance_daily_quotes)
        
        Args:
            symbols: List of stock symbols (with .NS suffix)
            
        Returns:
            Dict with symbol -> previous_close
        """
        results = {}
        
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.engine import URL
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            # Create database connection
            url = URL.create(
                drivername="mysql+pymysql",
                username=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                database=os.getenv('MYSQL_DB', 'marketdata'),
                query={"charset": "utf8mb4"},
            )
            
            engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
            
            with engine.connect() as conn:
                # Get yesterday's close for all symbols
                # Use MAX(date) to get the most recent available date (handles weekends/holidays)
                placeholders = ', '.join([f':sym{i}' for i in range(len(symbols))])
                sql = text(f"""
                    SELECT symbol, close
                    FROM yfinance_daily_quotes
                    WHERE symbol IN ({placeholders})
                      AND date = (
                          SELECT MAX(date) 
                          FROM yfinance_daily_quotes 
                          WHERE date < CURDATE()
                      )
                """)
                
                # Build params dict
                params = {f'sym{i}': sym for i, sym in enumerate(symbols)}
                
                result = conn.execute(sql, params)
                
                for row in result:
                    results[row[0]] = float(row[1])
                
                logger.info(f"✅ Fetched prev close from DB for {len(results)}/{len(symbols)} symbols")
            
            engine.dispose()
            
        except Exception as e:
            logger.warning(f"DB prev close failed: {e}, falling back to Yahoo Finance")
            # Fallback to Yahoo Finance
            try:
                data = yf.download(
                    symbols,
                    period="2d",
                    interval="1d",
                    progress=False,
                    auto_adjust=False,
                    group_by='ticker',
                    threads=True
                )
                
                if not data.empty:
                    if len(symbols) == 1:
                        symbol = symbols[0]
                        if 'Close' in data.columns and len(data) >= 1:
                            results[symbol] = float(data['Close'].iloc[-1])
                    else:
                        for symbol in symbols:
                            try:
                                if symbol in data.columns.get_level_values(0):
                                    symbol_data = data[symbol]
                                    if not symbol_data.empty and 'Close' in symbol_data.columns:
                                        results[symbol] = float(symbol_data['Close'].iloc[-1])
                            except:
                                continue
            except Exception as e2:
                logger.error(f"Yahoo Finance fallback also failed: {e2}")
        
        return results
    
    def fetch_realtime_data(self, symbols: List[str], include_prev_close=True) -> Dict[str, Dict]:
        """
        Fetch real-time data (1-min candles) for all symbols with batching.
        Uses cached previous close prices (loaded once at startup).
        
        Args:
            symbols: List of stock symbols
            include_prev_close: Whether to include previous close prices from cache
            
        Returns:
            Dict with symbol -> {ltp, prev_close, timestamp, volume, ...}
        """
        all_results = {}
        
        # Split into batches
        batches = [symbols[i:i+self.batch_size] for i in range(0, len(symbols), self.batch_size)]
        
        logger.info(f"Fetching data for {len(symbols)} symbols in {len(batches)} batches")
        
        # Fetch current 1-min candle data
        logger.info("Fetching current 1-min candle data...")
        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} symbols)")
            
            try:
                # Fetch 1-min data
                data = self._fetch_batch_1min(batch)
                
                # Extract LTP from candles
                batch_results = self.extract_ltp_from_1min_candles(data, batch)
                
                # Add previous close from CACHE (not fetching again!)
                if include_prev_close:
                    for symbol, info in batch_results.items():
                        if symbol in self.prev_close_cache:
                            info['prev_close'] = self.prev_close_cache[symbol]
                        else:
                            info['prev_close'] = None
                
                all_results.update(batch_results)
                
                logger.debug(f"Batch {i+1}: Got data for {len(batch_results)}/{len(batch)} symbols")
            
            except Exception as e:
                logger.error(f"Error processing batch {i+1}: {e}")
                continue
        
        logger.info(f"Successfully fetched data for {len(all_results)}/{len(symbols)} symbols")
        
        return all_results
    
    def fetch_realtime_data_parallel(self, symbols: List[str], max_workers=5) -> Dict[str, Dict]:
        """
        Fetch real-time data using parallel thread pool (faster but more API calls)
        
        Args:
            symbols: List of stock symbols
            max_workers: Number of parallel threads
            
        Returns:
            Dict with symbol -> {ltp, prev_close, timestamp, volume, ...}
        """
        all_results = {}
        
        # Split into batches
        batches = [symbols[i:i+self.batch_size] for i in range(0, len(symbols), self.batch_size)]
        
        logger.info(f"Fetching data for {len(symbols)} symbols in {len(batches)} batches (parallel)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batch jobs
            future_to_batch = {
                executor.submit(self._fetch_batch_1min, batch): batch 
                for batch in batches
            }
            
            # Process completed futures
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    data = future.result()
                    batch_results = self.extract_ltp_from_1min_candles(data, batch)
                    all_results.update(batch_results)
                    logger.debug(f"Got data for {len(batch_results)}/{len(batch)} symbols")
                except Exception as e:
                    logger.error(f"Batch failed: {e}")
        
        # Fetch previous close prices
        logger.info("Fetching previous close prices...")
        for batch in batches:
            prev_close_batch = self.fetch_previous_close(batch)
            for symbol, prev_close in prev_close_batch.items():
                if symbol in all_results:
                    all_results[symbol]['prev_close'] = prev_close
        
        logger.info(f"Successfully fetched data for {len(all_results)}/{len(symbols)} symbols")
        
        return all_results


if __name__ == "__main__":
    # Test the fetcher
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test with a few symbols
    test_symbols = [
        'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 
        'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS'
    ]
    
    print("=" * 70)
    print("Real-Time Data Fetcher - Test (1-Minute Candles)")
    print("=" * 70)
    
    fetcher = RealTimeDataFetcher(batch_size=4, calls_per_minute=20)
    
    print(f"\nFetching real-time data for {len(test_symbols)} test symbols...")
    print(f"Note: This uses 1-minute candles from Yahoo Finance\n")
    
    start_time = time.time()
    data = fetcher.fetch_realtime_data(test_symbols)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Fetch completed in {elapsed:.2f} seconds")
    print(f"Got data for {len(data)}/{len(test_symbols)} symbols\n")
    
    # Display results
    print("=" * 70)
    print("Symbol Data:")
    print("=" * 70)
    
    for symbol, info in sorted(data.items()):
        ltp = info.get('ltp')
        prev_close = info.get('prev_close')
        timestamp = info.get('timestamp')
        volume = info.get('volume', 0)
        
        if ltp and prev_close:
            change = ltp - prev_close
            change_pct = (change / prev_close) * 100
            status = "🟢 UP" if change > 0 else "🔴 DOWN" if change < 0 else "⚪ UNCH"
            
            print(f"\n{symbol}:")
            print(f"  LTP: ₹{ltp:.2f}")
            print(f"  Prev Close: ₹{prev_close:.2f}")
            print(f"  Change: ₹{change:+.2f} ({change_pct:+.2f}%) {status}")
            print(f"  Volume: {volume:,}")
            print(f"  Timestamp: {timestamp}")
        else:
            print(f"\n{symbol}: ⚠️  Data incomplete")
            print(f"  LTP: {ltp}")
            print(f"  Prev Close: {prev_close}")
    
    print("\n" + "=" * 70)
