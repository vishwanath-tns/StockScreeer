#!/usr/bin/env python3
"""
Setup FNO database tables for Dhan trading data
Creates dhan_fno_quotes table if it doesn't exist
"""

import os
import sys
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Get database credentials from environment
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_DB = os.environ.get('MYSQL_DB', 'marketdata')
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')

def create_tables():
    """Create necessary FNO tables"""
    
    # Create engine
    password = quote_plus(MYSQL_PASSWORD)
    db_url = f"mysql+pymysql://{MYSQL_USER}:{password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    engine = create_engine(db_url, echo=False)
    
    with engine.connect() as conn:
        # Create dhan_fno_quotes table
        print("Creating dhan_fno_quotes table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dhan_fno_quotes (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                security_id INT NOT NULL,
                exchange_segment VARCHAR(20),
                ltp DECIMAL(15, 2),
                open_price DECIMAL(15, 2),
                high DECIMAL(15, 2),
                low DECIMAL(15, 2),
                close_price DECIMAL(15, 2),
                volume BIGINT,
                bid DECIMAL(15, 2),
                ask DECIMAL(15, 2),
                quote_time DATETIME(3),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_security_id (security_id),
                INDEX idx_quote_time (quote_time),
                INDEX idx_segment (exchange_segment),
                UNIQUE KEY unique_quote (security_id, quote_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        conn.commit()
        print("✅ Table dhan_fno_quotes created successfully")
        
        # Create dhan_instruments table if not exists
        print("Creating dhan_instruments table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dhan_instruments (
                security_id INT PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                display_name VARCHAR(100),
                exchange VARCHAR(20),
                exchange_segment VARCHAR(20),
                underlying_symbol VARCHAR(50),
                expiry_date DATE,
                strike_price DECIMAL(10, 2),
                is_active TINYINT DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_symbol (symbol),
                INDEX idx_segment (exchange_segment),
                INDEX idx_expiry (expiry_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        conn.commit()
        print("✅ Table dhan_instruments created successfully")
    
    print("\n✅ All FNO tables created/verified!")
    print(f"Database: {MYSQL_DB}")
    print(f"Host: {MYSQL_HOST}:{MYSQL_PORT}")

if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
