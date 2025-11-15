-- NSE Indices Database Schema
-- ===========================
-- This schema supports storing NSE indices and their constituents
-- with historical tracking and analysis capabilities

-- Table 1: NSE Indices Master Table
-- Stores index metadata and information
CREATE TABLE nse_indices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(100) NOT NULL,
    index_code VARCHAR(50) NOT NULL,
    description TEXT,
    category VARCHAR(50), -- e.g., 'MAIN', 'SECTORAL', 'THEMATIC'
    sector VARCHAR(100), -- e.g., 'BANKING', 'IT', 'PHARMA', 'AUTO'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_index_code (index_code),
    INDEX idx_category (category),
    INDEX idx_sector (sector),
    INDEX idx_active (is_active)
);

-- Table 2: Index Data Snapshots
-- Stores index-level data for each date
CREATE TABLE nse_index_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    index_id INT NOT NULL,
    data_date DATE NOT NULL,
    open_value DECIMAL(12, 2),
    high_value DECIMAL(12, 2),
    low_value DECIMAL(12, 2),
    close_value DECIMAL(12, 2),
    prev_close DECIMAL(12, 2),
    change_points DECIMAL(10, 2),
    change_percent DECIMAL(8, 4),
    volume BIGINT,
    value_crores DECIMAL(12, 2),
    week52_high DECIMAL(12, 2),
    week52_low DECIMAL(12, 2),
    change_30d_percent DECIMAL(8, 4),
    change_365d_percent DECIMAL(8, 4),
    file_source VARCHAR(255), -- Source file name
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (index_id) REFERENCES nse_indices(id) ON DELETE CASCADE,
    UNIQUE KEY unique_index_date (index_id, data_date),
    INDEX idx_data_date (data_date),
    INDEX idx_index_id (index_id)
);

-- Table 3: Index Constituents
-- Stores the stocks that belong to each index on specific dates
CREATE TABLE nse_index_constituents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    index_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    data_date DATE NOT NULL,
    open_price DECIMAL(10, 2),
    high_price DECIMAL(10, 2),
    low_price DECIMAL(10, 2),
    close_price DECIMAL(10, 2),
    prev_close DECIMAL(10, 2),
    ltp DECIMAL(10, 2), -- Last Traded Price
    change_points DECIMAL(8, 2),
    change_percent DECIMAL(8, 4),
    volume BIGINT,
    value_crores DECIMAL(10, 2),
    week52_high DECIMAL(10, 2),
    week52_low DECIMAL(10, 2),
    change_30d_percent DECIMAL(8, 4),
    change_365d_percent DECIMAL(8, 4),
    weight_percent DECIMAL(8, 4), -- Stock weight in index (if available)
    is_active BOOLEAN DEFAULT TRUE, -- Whether stock is currently in index
    file_source VARCHAR(255), -- Source file name
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (index_id) REFERENCES nse_indices(id) ON DELETE CASCADE,
    INDEX idx_symbol (symbol),
    INDEX idx_index_date (index_id, data_date),
    INDEX idx_data_date (data_date),
    INDEX idx_active (is_active),
    INDEX idx_symbol_date (symbol, data_date)
);

-- Table 4: Data Import Log
-- Tracks file imports and processing status
CREATE TABLE index_import_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    index_code VARCHAR(50),
    data_date DATE,
    file_size BIGINT,
    records_processed INT DEFAULT 0,
    records_imported INT DEFAULT 0,
    status ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
    error_message TEXT,
    file_hash VARCHAR(64), -- MD5 hash to detect duplicate imports
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    UNIQUE KEY unique_file_hash (file_hash),
    INDEX idx_filename (filename),
    INDEX idx_status (status),
    INDEX idx_date (data_date)
);

-- Predefined Index Categories and their mappings
INSERT INTO nse_indices (index_code, index_name, category, sector, description) VALUES
('NIFTY-50', 'Nifty 50', 'MAIN', 'BROAD_MARKET', 'Top 50 companies by market capitalization'),
('NIFTY-NEXT-50', 'Nifty Next 50', 'MAIN', 'BROAD_MARKET', 'Next 50 largest companies after Nifty 50'),
('NIFTY-MIDCAP-SELECT', 'Nifty Midcap Select', 'MAIN', 'BROAD_MARKET', 'Selected midcap companies'),

-- Banking & Financial Services
('NIFTY-BANK', 'Nifty Bank', 'SECTORAL', 'BANKING', 'Banking sector index'),
('NIFTY-FINANCIAL-SERVICES', 'Nifty Financial Services', 'SECTORAL', 'FINANCIAL_SERVICES', 'Financial services sector index'),
('NIFTY-FINANCIAL-SERVICES-25_50', 'Nifty Financial Services 25/50', 'SECTORAL', 'FINANCIAL_SERVICES', 'Financial services 25/50 index'),
('NIFTY-FINANCIAL-SERVICES-EX-BANK', 'Nifty Financial Services Ex-Bank', 'SECTORAL', 'FINANCIAL_SERVICES', 'Financial services excluding banking'),
('NIFTY-PRIVATE-BANK', 'Nifty Private Bank', 'SECTORAL', 'BANKING', 'Private sector banks'),
('NIFTY-PSU-BANK', 'Nifty PSU Bank', 'SECTORAL', 'BANKING', 'Public sector banks'),
('NIFTY-MIDSMALL-FINANCIAL-SERVICES', 'Nifty MidSmall Financial Services', 'SECTORAL', 'FINANCIAL_SERVICES', 'Mid and small cap financial services'),

-- Sector Indices
('NIFTY-AUTO', 'Nifty Auto', 'SECTORAL', 'AUTOMOBILE', 'Automobile sector index'),
('NIFTY-CHEMICALS', 'Nifty Chemicals', 'SECTORAL', 'CHEMICALS', 'Chemicals sector index'),
('NIFTY-CONSUMER-DURABLES', 'Nifty Consumer Durables', 'SECTORAL', 'CONSUMER_DURABLES', 'Consumer durables sector index'),
('NIFTY-FMCG', 'Nifty FMCG', 'SECTORAL', 'FMCG', 'Fast moving consumer goods sector index'),
('NIFTY-IT', 'Nifty IT', 'SECTORAL', 'INFORMATION_TECHNOLOGY', 'Information technology sector index'),
('NIFTY-MEDIA', 'Nifty Media', 'SECTORAL', 'MEDIA', 'Media sector index'),
('NIFTY-METAL', 'Nifty Metal', 'SECTORAL', 'METALS', 'Metals sector index'),
('NIFTY-OIL-&-GAS', 'Nifty Oil & Gas', 'SECTORAL', 'OIL_GAS', 'Oil and gas sector index'),
('NIFTY-PHARMA', 'Nifty Pharma', 'SECTORAL', 'PHARMACEUTICALS', 'Pharmaceuticals sector index'),
('NIFTY-REALTY', 'Nifty Realty', 'SECTORAL', 'REAL_ESTATE', 'Real estate sector index'),

-- Healthcare Indices
('NIFTY-HEALTHCARE-INDEX', 'Nifty Healthcare Index', 'SECTORAL', 'HEALTHCARE', 'Healthcare sector index'),
('NIFTY-MIDSMALL-HEALTHCARE', 'Nifty MidSmall Healthcare', 'SECTORAL', 'HEALTHCARE', 'Mid and small cap healthcare'),
('NIFTY500-HEALTHCARE', 'Nifty500 Healthcare', 'SECTORAL', 'HEALTHCARE', 'Nifty 500 healthcare index'),

-- Technology
('NIFTY-MIDSMALL-IT-&-TELECOM', 'Nifty MidSmall IT & Telecom', 'SECTORAL', 'TECHNOLOGY', 'Mid and small cap IT and telecom');

-- Create views for easy data access
CREATE VIEW v_latest_index_data AS
SELECT 
    ni.index_code,
    ni.index_name,
    ni.category,
    ni.sector,
    nid.data_date,
    nid.close_value,
    nid.change_points,
    nid.change_percent,
    nid.volume,
    nid.value_crores
FROM nse_indices ni
JOIN nse_index_data nid ON ni.id = nid.index_id
WHERE nid.data_date = (
    SELECT MAX(data_date) 
    FROM nse_index_data nid2 
    WHERE nid2.index_id = ni.id
);

CREATE VIEW v_latest_constituents AS
SELECT 
    ni.index_code,
    ni.index_name,
    nic.symbol,
    nic.data_date,
    nic.close_price,
    nic.change_percent,
    nic.volume,
    nic.weight_percent
FROM nse_indices ni
JOIN nse_index_constituents nic ON ni.id = nic.index_id
WHERE nic.data_date = (
    SELECT MAX(data_date) 
    FROM nse_index_constituents nic2 
    WHERE nic2.index_id = ni.id
)
ORDER BY ni.index_code, nic.symbol;