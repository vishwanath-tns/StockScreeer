"""
Check Index Symbols Download Status for 25-Nov-2025
"""
from sync_bhav_gui import engine
from sqlalchemy import text

def check_indices_status():
    conn = engine().connect()
    
    # Get all index symbols from mapping table (indices start with ^)
    print("=" * 80)
    print("INDEX SYMBOLS IN nse_yahoo_symbol_map")
    print("=" * 80)
    
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active, is_verified 
        FROM nse_yahoo_symbol_map 
        WHERE yahoo_symbol LIKE '^%'
        ORDER BY nse_symbol
    """))
    
    indices = result.fetchall()
    
    print(f"\n{'NSE Symbol':<25} {'Yahoo Symbol':<25} {'Active':<10} {'Verified':<10}")
    print("-" * 80)
    for row in indices:
        print(f"{row[0]:<25} {row[1]:<25} {'Yes' if row[2] else 'No':<10} {'Yes' if row[3] else 'No':<10}")
    
    print(f"\nTotal index symbols in mapping: {len(indices)}")
    
    # Check data availability for 25-Nov-2025
    print("\n" + "=" * 80)
    print("DATA AVAILABILITY CHECK FOR 25-NOV-2025")
    print("=" * 80)
    
    print(f"\n{'NSE Symbol':<25} {'Yahoo Symbol':<25} {'Active':<10} {'25-Nov':<10} {'26-Nov':<10}")
    print("-" * 90)
    
    missing_25 = []
    missing_26 = []
    
    # Check each index symbol individually to avoid collation issues
    for nse_sym, yahoo_sym, is_active, is_verified in indices:
        # Check 25-Nov
        result = conn.execute(text("""
            SELECT COUNT(*) FROM yfinance_daily_quotes 
            WHERE symbol = :sym AND date = '2025-11-25'
        """), {'sym': yahoo_sym})
        has_25 = 'Yes' if result.scalar() > 0 else 'No'
        
        # Check 26-Nov
        result = conn.execute(text("""
            SELECT COUNT(*) FROM yfinance_daily_quotes 
            WHERE symbol = :sym AND date = '2025-11-26'
        """), {'sym': yahoo_sym})
        has_26 = 'Yes' if result.scalar() > 0 else 'No'
        
        active_str = 'Yes' if is_active else 'No'
        print(f"{nse_sym:<25} {yahoo_sym:<25} {active_str:<10} {has_25:<10} {has_26:<10}")
        
        if is_active and has_25 == 'No':
            missing_25.append((nse_sym, yahoo_sym))
        if is_active and has_26 == 'No':
            missing_26.append((nse_sym, yahoo_sym))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    active_count = sum(1 for row in indices if row[2])
    print(f"Total index symbols: {len(indices)}")
    print(f"Active index symbols: {active_count}")
    print(f"Missing data for 25-Nov-2025: {len(missing_25)}")
    print(f"Missing data for 26-Nov-2025: {len(missing_26)}")
    
    if missing_25:
        print("\n⚠️  INDICES MISSING DATA FOR 25-NOV-2025:")
        for nse_sym, yahoo_sym in missing_25:
            print(f"  - {nse_sym} ({yahoo_sym})")
    
    if missing_26:
        print("\n⚠️  INDICES MISSING DATA FOR 26-NOV-2025:")
        for nse_sym, yahoo_sym in missing_26:
            print(f"  - {nse_sym} ({yahoo_sym})")
    
    # Check what data actually exists for these dates
    print("\n" + "=" * 80)
    print("ACTUAL INDEX DATA IN DATABASE")
    print("=" * 80)
    
    result = conn.execute(text("""
        SELECT 
            DATE(date) as trade_date,
            COUNT(DISTINCT symbol) as symbol_count
        FROM yfinance_daily_quotes
        WHERE symbol LIKE '^%'
        AND date >= '2025-11-25'
        GROUP BY DATE(date)
        ORDER BY trade_date DESC
    """))
    
    print(f"\n{'Date':<15} {'Index Count':<15}")
    print("-" * 30)
    for row in result:
        print(f"{str(row[0]):<15} {row[1]:<15}")
    
    conn.close()

if __name__ == "__main__":
    check_indices_status()
