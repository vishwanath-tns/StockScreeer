-- Stock Rankings Database Schema
-- Tables for storing stock ranking scores and history

-- Main rankings table (current scores - upserted daily)
CREATE TABLE IF NOT EXISTS stock_rankings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Individual scores
    rs_rating DECIMAL(5,2) DEFAULT 0,           -- 1-99 scale
    momentum_score DECIMAL(5,2) DEFAULT 0,       -- 0-100 scale
    trend_template_score TINYINT DEFAULT 0,      -- 0-8 (conditions passed)
    technical_score DECIMAL(5,2) DEFAULT 0,      -- 0-100 scale
    composite_score DECIMAL(5,2) DEFAULT 0,      -- 0-100 scale
    
    -- Ranks (1 = best)
    rs_rank INT DEFAULT 0,
    momentum_rank INT DEFAULT 0,
    technical_rank INT DEFAULT 0,
    composite_rank INT DEFAULT 0,
    
    -- Percentiles (99 = top 1%)
    composite_percentile DECIMAL(5,2) DEFAULT 0,
    
    -- Metadata
    total_stocks_ranked INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Unique constraint for upsert
    UNIQUE KEY uk_symbol_date (symbol, calculation_date),
    INDEX idx_date (calculation_date),
    INDEX idx_composite_rank (calculation_date, composite_rank),
    INDEX idx_rs_rating (calculation_date, rs_rating DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Historical rankings table (daily snapshots for backtesting)
CREATE TABLE IF NOT EXISTS stock_rankings_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    ranking_date DATE NOT NULL,
    
    -- Scores snapshot
    rs_rating DECIMAL(5,2) DEFAULT 0,
    momentum_score DECIMAL(5,2) DEFAULT 0,
    trend_template_score TINYINT DEFAULT 0,
    technical_score DECIMAL(5,2) DEFAULT 0,
    composite_score DECIMAL(5,2) DEFAULT 0,
    
    -- Ranks snapshot
    composite_rank INT DEFAULT 0,
    composite_percentile DECIMAL(5,2) DEFAULT 0,
    total_stocks_ranked INT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint (one record per symbol per day)
    UNIQUE KEY uk_symbol_ranking_date (symbol, ranking_date),
    INDEX idx_ranking_date (ranking_date),
    INDEX idx_symbol (symbol),
    INDEX idx_composite_percentile (ranking_date, composite_percentile DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Trend template conditions detail (optional - for debugging)
CREATE TABLE IF NOT EXISTS stock_trend_template_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- 8 Trend Template conditions
    cond_price_above_150sma TINYINT(1) DEFAULT 0,
    cond_price_above_200sma TINYINT(1) DEFAULT 0,
    cond_150sma_above_200sma TINYINT(1) DEFAULT 0,
    cond_200sma_trending_up TINYINT(1) DEFAULT 0,
    cond_50sma_above_150sma TINYINT(1) DEFAULT 0,
    cond_50sma_above_200sma TINYINT(1) DEFAULT 0,
    cond_price_above_50sma TINYINT(1) DEFAULT 0,
    cond_price_near_52w_high TINYINT(1) DEFAULT 0,
    
    -- Actual values for debugging
    price DECIMAL(12,2),
    sma_50 DECIMAL(12,2),
    sma_150 DECIMAL(12,2),
    sma_200 DECIMAL(12,2),
    rsi DECIMAL(5,2),
    pct_from_52w_high DECIMAL(5,2),
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_symbol_date (symbol, calculation_date),
    INDEX idx_date (calculation_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
