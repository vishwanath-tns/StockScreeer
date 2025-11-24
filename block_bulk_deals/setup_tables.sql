-- NSE Block & Bulk Deals Database Schema
-- Database: marketdata

USE marketdata;

-- ============================================================================
-- Block Deals Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS nse_block_deals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    security_name VARCHAR(255),
    client_name VARCHAR(255),
    deal_type VARCHAR(10) COMMENT 'BUY or SELL',
    quantity BIGINT,
    trade_price DECIMAL(15,4),
    remarks VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for fast querying
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_symbol_date (symbol, trade_date),
    INDEX idx_client (client_name(100)),
    INDEX idx_deal_type (deal_type),
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY uk_block_deal (trade_date, symbol, client_name(200), deal_type, quantity, trade_price)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='NSE Block Deals - Transactions of 5 lakh shares or more';

-- ============================================================================
-- Bulk Deals Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS nse_bulk_deals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    security_name VARCHAR(255),
    client_name VARCHAR(255),
    deal_type VARCHAR(10) COMMENT 'BUY or SELL',
    quantity BIGINT,
    trade_price DECIMAL(15,4),
    remarks VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for fast querying
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_symbol_date (symbol, trade_date),
    INDEX idx_client (client_name(100)),
    INDEX idx_deal_type (deal_type),
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY uk_bulk_deal (trade_date, symbol, client_name(200), deal_type, quantity, trade_price)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='NSE Bulk Deals - Transactions >= 0.5% of equity shares';

-- ============================================================================
-- Import Log Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS block_bulk_deals_import_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    deal_category VARCHAR(20) NOT NULL COMMENT 'BLOCK or BULK',
    records_imported INT DEFAULT 0,
    import_status VARCHAR(20) DEFAULT 'SUCCESS' COMMENT 'SUCCESS, FAILED, NO_DATA',
    error_message TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_trade_date (trade_date),
    INDEX idx_category (deal_category),
    UNIQUE KEY uk_import_log (trade_date, deal_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Import history for Block & Bulk Deals';

-- ============================================================================
-- Views for Analysis
-- ============================================================================

-- Top Block Deal Clients by Volume
CREATE OR REPLACE VIEW vw_top_block_clients AS
SELECT 
    client_name,
    COUNT(*) as total_deals,
    SUM(CASE WHEN deal_type = 'BUY' THEN 1 ELSE 0 END) as buy_deals,
    SUM(CASE WHEN deal_type = 'SELL' THEN 1 ELSE 0 END) as sell_deals,
    SUM(quantity) as total_quantity,
    SUM(quantity * trade_price) as total_value,
    MAX(trade_date) as last_deal_date
FROM nse_block_deals
GROUP BY client_name
ORDER BY total_value DESC
LIMIT 100;

-- Top Bulk Deal Clients by Volume
CREATE OR REPLACE VIEW vw_top_bulk_clients AS
SELECT 
    client_name,
    COUNT(*) as total_deals,
    SUM(CASE WHEN deal_type = 'BUY' THEN 1 ELSE 0 END) as buy_deals,
    SUM(CASE WHEN deal_type = 'SELL' THEN 1 ELSE 0 END) as sell_deals,
    SUM(quantity) as total_quantity,
    SUM(quantity * trade_price) as total_value,
    MAX(trade_date) as last_deal_date
FROM nse_bulk_deals
GROUP BY client_name
ORDER BY total_value DESC
LIMIT 100;

-- Recent Block Deals (Last 30 days)
CREATE OR REPLACE VIEW vw_recent_block_deals AS
SELECT 
    trade_date,
    symbol,
    security_name,
    client_name,
    deal_type,
    quantity,
    trade_price,
    ROUND(quantity * trade_price / 10000000, 2) as value_cr
FROM nse_block_deals
WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY trade_date DESC, value_cr DESC;

-- Recent Bulk Deals (Last 30 days)
CREATE OR REPLACE VIEW vw_recent_bulk_deals AS
SELECT 
    trade_date,
    symbol,
    security_name,
    client_name,
    deal_type,
    quantity,
    trade_price,
    ROUND(quantity * trade_price / 10000000, 2) as value_cr
FROM nse_bulk_deals
WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY trade_date DESC, value_cr DESC;

-- Symbol-wise Block Deal Summary
CREATE OR REPLACE VIEW vw_symbol_block_summary AS
SELECT 
    symbol,
    security_name,
    COUNT(*) as total_deals,
    SUM(CASE WHEN deal_type = 'BUY' THEN quantity ELSE 0 END) as total_buy_qty,
    SUM(CASE WHEN deal_type = 'SELL' THEN quantity ELSE 0 END) as total_sell_qty,
    ROUND(AVG(trade_price), 2) as avg_price,
    MAX(trade_date) as last_deal_date,
    COUNT(DISTINCT client_name) as unique_clients
FROM nse_block_deals
GROUP BY symbol, security_name
HAVING total_deals >= 5
ORDER BY total_deals DESC;

-- Symbol-wise Bulk Deal Summary
CREATE OR REPLACE VIEW vw_symbol_bulk_summary AS
SELECT 
    symbol,
    security_name,
    COUNT(*) as total_deals,
    SUM(CASE WHEN deal_type = 'BUY' THEN quantity ELSE 0 END) as total_buy_qty,
    SUM(CASE WHEN deal_type = 'SELL' THEN quantity ELSE 0 END) as total_sell_qty,
    ROUND(AVG(trade_price), 2) as avg_price,
    MAX(trade_date) as last_deal_date,
    COUNT(DISTINCT client_name) as unique_clients
FROM nse_bulk_deals
GROUP BY symbol, security_name
HAVING total_deals >= 5
ORDER BY total_deals DESC;

-- ============================================================================
-- Summary Queries (uncomment to run)
-- ============================================================================

-- SELECT COUNT(*) as total_block_deals FROM nse_block_deals;
-- SELECT COUNT(*) as total_bulk_deals FROM nse_bulk_deals;
-- SELECT MIN(trade_date) as earliest_date, MAX(trade_date) as latest_date FROM nse_block_deals;
-- SELECT MIN(trade_date) as earliest_date, MAX(trade_date) as latest_date FROM nse_bulk_deals;
