"""
FNO Market Data Schema
======================
Database tables for storing Futures & Options real-time market data.
Created separately from dhan_quotes to keep FNO data isolated.

Tables:
  - dhan_fno_quotes: Futures & Commodity quotes (NSE_FNO, MCX_COMM segments)
  - dhan_options_quotes: Index Options quotes (FinNifty, BankNifty, others)
"""
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dhan_trading.db_setup import get_engine, DHAN_DB_NAME


def create_fno_quotes_table():
    """
    Create table for futures and commodity quotes.
    
    Stores real-time quotes for:
    - NSE Futures (Nifty, BankNifty, FinNifty, etc.)
    - MCX Commodity Futures (Gold, Crude Oil, etc.)
    """
    engine = get_engine(DHAN_DB_NAME)
    
    sql = """
    CREATE TABLE IF NOT EXISTS dhan_fno_quotes (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        
        -- Instrument identification
        security_id BIGINT NOT NULL COMMENT 'Dhan Security ID (unique)',
        exchange_segment VARCHAR(20) NOT NULL COMMENT 'Exchange segment: NSE_FNO, MCX_COMM',
        symbol VARCHAR(100) NOT NULL COMMENT 'Trading symbol (e.g., NIFTY26DEC25FUT)',
        
        -- Derivative details
        underlying_symbol VARCHAR(50) COMMENT 'Underlying symbol (e.g., NIFTY)',
        expiry_date DATE COMMENT 'Futures expiry date',
        contract_type VARCHAR(20) COMMENT 'Type: FUTURE, COMMODITY',
        
        -- Quote data (matches dhan_quotes structure)
        ltp DECIMAL(15,4) NOT NULL COMMENT 'Last Traded Price',
        ltq INT COMMENT 'Last Traded Quantity',
        ltt INT UNSIGNED COMMENT 'Last Trade Time (EPOCH)',
        atp DECIMAL(15,4) COMMENT 'Average Trade Price',
        volume BIGINT COMMENT 'Total Volume traded',
        total_sell_qty BIGINT COMMENT 'Total Sell Quantity',
        total_buy_qty BIGINT COMMENT 'Total Buy Quantity',
        
        -- OHLC for the day
        day_open DECIMAL(15,4) COMMENT 'Day Open price',
        day_close DECIMAL(15,4) COMMENT 'Day Close price',
        day_high DECIMAL(15,4) COMMENT 'Day High price',
        day_low DECIMAL(15,4) COMMENT 'Day Low price',
        
        -- Derivatives-specific data
        open_interest INT COMMENT 'Open Interest',
        prev_open_interest INT COMMENT 'Previous day OI',
        oi_change INT COMMENT 'Change in OI',
        bid_price DECIMAL(15,4) COMMENT 'Current Bid Price',
        ask_price DECIMAL(15,4) COMMENT 'Current Ask Price',
        bid_qty INT COMMENT 'Bid Quantity',
        ask_qty INT COMMENT 'Ask Quantity',
        
        -- Metadata
        trade_date DATE GENERATED ALWAYS AS (DATE(FROM_UNIXTIME(ltt))) STORED COMMENT 'Trade date derived from ltt',
        received_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'When quote was received by us',
        
        -- Indexes for fast lookups
        UNIQUE KEY uk_security_ltt (security_id, ltt),
        INDEX idx_received_at (received_at),
        INDEX idx_security_id (security_id),
        INDEX idx_underlying (underlying_symbol, expiry_date),
        INDEX idx_trade_date (trade_date),
        INDEX idx_segment (exchange_segment),
        INDEX idx_ltp (ltp)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='Futures & Commodity quotes (NSE_FNO, MCX_COMM)';
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("[OK] Table 'dhan_fno_quotes' created/verified")
    
    engine.dispose()


def create_options_quotes_table():
    """
    Create table for index options quotes.
    
    Stores real-time quotes for:
    - NIFTY Options (FinNifty, NIFTY)
    - BankNifty Options
    - Stock Options
    """
    engine = get_engine(DHAN_DB_NAME)
    
    sql = """
    CREATE TABLE IF NOT EXISTS dhan_options_quotes (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        
        -- Instrument identification
        security_id BIGINT NOT NULL COMMENT 'Dhan Security ID (unique)',
        exchange_segment VARCHAR(20) NOT NULL COMMENT 'Exchange segment: OPTIDX, OPTSTK',
        symbol VARCHAR(100) NOT NULL COMMENT 'Option symbol (e.g., BANKNIFTY30DEC4650CE)',
        display_name VARCHAR(150) COMMENT 'Display name (e.g., BANKNIFTY 30 DEC 4650 CALL)',
        
        -- Option details
        underlying_symbol VARCHAR(50) NOT NULL COMMENT 'Underlying symbol (e.g., BANKNIFTY)',
        expiry_date DATE NOT NULL COMMENT 'Option expiry date',
        strike_price DECIMAL(15,2) NOT NULL COMMENT 'Strike price',
        option_type VARCHAR(2) NOT NULL COMMENT 'Option type: CE (Call) or PE (Put)',
        contract_month VARCHAR(20) COMMENT 'Contract month (e.g., DEC2025)',
        
        -- Quote data (matches dhan_quotes structure)
        ltp DECIMAL(15,4) NOT NULL COMMENT 'Last Traded Price (Premium)',
        ltq INT COMMENT 'Last Traded Quantity',
        ltt INT UNSIGNED COMMENT 'Last Trade Time (EPOCH)',
        atp DECIMAL(15,4) COMMENT 'Average Trade Price',
        volume BIGINT COMMENT 'Total Volume traded',
        total_sell_qty BIGINT COMMENT 'Total Sell Quantity',
        total_buy_qty BIGINT COMMENT 'Total Buy Quantity',
        
        -- OHLC for the day
        day_open DECIMAL(15,4) COMMENT 'Day Open premium',
        day_close DECIMAL(15,4) COMMENT 'Day Close premium',
        day_high DECIMAL(15,4) COMMENT 'Day High premium',
        day_low DECIMAL(15,4) COMMENT 'Day Low premium',
        
        -- Options-specific data
        open_interest INT COMMENT 'Open Interest (number of contracts)',
        prev_open_interest INT COMMENT 'Previous day OI',
        oi_change INT COMMENT 'Change in OI',
        bid_price DECIMAL(15,4) COMMENT 'Bid Price (ask for puts, bid for calls)',
        ask_price DECIMAL(15,4) COMMENT 'Ask Price (bid for puts, ask for calls)',
        bid_qty INT COMMENT 'Bid Quantity',
        ask_qty INT COMMENT 'Ask Quantity',
        bid_ask_spread DECIMAL(15,4) GENERATED ALWAYS AS (ask_price - bid_price) STORED COMMENT 'Bid-Ask spread',
        
        -- Greeks data (will be calculated separately)
        implied_volatility DECIMAL(10,4) COMMENT 'Implied Volatility (can be calculated from bid-ask)',
        
        -- Metadata
        trade_date DATE GENERATED ALWAYS AS (DATE(FROM_UNIXTIME(ltt))) STORED COMMENT 'Trade date derived from ltt',
        received_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'When quote was received by us',
        
        -- Indexes for fast lookups
        UNIQUE KEY uk_security_ltt (security_id, ltt),
        INDEX idx_received_at (received_at),
        INDEX idx_security_id (security_id),
        INDEX idx_underlying_expiry (underlying_symbol, expiry_date),
        INDEX idx_option_chain (underlying_symbol, strike_price, option_type),
        INDEX idx_trade_date (trade_date),
        INDEX idx_ltp (ltp),
        INDEX idx_oi (open_interest)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='Index Options & Stock Options quotes (OPTIDX, OPTSTK)';
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("[OK] Table 'dhan_options_quotes' created/verified")
    
    engine.dispose()


def create_fno_metadata_table():
    """
    Create table for FNO-specific metadata (contracts, expirations, etc).
    """
    engine = get_engine(DHAN_DB_NAME)
    
    sql = """
    CREATE TABLE IF NOT EXISTS dhan_fno_metadata (
        id INT AUTO_INCREMENT PRIMARY KEY,
        
        -- Metadata
        data_type VARCHAR(50) NOT NULL COMMENT 'Type of metadata: FUTURES_CONTRACTS, EXPIRY_DATES, etc',
        category VARCHAR(50) COMMENT 'Category: NSE_FNO, MCX_COMM, OPTIONS, etc',
        key_name VARCHAR(100) COMMENT 'Metadata key (e.g., nearest_expiry)',
        key_value VARCHAR(500) COMMENT 'Metadata value (e.g., 26-DEC-2025)',
        description TEXT COMMENT 'Description of this metadata',
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        INDEX idx_data_type (data_type),
        INDEX idx_category (category),
        INDEX idx_updated (updated_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='FNO metadata (contract details, expirations, etc)';
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✅ Table 'dhan_fno_metadata' created/verified")
    
    engine.dispose()


def create_fno_feed_log_table():
    """
    Create table to log FNO feed subscriptions and data flow.
    """
    engine = get_engine(DHAN_DB_NAME)
    
    sql = """
    CREATE TABLE IF NOT EXISTS dhan_fno_feed_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        
        -- Feed info
        feed_type VARCHAR(50) NOT NULL COMMENT 'Feed type: FNO_LAUNCHER, FNO_DB_WRITER, etc',
        event_type VARCHAR(50) COMMENT 'Event: SUBSCRIBED, RECEIVED, ERROR, etc',
        
        -- Details
        security_count INT COMMENT 'Number of securities subscribed',
        instruments_subscribed TEXT COMMENT 'JSON or CSV of subscribed instruments',
        status VARCHAR(50) DEFAULT 'SUCCESS',
        message TEXT,
        error_message TEXT,
        
        -- Timing
        feed_start_time TIMESTAMP,
        feed_end_time TIMESTAMP,
        duration_seconds DECIMAL(10,2),
        
        -- Metrics
        quotes_received INT DEFAULT 0,
        quotes_written INT DEFAULT 0,
        errors INT DEFAULT 0,
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        INDEX idx_feed_type (feed_type),
        INDEX idx_event_type (event_type),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='FNO feed service event log';
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✅ Table 'dhan_fno_feed_log' created/verified")
    
    engine.dispose()


def setup_fno_database():
    """Setup all FNO-related tables."""
    print("=" * 60)
    print("Setting up FNO (Futures & Options) Database Tables")
    print("=" * 60)
    
    create_fno_quotes_table()
    create_options_quotes_table()
    create_fno_metadata_table()
    create_fno_feed_log_table()
    
    print("\n✅ FNO database setup complete!")
    print(f"   Database: {DHAN_DB_NAME}")
    print(f"   Tables:")
    print(f"     - dhan_fno_quotes (Futures & Commodities)")
    print(f"     - dhan_options_quotes (Index & Stock Options)")
    print(f"     - dhan_fno_metadata (Metadata)")
    print(f"     - dhan_fno_feed_log (Event log)")


if __name__ == '__main__':
    setup_fno_database()
