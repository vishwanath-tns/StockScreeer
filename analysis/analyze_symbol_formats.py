"""
Quick analysis of symbol formats in yfinance_daily_quotes
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

with engine.connect() as conn:
    # Count symbols with .NS suffix
    result = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT symbol) as total_symbols,
            SUM(CASE WHEN symbol LIKE '%.NS' THEN 1 ELSE 0 END) as with_ns_suffix,
            SUM(CASE WHEN symbol LIKE '^%' THEN 1 ELSE 0 END) as indices,
            SUM(CASE WHEN symbol NOT LIKE '%.NS' AND symbol NOT LIKE '^%' THEN 1 ELSE 0 END) as without_ns_suffix
        FROM (SELECT DISTINCT symbol FROM yfinance_daily_quotes) s
    """))
    
    row = result.fetchone()
    print(f"Total unique symbols: {row[0]}")
    print(f"With .NS suffix: {row[1]}")
    print(f"Indices (^): {row[2]}")
    print(f"Without .NS suffix: {row[3]}")
    
    # Check for duplicates
    print("\n" + "="*60)
    print("Checking for duplicate symbols (with and without .NS):")
    result = conn.execute(text("""
        SELECT 
            CASE 
                WHEN symbol LIKE '%.NS' THEN REPLACE(symbol, '.NS', '')
                ELSE symbol
            END as base_symbol,
            GROUP_CONCAT(symbol ORDER BY symbol) as all_versions,
            COUNT(*) as version_count
        FROM (SELECT DISTINCT symbol FROM yfinance_daily_quotes WHERE symbol NOT LIKE '^%') s
        GROUP BY base_symbol
        HAVING version_count > 1
        LIMIT 20
    """))
    
    duplicates = result.fetchall()
    if duplicates:
        print(f"\nFound {len(duplicates)} symbols with multiple versions:")
        for base, versions, count in duplicates[:10]:
            print(f"  {base}: {versions} ({count} versions)")
    else:
        print("No duplicates found")
