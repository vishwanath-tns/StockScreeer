"""
Daily Bollinger Bands Computation Service

Runs after market close to precompute BB indicators for all stocks.
Stores results in database for fast scanning and analysis.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..models.bb_models import BBConfig, BollingerBands, BB_PRESETS
from ..models.scan_models import SqueezeScanResult, TrendScanResult
from ..services.bb_calculator import BBCalculator
from ..services.squeeze_detector import SqueezeDetector
from ..services.trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ComputeStats:
    """Statistics from a compute run."""
    symbols_processed: int = 0
    symbols_failed: int = 0
    records_inserted: int = 0
    signals_generated: int = 0
    squeeze_count: int = 0
    bulge_count: int = 0
    uptrend_count: int = 0
    downtrend_count: int = 0
    execution_time_sec: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class DailyBBCompute:
    """
    Daily computation of Bollinger Bands indicators.
    
    Workflow:
    1. Get list of active symbols from nse_equity_bhavcopy_full
    2. For each symbol, fetch OHLC history (last 252 trading days)
    3. Calculate BB indicators (standard, tight, wide presets)
    4. Store daily BB values in stock_bollinger_daily
    5. Detect squeeze/bulge states
    6. Classify trends
    7. Generate and store signals
    8. Update scan cache for fast queries
    """
    
    # Default BB configurations to compute
    BB_CONFIGS = [
        ("standard", BBConfig(period=20, std_dev=2.0)),
        ("tight", BBConfig(period=20, std_dev=1.5)),
        ("wide", BBConfig(period=20, std_dev=2.5)),
    ]
    
    def __init__(self, 
                 engine: Engine,
                 lookback_days: int = 252,
                 progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        Initialize the daily compute service.
        
        Args:
            engine: SQLAlchemy engine for database connection
            lookback_days: Days of history to fetch for calculations
            progress_callback: Optional callback(current, total, message) for progress updates
        """
        self.engine = engine
        self.lookback_days = lookback_days
        self.progress_callback = progress_callback
        
        self.calculator = BBCalculator()
        self.squeeze_detector = SqueezeDetector()
        self.trend_analyzer = TrendAnalyzer()
    
    def run(self, 
            trade_date: Optional[date] = None,
            symbols: Optional[List[str]] = None) -> ComputeStats:
        """
        Run the daily BB computation.
        
        Args:
            trade_date: Date to compute for (default: latest available)
            symbols: Optional list of symbols to process (default: all active)
            
        Returns:
            ComputeStats with results
        """
        start_time = datetime.now()
        stats = ComputeStats()
        
        try:
            # Get trade date if not specified
            if trade_date is None:
                trade_date = self._get_latest_trade_date()
                if trade_date is None:
                    stats.errors.append("No trade data available")
                    return stats
            
            logger.info(f"Starting BB computation for {trade_date}")
            self._update_progress(0, 100, f"Starting computation for {trade_date}")
            
            # Get symbols to process
            if symbols is None:
                symbols = self._get_active_symbols(trade_date)
            
            if not symbols:
                stats.errors.append("No symbols to process")
                return stats
            
            total = len(symbols)
            logger.info(f"Processing {total} symbols")
            
            # Process each symbol
            batch_data = []
            for i, symbol in enumerate(symbols):
                try:
                    result = self._process_symbol(symbol, trade_date)
                    if result:
                        batch_data.append(result)
                        stats.symbols_processed += 1
                        
                        # Track states
                        if result.get('is_squeeze'):
                            stats.squeeze_count += 1
                        if result.get('is_bulge'):
                            stats.bulge_count += 1
                        if result.get('trend') == 'uptrend':
                            stats.uptrend_count += 1
                        elif result.get('trend') == 'downtrend':
                            stats.downtrend_count += 1
                    else:
                        stats.symbols_failed += 1
                        
                except Exception as e:
                    stats.symbols_failed += 1
                    stats.errors.append(f"{symbol}: {str(e)}")
                    logger.error(f"Error processing {symbol}: {e}")
                
                # Progress update every 10 symbols
                if (i + 1) % 10 == 0:
                    pct = int((i + 1) / total * 100)
                    self._update_progress(pct, 100, f"Processed {i+1}/{total} symbols")
            
            # Bulk insert results
            if batch_data:
                stats.records_inserted = self._bulk_insert(batch_data, trade_date)
            
            # Update scan cache
            self._update_scan_cache(trade_date, stats)
            
            stats.execution_time_sec = (datetime.now() - start_time).total_seconds()
            logger.info(f"Computation complete: {stats.symbols_processed} symbols in {stats.execution_time_sec:.1f}s")
            self._update_progress(100, 100, "Computation complete")
            
        except Exception as e:
            stats.errors.append(f"Fatal error: {str(e)}")
            logger.exception("Fatal error in BB computation")
        
        return stats
    
    def _get_latest_trade_date(self) -> Optional[date]:
        """Get the most recent trade date from Yahoo Finance data."""
        query = """
            SELECT MAX(date) as latest_date
            FROM yfinance_daily_quotes
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query)).fetchone()
            return result[0] if result and result[0] else None
    
    def _get_active_symbols(self, trade_date: date) -> List[str]:
        """Get list of symbols (stocks + indices) that traded on the given date."""
        query = """
            SELECT DISTINCT symbol
            FROM yfinance_daily_quotes
            WHERE date = :trade_date
            ORDER BY 
                CASE WHEN symbol LIKE '^%%' THEN 0 ELSE 1 END,
                symbol
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"trade_date": trade_date})
            return [row[0] for row in result]
    
    def _process_symbol(self, symbol: str, trade_date: date) -> Optional[Dict]:
        """
        Process a single symbol: fetch OHLC, calculate BB, detect states.
        
        Returns dict with all computed values or None if insufficient data.
        """
        # Fetch OHLC history
        df = self._fetch_ohlc(symbol, trade_date)
        
        if df is None or len(df) < 30:  # Need at least 30 days for BB
            return None
        
        # Add symbol column for calculator
        df['symbol'] = symbol
        
        # Calculate BB using the calculate() method
        config = self.BB_CONFIGS[0][1]  # Standard 20,2
        self.calculator.config = config
        bb_result = self.calculator.calculate(df, bandwidth_lookback=126)
        
        if not bb_result.success or not bb_result.current:
            return None
        
        # Get latest BB values
        latest = bb_result.current
        
        # Calculate bandwidth percentile over 126 days (6 months)
        bw_percentile = latest.bandwidth_percentile
        
        # Detect squeeze/bulge
        is_squeeze = bw_percentile <= 10  # Bottom 10%
        is_bulge = bw_percentile >= 90    # Top 10%
        
        # Classify trend based on %b using history
        if bb_result.history and len(bb_result.history) >= 5:
            recent_pb = [bb.percent_b for bb in bb_result.history[:5]]  # Most recent 5
            avg_pb = sum(recent_pb) / len(recent_pb)
            
            if avg_pb > 0.7:
                trend = 'uptrend'
                trend_strength = min((avg_pb - 0.5) * 200, 100)
            elif avg_pb < 0.3:
                trend = 'downtrend'
                trend_strength = min((0.5 - avg_pb) * 200, 100)
            else:
                trend = 'neutral'
                trend_strength = 50 - abs(avg_pb - 0.5) * 100
        else:
            trend = 'neutral'
            trend_strength = 50.0
        
        # Count consecutive days in current state using history
        squeeze_days = self._count_consecutive_state_from_history(bb_result.history, lambda bb: bb.bandwidth_percentile <= 10) if is_squeeze else 0
        trend_days = self._count_consecutive_trend_from_history(bb_result.history, trend)
        
        return {
            'symbol': symbol,
            'trade_date': trade_date,
            'close': latest.close,
            'upper_band': latest.upper,
            'middle_band': latest.middle,
            'lower_band': latest.lower,
            'percent_b': latest.percent_b,
            'bandwidth': latest.bandwidth,
            'bandwidth_percentile': bw_percentile,
            'is_squeeze': is_squeeze,
            'is_bulge': is_bulge,
            'squeeze_days': squeeze_days,
            'trend': trend,
            'trend_strength': trend_strength,
            'trend_days': trend_days,
            # Additional metrics
            'sma_20': latest.middle,
            'distance_from_middle': ((latest.close - latest.middle) / latest.middle) * 100 if latest.middle else 0,
        }
    
    def _count_consecutive_state_from_history(self, history: List, condition: Callable) -> int:
        """Count consecutive days from history where condition is True."""
        if not history:
            return 0
        count = 0
        for bb in history:  # History is most recent first
            if condition(bb):
                count += 1
            else:
                break
        return count
    
    def _count_consecutive_trend_from_history(self, history: List, current_trend: str) -> int:
        """Count consecutive days in the same trend."""
        if not history or len(history) < 5:
            return 0
        
        count = 0
        window = 5
        
        for i in range(0, len(history) - window + 1):
            recent_pb = [bb.percent_b for bb in history[i:i+window]]
            avg_pb = sum(recent_pb) / len(recent_pb)
            
            if avg_pb > 0.7:
                trend = 'uptrend'
            elif avg_pb < 0.3:
                trend = 'downtrend'
            else:
                trend = 'neutral'
            
            if trend == current_trend:
                count += 1
            else:
                break
        
        return count
    
    def _fetch_ohlc(self, symbol: str, end_date: date) -> Optional[pd.DataFrame]:
        """Fetch OHLC history for a symbol from Yahoo Finance data."""
        start_date = end_date - timedelta(days=self.lookback_days * 2)  # Extra buffer for non-trading days
        
        query = """
            SELECT date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol
              AND date BETWEEN :start_date AND :end_date
            ORDER BY date ASC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(
                text(query),
                conn,
                params={'symbol': symbol, 'start_date': start_date, 'end_date': end_date}
            )
        
        if df.empty:
            return None
        
        # Limit to lookback_days
        return df.tail(self.lookback_days)
    
    def _count_consecutive_state(self, bb_series: List[BollingerBands], 
                                   condition: Callable[[BollingerBands], bool]) -> int:
        """Count consecutive days matching a condition from most recent."""
        count = 0
        for bb in reversed(bb_series):
            if condition(bb):
                count += 1
            else:
                break
        return count
    
    def _count_consecutive_trend(self, bb_series: List[BollingerBands], trend: str) -> int:
        """Count consecutive days in the same trend."""
        count = 0
        for bb in reversed(bb_series):
            if trend == 'uptrend' and bb.percent_b > 0.6:
                count += 1
            elif trend == 'downtrend' and bb.percent_b < 0.4:
                count += 1
            elif trend == 'neutral' and 0.4 <= bb.percent_b <= 0.6:
                count += 1
            else:
                break
        return count
    
    def _bulk_insert(self, data: List[Dict], trade_date: date) -> int:
        """Bulk insert/update BB data into database."""
        if not data:
            return 0
        
        df = pd.DataFrame(data)
        
        # Use INSERT ... ON DUPLICATE KEY UPDATE for upsert
        with self.engine.begin() as conn:
            # Delete existing data for this date (simpler than upsert for bulk)
            conn.execute(
                text("DELETE FROM stock_bollinger_daily WHERE trade_date = :td"),
                {"td": trade_date}
            )
            
            # Insert new data
            df.to_sql(
                'stock_bollinger_daily',
                conn,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=500
            )
        
        return len(data)
    
    def _update_scan_cache(self, trade_date: date, stats: ComputeStats):
        """Update scan cache tables for fast lookups."""
        with self.engine.begin() as conn:
            # Update squeeze cache
            conn.execute(text("""
                INSERT INTO stock_bb_scan_cache (scan_type, trade_date, symbol_count, updated_at)
                VALUES ('squeeze', :td, :count, NOW())
                ON DUPLICATE KEY UPDATE symbol_count = :count, updated_at = NOW()
            """), {"td": trade_date, "count": stats.squeeze_count})
            
            # Update bulge cache
            conn.execute(text("""
                INSERT INTO stock_bb_scan_cache (scan_type, trade_date, symbol_count, updated_at)
                VALUES ('bulge', :td, :count, NOW())
                ON DUPLICATE KEY UPDATE symbol_count = :count, updated_at = NOW()
            """), {"td": trade_date, "count": stats.bulge_count})
            
            # Update trend caches
            conn.execute(text("""
                INSERT INTO stock_bb_scan_cache (scan_type, trade_date, symbol_count, updated_at)
                VALUES ('uptrend', :td, :count, NOW())
                ON DUPLICATE KEY UPDATE symbol_count = :count, updated_at = NOW()
            """), {"td": trade_date, "count": stats.uptrend_count})
            
            conn.execute(text("""
                INSERT INTO stock_bb_scan_cache (scan_type, trade_date, symbol_count, updated_at)
                VALUES ('downtrend', :td, :count, NOW())
                ON DUPLICATE KEY UPDATE symbol_count = :count, updated_at = NOW()
            """), {"td": trade_date, "count": stats.downtrend_count})
    
    def _update_progress(self, current: int, total: int, message: str):
        """Send progress update if callback is set."""
        if self.progress_callback:
            try:
                self.progress_callback(current, total, message)
            except Exception:
                pass


def create_bb_tables(engine: Engine) -> bool:
    """
    Create the required database tables for BB storage.
    
    Tables:
    - stock_bollinger_daily: Daily BB values for all symbols
    - stock_bb_signals: Generated buy/sell signals
    - stock_bb_ratings_history: Historical ratings
    - stock_bb_scan_cache: Precomputed scan results
    """
    
    ddl_statements = [
        # Main daily BB data
        """
        CREATE TABLE IF NOT EXISTS stock_bollinger_daily (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            trade_date DATE NOT NULL,
            close DECIMAL(12,2) NOT NULL,
            upper_band DECIMAL(12,2),
            middle_band DECIMAL(12,2),
            lower_band DECIMAL(12,2),
            percent_b DECIMAL(8,4),
            bandwidth DECIMAL(8,4),
            bandwidth_percentile DECIMAL(5,2),
            is_squeeze BOOLEAN DEFAULT FALSE,
            is_bulge BOOLEAN DEFAULT FALSE,
            squeeze_days INT DEFAULT 0,
            trend VARCHAR(20),
            trend_strength DECIMAL(5,2),
            trend_days INT DEFAULT 0,
            sma_20 DECIMAL(12,2),
            distance_from_middle DECIMAL(8,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE KEY uk_symbol_date (symbol, trade_date),
            INDEX idx_trade_date (trade_date),
            INDEX idx_squeeze (is_squeeze, trade_date),
            INDEX idx_bulge (is_bulge, trade_date),
            INDEX idx_trend (trend, trade_date),
            INDEX idx_percent_b (percent_b)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        
        # Signals table
        """
        CREATE TABLE IF NOT EXISTS stock_bb_signals (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            signal_date DATE NOT NULL,
            signal_type VARCHAR(30) NOT NULL,
            signal_direction VARCHAR(10) NOT NULL,
            confidence INT DEFAULT 50,
            entry_price DECIMAL(12,2),
            stop_loss DECIMAL(12,2),
            target_price DECIMAL(12,2),
            percent_b DECIMAL(8,4),
            bandwidth DECIMAL(8,4),
            pattern_type VARCHAR(30),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            INDEX idx_symbol_date (symbol, signal_date),
            INDEX idx_signal_type (signal_type, signal_date),
            INDEX idx_direction (signal_direction, signal_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        
        # Ratings history
        """
        CREATE TABLE IF NOT EXISTS stock_bb_ratings_history (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            rating_date DATE NOT NULL,
            overall_rating DECIMAL(5,2),
            letter_grade CHAR(2),
            squeeze_score DECIMAL(5,2),
            trend_score DECIMAL(5,2),
            momentum_score DECIMAL(5,2),
            pattern_score DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE KEY uk_symbol_date (symbol, rating_date),
            INDEX idx_rating_date (rating_date),
            INDEX idx_overall_rating (overall_rating)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        
        # Scan cache for fast queries
        """
        CREATE TABLE IF NOT EXISTS stock_bb_scan_cache (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scan_type VARCHAR(30) NOT NULL,
            trade_date DATE NOT NULL,
            symbol_count INT DEFAULT 0,
            symbols_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            UNIQUE KEY uk_scan_date (scan_type, trade_date),
            INDEX idx_trade_date (trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    ]
    
    try:
        with engine.begin() as conn:
            for ddl in ddl_statements:
                conn.execute(text(ddl))
        logger.info("BB tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create BB tables: {e}")
        return False


# Convenience function for running from command line
def run_daily_compute():
    """Run daily BB computation with database connection from environment."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Build connection string
    from urllib.parse import quote_plus
    
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    database = os.getenv('MYSQL_DB', 'stockdata')
    
    # URL-encode password to handle special characters like @
    encoded_password = quote_plus(password)
    conn_str = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
    engine = create_engine(conn_str, pool_pre_ping=True)
    
    # Ensure tables exist
    create_bb_tables(engine)
    
    # Run computation
    compute = DailyBBCompute(
        engine,
        progress_callback=lambda c, t, m: print(f"[{c}%] {m}")
    )
    
    stats = compute.run()
    
    print("\n" + "="*50)
    print("COMPUTATION COMPLETE")
    print("="*50)
    print(f"Symbols processed: {stats.symbols_processed}")
    print(f"Symbols failed: {stats.symbols_failed}")
    print(f"Records inserted: {stats.records_inserted}")
    print(f"Squeeze stocks: {stats.squeeze_count}")
    print(f"Bulge stocks: {stats.bulge_count}")
    print(f"Uptrend stocks: {stats.uptrend_count}")
    print(f"Downtrend stocks: {stats.downtrend_count}")
    print(f"Execution time: {stats.execution_time_sec:.1f} seconds")
    
    if stats.errors:
        print(f"\nErrors ({len(stats.errors)}):")
        for err in stats.errors[:10]:  # Show first 10
            print(f"  - {err}")
    
    return stats


if __name__ == "__main__":
    run_daily_compute()
