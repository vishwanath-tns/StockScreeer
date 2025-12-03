"""
Volume Scanner
==============

Scan stocks for accumulation and distribution signals.
Uses data from the marketdata MySQL database (yfinance_daily_quotes table).

Usage:
    scanner = VolumeScanner()
    
    # Scan all Nifty 500 stocks
    results = scanner.scan_nifty500()
    
    # Print top accumulation candidates
    for stock in results['accumulation'][:10]:
        print(f"{stock.symbol}: {stock.score:.1f}")
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from dotenv import load_dotenv

# Database imports
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

from ..analysis.accumulation_detector import (
    AccumulationDetector, 
    AccumulationSignal, 
    PhaseType, 
    SignalStrength
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class ScanResults:
    """
    Results from a volume scan.
    
    Attributes:
        timestamp: When the scan was performed
        total_scanned: Number of stocks scanned
        accumulation: List of stocks in accumulation phase
        distribution: List of stocks in distribution phase
        neutral: List of stocks in neutral phase
        errors: List of symbols that failed to scan
    """
    timestamp: datetime = field(default_factory=datetime.now)
    total_scanned: int = 0
    accumulation: List[AccumulationSignal] = field(default_factory=list)
    distribution: List[AccumulationSignal] = field(default_factory=list)
    neutral: List[AccumulationSignal] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        """Get a summary of the scan results."""
        return f"""
Volume Scan Results - {self.timestamp.strftime('%Y-%m-%d %H:%M')}
{'=' * 60}
Total Scanned: {self.total_scanned}
Accumulation: {len(self.accumulation)} stocks
Distribution: {len(self.distribution)} stocks
Neutral: {len(self.neutral)} stocks
Errors: {len(self.errors)} stocks
"""


class VolumeScanner:
    """
    Scan stocks for accumulation/distribution signals.
    
    Uses the yfinance_daily_quotes table from marketdata database
    to analyze volume patterns without downloading new data.
    """
    
    def __init__(self, 
                 lookback_days: int = 90,
                 min_volume: int = 100000,
                 min_price: float = 10.0):
        """
        Initialize the scanner.
        
        Args:
            lookback_days: Days of historical data to analyze
            min_volume: Minimum average daily volume filter
            min_price: Minimum stock price filter
        """
        self.lookback_days = lookback_days
        self.min_volume = min_volume
        self.min_price = min_price
        self.detector = AccumulationDetector()
        
        # Database configuration
        self.db_host = os.getenv('MYSQL_HOST', 'localhost')
        self.db_port = int(os.getenv('MYSQL_PORT', 3306))
        self.db_user = os.getenv('MYSQL_USER', 'root')
        self.db_password = os.getenv('MYSQL_PASSWORD', '')
        self.db_name = os.getenv('MYSQL_DB', 'marketdata')
        
        self._engine = None
    
    def _get_engine(self):
        """Create database engine with connection pooling."""
        if self._engine is None:
            password = quote_plus(self.db_password)
            connection_string = (
                f"mysql+pymysql://{self.db_user}:{password}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}"
            )
            self._engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=5,
                max_overflow=10
            )
        return self._engine
    
    def get_nifty500_symbols(self) -> List[str]:
        """
        Get list of Nifty 500 symbols from database.
        
        Returns:
            List of stock symbols
        """
        engine = self._get_engine()
        
        # Try to get from nifty500 table first
        query = """
        SELECT DISTINCT symbol 
        FROM yfinance_daily_quotes 
        WHERE timeframe = 'Daily'
        AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        ORDER BY symbol
        """
        
        try:
            with engine.connect() as conn:
                result = pd.read_sql(text(query), conn)
                symbols = result['symbol'].tolist()
                
                # Filter out index symbols
                symbols = [s for s in symbols if not s.startswith('^')]
                
                logger.info(f"Found {len(symbols)} symbols in database")
                return symbols
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            return []
    
    def get_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data for a symbol from database.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            
        Returns:
            DataFrame with OHLCV data or None if not found
        """
        engine = self._get_engine()
        
        start_date = (datetime.now() - timedelta(days=self.lookback_days + 30)).strftime('%Y-%m-%d')
        
        query = """
        SELECT 
            date,
            open,
            high,
            low,
            close,
            volume,
            adj_close
        FROM yfinance_daily_quotes
        WHERE symbol = :symbol
        AND timeframe = 'Daily'
        AND date >= :start_date
        ORDER BY date ASC
        """
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql(
                    text(query), 
                    conn, 
                    params={'symbol': symbol, 'start_date': start_date}
                )
                
                if df.empty:
                    return None
                
                # Ensure proper data types
                df['date'] = pd.to_datetime(df['date'])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Drop NaN rows
                df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
                
                return df
                
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def scan_symbol(self, symbol: str) -> Optional[AccumulationSignal]:
        """
        Scan a single symbol for accumulation/distribution.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            AccumulationSignal or None if scan fails
        """
        try:
            # Get data from database
            df = self.get_stock_data(symbol)
            
            if df is None or len(df) < 60:
                logger.debug(f"Insufficient data for {symbol}")
                return None
            
            # Apply filters
            avg_volume = df['volume'].tail(20).mean()
            latest_close = df['close'].iloc[-1]
            
            if avg_volume < self.min_volume:
                logger.debug(f"Volume filter: {symbol} ({avg_volume:.0f} < {self.min_volume})")
                return None
            
            if latest_close < self.min_price:
                logger.debug(f"Price filter: {symbol} (₹{latest_close:.2f} < ₹{self.min_price})")
                return None
            
            # Run analysis
            signal = self.detector.analyze(df, symbol)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None
    
    def scan_symbols(self, symbols: List[str], 
                     max_workers: int = 5,
                     progress_callback=None) -> ScanResults:
        """
        Scan multiple symbols for accumulation/distribution.
        
        Args:
            symbols: List of symbols to scan
            max_workers: Number of parallel workers
            progress_callback: Optional callback function(current, total, symbol)
            
        Returns:
            ScanResults with categorized signals
        """
        results = ScanResults()
        results.total_scanned = len(symbols)
        
        completed = 0
        
        # Use sequential processing for database access to avoid connection issues
        for symbol in symbols:
            try:
                signal = self.scan_symbol(symbol)
                
                if signal is None:
                    results.errors.append(symbol)
                elif signal.phase == PhaseType.ACCUMULATION:
                    results.accumulation.append(signal)
                elif signal.phase == PhaseType.DISTRIBUTION:
                    results.distribution.append(signal)
                else:
                    results.neutral.append(signal)
                    
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                results.errors.append(symbol)
            
            completed += 1
            if progress_callback:
                progress_callback(completed, len(symbols), symbol)
        
        # Sort by score
        results.accumulation.sort(key=lambda x: x.score, reverse=True)
        results.distribution.sort(key=lambda x: x.score)
        
        return results
    
    def scan_nifty500(self, progress_callback=None) -> ScanResults:
        """
        Scan all Nifty 500 stocks.
        
        Args:
            progress_callback: Optional callback function(current, total, symbol)
            
        Returns:
            ScanResults with categorized signals
        """
        symbols = self.get_nifty500_symbols()
        
        if not symbols:
            logger.error("No symbols found to scan")
            return ScanResults()
        
        logger.info(f"Scanning {len(symbols)} Nifty 500 stocks...")
        
        return self.scan_symbols(symbols, progress_callback=progress_callback)
    
    def display_results(self, results: ScanResults, 
                        top_n: int = 20,
                        show_details: bool = False) -> None:
        """
        Display scan results to console.
        
        Args:
            results: ScanResults object
            top_n: Number of top results to show
            show_details: Show detailed analysis for each stock
        """
        print(results.summary())
        
        # Top Accumulation
        print("\n🟢 TOP ACCUMULATION CANDIDATES")
        print("=" * 80)
        print(f"{'Symbol':<15} {'Score':>8} {'OBV':>8} {'A/D':>8} {'CMF':>8} {'Vol':>8} {'Price':>12}")
        print("-" * 80)
        
        for signal in results.accumulation[:top_n]:
            cmf_val = signal.details.get('cmf', {}).get('current', 0)
            price = signal.details.get('latest_close', 0)
            print(
                f"{signal.symbol:<15} "
                f"{signal.score:>8.1f} "
                f"{signal.obv_score:>8.1f} "
                f"{signal.ad_score:>8.1f} "
                f"{cmf_val:>8.3f} "
                f"{signal.volume_score:>8.1f} "
                f"₹{price:>10.2f}"
            )
            
            if show_details:
                print(f"   CMF: {cmf_val:.3f}, OBV Trend: {'↑' if signal.details['obv']['trending_up'] else '↓'}")
        
        # Top Distribution
        print("\n🔴 TOP DISTRIBUTION CANDIDATES")
        print("=" * 80)
        print(f"{'Symbol':<15} {'Score':>8} {'OBV':>8} {'A/D':>8} {'CMF':>8} {'Vol':>8} {'Price':>12}")
        print("-" * 80)
        
        for signal in results.distribution[:top_n]:
            cmf_val = signal.details.get('cmf', {}).get('current', 0)
            price = signal.details.get('latest_close', 0)
            print(
                f"{signal.symbol:<15} "
                f"{signal.score:>8.1f} "
                f"{signal.obv_score:>8.1f} "
                f"{signal.ad_score:>8.1f} "
                f"{cmf_val:>8.3f} "
                f"{signal.volume_score:>8.1f} "
                f"₹{price:>10.2f}"
            )
    
    def export_to_csv(self, results: ScanResults, 
                      filename: str = None) -> str:
        """
        Export results to CSV file.
        
        Args:
            results: ScanResults object
            filename: Output filename (default: volume_scan_YYYYMMDD.csv)
            
        Returns:
            Path to the created file
        """
        if filename is None:
            filename = f"volume_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        
        # Combine all signals
        all_signals = results.accumulation + results.distribution + results.neutral
        
        rows = []
        for signal in all_signals:
            row = {
                'symbol': signal.symbol,
                'phase': signal.phase.value,
                'strength': signal.strength.value,
                'composite_score': signal.score,
                'obv_score': signal.obv_score,
                'ad_score': signal.ad_score,
                'cmf_score': signal.cmf_score,
                'volume_score': signal.volume_score,
                'price_action_score': signal.price_action_score,
                'cmf_current': signal.details.get('cmf', {}).get('current', None),
                'latest_close': signal.details.get('latest_close', None),
                'avg_volume_20d': signal.details.get('avg_volume_20d', None),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df = df.sort_values('composite_score', ascending=False)
        df.to_csv(filename, index=False)
        
        logger.info(f"Results exported to {filename}")
        return filename


if __name__ == "__main__":
    # Test the scanner
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("Volume Scanner - Testing")
    print("=" * 60)
    
    scanner = VolumeScanner(
        lookback_days=90,
        min_volume=50000,
        min_price=10.0
    )
    
    # Test with a few symbols
    test_symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']
    
    def progress(current, total, symbol):
        print(f"  [{current}/{total}] Scanning {symbol}...")
    
    results = scanner.scan_symbols(test_symbols, progress_callback=progress)
    
    scanner.display_results(results, top_n=10)
