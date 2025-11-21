"""
Complete NSE Symbol Verification - Simple Approach
Continues verifying remaining symbols until completion
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

def get_unmapped_symbols():
    """Get all remaining unmapped symbols"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        """)
        
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return symbols
        
    except Exception as e:
        print(f"Error getting unmapped symbols: {e}")
        return []

def verify_symbol(nse_symbol):
    """Verify a single symbol"""
    suffixes = ['.NS', '.BO', '']
    
    for suffix in suffixes:
        yahoo_symbol = f"{nse_symbol}{suffix}"
        try:
            ticker = yf.Ticker(yahoo_symbol)
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            hist = ticker.history(start=start_date, end=end_date)
            
            if not hist.empty:
                try:
                    info = ticker.info
                    sector = info.get('sector', '')
                except:
                    sector = ''
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
            is_active = 1
        """, (nse_symbol, yahoo_symbol, sector))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error saving {nse_symbol}: {e}")
        return False

def main():
    print("Completing NSE Symbol Verification")
    print("=" * 35)
    
    while True:
        # Get remaining symbols
        unmapped = get_unmapped_symbols()
        
        if not unmapped:
            print("All symbols verified!")
            break
        
        print(f"Remaining symbols to verify: {len(unmapped)}")
        
        # Process next batch of 20
        batch = unmapped[:20]
        success_count = 0
        
        for i, symbol in enumerate(batch):
            print(f"[{i+1}/20] Verifying {symbol}...", end=' ')
            
            yahoo_symbol, sector = verify_symbol(symbol)
            
            if yahoo_symbol:
                if save_mapping(symbol, yahoo_symbol, sector):
                    print(f"OK -> {yahoo_symbol} ({sector})")
                    success_count += 1
                else:
                    print("SAVE_ERROR")
            else:
                print("NOT_FOUND")
            
            time.sleep(0.2)
        
        print(f"Batch complete: {success_count}/20 successful")
        
        if len(unmapped) <= 20:
            print("Verification complete!")
            break
    
    # Final status
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM nse_index_constituents WHERE symbol NOT LIKE '%NIFTY%' AND symbol NOT LIKE '%INDEX%' AND symbol NOT LIKE '%MIDCAP%' AND symbol NOT LIKE '%SMALLCAP%'")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1 AND is_verified = 1")
    verified = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Total NSE symbols: {total}")
    print(f"Successfully verified: {verified}")
    print(f"Success rate: {(verified/total)*100:.1f}%")

if __name__ == "__main__":
    main()