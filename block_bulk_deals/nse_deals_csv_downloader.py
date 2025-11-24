"""
NSE Block & Bulk Deals CSV Downloader

Downloads Block and Bulk Deals from NSE's CSV reports with anti-bot protection.
More reliable than API endpoints.
"""

import os
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
from io import StringIO
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


class NSEDealsCSVDownloader:
    """
    Downloads Block and Bulk Deals CSV files from NSE with anti-bot protection
    """
    
    BASE_URL = "https://www.nseindia.com"
    
    # CSV download URLs (based on NSE website structure)
    BLOCK_DEALS_CSV = "/api/reports?archives=%5B%7B%22name%22:%22CM%20-%20Bulk%20and%20block%20deals%22,%22type%22:%22block-deals%22,%22category%22:%22capital-market%22,%22section%22:%22equities%22%7D%5D&date={date}&type=block-deals&mode=single"
    BULK_DEALS_CSV = "/api/reports?archives=%5B%7B%22name%22:%22CM%20-%20Bulk%20and%20block%20deals%22,%22type%22:%22bulk-deals%22,%22category%22:%22capital-market%22,%22section%22:%22equities%22%7D%5D&date={date}&type=bulk-deals&mode=single"
    
    # Rotating User Agents
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.nseindia.com/all-reports',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
    def _rate_limit_wait(self):
        """Wait to respect rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            time.sleep(wait_time)
        self.last_request_time = time.time()
        
    def _get_cookies(self) -> bool:
        """Get fresh cookies from NSE homepage"""
        try:
            self._rate_limit_wait()
            response = self.session.get(self.BASE_URL, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return False
            
    def download_block_deals(self, date: datetime) -> Optional[pd.DataFrame]:
        """Download block deals CSV for a specific date"""
        return self._download_csv(date, "BLOCK")
        
    def download_bulk_deals(self, date: datetime) -> Optional[pd.DataFrame]:
        """Download bulk deals CSV for a specific date"""
        return self._download_csv(date, "BULK")
        
    def _download_csv(self, date: datetime, deal_type: str) -> Optional[pd.DataFrame]:
        """
        Download deals CSV from NSE
        
        Args:
            date: Trading date
            deal_type: "BLOCK" or "BULK"
            
        Returns:
            DataFrame with deals or None if failed
        """
        try:
            # Refresh cookies periodically
            if random.random() < 0.1:  # 10% chance
                self._get_cookies()
                
            # Format date for URL (DD-MMM-YYYY format)
            date_str = date.strftime("%d-%b-%Y").upper()
            
            # Select URL pattern
            if deal_type == "BLOCK":
                # Try direct CSV download URL
                csv_url = f"{self.BASE_URL}/archives/equities/mkt/block_deal_{date.strftime('%d%m%Y')}.csv"
            else:
                csv_url = f"{self.BASE_URL}/archives/equities/mkt/bulk_deal_{date.strftime('%d%m%Y')}.csv"
            
            # Rate limit
            self._rate_limit_wait()
            
            # Update headers occasionally
            if random.random() < 0.2:  # 20% chance
                self._update_headers()
            
            # Make request
            response = self.session.get(csv_url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Failed to download {deal_type} deals for {date_str}: HTTP {response.status_code}")
                return None
            
            # Check if response is actually CSV
            content_type = response.headers.get('Content-Type', '')
            if 'text/csv' not in content_type and 'application/octet-stream' not in content_type:
                logger.warning(f"Invalid content type for {deal_type} deals: {content_type}")
                return None
                
            # Parse CSV
            try:
                df = pd.read_csv(StringIO(response.text))
            except pd.errors.EmptyDataError:
                logger.info(f"No {deal_type} deals for {date_str} (empty CSV)")
                return pd.DataFrame()
            except Exception as e:
                logger.error(f"Error parsing CSV for {deal_type} deals: {e}")
                return None
            
            # Check if empty
            if df.empty:
                logger.info(f"No {deal_type} deals for {date_str}")
                return pd.DataFrame()
            
            # Add trade date
            df['trade_date'] = date
            
            # Standardize column names
            df = self._standardize_columns(df)
            
            logger.info(f"Downloaded {len(df)} {deal_type} deals for {date_str}")
            return df
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout downloading {deal_type} deals for {date.strftime('%d-%b-%Y')}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error downloading {deal_type} deals: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {deal_type} deals for {date.strftime('%d-%b-%Y')}: {e}")
            return None
            
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names from NSE CSV
        
        CSV columns (from your samples):
        - Date
        - Symbol
        - Security Name
        - Client Name
        - Buy/Sell
        - Quantity Traded
        - Trade Price / Wght. Avg. Price
        - Remarks (bulk deals only)
        """
        # Column mapping (NSE CSV → Our Schema)
        column_map = {
            'Date': 'trade_date',
            'Symbol': 'symbol',
            'Security Name': 'security_name',
            'Client Name': 'client_name',
            'Buy/Sell': 'deal_type',
            'Quantity Traded': 'quantity',
            'Trade Price / Wght. Avg. Price': 'trade_price',
            'Remarks': 'remarks'
        }
        
        # Rename columns
        df_renamed = df.copy()
        for old_col, new_col in column_map.items():
            if old_col in df_renamed.columns:
                df_renamed.rename(columns={old_col: new_col}, inplace=True)
        
        # Ensure required columns exist
        required_cols = ['trade_date', 'symbol', 'security_name', 'client_name', 
                        'deal_type', 'quantity', 'trade_price']
        
        for col in required_cols:
            if col not in df_renamed.columns:
                df_renamed[col] = None
        
        # Add remarks if missing
        if 'remarks' not in df_renamed.columns:
            df_renamed['remarks'] = None
        
        # Clean deal_type (BUY/SELL)
        if 'deal_type' in df_renamed.columns:
            df_renamed['deal_type'] = df_renamed['deal_type'].str.upper().str.strip()
        
        # Clean numeric columns
        if 'quantity' in df_renamed.columns:
            df_renamed['quantity'] = pd.to_numeric(df_renamed['quantity'], errors='coerce')
        
        if 'trade_price' in df_renamed.columns:
            df_renamed['trade_price'] = pd.to_numeric(df_renamed['trade_price'], errors='coerce')
        
        # Select final columns
        final_cols = ['trade_date', 'symbol', 'security_name', 'client_name', 
                     'deal_type', 'quantity', 'trade_price', 'remarks']
        
        return df_renamed[final_cols]
        
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()


class NSEDealsDatabase:
    """Database operations for Block & Bulk Deals"""
    
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
        
        # Clean the dataframe - remove rows with null required fields
        df_clean = df.dropna(subset=['symbol', 'trade_date', 'client_name', 'deal_type'])
        
        if df_clean.empty:
            return 0, 0
        
        # Direct insert approach - simpler and more reliable
        inserted = 0
        
        with self.engine.begin() as conn:
            for _, row in df_clean.iterrows():
                try:
                    conn.execute(text(f"""
                        INSERT INTO {table_name}
                        (trade_date, symbol, security_name, client_name, deal_type,
                         quantity, trade_price, remarks)
                        VALUES
                        (:trade_date, :symbol, :security_name, :client_name, :deal_type,
                         :quantity, :trade_price, :remarks)
                        ON DUPLICATE KEY UPDATE
                            security_name = VALUES(security_name),
                            remarks = VALUES(remarks),
                            updated_at = CURRENT_TIMESTAMP
                    """), {
                        'trade_date': row['trade_date'],
                        'symbol': row['symbol'],
                        'security_name': row['security_name'],
                        'client_name': row['client_name'],
                        'deal_type': row['deal_type'],
                        'quantity': float(row['quantity']) if pd.notna(row['quantity']) else None,
                        'trade_price': float(row['trade_price']) if pd.notna(row['trade_price']) else None,
                        'remarks': row['remarks'] if pd.notna(row['remarks']) else None
                    })
                    inserted += 1
                except Exception as e:
                    # Print first few errors for debugging
                    if inserted < 3:
                        print(f"      ⚠️  Insert error: {e}")
                    pass
        
        return inserted, 0
        
    def log_import(self, trade_date: datetime, deal_category: str, 
                   records: int, status: str = "SUCCESS", error: str = None):
        """Log import activity"""
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
        """Get set of dates already imported"""
        table_name = "nse_block_deals" if deal_category == "BLOCK" else "nse_bulk_deals"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT DISTINCT trade_date 
                FROM {table_name}
                ORDER BY trade_date
            """))
            
            return {row[0] for row in result}
            
    def get_import_stats(self):
        """Get import statistics"""
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


def get_trading_dates(start_date: datetime, end_date: datetime):
    """Get list of potential trading dates (excluding weekends)"""
    dates = []
    current = start_date
    
    while current <= end_date:
        # Exclude weekends
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
        
    return dates
