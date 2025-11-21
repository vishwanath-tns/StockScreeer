-- Yahoo Finance Data Schema
-- Database: marketdata
-- Purpose: Store daily stock market data from Yahoo Finance API

USE marketdata;

-- Table: yfinance_daily_quotes
-- Stores daily OHLCV data for stocks and indices
CREATE TABLE IF NOT EXISTS yfinance_daily_quotes (
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
    
    -- Constraints
    UNIQUE KEY uk_symbol_date_timeframe (symbol, date, timeframe),
    
    -- Indexes for performance
    INDEX idx_date (date),
    INDEX idx_symbol (symbol),
    INDEX idx_symbol_date (symbol, date),
    INDEX idx_timeframe (timeframe),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: yfinance_symbols
-- Stores symbol mapping and metadata
CREATE TABLE IF NOT EXISTS yfinance_symbols (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    yahoo_symbol VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    market VARCHAR(20) DEFAULT 'NSE',
    currency VARCHAR(5) DEFAULT 'INR',
    symbol_type ENUM('INDEX', 'STOCK', 'ETF') DEFAULT 'INDEX',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_symbol (symbol),
    INDEX idx_yahoo_symbol (yahoo_symbol),
    INDEX idx_market (market),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default symbols
INSERT IGNORE INTO yfinance_symbols (symbol, yahoo_symbol, name, symbol_type) VALUES
('NIFTY', '^NSEI', 'NIFTY 50', 'INDEX'),
('BANKNIFTY', '^NSEBANK', 'BANK NIFTY', 'INDEX'),
('SENSEX', '^BSESN', 'BSE SENSEX', 'INDEX');

-- Table: yfinance_download_log
-- Track download activities and status
CREATE TABLE IF NOT EXISTS yfinance_download_log (
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
    completed_at TIMESTAMP NULL,
    
    -- Indexes
    INDEX idx_symbol_date (symbol, start_date, end_date),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- View: Daily quotes with symbol details
CREATE OR REPLACE VIEW v_yfinance_daily_summary AS
SELECT 
    q.symbol,
    s.name as symbol_name,
    s.yahoo_symbol,
    q.date,
    q.open,
    q.high,
    q.low,
    q.close,
    q.volume,
    q.adj_close,
    q.timeframe,
    ROUND(((q.close - q.open) / q.open * 100), 2) as day_change_pct,
    q.created_at,
    q.updated_at
FROM yfinance_daily_quotes q
LEFT JOIN yfinance_symbols s ON q.symbol = s.symbol
WHERE s.is_active = TRUE
ORDER BY q.symbol, q.date DESC;

-- Indexes for optimal performance
-- Additional composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_symbol_date_desc ON yfinance_daily_quotes (symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_date_desc ON yfinance_daily_quotes (date DESC);

-- Check table status
SELECT 
    'yfinance_daily_quotes' as table_name,
    COUNT(*) as record_count,
    MIN(date) as earliest_date,
    MAX(date) as latest_date,
    COUNT(DISTINCT symbol) as unique_symbols
FROM yfinance_daily_quotes
UNION ALL
SELECT 
    'yfinance_symbols' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as earliest_date,
    MAX(created_at) as latest_date,
    COUNT(*) as unique_symbols
FROM yfinance_symbols;