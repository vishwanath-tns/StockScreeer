"""
Database service for Yahoo Finance data operations
"""

import mysql.connector
from mysql.connector import Error
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
import logging
import sys
import os

# Add current directory to path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import YFinanceConfig
from models import DailyQuote, SymbolInfo, DownloadLog

# Setup logging
logging.basicConfig(level=YFinanceConfig.LOG_LEVEL)
logger = logging.getLogger(__name__)

class YFinanceDBService:
    """Database service for Yahoo Finance data operations"""
    
    def __init__(self):
        self.config = YFinanceConfig()
        self.db_config = self.config.get_db_config()
    
    def get_connection(self):
        """Get database connection"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            return conn
        except Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def initialize_database(self) -> bool:
        """Initialize database tables if they don't exist"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Read and execute schema file
            schema_path = "database/yfinance_schema.sql"
            try:
                with open(schema_path, 'r') as file:
                    schema_sql = file.read()
                    
                # Execute schema statements
                for statement in schema_sql.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        cursor.execute(statement)
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                return True
                
            except FileNotFoundError:
                logger.warning(f"Schema file not found at {schema_path}, skipping initialization")
                return False
            
        except Error as e:
            logger.error(f"Error initializing database: {e}")
            return False
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    def insert_quotes(self, quotes: List[DailyQuote]) -> Tuple[int, int]:
        """
        Insert daily quotes into database
        
        Returns:
            Tuple of (inserted_count, updated_count)
        """
        if not quotes:
            return 0, 0
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            insert_query = """
            INSERT INTO yfinance_daily_quotes 
            (symbol, date, open, high, low, close, volume, adj_close, timeframe, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume),
            adj_close = VALUES(adj_close),
            updated_at = CURRENT_TIMESTAMP
            """
            
            # Prepare data for insertion
            data = []
            for quote in quotes:
                data.append((
                    quote.symbol,
                    quote.date,
                    quote.open,
                    quote.high,
                    quote.low,
                    quote.close,
                    quote.volume,
                    quote.adj_close,
                    quote.timeframe,
                    quote.source
                ))
            
            # Get initial count
            cursor.execute(
                "SELECT COUNT(*) FROM yfinance_daily_quotes WHERE symbol = %s AND date BETWEEN %s AND %s",
                (quotes[0].symbol, min(q.date for q in quotes), max(q.date for q in quotes))
            )
            initial_count = cursor.fetchone()[0]
            
            # Execute bulk insert
            cursor.executemany(insert_query, data)
            affected_rows = cursor.rowcount
            
            # Get final count
            cursor.execute(
                "SELECT COUNT(*) FROM yfinance_daily_quotes WHERE symbol = %s AND date BETWEEN %s AND %s",
                (quotes[0].symbol, min(q.date for q in quotes), max(q.date for q in quotes))
            )
            final_count = cursor.fetchone()[0]
            
            conn.commit()
            
            inserted = final_count - initial_count
            updated = len(quotes) - inserted
            
            logger.info(f"Database operation completed: {inserted} inserted, {updated} updated")
            return inserted, updated
            
        except Error as e:
            logger.error(f"Error inserting quotes: {e}")
            if 'conn' in locals():
                conn.rollback()
            raise
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_quotes(self, symbol: str, start_date: date, end_date: date) -> List[DailyQuote]:
        """Get quotes for a symbol within date range"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
            SELECT symbol, date, open, high, low, close, volume, adj_close, timeframe, source
            FROM yfinance_daily_quotes 
            WHERE symbol = %s AND date BETWEEN %s AND %s
            ORDER BY date
            """
            
            cursor.execute(query, (symbol, start_date, end_date))
            rows = cursor.fetchall()
            
            quotes = []
            for row in rows:
                quote = DailyQuote(
                    symbol=row['symbol'],
                    date=row['date'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    adj_close=row['adj_close'],
                    timeframe=row['timeframe'],
                    source=row['source']
                )
                quotes.append(quote)
            
            return quotes
            
        except Error as e:
            logger.error(f"Error getting quotes: {e}")
            return []
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_date_range(self, symbol: str) -> Tuple[Optional[date], Optional[date]]:
        """Get the date range for available data for a symbol"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM yfinance_daily_quotes 
            WHERE symbol = %s
            """
            
            cursor.execute(query, (symbol,))
            result = cursor.fetchone()
            
            if result and result[0]:
                return result[0], result[1]
            
            return None, None
            
        except Error as e:
            logger.error(f"Error getting date range: {e}")
            return None, None
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_record_count(self, symbol: str = None) -> int:
        """Get total record count, optionally filtered by symbol"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if symbol:
                query = "SELECT COUNT(*) FROM yfinance_daily_quotes WHERE symbol = %s"
                cursor.execute(query, (symbol,))
            else:
                query = "SELECT COUNT(*) FROM yfinance_daily_quotes"
                cursor.execute(query)
            
            result = cursor.fetchone()
            return result[0] if result else 0
            
        except Error as e:
            logger.error(f"Error getting record count: {e}")
            return 0
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    def log_download(self, download_log: DownloadLog) -> int:
        """Log download activity"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            insert_query = """
            INSERT INTO yfinance_download_log 
            (symbol, start_date, end_date, timeframe, records_downloaded, records_updated, 
             status, error_message, download_duration_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            data = (
                download_log.symbol,
                download_log.start_date,
                download_log.end_date,
                download_log.timeframe,
                download_log.records_downloaded,
                download_log.records_updated,
                download_log.status,
                download_log.error_message,
                download_log.download_duration_ms
            )
            
            cursor.execute(insert_query, data)
            log_id = cursor.lastrowid
            
            # Update completion time if status is completed
            if download_log.status in ['COMPLETED', 'FAILED']:
                cursor.execute(
                    "UPDATE yfinance_download_log SET completed_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (log_id,)
                )
            
            conn.commit()
            return log_id
            
        except Error as e:
            logger.error(f"Error logging download: {e}")
            return 0
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get database status information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get table statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_quotes,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM yfinance_daily_quotes
            """)
            
            quotes_stats = cursor.fetchone()
            
            # Get symbol breakdown
            cursor.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM yfinance_daily_quotes 
                GROUP BY symbol
                ORDER BY count DESC
            """)
            
            symbol_breakdown = cursor.fetchall()
            
            return {
                'connection_status': 'Connected',
                'total_quotes': quotes_stats['total_quotes'],
                'unique_symbols': quotes_stats['unique_symbols'],
                'earliest_date': quotes_stats['earliest_date'],
                'latest_date': quotes_stats['latest_date'],
                'symbol_breakdown': symbol_breakdown
            }
            
        except Error as e:
            logger.error(f"Error getting database status: {e}")
            return {
                'connection_status': f'Error: {e}',
                'total_quotes': 0,
                'unique_symbols': 0,
                'earliest_date': None,
                'latest_date': None,
                'symbol_breakdown': []
            }
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()