#!/usr/bin/env python3
"""
Check if all Nifty 500 constituent symbols are mapped to Yahoo Finance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sync_bhav_gui import engine
from sqlalchemy import text

def check_nifty500_mapping():
    """Check which Nifty 500 symbols are mapped and which are missing"""
    
    conn = engine().connect()
    
    print("=" * 100)
    print("NIFTY 500 SYMBOL MAPPING ANALYSIS")
    print("=" * 100)
    
    # Get all Nifty 500 constituents
    result = conn.execute(text("""
        SELECT DISTINCT symbol 
        FROM nse_index_constituents 
        WHERE index_id = 25
        ORDER BY symbol
    """))
    
    nifty500_symbols = [row[0] for row in result.fetchall()]
    total_nifty500 = len(nifty500_symbols)
    
    print(f"\nTotal Nifty 500 constituents: {total_nifty500}")
    
    # Check which are mapped in nse_yahoo_symbol_map
    result = conn.execute(text("""
        SELECT n.symbol,
               m.yahoo_symbol,
               m.is_verified,
               m.is_active,
               m.last_verified
        FROM nse_index_constituents n
        LEFT JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol
        WHERE n.index_id = 25
        ORDER BY n.symbol
    """))
    
    mapping_data = result.fetchall()
    
    # Categorize symbols
    mapped_verified = []
    mapped_unverified = []
    not_mapped = []
    
    for row in mapping_data:
        symbol = row[0]
        yahoo_symbol = row[1]
        is_verified = row[2]
        is_active = row[3]
        last_verified = row[4]
        
        if yahoo_symbol:
            if is_verified:
                mapped_verified.append((symbol, yahoo_symbol, last_verified))
            else:
                mapped_unverified.append((symbol, yahoo_symbol))
        else:
            not_mapped.append(symbol)
    
    # Statistics
    print(f"\n{'='*100}")
    print("MAPPING STATISTICS")
    print(f"{'='*100}")
    print(f"✅ Mapped & Verified:   {len(mapped_verified):4d} ({len(mapped_verified)/total_nifty500*100:5.1f}%)")
    print(f"⚠️  Mapped (Unverified): {len(mapped_unverified):4d} ({len(mapped_unverified)/total_nifty500*100:5.1f}%)")
    print(f"❌ Not Mapped:          {len(not_mapped):4d} ({len(not_mapped)/total_nifty500*100:5.1f}%)")
    print(f"{'='*100}")
    
    # Show mapped & verified symbols
    if mapped_verified:
        print(f"\n✅ MAPPED & VERIFIED ({len(mapped_verified)} symbols)")
        print(f"{'='*100}")
        print(f"{'NSE Symbol':<15} {'Yahoo Symbol':<20} {'Last Verified':<15}")
        print("-" * 100)
        for symbol, yahoo_symbol, last_verified in mapped_verified[:20]:  # Show first 20
            verified_str = str(last_verified) if last_verified else 'N/A'
            print(f"{symbol:<15} {yahoo_symbol:<20} {verified_str:<15}")
        if len(mapped_verified) > 20:
            print(f"... and {len(mapped_verified) - 20} more")
    
    # Show unverified mappings
    if mapped_unverified:
        print(f"\n⚠️  MAPPED BUT UNVERIFIED ({len(mapped_unverified)} symbols)")
        print(f"{'='*100}")
        print(f"{'NSE Symbol':<15} {'Yahoo Symbol':<20}")
        print("-" * 100)
        for symbol, yahoo_symbol in mapped_unverified[:20]:  # Show first 20
            print(f"{symbol:<15} {yahoo_symbol:<20}")
        if len(mapped_unverified) > 20:
            print(f"... and {len(mapped_unverified) - 20} more")
    
    # Show unmapped symbols
    if not_mapped:
        print(f"\n❌ NOT MAPPED ({len(not_mapped)} symbols)")
        print(f"{'='*100}")
        print("These symbols need to be added to the mapping table:")
        print("-" * 100)
        
        # Display in columns
        cols = 5
        for i in range(0, len(not_mapped), cols):
            row_symbols = not_mapped[i:i+cols]
            print("  ".join(f"{s:<15}" for s in row_symbols))
    
    # Check if there are symbols in yfinance_daily_quotes that we can use
    if not_mapped:
        print(f"\n{'='*100}")
        print("CHECKING EXISTING YAHOO FINANCE DATA")
        print(f"{'='*100}")
        
        # Check which unmapped symbols already have data in yfinance_daily_quotes
        placeholders = ','.join([':sym' + str(i) for i in range(len(not_mapped))])
        params = {f'sym{i}': sym for i, sym in enumerate(not_mapped)}
        
        result = conn.execute(text(f"""
            SELECT DISTINCT symbol
            FROM yfinance_daily_quotes
            WHERE symbol IN ({placeholders})
            ORDER BY symbol
        """), params)
        
        existing_in_yfinance = [row[0] for row in result.fetchall()]
        
        if existing_in_yfinance:
            print(f"\n✨ Found {len(existing_in_yfinance)} unmapped symbols that ALREADY have Yahoo Finance data!")
            print("These can be auto-mapped (NSE symbol = Yahoo symbol):")
            print("-" * 100)
            cols = 5
            for i in range(0, len(existing_in_yfinance), cols):
                row_symbols = existing_in_yfinance[i:i+cols]
                print("  ".join(f"{s:<15}" for s in row_symbols))
            
            # Ask if user wants to auto-map them
            print("\n" + "="*100)
            response = input(f"Auto-map these {len(existing_in_yfinance)} symbols? (y/n): ").strip().lower()
            
            if response == 'y':
                trans = conn.begin()
                try:
                    mapped_count = 0
                    for symbol in existing_in_yfinance:
                        conn.execute(text("""
                            INSERT INTO nse_yahoo_symbol_map 
                            (nse_symbol, yahoo_symbol, company_name, is_verified, is_active, notes)
                            VALUES (:nse, :yahoo, 
                                    (SELECT company_name FROM nse_index_constituents 
                                     WHERE symbol = :nse AND index_id = 25 LIMIT 1),
                                    FALSE, TRUE, 'Auto-mapped from existing yfinance data')
                            ON DUPLICATE KEY UPDATE
                                yahoo_symbol = VALUES(yahoo_symbol),
                                notes = VALUES(notes)
                        """), {'nse': symbol, 'yahoo': symbol})
                        mapped_count += 1
                    
                    trans.commit()
                    print(f"\n✅ Successfully auto-mapped {mapped_count} symbols!")
                    
                    # Re-run the statistics
                    print("\n" + "="*100)
                    print("UPDATED STATISTICS AFTER AUTO-MAPPING")
                    print("="*100)
                    conn.close()
                    conn = engine().connect()
                    check_nifty500_mapping()
                    return
                    
                except Exception as e:
                    trans.rollback()
                    print(f"\n❌ Error during auto-mapping: {e}")
        else:
            print("\n⚠️  None of the unmapped symbols have data in yfinance_daily_quotes")
            print("They need manual mapping with proper Yahoo Finance symbols (e.g., SYMBOL.NS)")
    
    # Summary and recommendations
    print(f"\n{'='*100}")
    print("RECOMMENDATIONS")
    print(f"{'='*100}")
    
    coverage_percent = (len(mapped_verified) + len(mapped_unverified)) / total_nifty500 * 100
    
    if coverage_percent == 100:
        print("✅ All Nifty 500 symbols are mapped!")
        if mapped_unverified:
            print(f"⚠️  However, {len(mapped_unverified)} symbols are not yet verified.")
            print("   Run: python yahoo_finance_service/validate_symbol_mapping.py")
    elif coverage_percent >= 90:
        print(f"✅ Good coverage: {coverage_percent:.1f}% of Nifty 500 symbols are mapped")
        if not_mapped:
            print(f"📝 {len(not_mapped)} symbols still need mapping")
            print("   Add them using: python yahoo_finance_service/create_symbol_mapping.py")
    else:
        print(f"⚠️  Low coverage: Only {coverage_percent:.1f}% of Nifty 500 symbols are mapped")
        print(f"📝 {len(not_mapped)} symbols need mapping urgently")
        print("   1. Add mappings using: python yahoo_finance_service/create_symbol_mapping.py")
        print("   2. Or use auto-download feature in yfinance_downloader_gui.py")
    
    if mapped_unverified:
        print(f"\n🔍 {len(mapped_unverified)} mapped symbols need verification")
        print("   Run: python yahoo_finance_service/validate_symbol_mapping.py")
    
    print(f"\n{'='*100}\n")
    
    conn.close()

def main():
    """Main entry point"""
    try:
        check_nifty500_mapping()
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
