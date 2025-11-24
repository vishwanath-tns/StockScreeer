"""
Check nse_yahoo_symbol_map for index mappings
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

print("=" * 80)
print("NSE to Yahoo Symbol Mapping - Indices")
print("=" * 80)

with engine.connect() as conn:
    # Check table structure
    result = conn.execute(text("DESCRIBE nse_yahoo_symbol_map"))
    print("\nTable Structure:")
    for row in result:
        print(f"  {row[0]:<20} {row[1]:<20}")
    
    # Get all index mappings
    result = conn.execute(text("""
        SELECT nse_symbol, yahoo_symbol, company_name, is_active
        FROM nse_yahoo_symbol_map
        WHERE nse_symbol LIKE 'NIFTY%' OR nse_symbol IN ('SENSEX', 'BANKNIFTY', 'IOCL')
        ORDER BY nse_symbol
    """))
    
    indices = result.fetchall()
    if indices:
        print(f"\n\nFound {len(indices)} index mappings:")
        print(f"{'NSE Symbol':<20} {'Yahoo Symbol':<20} {'Name':<40} {'Active'}")
        print("-" * 100)
        for nse, yahoo, name, active in indices:
            name_str = name if name else "N/A"
            print(f"{nse:<20} {yahoo:<20} {name_str:<40} {active}")
    else:
        print("\n❌ No index mappings found")
    
    # Check for failed symbols from previous download
    print("\n" + "=" * 80)
    print("Checking failed symbols in yfinance_daily_quotes")
    print("=" * 80)
    
    failed = ['BANKNIFTY', 'NIFTY', 'SENSEX', 'IOCL', 'TATAMOTORS']
    for symbol in failed:
        result = conn.execute(text("""
            SELECT yahoo_symbol FROM nse_yahoo_symbol_map 
            WHERE nse_symbol = :symbol AND is_active = 1
        """), {'symbol': symbol})
        row = result.fetchone()
        if row:
            print(f"✅ {symbol:<20} → {row[0]}")
        else:
            print(f"❌ {symbol:<20} → Not mapped")
