-- Nifty 500 Advance-Decline Analysis Schema
-- Database: marketdata
-- Purpose: Store daily advance/decline counts for Nifty 500 stocks from Yahoo Finance data

USE marketdata;

-- Table: nifty500_advance_decline
-- Stores daily advance/decline/unchanged counts for Nifty 500 stocks
CREATE TABLE IF NOT EXISTS nifty500_advance_decline (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    advances INT NOT NULL DEFAULT 0,
    declines INT NOT NULL DEFAULT 0,
    unchanged INT NOT NULL DEFAULT 0,
    total_stocks INT NOT NULL DEFAULT 0,
    
    -- Percentage metrics
    advance_pct DECIMAL(5,2) NULL,
    decline_pct DECIMAL(5,2) NULL,
    unchanged_pct DECIMAL(5,2) NULL,
    
    -- Breadth indicators
    advance_decline_ratio DECIMAL(10,4) NULL,  -- advances/declines
    advance_decline_diff INT NULL,              -- advances - declines
    
    -- Source tracking
    source VARCHAR(50) DEFAULT 'yfinance_daily_quotes',
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_trade_date (trade_date),
    INDEX idx_computed_at (computed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Daily advance/decline counts for Nifty 500 stocks';

-- View: Recent advance-decline summary
CREATE OR REPLACE VIEW v_nifty500_adv_decl_recent AS
SELECT 
    trade_date,
    advances,
    declines,
    unchanged,
    total_stocks,
    advance_pct,
    decline_pct,
    unchanged_pct,
    advance_decline_ratio,
    advance_decline_diff,
    CASE 
        WHEN advance_pct >= 70 THEN 'Very Bullish'
        WHEN advance_pct >= 55 THEN 'Bullish'
        WHEN advance_pct >= 45 THEN 'Neutral'
        WHEN advance_pct >= 30 THEN 'Bearish'
        ELSE 'Very Bearish'
    END as market_sentiment,
    computed_at
FROM nifty500_advance_decline
ORDER BY trade_date DESC
LIMIT 90;

-- View: Monthly advance-decline summary
CREATE OR REPLACE VIEW v_nifty500_adv_decl_monthly AS
SELECT 
    DATE_FORMAT(trade_date, '%Y-%m') as month,
    COUNT(*) as trading_days,
    AVG(advances) as avg_advances,
    AVG(declines) as avg_declines,
    AVG(unchanged) as avg_unchanged,
    AVG(advance_pct) as avg_advance_pct,
    AVG(decline_pct) as avg_decline_pct,
    SUM(CASE WHEN advance_pct >= 55 THEN 1 ELSE 0 END) as bullish_days,
    SUM(CASE WHEN advance_pct < 45 THEN 1 ELSE 0 END) as bearish_days,
    MIN(trade_date) as month_start,
    MAX(trade_date) as month_end
FROM nifty500_advance_decline
GROUP BY DATE_FORMAT(trade_date, '%Y-%m')
ORDER BY month DESC;

-- Check initial status
SELECT 
    'nifty500_advance_decline' as table_name,
    COUNT(*) as record_count,
    MIN(trade_date) as earliest_date,
    MAX(trade_date) as latest_date,
    AVG(advance_pct) as avg_advance_pct
FROM nifty500_advance_decline;
