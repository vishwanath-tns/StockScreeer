"""
Comprehensive NSE Symbol Verification - ALL 526 symbols
Verifies every symbol in nse_index_constituents including indices
"""

import os
import time
import mysql.connector
from dotenv import load_dotenv
import yfinance as yf
from datetime import date, timedelta

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        database=os.getenv('MYSQL_DB', 'MarketData'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'admin')
    )

def get_all_symbols():
    """Get ALL symbols from nse_index_constituents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT symbol
            FROM nse_index_constituents
            ORDER BY symbol
        """)
        
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return symbols
        
    except Exception as e:
        print(f"Error getting symbols: {e}")
        return []

def get_unmapped_symbols():
    """Get symbols not yet mapped"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT n.symbol
            FROM nse_index_constituents n
            LEFT JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol AND m.is_active = 1
            WHERE m.nse_symbol IS NULL
            ORDER BY n.symbol
        """)
        
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return symbols
        
    except Exception as e:
        print(f"Error getting unmapped symbols: {e}")
        return []

def verify_symbol(nse_symbol):
    """Verify a single symbol with special handling for indices"""
    
    # Special mappings for common indices
    special_mappings = {
        'NIFTY 50': '^NSEI',
        'NIFTY BANK': '^NSEBANK', 
        'NIFTY IT': '^CNXIT',
        'NIFTY AUTO': '^CNXAUTO',
        'NIFTY PHARMA': '^CNXPHARMA',
        'NIFTY FMCG': '^CNXFMCG',
        'NIFTY METAL': '^CNXMETAL',
        'NIFTY REALTY': '^CNXREALTY',
        'NIFTY ENERGY': '^CNXENERGY',
        'NIFTY PSU BANK': '^CNXPSUBANK',
        'NIFTY PVT BANK': '^CNXPVTBANK',
        'NIFTY MID 50': '^NSMIDCP',
        'NIFTY SMALL CAP 100': '^NSMALLCP',
        'NIFTY 100': '^CNX100',
        'NIFTY 200': '^CNX200',
        'NIFTY 500': '^CNX500'
    }
    
    # Check special mappings first
    if nse_symbol in special_mappings:
        yahoo_symbol = special_mappings[nse_symbol]
        try:
            ticker = yf.Ticker(yahoo_symbol)
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            hist = ticker.history(start=start_date, end=end_date)
            
            if not hist.empty:
                return yahoo_symbol, 'Index'
        except:
            pass
    
    # Try standard suffixes
    suffixes = ['.NS', '.BO', '']
    
    # For index-like names, also try ^ prefix
    if 'NIFTY' in nse_symbol or 'INDEX' in nse_symbol:
        # Try ^NSE format for indices
        test_symbols = [f"^{nse_symbol}", f"^NSE{nse_symbol}"] + [f"{nse_symbol}{suffix}" for suffix in suffixes]
    else:
        test_symbols = [f"{nse_symbol}{suffix}" for suffix in suffixes]
    
    for yahoo_symbol in test_symbols:
        try:
            ticker = yf.Ticker(yahoo_symbol)
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            hist = ticker.history(start=start_date, end=end_date)
            
            if not hist.empty:
                try:
                    info = ticker.info
                    sector = info.get('sector', '')
                    if not sector and ('^' in yahoo_symbol or 'NIFTY' in nse_symbol):
                        sector = 'Index'
                except:
                    sector = 'Index' if ('^' in yahoo_symbol or 'NIFTY' in nse_symbol) else ''
                return yahoo_symbol, sector
                
        except Exception:
            continue
        time.sleep(0.1)
    
    return None, ''

def save_mapping(nse_symbol, yahoo_symbol, sector):
    """Save mapping to database"""
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
            is_active = 1,
            updated_at = NOW()
        """, (nse_symbol, yahoo_symbol, sector))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error saving {nse_symbol}: {e}")
        return False

def get_current_stats():
    """Get current verification statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM nse_index_constituents")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1 AND is_verified = 1")
        verified = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1 AND is_verified = 0")
        failed = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return total, verified, failed
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return 0, 0, 0

def main():
    print("Comprehensive NSE Symbol Verification - ALL 526 symbols")
    print("=" * 55)
    
    # Get initial stats
    total_symbols, current_verified, current_failed = get_current_stats()
    print(f"Total symbols in database: {total_symbols}")
    print(f"Currently verified: {current_verified}")
    print(f"Currently failed: {current_failed}")
    print(f"Remaining to verify: {total_symbols - current_verified - current_failed}")
    
    response = input("\\nContinue with verification of remaining symbols? (y/n): ")
    if response.lower() != 'y':
        print("Verification cancelled.")
        return
    
    start_time = time.time()
    batch_num = 0
    
    while True:
        # Get remaining symbols
        unmapped = get_unmapped_symbols()
        
        if not unmapped:
            print("\\nAll symbols verified!")
            break
        
        batch_num += 1
        print(f"\\n--- Batch {batch_num} ---")
        print(f"Remaining symbols to verify: {len(unmapped)}")
        
        # Process next batch of 25
        batch = unmapped[:25]
        success_count = 0
        failed_count = 0
        
        for i, symbol in enumerate(batch):
            print(f"[{i+1}/25] Verifying {symbol}...", end=' ')
            
            yahoo_symbol, sector = verify_symbol(symbol)
            
            if yahoo_symbol:
                if save_mapping(symbol, yahoo_symbol, sector):
                    symbol_type = 'IDX' if sector == 'Index' else 'STK'
                    print(f"OK -> {yahoo_symbol} ({sector}) [{symbol_type}]")
                    success_count += 1
                else:
                    print("SAVE_ERROR")
                    failed_count += 1
            else:
                print("NOT_FOUND")
                failed_count += 1
                # Save as failed mapping
                save_mapping(symbol, f"{symbol}.NS", "Unknown")
            
            time.sleep(0.3)  # Slightly longer delay for stability
        
        print(f"Batch {batch_num} complete: {success_count} successful, {failed_count} failed")
        
        # Progress update
        total, verified, failed = get_current_stats()
        remaining = total - verified - failed
        print(f"Overall progress: {verified}/{total} verified ({(verified/total)*100:.1f}%)")
        
        if remaining <= 0:
            break
    
    # Final comprehensive report
    end_time = time.time()
    duration = int(end_time - start_time)
    
    total, verified, failed = get_current_stats()
    
    print(f"\\n{'='*60}")
    print("COMPREHENSIVE VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total NSE symbols processed: {total}")
    print(f"Successfully verified: {verified}")
    print(f"Failed verification: {failed}")
    print(f"Success rate: {(verified/total)*100:.1f}%")
    print(f"Duration: {duration} seconds")
    print(f"{'='*60}")
    
    # Show breakdown by type
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            CASE 
                WHEN sector = 'Index' THEN 'Indices'
                WHEN sector IN ('Financial Services', 'Technology', 'Healthcare', 'Energy', 'Basic Materials', 'Consumer Cyclical', 'Industrials', 'Utilities', 'Consumer Defensive', 'Real Estate', 'Communication Services') THEN 'Stocks'
                ELSE 'Other'
            END as category,
            COUNT(*) as count
        FROM nse_yahoo_symbol_map 
        WHERE is_active = 1 AND is_verified = 1
        GROUP BY category
        ORDER BY count DESC
    """)
    
    print("\\nBreakdown by category:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} symbols")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()