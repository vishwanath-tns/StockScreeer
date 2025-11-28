"""
Add index mappings to nse_yahoo_symbol_map table
"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv()

url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    database=os.getenv('MYSQL_DB', 'marketdata'),
    query={"charset": "utf8mb4"}
)
engine = create_engine(url, pool_pre_ping=True)

# Index mappings
indices_mapping = [
    ('NIFTY', '^NSEI', 'NIFTY 50'),
    ('BANKNIFTY', '^NSEBANK', 'NIFTY BANK'),
    ('SENSEX', '^BSESN', 'BSE SENSEX'),
]

print("=" * 80)
print("Adding Index Mappings to nse_yahoo_symbol_map")
print("=" * 80)

with engine.begin() as conn:
    for nse_symbol, yahoo_symbol, name in indices_mapping:
        # Check if mapping already exists
        result = conn.execute(text("""
            SELECT id, yahoo_symbol FROM nse_yahoo_symbol_map 
            WHERE nse_symbol = :nse_symbol
        """), {'nse_symbol': nse_symbol})
        
        existing = result.fetchone()
        
        if existing:
            print(f"✅ {nse_symbol:<15} → {existing[1]:<15} (already exists, ID: {existing[0]})")
        else:
            # Insert new mapping
            conn.execute(text("""
                INSERT INTO nse_yahoo_symbol_map 
                (nse_symbol, yahoo_symbol, company_name, is_active, is_verified, last_verified)
                VALUES (:nse, :yahoo, :name, 1, 1, CURDATE())
            """), {'nse': nse_symbol, 'yahoo': yahoo_symbol, 'name': name})
            print(f"➕ {nse_symbol:<15} → {yahoo_symbol:<15} (added)")

print("\n" + "=" * 80)
print("Verification")
print("=" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, company_name, is_active
        FROM nse_yahoo_symbol_map
        WHERE nse_symbol IN ('NIFTY', 'BANKNIFTY', 'SENSEX', 'NIFTY50', 'IOCL', 'TATAMOTORS')
        ORDER BY nse_symbol
    """))
    
    print(f"\n{'NSE Symbol':<20} {'Yahoo Symbol':<20} {'Name':<40} {'Active'}")
    print("-" * 100)
    for nse, yahoo, name, active in result:
        name_str = name if name else "N/A"
        print(f"{nse:<20} {yahoo:<20} {name_str:<40} {active}")

print("\n✅ Index mappings added successfully!")
