"""
Configuration management for Yahoo Finance Service
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class YFinanceConfig:
    """Configuration settings for Yahoo Finance service"""
    
    # Database configuration (reuse existing marketdata settings)
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'marketdata')
    
    # Yahoo Finance settings
    DEFAULT_SYMBOL = 'NIFTY'
    DEFAULT_YAHOO_SYMBOL = '^NSEI'
    DEFAULT_TIMEFRAME = 'Daily'
    
    # API settings
    REQUEST_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    # Data validation settings
    MIN_VOLUME = 0
    MAX_PRICE_CHANGE_PCT = 20  # Alert if price change > 20%
    
    # Default date ranges
    DEFAULT_START_YEAR = 2020
    MAX_DAYS_PER_REQUEST = 365  # Avoid API limits
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'yahoo_finance_service.log'
    
    @classmethod
    def get_db_config(cls):
        """Get database configuration dictionary"""
        return {
            'host': cls.MYSQL_HOST,
            'port': cls.MYSQL_PORT,
            'user': cls.MYSQL_USER,
            'password': cls.MYSQL_PASSWORD,
            'database': cls.MYSQL_DATABASE,
            'charset': 'utf8mb4',
            'autocommit': False
        }
    
    @classmethod
    def get_symbol_mapping(cls):
        """Get default symbol mappings"""
        return {
            'NIFTY': '^NSEI',
            'BANKNIFTY': '^NSEBANK', 
            'SENSEX': '^BSESN'
        }