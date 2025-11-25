"""Check for zero values in advance/decline data"""
from sqlalchemy import create_engine, text
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Create engine
password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
eng = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    f"?charset=utf8mb4"
)

conn = eng.connect()
today = date.today()
yesterday = today - timedelta(days=1)

# Check for rows with zero advances or declines
result = conn.execute(text("""
    SELECT poll_time, trade_date, advances, declines, unchanged
    FROM intraday_advance_decline
    WHERE trade_date >= :yesterday
      AND (advances = 0 OR declines = 0)
    ORDER BY poll_time
"""), {'yesterday': yesterday})

rows = result.fetchall()

if rows:
    print(f"Found {len(rows)} rows with zero values:\n")
    for row in rows:
        print(f"  {row[0]} | Date: {row[1]} | Advances: {row[2]} | Declines: {row[3]} | Unchanged: {row[4]}")
    
    print(f"\n🗑️  Would you like to delete these {len(rows)} invalid rows? (y/n)")
else:
    print("✅ No rows found with zero advances or declines")

conn.close()
