"""
Final update for TATAMOTORS symbol mapping
Simply update TATAMOTORS to point to TMCV.NS (which is the new symbol)
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
print("UPDATING TATAMOTORS SYMBOL MAPPING")
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
    
    # Update TATAMOTORS to point to TMCV.NS
    print("\n🔄 Updating TATAMOTORS -> TMCV.NS...")
    result = conn.execute(text("""
        UPDATE nse_yahoo_symbol_map 
        SET yahoo_symbol = 'TMCV.NS', 
            company_name = 'Tata Motors Limited',
            updated_at = NOW()
        WHERE nse_symbol = 'TATAMOTORS'
    """))
    
    if result.rowcount > 0:
        print(f"  ✅ Updated TATAMOTORS to use TMCV.NS ({result.rowcount} row(s))")
    else:
        print(f"  ⚠️  No rows updated")
    
    # Verify
    print("\n✓ Verified mappings:")
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('TATAMOTORS', 'TMCV')
        ORDER BY nse_symbol
    """))
    for nse_sym, yahoo_sym, is_active in result:
        status = "✅" if yahoo_sym == 'TMCV.NS' else "⚠️"
        print(f"  {status} {nse_sym:<15} -> {yahoo_sym:<20} (active: {is_active})")

print("\n" + "=" * 80)
print("✅ TATAMOTORS MAPPING UPDATED")
print("=" * 80)
print("\nNow both TATAMOTORS and TMCV point to TMCV.NS")
print("This ensures compatibility with old and new symbol names")
