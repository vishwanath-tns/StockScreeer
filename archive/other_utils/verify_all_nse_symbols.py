"""
NSE Symbol Verification Script
Verifies all symbols in nse_index_constituents against Yahoo Finance API
Creates mappings and validates data availability
"""

import os
import sys
import time
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
import yfinance as yf
import mysql.connector
from mysql.connector import Error
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nse_symbol_verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NSESymbolVerifier:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'database': os.getenv('MYSQL_DB', 'MarketData'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'admin')
        }
        
        # Yahoo Finance symbol suffixes to try
        self.suffixes = ['.NS', '.BO', '']
        
        # Verification stats
        self.total_symbols = 0
        self.verified_count = 0
        self.failed_count = 0
        self.existing_mappings = 0
        
    def get_nse_symbols(self) -> List[Dict]:
        """Get all NSE symbols from database"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            # Get all active NSE symbols excluding indices
            cursor.execute("""
                SELECT DISTINCT symbol
                FROM nse_index_constituents 
                WHERE symbol NOT LIKE '%NIFTY%' 
                AND symbol NOT LIKE '%INDEX%'
                AND symbol NOT LIKE '%MIDCAP%'
                AND symbol NOT LIKE '%SMALLCAP%'
                ORDER BY symbol
            """)
            
            symbols = cursor.fetchall()
            cursor.close()
            connection.close()
            
            logger.info(f"Found {len(symbols)} NSE symbols to verify")
            return symbols
            
        except Error as e:
            logger.error(f"Error fetching NSE symbols: {e}")
            return []
    
    def check_existing_mapping(self, nse_symbol: str) -> Optional[str]:
        """Check if symbol already has a mapping"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT yahoo_symbol, is_verified 
                FROM nse_yahoo_symbol_map 
                WHERE nse_symbol = %s AND is_active = 1
            """, (nse_symbol,))
            
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if result:
                return result[0]
            return None
            
        except Error as e:
            logger.error(f"Error checking existing mapping for {nse_symbol}: {e}")
            return None
    
    def verify_yahoo_symbol(self, yahoo_symbol: str) -> Tuple[bool, Dict]:
        """Verify if a Yahoo Finance symbol exists and has data"""
        try:
            ticker = yf.Ticker(yahoo_symbol)
            
            # Try to get recent data (last 5 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=10)
            
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                return False, {}
            
            # Get additional info if available
            info = {}
            try:
                ticker_info = ticker.info
                info = {
                    'name': ticker_info.get('shortName', ticker_info.get('longName', '')),
                    'sector': ticker_info.get('sector', ''),
                    'industry': ticker_info.get('industry', ''),
                    'currency': ticker_info.get('currency', 'INR'),
                    'market_cap': ticker_info.get('marketCap', None)
                }
            except:
                # Info might not be available for all symbols
                pass
            
            return True, info
            
        except Exception as e:
            logger.debug(f"Error verifying {yahoo_symbol}: {e}")
            return False, {}
    
    def find_yahoo_symbol(self, nse_symbol: str) -> Tuple[Optional[str], Dict]:
        """Try different suffixes to find valid Yahoo Finance symbol"""
        
        # First try common patterns
        candidates = [
            f"{nse_symbol}.NS",  # Most common for NSE
            f"{nse_symbol}.BO",  # Bombay Stock Exchange
            nse_symbol,          # Some symbols work without suffix
        ]
        
        for candidate in candidates:
            is_valid, info = self.verify_yahoo_symbol(candidate)
            if is_valid:
                logger.info(f"✓ Found mapping: {nse_symbol} -> {candidate}")
                return candidate, info
            
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
        
        logger.warning(f"✗ No valid Yahoo symbol found for {nse_symbol}")
        return None, {}
    
    def save_mapping(self, nse_symbol: str, yahoo_symbol: str, info: Dict, is_verified: bool = True):
        """Save symbol mapping to database"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Check if mapping already exists
            cursor.execute("""
                SELECT id FROM nse_yahoo_symbol_map 
                WHERE nse_symbol = %s
            """, (nse_symbol,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing mapping
                cursor.execute("""
                    UPDATE nse_yahoo_symbol_map 
                    SET yahoo_symbol = %s, sector = %s, is_verified = %s, 
                        is_active = 1, last_verified = NOW()
                    WHERE nse_symbol = %s
                """, (yahoo_symbol, info.get('sector', ''), is_verified, nse_symbol))
                
                logger.debug(f"Updated mapping: {nse_symbol} -> {yahoo_symbol}")
            else:
                # Insert new mapping
                cursor.execute("""
                    INSERT INTO nse_yahoo_symbol_map 
                    (nse_symbol, yahoo_symbol, sector, is_verified, is_active, created_at)
                    VALUES (%s, %s, %s, %s, 1, NOW())
                """, (nse_symbol, yahoo_symbol, info.get('sector', ''), is_verified))
                
                logger.debug(f"Created mapping: {nse_symbol} -> {yahoo_symbol}")
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Error as e:
            logger.error(f"Error saving mapping for {nse_symbol}: {e}")
    
    def log_verification_attempt(self, nse_symbol: str, yahoo_symbol: str, success: bool, error_msg: str = ''):
        """Log verification attempt to database"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            cursor.execute("""
                INSERT INTO symbol_mapping_validation_log 
                (nse_symbol, yahoo_symbol_tested, is_valid, error_message, tested_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                is_valid = VALUES(is_valid),
                error_message = VALUES(error_message),
                tested_at = VALUES(tested_at)
            """, (nse_symbol, yahoo_symbol, success, error_msg))
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Error as e:
            logger.error(f"Error logging verification for {nse_symbol}: {e}")
    
    def verify_all_symbols(self, batch_size: int = 50):
        """Verify all NSE symbols in batches"""
        symbols = self.get_nse_symbols()
        self.total_symbols = len(symbols)
        
        if not symbols:
            logger.error("No symbols found to verify")
            return
        
        logger.info(f"Starting verification of {self.total_symbols} NSE symbols...")
        
        for i, symbol_info in enumerate(symbols):
            nse_symbol = symbol_info['symbol'] if isinstance(symbol_info, dict) else symbol_info[0]
            
            try:
                # Check if already mapped
                existing_yahoo = self.check_existing_mapping(nse_symbol)
                if existing_yahoo:
                    logger.info(f"[{i+1}/{self.total_symbols}] {nse_symbol} already mapped to {existing_yahoo}")
                    self.existing_mappings += 1
                    continue
                
                logger.info(f"[{i+1}/{self.total_symbols}] Verifying {nse_symbol}...")
                
                # Find Yahoo Finance symbol
                yahoo_symbol, info = self.find_yahoo_symbol(nse_symbol)
                
                if yahoo_symbol:
                    # Save successful mapping
                    self.save_mapping(nse_symbol, yahoo_symbol, info, True)
                    self.log_verification_attempt(nse_symbol, yahoo_symbol, True)
                    self.verified_count += 1
                else:
                    # Log failed verification
                    self.log_verification_attempt(nse_symbol, nse_symbol + '.NS', False, 'No valid Yahoo symbol found')
                    self.failed_count += 1
                
                # Progress update every 10 symbols
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{self.total_symbols} processed")
                
                # Rate limiting - pause every batch
                if (i + 1) % batch_size == 0:
                    logger.info(f"Completed batch of {batch_size}, pausing for 5 seconds...")
                    time.sleep(5)
                else:
                    time.sleep(0.2)  # Small delay between requests
                    
            except Exception as e:
                logger.error(f"Error processing {nse_symbol}: {e}")
                self.failed_count += 1
                continue
        
        # Print final summary
        self.print_verification_summary()
    
    def print_verification_summary(self):
        """Print verification summary"""
        logger.info("=" * 60)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total symbols processed: {self.total_symbols}")
        logger.info(f"Already mapped: {self.existing_mappings}")
        logger.info(f"Successfully verified: {self.verified_count}")
        logger.info(f"Failed verification: {self.failed_count}")
        logger.info(f"Success rate: {(self.verified_count / max(1, self.total_symbols - self.existing_mappings)) * 100:.1f}%")
        logger.info("=" * 60)
        
        # Update verification stats in database
        self.update_verification_stats()
    
    def update_verification_stats(self):
        """Update verification statistics in database"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            cursor.execute("""
                INSERT INTO symbol_mapping_stats 
                (verification_date, total_symbols, verified_count, failed_count, success_rate)
                VALUES (NOW(), %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                verified_count = VALUES(verified_count),
                failed_count = VALUES(failed_count),
                success_rate = VALUES(success_rate)
            """, (
                self.total_symbols, 
                self.verified_count, 
                self.failed_count,
                (self.verified_count / max(1, self.total_symbols - self.existing_mappings)) * 100
            ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Error as e:
            logger.error(f"Error updating verification stats: {e}")

def main():
    """Main verification process"""
    print("NSE Symbol Verification Tool")
    print("=" * 40)
    
    # Confirm before starting
    response = input("This will verify all NSE symbols against Yahoo Finance. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Verification cancelled.")
        return
    
    verifier = NSESymbolVerifier()
    
    try:
        # Start verification
        start_time = datetime.now()
        verifier.verify_all_symbols(batch_size=50)
        end_time = datetime.now()
        
        duration = end_time - start_time
        logger.info(f"Verification completed in {duration}")
        
        print(f"\nVerification log saved to: nse_symbol_verification.log")
        print("Check the database tables:")
        print("- nse_yahoo_symbol_map: For successful mappings")
        print("- symbol_mapping_validation_log: For detailed verification logs")
        print("- symbol_mapping_stats: For summary statistics")
        
    except KeyboardInterrupt:
        logger.info("Verification stopped by user")
    except Exception as e:
        logger.error(f"Verification failed: {e}")

if __name__ == "__main__":
    main()