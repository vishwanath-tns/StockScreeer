"""
Fix TATAMOTORS mapping by removing old entry
Since TMCV already maps to TMCV.NS (which is correct), 
we just need to deactivate the old TATAMOTORS entry
"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv()

def create_db_engine():
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        database=os.getenv('MYSQL_DB', 'marketdata'),
        query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True)

engine = create_db_engine()

print("=" * 80)
print("FIXING TATAMOTORS SYMBOL MAPPING")
print("=" * 80)

with engine.begin() as conn:
    # Check current state
    print("\n📋 Current mappings:")
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('TATAMOTORS', 'TMCV')
        ORDER BY nse_symbol
    """))
    for nse_sym, yahoo_sym, is_active in result:
        print(f"  {nse_sym:<15} -> {yahoo_sym:<20} (active: {is_active})")
    
    # Deactivate TATAMOTORS (old symbol that points to TATAMOTORS.NS)
    print("\n🔄 Deactivating old TATAMOTORS entry...")
    result = conn.execute(text("""
        UPDATE nse_yahoo_symbol_map 
        SET is_active = 0, updated_at = NOW()
        WHERE nse_symbol = 'TATAMOTORS'
    """))
    
    if result.rowcount > 0:
        print(f"  ✅ Deactivated TATAMOTORS entry ({result.rowcount} row(s))")
    else:
        print(f"  ⚠️  No rows updated")
    
    # Verify final state
    print("\n✓ Final mappings:")
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('TATAMOTORS', 'TMCV')
        ORDER BY nse_symbol
    """))
    for nse_sym, yahoo_sym, is_active in result:
        if is_active:
            print(f"  ✅ {nse_sym:<15} -> {yahoo_sym:<20} (active: {is_active})")
        else:
            print(f"  ⚠️  {nse_sym:<15} -> {yahoo_sym:<20} (active: {is_active})")

print("\n" + "=" * 80)
print("✅ TATAMOTORS MAPPING FIXED")
print("=" * 80)
print("\nOld TATAMOTORS symbol has been deactivated.")
print("Use TMCV symbol (which correctly maps to TMCV.NS) going forward.")
print("Both TATAMOTORS and TMCV are the same company after symbol change.")
