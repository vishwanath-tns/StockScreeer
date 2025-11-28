"""
Verify NSE indices data download
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd
from urllib.parse import quote_plus

load_dotenv()

def get_engine():
    password = quote_plus(os.getenv('MYSQL_PASSWORD', 'rajat123'))
    return create_engine(
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
        f"{password}@"
        f"{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4"
    )

eng = get_engine()

print("=" * 100)
print("NSE INDICES DATA VERIFICATION")
print("=" * 100)

with eng.connect() as conn:
    # Total records
    result = conn.execute(text("SELECT COUNT(*) as total FROM yfinance_indices_daily_quotes"))
    total = result.fetchone()[0]
    print(f"\n📊 Total Records: {total:,}")
    
    # Per index summary
    result = conn.execute(text("""
        SELECT 
            m.index_name,
            m.yahoo_symbol,
            m.category,
            COUNT(q.id) as records,
            MIN(q.date) as first_date,
            MAX(q.date) as last_date,
            ROUND(AVG(q.volume), 0) as avg_volume
        FROM yfinance_indices_master m
        LEFT JOIN yfinance_indices_daily_quotes q ON m.yahoo_symbol = q.symbol
        GROUP BY m.id, m.index_name, m.yahoo_symbol, m.category
        ORDER BY m.category, m.index_name
    """))
    
    df = pd.DataFrame(result.fetchall(), columns=result.keys())
    
    print("\n" + "=" * 100)
    print("PER INDEX SUMMARY")
    print("=" * 100)
    
    for category in df['category'].unique():
        cat_df = df[df['category'] == category]
        print(f"\n🏷️  {category} ({len(cat_df)} indices)")
        print("-" * 100)
        for _, row in cat_df.iterrows():
            print(f"  {row['index_name']:30s} ({row['yahoo_symbol']:25s}) → {row['records']:5,} records | {row['first_date']} to {row['last_date']}")
    
    # Category summary
    print("\n" + "=" * 100)
    print("CATEGORY SUMMARY")
    print("=" * 100)
    
    result = conn.execute(text("""
        SELECT 
            m.category,
            COUNT(DISTINCT m.id) as indices_count,
            COUNT(q.id) as total_records,
            MIN(q.date) as earliest_date,
            MAX(q.date) as latest_date
        FROM yfinance_indices_master m
        LEFT JOIN yfinance_indices_daily_quotes q ON m.yahoo_symbol = q.symbol
        GROUP BY m.category
        ORDER BY m.category
    """))
    
    for row in result:
        print(f"\n  {row[0]:15s} → {row[1]:2d} indices | {row[2]:6,} records | {row[3]} to {row[4]}")
    
    print("\n" + "=" * 100)
    print("✅ Verification Complete!")
    print("=" * 100)
