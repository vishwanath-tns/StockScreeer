-- Additional table for storing raw 1-minute candle data
-- This stores ALL 1-min OHLCV data fetched during polling for future analysis

USE marketdata;

-- Table: Raw 1-minute candle data from each poll
DROP TABLE IF EXISTS intraday_1min_candles;
CREATE TABLE intraday_1min_candles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Polling metadata
    poll_time DATETIME NOT NULL COMMENT 'When we fetched this data',
    trade_date DATE NOT NULL COMMENT 'Trading day',
    
    -- Stock identification
    symbol VARCHAR(50) NOT NULL COMMENT 'Stock symbol (e.g., RELIANCE.NS)',
    
    -- Candle timestamp (from Yahoo Finance)
    candle_timestamp DATETIME NOT NULL COMMENT 'Timestamp of the 1-min candle',
    
    -- OHLCV data
    open_price DECIMAL(12,2) NOT NULL COMMENT 'Open price',
    high_price DECIMAL(12,2) NOT NULL COMMENT 'High price',
    low_price DECIMAL(12,2) NOT NULL COMMENT 'Low price',
    close_price DECIMAL(12,2) NOT NULL COMMENT 'Close price (LTP)',
    volume BIGINT NOT NULL DEFAULT 0 COMMENT 'Volume traded in this minute',
    
    -- Comparison with previous close
    prev_close DECIMAL(12,2) DEFAULT NULL COMMENT 'Previous day close',
    change_amt DECIMAL(10,2) AS (close_price - prev_close) STORED COMMENT 'Price change',
    change_pct DECIMAL(8,2) AS (
        CASE 
            WHEN prev_close > 0 THEN ((close_price - prev_close) / prev_close * 100)
            ELSE 0 
        END
    ) STORED COMMENT 'Percentage change',
    
    -- Status
    status ENUM('ADVANCE', 'DECLINE', 'UNCHANGED') AS (
        CASE 
            WHEN close_price > prev_close THEN 'ADVANCE'
            WHEN close_price < prev_close THEN 'DECLINE'
            ELSE 'UNCHANGED'
        END
    ) STORED COMMENT 'Stock status vs prev close',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for fast queries
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_poll_time (poll_time),
    INDEX idx_candle_timestamp (candle_timestamp),
    INDEX idx_trade_date_symbol (trade_date, symbol),
    INDEX idx_symbol_candle_time (symbol, candle_timestamp),
    
    -- Prevent duplicates: same stock, same candle time, same poll
    UNIQUE KEY unique_poll_symbol_candle (poll_time, symbol, candle_timestamp)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Raw 1-minute candle data from each polling cycle - full OHLCV history';


-- View: Latest 1-min candles for all stocks
CREATE OR REPLACE VIEW v_latest_1min_candles AS
SELECT 
    symbol,
    candle_timestamp,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    prev_close,
    change_amt,
    change_pct,
    status,
    poll_time
FROM intraday_1min_candles
WHERE poll_time = (SELECT MAX(poll_time) FROM intraday_1min_candles WHERE trade_date = CURDATE())
    AND trade_date = CURDATE()
ORDER BY symbol;


-- View: Complete 1-min time series for a trading day (all candles for all stocks)
CREATE OR REPLACE VIEW v_intraday_1min_timeseries AS
SELECT 
    candle_timestamp,
    symbol,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    prev_close,
    change_pct,
    status,
    poll_time
FROM intraday_1min_candles
WHERE trade_date = CURDATE()
ORDER BY candle_timestamp, symbol;


-- View: Aggregate stats per stock for today
CREATE OR REPLACE VIEW v_intraday_stock_summary AS
SELECT 
    symbol,
    COUNT(DISTINCT candle_timestamp) as num_candles,
    MIN(candle_timestamp) as first_candle,
    MAX(candle_timestamp) as last_candle,
    MIN(low_price) as day_low,
    MAX(high_price) as day_high,
    SUM(volume) as total_volume,
    AVG(change_pct) as avg_change_pct,
    MAX(ABS(change_pct)) as max_change_pct
FROM intraday_1min_candles
WHERE trade_date = CURDATE()
GROUP BY symbol
ORDER BY total_volume DESC;


-- Sample Queries for Future Analysis
-- ====================================

-- Q1: Get all 1-min candles for a specific stock today
-- SELECT * FROM intraday_1min_candles 
-- WHERE symbol = 'RELIANCE.NS' AND trade_date = CURDATE()
-- ORDER BY candle_timestamp;

-- Q2: Get OHLC data for 5-minute bars (aggregate 1-min candles)
-- SELECT 
--     symbol,
--     DATE_FORMAT(candle_timestamp, '%Y-%m-%d %H:%i:00') as time_bucket,
--     MIN(open_price) as open,
--     MAX(high_price) as high,
--     MIN(low_price) as low,
--     MAX(close_price) as close,
--     SUM(volume) as volume
-- FROM intraday_1min_candles
-- WHERE symbol = 'RELIANCE.NS' AND trade_date = CURDATE()
-- GROUP BY symbol, time_bucket
-- ORDER BY time_bucket;

-- Q3: Get volume profile (volume at each price level)
-- SELECT 
--     symbol,
--     ROUND(close_price, 0) as price_level,
--     SUM(volume) as total_volume,
--     COUNT(*) as num_candles
-- FROM intraday_1min_candles
-- WHERE symbol = 'RELIANCE.NS' AND trade_date = CURDATE()
-- GROUP BY symbol, price_level
-- ORDER BY total_volume DESC;

-- Q4: Get most active 1-minute candles (highest volume)
-- SELECT 
--     candle_timestamp,
--     symbol,
--     close_price,
--     volume,
--     change_pct
-- FROM intraday_1min_candles
-- WHERE trade_date = CURDATE()
-- ORDER BY volume DESC
-- LIMIT 50;

-- Q5: Count total candles stored per day
-- SELECT 
--     trade_date,
--     COUNT(*) as total_candles,
--     COUNT(DISTINCT symbol) as num_stocks,
--     COUNT(DISTINCT candle_timestamp) as num_unique_timestamps
-- FROM intraday_1min_candles
-- GROUP BY trade_date
-- ORDER BY trade_date DESC;

-- Q6: Get intraday high/low for each stock
-- SELECT 
--     symbol,
--     MIN(low_price) as day_low,
--     MAX(high_price) as day_high,
--     (MAX(high_price) - MIN(low_price)) as range_amt,
--     ((MAX(high_price) - MIN(low_price)) / MIN(low_price) * 100) as range_pct
-- FROM intraday_1min_candles
-- WHERE trade_date = CURDATE()
-- GROUP BY symbol
-- ORDER BY range_pct DESC;
