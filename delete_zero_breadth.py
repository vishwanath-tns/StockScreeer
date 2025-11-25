"""Delete rows with zero advances or declines"""
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

today = date.today()
yesterday = today - timedelta(days=1)

with eng.begin() as conn:
    # Check count before delete
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM intraday_advance_decline
        WHERE trade_date >= :yesterday
          AND (advances = 0 OR declines = 0)
    """), {'yesterday': yesterday})
    
    count = result.fetchone()[0]
    print(f"Found {count} rows with zero values")
    
    if count > 0:
        # Delete them
        result = conn.execute(text("""
            DELETE FROM intraday_advance_decline
            WHERE trade_date >= :yesterday
              AND (advances = 0 OR declines = 0)
        """), {'yesterday': yesterday})
        
        print(f"✅ Deleted {count} invalid rows")
    else:
        print("✅ No invalid rows to delete")

print("\nDone! Restart the dashboard to see clean data.")
