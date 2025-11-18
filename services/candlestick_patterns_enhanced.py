"""
Enhanced Candlestick Pattern Detection Services with Timeframe Support
====================================================================

High-performance, scalable services for detecting and storing candlestick patterns.
Supports Daily, Weekly, and Monthly timeframes using existing database tables.
Focuses on Narrow Range (NR) patterns: NR4, NR7, NR13, NR21.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Database imports
try:
    from services.market_breadth_service import get_engine
except ImportError:
    try:
        from db.connection import ensure_engine
        get_engine = ensure_engine
    except ImportError:
        print("Warning: Could not import database connection. Using fallback.")
        get_engine = None

import pymysql
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CandleData:
    """Data structure for candlestick information"""
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    range_value: float = None


class CandleDataService:
    """Enhanced service for fetching candlestick data from multiple timeframe tables"""
    
    TIMEFRAME_TABLES = {
        'Daily': 'nse_equity_bhavcopy_full',
        'Weekly': 'nse_bhav_weekly', 
        'Monthly': 'nse_bhav_monthly'
    }
    
    TIMEFRAME_COLUMNS = {
        'Daily': {
            'date': 'trade_date',
            'open': 'open_price', 
            'high': 'high_price',
            'low': 'low_price',
            'close': 'close_price',
            'volume': 'ttl_trd_qnty'
        },
        'Weekly': {
            'date': 'trade_date',
            'open': 'open', 
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        },
        'Monthly': {
            'date': 'trade_date',
            'open': 'open', 
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }
    }
    
    def __init__(self):
        if get_engine:
            self.engine = get_engine()
        else:
            self.engine = self._create_fallback_engine()
    
    def _create_fallback_engine(self):
        """Create database engine with proper URL encoding"""
        try:
            from urllib.parse import quote_plus
            
            host = os.getenv('MYSQL_HOST', 'localhost')
            port = os.getenv('MYSQL_PORT', 3306)
            user = os.getenv('MYSQL_USER', 'root')
            password = os.getenv('MYSQL_PASSWORD', '')
            database = os.getenv('MYSQL_DB', 'marketdata')
            
            # URL encode the password to handle special characters
            encoded_password = quote_plus(password) if password else ''
            
            connection_string = (
                f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/"
                f"{database}?charset=utf8mb4"
            )
            
            engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Database engine created successfully")
            return engine
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    
    def get_available_symbols(self, timeframe='Monthly') -> List[str]:
        """Get list of available symbols in the database for the given timeframe"""
        try:
            # Primary table based on timeframe
            primary_table = self.TIMEFRAME_TABLES.get(timeframe, 'nse_bhav_monthly')
            
            tables_to_check = [
                primary_table,
                'momentum_analysis',
                'nse_equity_bhavcopy_full'
            ]
            
            symbols = set()
            
            with self.engine.connect() as conn:
                for table in tables_to_check:
                    try:
                        query = f"SELECT DISTINCT symbol FROM {table} WHERE symbol IS NOT NULL"
                        result = conn.execute(text(query))
                        table_symbols = [row[0] for row in result]
                        symbols.update(table_symbols)
                        logger.info(f"Found {len(table_symbols)} symbols in {table}")
                    except Exception as e:
                        logger.warning(f"Could not fetch symbols from {table}: {e}")
                        continue
            
            symbols_list = sorted(list(symbols))
            logger.info(f"Total unique symbols found: {len(symbols_list)}")
            return symbols_list
            
        except Exception as e:
            logger.error(f"Error fetching available symbols: {e}")
            return []
    
    def check_data_freshness(self, timeframe='Monthly'):
        """Check data freshness for the given timeframe"""
        try:
            table = self.TIMEFRAME_TABLES.get(timeframe, 'nse_bhav_monthly')
            date_column = self.TIMEFRAME_COLUMNS[timeframe]['date']
            
            query = f"""
                SELECT 
                    MAX({date_column}) as latest_date,
                    COUNT(DISTINCT symbol) as symbol_count,
                    COUNT(*) as total_records
                FROM {table}
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                row = result.fetchone()
                
                if row and row[0]:
                    latest_date = row[0]
                    symbol_count = row[1] or 0
                    total_records = row[2] or 0
                    
                    # Calculate days behind (simplified)
                    from datetime import date
                    today = date.today()
                    days_behind = (today - latest_date).days if latest_date else 999
                    
                    return {
                        'timeframe': timeframe,
                        'table': table,
                        'latest_date': latest_date,
                        'symbol_count': symbol_count,
                        'total_records': total_records,
                        'days_behind': days_behind,
                        'status': '✅ Current' if days_behind <= 7 else '⚠️ Behind' if days_behind <= 30 else '❌ Stale'
                    }
                else:
                    return {
                        'timeframe': timeframe,
                        'table': table,
                        'latest_date': None,
                        'symbol_count': 0,
                        'total_records': 0,
                        'days_behind': 999,
                        'status': '❌ No Data'
                    }
                    
        except Exception as e:
            logger.error(f"Error checking data freshness for {timeframe}: {e}")
            return {
                'timeframe': timeframe,
                'table': 'unknown',
                'latest_date': None,
                'symbol_count': 0,
                'total_records': 0,
                'days_behind': 999,
                'status': '❌ Error'
            }
    
    def get_candle_data(self, symbol: str, start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None, timeframe='Monthly') -> pd.DataFrame:
        """Get candle data for a symbol in the specified timeframe"""
        try:
            table = self.TIMEFRAME_TABLES.get(timeframe, 'nse_bhav_monthly')
            columns = self.TIMEFRAME_COLUMNS[timeframe]
            
            # Build query based on timeframe
            if timeframe == 'Daily':
                query = f"""
                SELECT {columns['date']} as date, {columns['open']} as open, 
                       {columns['high']} as high, {columns['low']} as low, 
                       {columns['close']} as close, {columns['volume']} as volume
                FROM {table} 
                WHERE symbol = :symbol AND series = 'EQ'
                """
            else:
                query = f"""
                SELECT {columns['date']} as date, {columns['open']} as open, 
                       {columns['high']} as high, {columns['low']} as low, 
                       {columns['close']} as close, {columns['volume']} as volume
                FROM {table} 
                WHERE symbol = :symbol
                """
            
            params = {'symbol': symbol}
            
            if start_date:
                query += f" AND {columns['date']} >= :start_date"
                params['start_date'] = start_date.date()
            
            if end_date:
                query += f" AND {columns['date']} <= :end_date"
                params['end_date'] = end_date.date()
            
            query += f" ORDER BY {columns['date']} ASC"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                rows = result.fetchall()
                
                if rows:
                    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                    df['range'] = df['high'] - df['low']
                    df['date'] = pd.to_datetime(df['date'])
                    logger.info(f"Found {len(df)} {timeframe.lower()} candles for {symbol} from {table}")
                    return df
                else:
                    logger.warning(f"No {timeframe.lower()} data found for {symbol} in {table}")
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Error getting {timeframe.lower()} candles for {symbol}: {e}")
            return pd.DataFrame()
    
    # Backward compatibility
    def get_monthly_candles(self, symbol: str, start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> List[CandleData]:
        """Get monthly candle data for a symbol (backward compatibility)"""
        df = self.get_candle_data(symbol, start_date, end_date, 'Monthly')
        
        candles = []
        for _, row in df.iterrows():
            candles.append(CandleData(
                symbol=symbol,
                date=row['date'],
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']) if row['volume'] else 0,
                range_value=float(row['range'])
            ))
        
        return candles


class NarrowRangeDetector:
    """Detector for narrow range candlestick patterns"""
    
    def detect_narrow_range(self, df: pd.DataFrame, pattern_type: str = 'NR4') -> List[Dict]:
        """Detect narrow range patterns in the data"""
        if df.empty or len(df) < 4:
            return []
        
        # Get the period from pattern type (e.g., 'NR4' -> 4)
        try:
            period = int(pattern_type[2:])  # Extract number after 'NR'
        except:
            logger.error(f"Invalid pattern type: {pattern_type}")
            return []
        
        if len(df) < period:
            return []
        
        results = []
        
        # Calculate rolling minimum range for the specified period
        for i in range(period - 1, len(df)):
            current_range = df.iloc[i]['range']
            
            # Get the range values for the period (including current)
            period_ranges = df.iloc[i - period + 1:i + 1]['range'].values
            
            # Check if current range is the smallest in the period
            if current_range == min(period_ranges):
                # Calculate rank (1 = smallest)
                rank = sorted(period_ranges).index(current_range) + 1
                
                results.append({
                    'date': df.iloc[i]['date'],
                    'range': current_range,
                    'rank': rank,
                    'pattern_type': pattern_type
                })
        
        logger.info(f"Detected {len(results)} {pattern_type} patterns")
        return results


class PatternStorageService:
    """Service for storing detected patterns in database"""
    
    def __init__(self):
        if get_engine:
            self.engine = get_engine()
        else:
            from services.candlestick_patterns import CandleDataService
            temp_service = CandleDataService()
            self.engine = temp_service.engine
    
    def store_patterns(self, patterns: List[Dict]) -> int:
        """Store detected patterns in database"""
        if not patterns:
            return 0
        
        try:
            # Prepare data for insertion
            insert_data = []
            for pattern in patterns:
                insert_data.append({
                    'symbol': pattern['symbol'],
                    'pattern_date': pattern['detection_date'],
                    'pattern_type': pattern['pattern_type'],
                    'timeframe': pattern.get('timeframe', 'MONTHLY').upper(),
                    'current_range': pattern['range_value'],
                    'range_rank': pattern['period_rank'],
                    'comparison_periods': int(pattern['pattern_type'][2:]),  # Extract number from NR4, NR7, etc.
                    'detected_at': datetime.now()
                })
            
            # Insert into database
            query = """
                INSERT INTO candlestick_patterns 
                (symbol, pattern_date, pattern_type, timeframe, current_range, range_rank, 
                 comparison_periods, detected_at)
                VALUES (:symbol, :pattern_date, :pattern_type, :timeframe, 
                        :current_range, :range_rank, :comparison_periods, :detected_at)
                ON DUPLICATE KEY UPDATE
                current_range = VALUES(current_range),
                range_rank = VALUES(range_rank),
                updated_at = NOW()
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), insert_data)
                conn.commit()
                
                stored_count = len(insert_data)
                logger.info(f"Stored {stored_count} patterns in database")
                return stored_count
                
        except Exception as e:
            logger.error(f"Error storing patterns: {e}")
            return 0


class PatternScannerService:
    """Enhanced high-performance service for scanning symbols across timeframes"""
    
    def __init__(self, progress_callback=None):
        self.data_service = CandleDataService()
        self.detector = NarrowRangeDetector()
        self.storage_service = PatternStorageService()
        self.progress_callback = progress_callback
    
    def scan_patterns(self, symbols=None, start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None,
                     pattern_types: List[str] = None,
                     timeframe: str = 'Monthly',
                     batch_size: int = 50,
                     max_workers: int = 4,
                     progress_callback=None) -> List[Dict]:
        """Scan for patterns across symbols in specified timeframe"""
        try:
            if pattern_types is None:
                pattern_types = ['NR4', 'NR7', 'NR13', 'NR21']
            
            # Create job record
            job_id = self._create_job_record(len(symbols or []), pattern_types, timeframe)
            
            if symbols is None:
                symbols = self.data_service.get_available_symbols(timeframe)
            
            # Filter to known good symbols for testing
            good_symbols = [s for s in symbols if any(x in s for x in 
                           ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'SBIN', 'WIPRO', 
                            'BHARTI', 'MARUTI', 'ASIAN', 'TATA'])][:52]
            
            if not good_symbols:
                good_symbols = symbols[:52]  # Take first 52 if no good symbols found
            
            logger.info(f"Starting {timeframe.lower()} pattern scan for {len(good_symbols)} symbols")
            
            # Process in batches
            patterns_found = []
            total_processed = 0
            
            for i in range(0, len(good_symbols), batch_size):
                batch = good_symbols[i:i + batch_size]
                
                # Process batch with threading
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._scan_symbol_patterns,
                            symbol, start_date, end_date, pattern_types, timeframe
                        ): symbol for symbol in batch
                    }
                    
                    for future in as_completed(futures):
                        symbol = futures[future]
                        try:
                            symbol_patterns = future.result()
                            if symbol_patterns:
                                patterns_found.extend(symbol_patterns)
                            total_processed += 1
                            
                            # Update progress
                            if progress_callback:
                                progress = (total_processed / len(good_symbols)) * 100
                                progress_callback(f"Processed {total_processed}/{len(good_symbols)} symbols ({timeframe})", progress)
                                
                        except Exception as e:
                            logger.error(f"Error processing {symbol}: {e}")
                            total_processed += 1
                
                # Update job progress
                self._update_job_progress(job_id, total_processed, len(good_symbols))
            
            # Store patterns in database
            if patterns_found:
                stored_count = self.storage_service.store_patterns(patterns_found)
                logger.info(f"Stored {stored_count} patterns in database")
            
            # Complete job
            self._complete_job(job_id, len(patterns_found))
            
            logger.info(f"Pattern scan completed: {len(good_symbols)} symbols, {len(patterns_found)} patterns found")
            return patterns_found
            
        except Exception as e:
            logger.error(f"Error in pattern scan: {e}")
            return []
    
    def _scan_symbol_patterns(self, symbol: str, start_date: Optional[datetime], 
                             end_date: Optional[datetime], pattern_types: List[str], 
                             timeframe: str = 'Monthly') -> List[Dict]:
        """Scan patterns for a single symbol"""
        try:
            # Get candle data for the specified timeframe
            df = self.data_service.get_candle_data(symbol, start_date, end_date, timeframe)
            
            if df.empty:
                return []
            
            patterns = []
            for pattern_type in pattern_types:
                pattern_results = self.detector.detect_narrow_range(df, pattern_type)
                for result in pattern_results:
                    patterns.append({
                        'symbol': symbol,
                        'pattern_type': pattern_type,
                        'detection_date': result['date'],
                        'range_value': result['range'],
                        'period_rank': result['rank'],
                        'timeframe': timeframe
                    })
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error scanning patterns for {symbol}: {e}")
            return []
    
    def _create_job_record(self, total_symbols: int, pattern_types: List[str], timeframe: str = 'Monthly') -> int:
        """Create a job tracking record"""
        try:
            query = """
                INSERT INTO pattern_detection_jobs 
                (job_name, timeframe, pattern_types, total_symbols, status, started_at) 
                VALUES (:job_name, :timeframe, :pattern_types, :total_symbols, 'RUNNING', NOW())
            """
            
            job_name = f"Pattern Scan - {timeframe} - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import json
            pattern_json = json.dumps(pattern_types)  # Proper JSON formatting
            
            params = {
                'job_name': job_name,
                'timeframe': timeframe.upper(),
                'pattern_types': pattern_json,
                'total_symbols': total_symbols
            }
            
            with self.data_service.engine.connect() as conn:
                result = conn.execute(text(query), params)
                conn.commit()
                
                # Get the job ID
                job_id = result.lastrowid
                logger.info(f"Created job record with ID: {job_id} for {timeframe} timeframe")
                return job_id
                
        except Exception as e:
            logger.error(f"Error creating job record: {e}")
            return None
    
    def _update_job_progress(self, job_id: int, processed: int, total: int):
        """Update job progress"""
        try:
            if job_id is None:
                return
                
            query = """
                UPDATE pattern_detection_jobs 
                SET processed_symbols = :processed
                WHERE id = :job_id
            """
            
            with self.data_service.engine.connect() as conn:
                conn.execute(text(query), {'processed': processed, 'job_id': job_id})
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating job progress: {e}")
    
    def _complete_job(self, job_id: int, patterns_found: int):
        """Mark job as completed"""
        try:
            if job_id is None:
                return
                
            query = """
                UPDATE pattern_detection_jobs 
                SET status = 'COMPLETED', completed_at = NOW(), patterns_detected = :patterns_found
                WHERE id = :job_id
            """
            
            with self.data_service.engine.connect() as conn:
                conn.execute(text(query), {'patterns_found': patterns_found, 'job_id': job_id})
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error completing job: {e}")


# Demo functions for testing
def test_timeframe_data_availability():
    """Test data availability across timeframes"""
    print("🔍 Testing Data Availability Across Timeframes")
    print("=" * 60)
    
    service = CandleDataService()
    
    for timeframe in ['Daily', 'Weekly', 'Monthly']:
        print(f"\n📊 {timeframe} Data Status:")
        freshness = service.check_data_freshness(timeframe)
        
        print(f"   Table: {freshness['table']}")
        print(f"   Status: {freshness['status']}")
        print(f"   Latest Date: {freshness['latest_date']}")
        print(f"   Symbols: {freshness['symbol_count']:,}")
        print(f"   Records: {freshness['total_records']:,}")
        print(f"   Days Behind: {freshness['days_behind']}")
        
        # Test symbol availability
        symbols = service.get_available_symbols(timeframe)
        print(f"   Available Symbols: {len(symbols)}")


def demo_pattern_detection_all_timeframes():
    """Demo pattern detection across all timeframes"""
    print("🕯️ Candlestick Pattern Detection Demo - All Timeframes")
    print("=" * 70)
    
    def progress_callback(message, progress):
        print(f"   📈 {message} ({progress:.1f}%)")
    
    scanner = PatternScannerService(progress_callback=progress_callback)
    
    # Test with a few symbols for each timeframe
    test_symbols = ['RELIANCE', 'TCS', 'HDFC', 'SBIN']
    
    for timeframe in ['Monthly', 'Weekly', 'Daily']:
        print(f"\n🎯 Testing {timeframe} Pattern Detection:")
        print("-" * 40)
        
        patterns = scanner.scan_patterns(
            symbols=test_symbols,
            timeframe=timeframe,
            pattern_types=['NR4', 'NR7'],
            batch_size=2,
            max_workers=2,
            progress_callback=progress_callback
        )
        
        print(f"   ✅ Found {len(patterns)} patterns in {timeframe} timeframe")
        
        if patterns:
            for pattern in patterns[:3]:  # Show first 3
                print(f"      🔍 {pattern['symbol']}: {pattern['pattern_type']} on {pattern['detection_date']}")


if __name__ == "__main__":
    # Run availability test
    test_timeframe_data_availability()
    
    print("\n" + "=" * 70)
    
    # Run pattern detection demo
    demo_pattern_detection_all_timeframes()