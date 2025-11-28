"""
Update NSE-Yahoo Symbol Mappings for Indices and TATAMOTORS
Fixed to use correct table schema (no symbol_type column)
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
print("CHECKING NSE-YAHOO SYMBOL MAPPINGS")
print("=" * 80)

with engine.connect() as conn:
    # Check if table exists
    result = conn.execute(text("SHOW TABLES LIKE 'nse_yahoo_symbol_map'"))
    if not result.fetchone():
        print("❌ Table nse_yahoo_symbol_map does not exist")
        exit(1)
    
    # Check current mappings for indices
    print("\n📊 Current Index Mappings:")
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('NIFTY', 'BANKNIFTY', 'SENSEX', 'NIFTY BANK')
        ORDER BY nse_symbol
    """))
    
    indices = result.fetchall()
    if indices:
        for nse_sym, yahoo_sym, is_active in indices:
            print(f"  {nse_sym:<15} -> {yahoo_sym:<15} (active: {is_active})")
    else:
        print("  ⚠️  No index mappings found")
    
    # Check TATAMOTORS mapping
    print("\n🚗 TATAMOTORS Mapping:")
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('TATAMOTORS', 'TMCV')
        ORDER BY nse_symbol
    """))
    
    tatamotors = result.fetchall()
    if tatamotors:
        for nse_sym, yahoo_sym, is_active in tatamotors:
            print(f"  {nse_sym:<15} -> {yahoo_sym:<15} (active: {is_active})")
    else:
        print("  ⚠️  No TATAMOTORS mapping found")

print("\n" + "=" * 80)
print("UPDATING MAPPINGS")
print("=" * 80)

# Index mappings that should exist (using company_name field instead of symbol_type)
index_mappings = [
    ('NIFTY', '^NSEI', 'Nifty 50 Index'),
    ('BANKNIFTY', '^NSEBANK', 'Nifty Bank Index'),
    ('NIFTY BANK', '^NSEBANK', 'Nifty Bank Index'),  # Alias for BANKNIFTY
    ('SENSEX', '^BSESN', 'S&P BSE Sensex'),
]

with engine.begin() as conn:
    # Update/Insert index mappings
    print("\n🔄 Updating index mappings...")
    for nse_symbol, yahoo_symbol, company_name in index_mappings:
        result = conn.execute(text("""
            INSERT INTO nse_yahoo_symbol_map 
            (nse_symbol, yahoo_symbol, company_name, is_active, updated_at)
            VALUES (:nse_symbol, :yahoo_symbol, :company_name, 1, NOW())
            ON DUPLICATE KEY UPDATE 
            yahoo_symbol = VALUES(yahoo_symbol),
            company_name = VALUES(company_name),
            is_active = 1,
            updated_at = NOW()
        """), {
            'nse_symbol': nse_symbol,
            'yahoo_symbol': yahoo_symbol,
            'company_name': company_name
        })
        print(f"  ✅ Updated: {nse_symbol} -> {yahoo_symbol}")
    
    # Deactivate old TATAMOTORS mapping
    print("\n🔄 Deactivating old TATAMOTORS mapping...")
    result = conn.execute(text("""
        UPDATE nse_yahoo_symbol_map 
        SET is_active = 0, updated_at = NOW()
        WHERE nse_symbol = 'TATAMOTORS' AND yahoo_symbol = 'TATAMOTORS.NS'
    """))
    if result.rowcount > 0:
        print(f"  ⚠️  Deactivated: TATAMOTORS -> TATAMOTORS.NS")
    else:
        print(f"  ℹ️  No old TATAMOTORS.NS mapping found to deactivate")
    
    # Add/Update new TATAMOTORS -> TMCV.NS mapping
    print("\n🔄 Updating TATAMOTORS -> TMCV.NS mapping...")
    conn.execute(text("""
        INSERT INTO nse_yahoo_symbol_map 
        (nse_symbol, yahoo_symbol, company_name, is_active, updated_at)
        VALUES ('TATAMOTORS', 'TMCV.NS', 'Tata Motors Limited', 1, NOW())
        ON DUPLICATE KEY UPDATE 
        yahoo_symbol = 'TMCV.NS',
        company_name = 'Tata Motors Limited',
        is_active = 1,
        updated_at = NOW()
    """))
    print(f"  ✅ Updated: TATAMOTORS -> TMCV.NS")
    
    # Also add TMCV as alias
    print("\n🔄 Adding TMCV alias...")
    conn.execute(text("""
        INSERT INTO nse_yahoo_symbol_map 
        (nse_symbol, yahoo_symbol, company_name, is_active, updated_at)
        VALUES ('TMCV', 'TMCV.NS', 'Tata Motors Limited', 1, NOW())
        ON DUPLICATE KEY UPDATE 
        yahoo_symbol = 'TMCV.NS',
        company_name = 'Tata Motors Limited',
        is_active = 1,
        updated_at = NOW()
    """))
    print(f"  ✅ Updated: TMCV -> TMCV.NS")

print("\n" + "=" * 80)
print("VERIFYING UPDATES")
print("=" * 80)

with engine.connect() as conn:
    # Verify index mappings
    print("\n📊 Verified Index Mappings:")
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('NIFTY', 'BANKNIFTY', 'SENSEX', 'NIFTY BANK')
        ORDER BY nse_symbol
    """))
    
    for nse_sym, yahoo_sym, is_active in result:
        status = "✅" if is_active else "⚠️"
        print(f"  {status} {nse_sym:<15} -> {yahoo_sym:<15} (active: {is_active})")
    
    # Verify TATAMOTORS mappings
    print("\n🚗 Verified TATAMOTORS Mappings:")
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, is_active 
        FROM nse_yahoo_symbol_map 
        WHERE nse_symbol IN ('TATAMOTORS', 'TMCV')
        ORDER BY nse_symbol, is_active DESC
    """))
    
    for nse_sym, yahoo_sym, is_active in result:
        status = "✅" if is_active else "⚠️"
        print(f"  {status} {nse_sym:<15} -> {yahoo_sym:<15} (active: {is_active})")

print("\n" + "=" * 80)
print("✅ SYMBOL MAPPINGS UPDATED SUCCESSFULLY")
print("=" * 80)
