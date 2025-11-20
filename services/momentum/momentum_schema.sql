-- Momentum Analysis Database Schema
-- ====================================

-- Table to store momentum calculations for different durations
CREATE TABLE IF NOT EXISTS momentum_analysis (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Stock identification
    symbol VARCHAR(50) NOT NULL,
    series VARCHAR(10) NOT NULL DEFAULT 'EQ',
    
    -- Duration specification
    duration_type ENUM('1W', '1M', '3M', '6M', '9M', '12M') NOT NULL,
    duration_days INT NOT NULL,
    
    -- Date range for calculation
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Price data
    start_price DECIMAL(15, 4) NOT NULL,
    end_price DECIMAL(15, 4) NOT NULL,
    high_price DECIMAL(15, 4) NOT NULL,
    low_price DECIMAL(15, 4) NOT NULL,
    
    -- Momentum metrics
    absolute_change DECIMAL(15, 4) NOT NULL,
    percentage_change DECIMAL(10, 4) NOT NULL,
    
    -- Volume metrics
    avg_volume BIGINT,
    total_volume BIGINT,
    volume_surge_factor DECIMAL(8, 4),
    
    -- Volatility metrics
    price_volatility DECIMAL(8, 4),
    high_low_ratio DECIMAL(8, 4),
    
    -- Performance ranking
    percentile_rank DECIMAL(5, 2),
    sector_rank INT,
    overall_rank INT,
    
    -- Metadata
    trading_days INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_symbol_duration_date (symbol, duration_type, end_date),
    INDEX idx_duration_date (duration_type, end_date),
    INDEX idx_percentage_change (duration_type, percentage_change),
    INDEX idx_calculation_date (calculation_date),
    INDEX idx_symbol_calc_date (symbol, calculation_date),
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY uk_momentum (symbol, duration_type, end_date)
) ENGINE=InnoDB;

-- Table to store momentum rankings by duration and date
CREATE TABLE IF NOT EXISTS momentum_rankings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    calculation_date DATE NOT NULL,
    duration_type ENUM('1W', '1M', '3M', '6M', '9M', '12M') NOT NULL,
    
    -- Top performers
    top_gainers JSON,
    top_losers JSON,
    
    -- Statistical summaries
    avg_gain DECIMAL(10, 4),
    median_gain DECIMAL(10, 4),
    std_deviation DECIMAL(10, 4),
    
    -- Counts
    total_stocks INT,
    positive_stocks INT,
    negative_stocks INT,
    
    -- Sector analysis
    best_sector VARCHAR(100),
    worst_sector VARCHAR(100),
    sector_performance JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_calc_duration (calculation_date, duration_type),
    UNIQUE KEY uk_ranking (calculation_date, duration_type)
) ENGINE=InnoDB;

-- Table to store sector-wise momentum analysis
CREATE TABLE IF NOT EXISTS sector_momentum (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    sector VARCHAR(100) NOT NULL,
    duration_type ENUM('1W', '1M', '3M', '6M', '9M', '12M') NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Sector metrics
    stock_count INT NOT NULL,
    avg_momentum DECIMAL(10, 4),
    median_momentum DECIMAL(10, 4),
    sector_rank INT,
    
    -- Performance distribution
    positive_count INT,
    negative_count INT,
    strong_positive_count INT, -- > 10%
    strong_negative_count INT, -- < -10%
    
    -- Best and worst in sector
    best_performer VARCHAR(50),
    best_performance DECIMAL(10, 4),
    worst_performer VARCHAR(50),
    worst_performance DECIMAL(10, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_sector_duration_date (sector, duration_type, calculation_date),
    INDEX idx_duration_rank (duration_type, sector_rank),
    UNIQUE KEY uk_sector_momentum (sector, duration_type, calculation_date)
) ENGINE=InnoDB;

-- Table to track momentum calculation jobs and status
CREATE TABLE IF NOT EXISTS momentum_calculation_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    job_id VARCHAR(100) NOT NULL UNIQUE,
    duration_type ENUM('1W', '1M', '3M', '6M', '9M', '12M') NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Job status
    status ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    
    -- Progress tracking
    total_symbols INT,
    processed_symbols INT,
    failed_symbols INT,
    
    -- Results summary
    results_summary JSON,
    error_details TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_status_date (status, calculation_date),
    INDEX idx_duration_date (duration_type, calculation_date)
) ENGINE=InnoDB;

-- Create summary view for quick reporting
CREATE OR REPLACE VIEW momentum_summary AS
SELECT 
    m.symbol,
    m.duration_type,
    m.end_date,
    m.percentage_change,
    m.percentile_rank,
    m.overall_rank,
    m.trading_days,
    -- Add sector information if available (you may need to join with a stocks master table)
    'Technology' as sector  -- Placeholder - replace with actual sector lookup
FROM momentum_analysis m
WHERE m.calculation_date = (
    SELECT MAX(calculation_date) 
    FROM momentum_analysis m2 
    WHERE m2.symbol = m.symbol AND m2.duration_type = m.duration_type
);

-- Performance monitoring indexes
CREATE INDEX idx_momentum_performance ON momentum_analysis(end_date, duration_type, percentage_change DESC);
CREATE INDEX idx_momentum_volume ON momentum_analysis(duration_type, volume_surge_factor DESC);

DELIMITER //

-- Stored procedure to clean old momentum data (keep last 90 days)
CREATE PROCEDURE CleanOldMomentumData()
BEGIN
    DECLARE cutoff_date DATE DEFAULT DATE_SUB(CURDATE(), INTERVAL 90 DAY);
    
    DELETE FROM momentum_analysis WHERE calculation_date < cutoff_date;
    DELETE FROM momentum_rankings WHERE calculation_date < cutoff_date;
    DELETE FROM sector_momentum WHERE calculation_date < cutoff_date;
    DELETE FROM momentum_calculation_jobs WHERE calculation_date < cutoff_date;
    
    SELECT ROW_COUNT() as deleted_rows;
END//

-- Function to get momentum duration in days
CREATE FUNCTION GetMomentumDurationDays(duration_type VARCHAR(10))
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    RETURN CASE duration_type
        WHEN '1W' THEN 7
        WHEN '1M' THEN 30
        WHEN '3M' THEN 90
        WHEN '6M' THEN 180
        WHEN '9M' THEN 270
        WHEN '12M' THEN 365
        ELSE 30
    END;
END//

DELIMITER ;