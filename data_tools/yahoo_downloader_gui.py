#!/usr/bin/env python3
"""
Yahoo Finance Data Downloader GUI
=================================

A comprehensive GUI for downloading stock data from Yahoo Finance.
Supports both daily and intraday data for Nifty 500 stocks.

Features:
- Download daily data with date range selection
- Download intraday data (1m, 5m, 15m, 30m, 60m)
- Sync mode to resume from last download
- Gap detection for identifying missing data/holidays
- Overwrite protection with optional override
- Separate tables for daily and intraday data

Database Tables:
- yfinance_daily_quotes: Daily OHLCV data
- yfinance_intraday_quotes: Intraday OHLCV data (created if not exists)

Usage:
    python data_tools/yahoo_downloader_gui.py

Author: StockScreener Project
Version: 1.0.0
Date: November 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, date, timedelta
import threading
import time
import sys
import os
import pandas as pd
import logging
import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system("pip install yfinance")
    import yfinance as yf

try:
    from tkcalendar import DateEntry
except ImportError:
    print("Installing tkcalendar...")
    os.system("pip install tkcalendar")
    from tkcalendar import DateEntry

from dotenv import load_dotenv
load_dotenv()

from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE SERVICE
# =============================================================================

class YahooDBService:
    """Database service for Yahoo Finance data operations"""
    
    # Intraday table name
    INTRADAY_TABLE = 'yfinance_intraday_quotes'
    DAILY_TABLE = 'yfinance_daily_quotes'
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'marketdata'),
            'charset': 'utf8mb4'
        }
        self._engine = None
        self._ensure_intraday_table()
    
    def get_connection(self):
        """Get database connection"""
        return mysql.connector.connect(**self.db_config)
    
    def get_engine(self):
        """Get SQLAlchemy engine"""
        if self._engine is None:
            from urllib.parse import quote_plus
            user = self.db_config['user']
            password = quote_plus(self.db_config['password']) if self.db_config['password'] else ''
            host = self.db_config['host']
            port = self.db_config['port']
            database = self.db_config['database']
            conn_str = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
            self._engine = create_engine(conn_str)
        return self._engine
    
    def _ensure_intraday_table(self):
        """Create intraday table if it doesn't exist"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.INTRADAY_TABLE} (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                datetime DATETIME NOT NULL,
                open DECIMAL(15,4),
                high DECIMAL(15,4),
                low DECIMAL(15,4),
                close DECIMAL(15,4),
                volume BIGINT,
                timeframe VARCHAR(10) NOT NULL,
                source VARCHAR(20) DEFAULT 'yfinance',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY idx_symbol_datetime_tf (symbol, datetime, timeframe),
                INDEX idx_symbol (symbol),
                INDEX idx_datetime (datetime),
                INDEX idx_timeframe (timeframe)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            
            cursor.execute(create_sql)
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Ensured {self.INTRADAY_TABLE} table exists")
            
        except Error as e:
            logger.error(f"Error creating intraday table: {e}")
    
    def get_last_download_date(self, symbol: str, table: str = 'daily') -> date:
        """Get the last date of data for a symbol"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if table == 'daily':
                query = f"SELECT MAX(date) FROM {self.DAILY_TABLE} WHERE symbol = %s"
            else:
                query = f"SELECT MAX(DATE(datetime)) FROM {self.INTRADAY_TABLE} WHERE symbol = %s"
            
            cursor.execute(query, (symbol,))
            result = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return result if result else None
            
        except Error as e:
            logger.error(f"Error getting last download date: {e}")
            return None
    
    def check_existing_data(self, symbol: str, start_date: date, end_date: date, 
                           table: str = 'daily') -> list:
        """Check which dates already have data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if table == 'daily':
                query = f"""
                    SELECT DISTINCT date FROM {self.DAILY_TABLE}
                    WHERE symbol = %s AND date BETWEEN %s AND %s
                """
            else:
                query = f"""
                    SELECT DISTINCT DATE(datetime) FROM {self.INTRADAY_TABLE}
                    WHERE symbol = %s AND DATE(datetime) BETWEEN %s AND %s
                """
            
            cursor.execute(query, (symbol, start_date, end_date))
            existing_dates = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return existing_dates
            
        except Error as e:
            logger.error(f"Error checking existing data: {e}")
            return []
    
    def insert_daily_quotes(self, symbol: str, data: pd.DataFrame, overwrite: bool = False) -> tuple:
        """
        Insert daily quotes into database.
        Returns (inserted_count, skipped_count)
        """
        if data.empty:
            return 0, 0
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if overwrite:
                insert_query = f"""
                    INSERT INTO {self.DAILY_TABLE}
                    (symbol, date, open, high, low, close, volume, adj_close, timeframe, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Daily', 'yfinance')
                    ON DUPLICATE KEY UPDATE
                    open = VALUES(open),
                    high = VALUES(high),
                    low = VALUES(low),
                    close = VALUES(close),
                    volume = VALUES(volume),
                    adj_close = VALUES(adj_close),
                    updated_at = CURRENT_TIMESTAMP
                """
            else:
                insert_query = f"""
                    INSERT IGNORE INTO {self.DAILY_TABLE}
                    (symbol, date, open, high, low, close, volume, adj_close, timeframe, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Daily', 'yfinance')
                """
            
            inserted = 0
            skipped = 0
            
            for idx, row in data.iterrows():
                try:
                    quote_date = idx.date() if hasattr(idx, 'date') else idx
                    values = (
                        symbol,
                        quote_date,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']),
                        float(row.get('Adj Close', row['Close']))
                    )
                    cursor.execute(insert_query, values)
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    logger.debug(f"Error inserting row for {quote_date}: {e}")
                    skipped += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return inserted, skipped
            
        except Error as e:
            logger.error(f"Error inserting daily quotes: {e}")
            return 0, 0
    
    def insert_intraday_quotes(self, symbol: str, data: pd.DataFrame, 
                               timeframe: str, overwrite: bool = False) -> tuple:
        """
        Insert intraday quotes into database.
        Returns (inserted_count, skipped_count)
        """
        if data.empty:
            return 0, 0
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if overwrite:
                insert_query = f"""
                    INSERT INTO {self.INTRADAY_TABLE}
                    (symbol, datetime, open, high, low, close, volume, timeframe, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'yfinance')
                    ON DUPLICATE KEY UPDATE
                    open = VALUES(open),
                    high = VALUES(high),
                    low = VALUES(low),
                    close = VALUES(close),
                    volume = VALUES(volume),
                    updated_at = CURRENT_TIMESTAMP
                """
            else:
                insert_query = f"""
                    INSERT IGNORE INTO {self.INTRADAY_TABLE}
                    (symbol, datetime, open, high, low, close, volume, timeframe, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'yfinance')
                """
            
            inserted = 0
            skipped = 0
            
            for idx, row in data.iterrows():
                try:
                    dt = idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx
                    values = (
                        symbol,
                        dt,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']),
                        timeframe
                    )
                    cursor.execute(insert_query, values)
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    logger.debug(f"Error inserting intraday row: {e}")
                    skipped += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return inserted, skipped
            
        except Error as e:
            logger.error(f"Error inserting intraday quotes: {e}")
            return 0, 0
    
    def get_data_summary(self, symbols: list, table: str = 'daily') -> dict:
        """Get data summary for symbols"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            placeholders = ', '.join(['%s'] * len(symbols))
            
            if table == 'daily':
                query = f"""
                    SELECT symbol, COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
                    FROM {self.DAILY_TABLE}
                    WHERE symbol IN ({placeholders})
                    GROUP BY symbol
                """
            else:
                query = f"""
                    SELECT symbol, COUNT(*) as count, MIN(DATE(datetime)) as min_date, 
                           MAX(DATE(datetime)) as max_date
                    FROM {self.INTRADAY_TABLE}
                    WHERE symbol IN ({placeholders})
                    GROUP BY symbol
                """
            
            cursor.execute(query, symbols)
            results = {row['symbol']: row for row in cursor.fetchall()}
            cursor.close()
            conn.close()
            
            return results
            
        except Error as e:
            logger.error(f"Error getting data summary: {e}")
            return {}
    
    def find_gaps(self, symbol: str, start_date: date, end_date: date, 
                  table: str = 'daily') -> list:
        """Find gaps in data for a symbol"""
        try:
            existing_dates = set(self.check_existing_data(symbol, start_date, end_date, table))
            
            # Generate all weekdays in range
            all_dates = []
            current = start_date
            while current <= end_date:
                if current.weekday() < 5:  # Monday to Friday
                    all_dates.append(current)
                current += timedelta(days=1)
            
            # Find missing dates
            gaps = [d for d in all_dates if d not in existing_dates]
            return gaps
            
        except Exception as e:
            logger.error(f"Error finding gaps: {e}")
            return []
    
    def analyze_gaps(self, symbols: list, start_date: date, end_date: date,
                     table: str = 'daily') -> dict:
        """
        Analyze gaps across multiple symbols to identify holidays.
        Returns dict with 'holidays' and 'gaps' keys.
        """
        try:
            # Get gaps for each symbol
            all_gaps = defaultdict(list)
            for symbol in symbols[:50]:  # Check first 50 symbols
                gaps = self.find_gaps(symbol, start_date, end_date, table)
                for gap_date in gaps:
                    all_gaps[gap_date].append(symbol)
            
            # Dates missing for >90% of symbols are likely holidays
            threshold = len(symbols[:50]) * 0.9
            holidays = []
            gaps = []
            
            for gap_date, missing_symbols in all_gaps.items():
                if len(missing_symbols) >= threshold:
                    holidays.append(gap_date)
                else:
                    gaps.append((gap_date, len(missing_symbols)))
            
            return {
                'holidays': sorted(holidays),
                'gaps': sorted(gaps, key=lambda x: (-x[1], x[0]))  # Sort by count desc
            }
            
        except Exception as e:
            logger.error(f"Error analyzing gaps: {e}")
            return {'holidays': [], 'gaps': []}


# =============================================================================
# YAHOO DOWNLOADER
# =============================================================================

class YahooDownloader:
    """Yahoo Finance data downloader"""
    
    # Intraday intervals supported by yfinance
    INTRADAY_INTERVALS = ['1m', '5m', '15m', '30m', '60m', '90m']
    
    # Max days for intraday data (yfinance limitations)
    INTRADAY_MAX_DAYS = {
        '1m': 7,
        '5m': 60,
        '15m': 60,
        '30m': 60,
        '60m': 730,
        '90m': 60
    }
    
    def __init__(self, db_service: YahooDBService):
        self.db_service = db_service
    
    def get_yahoo_symbol(self, symbol: str) -> str:
        """Convert NSE symbol to Yahoo Finance symbol"""
        # Skip ETFs and other non-tradable symbols
        skip_suffixes = ['BEES', 'ETF', 'CASE', 'GOLD', 'SILVER']
        if any(symbol.upper().endswith(s) for s in skip_suffixes):
            return None
        
        # Add .NS suffix if not present
        if not symbol.endswith('.NS'):
            return f"{symbol}.NS"
        return symbol
    
    def download_daily(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Download daily data from Yahoo Finance"""
        yahoo_symbol = self.get_yahoo_symbol(symbol)
        if not yahoo_symbol:
            return pd.DataFrame()
        
        try:
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, end=end_date + timedelta(days=1))
            return data
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return pd.DataFrame()
    
    def download_intraday(self, symbol: str, interval: str, period: str = None, 
                         start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """Download intraday data from Yahoo Finance"""
        yahoo_symbol = self.get_yahoo_symbol(symbol)
        if not yahoo_symbol:
            return pd.DataFrame()
        
        try:
            ticker = yf.Ticker(yahoo_symbol)
            
            # Calculate period based on interval limits
            max_days = self.INTRADAY_MAX_DAYS.get(interval, 7)
            
            if start_date and end_date:
                # Check if date range is within limits
                days_requested = (end_date - start_date).days
                if days_requested > max_days:
                    logger.warning(f"Date range {days_requested} days exceeds max {max_days} for {interval}")
                    start_date = end_date - timedelta(days=max_days)
                
                data = ticker.history(start=start_date, end=end_date + timedelta(days=1), interval=interval)
            else:
                # Use period string
                period = period or f"{max_days}d"
                data = ticker.history(period=period, interval=interval)
            
            return data
            
        except Exception as e:
            logger.error(f"Error downloading intraday {symbol}: {e}")
            return pd.DataFrame()


# =============================================================================
# MAIN GUI
# =============================================================================

class YahooDownloaderGUI:
    """Yahoo Finance Data Downloader GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Yahoo Finance Data Downloader")
        self.root.geometry("1000x800")
        
        # Initialize services
        self.db_service = YahooDBService()
        self.downloader = YahooDownloader(self.db_service)
        
        # State
        self.is_downloading = False
        self.stop_requested = False
        self.unfetchable_symbols = set()
        
        # Color scheme - Light theme
        self.colors = {
            'bg': '#f5f7fa',
            'card': '#ffffff',
            'accent': '#e8ecf1',
            'primary': '#2563eb',
            'text': '#0f172a',
            'secondary': '#334155',
            'success': '#16a34a',
            'warning': '#ea580c',
            'error': '#dc2626',
        }
        
        # Fonts
        self.fonts = {
            'title': ('Segoe UI', 18, 'bold'),
            'subtitle': ('Segoe UI', 12, 'bold'),
            'body': ('Segoe UI', 10, 'bold'),
            'small': ('Segoe UI', 9),
        }
        
        self.root.configure(bg=self.colors['bg'])
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        self.setup_title(main_frame)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Daily data tab
        self.daily_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.daily_frame, text="📅 Daily Data")
        self.setup_daily_tab(self.daily_frame)
        
        # Intraday data tab
        self.intraday_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.intraday_frame, text="⏱️ Intraday Data")
        self.setup_intraday_tab(self.intraday_frame)
        
        # Gap Analysis tab
        self.gap_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.gap_frame, text="🔍 Gap Analysis")
        self.setup_gap_tab(self.gap_frame)
        
        # Log panel
        self.setup_log_panel(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_title(self, parent):
        """Setup title section"""
        title_frame = tk.Frame(parent, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(
            title_frame,
            text="📊 Yahoo Finance Data Downloader",
            font=self.fonts['title'],
            fg=self.colors['primary'],
            bg=self.colors['bg']
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle = tk.Label(
            title_frame,
            text=f"• Database: marketdata • Nifty 500 Stocks",
            font=self.fonts['small'],
            fg=self.colors['secondary'],
            bg=self.colors['bg']
        )
        subtitle.pack(side=tk.LEFT, padx=20)
    
    def setup_daily_tab(self, parent):
        """Setup daily data download tab"""
        # Settings card
        settings_card = tk.Frame(parent, bg=self.colors['card'], relief='flat')
        settings_card.pack(fill=tk.X, pady=10, padx=5)
        
        inner = tk.Frame(settings_card, bg=self.colors['card'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Date range row
        date_frame = tk.Frame(inner, bg=self.colors['card'])
        date_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(date_frame, text="Date Range:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        tk.Label(date_frame, text="From:", font=self.fonts['small'],
                fg=self.colors['secondary'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.daily_start_date = DateEntry(
            date_frame, width=12, date_pattern='yyyy-mm-dd',
            year=2024, month=1, day=1
        )
        self.daily_start_date.pack(side=tk.LEFT, padx=5)
        
        tk.Label(date_frame, text="To:", font=self.fonts['small'],
                fg=self.colors['secondary'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.daily_end_date = DateEntry(
            date_frame, width=12, date_pattern='yyyy-mm-dd'
        )
        self.daily_end_date.pack(side=tk.LEFT, padx=5)
        
        # Options row
        options_frame = tk.Frame(inner, bg=self.colors['card'])
        options_frame.pack(fill=tk.X, pady=10)
        
        self.daily_overwrite_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            options_frame, text="Overwrite existing data",
            variable=self.daily_overwrite_var,
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card'],
            selectcolor=self.colors['accent']
        ).pack(side=tk.LEFT, padx=10)
        
        # Stock limit
        tk.Label(options_frame, text="Stocks:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=(20, 5))
        
        self.daily_limit_var = tk.StringVar(value="All (500)")
        limit_combo = ttk.Combobox(
            options_frame, textvariable=self.daily_limit_var,
            values=["10", "25", "50", "100", "200", "All (500)"],
            width=10, state='readonly'
        )
        limit_combo.pack(side=tk.LEFT, padx=5)
        
        # Buttons row
        btn_frame = tk.Frame(inner, bg=self.colors['card'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.daily_sync_btn = tk.Button(
            btn_frame, text="🔄 Sync (Resume from last)",
            command=self.sync_daily_data,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['primary'],
            activebackground='#1d4ed8', relief='flat', cursor='hand2', padx=15
        )
        self.daily_sync_btn.pack(side=tk.LEFT, padx=5)
        
        self.daily_download_btn = tk.Button(
            btn_frame, text="📥 Download Date Range",
            command=self.download_daily_data,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['success'],
            activebackground='#15803d', relief='flat', cursor='hand2', padx=15
        )
        self.daily_download_btn.pack(side=tk.LEFT, padx=5)
        
        self.daily_stop_btn = tk.Button(
            btn_frame, text="⏹ Stop",
            command=self.stop_download,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['error'],
            activebackground='#b91c1c', relief='flat', cursor='hand2', padx=15,
            state='disabled'
        )
        self.daily_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress
        progress_frame = tk.Frame(inner, bg=self.colors['card'])
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.daily_progress_var = tk.DoubleVar(value=0)
        self.daily_progress = ttk.Progressbar(
            progress_frame, variable=self.daily_progress_var,
            maximum=100, length=400
        )
        self.daily_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.daily_progress_label = tk.Label(
            progress_frame, text="Ready",
            font=self.fonts['small'], fg=self.colors['secondary'], bg=self.colors['card']
        )
        self.daily_progress_label.pack(side=tk.LEFT, padx=10)
    
    def setup_intraday_tab(self, parent):
        """Setup intraday data download tab"""
        # Settings card
        settings_card = tk.Frame(parent, bg=self.colors['card'], relief='flat')
        settings_card.pack(fill=tk.X, pady=10, padx=5)
        
        inner = tk.Frame(settings_card, bg=self.colors['card'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Info label
        info_label = tk.Label(
            inner,
            text="⚠️ Intraday data limits: 1m=7 days, 5m/15m/30m=60 days, 60m=730 days",
            font=self.fonts['small'], fg=self.colors['warning'], bg=self.colors['card']
        )
        info_label.pack(fill=tk.X, pady=5)
        
        # Timeframe selection
        tf_frame = tk.Frame(inner, bg=self.colors['card'])
        tf_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(tf_frame, text="Timeframe:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.intraday_tf_var = tk.StringVar(value="15m")
        for tf in ['1m', '5m', '15m', '30m', '60m']:
            rb = tk.Radiobutton(
                tf_frame, text=tf, variable=self.intraday_tf_var, value=tf,
                font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card'],
                selectcolor=self.colors['accent']
            )
            rb.pack(side=tk.LEFT, padx=10)
        
        # Date range row
        date_frame = tk.Frame(inner, bg=self.colors['card'])
        date_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(date_frame, text="Date Range:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        tk.Label(date_frame, text="From:", font=self.fonts['small'],
                fg=self.colors['secondary'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        # Default to 7 days ago for intraday
        self.intraday_start_date = DateEntry(
            date_frame, width=12, date_pattern='yyyy-mm-dd'
        )
        self.intraday_start_date.set_date(date.today() - timedelta(days=7))
        self.intraday_start_date.pack(side=tk.LEFT, padx=5)
        
        tk.Label(date_frame, text="To:", font=self.fonts['small'],
                fg=self.colors['secondary'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.intraday_end_date = DateEntry(
            date_frame, width=12, date_pattern='yyyy-mm-dd'
        )
        self.intraday_end_date.pack(side=tk.LEFT, padx=5)
        
        # Options row
        options_frame = tk.Frame(inner, bg=self.colors['card'])
        options_frame.pack(fill=tk.X, pady=10)
        
        self.intraday_overwrite_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            options_frame, text="Overwrite existing data",
            variable=self.intraday_overwrite_var,
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card'],
            selectcolor=self.colors['accent']
        ).pack(side=tk.LEFT, padx=10)
        
        # Stock limit
        tk.Label(options_frame, text="Stocks:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=(20, 5))
        
        self.intraday_limit_var = tk.StringVar(value="50")
        limit_combo = ttk.Combobox(
            options_frame, textvariable=self.intraday_limit_var,
            values=["10", "25", "50", "100", "200", "All (500)"],
            width=10, state='readonly'
        )
        limit_combo.pack(side=tk.LEFT, padx=5)
        
        # Buttons row
        btn_frame = tk.Frame(inner, bg=self.colors['card'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.intraday_sync_btn = tk.Button(
            btn_frame, text="🔄 Sync (Resume from last)",
            command=self.sync_intraday_data,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['primary'],
            activebackground='#1d4ed8', relief='flat', cursor='hand2', padx=15
        )
        self.intraday_sync_btn.pack(side=tk.LEFT, padx=5)
        
        self.intraday_download_btn = tk.Button(
            btn_frame, text="📥 Download Date Range",
            command=self.download_intraday_data,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['success'],
            activebackground='#15803d', relief='flat', cursor='hand2', padx=15
        )
        self.intraday_download_btn.pack(side=tk.LEFT, padx=5)
        
        self.intraday_stop_btn = tk.Button(
            btn_frame, text="⏹ Stop",
            command=self.stop_download,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['error'],
            activebackground='#b91c1c', relief='flat', cursor='hand2', padx=15,
            state='disabled'
        )
        self.intraday_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress
        progress_frame = tk.Frame(inner, bg=self.colors['card'])
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.intraday_progress_var = tk.DoubleVar(value=0)
        self.intraday_progress = ttk.Progressbar(
            progress_frame, variable=self.intraday_progress_var,
            maximum=100, length=400
        )
        self.intraday_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.intraday_progress_label = tk.Label(
            progress_frame, text="Ready",
            font=self.fonts['small'], fg=self.colors['secondary'], bg=self.colors['card']
        )
        self.intraday_progress_label.pack(side=tk.LEFT, padx=10)
    
    def setup_gap_tab(self, parent):
        """Setup gap analysis tab"""
        # Settings card
        settings_card = tk.Frame(parent, bg=self.colors['card'], relief='flat')
        settings_card.pack(fill=tk.X, pady=10, padx=5)
        
        inner = tk.Frame(settings_card, bg=self.colors['card'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Data type selection
        type_frame = tk.Frame(inner, bg=self.colors['card'])
        type_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(type_frame, text="Data Type:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.gap_type_var = tk.StringVar(value="daily")
        tk.Radiobutton(
            type_frame, text="Daily", variable=self.gap_type_var, value="daily",
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card'],
            selectcolor=self.colors['accent']
        ).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(
            type_frame, text="Intraday", variable=self.gap_type_var, value="intraday",
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card'],
            selectcolor=self.colors['accent']
        ).pack(side=tk.LEFT, padx=10)
        
        # Date range
        date_frame = tk.Frame(inner, bg=self.colors['card'])
        date_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(date_frame, text="Analyze From:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.gap_start_date = DateEntry(
            date_frame, width=12, date_pattern='yyyy-mm-dd'
        )
        self.gap_start_date.set_date(date.today() - timedelta(days=30))
        self.gap_start_date.pack(side=tk.LEFT, padx=5)
        
        tk.Label(date_frame, text="To:", font=self.fonts['small'],
                fg=self.colors['secondary'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.gap_end_date = DateEntry(
            date_frame, width=12, date_pattern='yyyy-mm-dd'
        )
        self.gap_end_date.pack(side=tk.LEFT, padx=5)
        
        # Analyze button
        self.gap_analyze_btn = tk.Button(
            inner, text="🔍 Analyze Gaps",
            command=self.analyze_gaps,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['primary'],
            activebackground='#1d4ed8', relief='flat', cursor='hand2', padx=15
        )
        self.gap_analyze_btn.pack(pady=10)
        
        # Results area
        results_frame = tk.Frame(parent, bg=self.colors['card'], relief='flat')
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Holidays
        holidays_frame = tk.LabelFrame(
            results_frame, text="🏖️ Detected Holidays (Missing for 90%+ stocks)",
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card']
        )
        holidays_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.holidays_text = tk.Text(
            holidays_frame, height=5, wrap=tk.WORD,
            font=self.fonts['small'], bg=self.colors['accent']
        )
        self.holidays_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Gaps
        gaps_frame = tk.LabelFrame(
            results_frame, text="⚠️ Data Gaps (Missing for some stocks)",
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card']
        )
        gaps_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.gaps_text = tk.Text(
            gaps_frame, height=10, wrap=tk.WORD,
            font=self.fonts['small'], bg=self.colors['accent']
        )
        self.gaps_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def setup_log_panel(self, parent):
        """Setup log panel"""
        log_frame = tk.LabelFrame(
            parent, text="📋 Download Log",
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card']
        )
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Log text with scrollbar
        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame, height=10, wrap=tk.WORD,
            font=('Consolas', 9), bg='#1e293b', fg='#e2e8f0',
            yscrollcommand=log_scroll.set
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_scroll.config(command=self.log_text.yview)
        
        # Configure tags for colored logs
        self.log_text.tag_configure('info', foreground='#60a5fa')
        self.log_text.tag_configure('success', foreground='#4ade80')
        self.log_text.tag_configure('warning', foreground='#fbbf24')
        self.log_text.tag_configure('error', foreground='#f87171')
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = tk.Frame(parent, bg=self.colors['accent'])
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready to download data",
            font=self.fonts['small'],
            fg=self.colors['text'],
            bg=self.colors['accent'],
            pady=5
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def log(self, message: str, level: str = 'info'):
        """Add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] ", 'info')
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)
    
    def get_stock_limit(self, limit_var) -> int:
        """Get number of stocks to process"""
        limit = limit_var.get()
        if 'All' in limit:
            return 500
        return int(limit)
    
    def get_symbols(self, limit: int) -> list:
        """Get list of symbols with .NS suffix"""
        return [f"{s}.NS" for s in NIFTY_500_STOCKS[:limit]]
    
    def update_status(self, text: str):
        """Update status bar"""
        self.status_label.configure(text=text)
    
    def set_downloading(self, is_downloading: bool, tab: str = 'daily'):
        """Set downloading state and update UI"""
        self.is_downloading = is_downloading
        
        if tab == 'daily':
            state = 'disabled' if is_downloading else 'normal'
            self.daily_sync_btn.configure(state=state)
            self.daily_download_btn.configure(state=state)
            self.daily_stop_btn.configure(state='normal' if is_downloading else 'disabled')
        else:
            state = 'disabled' if is_downloading else 'normal'
            self.intraday_sync_btn.configure(state=state)
            self.intraday_download_btn.configure(state=state)
            self.intraday_stop_btn.configure(state='normal' if is_downloading else 'disabled')
    
    def stop_download(self):
        """Stop current download"""
        self.stop_requested = True
        self.log("Stop requested...", 'warning')
    
    # =========================================================================
    # DAILY DATA METHODS
    # =========================================================================
    
    def sync_daily_data(self):
        """Sync daily data - resume from last download date"""
        if self.is_downloading:
            return
        
        self.stop_requested = False
        self.set_downloading(True, 'daily')
        
        thread = threading.Thread(target=self._sync_daily_worker)
        thread.daemon = True
        thread.start()
    
    def _sync_daily_worker(self):
        """Background worker for daily sync"""
        try:
            limit = self.get_stock_limit(self.daily_limit_var)
            symbols = self.get_symbols(limit)
            overwrite = self.daily_overwrite_var.get()
            end_date = date.today()
            
            self.log(f"Starting daily sync for {len(symbols)} stocks...", 'info')
            
            total_inserted = 0
            total_skipped = 0
            failed = 0
            
            for i, symbol in enumerate(symbols):
                if self.stop_requested:
                    self.log("Download stopped by user", 'warning')
                    break
                
                # Get last download date for this symbol
                last_date = self.db_service.get_last_download_date(symbol, 'daily')
                
                if last_date:
                    start_date = last_date + timedelta(days=1)
                    if start_date > end_date:
                        # Already up to date
                        progress = ((i + 1) / len(symbols)) * 100
                        self.root.after(0, lambda p=progress: self.daily_progress_var.set(p))
                        self.root.after(0, lambda s=symbol: 
                            self.daily_progress_label.configure(text=f"{s} - Up to date"))
                        continue
                else:
                    # No data, download from 1 year ago
                    start_date = end_date - timedelta(days=365)
                
                # Download data
                data = self.downloader.download_daily(symbol, start_date, end_date)
                
                if not data.empty:
                    inserted, skipped = self.db_service.insert_daily_quotes(
                        symbol, data, overwrite
                    )
                    total_inserted += inserted
                    total_skipped += skipped
                    self.log(f"{symbol}: +{inserted} records", 'success')
                else:
                    failed += 1
                    if symbol not in self.unfetchable_symbols:
                        self.unfetchable_symbols.add(symbol)
                
                # Update progress
                progress = ((i + 1) / len(symbols)) * 100
                self.root.after(0, lambda p=progress: self.daily_progress_var.set(p))
                self.root.after(0, lambda s=symbol, p=progress: 
                    self.daily_progress_label.configure(text=f"{s} ({p:.0f}%)"))
                
                time.sleep(0.2)  # Rate limiting
            
            self.log(f"Sync complete: {total_inserted} inserted, {total_skipped} skipped, {failed} failed", 
                    'success' if failed == 0 else 'warning')
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.root.after(0, lambda: self.set_downloading(False, 'daily'))
            self.root.after(0, lambda: self.update_status("Daily sync complete"))
    
    def download_daily_data(self):
        """Download daily data for date range"""
        if self.is_downloading:
            return
        
        self.stop_requested = False
        self.set_downloading(True, 'daily')
        
        thread = threading.Thread(target=self._download_daily_worker)
        thread.daemon = True
        thread.start()
    
    def _download_daily_worker(self):
        """Background worker for daily download"""
        try:
            limit = self.get_stock_limit(self.daily_limit_var)
            symbols = self.get_symbols(limit)
            start_date = self.daily_start_date.get_date()
            end_date = self.daily_end_date.get_date()
            overwrite = self.daily_overwrite_var.get()
            
            self.log(f"Downloading daily data for {len(symbols)} stocks from {start_date} to {end_date}", 'info')
            
            total_inserted = 0
            total_skipped = 0
            failed = 0
            
            for i, symbol in enumerate(symbols):
                if self.stop_requested:
                    self.log("Download stopped by user", 'warning')
                    break
                
                # Check existing data if not overwriting
                if not overwrite:
                    existing = self.db_service.check_existing_data(symbol, start_date, end_date, 'daily')
                    if len(existing) > 0:
                        self.log(f"{symbol}: {len(existing)} days already exist, skipping...", 'info')
                
                # Download data
                data = self.downloader.download_daily(symbol, start_date, end_date)
                
                if not data.empty:
                    inserted, skipped = self.db_service.insert_daily_quotes(
                        symbol, data, overwrite
                    )
                    total_inserted += inserted
                    total_skipped += skipped
                    if inserted > 0:
                        self.log(f"{symbol}: +{inserted} records", 'success')
                else:
                    failed += 1
                
                # Update progress
                progress = ((i + 1) / len(symbols)) * 100
                self.root.after(0, lambda p=progress: self.daily_progress_var.set(p))
                self.root.after(0, lambda s=symbol, p=progress: 
                    self.daily_progress_label.configure(text=f"{s} ({p:.0f}%)"))
                
                time.sleep(0.2)  # Rate limiting
            
            self.log(f"Download complete: {total_inserted} inserted, {total_skipped} skipped, {failed} failed", 
                    'success' if failed == 0 else 'warning')
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.root.after(0, lambda: self.set_downloading(False, 'daily'))
            self.root.after(0, lambda: self.update_status("Daily download complete"))
    
    # =========================================================================
    # INTRADAY DATA METHODS
    # =========================================================================
    
    def sync_intraday_data(self):
        """Sync intraday data - resume from last download"""
        if self.is_downloading:
            return
        
        self.stop_requested = False
        self.set_downloading(True, 'intraday')
        
        thread = threading.Thread(target=self._sync_intraday_worker)
        thread.daemon = True
        thread.start()
    
    def _sync_intraday_worker(self):
        """Background worker for intraday sync"""
        try:
            limit = self.get_stock_limit(self.intraday_limit_var)
            symbols = self.get_symbols(limit)
            timeframe = self.intraday_tf_var.get()
            overwrite = self.intraday_overwrite_var.get()
            end_date = date.today()
            
            # Get max days for this timeframe
            max_days = YahooDownloader.INTRADAY_MAX_DAYS.get(timeframe, 7)
            
            self.log(f"Starting intraday sync ({timeframe}) for {len(symbols)} stocks...", 'info')
            
            total_inserted = 0
            total_skipped = 0
            failed = 0
            
            for i, symbol in enumerate(symbols):
                if self.stop_requested:
                    self.log("Download stopped by user", 'warning')
                    break
                
                # Get last download date
                last_date = self.db_service.get_last_download_date(symbol, 'intraday')
                
                if last_date:
                    start_date = last_date + timedelta(days=1)
                    if start_date > end_date:
                        progress = ((i + 1) / len(symbols)) * 100
                        self.root.after(0, lambda p=progress: self.intraday_progress_var.set(p))
                        continue
                else:
                    start_date = end_date - timedelta(days=max_days)
                
                # Download data
                data = self.downloader.download_intraday(
                    symbol, timeframe, start_date=start_date, end_date=end_date
                )
                
                if not data.empty:
                    inserted, skipped = self.db_service.insert_intraday_quotes(
                        symbol, data, timeframe, overwrite
                    )
                    total_inserted += inserted
                    total_skipped += skipped
                    if inserted > 0:
                        self.log(f"{symbol}: +{inserted} {timeframe} records", 'success')
                else:
                    failed += 1
                
                # Update progress
                progress = ((i + 1) / len(symbols)) * 100
                self.root.after(0, lambda p=progress: self.intraday_progress_var.set(p))
                self.root.after(0, lambda s=symbol, p=progress: 
                    self.intraday_progress_label.configure(text=f"{s} ({p:.0f}%)"))
                
                time.sleep(0.3)  # Rate limiting
            
            self.log(f"Intraday sync complete: {total_inserted} inserted, {failed} failed", 
                    'success' if failed == 0 else 'warning')
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.root.after(0, lambda: self.set_downloading(False, 'intraday'))
            self.root.after(0, lambda: self.update_status("Intraday sync complete"))
    
    def download_intraday_data(self):
        """Download intraday data for date range"""
        if self.is_downloading:
            return
        
        self.stop_requested = False
        self.set_downloading(True, 'intraday')
        
        thread = threading.Thread(target=self._download_intraday_worker)
        thread.daemon = True
        thread.start()
    
    def _download_intraday_worker(self):
        """Background worker for intraday download"""
        try:
            limit = self.get_stock_limit(self.intraday_limit_var)
            symbols = self.get_symbols(limit)
            timeframe = self.intraday_tf_var.get()
            start_date = self.intraday_start_date.get_date()
            end_date = self.intraday_end_date.get_date()
            overwrite = self.intraday_overwrite_var.get()
            
            # Check date range limit
            max_days = YahooDownloader.INTRADAY_MAX_DAYS.get(timeframe, 7)
            days_requested = (end_date - start_date).days
            
            if days_requested > max_days:
                self.log(f"Warning: {timeframe} max is {max_days} days, adjusting range", 'warning')
                start_date = end_date - timedelta(days=max_days)
            
            self.log(f"Downloading {timeframe} data for {len(symbols)} stocks from {start_date} to {end_date}", 'info')
            
            total_inserted = 0
            failed = 0
            
            for i, symbol in enumerate(symbols):
                if self.stop_requested:
                    self.log("Download stopped by user", 'warning')
                    break
                
                # Download data
                data = self.downloader.download_intraday(
                    symbol, timeframe, start_date=start_date, end_date=end_date
                )
                
                if not data.empty:
                    inserted, _ = self.db_service.insert_intraday_quotes(
                        symbol, data, timeframe, overwrite
                    )
                    total_inserted += inserted
                    if inserted > 0:
                        self.log(f"{symbol}: +{inserted} {timeframe} records", 'success')
                else:
                    failed += 1
                
                # Update progress
                progress = ((i + 1) / len(symbols)) * 100
                self.root.after(0, lambda p=progress: self.intraday_progress_var.set(p))
                self.root.after(0, lambda s=symbol, p=progress: 
                    self.intraday_progress_label.configure(text=f"{s} ({p:.0f}%)"))
                
                time.sleep(0.3)  # Rate limiting
            
            self.log(f"Intraday download complete: {total_inserted} inserted, {failed} failed", 
                    'success' if failed == 0 else 'warning')
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.root.after(0, lambda: self.set_downloading(False, 'intraday'))
            self.root.after(0, lambda: self.update_status("Intraday download complete"))
    
    # =========================================================================
    # GAP ANALYSIS METHODS
    # =========================================================================
    
    def analyze_gaps(self):
        """Analyze gaps in data"""
        self.log("Analyzing gaps...", 'info')
        self.gap_analyze_btn.configure(state='disabled')
        
        thread = threading.Thread(target=self._analyze_gaps_worker)
        thread.daemon = True
        thread.start()
    
    def _analyze_gaps_worker(self):
        """Background worker for gap analysis"""
        try:
            data_type = self.gap_type_var.get()
            start_date = self.gap_start_date.get_date()
            end_date = self.gap_end_date.get_date()
            symbols = self.get_symbols(50)  # Check first 50 stocks
            
            result = self.db_service.analyze_gaps(symbols, start_date, end_date, data_type)
            
            # Update holidays text
            self.root.after(0, lambda: self._update_holidays_display(result['holidays']))
            
            # Update gaps text
            self.root.after(0, lambda: self._update_gaps_display(result['gaps']))
            
            self.log(f"Gap analysis complete: {len(result['holidays'])} holidays, {len(result['gaps'])} gaps found", 'info')
            
        except Exception as e:
            self.log(f"Error analyzing gaps: {e}", 'error')
        finally:
            self.root.after(0, lambda: self.gap_analyze_btn.configure(state='normal'))
    
    def _update_holidays_display(self, holidays):
        """Update holidays text widget"""
        self.holidays_text.delete('1.0', tk.END)
        if holidays:
            for h in holidays:
                weekday = h.strftime('%A')
                self.holidays_text.insert(tk.END, f"• {h.strftime('%Y-%m-%d')} ({weekday})\n")
        else:
            self.holidays_text.insert(tk.END, "No holidays detected in this range.\n")
    
    def _update_gaps_display(self, gaps):
        """Update gaps text widget"""
        self.gaps_text.delete('1.0', tk.END)
        if gaps:
            for gap_date, count in gaps[:50]:  # Show top 50
                weekday = gap_date.strftime('%a')
                self.gaps_text.insert(tk.END, f"• {gap_date.strftime('%Y-%m-%d')} ({weekday}) - Missing for {count} stocks\n")
        else:
            self.gaps_text.insert(tk.END, "No gaps found in this range.\n")
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point"""
    app = YahooDownloaderGUI()
    app.run()


if __name__ == "__main__":
    main()
