"""
Tick Data Models
================
Database tables for storing real-time market tick data.
"""
import os
import sys
from datetime import datetime, date
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.db_setup import get_engine, DHAN_DB_NAME


def create_tick_tables():
    """Create tables for storing tick data."""
    engine = get_engine(DHAN_DB_NAME)
    
    # Ticker data table (LTP only - lightweight)
    ticker_sql = """
    CREATE TABLE IF NOT EXISTS dhan_ticks (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        
        -- Instrument identification
        security_id BIGINT NOT NULL COMMENT 'Dhan Security ID',
        exchange_segment TINYINT NOT NULL COMMENT 'Exchange segment code',
        
        -- Tick data
        ltp DECIMAL(15,4) NOT NULL COMMENT 'Last Traded Price',
        ltt INT UNSIGNED NOT NULL COMMENT 'Last Trade Time (EPOCH)',
        
        -- Metadata
        received_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'When tick was received',
        
        INDEX idx_security_ltt (security_id, ltt),
        INDEX idx_received (received_at),
        INDEX idx_segment_ltt (exchange_segment, ltt)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    COMMENT='Real-time tick data (LTP) from Dhan WebSocket';
    """
    
    # Quote data table (more detailed)
    quote_sql = """
    CREATE TABLE IF NOT EXISTS dhan_quotes (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        
        -- Instrument identification
        security_id BIGINT NOT NULL COMMENT 'Dhan Security ID',
        exchange_segment TINYINT NOT NULL COMMENT 'Exchange segment code',
        
        -- Quote data
        ltp DECIMAL(15,4) NOT NULL COMMENT 'Last Traded Price',
        ltq INT NOT NULL COMMENT 'Last Traded Quantity',
        ltt INT UNSIGNED NOT NULL COMMENT 'Last Trade Time (EPOCH)',
        atp DECIMAL(15,4) COMMENT 'Average Trade Price',
        volume BIGINT COMMENT 'Total Volume',
        total_sell_qty BIGINT COMMENT 'Total Sell Quantity',
        total_buy_qty BIGINT COMMENT 'Total Buy Quantity',
        day_open DECIMAL(15,4) COMMENT 'Day Open',
        day_close DECIMAL(15,4) COMMENT 'Day Close',
        day_high DECIMAL(15,4) COMMENT 'Day High',
        day_low DECIMAL(15,4) COMMENT 'Day Low',
        
        -- OI for derivatives
        open_interest INT COMMENT 'Open Interest',
        
        -- Metadata
        received_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'When quote was received',
        
        INDEX idx_security_ltt (security_id, ltt),
        INDEX idx_received (received_at),
        INDEX idx_segment_ltt (exchange_segment, ltt)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    COMMENT='Real-time quote data from Dhan WebSocket';
    """
    
    # Full packet data table (with market depth)
    full_sql = """
    CREATE TABLE IF NOT EXISTS dhan_full_packets (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        
        -- Instrument identification
        security_id BIGINT NOT NULL COMMENT 'Dhan Security ID',
        exchange_segment TINYINT NOT NULL COMMENT 'Exchange segment code',
        
        -- Full quote data
        ltp DECIMAL(15,4) NOT NULL COMMENT 'Last Traded Price',
        ltq INT NOT NULL COMMENT 'Last Traded Quantity',
        ltt INT UNSIGNED NOT NULL COMMENT 'Last Trade Time (EPOCH)',
        atp DECIMAL(15,4) COMMENT 'Average Trade Price',
        volume BIGINT COMMENT 'Total Volume',
        total_sell_qty BIGINT COMMENT 'Total Sell Quantity',
        total_buy_qty BIGINT COMMENT 'Total Buy Quantity',
        
        -- OI data
        open_interest INT COMMENT 'Open Interest',
        oi_high INT COMMENT 'OI High for day',
        oi_low INT COMMENT 'OI Low for day',
        
        -- OHLC
        day_open DECIMAL(15,4) COMMENT 'Day Open',
        day_close DECIMAL(15,4) COMMENT 'Day Close',
        day_high DECIMAL(15,4) COMMENT 'Day High',
        day_low DECIMAL(15,4) COMMENT 'Day Low',
        
        -- Market Depth (JSON for flexibility)
        depth_json JSON COMMENT 'Market depth 5 levels',
        
        -- Metadata
        received_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'When packet was received',
        
        INDEX idx_security_ltt (security_id, ltt),
        INDEX idx_received (received_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    COMMENT='Full market data packets with depth';
    """
    
    # Latest tick cache table (for quick current price lookup)
    latest_sql = """
    CREATE TABLE IF NOT EXISTS dhan_latest_tick (
        security_id BIGINT PRIMARY KEY COMMENT 'Dhan Security ID',
        exchange_segment TINYINT NOT NULL COMMENT 'Exchange segment code',
        symbol VARCHAR(50) NOT NULL COMMENT 'Trading symbol',
        
        -- Latest data
        ltp DECIMAL(15,4) NOT NULL COMMENT 'Last Traded Price',
        prev_close DECIMAL(15,4) COMMENT 'Previous Close',
        change_pct DECIMAL(8,4) COMMENT 'Change percentage',
        ltt INT UNSIGNED COMMENT 'Last Trade Time (EPOCH)',
        volume BIGINT COMMENT 'Total Volume',
        open_interest INT COMMENT 'Open Interest',
        
        -- OHLC
        day_open DECIMAL(15,4) COMMENT 'Day Open',
        day_high DECIMAL(15,4) COMMENT 'Day High',
        day_low DECIMAL(15,4) COMMENT 'Day Low',
        
        -- Metadata
        updated_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
        
        INDEX idx_segment (exchange_segment),
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    COMMENT='Latest tick for each subscribed instrument';
    """
    
    # Feed subscription table (track what we're subscribing to)
    subscription_sql = """
    CREATE TABLE IF NOT EXISTS dhan_feed_subscriptions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        
        -- Instrument
        security_id BIGINT NOT NULL COMMENT 'Dhan Security ID',
        exchange_segment VARCHAR(20) NOT NULL COMMENT 'Exchange segment string',
        symbol VARCHAR(50) NOT NULL COMMENT 'Symbol',
        display_name VARCHAR(100) COMMENT 'Display name',
        instrument_type VARCHAR(20) COMMENT 'FUTIDX, OPTIDX, etc',
        
        -- Subscription settings
        feed_type VARCHAR(20) DEFAULT 'QUOTE' COMMENT 'TICKER, QUOTE, FULL',
        is_active TINYINT(1) DEFAULT 1 COMMENT 'Is subscription active',
        priority INT DEFAULT 0 COMMENT 'Priority for connection allocation',
        
        -- Expiry info (for derivatives)
        expiry_date DATE COMMENT 'Expiry date',
        strike_price DECIMAL(15,2) COMMENT 'Strike price',
        option_type VARCHAR(5) COMMENT 'CE/PE',
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        UNIQUE KEY idx_security (security_id),
        INDEX idx_active_type (is_active, feed_type),
        INDEX idx_segment (exchange_segment),
        INDEX idx_expiry (expiry_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    COMMENT='Instruments subscribed for live feed';
    """
    
    with engine.connect() as conn:
        print("Creating tick data tables...")
        
        conn.execute(text(ticker_sql))
        print("  [OK] dhan_ticks table created")
        
        conn.execute(text(quote_sql))
        print("  [OK] dhan_quotes table created")
        
        conn.execute(text(full_sql))
        print("  [OK] dhan_full_packets table created")
        
        conn.execute(text(latest_sql))
        print("  [OK] dhan_latest_tick table created")
        
        conn.execute(text(subscription_sql))
        print("  [OK] dhan_feed_subscriptions table created")
        
        conn.commit()
    
    engine.dispose()
    print("\n[OK] All tick data tables created!")


if __name__ == "__main__":
    create_tick_tables()
