-- Intraday Advance-Decline Tables Schema
-- =========================================
-- Tables for storing real-time intraday breadth data

USE marketdata;

-- Table 1: Intraday Advance-Decline Snapshots
-- Stores breadth metrics captured every 5 minutes during market hours
DROP TABLE IF EXISTS intraday_advance_decline;
CREATE TABLE intraday_advance_decline (
    id INT AUTO_INCREMENT PRIMARY KEY,
    poll_time DATETIME NOT NULL COMMENT 'When data was fetched',
    trade_date DATE NOT NULL COMMENT 'Trading day',
    
    -- Counts
    advances INT NOT NULL DEFAULT 0 COMMENT 'Number of advancing stocks',
    declines INT NOT NULL DEFAULT 0 COMMENT 'Number of declining stocks',
    unchanged INT NOT NULL DEFAULT 0 COMMENT 'Number of unchanged stocks',
    total_stocks INT NOT NULL DEFAULT 0 COMMENT 'Total stocks tracked',
    
    -- Percentages
    adv_pct DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Percentage advancing',
    decl_pct DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Percentage declining',
    unch_pct DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Percentage unchanged',
    
    -- Ratios and differences
    adv_decl_ratio DECIMAL(8,2) DEFAULT NULL COMMENT 'Advance/Decline ratio',
    adv_decl_diff INT DEFAULT 0 COMMENT 'Advances - Declines',
    
    -- Metadata
    market_sentiment VARCHAR(50) DEFAULT NULL COMMENT 'BULLISH/BEARISH/NEUTRAL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_trade_date (trade_date),
    INDEX idx_poll_time (poll_time),
    INDEX idx_trade_date_poll_time (trade_date, poll_time),
    UNIQUE KEY unique_poll (trade_date, poll_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Intraday advance-decline snapshots (5-min intervals)';


-- Table 2: Intraday Stock Prices (Optional - for detailed analysis)
-- Stores individual stock prices at each polling cycle
DROP TABLE IF EXISTS intraday_stock_prices;
CREATE TABLE intraday_stock_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    poll_time DATETIME NOT NULL COMMENT 'When data was fetched',
    trade_date DATE NOT NULL COMMENT 'Trading day',
    symbol VARCHAR(50) NOT NULL COMMENT 'Stock symbol',
    
    -- Price data
    ltp DECIMAL(10,2) NOT NULL COMMENT 'Last traded price',
    prev_close DECIMAL(10,2) NOT NULL COMMENT 'Previous day close',
    change_amt DECIMAL(10,2) AS (ltp - prev_close) STORED COMMENT 'Price change',
    change_pct DECIMAL(8,2) NOT NULL COMMENT 'Percentage change',
    
    -- Volume
    volume BIGINT DEFAULT 0 COMMENT 'Trading volume',
    
    -- Status
    status ENUM('ADVANCE', 'DECLINE', 'UNCHANGED') AS (
        CASE 
            WHEN ltp > prev_close THEN 'ADVANCE'
            WHEN ltp < prev_close THEN 'DECLINE'
            ELSE 'UNCHANGED'
        END
    ) STORED COMMENT 'Stock status',
    
    -- Metadata
    data_timestamp DATETIME DEFAULT NULL COMMENT 'Timestamp from data source',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_poll_time (poll_time),
    INDEX idx_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date_poll_time (trade_date, poll_time),
    UNIQUE KEY unique_poll_symbol (trade_date, poll_time, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Individual stock prices at each polling cycle';


-- View 1: Latest Intraday Snapshot
CREATE OR REPLACE VIEW v_latest_intraday_breadth AS
SELECT *
FROM intraday_advance_decline
WHERE trade_date = CURDATE()
ORDER BY poll_time DESC
LIMIT 1;


-- View 2: Today's Intraday Time Series
CREATE OR REPLACE VIEW v_today_intraday_timeseries AS
SELECT 
    poll_time,
    TIME(poll_time) as time_of_day,
    advances,
    declines,
    unchanged,
    total_stocks,
    adv_pct,
    adv_decl_ratio,
    adv_decl_diff,
    market_sentiment
FROM intraday_advance_decline
WHERE trade_date = CURDATE()
ORDER BY poll_time;


-- View 3: Top Movers Current Session
CREATE OR REPLACE VIEW v_top_movers_today AS
SELECT 
    symbol,
    ltp,
    prev_close,
    change_amt,
    change_pct,
    volume,
    status,
    poll_time
FROM intraday_stock_prices
WHERE trade_date = CURDATE()
    AND poll_time = (
        SELECT MAX(poll_time) 
        FROM intraday_stock_prices 
        WHERE trade_date = CURDATE()
    )
ORDER BY ABS(change_pct) DESC
LIMIT 50;


-- View 4: Market Breadth Summary by Day
CREATE OR REPLACE VIEW v_intraday_breadth_summary AS
SELECT 
    trade_date,
    COUNT(*) as num_snapshots,
    MIN(poll_time) as first_snapshot,
    MAX(poll_time) as last_snapshot,
    AVG(adv_pct) as avg_adv_pct,
    AVG(adv_decl_ratio) as avg_adv_decl_ratio,
    MAX(advances) as max_advances,
    MAX(declines) as max_declines
FROM intraday_advance_decline
GROUP BY trade_date
ORDER BY trade_date DESC;


-- Sample Queries
-- ===============

-- Q1: Get all snapshots for today
-- SELECT * FROM v_today_intraday_timeseries;

-- Q2: Get latest breadth reading
-- SELECT * FROM v_latest_intraday_breadth;

-- Q3: Top gainers right now
-- SELECT * FROM v_top_movers_today WHERE status = 'ADVANCE' LIMIT 10;

-- Q4: Top losers right now  
-- SELECT * FROM v_top_movers_today WHERE status = 'DECLINE' LIMIT 10;

-- Q5: Intraday trend for specific stock
-- SELECT poll_time, ltp, change_pct, volume
-- FROM intraday_stock_prices
-- WHERE trade_date = CURDATE() AND symbol = 'RELIANCE.NS'
-- ORDER BY poll_time;

-- Q6: Count how many polls completed today
-- SELECT COUNT(*) as num_polls, 
--        MIN(poll_time) as first_poll,
--        MAX(poll_time) as last_poll
-- FROM intraday_advance_decline
-- WHERE trade_date = CURDATE();

-- Q7: Breadth trend throughout the day
-- SELECT 
--     TIME(poll_time) as time,
--     advances,
--     declines,
--     adv_pct,
--     market_sentiment
-- FROM intraday_advance_decline
-- WHERE trade_date = CURDATE()
-- ORDER BY poll_time;
