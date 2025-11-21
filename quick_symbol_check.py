"""
Quick NSE Symbol Status Check
Shows current verification status and runs verification for unmapped symbols
"""

import os
import mysql.connector
from dotenv import load_dotenv
import yfinance as yf
from datetime import date, timedelta
import time

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        database=os.getenv('MYSQL_DB', 'MarketData'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'admin')
    )

def check_current_status():
    """Check current verification status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total NSE symbols (excluding indices)
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol) 
            FROM nse_index_constituents 
            WHERE symbol NOT LIKE '%NIFTY%' 
            AND symbol NOT LIKE '%INDEX%'
            AND symbol NOT LIKE '%MIDCAP%'
            AND symbol NOT LIKE '%SMALLCAP%'
        """)
        total_symbols = cursor.fetchone()[0]
        
        # Currently mapped symbols
        cursor.execute("""
            SELECT COUNT(*) 
            FROM nse_yahoo_symbol_map 
            WHERE is_active = 1
        """)
        mapped_symbols = cursor.fetchone()[0]
        
        # Verified symbols
        cursor.execute("""
            SELECT COUNT(*) 
            FROM nse_yahoo_symbol_map 
            WHERE is_active = 1 AND is_verified = 1
        """)
        verified_symbols = cursor.fetchone()[0]
        
        # Failed verifications
        cursor.execute("""
            SELECT COUNT(*) 
            FROM nse_yahoo_symbol_map 
            WHERE is_active = 1 AND is_verified = 0
        """)
        failed_symbols = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print("="*50)
        print("NSE SYMBOL VERIFICATION STATUS")
        print("="*50)
        print(f"Total NSE symbols: {total_symbols}")
        print(f"Currently mapped: {mapped_symbols}")
        print(f"Successfully verified: {verified_symbols}")
        print(f"Failed verification: {failed_symbols}")
        print(f"Unmapped symbols: {total_symbols - mapped_symbols}")
        print(f"Success rate: {(verified_symbols/max(1,mapped_symbols))*100:.1f}%")
        print("="*50)
        
        return total_symbols, mapped_symbols, verified_symbols
        
    except Exception as e:
        print(f"Error checking status: {e}")
        return 0, 0, 0

def get_unmapped_symbols(limit=20):
    """Get unmapped symbols to verify"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT DISTINCT n.symbol
            FROM nse_index_constituents n
            LEFT JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol AND m.is_active = 1
            WHERE m.nse_symbol IS NULL
            AND n.symbol NOT LIKE '%NIFTY%' 
            AND n.symbol NOT LIKE '%INDEX%'
            AND n.symbol NOT LIKE '%MIDCAP%'
            AND n.symbol NOT LIKE '%SMALLCAP%'
            ORDER BY n.symbol
            LIMIT %s
        """, (limit,))
        
        symbols = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return symbols
        
    except Exception as e:
        print(f"Error getting unmapped symbols: {e}")
        return []

def verify_symbol(nse_symbol):
    """Quick verification of a single symbol"""
    suffixes = ['.NS', '.BO', '']
    
    for suffix in suffixes:
        yahoo_symbol = f"{nse_symbol}{suffix}"
        try:
            ticker = yf.Ticker(yahoo_symbol)
            
            # Try to get recent data
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            
            hist = ticker.history(start=start_date, end=end_date)
            
            if not hist.empty:
                # Get basic info
                try:
                    info = ticker.info
                    sector = info.get('sector', '')
                    name = info.get('shortName', info.get('longName', ''))
                except:
                    sector = ''
                    name = ''
                
                return yahoo_symbol, sector, name
                
        except Exception as e:
            continue
        
        time.sleep(0.1)  # Small delay
    
    return None, '', ''

def save_mapping(nse_symbol, yahoo_symbol, sector, name=''):
    """Save verified mapping to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO nse_yahoo_symbol_map 
            (nse_symbol, yahoo_symbol, sector, is_verified, is_active, created_at)
            VALUES (%s, %s, %s, 1, 1, NOW())
            ON DUPLICATE KEY UPDATE
            yahoo_symbol = VALUES(yahoo_symbol),
            sector = VALUES(sector),
            is_verified = 1,
            is_active = 1
        """, (nse_symbol, yahoo_symbol, sector))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error saving mapping for {nse_symbol}: {e}")
        return False

def quick_verify_batch(batch_size=20):
    """Run quick verification for a batch of unmapped symbols"""
    print(f"\nRunning quick verification for {batch_size} unmapped symbols...")
    
    symbols = get_unmapped_symbols(batch_size)
    if not symbols:
        print("No unmapped symbols found!")
        return
    
    success_count = 0
    failed_count = 0
    
    for i, symbol_info in enumerate(symbols):
        nse_symbol = symbol_info['symbol'] if isinstance(symbol_info, dict) else symbol_info[0]
        
        print(f"[{i+1}/{len(symbols)}] Verifying {nse_symbol}... ", end='')
        
        yahoo_symbol, sector, name = verify_symbol(nse_symbol)
        
        if yahoo_symbol:
            if save_mapping(nse_symbol, yahoo_symbol, sector, name):
                print(f"✓ {yahoo_symbol} ({sector})")
                success_count += 1
            else:
                print("✗ Failed to save")
                failed_count += 1
        else:
            print("✗ No valid mapping")
            failed_count += 1
        
        time.sleep(0.2)  # Rate limiting
    
    print(f"\nBatch verification complete:")
    print(f"Successfully verified: {success_count}")
    print(f"Failed: {failed_count}")

def main():
    print("NSE Symbol Verification Status Checker")
    print("="*40)
    
    # Check current status
    total, mapped, verified = check_current_status()
    
    if total == 0:
        print("No symbols found or database connection error")
        return
    
    # Show some unmapped symbols
    unmapped = get_unmapped_symbols(10)
    if unmapped:
        print(f"\nSample unmapped symbols:")
        for symbol in unmapped[:10]:
            symbol_name = symbol['symbol'] if isinstance(symbol, dict) else symbol[0]
            print(f"  {symbol_name}")
    
    # Ask if user wants to verify some symbols
    print(f"\nFound {total - mapped} unmapped symbols")
    response = input("Verify a batch of 20 symbols now? (y/n): ")
    
    if response.lower() == 'y':
        quick_verify_batch(20)
        print("\nUpdated status:")
        check_current_status()

if __name__ == "__main__":
    main()