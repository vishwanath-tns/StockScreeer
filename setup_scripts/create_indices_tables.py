#!/usr/bin/env python3
"""Create yfinance indices tables"""
from sync_bhav_gui import engine
from sqlalchemy import text

conn = engine().connect()

# Create master table
conn.execute(text("""
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""))
print('✅ Created yfinance_indices_master')

# Create daily quotes table
conn.execute(text("""
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""))
print('✅ Created yfinance_indices_daily_quotes')

# Insert indices data
indices = [
    ('NIFTY50', 'Nifty 50', '^NSEI', 'BROAD_MARKET'),
    ('NIFTYNEXT50', 'Nifty Next 50', '^NSMIDCP', 'BROAD_MARKET'),
    ('NIFTYLARGEMID250', 'Nifty LargeMidcap 250', 'NIFTY_LARGEMID250.NS', 'BROAD_MARKET'),
    ('NIFTYAUTO', 'Nifty Auto', '^CNXAUTO', 'SECTORAL'),
    ('NIFTYBANK', 'Nifty Bank', '^NSEBANK', 'SECTORAL'),
    ('NIFTYFINSVC', 'Nifty Financial Services', 'NIFTY_FIN_SERVICE.NS', 'SECTORAL'),
    ('NIFTYFMCG', 'Nifty FMCG', '^CNXFMCG', 'SECTORAL'),
    ('NIFTYIT', 'Nifty IT', '^CNXIT', 'SECTORAL'),
    ('NIFTYMETAL', 'Nifty Metal', '^CNXMETAL', 'SECTORAL'),
    ('NIFTYPHARMA', 'Nifty Pharma', '^CNXPHARMA', 'SECTORAL'),
    ('NIFTYPSUBANK', 'Nifty PSU Bank', '^CNXPSUBANK', 'SECTORAL'),
    ('NIFTYPVTBANK', 'Nifty Private Bank', 'NIFTY_PVT_BANK.NS', 'SECTORAL'),
    ('NIFTYREALTY', 'Nifty Realty', '^CNXREALTY', 'SECTORAL'),
    ('NIFTYENERGY', 'Nifty Energy', '^CNXENERGY', 'SECTORAL'),
    ('NIFTYINFRA', 'Nifty Infrastructure', '^CNXINFRA', 'SECTORAL'),
    ('NIFTYCPSE', 'Nifty CPSE', 'NIFTY_CPSE.NS', 'SECTORAL'),
    ('NIFTYOILGAS', 'Nifty Oil & Gas', 'NIFTY_OIL_AND_GAS.NS', 'SECTORAL'),
    ('NIFTYHEALTHCARE', 'Nifty Healthcare', 'NIFTY_HEALTHCARE.NS', 'SECTORAL'),
    ('NIFTYINDIACONSUMPTION', 'Nifty India Consumption', 'NIFTY_CONSR_DURBL.NS', 'THEMATIC'),
    ('NIFTYMOBILITY', 'Nifty Mobility', 'NIFTY_MOBILITY.NS', 'THEMATIC'),
    ('NIFTYHOUSING', 'Nifty Housing', 'NIFTY_HOUSING.NS', 'THEMATIC'),
    ('NIFTY100EQLWGT', 'Nifty100 Equal Weight', 'NIFTY100_EQL_WGT.NS', 'STRATEGY'),
    ('NIFTY200MOM30', 'Nifty200 Momentum 30', 'NIFTY200MOMENTM30.NS', 'STRATEGY'),
    ('NIFTY100ESG', 'Nifty 100 ESG', 'NIFTY100_ESG.NS', 'STRATEGY'),
]

for code, name, symbol, category in indices:
    conn.execute(text("""
        INSERT INTO yfinance_indices_master (index_code, index_name, yahoo_symbol, category)
        VALUES (:code, :name, :symbol, :category)
        ON DUPLICATE KEY UPDATE 
            index_name = :name,
            category = :category,
            updated_at = CURRENT_TIMESTAMP
    """), {'code': code, 'name': name, 'symbol': symbol, 'category': category})

print(f'✅ Inserted {len(indices)} indices')

# Verify
result = conn.execute(text('SELECT COUNT(*) FROM yfinance_indices_master'))
count = result.fetchone()[0]
print(f'\n📊 Total indices in master table: {count}')

result = conn.execute(text('SELECT category, COUNT(*) FROM yfinance_indices_master GROUP BY category'))
print('\nBy Category:')
for row in result:
    print(f'  {row[0]}: {row[1]}')

conn.close()
print('\n✅ Tables created and populated successfully!')
