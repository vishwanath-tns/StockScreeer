-- Simple Momentum Analysis Database Schema
-- ========================================

-- Table to store momentum calculations for different durations
CREATE TABLE IF NOT EXISTS momentum_analysis (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- Stock identification
    symbol VARCHAR(50) NOT NULL,
    series VARCHAR(10) NOT NULL DEFAULT 'EQ',
    
    -- Duration specification
    duration_type VARCHAR(10) NOT NULL,
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
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY uk_momentum (symbol, duration_type, end_date)
) ENGINE=InnoDB;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_symbol_duration_date ON momentum_analysis(symbol, duration_type, end_date);
CREATE INDEX IF NOT EXISTS idx_duration_date ON momentum_analysis(duration_type, end_date);
CREATE INDEX IF NOT EXISTS idx_percentage_change ON momentum_analysis(duration_type, percentage_change);
CREATE INDEX IF NOT EXISTS idx_calculation_date ON momentum_analysis(calculation_date);
CREATE INDEX IF NOT EXISTS idx_symbol_calc_date ON momentum_analysis(symbol, calculation_date);

-- Table to store momentum rankings by duration and date
CREATE TABLE IF NOT EXISTS momentum_rankings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    calculation_date DATE NOT NULL,
    duration_type VARCHAR(10) NOT NULL,
    
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
    
    UNIQUE KEY uk_ranking (calculation_date, duration_type)
) ENGINE=InnoDB;

CREATE INDEX IF NOT EXISTS idx_calc_duration ON momentum_rankings(calculation_date, duration_type);

-- Table to store sector-wise momentum analysis
CREATE TABLE IF NOT EXISTS sector_momentum (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    sector VARCHAR(100) NOT NULL,
    duration_type VARCHAR(10) NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Sector metrics
    stock_count INT NOT NULL,
    avg_momentum DECIMAL(10, 4),
    median_momentum DECIMAL(10, 4),
    sector_rank INT,
    
    -- Performance distribution
    positive_count INT,
    negative_count INT,
    strong_positive_count INT,
    strong_negative_count INT,
    
    -- Best and worst in sector
    best_performer VARCHAR(50),
    best_performance DECIMAL(10, 4),
    worst_performer VARCHAR(50),
    worst_performance DECIMAL(10, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_sector_momentum (sector, duration_type, calculation_date)
) ENGINE=InnoDB;

CREATE INDEX IF NOT EXISTS idx_sector_duration_date ON sector_momentum(sector, duration_type, calculation_date);
CREATE INDEX IF NOT EXISTS idx_duration_rank ON sector_momentum(duration_type, sector_rank);

-- Table to track momentum calculation jobs and status
CREATE TABLE IF NOT EXISTS momentum_calculation_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    job_id VARCHAR(100) NOT NULL UNIQUE,
    duration_type VARCHAR(10) NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Job status
    status VARCHAR(20) DEFAULT 'PENDING',
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX IF NOT EXISTS idx_status_date ON momentum_calculation_jobs(status, calculation_date);
CREATE INDEX IF NOT EXISTS idx_duration_date_jobs ON momentum_calculation_jobs(duration_type, calculation_date);