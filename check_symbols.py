from load_verified_symbols import *
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import os
from dotenv import load_dotenv

load_dotenv()
url = URL.create(
    "mysql+pymysql",
    os.getenv("MYSQL_USER", "root"),
    os.getenv("MYSQL_PASSWORD", ""),
    os.getenv("MYSQL_HOST", "127.0.0.1"),
    int(os.getenv("MYSQL_PORT", 3306)),
    os.getenv("MYSQL_DB", "marketdata"),
    {"charset": "utf8mb4"}
)

eng = create_engine(url)
conn = eng.connect()

# Check counts
r = conn.execute(text("""
    SELECT 
        COUNT(*) as total,
        SUM(is_active=1) as active,
        SUM(is_verified=1) as verified,
        SUM(is_active=1 AND is_verified=1) as both_active_verified,
        SUM(is_active=1 OR is_verified=1) as either_active_or_verified
    FROM nse_yahoo_symbol_map
"""))
row = r.fetchone()
print(f"Total symbols: {row[0]}")
print(f"Active only: {row[1]}")
print(f"Verified only: {row[2]}")
print(f"Both active AND verified: {row[3]}")
print(f"Active OR verified: {row[4]}")

# Check sample of non-selected symbols
r = conn.execute(text("""
    SELECT nse_symbol, yahoo_symbol, is_active, is_verified
    FROM nse_yahoo_symbol_map
    WHERE NOT (is_active=1 AND is_verified=1)
    LIMIT 10
"""))
print("\nSample of excluded symbols:")
for row in r.fetchall():
    print(f"  {row[0]} -> {row[1]} (active={row[2]}, verified={row[3]})")
