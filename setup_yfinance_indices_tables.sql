-- =====================================================
-- Yahoo Finance Indices Tables Setup
-- Database: marketdata
-- =====================================================

USE marketdata;

-- Table 1: yfinance_indices_master
-- Stores metadata about NSE indices available on Yahoo Finance
CREATE TABLE IF NOT EXISTS yfinance_indices_master (
    id INT AUTO_INCREMENT PRIMARY KEY,
    index_code VARCHAR(50) NOT NULL UNIQUE,
    index_name VARCHAR(200) NOT NULL,
    yahoo_symbol VARCHAR(50) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_yahoo_symbol (yahoo_symbol),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table 2: yfinance_indices_daily_quotes
-- Stores daily OHLCV data for NSE indices from Yahoo Finance
CREATE TABLE IF NOT EXISTS yfinance_indices_daily_quotes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12,2) NOT NULL,
    high DECIMAL(12,2) NOT NULL,
    low DECIMAL(12,2) NOT NULL,
    close DECIMAL(12,2) NOT NULL,
    volume BIGINT DEFAULT 0,
    adj_close DECIMAL(12,2),
    timeframe VARCHAR(20) DEFAULT 'Daily',
    source VARCHAR(50) DEFAULT 'Yahoo Finance',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date_timeframe (symbol, date, timeframe),
    INDEX idx_symbol (symbol),
    INDEX idx_date (date),
    INDEX idx_symbol_date (symbol, date),
    INDEX idx_timeframe (timeframe)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert available NSE indices from discovery
INSERT INTO yfinance_indices_master (index_code, index_name, yahoo_symbol, category, description) VALUES
-- BROAD MARKET INDICES
('NIFTY50', 'Nifty 50', '^NSEI', 'BROAD_MARKET', 'Nifty 50 - India''s benchmark stock market index'),
('NIFTYNEXT50', 'Nifty Next 50', '^NSMIDCP', 'BROAD_MARKET', 'Nifty Next 50 - Top 50 companies after Nifty 50'),
('NIFTYLARGEMID250', 'Nifty LargeMidcap 250', 'NIFTY_LARGEMID250.NS', 'BROAD_MARKET', 'Nifty LargeMidcap 250 - Large and midcap stocks'),

-- SECTORAL INDICES
('NIFTYAUTO', 'Nifty Auto', '^CNXAUTO', 'SECTORAL', 'Nifty Auto - Automobile sector index'),
('NIFTYBANK', 'Nifty Bank', '^NSEBANK', 'SECTORAL', 'Nifty Bank - Banking sector index'),
('NIFTYFINSVC', 'Nifty Financial Services', 'NIFTY_FIN_SERVICE.NS', 'SECTORAL', 'Nifty Financial Services - Financial services sector'),
('NIFTYFMCG', 'Nifty FMCG', '^CNXFMCG', 'SECTORAL', 'Nifty FMCG - Fast moving consumer goods sector'),
('NIFTYIT', 'Nifty IT', '^CNXIT', 'SECTORAL', 'Nifty IT - Information technology sector'),
('NIFTYMETAL', 'Nifty Metal', '^CNXMETAL', 'SECTORAL', 'Nifty Metal - Metals sector index'),
('NIFTYPHARMA', 'Nifty Pharma', '^CNXPHARMA', 'SECTORAL', 'Nifty Pharma - Pharmaceutical sector'),
('NIFTYPSUBANK', 'Nifty PSU Bank', '^CNXPSUBANK', 'SECTORAL', 'Nifty PSU Bank - Public sector banks'),
('NIFTYPVTBANK', 'Nifty Private Bank', 'NIFTY_PVT_BANK.NS', 'SECTORAL', 'Nifty Private Bank - Private sector banks'),
('NIFTYREALTY', 'Nifty Realty', '^CNXREALTY', 'SECTORAL', 'Nifty Realty - Real estate sector'),
('NIFTYENERGY', 'Nifty Energy', '^CNXENERGY', 'SECTORAL', 'Nifty Energy - Energy sector index'),
('NIFTYINFRA', 'Nifty Infrastructure', '^CNXINFRA', 'SECTORAL', 'Nifty Infrastructure - Infrastructure sector'),
('NIFTYCPSE', 'Nifty CPSE', 'NIFTY_CPSE.NS', 'SECTORAL', 'Nifty CPSE - Central public sector enterprises'),
('NIFTYOILGAS', 'Nifty Oil & Gas', 'NIFTY_OIL_AND_GAS.NS', 'SECTORAL', 'Nifty Oil & Gas - Oil and gas sector'),
('NIFTYHEALTHCARE', 'Nifty Healthcare Index', 'NIFTY_HEALTHCARE.NS', 'SECTORAL', 'Nifty Healthcare - Healthcare sector'),

-- THEMATIC INDICES
('NIFTYINDIACONSUMPTION', 'Nifty India Consumption', 'NIFTY_CONSR_DURBL.NS', 'THEMATIC', 'Nifty India Consumption - Consumer durables'),
('NIFTYMOBILITY', 'Nifty Mobility', 'NIFTY_MOBILITY.NS', 'THEMATIC', 'Nifty Mobility - Mobility and transportation'),
('NIFTYHOUSING', 'Nifty Housing', 'NIFTY_HOUSING.NS', 'THEMATIC', 'Nifty Housing - Housing sector'),

-- STRATEGY INDICES
('NIFTY100EQLWGT', 'Nifty100 Equal Weight', 'NIFTY100_EQL_WGT.NS', 'STRATEGY', 'Nifty100 Equal Weight - Equal weighted Nifty 100'),
('NIFTY200MOM30', 'Nifty200 Momentum 30', 'NIFTY200MOMENTM30.NS', 'STRATEGY', 'Nifty200 Momentum 30 - Momentum based strategy'),
('NIFTY100ESG', 'Nifty 100 ESG', 'NIFTY100_ESG.NS', 'STRATEGY', 'Nifty 100 ESG - Environmental, social, governance criteria')
ON DUPLICATE KEY UPDATE 
    index_name = VALUES(index_name),
    category = VALUES(category),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

-- Create view for easy querying
CREATE OR REPLACE VIEW vw_yfinance_indices_latest AS
SELECT 
    im.id,
    im.index_code,
    im.index_name,
    im.yahoo_symbol,
    im.category,
    dq.date as last_date,
    dq.close as last_close,
    dq.open,
    dq.high,
    dq.low,
    dq.volume,
    ROUND(((dq.close - prev.close) / prev.close * 100), 2) as change_pct,
    dq.updated_at
FROM yfinance_indices_master im
LEFT JOIN yfinance_indices_daily_quotes dq ON im.yahoo_symbol = dq.symbol
LEFT JOIN LATERAL (
    SELECT close 
    FROM yfinance_indices_daily_quotes 
    WHERE symbol = im.yahoo_symbol 
    AND date < dq.date 
    ORDER BY date DESC 
    LIMIT 1
) prev ON TRUE
WHERE dq.date = (
    SELECT MAX(date) 
    FROM yfinance_indices_daily_quotes 
    WHERE symbol = im.yahoo_symbol
)
AND im.is_active = TRUE
ORDER BY im.category, im.index_name;

-- Summary query
SELECT 
    category,
    COUNT(*) as index_count
FROM yfinance_indices_master
WHERE is_active = TRUE
GROUP BY category
ORDER BY category;

SELECT 'Tables created successfully!' as status;
