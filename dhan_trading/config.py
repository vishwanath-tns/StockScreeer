"""
Dhan Trading System - Configuration
====================================
Database and API configuration for Dhan trading.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dhan API Configuration
DHAN_CLIENT_ID = os.getenv('DHAN_CLIENT_ID', '')
DHAN_ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN', '')

# Dhan API Base URLs
DHAN_API_BASE_URL = "https://api.dhan.co/v2"
DHAN_INSTRUMENTS_CSV_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
DHAN_INSTRUMENTS_DETAILED_CSV_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

# Database Configuration (separate database for Dhan)
DHAN_DB_HOST = os.getenv('DHAN_DB_HOST', os.getenv('MYSQL_HOST', 'localhost'))
DHAN_DB_PORT = int(os.getenv('DHAN_DB_PORT', os.getenv('MYSQL_PORT', '3306')))
DHAN_DB_USER = os.getenv('DHAN_DB_USER', os.getenv('MYSQL_USER', 'root'))
DHAN_DB_PASSWORD = os.getenv('DHAN_DB_PASSWORD', os.getenv('MYSQL_PASSWORD', ''))
DHAN_DB_NAME = os.getenv('DHAN_DB_NAME', 'dhan_trading')

# Data directory
DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

# Exchange Segment Mapping (from Dhan docs)
EXCHANGE_SEGMENTS = {
    'NSE_EQ': 'NSE Equity',
    'NSE_FNO': 'NSE F&O',
    'NSE_CURRENCY': 'NSE Currency',
    'BSE_EQ': 'BSE Equity',
    'BSE_FNO': 'BSE F&O',
    'BSE_CURRENCY': 'BSE Currency',
    'MCX_COMM': 'MCX Commodity',
    'IDX_I': 'Index',
}

# Order Types
ORDER_TYPES = {
    'LIMIT': 'Limit Order',
    'MARKET': 'Market Order',
    'STOP_LOSS': 'Stop Loss Order',
    'STOP_LOSS_MARKET': 'Stop Loss Market Order',
}

# Product Types
PRODUCT_TYPES = {
    'CNC': 'Cash and Carry (Delivery)',
    'INTRADAY': 'Intraday',
    'MARGIN': 'Margin',
    'MTF': 'Margin Trade Funding',
    'CO': 'Cover Order',
    'BO': 'Bracket Order',
}

# Validity Types
VALIDITY_TYPES = {
    'DAY': 'Day Order',
    'IOC': 'Immediate or Cancel',
}
