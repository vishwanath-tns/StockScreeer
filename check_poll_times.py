from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import pytz

load_dotenv()
engine = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}",
    echo=False
)

ist = pytz.timezone('Asia/Kolkata')
today = datetime.now(ist).date()
yesterday = today - timedelta(days=1)

print(f"Yesterday: {yesterday}")
print(f"Today: {today}")
print()

with engine.connect() as conn:
    # Check breadth data for yesterday
    result = conn.execute(text('''
        SELECT MIN(poll_time) as first_poll, MAX(poll_time) as last_poll, COUNT(*) as count
        FROM intraday_advance_decline
        WHERE trade_date = :yesterday
    '''), {'yesterday': yesterday})
    row = result.fetchone()
    print(f'Yesterday breadth: First={row[0]}, Last={row[1]}, Count={row[2]}')
    
    # Check breadth data for today
    result = conn.execute(text('''
        SELECT MIN(poll_time) as first_poll, MAX(poll_time) as last_poll, COUNT(*) as count
        FROM intraday_advance_decline
        WHERE trade_date = :today
    '''), {'today': today})
    row = result.fetchone()
    print(f'Today breadth: First={row[0]}, Last={row[1]}, Count={row[2]}')
    
    # Check last few entries from yesterday
    print("\nLast 5 entries from yesterday:")
    result = conn.execute(text('''
        SELECT poll_time, advances, declines
        FROM intraday_advance_decline
        WHERE trade_date = :yesterday
        ORDER BY poll_time DESC
        LIMIT 5
    '''), {'yesterday': yesterday})
    for row in result:
        print(f"  {row[0]} - Adv:{row[1]}, Dec:{row[2]}")
    
    # Check first few entries from today
    print("\nFirst 5 entries from today:")
    result = conn.execute(text('''
        SELECT poll_time, advances, declines
        FROM intraday_advance_decline
        WHERE trade_date = :today
        ORDER BY poll_time
        LIMIT 5
    '''), {'today': today})
    for row in result:
        print(f"  {row[0]} - Adv:{row[1]}, Dec:{row[2]}")
