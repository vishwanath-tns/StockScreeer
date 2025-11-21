#!/usr/bin/env python3
"""
Bulk NSE Stock Data Downloader using Symbol Mappings
Downloads data for all verified NSE stocks from Yahoo Finance
"""

import sys
import os
import mysql.connector
from mysql.connector import Error
import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
import time
import logging
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from yahoo_client import YahooFinanceClient
from db_service import YFinanceDBService

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BulkStockDataDownloader:
    """Bulk downloader for NSE stocks using verified symbol mappings"""
    
    def __init__(self):
        self.yahoo_client = YahooFinanceClient()
        self.db_service = YFinanceDBService()
        self.download_lock = threading.Lock()
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            return mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database='marketdata',
                charset='utf8mb4'
            )
        except Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def get_verified_mappings(self, limit: int = None) -> list:
        """Get list of verified symbol mappings"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
                SELECT nse_symbol, yahoo_symbol, company_name, sector, market_cap_category
                FROM nse_yahoo_symbol_map 
                WHERE is_verified = TRUE AND is_active = TRUE
                ORDER BY market_cap_category, sector, nse_symbol
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql)
            mappings = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return mappings
            
        except Exception as e:
            logger.error(f"Error getting verified mappings: {e}")
            return []
    
    def download_single_stock_data(self, mapping: dict, start_date: date, end_date: date, interval: str = "1d") -> dict:
        """Download data for a single stock"""
        result = {
            'nse_symbol': mapping['nse_symbol'],
            'yahoo_symbol': mapping['yahoo_symbol'],
            'status': 'FAILED',
            'records_downloaded': 0,
            'error_message': None,
            'download_duration': 0
        }
        
        start_time = time.time()
        
        try:
            # Download data from Yahoo Finance
            ticker = yf.Ticker(mapping['yahoo_symbol'])
            data = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if not data.empty:
                # Prepare data for database
                data_records = []
                for trade_date, row in data.iterrows():
                    if pd.notna(row['Close']) and row['Close'] > 0:
                        data_records.append({
                            'symbol': mapping['yahoo_symbol'],
                            'trade_date': trade_date.date(),
                            'open_price': float(row['Open']) if pd.notna(row['Open']) else None,
                            'high_price': float(row['High']) if pd.notna(row['High']) else None,
                            'low_price': float(row['Low']) if pd.notna(row['Low']) else None,
                            'close_price': float(row['Close']),
                            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                            'adj_close': float(row['Close'])  # NSE data: use Close as adj_close
                        })
                
                # Store in database
                if data_records:
                    # Convert to DailyQuote objects
                    from models import DailyQuote
                    quote_objects = []
                    
                    for record in data_records:
                        quote = DailyQuote(
                            symbol=record['symbol'],
                            date=record['trade_date'],
                            open=record['open_price'],
                            high=record['high_price'],
                            low=record['low_price'],
                            close=record['close_price'],
                            volume=record['volume'],
                            adj_close=record['adj_close'],
                            timeframe='1d',
                            source='yahoo'
                        )
                        quote_objects.append(quote)
                    
                    with self.download_lock:
                        inserted, updated = self.db_service.insert_quotes(quote_objects)
                        stored_count = inserted + updated
                    
                    result['status'] = 'SUCCESS'
                    result['records_downloaded'] = stored_count
                else:
                    result['status'] = 'NO_VALID_DATA'
                    result['error_message'] = 'No valid price data found'
            else:
                result['status'] = 'NO_DATA'
                result['error_message'] = 'No data returned from Yahoo Finance'
                
        except Exception as e:
            result['status'] = 'FAILED'
            result['error_message'] = str(e)
        
        result['download_duration'] = time.time() - start_time
        return result
    
    def log_download_results(self, results: list):
        """Log download results to database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Create bulk download log table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bulk_download_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    download_session_id VARCHAR(50),
                    nse_symbol VARCHAR(20),
                    yahoo_symbol VARCHAR(30),
                    download_status ENUM('SUCCESS', 'FAILED', 'NO_DATA', 'NO_VALID_DATA'),
                    records_downloaded INT DEFAULT 0,
                    error_message TEXT,
                    download_duration DECIMAL(8,3),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_session (download_session_id),
                    INDEX idx_status (download_status),
                    INDEX idx_nse_symbol (nse_symbol)
                ) ENGINE=InnoDB COMMENT='Log for bulk stock data downloads'
            """)
            
            # Generate session ID
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Insert results
            insert_sql = """
                INSERT INTO bulk_download_log
                (download_session_id, nse_symbol, yahoo_symbol, download_status, 
                 records_downloaded, error_message, download_duration)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            for result in results:
                cursor.execute(insert_sql, (
                    session_id,
                    result['nse_symbol'],
                    result['yahoo_symbol'],
                    result['status'],
                    result['records_downloaded'],
                    result['error_message'],
                    result['download_duration']
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error logging download results: {e}")
            return None
    
    def download_bulk_data(self, start_date: date, end_date: date, 
                          max_workers: int = 3, max_symbols: int = None,
                          interval: str = "1d") -> dict:
        """Download data for multiple stocks in parallel"""
        
        print(f"🚀 Bulk NSE Stock Data Download")
        print(f"📅 Period: {start_date} to {end_date}")
        print(f"⚡ Max Workers: {max_workers}")
        print("=" * 60)
        
        # Get verified mappings
        mappings = self.get_verified_mappings(limit=max_symbols)
        if not mappings:
            print("❌ No verified symbol mappings found!")
            return {'error': 'No verified mappings'}
        
        print(f"📋 Found {len(mappings)} verified symbol mappings")
        
        results = []
        success_count = 0
        failed_count = 0
        total_records = 0
        
        print(f"\n⬇️  Starting downloads...")
        
        # Download with thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_mapping = {
                executor.submit(self.download_single_stock_data, mapping, start_date, end_date, interval): mapping
                for mapping in mappings
            }
            
            # Process completed downloads
            for i, future in enumerate(as_completed(future_to_mapping), 1):
                mapping = future_to_mapping[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'SUCCESS':
                        success_count += 1
                        total_records += result['records_downloaded']
                        print(f"[{i}/{len(mappings)}] ✅ {result['nse_symbol']}: {result['records_downloaded']} records ({result['download_duration']:.1f}s)")
                    else:
                        failed_count += 1
                        print(f"[{i}/{len(mappings)}] ❌ {result['nse_symbol']}: {result['status']} - {result['error_message']}")
                    
                    # Small delay to avoid overwhelming the API
                    time.sleep(0.1)
                    
                except Exception as e:
                    failed_count += 1
                    print(f"[{i}/{len(mappings)}] ❌ {mapping['nse_symbol']}: Exception - {e}")
                    results.append({
                        'nse_symbol': mapping['nse_symbol'],
                        'yahoo_symbol': mapping['yahoo_symbol'],
                        'status': 'FAILED',
                        'records_downloaded': 0,
                        'error_message': str(e),
                        'download_duration': 0
                    })
        
        # Log results to database
        session_id = self.log_download_results(results)
        
        # Summary
        success_rate = (success_count / len(mappings) * 100) if mappings else 0
        avg_duration = sum(r['download_duration'] for r in results) / len(results) if results else 0
        
        summary = {
            'total_symbols': len(mappings),
            'success_count': success_count,
            'failed_count': failed_count,
            'total_records_downloaded': total_records,
            'success_rate': success_rate,
            'average_duration': avg_duration,
            'session_id': session_id,
            'results': results
        }
        
        print(f"\n📊 Download Summary")
        print("=" * 40)
        print(f"Total Symbols: {summary['total_symbols']}")
        print(f"Successful: {summary['success_count']} ({summary['success_rate']:.1f}%)")
        print(f"Failed: {summary['failed_count']}")
        print(f"Records Downloaded: {summary['total_records_downloaded']:,}")
        print(f"Avg Duration: {summary['average_duration']:.1f}s")
        print(f"Session ID: {summary['session_id']}")
        
        return summary

def main():
    """Main function"""
    print("📈 NSE Bulk Stock Data Downloader")
    print("=" * 60)
    
    downloader = BulkStockDataDownloader()
    
    try:
        # Get date range from user
        print("📅 Enter download period:")
        
        # Default to last 30 days
        default_end = date.today()
        default_start = default_end - timedelta(days=30)
        
        start_input = input(f"Start date (YYYY-MM-DD) [default: {default_start}]: ").strip()
        end_input = input(f"End date (YYYY-MM-DD) [default: {default_end}]: ").strip()
        
        start_date = datetime.strptime(start_input, '%Y-%m-%d').date() if start_input else default_start
        end_date = datetime.strptime(end_input, '%Y-%m-%d').date() if end_input else default_end
        
        # Get number of symbols limit
        limit_input = input("Max symbols to download (default: all verified): ").strip()
        max_symbols = int(limit_input) if limit_input.isdigit() else None
        
        # Get thread count
        workers_input = input("Number of parallel workers (default: 3): ").strip()
        max_workers = int(workers_input) if workers_input.isdigit() else 3
        max_workers = min(max(max_workers, 1), 10)  # Limit between 1-10
        
        print(f"\n🎯 Configuration:")
        print(f"  Period: {start_date} to {end_date}")
        print(f"  Max Symbols: {max_symbols or 'All'}")
        print(f"  Workers: {max_workers}")
        
        confirm = input("\nProceed with download? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Download cancelled")
            return False
        
        # Start download
        summary = downloader.download_bulk_data(
            start_date=start_date,
            end_date=end_date,
            max_workers=max_workers,
            max_symbols=max_symbols
        )
        
        if 'error' in summary:
            print(f"❌ Download failed: {summary['error']}")
            return False
        
        print(f"\n✅ Bulk download completed!")
        print(f"📊 {summary['success_count']}/{summary['total_symbols']} symbols downloaded successfully")
        print(f"💾 {summary['total_records_downloaded']:,} total records stored")
        
        # Show failed downloads if any
        if summary['failed_count'] > 0:
            print(f"\n⚠️  Failed Downloads:")
            for result in summary['results']:
                if result['status'] != 'SUCCESS':
                    print(f"  • {result['nse_symbol']}: {result['error_message']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)