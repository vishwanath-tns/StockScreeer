"""
FNO Database Schema Creation Script
Creates the MySQL database and tables for NSE F&O data
Database: fno_marketdata
"""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
import pymysql

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
}

FNO_DATABASE = 'fno_marketdata'

# SQL to create database
CREATE_DATABASE_SQL = f"""
CREATE DATABASE IF NOT EXISTS {FNO_DATABASE}
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"""

# SQL to create futures table
CREATE_FUTURES_TABLE = """
CREATE TABLE IF NOT EXISTS nse_futures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    expiry_date DATE NOT NULL,
    instrument_type VARCHAR(20) NOT NULL DEFAULT 'FUTSTK',  -- FUTSTK, FUTIDX
    
    -- Price data
    previous_close DECIMAL(15,4),
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    close_price DECIMAL(15,4),
    settlement_price DECIMAL(15,4),
    net_change_pct DECIMAL(10,4),
    
    -- Volume and OI
    open_interest BIGINT,
    oi_change BIGINT DEFAULT 0,  -- OI change from previous day
    oi_change_pct DECIMAL(10,4) DEFAULT 0,
    traded_quantity BIGINT,
    number_of_trades INT,
    traded_value DECIMAL(20,4),
    
    -- Contract info
    contract_descriptor VARCHAR(100),
    lot_size INT DEFAULT 1,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes
    UNIQUE KEY uk_futures_trade (trade_date, symbol, expiry_date),
    INDEX idx_futures_symbol (symbol),
    INDEX idx_futures_expiry (expiry_date),
    INDEX idx_futures_date (trade_date),
    INDEX idx_futures_instrument (instrument_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# SQL to create options table
CREATE_OPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS nse_options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    expiry_date DATE NOT NULL,
    option_type CHAR(2) NOT NULL,  -- CE or PE
    strike_price DECIMAL(15,2) NOT NULL,
    instrument_type VARCHAR(20) NOT NULL DEFAULT 'OPTSTK',  -- OPTSTK, OPTIDX
    
    -- Price data
    previous_close DECIMAL(15,4),
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    close_price DECIMAL(15,4),
    settlement_price DECIMAL(15,4),
    net_change_pct DECIMAL(10,4),
    
    -- Volume and OI
    open_interest BIGINT,
    oi_change BIGINT DEFAULT 0,
    oi_change_pct DECIMAL(10,4) DEFAULT 0,
    traded_quantity BIGINT,
    number_of_trades INT,
    
    -- Underlying
    underlying_price DECIMAL(15,4),
    
    -- Value calculations
    notional_value DECIMAL(20,4),
    premium_traded DECIMAL(20,4),
    
    -- Contract info
    contract_descriptor VARCHAR(100),
    lot_size INT DEFAULT 1,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes
    UNIQUE KEY uk_options_trade (trade_date, symbol, expiry_date, option_type, strike_price),
    INDEX idx_options_symbol (symbol),
    INDEX idx_options_expiry (expiry_date),
    INDEX idx_options_date (trade_date),
    INDEX idx_options_type (option_type),
    INDEX idx_options_strike (strike_price),
    INDEX idx_options_instrument (instrument_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# SQL to create imports log table
CREATE_IMPORTS_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS fno_imports_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    file_type VARCHAR(20) NOT NULL,  -- 'futures' or 'options'
    file_name VARCHAR(255) NOT NULL,
    file_checksum VARCHAR(64),
    records_imported INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    import_status VARCHAR(20) DEFAULT 'success',  -- success, failed, partial
    error_message TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_import_date_type (trade_date, file_type),
    INDEX idx_imports_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# SQL to create symbols master table
CREATE_SYMBOLS_TABLE = """
CREATE TABLE IF NOT EXISTS fno_symbols (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL UNIQUE,
    symbol_name VARCHAR(200),
    instrument_type VARCHAR(20),  -- STOCK, INDEX
    lot_size INT DEFAULT 1,
    tick_size DECIMAL(10,4) DEFAULT 0.05,
    is_active TINYINT(1) DEFAULT 1,
    first_seen_date DATE,
    last_seen_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_symbols_type (instrument_type),
    INDEX idx_symbols_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# SQL to create option chain summary table (for quick analysis)
CREATE_OPTION_CHAIN_SUMMARY = """
CREATE TABLE IF NOT EXISTS option_chain_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    expiry_date DATE NOT NULL,
    
    -- Underlying
    underlying_price DECIMAL(15,4),
    
    -- Max Pain Analysis
    max_pain_strike DECIMAL(15,2),
    
    -- PCR (Put Call Ratio)
    pcr_oi DECIMAL(10,4),          -- OI based PCR
    pcr_volume DECIMAL(10,4),       -- Volume based PCR
    
    -- Support/Resistance levels (based on max OI)
    resistance_1 DECIMAL(15,2),     -- Highest CE OI strike
    resistance_2 DECIMAL(15,2),
    support_1 DECIMAL(15,2),        -- Highest PE OI strike
    support_2 DECIMAL(15,2),
    
    -- Total OI
    total_ce_oi BIGINT,
    total_pe_oi BIGINT,
    total_ce_volume BIGINT,
    total_pe_volume BIGINT,
    
    -- OI change from previous day
    ce_oi_change BIGINT DEFAULT 0,
    pe_oi_change BIGINT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_chain_summary (trade_date, symbol, expiry_date),
    INDEX idx_chain_date (trade_date),
    INDEX idx_chain_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# SQL to create futures analysis table
CREATE_FUTURES_ANALYSIS = """
CREATE TABLE IF NOT EXISTS futures_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    expiry_date DATE NOT NULL,
    
    -- Price info
    close_price DECIMAL(15,4),
    price_change DECIMAL(15,4),
    price_change_pct DECIMAL(10,4),
    
    -- OI info
    open_interest BIGINT,
    oi_change BIGINT,
    oi_change_pct DECIMAL(10,4),
    
    -- Analysis interpretation
    -- LONG_BUILDUP: Price up + OI up
    -- SHORT_BUILDUP: Price down + OI up  
    -- LONG_UNWINDING: Price down + OI down
    -- SHORT_COVERING: Price up + OI down
    interpretation VARCHAR(30),
    
    -- Volume
    traded_quantity BIGINT,
    volume_change_pct DECIMAL(10,4),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_futures_analysis (trade_date, symbol, expiry_date),
    INDEX idx_analysis_date (trade_date),
    INDEX idx_analysis_symbol (symbol),
    INDEX idx_analysis_interpretation (interpretation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def create_database():
    """Create the FNO database and all tables."""
    try:
        # Connect without database
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create database
        cursor.execute(CREATE_DATABASE_SQL)
        print(f"✅ Database '{FNO_DATABASE}' created/verified")
        
        # Switch to database
        cursor.execute(f"USE {FNO_DATABASE}")
        
        # Create tables
        tables = [
            ('nse_futures', CREATE_FUTURES_TABLE),
            ('nse_options', CREATE_OPTIONS_TABLE),
            ('fno_imports_log', CREATE_IMPORTS_LOG_TABLE),
            ('fno_symbols', CREATE_SYMBOLS_TABLE),
            ('option_chain_summary', CREATE_OPTION_CHAIN_SUMMARY),
            ('futures_analysis', CREATE_FUTURES_ANALYSIS),
        ]
        
        for table_name, create_sql in tables:
            cursor.execute(create_sql)
            print(f"✅ Table '{table_name}' created/verified")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n🎉 FNO database setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False


def get_table_stats():
    """Get row counts for all FNO tables."""
    try:
        conn = pymysql.connect(**DB_CONFIG, database=FNO_DATABASE)
        cursor = conn.cursor()
        
        tables = ['nse_futures', 'nse_options', 'fno_imports_log', 
                  'fno_symbols', 'option_chain_summary', 'futures_analysis']
        
        stats = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return stats
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {}


if __name__ == "__main__":
    print("=" * 60)
    print("NSE F&O Database Setup")
    print("=" * 60)
    
    success = create_database()
    
    if success:
        print("\n📊 Table Statistics:")
        stats = get_table_stats()
        for table, count in stats.items():
            print(f"   {table}: {count:,} rows")
