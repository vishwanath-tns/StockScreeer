"""
Historical Data Downloader
==========================
Downloads daily and intraday historical data from Dhan API.

Dhan Historical Data API:
- Endpoint: /charts/historical (daily), /charts/intraday (1m,5m,15m,25m,60m)
- Provides OHLCV data for stocks, indices, F&O
- Daily data: Unlimited history, max 2000 candles per request
- Intraday data: 5 years max, but only 90 days can be polled at once

Daily data: 20 years = 7300 days = ~5200 trading days (need ~3 requests per stock)
1-min data: 5 years = 1825 days x 375 mins = ~684K candles per stock 
           (90 days/chunk = ~21 chunks per stock, each ~33K candles)

Optimizations:
- Multi-threaded parallel downloads (configurable workers)
- Bulk database inserts via temp tables
- Thread-safe rate limiting
"""
import os
import sys
import time
import logging
import requests
import threading
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv
from dataclasses import dataclass, field
from queue import Queue

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """Track download progress."""
    total_stocks: int = 0
    completed_stocks: int = 0
    failed_stocks: int = 0
    total_candles: int = 0
    current_symbol: str = ""
    status: str = "idle"  # idle, running, paused, completed, error
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    
    def increment_completed(self, candles: int = 0):
        """Thread-safe increment of completed count."""
        with self._lock:
            self.completed_stocks += 1
            self.total_candles += candles
    
    def increment_failed(self):
        """Thread-safe increment of failed count."""
        with self._lock:
            self.failed_stocks += 1


class DhanHistoricalAPI:
    """Dhan Historical Data API Client with thread-safe rate limiting."""
    
    BASE_URL = "https://api.dhan.co/v2"
    
    # Exchange segment codes for Dhan API
    EXCHANGE_SEGMENTS = {
        'NSE_EQ': 'NSE_EQ',
        'BSE_EQ': 'BSE_EQ',
        'NSE_FNO': 'NSE_FNO',
        'BSE_FNO': 'BSE_FNO',
        'IDX_I': 'IDX_I',  # Indices
    }
    
    # Class-level rate limiting (shared across all instances)
    _rate_lock = threading.Lock()
    _last_request_time = 0
    _request_delay = 0.25  # 250ms = 4 requests/sec (safe limit)
    
    def __init__(self):
        """Initialize API client."""
        self.access_token = os.getenv('DHAN_ACCESS_TOKEN', '')
        self.client_id = os.getenv('DHAN_CLIENT_ID', '')
        
        if not self.access_token:
            raise ValueError("DHAN_ACCESS_TOKEN not set in environment")
        
        # Thread-local session
        self._local = threading.local()
    
    @property
    def session(self):
        """Get thread-local session."""
        if not hasattr(self._local, 'session'):
            self._local.session = requests.Session()
            self._local.session.headers.update({
                'access-token': self.access_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        return self._local.session
    
    def _rate_limit(self):
        """Thread-safe rate limiting."""
        with DhanHistoricalAPI._rate_lock:
            elapsed = time.time() - DhanHistoricalAPI._last_request_time
            if elapsed < DhanHistoricalAPI._request_delay:
                time.sleep(DhanHistoricalAPI._request_delay - elapsed)
            DhanHistoricalAPI._last_request_time = time.time()
    
    def get_historical_data(
        self,
        security_id: int,
        exchange_segment: str,
        instrument: str,
        from_date: str,
        to_date: str,
        interval: str = "day"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data.
        
        Args:
            security_id: Dhan security ID
            exchange_segment: NSE_EQ, BSE_EQ, NSE_FNO, etc.
            instrument: EQUITY, OPTIDX, FUTIDX, etc.
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: 1m, 5m, 15m, 25m, 60m, day
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/charts/historical"
        
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment,
            "instrument": instrument,
            "expiryCode": 0,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Dhan returns data in specific format
                if data and 'open' in data:
                    df = pd.DataFrame({
                        'timestamp': data.get('timestamp', []),
                        'open': data.get('open', []),
                        'high': data.get('high', []),
                        'low': data.get('low', []),
                        'close': data.get('close', []),
                        'volume': data.get('volume', [])
                    })
                    
                    if not df.empty:
                        # Convert timestamp to datetime
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        return df
                    
                return None
                
            elif response.status_code == 401:
                logger.error("Authentication failed - check access token")
                raise ValueError("Invalid access token")
            elif response.status_code == 429:
                logger.warning("Rate limited - waiting 60s")
                time.sleep(60)
                return self.get_historical_data(security_id, exchange_segment, instrument, from_date, to_date, interval)
            else:
                logger.warning(f"API returned {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for security {security_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data for {security_id}: {e}")
            return None
    
    def get_intraday_data(
        self,
        security_id: int,
        exchange_segment: str,
        instrument: str,
        from_date: str,
        to_date: str,
        interval: str = "1"  # 1 minute
    ) -> Optional[pd.DataFrame]:
        """
        Fetch intraday OHLCV data.
        
        Args:
            security_id: Dhan security ID  
            exchange_segment: NSE_EQ, BSE_EQ, etc.
            instrument: EQUITY, INDEX, etc.
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: 1, 5, 15, 25, 60 (minutes)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/charts/intraday"
        
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment,
            "instrument": instrument,
            "interval": interval,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and 'open' in data:
                    df = pd.DataFrame({
                        'timestamp': data.get('timestamp', []),
                        'open': data.get('open', []),
                        'high': data.get('high', []),
                        'low': data.get('low', []),
                        'close': data.get('close', []),
                        'volume': data.get('volume', [])
                    })
                    
                    if not df.empty:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        return df
                
                return None
            else:
                logger.warning(f"Intraday API returned {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching intraday for {security_id}: {e}")
            return None


class HistoricalDownloader:
    """Downloads historical data for all stocks in dhan_stocks table."""
    
    def __init__(self):
        """Initialize downloader."""
        self.api = DhanHistoricalAPI()
        self.engine = self._get_engine()
        self.progress = DownloadProgress()
    
    def _get_engine(self):
        """Create database engine."""
        pw = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
        user = os.getenv("MYSQL_USER", "root")
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        db = os.getenv("MYSQL_DB", "dhan_trading")
        return create_engine(f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}")
    
    def get_stocks_to_download(self) -> pd.DataFrame:
        """Get list of stocks that need historical data download."""
        query = """
            SELECT s.symbol, s.security_id
            FROM dhan_stocks s
            LEFT JOIN (
                SELECT symbol, MAX(trade_date) as last_date
                FROM dhan_daily_ohlcv
                GROUP BY symbol
            ) d ON s.symbol = d.symbol
            WHERE s.security_id IS NOT NULL
            ORDER BY s.symbol
        """
        return pd.read_sql(query, self.engine)
    
    def get_missing_security_ids(self) -> List[str]:
        """Get symbols missing security_id."""
        query = """
            SELECT symbol FROM dhan_stocks WHERE security_id IS NULL
        """
        df = pd.read_sql(query, self.engine)
        return df['symbol'].tolist()
    
    def update_security_id(self, symbol: str, security_id: int, exchange_segment: str = 'NSE_EQ', instrument: str = 'EQUITY'):
        """Update security ID for a symbol."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                UPDATE dhan_stocks 
                SET security_id = :security_id
                WHERE symbol = :symbol
            """), {
                'symbol': symbol,
                'security_id': security_id
            })
    
    def lookup_security_ids_from_instruments(self):
        """Look up security IDs from dhan_instruments table or download fresh CSV."""
        logger.info("Looking up security IDs from instruments table...")
        
        # Get symbols without security_id
        missing = self.get_missing_security_ids()
        if not missing:
            logger.info("All symbols have security IDs")
            return 0
        
        logger.info(f"Found {len(missing)} symbols without security ID")
        
        # Try downloading the compact CSV which has trading symbols
        try:
            import requests
            url = "https://images.dhan.co/api-data/api-scrip-master.csv"
            logger.info(f"Downloading instrument master from {url}...")
            
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            
            from io import StringIO
            instruments_df = pd.read_csv(StringIO(response.text), low_memory=False)
            
            # Get trading symbols for NSE equity
            nse_eq = instruments_df[
                (instruments_df['SEM_EXM_EXCH_ID'] == 'NSE') & 
                (instruments_df['SEM_SEGMENT'] == 'E') &
                (instruments_df['SEM_INSTRUMENT_NAME'] == 'EQUITY')
            ].copy()
            
            logger.info(f"Found {len(nse_eq)} NSE equity instruments")
            
            # Create mapping from trading symbol to security_id
            # SEM_TRADING_SYMBOL is the NSE trading symbol (like RELIANCE-EQ)
            # SM_SYMBOL_NAME is the full name
            nse_eq['trading_symbol'] = nse_eq['SEM_TRADING_SYMBOL'].str.replace('-EQ', '', regex=False)
            
            # Also try custom symbol
            if 'SEM_CUSTOM_SYMBOL' in nse_eq.columns:
                nse_eq['custom_symbol'] = nse_eq['SEM_CUSTOM_SYMBOL'].str.upper()
            
            updated = 0
            for symbol in missing:
                # Try exact match on trading symbol
                match = nse_eq[nse_eq['trading_symbol'] == symbol]
                
                if match.empty and 'custom_symbol' in nse_eq.columns:
                    # Try custom symbol
                    match = nse_eq[nse_eq['custom_symbol'] == symbol]
                
                if not match.empty:
                    row = match.iloc[0]
                    self.update_security_id(
                        symbol,
                        int(row['SEM_SMST_SECURITY_ID']),
                        'NSE_EQ',
                        'EQUITY'
                    )
                    updated += 1
            
            logger.info(f"Updated {updated} security IDs from CSV")
            return updated
            
        except Exception as e:
            logger.error(f"Error downloading instruments: {e}")
            return 0
    
    def download_daily_data(
        self,
        symbol: str,
        security_id: int,
        exchange_segment: str = 'NSE_EQ',
        instrument: str = 'EQUITY',
        years: int = 20,
        log_cb=None
    ) -> int:
        """
        Download daily OHLCV data for a symbol.
        
        Args:
            symbol: Stock symbol
            security_id: Dhan security ID
            exchange_segment: NSE_EQ, BSE_EQ, etc.
            instrument: EQUITY, INDEX, etc.
            years: Number of years of data to download
            log_cb: Logging callback
        
        Returns:
            Number of records saved
        """
        if log_cb is None:
            log_cb = logger.info
        
        end_date = date.today()
        start_date = end_date - timedelta(days=years * 365)
        
        # Get existing data range
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT MIN(trade_date) as min_date, MAX(trade_date) as max_date
                FROM dhan_daily_ohlcv WHERE symbol = :symbol
            """), {'symbol': symbol})
            row = result.fetchone()
            existing_min = row[0] if row else None
            existing_max = row[1] if row else None
        
        total_saved = 0
        
        # Download in chunks (2000 days max per request)
        chunk_days = 1800  # ~5 years per chunk
        current_start = start_date
        
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=chunk_days), end_date)
            
            # Skip if we already have this data
            if existing_min and existing_max:
                if current_start >= existing_min and current_end <= existing_max:
                    current_start = current_end + timedelta(days=1)
                    continue
            
            from_str = current_start.strftime('%Y-%m-%d')
            to_str = current_end.strftime('%Y-%m-%d')
            
            df = self.api.get_historical_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
                instrument=instrument,
                from_date=from_str,
                to_date=to_str,
                interval="day"
            )
            
            if df is not None and not df.empty:
                # Add symbol column
                df['symbol'] = symbol
                df['trade_date'] = df['timestamp'].dt.date
                
                # Prepare for insert
                df_insert = df[['symbol', 'trade_date', 'open', 'high', 'low', 'close', 'volume']].copy()
                df_insert.columns = ['symbol', 'trade_date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
                
                # Insert with upsert
                self._upsert_daily_data(df_insert)
                total_saved += len(df_insert)
            
            current_start = current_end + timedelta(days=1)
            time.sleep(0.1)  # Small delay between chunks
        
        return total_saved
    
    def _upsert_daily_data(self, df: pd.DataFrame):
        """Insert or update daily OHLCV data."""
        with self.engine.begin() as conn:
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO dhan_daily_ohlcv (symbol, trade_date, open_price, high_price, low_price, close_price, volume)
                    VALUES (:symbol, :trade_date, :open_price, :high_price, :low_price, :close_price, :volume)
                    ON DUPLICATE KEY UPDATE
                        open_price = VALUES(open_price),
                        high_price = VALUES(high_price),
                        low_price = VALUES(low_price),
                        close_price = VALUES(close_price),
                        volume = VALUES(volume)
                """), {
                    'symbol': row['symbol'],
                    'trade_date': row['trade_date'],
                    'open_price': float(row['open_price']) if pd.notna(row['open_price']) else None,
                    'high_price': float(row['high_price']) if pd.notna(row['high_price']) else None,
                    'low_price': float(row['low_price']) if pd.notna(row['low_price']) else None,
                    'close_price': float(row['close_price']) if pd.notna(row['close_price']) else None,
                    'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                })
    
    def download_all_daily(self, years: int = 20, max_workers: int = 3, log_cb=None):
        """
        Download daily data for all stocks.
        
        Args:
            years: Number of years of data
            max_workers: Number of parallel workers
            log_cb: Logging callback
        """
        if log_cb is None:
            log_cb = logger.info
        
        # First, look up missing security IDs
        self.lookup_security_ids_from_instruments()
        
        # Get stocks to download
        stocks = self.get_stocks_to_download()
        stocks = stocks[stocks['security_id'].notna()]
        
        log_cb(f"📊 Starting daily download for {len(stocks)} stocks ({years} years)")
        
        self.progress.total_stocks = len(stocks)
        self.progress.completed_stocks = 0
        self.progress.failed_stocks = 0
        self.progress.status = "running"
        
        for idx, row in stocks.iterrows():
            symbol = row['symbol']
            security_id = int(row['security_id'])
            # Use default NSE_EQ and EQUITY for all stocks
            exchange_segment = 'NSE_EQ'
            instrument = 'EQUITY'
            
            self.progress.current_symbol = symbol
            
            try:
                saved = self.download_daily_data(
                    symbol=symbol,
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    instrument=instrument,
                    years=years,
                    log_cb=log_cb
                )
                
                self.progress.total_candles += saved
                self.progress.completed_stocks += 1
                
                if saved > 0:
                    log_cb(f"✓ {symbol}: {saved} daily records")
                else:
                    log_cb(f"○ {symbol}: no new data")
                
            except Exception as e:
                self.progress.failed_stocks += 1
                log_cb(f"✗ {symbol}: {e}")
            
            # Progress update
            if self.progress.completed_stocks % 10 == 0:
                pct = self.progress.completed_stocks / self.progress.total_stocks * 100
                log_cb(f"Progress: {self.progress.completed_stocks}/{self.progress.total_stocks} ({pct:.1f}%)")
        
        self.progress.status = "completed"
        log_cb(f"\n✅ Daily download complete!")
        log_cb(f"   Stocks: {self.progress.completed_stocks} completed, {self.progress.failed_stocks} failed")
        log_cb(f"   Records: {self.progress.total_candles:,}")

    # ==================== INTRADAY (1-MIN) DATA ====================
    
    def download_intraday_data(
        self,
        symbol: str,
        security_id: int,
        exchange_segment: str = 'NSE_EQ',
        instrument: str = 'EQUITY',
        years: int = 5,  # Dhan API supports up to 5 years of intraday data
        chunk_days: int = 90,  # API allows max 90 days per request
        log_cb=None
    ) -> int:
        """
        Download 1-minute intraday data for a single stock.
        
        Dhan API allows up to 5 years of intraday data, but max 90 days per request.
        This method fetches data in 90-day chunks going backwards.
        
        Args:
            symbol: Stock symbol
            security_id: Dhan security ID
            exchange_segment: Exchange segment
            instrument: Instrument type
            years: Number of years of data to download (max 5)
            chunk_days: Days per API request (max 90)
            log_cb: Logging callback
            
        Returns:
            Number of records saved
        """
        if log_cb is None:
            log_cb = logger.info
        
        total_saved = 0
        
        # Get the last intraday date we have for this symbol
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT MAX(trade_datetime) as last_dt 
                FROM dhan_minute_ohlcv 
                WHERE symbol = :symbol
            """), {'symbol': symbol})
            row = result.fetchone()
            last_date = row[0] if row and row[0] else None
        
        # Also get the earliest date we have
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT MIN(trade_datetime) as first_dt 
                FROM dhan_minute_ohlcv 
                WHERE symbol = :symbol
            """), {'symbol': symbol})
            row = result.fetchone()
            first_date = row[0] if row and row[0] else None
        
        # Determine date range - we'll download both:
        # 1. New data from last_date to now
        # 2. Historical data going back 'years' years
        end_date = datetime.now()
        earliest_date = end_date - timedelta(days=years * 365)
        
        # Part 1: Download new data (from last_date to now) if we have existing data
        if last_date and last_date.date() < end_date.date():
            new_start = last_date + timedelta(days=1)
            
            # Fetch in chunks if needed
            current_start = new_start
            while current_start.date() < end_date.date():
                current_end = min(current_start + timedelta(days=chunk_days - 1), end_date)
                
                df = self.api.get_intraday_data(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    instrument=instrument,
                    from_date=current_start.strftime('%Y-%m-%d'),
                    to_date=current_end.strftime('%Y-%m-%d'),
                    interval="1"
                )
                
                if df is not None and not df.empty:
                    df['symbol'] = symbol
                    df['security_id'] = security_id
                    df.rename(columns={
                        'timestamp': 'trade_datetime',
                        'open': 'open_price',
                        'high': 'high_price',
                        'low': 'low_price',
                        'close': 'close_price'
                    }, inplace=True)
                    
                    self._upsert_intraday_data(df)
                    total_saved += len(df)
                
                current_start = current_end + timedelta(days=1)
                time.sleep(0.1)  # Small delay between chunks
        
        # Part 2: Download historical data (going back from first_date or from now if no data)
        if first_date:
            # We already have some data, go backwards from our earliest point
            historical_end = first_date - timedelta(days=1)
        else:
            # No data yet, start from today and go back
            historical_end = end_date
        
        # Download backwards in chunks until we reach earliest_date
        current_end = historical_end
        while current_end.date() > earliest_date.date():
            current_start = max(current_end - timedelta(days=chunk_days - 1), earliest_date)
            
            df = self.api.get_intraday_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
                instrument=instrument,
                from_date=current_start.strftime('%Y-%m-%d'),
                to_date=current_end.strftime('%Y-%m-%d'),
                interval="1"
            )
            
            if df is not None and not df.empty:
                df['symbol'] = symbol
                df['security_id'] = security_id
                df.rename(columns={
                    'timestamp': 'trade_datetime',
                    'open': 'open_price',
                    'high': 'high_price',
                    'low': 'low_price',
                    'close': 'close_price'
                }, inplace=True)
                
                self._upsert_intraday_data(df)
                total_saved += len(df)
            else:
                # No more historical data available, stop going back
                break
            
            current_end = current_start - timedelta(days=1)
            time.sleep(0.1)  # Small delay between chunks
        
        return total_saved
    
    def _upsert_intraday_data(self, df: pd.DataFrame):
        """Upsert intraday data to database."""
        if df.empty:
            return
        
        with self.engine.begin() as conn:
            # Create temp table
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_intraday"))
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_intraday (
                    symbol VARCHAR(50),
                    security_id BIGINT,
                    trade_datetime DATETIME,
                    open_price DECIMAL(15,4),
                    high_price DECIMAL(15,4),
                    low_price DECIMAL(15,4),
                    close_price DECIMAL(15,4),
                    volume BIGINT
                )
            """))
            
            # Bulk insert to temp table
            df_insert = df[['symbol', 'security_id', 'trade_datetime', 
                           'open_price', 'high_price', 'low_price', 'close_price', 'volume']].copy()
            df_insert.to_sql('tmp_intraday', conn, if_exists='append', index=False, method='multi', chunksize=5000)
            
            # Upsert to main table
            conn.execute(text("""
                INSERT INTO dhan_minute_ohlcv (symbol, security_id, trade_datetime, 
                    open_price, high_price, low_price, close_price, volume)
                SELECT symbol, security_id, trade_datetime,
                    open_price, high_price, low_price, close_price, volume
                FROM tmp_intraday
                ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume)
            """))
    
    def download_all_intraday(self, days: int = 90, max_workers: int = 4, log_cb=None):
        """
        Download 1-minute intraday data for all stocks using parallel threads.
        
        This is the FAST version - downloads only recent data (default 90 days).
        Skips stocks that already have recent data.
        
        Args:
            days: Number of days to download (default 90 = 3 months, max per API call)
            max_workers: Number of parallel download threads (default 4)
            log_cb: Logging callback
        """
        if log_cb is None:
            log_cb = logger.info
        
        # Get stocks to download
        stocks = self.get_stocks_to_download()
        stocks = stocks[stocks['security_id'].notna()]
        
        log_cb(f"[INFO] Starting PARALLEL intraday download for {len(stocks)} stocks")
        log_cb(f"   Config: {days} days, {max_workers} workers")
        
        self.progress = DownloadProgress()
        self.progress.total_stocks = len(stocks)
        self.progress.status = "running"
        
        # Convert to list of tuples for processing
        stock_list = [(row['symbol'], int(row['security_id'])) for _, row in stocks.iterrows()]
        
        def download_stock(args):
            """Worker function to download a single stock."""
            symbol, security_id = args
            try:
                saved = self.download_intraday_fast(
                    symbol=symbol,
                    security_id=security_id,
                    days=days,
                    log_cb=None  # Suppress per-stock logging in parallel mode
                )
                return (symbol, saved, None)
            except Exception as e:
                return (symbol, 0, str(e))
        
        # Process stocks in parallel
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(download_stock, stock): stock for stock in stock_list}
            
            for future in as_completed(futures):
                symbol, saved, error = future.result()
                completed += 1
                
                if error:
                    self.progress.increment_failed()
                    log_cb(f"[FAIL] {symbol}: {error}")
                else:
                    self.progress.increment_completed(saved)
                    if saved > 0:
                        log_cb(f"[OK] {symbol}: {saved:,} 1-min records")
                    else:
                        log_cb(f"[SKIP] {symbol}: no new data")
                
                # Progress update every 10 stocks
                if completed % 10 == 0:
                    pct = completed / self.progress.total_stocks * 100
                    log_cb(f"Progress: {completed}/{self.progress.total_stocks} ({pct:.1f}%) - {self.progress.total_candles:,} total records")
        
        self.progress.status = "completed"
        log_cb(f"\n[DONE] Intraday download complete!")
        log_cb(f"   Stocks: {self.progress.completed_stocks} completed, {self.progress.failed_stocks} failed")
        log_cb(f"   Records: {self.progress.total_candles:,}")
    
    def download_intraday_fast(
        self,
        symbol: str,
        security_id: int,
        days: int = 90,
        exchange_segment: str = 'NSE_EQ',
        instrument: str = 'EQUITY',
        log_cb=None
    ) -> int:
        """
        FAST intraday download - single API call for up to 90 days.
        
        Checks existing data and only downloads what's missing.
        Uses ON DUPLICATE KEY UPDATE to avoid duplicates.
        
        Args:
            symbol: Stock symbol
            security_id: Dhan security ID
            days: Days to download (max 90)
            exchange_segment: Exchange segment
            instrument: Instrument type
            log_cb: Logging callback
            
        Returns:
            Number of new records saved
        """
        if log_cb is None:
            log_cb = logger.info
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Check what data we already have in this range
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT MAX(trade_datetime) as last_dt 
                FROM dhan_minute_ohlcv 
                WHERE symbol = :symbol 
                  AND trade_datetime >= :start_date
            """), {'symbol': symbol, 'start_date': start_date})
            row = result.fetchone()
            last_date = row[0] if row and row[0] else None
        
        # If we have recent data (within last 2 days), skip
        if last_date:
            days_old = (end_date - last_date).days
            if days_old <= 1:
                return 0  # Already up to date
            # Otherwise, fetch from last_date onwards
            start_date = last_date + timedelta(minutes=1)
        
        # Single API call (max 90 days)
        df = self.api.get_intraday_data(
            security_id=security_id,
            exchange_segment=exchange_segment,
            instrument=instrument,
            from_date=start_date.strftime('%Y-%m-%d'),
            to_date=end_date.strftime('%Y-%m-%d'),
            interval="1"
        )
        
        if df is None or df.empty:
            return 0
        
        # Prepare data
        df['symbol'] = symbol
        df['security_id'] = security_id
        df.rename(columns={
            'timestamp': 'trade_datetime',
            'open': 'open_price',
            'high': 'high_price',
            'low': 'low_price',
            'close': 'close_price'
        }, inplace=True)
        
        # Upsert to database (handles duplicates)
        self._upsert_intraday_data(df)
        return len(df)
    
    def download_all_intraday_full(self, years: int = 5, chunk_days: int = 90, max_workers: int = 4, log_cb=None):
        """
        Download 1-minute intraday data for all stocks using parallel threads.
        
        Dhan API supports up to 5 years of intraday data, fetched in 90-day chunks.
        Uses multi-threading to download multiple stocks in parallel.
        
        Args:
            years: Number of years of data (max 5 per Dhan API)
            chunk_days: Days per API request (max 90 per Dhan API)
            max_workers: Number of parallel download threads (default 4)
            log_cb: Logging callback
        """
        if log_cb is None:
            log_cb = logger.info
        
        # Get stocks to download
        stocks = self.get_stocks_to_download()
        stocks = stocks[stocks['security_id'].notna()]
        
        log_cb(f"[INFO] Starting PARALLEL intraday download for {len(stocks)} stocks")
        log_cb(f"   Config: {years} years, {chunk_days}-day chunks, {max_workers} workers")
        
        self.progress = DownloadProgress()
        self.progress.total_stocks = len(stocks)
        self.progress.status = "running"
        
        # Convert to list of tuples for processing
        stock_list = [(row['symbol'], int(row['security_id'])) for _, row in stocks.iterrows()]
        
        def download_stock(args):
            """Worker function to download a single stock."""
            symbol, security_id = args
            try:
                saved = self.download_intraday_data(
                    symbol=symbol,
                    security_id=security_id,
                    years=years,
                    chunk_days=chunk_days,
                    log_cb=None  # Suppress per-stock logging in parallel mode
                )
                return (symbol, saved, None)
            except Exception as e:
                return (symbol, 0, str(e))
        
        # Process stocks in parallel
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(download_stock, stock): stock for stock in stock_list}
            
            for future in as_completed(futures):
                symbol, saved, error = future.result()
                completed += 1
                
                if error:
                    self.progress.increment_failed()
                    log_cb(f"[FAIL] {symbol}: {error}")
                else:
                    self.progress.increment_completed(saved)
                    if saved > 0:
                        log_cb(f"[OK] {symbol}: {saved:,} 1-min records")
                    else:
                        log_cb(f"[SKIP] {symbol}: no new data")
                
                # Progress update every 10 stocks
                if completed % 10 == 0:
                    pct = completed / self.progress.total_stocks * 100
                    log_cb(f"Progress: {completed}/{self.progress.total_stocks} ({pct:.1f}%) - {self.progress.total_candles:,} total records")
        
        self.progress.status = "completed"
        log_cb(f"\n[DONE] Intraday download complete!")
        log_cb(f"   Stocks: {self.progress.completed_stocks} completed, {self.progress.failed_stocks} failed")
        log_cb(f"   Records: {self.progress.total_candles:,}")
    
    def download_all_intraday_sequential(self, years: int = 5, chunk_days: int = 90, log_cb=None):
        """
        Download 1-minute intraday data sequentially (non-parallel version).
        Use this if you encounter rate limiting issues with parallel download.
        """
        if log_cb is None:
            log_cb = logger.info
        
        stocks = self.get_stocks_to_download()
        stocks = stocks[stocks['security_id'].notna()]
        
        log_cb(f"[INFO] Starting sequential intraday download for {len(stocks)} stocks ({years} years)")
        
        self.progress = DownloadProgress()
        self.progress.total_stocks = len(stocks)
        
        for idx, row in stocks.iterrows():
            symbol = row['symbol']
            security_id = int(row['security_id'])
            
            self.progress.current_symbol = symbol
            
            try:
                saved = self.download_intraday_data(
                    symbol=symbol,
                    security_id=security_id,
                    years=years,
                    chunk_days=chunk_days,
                    log_cb=log_cb
                )
                
                self.progress.total_candles += saved
                self.progress.completed_stocks += 1
                
                if saved > 0:
                    log_cb(f"[OK] {symbol}: {saved} 1-min records")
                else:
                    log_cb(f"[SKIP] {symbol}: no new data")
                
            except Exception as e:
                self.progress.failed_stocks += 1
                log_cb(f"[FAIL] {symbol}: {e}")
            
            # Progress update
            if self.progress.completed_stocks % 10 == 0:
                pct = self.progress.completed_stocks / self.progress.total_stocks * 100
                log_cb(f"Progress: {self.progress.completed_stocks}/{self.progress.total_stocks} ({pct:.1f}%)")
        
        self.progress.status = "completed"
        log_cb(f"\n[DONE] Intraday download complete!")
        log_cb(f"   Stocks: {self.progress.completed_stocks} completed, {self.progress.failed_stocks} failed")
        log_cb(f"   Records: {self.progress.total_candles:,}")


def main():
    """Test the downloader."""
    print("=" * 60)
    print("Dhan Historical Data Downloader")
    print("=" * 60)
    
    downloader = HistoricalDownloader()
    
    # Look up security IDs first
    updated = downloader.lookup_security_ids_from_instruments()
    print(f"Updated {updated} security IDs")
    
    # Get stocks
    stocks = downloader.get_stocks_to_download()
    print(f"\nStocks ready for download: {len(stocks)}")
    
    missing = downloader.get_missing_security_ids()
    print(f"Stocks missing security ID: {len(missing)}")
    
    if len(stocks) > 0:
        # Download daily data for first 5 stocks as test
        print("\n--- Test: Downloading first 5 stocks ---")
        for idx, row in stocks.head(5).iterrows():
            if pd.notna(row['security_id']):
                symbol = row['symbol']
                security_id = int(row['security_id'])
                print(f"\nDownloading {symbol} (ID: {security_id})...")
                
                saved = downloader.download_daily_data(
                    symbol=symbol,
                    security_id=security_id,
                    exchange_segment=row['exchange_segment'] or 'NSE_EQ',
                    instrument=row['instrument'] or 'EQUITY',
                    years=5  # Test with 5 years
                )
                print(f"  Saved {saved} records")


if __name__ == "__main__":
    main()
