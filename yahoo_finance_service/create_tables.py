#!/usr/bin/env python3
"""
Quick database setup script for Yahoo Finance tables
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database='marketdata'
    )

    cursor = conn.cursor()
    
    print('✅ Connected to database successfully')
    
    # Check if tables already exist
    cursor.execute("SHOW TABLES LIKE 'yfinance_%'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    print(f'Existing yfinance tables: {existing_tables}')
    
    if 'yfinance_daily_quotes' not in existing_tables:
        print('Creating yfinance_daily_quotes table...')
        cursor.execute("""
        CREATE TABLE yfinance_daily_quotes (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL DEFAULT 'NIFTY',
            date DATE NOT NULL,
            open DECIMAL(15,4) NULL,
            high DECIMAL(15,4) NULL,
            low DECIMAL(15,4) NULL,
            close DECIMAL(15,4) NULL,
            volume BIGINT NULL,
            adj_close DECIMAL(15,4) NULL,
            timeframe VARCHAR(10) NOT NULL DEFAULT 'Daily',
            source VARCHAR(20) NOT NULL DEFAULT 'Yahoo Finance',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_symbol_date_timeframe (symbol, date, timeframe),
            INDEX idx_date (date),
            INDEX idx_symbol (symbol)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print('✅ yfinance_daily_quotes created')
    else:
        print('✅ yfinance_daily_quotes already exists')
    
    if 'yfinance_symbols' not in existing_tables:
        print('Creating yfinance_symbols table...')
        cursor.execute("""
        CREATE TABLE yfinance_symbols (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL UNIQUE,
            yahoo_symbol VARCHAR(30) NOT NULL,
            name VARCHAR(100) NOT NULL,
            market VARCHAR(20) DEFAULT 'NSE',
            currency VARCHAR(5) DEFAULT 'INR',
            symbol_type ENUM('INDEX', 'STOCK', 'ETF') DEFAULT 'INDEX',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # Insert default symbols
        cursor.execute("""
        INSERT INTO yfinance_symbols (symbol, yahoo_symbol, name, symbol_type) VALUES
        ('NIFTY', '^NSEI', 'NIFTY 50', 'INDEX'),
        ('BANKNIFTY', '^NSEBANK', 'BANK NIFTY', 'INDEX'),
        ('SENSEX', '^BSESN', 'BSE SENSEX', 'INDEX')
        """)
        print('✅ yfinance_symbols created with default symbols')
    else:
        print('✅ yfinance_symbols already exists')
    
    if 'yfinance_download_log' not in existing_tables:
        print('Creating yfinance_download_log table...')
        cursor.execute("""
        CREATE TABLE yfinance_download_log (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            records_downloaded INT DEFAULT 0,
            records_updated INT DEFAULT 0,
            status ENUM('STARTED', 'COMPLETED', 'FAILED', 'PARTIAL') DEFAULT 'STARTED',
            error_message TEXT NULL,
            download_duration_ms INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print('✅ yfinance_download_log created')
    else:
        print('✅ yfinance_download_log already exists')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('\n🎉 Database setup complete!')
    print('Ready to launch Yahoo Finance Data Downloader')
    
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)