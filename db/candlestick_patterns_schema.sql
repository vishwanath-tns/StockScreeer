-- Candlestick Pattern Database Schema
-- =====================================

-- Table to store detected candlestick patterns
CREATE TABLE IF NOT EXISTS candlestick_patterns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    pattern_date DATE NOT NULL,
    pattern_type ENUM('NR4', 'NR7', 'NR13', 'NR21', 'NR30', 'NR50') NOT NULL,
    timeframe ENUM('DAILY', 'WEEKLY', 'MONTHLY') NOT NULL DEFAULT 'MONTHLY',
    
    -- Range calculation data
    current_range DECIMAL(15,4) NOT NULL,
    range_rank INTEGER NOT NULL,  -- Rank among last N periods
    range_percentile DECIMAL(5,2),  -- Percentile within comparison periods
    
    -- OHLC data for the pattern day
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    close_price DECIMAL(15,4),
    volume BIGINT,
    
    -- Context data
    comparison_periods INTEGER NOT NULL,  -- Number of periods used for comparison (4, 7, 13, etc.)
    avg_range_comparison DECIMAL(15,4),   -- Average range of comparison periods
    
    -- Metadata
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    UNIQUE KEY unique_pattern (symbol, pattern_date, pattern_type, timeframe),
    INDEX idx_symbol_date (symbol, pattern_date),
    INDEX idx_pattern_type (pattern_type),
    INDEX idx_date_range (pattern_date, pattern_type),
    INDEX idx_symbol_type (symbol, pattern_type),
    INDEX idx_timeframe (timeframe)
);

-- Table to track pattern detection jobs and progress
CREATE TABLE IF NOT EXISTS pattern_detection_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    start_date DATE,
    end_date DATE,
    timeframe ENUM('DAILY', 'WEEKLY', 'MONTHLY') NOT NULL,
    pattern_types JSON,  -- Array of pattern types to detect
    
    -- Progress tracking
    total_symbols INTEGER DEFAULT 0,
    processed_symbols INTEGER DEFAULT 0,
    patterns_detected INTEGER DEFAULT 0,
    status ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
    
    -- Performance metrics
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    processing_time_seconds INTEGER,
    error_message TEXT,
    
    -- Configuration
    batch_size INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_timeframe_job (timeframe),
    INDEX idx_created_at (created_at)
);

-- View for easy pattern analysis
CREATE OR REPLACE VIEW v_latest_patterns AS
SELECT 
    cp.*,
    ROW_NUMBER() OVER (PARTITION BY cp.symbol ORDER BY cp.pattern_date DESC) as recency_rank
FROM candlestick_patterns cp
WHERE cp.pattern_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY);

-- View for pattern statistics
CREATE OR REPLACE VIEW v_pattern_statistics AS
SELECT 
    pattern_type,
    timeframe,
    COUNT(*) as total_patterns,
    COUNT(DISTINCT symbol) as unique_symbols,
    AVG(range_percentile) as avg_percentile,
    MIN(pattern_date) as earliest_date,
    MAX(pattern_date) as latest_date
FROM candlestick_patterns
GROUP BY pattern_type, timeframe;