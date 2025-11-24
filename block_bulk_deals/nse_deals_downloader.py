"""
NSE Block & Bulk Deals Downloader with Anti-Bot Protection

This module downloads Block and Bulk Deals data from NSE India website
with proper anti-bot measures including:
- Rotating User-Agents
- Session management
- Rate limiting
- Cookie handling
- Referer headers
"""

import os
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NSEDealsDownloader:
    """
    Downloads Block and Bulk Deals from NSE with anti-bot protection
    """
    
    BASE_URL = "https://www.nseindia.com"
    BLOCK_DEALS_API = "/api/block-deal"
    BULK_DEALS_API = "/api/bulk-deal"
    
    # Rotating User Agents to avoid detection
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, rate_limit: float = 2.0):
        """
        Initialize the downloader with rate limiting
        
        Args:
            rate_limit: Minimum seconds to wait between requests (default: 2.0)
        """
        self.rate_limit = rate_limit
        self.session = None
        self.last_request_time = 0
        self._init_session()
        
    def _init_session(self):
        """Initialize requests session with proper headers"""
        self.session = requests.Session()
        self._update_headers()
        
    def _update_headers(self):
        """Update session headers with random User-Agent"""
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.nseindia.com/market-data/bulk-block-deals',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        
    def _rate_limit_wait(self):
        """Wait to respect rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            time.sleep(wait_time)
        self.last_request_time = time.time()
        
    def _get_cookies(self) -> bool:
        """
        Get fresh cookies from NSE homepage
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._rate_limit_wait()
            response = self.session.get(
                self.BASE_URL,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return False
            
    def download_block_deals(self, date: datetime) -> Optional[pd.DataFrame]:
        """
        Download block deals for a specific date
        
        Args:
            date: Trading date
            
        Returns:
            DataFrame with block deals or None if failed
        """
        return self._download_deals(date, "BLOCK")
        
    def download_bulk_deals(self, date: datetime) -> Optional[pd.DataFrame]:
        """
        Download bulk deals for a specific date
        
        Args:
            date: Trading date
            
        Returns:
            DataFrame with bulk deals or None if failed
        """
        return self._download_deals(date, "BULK")
        
    def _download_deals(self, date: datetime, deal_type: str) -> Optional[pd.DataFrame]:
        """
        Download deals from NSE API
        
        Args:
            date: Trading date
            deal_type: "BLOCK" or "BULK"
            
        Returns:
            DataFrame with deals or None if failed
        """
        try:
            # Refresh cookies periodically
            if random.random() < 0.1:  # 10% chance to refresh
                self._get_cookies()
                
            # Format date for API
            date_str = date.strftime("%d-%m-%Y")
            
            # Select API endpoint
            api_url = self.BASE_URL + (
                self.BLOCK_DEALS_API if deal_type == "BLOCK" else self.BULK_DEALS_API
            )
            
            # Add query parameters
            params = {
                'from': date_str,
                'to': date_str
            }
            
            # Rate limit
            self._rate_limit_wait()
            
            # Update headers occasionally
            if random.random() < 0.2:  # 20% chance
                self._update_headers()
            
            # Make request
            response = self.session.get(
                api_url,
                params=params,
                timeout=15
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to download {deal_type} deals for {date_str}: HTTP {response.status_code}")
                return None
                
            # Parse JSON response
            data = response.json()
            
            # Check if data exists
            if not data or len(data) == 0:
                logger.info(f"No {deal_type} deals for {date_str}")
                return pd.DataFrame()  # Empty but valid
            
            # Handle different response formats
            if isinstance(data, dict):
                # Response might be wrapped in a dict
                if 'data' in data:
                    data = data['data']
                elif len(data) > 0:
                    # Single dict - convert to list
                    data = [data]
                else:
                    logger.info(f"No {deal_type} deals for {date_str}")
                    return pd.DataFrame()
            
            # Convert to DataFrame
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
            else:
                logger.info(f"No {deal_type} deals for {date_str}")
                return pd.DataFrame()
            
            # Add trade date
            df['trade_date'] = date
            
            # Standardize column names
            df = self._standardize_columns(df, deal_type)
            
            logger.info(f"Downloaded {len(df)} {deal_type} deals for {date_str}")
            return df
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout downloading {deal_type} deals for {date.strftime('%d-%m-%Y')}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error downloading {deal_type} deals: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {deal_type} deals for {date.strftime('%d-%m-%Y')}: {e}")
            return None
            
    def _standardize_columns(self, df: pd.DataFrame, deal_type: str) -> pd.DataFrame:
        """
        Standardize column names from NSE API response
        
        Args:
            df: Raw DataFrame from API
            deal_type: "BLOCK" or "BULK"
            
        Returns:
            DataFrame with standardized columns
        """
        # Column mapping (NSE API → Our Schema)
        column_map = {
            'symbol': 'symbol',
            'securityName': 'security_name',
            'companyName': 'security_name',
            'clientName': 'client_name',
            'buySell': 'deal_type',
            'dealType': 'deal_type',
            'quantityTraded': 'quantity',
            'quantity': 'quantity',
            'tradePrice': 'trade_price',
            'pricePerShare': 'trade_price',
            'price': 'trade_price',
            'remarks': 'remarks',
            'remark': 'remarks'
        }
        
        # Rename columns
        df_renamed = df.copy()
        for old_col, new_col in column_map.items():
            if old_col in df_renamed.columns:
                df_renamed.rename(columns={old_col: new_col}, inplace=True)
                
        # Ensure required columns exist
        required_cols = ['symbol', 'security_name', 'client_name', 'deal_type', 
                        'quantity', 'trade_price', 'trade_date']
        
        for col in required_cols:
            if col not in df_renamed.columns:
                df_renamed[col] = None
                
        # Add remarks if missing
        if 'remarks' not in df_renamed.columns:
            df_renamed['remarks'] = None
            
        # Clean deal_type
        if 'deal_type' in df_renamed.columns:
            df_renamed['deal_type'] = df_renamed['deal_type'].str.upper().str.strip()
            
        # Select final columns
        final_cols = ['trade_date', 'symbol', 'security_name', 'client_name', 
                     'deal_type', 'quantity', 'trade_price', 'remarks']
        
        return df_renamed[final_cols]
        
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()


class NSEDealsDatabase:
    """
    Database operations for Block & Bulk Deals
    """
    
    def __init__(self):
        """Initialize database connection"""
        self.engine = self._create_engine()
        
    def _create_engine(self):
        """Create SQLAlchemy engine with connection pooling"""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', 'rajat123'))
        connection_string = (
            f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
            f"{password}@"
            f"{os.getenv('MYSQL_HOST', 'localhost')}:"
            f"{os.getenv('MYSQL_PORT', '3306')}/"
            f"{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4"
        )
        
        return create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
    def save_deals(self, df: pd.DataFrame, deal_type: str) -> Tuple[int, int]:
        """
        Save deals to database with upsert logic
        
        Args:
            df: DataFrame with deals
            deal_type: "BLOCK" or "BULK"
            
        Returns:
            Tuple of (new_records, updated_records)
        """
        if df is None or df.empty:
            return 0, 0
            
        table_name = "nse_block_deals" if deal_type == "BLOCK" else "nse_bulk_deals"
        
        with self.engine.begin() as conn:
            # Create temporary table
            conn.execute(text(f"""
                CREATE TEMPORARY TABLE tmp_deals LIKE {table_name}
            """))
            
            # Insert into temporary table
            df.to_sql(
                name='tmp_deals',
                con=conn.engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=1000
            )
            
            # Upsert into main table
            result = conn.execute(text(f"""
                INSERT INTO {table_name} 
                (trade_date, symbol, security_name, client_name, deal_type, 
                 quantity, trade_price, remarks)
                SELECT trade_date, symbol, security_name, client_name, deal_type, 
                       quantity, trade_price, remarks
                FROM tmp_deals
                ON DUPLICATE KEY UPDATE
                    security_name = VALUES(security_name),
                    remarks = VALUES(remarks),
                    updated_at = CURRENT_TIMESTAMP
            """))
            
            # Get counts
            new_records = result.rowcount
            
            # Drop temporary table
            conn.execute(text("DROP TEMPORARY TABLE tmp_deals"))
            
        return new_records, 0
        
    def log_import(self, trade_date: datetime, deal_category: str, 
                   records: int, status: str = "SUCCESS", error: str = None):
        """
        Log import activity
        
        Args:
            trade_date: Trading date
            deal_category: "BLOCK" or "BULK"
            records: Number of records imported
            status: Import status
            error: Error message if failed
        """
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO block_bulk_deals_import_log
                (trade_date, deal_category, records_imported, import_status, error_message)
                VALUES (:trade_date, :category, :records, :status, :error)
                ON DUPLICATE KEY UPDATE
                    records_imported = VALUES(records_imported),
                    import_status = VALUES(import_status),
                    error_message = VALUES(error_message),
                    imported_at = CURRENT_TIMESTAMP
            """), {
                'trade_date': trade_date,
                'category': deal_category,
                'records': records,
                'status': status,
                'error': error
            })
            
    def get_imported_dates(self, deal_category: str) -> set:
        """
        Get set of dates already imported
        
        Args:
            deal_category: "BLOCK" or "BULK"
            
        Returns:
            Set of datetime objects
        """
        table_name = "nse_block_deals" if deal_category == "BLOCK" else "nse_bulk_deals"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT DISTINCT trade_date 
                FROM {table_name}
                ORDER BY trade_date
            """))
            
            return {row[0] for row in result}
            
    def get_import_stats(self) -> Dict:
        """
        Get import statistics
        
        Returns:
            Dictionary with stats
        """
        with self.engine.connect() as conn:
            # Block deals stats
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_deals,
                    MIN(trade_date) as earliest_date,
                    MAX(trade_date) as latest_date,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(DISTINCT client_name) as unique_clients
                FROM nse_block_deals
            """))
            block_stats = dict(zip(result.keys(), result.fetchone()))
            
            # Bulk deals stats
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_deals,
                    MIN(trade_date) as earliest_date,
                    MAX(trade_date) as latest_date,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(DISTINCT client_name) as unique_clients
                FROM nse_bulk_deals
            """))
            bulk_stats = dict(zip(result.keys(), result.fetchone()))
            
            return {
                'block_deals': block_stats,
                'bulk_deals': bulk_stats
            }


def get_trading_dates(start_date: datetime, end_date: datetime) -> List[datetime]:
    """
    Get list of potential trading dates (excluding Saturdays and Sundays)
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        List of datetime objects (weekdays only)
    """
    dates = []
    current = start_date
    
    while current <= end_date:
        # Exclude weekends (Saturday=5, Sunday=6)
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
        
    return dates
