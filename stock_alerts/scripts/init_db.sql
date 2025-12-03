-- Stock Alert System Database Schema
-- Database: alerts_db

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS alerts_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE alerts_db;

-- =====================================================
-- Users Table
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    max_alerts INT DEFAULT 100,
    telegram_chat_id VARCHAR(50) NULL,
    notification_preferences JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB;

-- =====================================================
-- API Keys Table (for external scanner integration)
-- =====================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    permissions JSON NULL,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_key_prefix (key_prefix),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB;

-- =====================================================
-- Price Alerts Table
-- =====================================================
CREATE TABLE IF NOT EXISTS price_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- Symbol identification
    symbol VARCHAR(50) NOT NULL,
    yahoo_symbol VARCHAR(50) NOT NULL,
    asset_type ENUM('NSE_EQUITY', 'BSE_EQUITY', 'NSE_INDEX', 'COMMODITY', 'CRYPTO', 'FOREX') NOT NULL,
    
    -- Alert type and condition
    alert_type ENUM('PRICE', 'VOLUME', 'TECHNICAL', 'CUSTOM') NOT NULL DEFAULT 'PRICE',
    condition ENUM(
        'PRICE_ABOVE', 'PRICE_BELOW', 'PRICE_BETWEEN',
        'PRICE_CROSSES_UP', 'PRICE_CROSSES_DOWN',
        'PCT_CHANGE_UP', 'PCT_CHANGE_DOWN',
        'VOLUME_SPIKE', 'VOLUME_ABOVE',
        'RSI_OVERSOLD', 'RSI_OVERBOUGHT',
        'MACD_CROSSOVER', 'MACD_CROSSUNDER',
        'BOLLINGER_UPPER', 'BOLLINGER_LOWER',
        'SMA_CROSS_ABOVE', 'SMA_CROSS_BELOW',
        'NEW_52W_HIGH', 'NEW_52W_LOW',
        'CUSTOM'
    ) NOT NULL,
    
    -- Target values
    target_value DECIMAL(18, 4) NULL,
    target_value_2 DECIMAL(18, 4) NULL,
    pct_threshold DECIMAL(8, 4) NULL,
    
    -- Technical indicator parameters
    indicator_params JSON NULL,
    
    -- Alert settings
    notification_channels JSON NOT NULL DEFAULT '["DESKTOP"]',
    is_active BOOLEAN DEFAULT TRUE,
    is_recurring BOOLEAN DEFAULT FALSE,
    cooldown_minutes INT DEFAULT 60,
    
    -- Tracking
    last_triggered_at TIMESTAMP NULL,
    trigger_count INT DEFAULT 0,
    last_price DECIMAL(18, 4) NULL,
    
    -- External source tracking
    source VARCHAR(50) DEFAULT 'manual',
    source_data JSON NULL,
    
    -- User notes
    notes TEXT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_user_id (user_id),
    INDEX idx_symbol (symbol),
    INDEX idx_yahoo_symbol (yahoo_symbol),
    INDEX idx_asset_type (asset_type),
    INDEX idx_is_active (is_active),
    INDEX idx_condition (condition),
    INDEX idx_source (source),
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_asset_active (asset_type, is_active)
) ENGINE=InnoDB;

-- =====================================================
-- Alert History Table
-- =====================================================
CREATE TABLE IF NOT EXISTS alert_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT NOT NULL,
    user_id INT NOT NULL,
    
    -- Snapshot of alert at trigger time
    symbol VARCHAR(50) NOT NULL,
    yahoo_symbol VARCHAR(50) NOT NULL,
    condition VARCHAR(50) NOT NULL,
    target_value DECIMAL(18, 4) NULL,
    
    -- Trigger details
    trigger_price DECIMAL(18, 4) NOT NULL,
    trigger_volume BIGINT NULL,
    trigger_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Notification delivery
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channels JSON NULL,
    notification_error TEXT NULL,
    
    -- Additional data
    market_data JSON NULL,
    
    INDEX idx_alert_id (alert_id),
    INDEX idx_user_id (user_id),
    INDEX idx_symbol (symbol),
    INDEX idx_trigger_time (trigger_time),
    INDEX idx_user_time (user_id, trigger_time)
) ENGINE=InnoDB;

-- =====================================================
-- Watchlists Table
-- =====================================================
CREATE TABLE IF NOT EXISTS watchlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    symbols JSON NOT NULL DEFAULT '[]',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_name (user_id, name),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB;

-- =====================================================
-- Symbols Cache Table (for quick lookup)
-- =====================================================
CREATE TABLE IF NOT EXISTS symbols_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    yahoo_symbol VARCHAR(50) NOT NULL UNIQUE,
    asset_type ENUM('NSE_EQUITY', 'BSE_EQUITY', 'NSE_INDEX', 'COMMODITY', 'CRYPTO', 'FOREX') NOT NULL,
    name VARCHAR(200) NULL,
    exchange VARCHAR(20) NULL,
    currency VARCHAR(10) NULL,
    last_price DECIMAL(18, 4) NULL,
    last_updated TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_symbol (symbol),
    INDEX idx_asset_type (asset_type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB;

-- =====================================================
-- System Configuration Table
-- =====================================================
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================
-- Insert default configuration
-- =====================================================
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('price_fetch_interval', '5', 'Seconds between price fetches'),
    ('alert_cooldown_default', '60', 'Default cooldown minutes for alerts'),
    ('max_alerts_per_user', '100', 'Maximum alerts per user'),
    ('max_symbols_per_batch', '50', 'Maximum symbols per Yahoo Finance batch'),
    ('notification_retry_count', '3', 'Number of notification retry attempts'),
    ('demo_mode', 'false', 'Whether to run in demo mode')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- =====================================================
-- Create default admin user (password: admin123)
-- =====================================================
INSERT INTO users (username, email, password_hash, is_admin, max_alerts)
VALUES ('admin', 'admin@localhost', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.W8XJaX.5.5.5', TRUE, 1000)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- =====================================================
-- Views for common queries
-- =====================================================

-- Active alerts with user info
CREATE OR REPLACE VIEW v_active_alerts AS
SELECT 
    pa.*,
    u.username,
    u.email
FROM price_alerts pa
JOIN users u ON pa.user_id = u.id
WHERE pa.is_active = TRUE
  AND u.is_active = TRUE
  AND (pa.expires_at IS NULL OR pa.expires_at > NOW());

-- Alert statistics by user
CREATE OR REPLACE VIEW v_user_alert_stats AS
SELECT 
    u.id as user_id,
    u.username,
    COUNT(pa.id) as total_alerts,
    SUM(CASE WHEN pa.is_active = TRUE THEN 1 ELSE 0 END) as active_alerts,
    SUM(pa.trigger_count) as total_triggers,
    MAX(pa.last_triggered_at) as last_trigger_time
FROM users u
LEFT JOIN price_alerts pa ON u.id = pa.user_id
GROUP BY u.id, u.username;

-- Recent alert history
CREATE OR REPLACE VIEW v_recent_alerts AS
SELECT 
    ah.*,
    u.username,
    pa.notes as alert_notes
FROM alert_history ah
JOIN users u ON ah.user_id = u.id
LEFT JOIN price_alerts pa ON ah.alert_id = pa.id
ORDER BY ah.trigger_time DESC
LIMIT 1000;

-- =====================================================
-- Done!
-- =====================================================
SELECT 'Database schema created successfully!' as message;
