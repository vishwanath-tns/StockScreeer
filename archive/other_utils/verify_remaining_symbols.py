#!/usr/bin/env python3
"""
Fixed symbol verification script to verify only remaining unmapped symbols
"""

import sys
from sqlalchemy import text
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

# Import the engine function from sync_bhav_gui to reuse database connection
from sync_bhav_gui import engine

def get_unmapped_symbols():
    """Get symbols that haven't been verified yet"""
    eng = engine()
    
    query = """
    SELECT DISTINCT nic.symbol, nic.company_name, nic.index_id
    FROM nse_index_constituents nic
    LEFT JOIN nse_yahoo_symbol_map nysm ON nic.symbol = nysm.nse_symbol
    WHERE nysm.nse_symbol IS NULL
    ORDER BY nic.symbol
    """
    
    with eng.connect() as conn:
        result = conn.execute(text(query))
        symbols = []
        for row in result:
            symbols.append({
                'symbol': row[0],
                'company_name': row[1],
                'index_id': row[2]
            })
    
    return symbols

def categorize_symbol(symbol, company_name):
    """Categorize symbol into sector based on name"""
    symbol_lower = symbol.lower()
    company_lower = company_name.lower() if company_name else ""
    
    # Banking
    if any(keyword in company_lower for keyword in ['bank', 'financial']):
        return 'Banking'
    
    # IT
    if any(keyword in company_lower for keyword in ['tech', 'info', 'software', 'system', 'computer']):
        return 'IT'
    
    # Energy/Oil
    if any(keyword in company_lower for keyword in ['oil', 'gas', 'petroleum', 'energy', 'power']):
        return 'Energy'
    
    # Pharma
    if any(keyword in company_lower for keyword in ['pharma', 'drug', 'medicine', 'healthcare']):
        return 'Pharmaceuticals'
    
    # Auto
    if any(keyword in company_lower for keyword in ['auto', 'motor', 'vehicle', 'tyre']):
        return 'Automotive'
    
    # Telecom
    if any(keyword in company_lower for keyword in ['telecom', 'communication', 'bharti']):
        return 'Telecom'
    
    # Metal
    if any(keyword in company_lower for keyword in ['steel', 'metal', 'mining', 'aluminium', 'copper']):
        return 'Metals'
    
    # FMCG
    if any(keyword in company_lower for keyword in ['consumer', 'goods', 'food', 'cigarette']):
        return 'FMCG'
    
    return 'Others'

def verify_yahoo_symbol(symbol):
    """Verify if a symbol exists on Yahoo Finance"""
    candidates = [
        f"{symbol}.NS",    # NSE format
        f"{symbol}.BO",    # BSE format  
        symbol             # Direct symbol
    ]
    
    for candidate in candidates:
        try:
            ticker = yf.Ticker(candidate)
            # Try to get basic info
            info = ticker.info
            if info and len(info) > 5:  # Basic validation
                return candidate, 'STK'
        except Exception:
            continue
    
    return None, None

def save_mapping(nse_symbol, yahoo_symbol, symbol_type, sector, company_name):
    """Save the symbol mapping to database"""
    eng = engine()
    
    insert_query = """
    INSERT INTO nse_yahoo_symbol_map 
    (nse_symbol, yahoo_symbol, sector, company_name, last_verified, is_active, is_verified)
    VALUES (:nse_symbol, :yahoo_symbol, :sector, :company_name, :last_verified, 1, 1)
    ON DUPLICATE KEY UPDATE
        yahoo_symbol = VALUES(yahoo_symbol),
        sector = VALUES(sector),
        company_name = VALUES(company_name),
        last_verified = VALUES(last_verified),
        is_active = 1,
        is_verified = 1
    """
    
    with eng.connect() as conn:
        conn.execute(text(insert_query), {
            'nse_symbol': nse_symbol,
            'yahoo_symbol': yahoo_symbol, 
            'sector': sector,
            'company_name': company_name,
            'last_verified': datetime.now().date()
        })
        conn.commit()

def main():
    print("Getting unmapped symbols...")
    unmapped_symbols = get_unmapped_symbols()
    
    if not unmapped_symbols:
        print("All symbols are already verified!")
        return
    
    total_symbols = len(unmapped_symbols)
    print(f"Found {total_symbols} unmapped symbols to verify")
    
    successful = 0
    failed = 0
    
    for i, symbol_info in enumerate(unmapped_symbols, 1):
        symbol = symbol_info['symbol']
        company_name = symbol_info['company_name']
        
        print(f"[{i}/{total_symbols}] Verifying {symbol}...", end=" ")
        
        yahoo_symbol, symbol_type = verify_yahoo_symbol(symbol)
        
        if yahoo_symbol:
            sector = categorize_symbol(symbol, company_name)
            save_mapping(symbol, yahoo_symbol, symbol_type, sector, company_name)
            print(f"OK -> {yahoo_symbol} ({sector})")
            successful += 1
        else:
            print("FAILED")
            failed += 1
        
        # Progress update every 25 symbols
        if i % 25 == 0:
            print(f"Progress: {i}/{total_symbols} ({(i/total_symbols)*100:.1f}%) - Success: {successful}, Failed: {failed}")
    
    # Final summary
    print(f"\n=== VERIFICATION COMPLETE ===")
    print(f"Total symbols processed: {total_symbols}")
    print(f"Successfully verified: {successful}")
    print(f"Failed to verify: {failed}")
    print(f"Success rate: {(successful/total_symbols)*100:.1f}%")
    
    # Get final count from database
    eng = engine()
    with eng.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1"))
        total_verified = result.scalar()
        
        result = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM nse_index_constituents"))
        total_in_db = result.scalar()
        
        print(f"\nDatabase Status:")
        print(f"Total symbols in database: {total_in_db}")
        print(f"Total verified mappings: {total_verified}")
        print(f"Overall completion: {(total_verified/total_in_db)*100:.1f}%")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)