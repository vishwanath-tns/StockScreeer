"""Quick script to create nifty500_advance_decline table"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import os
from dotenv import load_dotenv

load_dotenv()

url = URL.create(
    drivername='mysql+pymysql',
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DB', 'marketdata'),
    query={'charset': 'utf8mb4'}
)

engine = create_engine(url)
conn = engine.connect()

# Drop if exists
try:
    conn.execute(text('DROP TABLE IF EXISTS nifty500_advance_decline'))
    conn.commit()
    print("Dropped existing table")
except:
    pass

# Create table
create_sql = """
CREATE TABLE nifty500_advance_decline (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    advances INT NOT NULL DEFAULT 0,
    declines INT NOT NULL DEFAULT 0,
    unchanged INT NOT NULL DEFAULT 0,
    total_stocks INT NOT NULL DEFAULT 0,
    advance_pct DECIMAL(5,2) NULL,
    decline_pct DECIMAL(5,2) NULL,
    unchanged_pct DECIMAL(5,2) NULL,
    advance_decline_ratio DECIMAL(10,4) NULL,
    advance_decline_diff INT NULL,
    source VARCHAR(50) DEFAULT 'yfinance_daily_quotes',
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_trade_date (trade_date),
    INDEX idx_computed_at (computed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

conn.execute(text(create_sql))
conn.commit()

# Verify
result = conn.execute(text("SHOW TABLES LIKE 'nifty500_advance_decline'")).fetchone()
if result:
    print("✓ Table 'nifty500_advance_decline' created successfully!")
    
    # Show structure
    result = conn.execute(text("DESCRIBE nifty500_advance_decline")).fetchall()
    print("\nTable structure:")
    for row in result:
        print(f"  {row[0]:25} {row[1]:20} {row[2]:5} {row[3]:5}")
else:
    print("✗ Failed to create table")

conn.close()
