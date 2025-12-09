"""
Dhan Trading System - Database Setup
=====================================
Creates and manages the dhan_trading database.
"""
import os
import sys
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dhan_trading.config import (
    DHAN_DB_HOST, DHAN_DB_PORT, DHAN_DB_USER, 
    DHAN_DB_PASSWORD, DHAN_DB_NAME
)


def get_engine(database: str = None):
    """
    Create SQLAlchemy engine for Dhan database.
    
    Args:
        database: Database name (None to connect without selecting a database)
    """
    password = quote_plus(DHAN_DB_PASSWORD)
    
    if database:
        url = f"mysql+pymysql://{DHAN_DB_USER}:{password}@{DHAN_DB_HOST}:{DHAN_DB_PORT}/{database}"
    else:
        url = f"mysql+pymysql://{DHAN_DB_USER}:{password}@{DHAN_DB_HOST}:{DHAN_DB_PORT}"
    
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )


def create_database():
    """Create the dhan_trading database if it doesn't exist."""
    engine = get_engine()  # Connect without database
    
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DHAN_DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        print(f"✅ Database '{DHAN_DB_NAME}' created/verified")
    
    engine.dispose()


def create_instruments_table():
    """Create the dhan_instruments table."""
    engine = get_engine(DHAN_DB_NAME)
    
    sql = """
    CREATE TABLE IF NOT EXISTS dhan_instruments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        
        -- Core identifiers
        security_id BIGINT NOT NULL COMMENT 'Dhan Security ID - unique identifier',
        exchange VARCHAR(10) NOT NULL COMMENT 'Exchange: NSE, BSE, MCX',
        segment VARCHAR(20) NOT NULL COMMENT 'Segment: E-Equity, D-Derivatives, C-Currency, M-Commodity',
        exchange_segment VARCHAR(20) COMMENT 'Combined exchange_segment code',
        
        -- Symbol information
        symbol VARCHAR(50) NOT NULL COMMENT 'Trading symbol',
        display_name VARCHAR(100) COMMENT 'Display name shown in Dhan',
        isin VARCHAR(15) COMMENT 'ISIN code (for equity)',
        instrument VARCHAR(50) COMMENT 'Instrument category: EQUITY, FUTIDX, OPTIDX, etc',
        
        -- Instrument details
        instrument_type VARCHAR(50) COMMENT 'Instrument type from exchange',
        series VARCHAR(10) COMMENT 'Series: EQ, BE, etc',
        lot_size INT DEFAULT 1 COMMENT 'Lot size for trading',
        tick_size DECIMAL(10,4) DEFAULT 0.05 COMMENT 'Minimum price movement',
        
        -- Derivative specific
        underlying_security_id BIGINT COMMENT 'Security ID of underlying (for derivatives)',
        underlying_symbol VARCHAR(100) COMMENT 'Symbol of underlying',
        expiry_date DATE COMMENT 'Expiry date (for derivatives)',
        strike_price DECIMAL(15,2) COMMENT 'Strike price (for options)',
        option_type VARCHAR(5) COMMENT 'CE or PE (for options)',
        expiry_flag VARCHAR(5) COMMENT 'M-Monthly, W-Weekly',
        
        -- Trading flags
        bracket_flag VARCHAR(5) DEFAULT 'N' COMMENT 'Bracket order allowed: Y/N',
        cover_flag VARCHAR(5) DEFAULT 'N' COMMENT 'Cover order allowed: Y/N',
        asm_gsm_flag VARCHAR(5) DEFAULT 'N' COMMENT 'ASM/GSM status',
        asm_gsm_category VARCHAR(20) COMMENT 'ASM/GSM category if applicable',
        buy_sell_indicator VARCHAR(5) DEFAULT 'A' COMMENT 'A-Both allowed',
        mtf_leverage DECIMAL(5,2) COMMENT 'MTF leverage multiplier',
        
        -- Margin requirements (Cover Order)
        buy_co_min_margin_per DECIMAL(10,4) COMMENT 'Buy CO minimum margin %',
        sell_co_min_margin_per DECIMAL(10,4) COMMENT 'Sell CO minimum margin %',
        buy_co_sl_range_max_perc DECIMAL(10,4) COMMENT 'Buy CO max SL range %',
        sell_co_sl_range_max_perc DECIMAL(10,4) COMMENT 'Sell CO max SL range %',
        buy_co_sl_range_min_perc DECIMAL(10,4) COMMENT 'Buy CO min SL range %',
        sell_co_sl_range_min_perc DECIMAL(10,4) COMMENT 'Sell CO min SL range %',
        
        -- Margin requirements (Bracket Order)
        buy_bo_min_margin_per DECIMAL(10,4) COMMENT 'Buy BO minimum margin %',
        sell_bo_min_margin_per DECIMAL(10,4) COMMENT 'Sell BO minimum margin %',
        buy_bo_sl_range_max_perc DECIMAL(10,4) COMMENT 'Buy BO max SL range %',
        sell_bo_sl_range_max_perc DECIMAL(10,4) COMMENT 'Sell BO max SL range %',
        buy_bo_sl_range_min_perc DECIMAL(10,4) COMMENT 'Buy BO min SL range %',
        sell_bo_sl_range_min_perc DECIMAL(10,4) COMMENT 'Sell BO min SL range %',
        buy_bo_profit_range_max_perc DECIMAL(10,4) COMMENT 'Buy BO max profit range %',
        sell_bo_profit_range_max_perc DECIMAL(10,4) COMMENT 'Sell BO max profit range %',
        buy_bo_profit_range_min_perc DECIMAL(10,4) COMMENT 'Buy BO min profit range %',
        sell_bo_profit_range_min_perc DECIMAL(10,4) COMMENT 'Sell BO min profit range %',
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        -- Indexes
        UNIQUE KEY uk_security_id (security_id),
        INDEX idx_exchange_segment (exchange, segment),
        INDEX idx_symbol (symbol),
        INDEX idx_underlying (underlying_security_id),
        INDEX idx_expiry (expiry_date),
        INDEX idx_option (underlying_symbol, expiry_date, strike_price, option_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='Dhan instrument master - updated daily from Dhan API';
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✅ Table 'dhan_instruments' created/verified")
    
    engine.dispose()


def create_imports_log_table():
    """Create table to track instrument imports."""
    engine = get_engine(DHAN_DB_NAME)
    
    sql = """
    CREATE TABLE IF NOT EXISTS dhan_imports_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        import_date DATE NOT NULL,
        import_type VARCHAR(50) NOT NULL COMMENT 'INSTRUMENTS, ORDERS, etc',
        records_count INT DEFAULT 0,
        source_url VARCHAR(500),
        status VARCHAR(20) DEFAULT 'SUCCESS',
        error_message TEXT,
        duration_seconds DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        INDEX idx_import_date (import_date),
        INDEX idx_import_type (import_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✅ Table 'dhan_imports_log' created/verified")
    
    engine.dispose()


def setup_database():
    """Setup the complete Dhan database."""
    print("=" * 50)
    print("Setting up Dhan Trading Database")
    print("=" * 50)
    
    create_database()
    create_instruments_table()
    create_imports_log_table()
    
    print("\n✅ Dhan database setup complete!")
    print(f"   Database: {DHAN_DB_NAME}")
    print(f"   Host: {DHAN_DB_HOST}:{DHAN_DB_PORT}")


if __name__ == '__main__':
    setup_database()
