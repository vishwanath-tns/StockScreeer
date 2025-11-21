#!/usr/bin/env python3
"""
Symbol Mapping Validator
Tests NSE to Yahoo Finance symbol mappings by downloading sample data
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

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from yahoo_client import YahooFinanceClient
from db_service import YFinanceDBService

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SymbolMappingValidator:
    """Validates NSE to Yahoo Finance symbol mappings"""
    
    def __init__(self):
        self.yahoo_client = YahooFinanceClient()
        self.db_service = YFinanceDBService()
        
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
    
    def validate_single_mapping(self, nse_symbol: str, yahoo_symbol: str, test_days: int = 5) -> dict:
        """Validate a single symbol mapping"""
        result = {
            'nse_symbol': nse_symbol,
            'yahoo_symbol': yahoo_symbol,
            'status': 'FAILED',
            'error_message': None,
            'sample_data_matches': False,
            'last_trading_date': None,
            'validation_method': 'API_TEST'
        }
        
        try:
            # Test with yfinance
            ticker = yf.Ticker(yahoo_symbol)
            end_date = date.today()
            start_date = end_date - timedelta(days=test_days)
            
            # Get recent data
            data = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if not data.empty:
                result['status'] = 'SUCCESS'
                result['sample_data_matches'] = True
                result['last_trading_date'] = data.index[-1].date()
                
                # Basic data quality checks
                latest_data = data.iloc[-1]
                if pd.isna(latest_data['Close']) or latest_data['Close'] <= 0:
                    result['status'] = 'DATA_MISMATCH'
                    result['error_message'] = 'Invalid price data'
                    result['sample_data_matches'] = False
                
            else:
                result['status'] = 'NOT_FOUND'
                result['error_message'] = 'No data returned from Yahoo Finance'
                
        except Exception as e:
            result['status'] = 'FAILED'
            result['error_message'] = str(e)
            
        return result
    
    def log_validation_result(self, validation_result: dict):
        """Log validation result to database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            insert_sql = """
                INSERT INTO symbol_mapping_validation_log
                (nse_symbol, yahoo_symbol, validation_status, validation_method, 
                 error_message, sample_data_matches, last_trading_date, validation_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_sql, (
                validation_result['nse_symbol'],
                validation_result['yahoo_symbol'],
                validation_result['status'],
                validation_result['validation_method'],
                validation_result['error_message'],
                validation_result['sample_data_matches'],
                validation_result['last_trading_date'],
                f"Automated validation on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ))
            
            # Update mapping table if validation succeeded
            if validation_result['status'] == 'SUCCESS':
                cursor.execute("""
                    UPDATE nse_yahoo_symbol_map 
                    SET is_verified = TRUE, last_verified = CURRENT_DATE
                    WHERE nse_symbol = %s
                """, (validation_result['nse_symbol'],))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging validation result: {e}")
    
    def validate_batch_mappings(self, limit: int = 20, delay: float = 1.0) -> dict:
        """Validate multiple mappings with rate limiting"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get unverified mappings
            cursor.execute("""
                SELECT nse_symbol, yahoo_symbol, company_name, sector
                FROM nse_yahoo_symbol_map 
                WHERE is_verified = FALSE
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            mappings = cursor.fetchall()
            cursor.close()
            conn.close()
            
            results = {
                'total': len(mappings),
                'success': 0,
                'failed': 0,
                'not_found': 0,
                'data_mismatch': 0,
                'details': []
            }
            
            print(f"🔍 Validating {len(mappings)} symbol mappings...")
            
            for i, mapping in enumerate(mappings, 1):
                print(f"[{i}/{len(mappings)}] Testing {mapping['nse_symbol']} → {mapping['yahoo_symbol']}")
                
                # Validate mapping
                result = self.validate_single_mapping(
                    mapping['nse_symbol'], 
                    mapping['yahoo_symbol']
                )
                
                # Log result
                self.log_validation_result(result)
                
                # Update counters
                if result['status'] == 'SUCCESS':
                    results['success'] += 1
                    print(f"  ✅ SUCCESS - Last trading: {result['last_trading_date']}")
                elif result['status'] == 'NOT_FOUND':
                    results['not_found'] += 1
                    print(f"  ❌ NOT FOUND - {result['error_message']}")
                elif result['status'] == 'DATA_MISMATCH':
                    results['data_mismatch'] += 1
                    print(f"  ⚠️  DATA ISSUE - {result['error_message']}")
                else:
                    results['failed'] += 1
                    print(f"  ❌ FAILED - {result['error_message']}")
                
                results['details'].append(result)
                
                # Rate limiting to avoid overwhelming Yahoo Finance
                if delay > 0 and i < len(mappings):
                    time.sleep(delay)
            
            # Update overall statistics
            self.update_validation_statistics(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating batch mappings: {e}")
            return {'error': str(e)}
    
    def update_validation_statistics(self, results: dict):
        """Update validation statistics in database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get current stats
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM nse_yahoo_symbol_map) as total_mapped,
                    (SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_verified = TRUE) as verified
            """)
            
            stats = cursor.fetchone()
            total_mapped = stats[0] if stats else 0
            verified = stats[1] if stats else 0
            
            # Update statistics
            cursor.execute("""
                UPDATE symbol_mapping_stats 
                SET mapped_symbols = %s,
                    verified_symbols = %s,
                    last_validation_run = CURRENT_TIMESTAMP,
                    notes = %s
                ORDER BY id DESC LIMIT 1
            """, (
                total_mapped,
                verified,
                f"Validation run completed: {results['success']} success, {results['failed']} failed"
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def show_validation_summary(self):
        """Show validation summary"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            print("\n📊 Symbol Mapping Validation Summary")
            print("=" * 50)
            
            # Overall statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_mappings,
                    SUM(CASE WHEN is_verified = TRUE THEN 1 ELSE 0 END) as verified_mappings,
                    SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_mappings
                FROM nse_yahoo_symbol_map
            """)
            
            stats = cursor.fetchone()
            if stats:
                verification_rate = (stats['verified_mappings'] / stats['total_mappings'] * 100) if stats['total_mappings'] > 0 else 0
                print(f"Total Mappings: {stats['total_mappings']}")
                print(f"Verified: {stats['verified_mappings']} ({verification_rate:.1f}%)")
                print(f"Active: {stats['active_mappings']}")
            
            # Validation results breakdown
            print("\n📋 Recent Validation Results:")
            cursor.execute("""
                SELECT validation_status, COUNT(*) as count
                FROM symbol_mapping_validation_log
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
                GROUP BY validation_status
            """)
            
            validation_stats = cursor.fetchall()
            for stat in validation_stats:
                print(f"  {stat['validation_status']}: {stat['count']}")
            
            # Top sectors mapped
            print("\n🏢 Sectors Coverage:")
            cursor.execute("""
                SELECT sector, 
                       COUNT(*) as total,
                       SUM(CASE WHEN is_verified = TRUE THEN 1 ELSE 0 END) as verified
                FROM nse_yahoo_symbol_map
                WHERE sector IS NOT NULL
                GROUP BY sector
                ORDER BY total DESC
                LIMIT 10
            """)
            
            sector_stats = cursor.fetchall()
            for sector in sector_stats:
                verification_pct = (sector['verified'] / sector['total'] * 100) if sector['total'] > 0 else 0
                print(f"  {sector['sector']}: {sector['verified']}/{sector['total']} ({verification_pct:.1f}%)")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error showing validation summary: {e}")

def main():
    """Main function"""
    print("🔍 NSE to Yahoo Finance Symbol Mapping Validator")
    print("=" * 60)
    
    validator = SymbolMappingValidator()
    
    try:
        # Show current summary
        validator.show_validation_summary()
        
        # Ask user for validation batch size
        print("\n" + "=" * 60)
        response = input("Enter number of mappings to validate (default 10, 0 to skip): ").strip()
        
        if response == "0":
            print("Skipping validation...")
        else:
            try:
                batch_size = int(response) if response else 10
                batch_size = min(max(batch_size, 1), 50)  # Limit between 1-50
                
                print(f"\n🚀 Starting validation of {batch_size} mappings...")
                results = validator.validate_batch_mappings(limit=batch_size, delay=1.0)
                
                if 'error' in results:
                    print(f"❌ Validation failed: {results['error']}")
                else:
                    print(f"\n✅ Validation completed!")
                    print(f"  Success: {results['success']}/{results['total']}")
                    print(f"  Failed: {results['failed']}/{results['total']}")
                    print(f"  Not Found: {results['not_found']}/{results['total']}")
                    print(f"  Data Issues: {results['data_mismatch']}/{results['total']}")
                
            except ValueError:
                print("❌ Invalid number entered")
        
        # Show updated summary
        print("\n" + "=" * 60)
        validator.show_validation_summary()
        
        print("\n✅ Validation process completed!")
        print("\n📋 Next steps:")
        print("1. Review failed validations and fix symbol mappings")
        print("2. Use verified mappings for bulk data download")
        print("3. Run validation periodically to maintain data quality")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)