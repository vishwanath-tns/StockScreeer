-- Real-Time Market Data Table
-- Dedicated table for Yahoo Finance real-time streaming data
-- Do NOT use nse_equity_bhavcopy_full as it's for NSE BHAV copy data

CREATE TABLE IF NOT EXISTS realtime_market_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL COMMENT 'Stock/Futures symbol (e.g., GC=F, AAPL)',
    series VARCHAR(10) DEFAULT 'EQ' COMMENT 'Market series',
    trade_date DATE NOT NULL COMMENT 'Trading date',
    prev_close DECIMAL(20, 4) NOT NULL COMMENT 'Previous closing price',
    open_price DECIMAL(20, 4) NOT NULL COMMENT 'Opening price',
    high_price DECIMAL(20, 4) NOT NULL COMMENT 'High price',
    low_price DECIMAL(20, 4) NOT NULL COMMENT 'Low price',
    close_price DECIMAL(20, 4) NOT NULL COMMENT 'Closing/Current price',
    volume BIGINT DEFAULT 0 COMMENT 'Trading volume',
    deliv_qty BIGINT DEFAULT NULL COMMENT 'Delivery quantity (if available)',
    deliv_per DECIMAL(10, 2) DEFAULT NULL COMMENT 'Delivery percentage (if available)',
    timestamp BIGINT NOT NULL COMMENT 'Unix epoch timestamp of data fetch',
    data_source VARCHAR(50) DEFAULT 'yahoo_finance' COMMENT 'Data source identifier',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Record update time',
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY unique_symbol_date (symbol, trade_date, timestamp),
    
    -- Indexes for faster queries
    INDEX idx_symbol (symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol_date (symbol, trade_date),
    INDEX idx_data_source (data_source),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Real-time market data from Yahoo Finance streaming service';

-- Optional: Create a separate table for intraday ticks if needed
CREATE TABLE IF NOT EXISTS realtime_market_ticks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    price DECIMAL(20, 4) NOT NULL,
    volume BIGINT DEFAULT 0,
    timestamp BIGINT NOT NULL COMMENT 'Unix epoch timestamp',
    data_source VARCHAR(50) DEFAULT 'yahoo_finance',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_symbol_timestamp (symbol, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Intraday tick data for high-frequency updates';
