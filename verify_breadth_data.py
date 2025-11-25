"""Check all advance/decline data for any zeros"""
from sqlalchemy import create_engine, text
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
eng = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    f"?charset=utf8mb4"
)

conn = eng.connect()
yesterday = date.today() - timedelta(days=1)

result = conn.execute(text("""
    SELECT poll_time, advances, declines, unchanged
    FROM intraday_advance_decline
    WHERE trade_date >= :yesterday
    ORDER BY poll_time
"""), {'yesterday': yesterday})

rows = result.fetchall()
print(f"Total rows: {len(rows)}\n")

zero_count = 0
for row in rows:
    if row[1] == 0 or row[2] == 0:
        print(f"⚠️  {row[0]} | Advances: {row[1]} | Declines: {row[2]} | Unchanged: {row[3]}")
        zero_count += 1

if zero_count == 0:
    print("✅ No zero values found in database")
    print("\nShowing last 10 rows:")
    for row in rows[-10:]:
        print(f"   {row[0]} | A:{row[1]} D:{row[2]} U:{row[3]}")
else:
    print(f"\n❌ Found {zero_count} rows with zeros in database!")

conn.close()
