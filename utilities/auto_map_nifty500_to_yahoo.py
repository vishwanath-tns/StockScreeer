#!/usr/bin/env python3
"""
Auto-map missing Nifty 500 symbols to Yahoo Finance with .NS suffix
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sync_bhav_gui import engine
from sqlalchemy import text

def auto_map_missing_nifty500():
    """Auto-map all missing Nifty 500 symbols with .NS suffix"""
    
    conn = engine().connect()
    
    # Get unmapped Nifty 500 symbols
    result = conn.execute(text("""
        SELECT DISTINCT n.symbol
        FROM nse_index_constituents n
        LEFT JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol
        WHERE n.index_id = 25 
        AND m.nse_symbol IS NULL
        ORDER BY n.symbol
    """))
    
    unmapped_symbols = [row[0] for row in result.fetchall()]
    
    if not unmapped_symbols:
        print("✅ All Nifty 500 symbols are already mapped!")
        conn.close()
        return 0
    
    print(f"Found {len(unmapped_symbols)} unmapped Nifty 500 symbols")
    print("\nWill map with .NS suffix (e.g., RELIANCE → RELIANCE.NS)")
    print(f"\n{'='*100}")
    
    # Show first 10 as preview
    print("Preview of mappings:")
    for symbol in unmapped_symbols[:10]:
        print(f"  {symbol:<15} → {symbol}.NS")
    if len(unmapped_symbols) > 10:
        print(f"  ... and {len(unmapped_symbols) - 10} more")
    
    print(f"\n{'='*100}")
    response = input(f"\nProceed to map {len(unmapped_symbols)} symbols? (y/n): ").strip().lower()
    
    if response != 'y':
        print("❌ Cancelled by user")
        conn.close()
        return 1
    
    # Close and reopen connection for fresh transaction
    conn.close()
    conn = engine().connect()
    
    # Start mapping
    trans = conn.begin()
    
    try:
        mapped_count = 0
        
        for symbol in unmapped_symbols:
            yahoo_symbol = f"{symbol}.NS"
            
            # Get company name if available
            company_result = conn.execute(text("""
                SELECT company_name 
                FROM nse_index_constituents 
                WHERE symbol = :symbol AND index_id = 25 
                LIMIT 1
            """), {'symbol': symbol})
            
            company_row = company_result.fetchone()
            company_name = company_row[0] if company_row else None
            
            # Insert mapping
            conn.execute(text("""
                INSERT INTO nse_yahoo_symbol_map 
                (nse_symbol, yahoo_symbol, company_name, sector, 
                 is_verified, is_active, created_at)
                VALUES (:nse, :yahoo, :company, 'NIFTY_500',
                        FALSE, TRUE, NOW())
                ON DUPLICATE KEY UPDATE
                    yahoo_symbol = VALUES(yahoo_symbol),
                    is_active = TRUE,
                    updated_at = NOW()
            """), {
                'nse': symbol,
                'yahoo': yahoo_symbol,
                'company': company_name
            })
            
            mapped_count += 1
            
            if mapped_count % 50 == 0:
                print(f"  Mapped {mapped_count}/{len(unmapped_symbols)}...")
        
        trans.commit()
        
        print(f"\n✅ Successfully mapped {mapped_count} symbols!")
        print(f"\n{'='*100}")
        print("NEXT STEPS:")
        print("1. Verify mappings: python yahoo_finance_service/validate_symbol_mapping.py")
        print("2. Download data: python yahoo_finance_service/yfinance_downloader_gui.py")
        print(f"{'='*100}\n")
        
        # Show updated statistics
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN m.nse_symbol IS NOT NULL THEN 1 ELSE 0 END) as mapped
            FROM nse_index_constituents n
            LEFT JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol
            WHERE n.index_id = 25
        """))
        
        stats = result.fetchone()
        if stats:
            coverage = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
            print(f"Updated Coverage: {stats[1]}/{stats[0]} ({coverage:.1f}%)")
        
        conn.close()
        return 0
        
    except Exception as e:
        trans.rollback()
        print(f"\n❌ Error during mapping: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return 1

if __name__ == '__main__':
    sys.exit(auto_map_missing_nifty500())
