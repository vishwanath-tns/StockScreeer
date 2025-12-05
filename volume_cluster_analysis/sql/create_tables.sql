-- Volume Cluster Events Table
-- Stores high volume events with forward returns for analysis

CREATE TABLE IF NOT EXISTS volume_cluster_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    event_date DATE NOT NULL,
    volume BIGINT NOT NULL,
    volume_quintile VARCHAR(20) NOT NULL COMMENT 'Very Low, Low, Normal, High, Very High',
    close_price DECIMAL(12, 2),
    prev_close DECIMAL(12, 2),
    day_return DECIMAL(8, 2) COMMENT 'Same day return %',
    relative_volume DECIMAL(8, 2) COMMENT 'Volume / 20-day MA volume',
    
    -- Forward returns (can be positive or negative)
    return_1d DECIMAL(8, 2) COMMENT '1 day forward return %',
    return_1w DECIMAL(8, 2) COMMENT '1 week (5 days) forward return %',
    return_2w DECIMAL(8, 2) COMMENT '2 weeks (10 days) forward return %',
    return_3w DECIMAL(8, 2) COMMENT '3 weeks (15 days) forward return %',
    return_1m DECIMAL(8, 2) COMMENT '1 month (21 days) forward return %',
    
    -- Forward prices
    price_1d DECIMAL(12, 2),
    price_1w DECIMAL(12, 2),
    price_2w DECIMAL(12, 2),
    price_3w DECIMAL(12, 2),
    price_1m DECIMAL(12, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_symbol_date (symbol, event_date),
    INDEX idx_symbol (symbol),
    INDEX idx_event_date (event_date),
    INDEX idx_quintile (volume_quintile),
    INDEX idx_return_1m (return_1m)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- View for quick statistics
CREATE OR REPLACE VIEW v_volume_event_stats AS
SELECT 
    symbol,
    volume_quintile,
    COUNT(*) as event_count,
    ROUND(AVG(day_return), 2) as avg_day_return,
    ROUND(AVG(return_1d), 2) as avg_return_1d,
    ROUND(AVG(return_1w), 2) as avg_return_1w,
    ROUND(AVG(return_2w), 2) as avg_return_2w,
    ROUND(AVG(return_3w), 2) as avg_return_3w,
    ROUND(AVG(return_1m), 2) as avg_return_1m,
    ROUND(SUM(CASE WHEN return_1m > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate_1m
FROM volume_cluster_events
WHERE return_1m IS NOT NULL
GROUP BY symbol, volume_quintile
ORDER BY symbol, 
    CASE volume_quintile 
        WHEN 'Very Low' THEN 1 
        WHEN 'Low' THEN 2 
        WHEN 'Normal' THEN 3 
        WHEN 'High' THEN 4 
        WHEN 'Very High' THEN 5 
    END;
