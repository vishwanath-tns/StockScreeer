#!/usr/bin/env python3
"""
Momentum Scanner GUI
====================

A visual interface for scanning stock momentum across multiple timeframes.
Uses Yahoo Finance data stored in MySQL database (yfinance_daily_quotes table).

Features:
- Pre-scan data validation and gap detection
- Automatic download of missing data
- Scan Nifty 500 stocks for momentum
- Multiple timeframes (1W, 1M, 3M, 6M, 9M, 12M)
- Real-time progress tracking
- Sort by any momentum column
- Export to CSV
- Visual momentum indicators (color-coded)

Data Flow:
1. Check database for data completeness
2. Identify stocks with missing/stale data
3. Download missing data from Yahoo Finance
4. Calculate momentum from database
5. Display results and generate reports

Database Table: yfinance_daily_quotes (in marketdata database)

Usage:
    python scanners/momentum_scanner_gui.py

Author: StockScreener Project
Version: 2.0.0
Date: November 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
import warnings

# Suppress pandas SQLAlchemy warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system("pip install yfinance")
    import yfinance as yf

from dotenv import load_dotenv
load_dotenv()

from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE SERVICE
# =============================================================================

class MomentumDBService:
    """
    Database service for momentum scanner.
    Handles data retrieval and storage from yfinance_daily_quotes table.
    """
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'marketdata'),
            'charset': 'utf8mb4'
        }
        # Create SQLAlchemy engine for pandas read_sql
        self._engine = None
    
    def get_connection(self):
        """Get database connection"""
        return mysql.connector.connect(**self.db_config)
    
    def get_engine(self):
        """Get SQLAlchemy engine for pandas operations"""
        if self._engine is None:
            user = self.db_config['user']
            password = self.db_config['password']
            host = self.db_config['host']
            port = self.db_config['port']
            database = self.db_config['database']
            # URL encode password if it contains special characters
            from urllib.parse import quote_plus
            password_encoded = quote_plus(password) if password else ''
            conn_str = f"mysql+mysqlconnector://{user}:{password_encoded}@{host}:{port}/{database}"
            self._engine = create_engine(conn_str)
        return self._engine
    
    def check_data_availability(self, symbols: list, required_days: int = 365) -> dict:
        """
        Check data availability for given symbols.
        
        Returns:
            dict with keys:
                - complete: list of symbols with sufficient data
                - missing: list of symbols with no data
                - stale: list of symbols with outdated data (not today)
                - insufficient: list of symbols with less than required days
        """
        result = {
            'complete': [],
            'missing': [],
            'stale': [],
            'insufficient': [],
            'latest_dates': {},
            'record_counts': {}
        }
        
        today = date.today()
        # Consider data stale if not updated in last 2 trading days
        stale_threshold = today - timedelta(days=3)
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get data summary for all symbols at once
            placeholders = ', '.join(['%s'] * len(symbols))
            query = f"""
                SELECT 
                    symbol,
                    COUNT(*) as record_count,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM yfinance_daily_quotes
                WHERE symbol IN ({placeholders})
                GROUP BY symbol
            """
            
            cursor.execute(query, symbols)
            rows = cursor.fetchall()
            
            # Build lookup
            symbol_data = {row['symbol']: row for row in rows}
            
            for symbol in symbols:
                if symbol not in symbol_data:
                    result['missing'].append(symbol)
                else:
                    data = symbol_data[symbol]
                    result['latest_dates'][symbol] = data['latest_date']
                    result['record_counts'][symbol] = data['record_count']
                    
                    if data['latest_date'] < stale_threshold:
                        result['stale'].append(symbol)
                    elif data['record_count'] < required_days:
                        result['insufficient'].append(symbol)
                    else:
                        result['complete'].append(symbol)
            
            cursor.close()
            conn.close()
            
        except Error as e:
            logger.error(f"Database error: {e}")
            result['error'] = str(e)
        
        return result
    
    def get_ohlcv_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Get OHLCV data for a symbol from database"""
        try:
            engine = self.get_engine()
            
            query = """
                SELECT date, open, high, low, close, volume, adj_close
                FROM yfinance_daily_quotes
                WHERE symbol = %s AND date BETWEEN %s AND %s
                ORDER BY date
            """
            
            df = pd.read_sql(query, engine, params=(symbol, start_date, end_date))
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def insert_quotes(self, symbol: str, data: pd.DataFrame) -> int:
        """Insert/update quotes in database"""
        if data.empty:
            return 0
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO yfinance_daily_quotes 
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
            
            records = []
            for _, row in data.iterrows():
                records.append((
                    symbol,
                    row.name.date() if hasattr(row.name, 'date') else row.name,
                    float(row['Open']),
                    float(row['High']),
                    float(row['Low']),
                    float(row['Close']),
                    int(row['Volume']),
                    float(row.get('Adj Close', row['Close']))
                ))
            
            cursor.executemany(insert_query, records)
            conn.commit()
            
            inserted = cursor.rowcount
            cursor.close()
            conn.close()
            
            return inserted
            
        except Error as e:
            logger.error(f"Error inserting data for {symbol}: {e}")
            return 0
    
    def get_today_coverage(self, symbols: list) -> dict:
        """Check how many symbols have today's data"""
        today = date.today()
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholders = ', '.join(['%s'] * len(symbols))
            query = f"""
                SELECT symbol FROM yfinance_daily_quotes
                WHERE symbol IN ({placeholders}) AND date = %s
            """
            
            cursor.execute(query, symbols + [today])
            rows = cursor.fetchall()
            
            has_today = [row[0] for row in rows]
            missing_today = [s for s in symbols if s not in has_today]
            
            cursor.close()
            conn.close()
            
            return {
                'has_today': has_today,
                'missing_today': missing_today,
                'coverage_pct': len(has_today) / len(symbols) * 100 if symbols else 0
            }
            
        except Error as e:
            logger.error(f"Error checking today's coverage: {e}")
            return {'has_today': [], 'missing_today': symbols, 'coverage_pct': 0}


# =============================================================================
# MOMENTUM CALCULATOR (DATABASE-BASED)
# =============================================================================

class MomentumResult:
    """Data class for momentum calculation results"""
    def __init__(self, symbol: str, duration: str, pct_change: float, 
                 start_price: float, end_price: float, volume: int,
                 latest_date: date = None):
        self.symbol = symbol
        self.duration = duration
        self.pct_change = pct_change
        self.start_price = start_price
        self.end_price = end_price
        self.volume = volume
        self.latest_date = latest_date  # Date of the latest data point used


class DatabaseMomentumCalculator:
    """
    Momentum calculator using database data.
    
    Calculates price momentum for stocks using Yahoo Finance data
    stored in the yfinance_daily_quotes table.
    """
    
    DURATIONS = {
        '1W': 7,
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '9M': 270,
        '12M': 365
    }
    
    def __init__(self):
        self.db_service = MomentumDBService()
        
    def get_yahoo_symbol(self, symbol: str) -> str:
        """Convert NSE symbol to Yahoo Finance symbol"""
        skip_suffixes = ['BEES', 'ETF', 'CASE', 'GOLD', 'SILVER']
        if any(symbol.endswith(s) for s in skip_suffixes):
            return None
        return f"{symbol}.NS"
    
    def download_missing_data(self, symbol: str, days: int = 400) -> bool:
        """Download missing data from Yahoo Finance"""
        yahoo_symbol = self.get_yahoo_symbol(symbol)
        if not yahoo_symbol:
            return False
        
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                return False
            
            # Store in database - use Yahoo symbol format (with .NS) for consistency
            inserted = self.db_service.insert_quotes(yahoo_symbol, data)
            logger.info(f"Downloaded {inserted} records for {yahoo_symbol}")
            return inserted > 0
            
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return False
    
    def calculate_momentum(self, symbol: str, durations: list = None) -> dict:
        """
        Calculate momentum for a single stock from database.
        
        Args:
            symbol: Stock symbol (NSE format)
            durations: List of duration codes ['1W', '1M', etc.]
            
        Returns:
            Dictionary of duration -> MomentumResult
        """
        if durations is None:
            durations = list(self.DURATIONS.keys())
        
        results = {}
        
        try:
            # Get data from database
            max_days = max(self.DURATIONS[d] for d in durations) + 30
            end_date = date.today()
            start_date = end_date - timedelta(days=max_days)
            
            data = self.db_service.get_ohlcv_data(symbol, start_date, end_date)
            
            if data.empty or len(data) < 5:
                logger.warning(f"Insufficient data for {symbol}")
                return {}
            
            # Calculate momentum for each duration
            for duration in durations:
                days = self.DURATIONS[duration]
                target_date = end_date - timedelta(days=days)
                
                try:
                    data_sorted = data.sort_values('date')
                    
                    # Get end price (latest)
                    end_row = data_sorted.iloc[-1]
                    end_price = float(end_row['close'])
                    latest_date = end_row['date'].date() if hasattr(end_row['date'], 'date') else end_row['date']
                    
                    # Find start price (closest to target date)
                    mask = data_sorted['date'].dt.date >= target_date
                    if mask.any():
                        start_row = data_sorted[mask].iloc[0]
                    else:
                        start_row = data_sorted.iloc[0]
                    
                    start_price = float(start_row['close'])
                    
                    # Calculate momentum
                    if start_price > 0:
                        pct_change = ((end_price - start_price) / start_price) * 100
                    else:
                        pct_change = 0.0
                    
                    # Average volume
                    period_data = data_sorted.tail(min(days, len(data_sorted)))
                    avg_volume = int(period_data['volume'].mean()) if len(period_data) > 0 else 0
                    
                    results[duration] = MomentumResult(
                        symbol=symbol,
                        duration=duration,
                        pct_change=round(pct_change, 2),
                        start_price=round(start_price, 2),
                        end_price=round(end_price, 2),
                        volume=avg_volume,
                        latest_date=latest_date
                    )
                    
                except Exception as e:
                    logger.debug(f"Error calculating {duration} for {symbol}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating momentum for {symbol}: {e}")
            return {}


class MomentumScannerGUI:
    """
    Main GUI for the Momentum Scanner.
    
    Provides visual interface for:
    - Pre-scan data validation
    - Automatic data download for missing stocks
    - Scanning stocks and viewing results
    - Exporting data to CSV
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Momentum Scanner - Database + Yahoo Finance")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')
        
        # State
        self.is_scanning = False
        self.is_validating = False
        self.scan_thread = None
        self.results_data = []
        self.calculator = DatabaseMomentumCalculator()
        self.db_service = MomentumDBService()
        
        # Data validation state
        self.data_status = None
        
        # Color scheme - Light theme
        self.colors = {
            'bg': '#f5f7fa',           # Light gray background
            'card': '#ffffff',          # White cards
            'accent': '#e8ecf1',        # Light accent
            'primary': '#2563eb',       # Blue primary
            'text': '#0f172a',          # Very dark text (darker)
            'secondary': '#334155',     # Darker secondary text
            'success': '#16a34a',       # Green success
            'warning': '#ea580c',       # Orange warning
            'error': '#dc2626',         # Red error
            'positive': '#15803d',      # Darker green positive
            'negative': '#b91c1c',      # Darker red negative
            'neutral': '#475569'        # Darker gray neutral
        }
        
        # Fonts - Bold body text
        self.fonts = {
            'title': ('Segoe UI', 18, 'bold'),
            'subtitle': ('Segoe UI', 12, 'bold'),
            'body': ('Segoe UI', 10, 'bold'),
            'small': ('Segoe UI', 9, 'bold'),
            'mono': ('Consolas', 10, 'bold')
        }
        
        self.setup_ui()
        
        # Auto-validate on startup
        self.root.after(500, self.validate_data)
        
    def setup_ui(self):
        """Setup the complete user interface"""
        
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title bar
        self.setup_title_bar(main_frame)
        
        # Data validation panel (NEW)
        self.setup_validation_panel(main_frame)
        
        # Control panel
        self.setup_control_panel(main_frame)
        
        # Progress section
        self.setup_progress_section(main_frame)
        
        # Results table
        self.setup_results_table(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
        
    def setup_title_bar(self, parent):
        """Setup title bar with app name and info"""
        title_frame = tk.Frame(parent, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title
        title_label = tk.Label(
            title_frame,
            text="📊 Momentum Scanner",
            font=self.fonts['title'],
            fg=self.colors['primary'],
            bg=self.colors['bg']
        )
        title_label.pack(side=tk.LEFT)
        
        # Subtitle
        subtitle = tk.Label(
            title_frame,
            text="  •  Database + Yahoo Finance  •  Nifty 500 Stocks",
            font=self.fonts['body'],
            fg=self.colors['secondary'],
            bg=self.colors['bg']
        )
        subtitle.pack(side=tk.LEFT, padx=10)
        
        # Stock count
        self.stock_count_label = tk.Label(
            title_frame,
            text=f"({len(NIFTY_500_STOCKS)} stocks)",
            font=self.fonts['small'],
            fg=self.colors['secondary'],
            bg=self.colors['bg']
        )
        self.stock_count_label.pack(side=tk.RIGHT)
    
    def setup_validation_panel(self, parent):
        """Setup data validation panel"""
        validation_frame = tk.Frame(parent, bg=self.colors['card'], relief='flat')
        validation_frame.pack(fill=tk.X, pady=(0, 10))
        
        inner = tk.Frame(validation_frame, bg=self.colors['card'])
        inner.pack(fill=tk.X, padx=15, pady=12)
        
        # Title
        val_title = tk.Label(
            inner,
            text="📋 Data Validation",
            font=self.fonts['subtitle'],
            fg=self.colors['primary'],
            bg=self.colors['card']
        )
        val_title.pack(side=tk.LEFT)
        
        # Status indicators frame
        status_frame = tk.Frame(inner, bg=self.colors['card'])
        status_frame.pack(side=tk.LEFT, padx=30)
        
        # Complete count
        self.complete_label = tk.Label(
            status_frame,
            text="✓ Complete: --",
            font=self.fonts['body'],
            fg=self.colors['success'],
            bg=self.colors['card']
        )
        self.complete_label.pack(side=tk.LEFT, padx=10)
        
        # Stale count
        self.stale_label = tk.Label(
            status_frame,
            text="⏰ Stale: --",
            font=self.fonts['body'],
            fg=self.colors['warning'],
            bg=self.colors['card']
        )
        self.stale_label.pack(side=tk.LEFT, padx=10)
        
        # Missing count
        self.missing_label = tk.Label(
            status_frame,
            text="✗ Missing: --",
            font=self.fonts['body'],
            fg=self.colors['error'],
            bg=self.colors['card']
        )
        self.missing_label.pack(side=tk.LEFT, padx=10)
        
        # Today's coverage
        self.today_label = tk.Label(
            status_frame,
            text="📅 Today: --%",
            font=self.fonts['body'],
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        self.today_label.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        self.validate_btn = tk.Button(
            inner,
            text="🔄 Validate",
            command=self.validate_data,
            font=self.fonts['body'],
            fg='#ffffff',
            bg=self.colors['primary'],
            activebackground='#1d4ed8',
            relief='flat',
            cursor='hand2',
            padx=15
        )
        self.validate_btn.pack(side=tk.RIGHT, padx=5)
        
        self.download_btn = tk.Button(
            inner,
            text="📥 Download Missing",
            command=self.download_missing_data,
            font=self.fonts['body'],
            fg='#ffffff',
            bg=self.colors['warning'],
            activebackground='#c2410c',
            relief='flat',
            cursor='hand2',
            state='disabled',
            padx=15
        )
        self.download_btn.pack(side=tk.RIGHT, padx=5)
        
    def setup_control_panel(self, parent):
        """Setup control panel with scan options"""
        control_frame = tk.Frame(parent, bg=self.colors['card'], relief='flat')
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        inner = tk.Frame(control_frame, bg=self.colors['card'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Timeframe selection
        tf_label = tk.Label(
            inner,
            text="Timeframes:",
            font=self.fonts['subtitle'],
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        tf_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Checkboxes for each timeframe
        self.timeframe_vars = {}
        timeframes = ['1W', '1M', '3M', '6M', '9M', '12M']
        
        for tf in timeframes:
            var = tk.BooleanVar(value=tf in ['1W', '1M', '3M'])  # Default selected
            self.timeframe_vars[tf] = var
            
            cb = tk.Checkbutton(
                inner,
                text=tf,
                variable=var,
                font=self.fonts['body'],
                fg=self.colors['text'],
                bg=self.colors['card'],
                selectcolor=self.colors['accent'],
                activebackground=self.colors['card'],
                activeforeground=self.colors['text']
            )
            cb.pack(side=tk.LEFT, padx=5)
        
        # Separator
        sep = tk.Frame(inner, width=2, bg=self.colors['accent'])
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=20)
        
        # Stock limit
        limit_label = tk.Label(
            inner,
            text="Scan:",
            font=self.fonts['body'],
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        limit_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.limit_var = tk.StringVar(value="50")
        limit_combo = ttk.Combobox(
            inner,
            textvariable=self.limit_var,
            values=["25", "50", "100", "200", "All (500)"],
            width=10,
            state='readonly'
        )
        limit_combo.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        self.scan_btn = tk.Button(
            inner,
            text="▶ Start Scan",
            command=self.start_scan,
            font=self.fonts['subtitle'],
            fg='#ffffff',
            bg=self.colors['success'],
            activebackground='#15803d',
            relief='flat',
            cursor='hand2',
            padx=20
        )
        self.scan_btn.pack(side=tk.RIGHT, padx=5)
        
        self.stop_btn = tk.Button(
            inner,
            text="⏹ Stop",
            command=self.stop_scan,
            font=self.fonts['body'],
            fg='#ffffff',
            bg=self.colors['error'],
            activebackground='#b91c1c',
            relief='flat',
            cursor='hand2',
            state='disabled',
            padx=15
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=5)
        
        self.export_btn = tk.Button(
            inner,
            text="📥 Export CSV",
            command=self.export_csv,
            font=self.fonts['body'],
            fg=self.colors['text'],
            bg=self.colors['accent'],
            activebackground='#cbd5e1',
            relief='flat',
            cursor='hand2',
            padx=15
        )
        self.export_btn.pack(side=tk.RIGHT, padx=5)
        
    def setup_progress_section(self, parent):
        """Setup progress bar and status"""
        progress_frame = tk.Frame(parent, bg=self.colors['bg'])
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress text
        self.progress_label = tk.Label(
            progress_frame,
            text="Ready to scan",
            font=self.fonts['body'],
            fg=self.colors['secondary'],
            bg=self.colors['bg'],
            width=30
        )
        self.progress_label.pack(side=tk.RIGHT, padx=10)
        
    def setup_results_table(self, parent):
        """Setup the results treeview table"""
        table_frame = tk.Frame(parent, bg=self.colors['card'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Column definitions - added 'latest_date' column
        columns = ('symbol', 'price', 'latest_date', '1W', '1M', '3M', '6M', '9M', '12M', 'volume')
        
        # Treeview with scrollbars
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            selectmode='browse'
        )
        
        # Configure columns
        col_widths = {
            'symbol': 100,
            'price': 80,
            'latest_date': 105,
            '1W': 75,
            '1M': 75,
            '3M': 75,
            '6M': 75,
            '9M': 75,
            '12M': 75,
            'volume': 90
        }
        
        col_headers = {
            'symbol': 'Symbol',
            'price': 'Close ₹',
            'latest_date': 'Data Date',
            '1W': '1 Week %',
            '1M': '1 Month %',
            '3M': '3 Month %',
            '6M': '6 Month %',
            '9M': '9 Month %',
            '12M': '12 Month %',
            'volume': 'Avg Volume'
        }
        
        for col in columns:
            self.tree.heading(col, text=col_headers[col], 
                            command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=col_widths[col], anchor='center')
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Style configuration - Light theme with dark bold text
        style = ttk.Style()
        style.configure('Treeview', 
                       background='#ffffff',
                       foreground='#0f172a',
                       fieldbackground='#ffffff',
                       rowheight=28,
                       font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview.Heading',
                       background='#e2e8f0',
                       foreground='#1e3a8a',
                       font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#dbeafe')])
        style.map('Treeview.Heading', 
                  background=[('active', '#cbd5e1')],
                  foreground=[('active', '#1e3a8a')])
        
        # Tags for coloring - adjusted for light background with darker colors
        self.tree.tag_configure('positive', foreground='#15803d')
        self.tree.tag_configure('negative', foreground='#b91c1c')
        self.tree.tag_configure('neutral', foreground='#475569')
        self.tree.tag_configure('stale', foreground='#c2410c')  # Darker orange for stale data
        
    def setup_status_bar(self, parent):
        """Setup bottom status bar"""
        status_frame = tk.Frame(parent, bg=self.colors['accent'])
        status_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            status_frame,
            text="💡 'Close ₹' shows closing price of the 'Data Date'. Click 'Download Missing' to get latest data.",
            font=self.fonts['small'],
            fg=self.colors['text'],
            bg=self.colors['accent'],
            pady=8
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Timestamp
        self.time_label = tk.Label(
            status_frame,
            text="",
            font=self.fonts['small'],
            fg=self.colors['secondary'],
            bg=self.colors['accent'],
            pady=8
        )
        self.time_label.pack(side=tk.RIGHT, padx=10)
        
    def get_selected_timeframes(self):
        """Get list of selected timeframes"""
        return [tf for tf, var in self.timeframe_vars.items() if var.get()]
    
    def get_stock_limit(self):
        """Get the number of stocks to scan"""
        limit_str = self.limit_var.get()
        if "All" in limit_str:
            return len(NIFTY_500_STOCKS)
        return int(limit_str)
    
    def start_scan(self):
        """Start the momentum scan"""
        if self.is_scanning:
            return
        
        timeframes = self.get_selected_timeframes()
        if not timeframes:
            messagebox.showwarning("Warning", "Please select at least one timeframe")
            return
        
        # Check if data validation has been done
        if self.data_status is None:
            # Just warn, don't block
            self.status_label.configure(
                text="⚠️ Data not validated. Using available data in database..."
            )
        else:
            # Check today's coverage and show info (don't block)
            today_status = self.db_service.get_today_coverage(NIFTY_500_STOCKS[:self.get_stock_limit()])
            if today_status['coverage_pct'] < 50:
                self.status_label.configure(
                    text=f"⚠️ Only {today_status['coverage_pct']:.0f}% have today's data. Using latest available data..."
                )
        
        self.is_scanning = True
        self.scan_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_data = []
        self.stale_count = 0  # Track stocks with stale data
        
        # Start scan thread
        self.scan_thread = threading.Thread(target=self.run_scan, args=(timeframes,))
        self.scan_thread.daemon = True
        self.scan_thread.start()
        
    def stop_scan(self):
        """Stop the ongoing scan"""
        self.is_scanning = False
        self.status_label.configure(text="⏹ Scan stopped by user")
        self.scan_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        
    def run_scan(self, timeframes):
        """Run the momentum scan (in background thread)"""
        try:
            limit = self.get_stock_limit()
            # Add .NS suffix for database lookup
            stocks = [f"{s}.NS" for s in NIFTY_500_STOCKS[:limit]]
            total = len(stocks)
            
            self.update_status(f"🔄 Scanning {total} stocks...")
            
            success_count = 0
            fail_count = 0
            
            for i, symbol in enumerate(stocks):
                if not self.is_scanning:
                    break
                
                # Update progress
                progress = ((i + 1) / total) * 100
                self.root.after(0, lambda p=progress, s=symbol: self.update_progress(p, s))
                
                # Calculate momentum
                results = self.calculator.calculate_momentum(symbol, timeframes)
                
                if results:
                    success_count += 1
                    # Add to table
                    self.root.after(0, lambda r=results, s=symbol: self.add_result_row(s, r))
                else:
                    fail_count += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            
            # Scan complete
            self.root.after(0, lambda: self.scan_complete(success_count, fail_count))
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.root.after(0, lambda: self.scan_error(str(e)))
            
    def update_progress(self, progress, symbol):
        """Update progress bar and label"""
        self.progress_var.set(progress)
        self.progress_label.configure(text=f"Scanning: {symbol} ({progress:.1f}%)")
        
    def add_result_row(self, symbol, results):
        """Add a result row to the table"""
        # Get values for each column - show clean symbol without .NS
        display_symbol = symbol.replace('.NS', '') if symbol.endswith('.NS') else symbol
        values = [display_symbol]
        
        # Price (from latest result)
        price = 0
        latest_date = None
        for r in results.values():
            price = r.end_price
            latest_date = r.latest_date
            break
        values.append(f"₹{price:.2f}")
        
        # Latest date column - show actual date used for analysis
        today = date.today()
        if latest_date:
            # Format date clearly
            if hasattr(latest_date, 'strftime'):
                date_str = latest_date.strftime('%d-%b-%y')
            else:
                date_str = str(latest_date)
            
            # Add warning indicator if not today's data
            if hasattr(latest_date, 'year'):
                days_old = (today - latest_date).days
                if days_old == 0:
                    date_str = f"{date_str} ✓"  # Today's data
                elif days_old == 1:
                    date_str = f"{date_str}"  # Yesterday is ok
                else:
                    date_str = f"{date_str} ({days_old}d)"  # Show how old
            values.append(date_str)
        else:
            values.append("-")
        
        # Momentum values for each timeframe
        timeframes = ['1W', '1M', '3M', '6M', '9M', '12M']
        row_data = {'symbol': symbol, 'price': price, 'latest_date': latest_date}
        
        for tf in timeframes:
            if tf in results:
                pct = results[tf].pct_change
                values.append(f"{pct:+.2f}%")
                row_data[tf] = pct
            else:
                values.append("-")
                row_data[tf] = None
        
        # Volume
        volume = 0
        for r in results.values():
            volume = r.volume
            break
        values.append(self.format_volume(volume))
        row_data['volume'] = volume
        
        # Determine row tag based on 1M momentum and data freshness
        tag = 'neutral'
        is_stale = False
        if latest_date and hasattr(latest_date, 'year'):
            days_old = (today - latest_date).days
            if days_old > 1:
                tag = 'stale'  # Stale data warning
                is_stale = True
            elif '1M' in results:
                if results['1M'].pct_change > 0:
                    tag = 'positive'
                elif results['1M'].pct_change < 0:
                    tag = 'negative'
        elif '1M' in results:
            if results['1M'].pct_change > 0:
                tag = 'positive'
            elif results['1M'].pct_change < 0:
                tag = 'negative'
        
        # Track stale count
        if is_stale and hasattr(self, 'stale_count'):
            self.stale_count += 1
        # Insert row
        self.tree.insert('', 'end', values=values, tags=(tag,))
        self.results_data.append(row_data)
        
    def format_volume(self, volume):
        """Format volume for display"""
        if volume >= 10000000:  # 1 Cr
            return f"{volume/10000000:.2f} Cr"
        elif volume >= 100000:  # 1 Lakh
            return f"{volume/100000:.2f} L"
        elif volume >= 1000:
            return f"{volume/1000:.1f} K"
        return str(volume)
        
    def scan_complete(self, success, fail):
        """Handle scan completion"""
        self.is_scanning = False
        self.scan_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.progress_var.set(100)
        
        # Check for stale data
        stale_count = getattr(self, 'stale_count', 0)
        if stale_count > 0:
            self.status_label.configure(
                text=f"✅ Scan complete! {success} analyzed, {fail} failed. ⚠️ {stale_count} stocks using older data (see Data Date column)"
            )
        else:
            self.status_label.configure(
                text=f"✅ Scan complete! {success} stocks analyzed, {fail} failed. All data is current."
            )
        
        self.time_label.configure(
            text=f"Last scan: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.progress_label.configure(text="Scan complete")
        
    def scan_error(self, error):
        """Handle scan error"""
        self.is_scanning = False
        self.scan_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        
        self.status_label.configure(text=f"❌ Error: {error}")
        messagebox.showerror("Scan Error", f"An error occurred:\n{error}")
        
    def update_status(self, message):
        """Update status bar message"""
        self.root.after(0, lambda: self.status_label.configure(text=message))
        
    def sort_by_column(self, col):
        """Sort table by clicked column"""
        # Get all items
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        # Parse values for sorting
        def parse_value(val):
            if val == '-':
                return float('-inf')
            try:
                # Remove %, ₹, and other formatting
                clean = val.replace('%', '').replace('₹', '').replace(',', '')
                clean = clean.replace(' Cr', 'e7').replace(' L', 'e5').replace(' K', 'e3')
                clean = clean.replace('+', '')
                return float(clean)
            except:
                return val
        
        # Sort
        items.sort(key=lambda x: parse_value(x[0]), reverse=True)
        
        # Rearrange items
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
            
    def export_csv(self):
        """Export results to CSV"""
        if not self.results_data:
            messagebox.showwarning("Warning", "No data to export. Run a scan first.")
            return
        
        # Ask for file location
        filename = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')],
            initialfile=f"momentum_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                df = pd.DataFrame(self.results_data)
                df.to_csv(filename, index=False)
                messagebox.showinfo("Success", f"Data exported to:\n{filename}")
                self.status_label.configure(text=f"📥 Exported to {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export:\n{e}")
    
    # =========================================================================
    # DATA VALIDATION METHODS
    # =========================================================================
    
    def validate_data(self):
        """Validate data availability for all Nifty 500 stocks"""
        if self.is_validating:
            return
        
        self.is_validating = True
        self.validate_btn.configure(state='disabled')
        self.status_label.configure(text="🔄 Validating data availability...")
        
        # Run validation in background thread
        thread = threading.Thread(target=self._run_validation)
        thread.daemon = True
        thread.start()
    
    def _run_validation(self):
        """Run validation in background thread"""
        try:
            limit = self.get_stock_limit()
            # Add .NS suffix for database lookup
            stocks = [f"{s}.NS" for s in NIFTY_500_STOCKS[:limit]]
            
            # Check data availability
            self.data_status = self.db_service.check_data_availability(stocks, required_days=365)
            
            # Check today's coverage
            today_status = self.db_service.get_today_coverage(stocks)
            
            # Update UI
            self.root.after(0, lambda: self._update_validation_ui(today_status))
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            self.root.after(0, lambda: self._validation_error(str(e)))
        finally:
            self.is_validating = False
            self.root.after(0, lambda: self.validate_btn.configure(state='normal'))
    
    def _update_validation_ui(self, today_status):
        """Update UI with validation results"""
        if not self.data_status:
            return
        
        complete = len(self.data_status['complete'])
        stale = len(self.data_status['stale'])
        missing = len(self.data_status['missing'])
        insufficient = len(self.data_status['insufficient'])
        today_pct = today_status['coverage_pct']
        
        # Exclude known unfetchable symbols from missing count
        unfetchable = getattr(self, 'unfetchable_symbols', set())
        actual_missing = [s for s in self.data_status['missing'] if s not in unfetchable]
        actual_stale = [s for s in self.data_status['stale'] if s not in unfetchable]
        unfetchable_count = len(unfetchable)
        
        # Update labels
        self.complete_label.configure(text=f"✓ Complete: {complete}")
        self.stale_label.configure(text=f"⏰ Stale: {len(actual_stale)}")
        if unfetchable_count > 0:
            self.missing_label.configure(text=f"✗ Missing: {len(actual_missing)} (+ {unfetchable_count} ETFs)")
        else:
            self.missing_label.configure(text=f"✗ Missing: {len(actual_missing) + insufficient}")
        self.today_label.configure(text=f"📅 Today: {today_pct:.0f}%")
        
        # Enable download button if there are fetchable missing/stale stocks
        need_download = len(actual_stale) + len(actual_missing) + insufficient
        if need_download > 0:
            self.download_btn.configure(state='normal')
            self.status_label.configure(
                text=f"⚠️ {need_download} stocks need data update. Click 'Download Missing' to fetch."
            )
        else:
            self.download_btn.configure(state='disabled')
            if unfetchable_count > 0:
                self.status_label.configure(
                    text=f"✅ Data complete for {complete} stocks. {unfetchable_count} symbols unavailable (ETFs/delisted)."
                )
            else:
                self.status_label.configure(
                    text=f"✅ Data is complete for all {complete} stocks. Ready to scan!"
                )
    
    def _validation_error(self, error):
        """Handle validation error"""
        self.status_label.configure(text=f"❌ Validation error: {error}")
        self.complete_label.configure(text="✓ Complete: Error")
        self.stale_label.configure(text="⏰ Stale: Error")
        self.missing_label.configure(text="✗ Missing: Error")
    
    def download_missing_data(self):
        """Download missing data for stocks that need updates"""
        if not self.data_status:
            messagebox.showwarning("Warning", "Please validate data first")
            return
        
        # Get known unfetchable symbols
        unfetchable = getattr(self, 'unfetchable_symbols', set())
        
        # Collect all stocks that need downloading (excluding known unfetchable)
        stocks_to_download = [
            s for s in (
                self.data_status['missing'] + 
                self.data_status['stale'] + 
                self.data_status['insufficient']
            ) if s not in unfetchable
        ]
        
        if not stocks_to_download:
            if unfetchable:
                messagebox.showinfo("Info", 
                    f"No fetchable stocks need downloading.\n"
                    f"{len(unfetchable)} symbols are ETFs/delisted (unavailable on Yahoo).")
            else:
                messagebox.showinfo("Info", "No stocks need downloading")
            return
        
        # Confirm
        if not messagebox.askyesno(
            "Download Data",
            f"Download data for {len(stocks_to_download)} stocks?\n\n"
            f"This may take a few minutes."
        ):
            return
        
        self.download_btn.configure(state='disabled')
        self.status_label.configure(text=f"📥 Downloading data for {len(stocks_to_download)} stocks...")
        
        # Run download in background
        thread = threading.Thread(target=self._run_download, args=(stocks_to_download,))
        thread.daemon = True
        thread.start()
    
    def _run_download(self, stocks):
        """Run download in background thread"""
        success_count = 0
        fail_count = 0
        failed_symbols = []
        total = len(stocks)
        
        for i, symbol in enumerate(stocks):
            try:
                # Update progress
                progress = ((i + 1) / total) * 100
                self.root.after(0, lambda p=progress, s=symbol: 
                    self.progress_label.configure(text=f"Downloading: {s} ({p:.0f}%)"))
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # Download
                if self.calculator.download_missing_data(symbol, days=400):
                    success_count += 1
                else:
                    fail_count += 1
                    failed_symbols.append(symbol)
                
                # Rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {e}")
                fail_count += 1
                failed_symbols.append(symbol)
        
        # Complete - track failed symbols
        self.root.after(0, lambda: self._download_complete(success_count, fail_count, failed_symbols))
    
    def _download_complete(self, success, fail, failed_symbols):
        """Handle download completion"""
        self.download_btn.configure(state='normal')
        self.progress_var.set(0)
        self.progress_label.configure(text="Download complete")
        
        # Store failed symbols (ETFs, delisted stocks, etc.)
        if not hasattr(self, 'unfetchable_symbols'):
            self.unfetchable_symbols = set()
        self.unfetchable_symbols.update(failed_symbols)
        
        if fail > 0:
            self.status_label.configure(
                text=f"📥 Download: {success} succeeded, {fail} unavailable (ETFs/delisted). Revalidating..."
            )
        else:
            self.status_label.configure(
                text=f"📥 Download complete! {success} stocks updated. Revalidating..."
            )
        
        # Auto-revalidate
        self.root.after(1000, self.validate_data)
                
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = MomentumScannerGUI()
    app.run()


if __name__ == "__main__":
    main()
