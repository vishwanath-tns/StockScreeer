"""
Golden Cross / Death Cross Detector
====================================
Core detection logic for moving average crossover signals.

Golden Cross: Short-term MA (50) crosses ABOVE long-term MA (200)
Death Cross: Short-term MA (50) crosses BELOW long-term MA (200)

These are widely followed signals:
- Golden Cross is considered BULLISH (start of uptrend)
- Death Cross is considered BEARISH (start of downtrend)
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
from urllib.parse import quote_plus
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class CrossoverType(Enum):
    """Type of crossover signal."""
    GOLDEN_CROSS = "GOLDEN_CROSS"  # Bullish: 50 SMA crosses above 200 SMA
    DEATH_CROSS = "DEATH_CROSS"    # Bearish: 50 SMA crosses below 200 SMA


@dataclass
class CrossoverSignal:
    """Represents a single crossover signal."""
    symbol: str
    signal_date: date
    signal_type: CrossoverType
    
    # Prices at crossover
    close_price: float
    sma_50: float
    sma_200: float
    
    # Additional context
    previous_signal_type: Optional[CrossoverType] = None
    previous_signal_date: Optional[date] = None
    days_since_previous: Optional[int] = None
    
    # Performance tracking (filled in later)
    price_1d_later: Optional[float] = None
    price_5d_later: Optional[float] = None
    price_20d_later: Optional[float] = None
    pct_change_1d: Optional[float] = None
    pct_change_5d: Optional[float] = None
    pct_change_20d: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'symbol': self.symbol,
            'signal_date': self.signal_date,
            'signal_type': self.signal_type.value,
            'close_price': self.close_price,
            'sma_50': self.sma_50,
            'sma_200': self.sma_200,
            'previous_signal_type': self.previous_signal_type.value if self.previous_signal_type else None,
            'previous_signal_date': self.previous_signal_date,
            'days_since_previous': self.days_since_previous,
            'price_1d_later': self.price_1d_later,
            'price_5d_later': self.price_5d_later,
            'price_20d_later': self.price_20d_later,
            'pct_change_1d': self.pct_change_1d,
            'pct_change_5d': self.pct_change_5d,
            'pct_change_20d': self.pct_change_20d,
        }


class CrossoverDetector:
    """
    Detects Golden Cross and Death Cross signals from stock data.
    
    Features:
    - Configurable SMA periods (default: 50/200)
    - Historical signal tracking
    - Parallel processing for multiple stocks
    - Database storage of signals
    - Incremental daily scanning
    """
    
    # Default SMA periods for crossover detection
    DEFAULT_SHORT_SMA = 50
    DEFAULT_LONG_SMA = 200
    
    def __init__(self, 
                 short_sma: int = DEFAULT_SHORT_SMA,
                 long_sma: int = DEFAULT_LONG_SMA,
                 max_workers: int = 10):
        """
        Initialize the detector.
        
        Args:
            short_sma: Short-term SMA period (default: 50)
            long_sma: Long-term SMA period (default: 200)
            max_workers: Number of parallel workers for scanning
        """
        self.short_sma = short_sma
        self.long_sma = long_sma
        self.max_workers = max_workers
        self.engine = self._create_engine()
        
        # Ensure table exists
        self._ensure_table()
    
    def _create_engine(self):
        """Create SQLAlchemy engine."""
        try:
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
            raise
    
    def _ensure_table(self):
        """Ensure the crossover signals table exists."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ma_crossover_signals (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(50) NOT NULL,
                    signal_date DATE NOT NULL,
                    signal_type VARCHAR(20) NOT NULL,
                    close_price DECIMAL(15, 4),
                    sma_short DECIMAL(15, 4),
                    sma_long DECIMAL(15, 4),
                    short_period INT DEFAULT 50,
                    long_period INT DEFAULT 200,
                    previous_signal_type VARCHAR(20),
                    previous_signal_date DATE,
                    days_since_previous INT,
                    price_1d_later DECIMAL(15, 4),
                    price_5d_later DECIMAL(15, 4),
                    price_20d_later DECIMAL(15, 4),
                    pct_change_1d DECIMAL(10, 4),
                    pct_change_5d DECIMAL(10, 4),
                    pct_change_20d DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY idx_symbol_date_type (symbol, signal_date, signal_type),
                    INDEX idx_signal_date (signal_date),
                    INDEX idx_signal_type (signal_type),
                    INDEX idx_symbol (symbol)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            logger.info("Crossover signals table ready")
    
    def get_nifty500_symbols(self) -> List[str]:
        """Get list of Nifty 500 symbols from database."""
        try:
            from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
            return [f"{s}.NS" for s in NIFTY_500_STOCKS]
        except ImportError:
            # Fallback: get from database
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT symbol FROM yfinance_daily_ma
                    WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                """))
                return [row[0] for row in result]
    
    def detect_crossover(self, df: pd.DataFrame, symbol: str) -> List[CrossoverSignal]:
        """
        Detect crossover signals in a stock's data.
        
        Args:
            df: DataFrame with columns: date, close, sma_50, sma_200
            symbol: Stock symbol
            
        Returns:
            List of CrossoverSignal objects
        """
        if df.empty or len(df) < 2:
            return []
        
        # Ensure sorted by date
        df = df.sort_values('date').copy()
        
        # Column names based on configured periods
        sma_short_col = f'sma_{self.short_sma}'
        sma_long_col = f'sma_{self.long_sma}'
        
        # Check if required columns exist
        required_cols = ['date', 'close', sma_short_col, sma_long_col]
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"Missing column {col} for {symbol}")
                return []
        
        signals = []
        previous_signal: Optional[CrossoverSignal] = None
        
        for i in range(1, len(df)):
            prev_row = df.iloc[i - 1]
            curr_row = df.iloc[i]
            
            # Skip if SMAs are null
            if (pd.isna(prev_row[sma_short_col]) or pd.isna(prev_row[sma_long_col]) or
                pd.isna(curr_row[sma_short_col]) or pd.isna(curr_row[sma_long_col])):
                continue
            
            prev_short = prev_row[sma_short_col]
            prev_long = prev_row[sma_long_col]
            curr_short = curr_row[sma_short_col]
            curr_long = curr_row[sma_long_col]
            
            signal_type = None
            
            # Golden Cross: short was below or equal to long, now above
            if prev_short <= prev_long and curr_short > curr_long:
                signal_type = CrossoverType.GOLDEN_CROSS
            
            # Death Cross: short was above or equal to long, now below
            elif prev_short >= prev_long and curr_short < curr_long:
                signal_type = CrossoverType.DEATH_CROSS
            
            if signal_type:
                signal_date = curr_row['date'].date() if hasattr(curr_row['date'], 'date') else curr_row['date']
                
                signal = CrossoverSignal(
                    symbol=symbol,
                    signal_date=signal_date,
                    signal_type=signal_type,
                    close_price=float(curr_row['close']),
                    sma_50=float(curr_short),
                    sma_200=float(curr_long),
                    previous_signal_type=previous_signal.signal_type if previous_signal else None,
                    previous_signal_date=previous_signal.signal_date if previous_signal else None,
                    days_since_previous=(signal_date - previous_signal.signal_date).days if previous_signal else None
                )
                
                signals.append(signal)
                previous_signal = signal
        
        return signals
    
    def scan_symbol_yahoo(self, symbol: str,
                          start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> List[CrossoverSignal]:
        """
        Scan a single symbol using FRESH Yahoo Finance data with UNADJUSTED prices.
        This ensures crossovers match what traders see on TradingView.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            start_date: Start date for scanning (default: 2 years ago)
            end_date: End date for scanning (default: today)
            
        Returns:
            List of CrossoverSignal objects
        """
        import yfinance as yf
        
        if start_date is None:
            start_date = date.today() - timedelta(days=730)  # 2 years for proper 200 SMA
        if end_date is None:
            end_date = date.today()
        
        try:
            ticker = yf.Ticker(symbol)
            # Use auto_adjust=False for UNADJUSTED prices (matches TradingView)
            df = ticker.history(
                start=start_date - timedelta(days=250),  # Extra buffer for SMA calculation
                end=end_date + timedelta(days=1),
                auto_adjust=False
            )
            
            if df.empty or len(df) < self.long_sma + 1:
                return []
            
            df = df.reset_index()
            df = df.rename(columns={'Date': 'date', 'Close': 'close'})
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # Calculate SMAs from unadjusted close
            sma_short_col = f'sma_{self.short_sma}'
            sma_long_col = f'sma_{self.long_sma}'
            df[sma_short_col] = df['close'].rolling(self.short_sma).mean()
            df[sma_long_col] = df['close'].rolling(self.long_sma).mean()
            
            # Filter to requested date range (after SMA calculation)
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if df.empty:
                return []
            
            return self.detect_crossover(df, symbol)
            
        except Exception as e:
            logger.error(f"Error scanning {symbol} from Yahoo: {e}")
            return []
    
    def scan_symbol(self, symbol: str, 
                    start_date: Optional[date] = None,
                    end_date: Optional[date] = None,
                    use_yahoo: bool = True) -> List[CrossoverSignal]:
        """
        Scan a single symbol for crossover signals.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            start_date: Start date for scanning (default: 1 year ago)
            end_date: End date for scanning (default: today)
            use_yahoo: If True, fetch fresh data from Yahoo (recommended for accuracy)
            
        Returns:
            List of CrossoverSignal objects
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=365)
        if end_date is None:
            end_date = date.today()
        
        # Use Yahoo Finance for accurate unadjusted prices (matches TradingView)
        if use_yahoo:
            return self.scan_symbol_yahoo(symbol, start_date, end_date)
        
        # Fallback to database (uses adjusted prices - may not match TradingView)
        sma_short_col = f'sma_{self.short_sma}'
        sma_long_col = f'sma_{self.long_sma}'
        
        query = text(f"""
            SELECT date, close, {sma_short_col}, {sma_long_col}
            FROM yfinance_daily_ma
            WHERE symbol = :symbol
              AND date BETWEEN :start_date AND :end_date
              AND {sma_short_col} IS NOT NULL
              AND {sma_long_col} IS NOT NULL
            ORDER BY date
        """)
        
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'symbol': symbol,
                    'start_date': start_date,
                    'end_date': end_date
                })
            
            if df.empty:
                return []
            
            return self.detect_crossover(df, symbol)
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return []
    
    def scan_all_stocks(self,
                        symbols: Optional[List[str]] = None,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None,
                        progress_callback=None,
                        use_yahoo: bool = True) -> List[CrossoverSignal]:
        """
        Scan all stocks for crossover signals using parallel processing.
        
        Args:
            symbols: List of symbols (default: Nifty 500)
            start_date: Start date for scanning
            end_date: End date for scanning
            progress_callback: Optional callback(current, total, symbol)
            
        Returns:
            List of all CrossoverSignal objects found
        """
        if symbols is None:
            symbols = self.get_nifty500_symbols()
        
        all_signals = []
        total = len(symbols)
        
        logger.info(f"Scanning {total} symbols for crossovers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.scan_symbol, symbol, start_date, end_date): symbol
                for symbol in symbols
            }
            
            completed = 0
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    signals = future.result()
                    all_signals.extend(signals)
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total, symbol)
        
        logger.info(f"Found {len(all_signals)} crossover signals")
        return all_signals
    
    def scan_for_date(self, target_date: date,
                      symbols: Optional[List[str]] = None,
                      use_yahoo: bool = True) -> List[CrossoverSignal]:
        """
        Scan for crossover signals on a specific date only.
        Uses Yahoo Finance with unadjusted prices for accuracy.
        
        Args:
            target_date: The date to scan
            symbols: Optional list of symbols (default: Nifty 500)
            use_yahoo: If True, use Yahoo Finance (accurate), else use database
            
        Returns:
            List of signals that occurred on target_date
        """
        if symbols is None:
            symbols = self.get_nifty500_symbols()
        
        all_signals = []
        
        if use_yahoo:
            # Use Yahoo Finance with unadjusted prices for each symbol
            # We only need to check if crossover happened on target_date
            start_date = target_date - timedelta(days=10)  # Buffer for crossover detection
            
            logger.info(f"Scanning {len(symbols)} symbols for crossovers on {target_date}...")
            
            def scan_one(symbol):
                try:
                    signals = self.scan_symbol_yahoo(symbol, start_date, target_date)
                    # Filter to only signals on target_date
                    return [s for s in signals if s.signal_date == target_date]
                except Exception as e:
                    logger.debug(f"Error scanning {symbol}: {e}")
                    return []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(scan_one, sym) for sym in symbols]
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        all_signals.extend(result)
                    except Exception as e:
                        pass
            
            return all_signals
        
        # Fallback to database (uses adjusted prices - may not match TradingView)
        start_date = target_date - timedelta(days=5)  # Buffer for weekends
        
        sma_short_col = f'sma_{self.short_sma}'
        sma_long_col = f'sma_{self.long_sma}'
        
        # Batch query all symbols
        query = text(f"""
            SELECT symbol, date, close, {sma_short_col}, {sma_long_col}
            FROM yfinance_daily_ma
            WHERE date BETWEEN :start_date AND :target_date
              AND {sma_short_col} IS NOT NULL
              AND {sma_long_col} IS NOT NULL
            ORDER BY symbol, date
        """)
        
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'start_date': start_date,
                    'target_date': target_date
                })
            
            if df.empty:
                return []
            
            for symbol, group in df.groupby('symbol'):
                signals = self.detect_crossover(group, symbol)
                # Filter to only signals on target_date
                for signal in signals:
                    if signal.signal_date == target_date:
                        all_signals.append(signal)
            
            return all_signals
            
        except Exception as e:
            logger.error(f"Error scanning for date {target_date}: {e}")
            return []
    
    def _enrich_with_previous_signal(self, signal: CrossoverSignal) -> CrossoverSignal:
        """
        Enrich a signal with previous signal info from the database.
        This is used when the signal doesn't have previous signal info
        (e.g., when scanning a single date).
        
        Args:
            signal: The signal to enrich
            
        Returns:
            The enriched signal (modified in place)
        """
        if signal.previous_signal_type is not None:
            # Already has previous signal info
            return signal
        
        # Look up the last signal for this symbol before this date
        query = text("""
            SELECT signal_type, signal_date 
            FROM ma_crossover_signals
            WHERE symbol = :symbol 
              AND signal_date < :signal_date
            ORDER BY signal_date DESC
            LIMIT 1
        """)
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {
                    'symbol': signal.symbol,
                    'signal_date': signal.signal_date
                }).fetchone()
                
                if result:
                    prev_type_str = result[0]
                    prev_date = result[1]
                    
                    signal.previous_signal_type = CrossoverType(prev_type_str)
                    signal.previous_signal_date = prev_date
                    signal.days_since_previous = (signal.signal_date - prev_date).days
        except Exception as e:
            logger.warning(f"Could not fetch previous signal for {signal.symbol}: {e}")
        
        return signal
    
    def save_signals(self, signals: List[CrossoverSignal], enrich_previous: bool = True) -> int:
        """
        Save signals to database.
        
        Args:
            signals: List of CrossoverSignal objects
            enrich_previous: If True, look up previous signal from DB if not set
            
        Returns:
            Number of signals saved
        """
        if not signals:
            return 0
        
        saved = 0
        
        with self.engine.begin() as conn:
            for signal in signals:
                try:
                    # Enrich with previous signal info if not set
                    if enrich_previous and signal.previous_signal_type is None:
                        self._enrich_with_previous_signal(signal)
                    
                    conn.execute(text("""
                        INSERT INTO ma_crossover_signals 
                        (symbol, signal_date, signal_type, close_price, sma_short, sma_long,
                         short_period, long_period, previous_signal_type, previous_signal_date,
                         days_since_previous, price_1d_later, price_5d_later, price_20d_later,
                         pct_change_1d, pct_change_5d, pct_change_20d)
                        VALUES (:symbol, :signal_date, :signal_type, :close_price, :sma_short, :sma_long,
                                :short_period, :long_period, :previous_signal_type, :previous_signal_date,
                                :days_since_previous, :price_1d_later, :price_5d_later, :price_20d_later,
                                :pct_change_1d, :pct_change_5d, :pct_change_20d)
                        ON DUPLICATE KEY UPDATE
                            close_price = VALUES(close_price),
                            sma_short = VALUES(sma_short),
                            sma_long = VALUES(sma_long),
                            previous_signal_type = VALUES(previous_signal_type),
                            previous_signal_date = VALUES(previous_signal_date),
                            days_since_previous = VALUES(days_since_previous),
                            updated_at = CURRENT_TIMESTAMP
                    """), {
                        'symbol': signal.symbol,
                        'signal_date': signal.signal_date,
                        'signal_type': signal.signal_type.value,
                        'close_price': signal.close_price,
                        'sma_short': signal.sma_50,
                        'sma_long': signal.sma_200,
                        'short_period': self.short_sma,
                        'long_period': self.long_sma,
                        'previous_signal_type': signal.previous_signal_type.value if signal.previous_signal_type else None,
                        'previous_signal_date': signal.previous_signal_date,
                        'days_since_previous': signal.days_since_previous,
                        'price_1d_later': signal.price_1d_later,
                        'price_5d_later': signal.price_5d_later,
                        'price_20d_later': signal.price_20d_later,
                        'pct_change_1d': signal.pct_change_1d,
                        'pct_change_5d': signal.pct_change_5d,
                        'pct_change_20d': signal.pct_change_20d,
                    })
                    saved += 1
                except Exception as e:
                    logger.error(f"Error saving signal for {signal.symbol}: {e}")
        
        logger.info(f"Saved {saved} signals to database")
        return saved
    
    def load_signals(self,
                     symbol: Optional[str] = None,
                     signal_type: Optional[CrossoverType] = None,
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None,
                     limit: int = 1000) -> pd.DataFrame:
        """
        Load signals from database with optional filters.
        
        Args:
            symbol: Filter by symbol
            signal_type: Filter by signal type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            
        Returns:
            DataFrame of signals
        """
        conditions = ["1=1"]
        params = {'limit': limit}
        
        if symbol:
            conditions.append("symbol = :symbol")
            params['symbol'] = symbol
        
        if signal_type:
            conditions.append("signal_type = :signal_type")
            params['signal_type'] = signal_type.value
        
        if start_date:
            conditions.append("signal_date >= :start_date")
            params['start_date'] = start_date
        
        if end_date:
            conditions.append("signal_date <= :end_date")
            params['end_date'] = end_date
        
        query = text(f"""
            SELECT * FROM ma_crossover_signals
            WHERE {' AND '.join(conditions)}
            ORDER BY signal_date DESC, symbol
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params=params)
        
        return df
    
    def get_last_signal(self, symbol: str) -> Optional[Dict]:
        """
        Get the most recent signal for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with signal info or None
        """
        query = text("""
            SELECT * FROM ma_crossover_signals
            WHERE symbol = :symbol
            ORDER BY signal_date DESC
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'symbol': symbol}).fetchone()
        
        if result:
            return dict(result._mapping)
        return None
    
    def get_opposite_signal(self, symbol: str, signal_type: CrossoverType) -> Optional[Dict]:
        """
        Get the last opposite signal for a symbol.
        
        If signal_type is GOLDEN_CROSS, returns last DEATH_CROSS and vice versa.
        
        Args:
            symbol: Stock symbol
            signal_type: Current signal type
            
        Returns:
            Dict with opposite signal info or None
        """
        opposite_type = (CrossoverType.DEATH_CROSS if signal_type == CrossoverType.GOLDEN_CROSS 
                        else CrossoverType.GOLDEN_CROSS)
        
        query = text("""
            SELECT * FROM ma_crossover_signals
            WHERE symbol = :symbol AND signal_type = :signal_type
            ORDER BY signal_date DESC
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'symbol': symbol,
                'signal_type': opposite_type.value
            }).fetchone()
        
        if result:
            return dict(result._mapping)
        return None
    
    def backfill_previous_signals(self) -> int:
        """
        Backfill previous signal info for existing records that are missing it.
        This updates records in the database where previous_signal_type is NULL.
        
        Returns:
            Number of records updated
        """
        # Find all records missing previous signal info
        query = text("""
            SELECT id, symbol, signal_date, signal_type
            FROM ma_crossover_signals
            WHERE previous_signal_type IS NULL
            ORDER BY symbol, signal_date
        """)
        
        updated = 0
        
        with self.engine.connect() as conn:
            records = conn.execute(query).fetchall()
        
        if not records:
            logger.info("No records need previous signal backfill")
            return 0
        
        logger.info(f"Backfilling previous signal info for {len(records)} records...")
        
        with self.engine.begin() as conn:
            for record in records:
                record_id = record[0]
                symbol = record[1]
                signal_date = record[2]
                
                # Find the previous signal for this symbol
                prev_query = text("""
                    SELECT signal_type, signal_date 
                    FROM ma_crossover_signals
                    WHERE symbol = :symbol 
                      AND signal_date < :signal_date
                    ORDER BY signal_date DESC
                    LIMIT 1
                """)
                
                prev_result = conn.execute(prev_query, {
                    'symbol': symbol,
                    'signal_date': signal_date
                }).fetchone()
                
                if prev_result:
                    prev_type = prev_result[0]
                    prev_date = prev_result[1]
                    days_since = (signal_date - prev_date).days
                    
                    # Update the record
                    conn.execute(text("""
                        UPDATE ma_crossover_signals
                        SET previous_signal_type = :prev_type,
                            previous_signal_date = :prev_date,
                            days_since_previous = :days_since
                        WHERE id = :id
                    """), {
                        'id': record_id,
                        'prev_type': prev_type,
                        'prev_date': prev_date,
                        'days_since': days_since
                    })
                    updated += 1
        
        logger.info(f"Updated {updated} records with previous signal info")
        return updated
    
    def get_signals_summary(self, target_date: Optional[date] = None) -> Dict:
        """
        Get summary statistics of signals.
        
        Args:
            target_date: Date to summarize (default: today)
            
        Returns:
            Dict with summary statistics
        """
        if target_date is None:
            target_date = date.today()
        
        with self.engine.connect() as conn:
            # Today's signals
            today_result = conn.execute(text("""
                SELECT signal_type, COUNT(*) as cnt
                FROM ma_crossover_signals
                WHERE signal_date = :target_date
                GROUP BY signal_type
            """), {'target_date': target_date}).fetchall()
            
            today_counts = {row[0]: row[1] for row in today_result}
            
            # Last 30 days
            month_result = conn.execute(text("""
                SELECT signal_type, COUNT(*) as cnt
                FROM ma_crossover_signals
                WHERE signal_date >= DATE_SUB(:target_date, INTERVAL 30 DAY)
                GROUP BY signal_type
            """), {'target_date': target_date}).fetchall()
            
            month_counts = {row[0]: row[1] for row in month_result}
            
            # Total signals
            total_result = conn.execute(text("""
                SELECT signal_type, COUNT(*) as cnt
                FROM ma_crossover_signals
                GROUP BY signal_type
            """)).fetchall()
            
            total_counts = {row[0]: row[1] for row in total_result}
        
        return {
            'date': target_date,
            'today': {
                'golden_cross': today_counts.get('GOLDEN_CROSS', 0),
                'death_cross': today_counts.get('DEATH_CROSS', 0),
            },
            'last_30_days': {
                'golden_cross': month_counts.get('GOLDEN_CROSS', 0),
                'death_cross': month_counts.get('DEATH_CROSS', 0),
            },
            'total': {
                'golden_cross': total_counts.get('GOLDEN_CROSS', 0),
                'death_cross': total_counts.get('DEATH_CROSS', 0),
            }
        }
    
    def update_performance(self, lookback_days: int = 30):
        """
        Update performance metrics (1d, 5d, 20d returns) for signals.
        Only updates signals that don't have performance data yet.
        
        Args:
            lookback_days: How far back to look for signals to update
        """
        # Find signals without performance data
        query = text("""
            SELECT id, symbol, signal_date, close_price
            FROM ma_crossover_signals
            WHERE signal_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
              AND signal_date <= DATE_SUB(CURDATE(), INTERVAL 20 DAY)
              AND pct_change_20d IS NULL
        """)
        
        with self.engine.connect() as conn:
            signals = conn.execute(query, {'days': lookback_days + 20}).fetchall()
        
        if not signals:
            logger.info("No signals need performance updates")
            return
        
        logger.info(f"Updating performance for {len(signals)} signals...")
        
        updates = 0
        with self.engine.begin() as conn:
            for row in signals:
                signal_id = row[0]
                symbol = row[1]
                signal_date = row[2]
                signal_price = float(row[3])
                
                # Get future prices
                price_query = text("""
                    SELECT date, close FROM yfinance_daily_ma
                    WHERE symbol = :symbol AND date > :signal_date
                    ORDER BY date
                    LIMIT 25
                """)
                
                future_prices = conn.execute(price_query, {
                    'symbol': symbol,
                    'signal_date': signal_date
                }).fetchall()
                
                if not future_prices:
                    continue
                
                # Find 1d, 5d, 20d prices
                price_1d = price_5d = price_20d = None
                pct_1d = pct_5d = pct_20d = None
                
                for i, (dt, price) in enumerate(future_prices):
                    trading_days = i + 1
                    if trading_days == 1 and price_1d is None:
                        price_1d = float(price)
                        pct_1d = (price_1d - signal_price) / signal_price * 100
                    elif trading_days == 5 and price_5d is None:
                        price_5d = float(price)
                        pct_5d = (price_5d - signal_price) / signal_price * 100
                    elif trading_days >= 20 and price_20d is None:
                        price_20d = float(price)
                        pct_20d = (price_20d - signal_price) / signal_price * 100
                        break
                
                # Update record
                conn.execute(text("""
                    UPDATE ma_crossover_signals
                    SET price_1d_later = :p1, price_5d_later = :p5, price_20d_later = :p20,
                        pct_change_1d = :pct1, pct_change_5d = :pct5, pct_change_20d = :pct20
                    WHERE id = :id
                """), {
                    'id': signal_id,
                    'p1': price_1d, 'p5': price_5d, 'p20': price_20d,
                    'pct1': pct_1d, 'pct5': pct_5d, 'pct20': pct_20d
                })
                updates += 1
        
        logger.info(f"Updated performance for {updates} signals")


def run_daily_scan(progress_callback=None):
    """
    Run daily scan for crossover signals.
    This is called by the Daily Data Wizard.
    
    Args:
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (signals_found, signals_saved)
    """
    detector = CrossoverDetector()
    target_date = date.today()
    
    if progress_callback:
        progress_callback(f"Scanning for crossovers on {target_date}...")
    
    signals = detector.scan_for_date(target_date)
    
    if progress_callback:
        progress_callback(f"Found {len(signals)} crossover signals")
    
    saved = detector.save_signals(signals)
    
    # Also update performance for older signals
    detector.update_performance()
    
    return len(signals), saved


def main():
    """Main entry point - run full historical scan."""
    print("=" * 70)
    print("   GOLDEN CROSS / DEATH CROSS SCANNER")
    print("=" * 70)
    print()
    
    detector = CrossoverDetector()
    
    # Scan last 1 year
    start_date = date.today() - timedelta(days=365)
    end_date = date.today()
    
    print(f"Scanning from {start_date} to {end_date}...")
    print()
    
    def progress(current, total, symbol):
        print(f"\r  Progress: {current}/{total} ({symbol})          ", end='')
    
    signals = detector.scan_all_stocks(start_date=start_date, end_date=end_date, 
                                        progress_callback=progress)
    print()
    
    # Save to database
    saved = detector.save_signals(signals)
    print(f"\nSaved {saved} signals to database")
    
    # Update performance
    print("\nUpdating performance metrics...")
    detector.update_performance()
    
    # Show summary
    summary = detector.get_signals_summary()
    print("\n" + "=" * 70)
    print("   SUMMARY")
    print("=" * 70)
    print(f"\nToday ({summary['date']}):")
    print(f"  Golden Cross: {summary['today']['golden_cross']}")
    print(f"  Death Cross:  {summary['today']['death_cross']}")
    print(f"\nLast 30 Days:")
    print(f"  Golden Cross: {summary['last_30_days']['golden_cross']}")
    print(f"  Death Cross:  {summary['last_30_days']['death_cross']}")
    print(f"\nAll Time:")
    print(f"  Golden Cross: {summary['total']['golden_cross']}")
    print(f"  Death Cross:  {summary['total']['death_cross']}")
    
    # Show recent signals
    print("\n" + "=" * 70)
    print("   RECENT SIGNALS (Last 5 Days)")
    print("=" * 70)
    
    recent = detector.load_signals(
        start_date=date.today() - timedelta(days=5),
        limit=50
    )
    
    if not recent.empty:
        for signal_type in ['GOLDEN_CROSS', 'DEATH_CROSS']:
            type_df = recent[recent['signal_type'] == signal_type]
            emoji = "🟢" if signal_type == 'GOLDEN_CROSS' else "🔴"
            print(f"\n{emoji} {signal_type.replace('_', ' ')} ({len(type_df)} stocks):")
            for _, row in type_df.head(10).iterrows():
                print(f"   {row['symbol']:15} | {row['signal_date']} | ₹{row['close_price']:,.2f}")
    else:
        print("\nNo recent signals found")
    
    print("\n✅ Scan complete!")


if __name__ == "__main__":
    main()
