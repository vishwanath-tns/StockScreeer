-- ========================================
-- COMPREHENSIVE VEDIC ASTROLOGY DATABASE SCHEMA
-- Based on Jagannatha Hora Professional Standards
-- ========================================

-- Main planetary positions table
CREATE TABLE planetary_positions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    calculation_time DATETIME(3) NOT NULL,
    location_lat DECIMAL(10,6) DEFAULT 28.6139, -- Default Delhi
    location_lon DECIMAL(10,6) DEFAULT 77.2090,
    ayanamsa_type VARCHAR(20) DEFAULT 'Lahiri',
    ayanamsa_value DECIMAL(8,4) NOT NULL,
    
    -- Main Planets
    sun_longitude DECIMAL(8,4) NOT NULL,
    sun_nakshatra VARCHAR(20),
    sun_pada TINYINT,
    sun_rasi VARCHAR(15),
    sun_navamsa VARCHAR(15),
    
    moon_longitude DECIMAL(8,4) NOT NULL,
    moon_nakshatra VARCHAR(20),
    moon_pada TINYINT,
    moon_rasi VARCHAR(15),
    moon_navamsa VARCHAR(15),
    
    mars_longitude DECIMAL(8,4) NOT NULL,
    mars_nakshatra VARCHAR(20),
    mars_pada TINYINT,
    mars_rasi VARCHAR(15),
    mars_navamsa VARCHAR(15),
    mars_retrograde BOOLEAN DEFAULT FALSE,
    
    mercury_longitude DECIMAL(8,4) NOT NULL,
    mercury_nakshatra VARCHAR(20),
    mercury_pada TINYINT,
    mercury_rasi VARCHAR(15),
    mercury_navamsa VARCHAR(15),
    mercury_retrograde BOOLEAN DEFAULT FALSE,
    
    jupiter_longitude DECIMAL(8,4) NOT NULL,
    jupiter_nakshatra VARCHAR(20),
    jupiter_pada TINYINT,
    jupiter_rasi VARCHAR(15),
    jupiter_navamsa VARCHAR(15),
    jupiter_retrograde BOOLEAN DEFAULT FALSE,
    
    venus_longitude DECIMAL(8,4) NOT NULL,
    venus_nakshatra VARCHAR(20),
    venus_pada TINYINT,
    venus_rasi VARCHAR(15),
    venus_navamsa VARCHAR(15),
    venus_retrograde BOOLEAN DEFAULT FALSE,
    
    saturn_longitude DECIMAL(8,4) NOT NULL,
    saturn_nakshatra VARCHAR(20),
    saturn_pada TINYINT,
    saturn_rasi VARCHAR(15),
    saturn_navamsa VARCHAR(15),
    saturn_retrograde BOOLEAN DEFAULT FALSE,
    
    rahu_longitude DECIMAL(8,4) NOT NULL,
    rahu_nakshatra VARCHAR(20),
    rahu_pada TINYINT,
    rahu_rasi VARCHAR(15),
    rahu_navamsa VARCHAR(15),
    
    ketu_longitude DECIMAL(8,4) NOT NULL,
    ketu_nakshatra VARCHAR(20),
    ketu_pada TINYINT,
    ketu_rasi VARCHAR(15),
    ketu_navamsa VARCHAR(15),
    
    -- Indexes for fast queries
    INDEX idx_time (calculation_time),
    INDEX idx_time_location (calculation_time, location_lat, location_lon),
    INDEX idx_moon_nakshatra (calculation_time, moon_nakshatra),
    INDEX idx_sun_rasi (calculation_time, sun_rasi)
);

-- Special Lagnas table (based on your Jagannatha Hora screenshot)
CREATE TABLE special_lagnas (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    calculation_time DATETIME(3) NOT NULL,
    location_lat DECIMAL(10,6) NOT NULL,
    location_lon DECIMAL(10,6) NOT NULL,
    
    -- Main Lagna (Ascendant)
    lagna_longitude DECIMAL(8,4) NOT NULL,
    lagna_nakshatra VARCHAR(20),
    lagna_pada TINYINT,
    lagna_rasi VARCHAR(15),
    lagna_navamsa VARCHAR(15),
    
    -- Special Lagnas from your screenshot
    maandi_longitude DECIMAL(8,4) NOT NULL,
    maandi_nakshatra VARCHAR(20),
    maandi_pada TINYINT,
    maandi_rasi VARCHAR(15),
    
    gulika_longitude DECIMAL(8,4) NOT NULL,
    gulika_nakshatra VARCHAR(20),
    gulika_pada TINYINT,
    gulika_rasi VARCHAR(15),
    
    bhava_lagna_longitude DECIMAL(8,4) NOT NULL,
    bhava_lagna_nakshatra VARCHAR(20),
    bhava_lagna_pada TINYINT,
    bhava_lagna_rasi VARCHAR(15),
    
    hora_lagna_longitude DECIMAL(8,4) NOT NULL,
    hora_lagna_nakshatra VARCHAR(20),
    hora_lagna_pada TINYINT,
    hora_lagna_rasi VARCHAR(15),
    
    ghati_lagna_longitude DECIMAL(8,4) NOT NULL,
    ghati_lagna_nakshatra VARCHAR(20),
    ghati_lagna_pada TINYINT,
    ghati_lagna_rasi VARCHAR(15),
    
    vighati_lagna_longitude DECIMAL(8,4) NOT NULL,
    vighati_lagna_nakshatra VARCHAR(20),
    vighati_lagna_pada TINYINT,
    vighati_lagna_rasi VARCHAR(15),
    
    varnada_lagna_longitude DECIMAL(8,4) NOT NULL,
    varnada_lagna_nakshatra VARCHAR(20),
    varnada_lagna_pada TINYINT,
    varnada_lagna_rasi VARCHAR(15),
    
    sree_lagna_longitude DECIMAL(8,4) NOT NULL,
    sree_lagna_nakshatra VARCHAR(20),
    sree_lagna_pada TINYINT,
    sree_lagna_rasi VARCHAR(15),
    
    pranapada_lagna_longitude DECIMAL(8,4) NOT NULL,
    pranapada_lagna_nakshatra VARCHAR(20),
    pranapada_lagna_pada TINYINT,
    pranapada_lagna_rasi VARCHAR(15),
    
    indu_lagna_longitude DECIMAL(8,4) NOT NULL,
    indu_lagna_nakshatra VARCHAR(20),
    indu_lagna_pada TINYINT,
    indu_lagna_rasi VARCHAR(15),
    
    bhrigu_bindu_longitude DECIMAL(8,4) NOT NULL,
    bhrigu_bindu_nakshatra VARCHAR(20),
    bhrigu_bindu_pada TINYINT,
    bhrigu_bindu_rasi VARCHAR(15),
    
    INDEX idx_time_location (calculation_time, location_lat, location_lon),
    INDEX idx_lagna_nakshatra (calculation_time, lagna_nakshatra)
);

-- Panchanga elements table
CREATE TABLE panchanga_elements (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    calculation_time DATETIME(3) NOT NULL,
    location_lat DECIMAL(10,6) NOT NULL,
    location_lon DECIMAL(10,6) NOT NULL,
    
    -- Tithi
    tithi_number TINYINT NOT NULL,
    tithi_name VARCHAR(30) NOT NULL,
    tithi_percentage DECIMAL(5,2) NOT NULL,
    tithi_remaining_hours DECIMAL(4,2),
    
    -- Nakshatra
    nakshatra_number TINYINT NOT NULL,
    nakshatra_name VARCHAR(20) NOT NULL,
    nakshatra_percentage DECIMAL(5,2) NOT NULL,
    nakshatra_remaining_hours DECIMAL(4,2),
    nakshatra_lord VARCHAR(15),
    
    -- Yoga
    yoga_number TINYINT NOT NULL,
    yoga_name VARCHAR(30) NOT NULL,
    yoga_percentage DECIMAL(5,2) NOT NULL,
    yoga_remaining_hours DECIMAL(4,2),
    
    -- Karana
    karana_number TINYINT NOT NULL,
    karana_name VARCHAR(20) NOT NULL,
    karana_percentage DECIMAL(5,2) NOT NULL,
    karana_remaining_hours DECIMAL(4,2),
    
    -- Var (Day of week)
    var_number TINYINT NOT NULL,
    var_name VARCHAR(15) NOT NULL,
    var_lord VARCHAR(15),
    
    INDEX idx_time_location (calculation_time, location_lat, location_lon),
    INDEX idx_tithi (calculation_time, tithi_number),
    INDEX idx_nakshatra_panchanga (calculation_time, nakshatra_number)
);

-- Sunrise/Sunset and Muhurta times
CREATE TABLE muhurta_times (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    calculation_date DATE NOT NULL,
    location_lat DECIMAL(10,6) NOT NULL,
    location_lon DECIMAL(10,6) NOT NULL,
    timezone_offset DECIMAL(4,2) NOT NULL,
    
    sunrise_time TIME NOT NULL,
    sunset_time TIME NOT NULL,
    moonrise_time TIME,
    moonset_time TIME,
    
    -- Muhurta divisions
    brahma_muhurta_start TIME,
    brahma_muhurta_end TIME,
    abhijit_muhurta_start TIME,
    abhijit_muhurta_end TIME,
    
    -- Rahukaalam
    rahukaalam_start TIME,
    rahukaalam_end TIME,
    
    -- Yamagandam
    yamagandam_start TIME,
    yamagandam_end TIME,
    
    -- Gulika kaalam
    gulika_kaalam_start TIME,
    gulika_kaalam_end TIME,
    
    INDEX idx_date_location (calculation_date, location_lat, location_lon)
);

-- Validation logs for accuracy testing
CREATE TABLE validation_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    calculation_time DATETIME(3) NOT NULL,
    data_source VARCHAR(20) NOT NULL, -- 'PyJHora', 'JagannathHora', 'DrikPanchang'
    validation_type VARCHAR(30) NOT NULL, -- 'planetary_position', 'nakshatra', 'tithi', etc.
    object_name VARCHAR(30) NOT NULL, -- 'Sun', 'Moon', 'Mars', etc. or 'Tithi', 'Nakshatra'
    
    our_value DECIMAL(10,4),
    reference_value DECIMAL(10,4),
    difference_arcseconds DECIMAL(8,2),
    difference_percentage DECIMAL(6,3),
    
    validation_status ENUM('PASS', 'FAIL', 'WARNING', 'INFO') NOT NULL,
    accuracy_grade VARCHAR(5), -- A+, A, B+, B, C, F
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_time_source (calculation_time, data_source),
    INDEX idx_validation_status (validation_status),
    INDEX idx_accuracy_grade (accuracy_grade)
);

-- Configuration and metadata
CREATE TABLE system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(50) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default configurations
INSERT INTO system_config (config_key, config_value, description) VALUES 
('default_ayanamsa', 'Lahiri', 'Default ayanamsa system for calculations'),
('calculation_interval_minutes', '5', 'Interval in minutes for automatic calculations'),
('default_location_name', 'Delhi', 'Default location name'),
('default_latitude', '28.6139', 'Default latitude for calculations'),
('default_longitude', '77.2090', 'Default longitude for calculations'),
('default_timezone', '+05:30', 'Default timezone offset'),
('validation_tolerance_arcseconds', '3.6', 'Maximum allowed difference in arcseconds for validation'),
('data_retention_days', '3650', 'Number of days to retain calculated data'),
('enable_auto_validation', 'true', 'Enable automatic validation against reference sources');

-- Create views for easy access
CREATE VIEW current_planetary_positions AS
SELECT 
    calculation_time,
    sun_longitude, sun_nakshatra, sun_rasi,
    moon_longitude, moon_nakshatra, moon_rasi,
    mars_longitude, mars_nakshatra, mars_rasi, mars_retrograde,
    mercury_longitude, mercury_nakshatra, mercury_rasi, mercury_retrograde,
    jupiter_longitude, jupiter_nakshatra, jupiter_rasi, jupiter_retrograde,
    venus_longitude, venus_nakshatra, venus_rasi, venus_retrograde,
    saturn_longitude, saturn_nakshatra, saturn_rasi, saturn_retrograde,
    rahu_longitude, rahu_nakshatra, rahu_rasi,
    ketu_longitude, ketu_nakshatra, ketu_rasi
FROM planetary_positions 
ORDER BY calculation_time DESC 
LIMIT 1;

CREATE VIEW current_panchanga AS
SELECT 
    calculation_time,
    tithi_number, tithi_name, tithi_percentage,
    nakshatra_number, nakshatra_name, nakshatra_percentage, nakshatra_lord,
    yoga_number, yoga_name, yoga_percentage,
    karana_number, karana_name, karana_percentage,
    var_number, var_name, var_lord
FROM panchanga_elements 
ORDER BY calculation_time DESC 
LIMIT 1;

-- Performance optimization indexes
CREATE INDEX idx_moon_phases ON planetary_positions (calculation_time, moon_longitude);
CREATE INDEX idx_retrograde_planets ON planetary_positions (calculation_time, mars_retrograde, mercury_retrograde, jupiter_retrograde, venus_retrograde, saturn_retrograde);
CREATE INDEX idx_nakshatra_transits ON planetary_positions (calculation_time, sun_nakshatra, moon_nakshatra);
CREATE INDEX idx_rasi_transits ON planetary_positions (calculation_time, sun_rasi, moon_rasi);

-- Stored procedures for common queries
DELIMITER //

CREATE PROCEDURE GetPlanetaryPositionsForTime(
    IN query_time DATETIME,
    IN latitude DECIMAL(10,6),
    IN longitude DECIMAL(10,6)
)
BEGIN
    SELECT pp.*, sl.lagna_longitude, sl.lagna_nakshatra, sl.lagna_rasi,
           pe.tithi_name, pe.nakshatra_name, pe.yoga_name, pe.karana_name
    FROM planetary_positions pp
    LEFT JOIN special_lagnas sl ON pp.calculation_time = sl.calculation_time 
        AND sl.location_lat = latitude AND sl.location_lon = longitude
    LEFT JOIN panchanga_elements pe ON pp.calculation_time = pe.calculation_time
        AND pe.location_lat = latitude AND pe.location_lon = longitude
    WHERE pp.calculation_time <= query_time
    ORDER BY pp.calculation_time DESC
    LIMIT 1;
END //

CREATE PROCEDURE GetValidationSummary(
    IN start_time DATETIME,
    IN end_time DATETIME
)
BEGIN
    SELECT 
        data_source,
        validation_type,
        object_name,
        COUNT(*) as total_validations,
        SUM(CASE WHEN validation_status = 'PASS' THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN validation_status = 'FAIL' THEN 1 ELSE 0 END) as failed,
        AVG(ABS(difference_arcseconds)) as avg_difference_arcseconds,
        MAX(ABS(difference_arcseconds)) as max_difference_arcseconds,
        MIN(ABS(difference_arcseconds)) as min_difference_arcseconds
    FROM validation_logs
    WHERE calculation_time BETWEEN start_time AND end_time
    GROUP BY data_source, validation_type, object_name
    ORDER BY data_source, validation_type, object_name;
END //

DELIMITER ;