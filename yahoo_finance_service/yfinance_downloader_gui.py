#!/usr/bin/env python3
"""
Yahoo Finance Data Downloader GUI
Main interface for downloading stock market data from Yahoo Finance
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import threading
import time
import logging
from typing import Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from yahoo_client import YahooFinanceClient
from db_service import YFinanceDBService
from models import DownloadLog
from config import YFinanceConfig

# Setup logging
logging.basicConfig(level=YFinanceConfig.LOG_LEVEL)
logger = logging.getLogger(__name__)

class YFinanceDownloaderGUI:
    """Main GUI for Yahoo Finance data downloading"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📈 Yahoo Finance Data Downloader")
        self.root.geometry("800x700")
        self.root.configure(bg='#1a1a2e')
        
        # Services
        self.yahoo_client = YahooFinanceClient()
        self.db_service = YFinanceDBService()
        
        # State variables
        self.is_downloading = False
        self.download_thread = None
        
        # Bulk download tracking
        self.is_bulk_downloading = False
        self.bulk_symbols_list = []
        self.current_bulk_index = 0
        self.bulk_success_count = 0
        self.bulk_failure_count = 0
        
        # Cache for loaded symbols
        self.index_symbols = []
        self.stock_symbols = []
        
        # Color scheme
        self.colors = {
            'bg': '#1a1a2e',
            'card': '#16213e',
            'accent': '#0f3460',
            'primary': '#e94560',
            'text': '#ffffff',
            'secondary': '#a8a8a8',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'error': '#e74c3c'
        }
        
        # Fonts
        self.fonts = {
            'title': ('Segoe UI', 16, 'bold'),
            'subtitle': ('Segoe UI', 12, 'bold'),
            'body': ('Segoe UI', 10),
            'small': ('Segoe UI', 9),
            'mono': ('Consolas', 10)
        }
        
        self.setup_ui()
        self.check_database_connection()
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        self.setup_title(main_frame)
        
        # Settings panel
        self.setup_settings_panel(main_frame)
        
        # Date range panel
        self.setup_date_panel(main_frame)
        
        # Control panel
        self.setup_control_panel(main_frame)
        
        # Progress panel
        self.setup_progress_panel(main_frame)
        
        # Data preview panel
        self.setup_preview_panel(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_title(self, parent):
        """Setup title section"""
        title_frame = tk.Frame(parent, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            title_frame,
            text="📈 Yahoo Finance Data Downloader",
            font=self.fonts['title'],
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title_label.pack(side=tk.LEFT)
        
        version_label = tk.Label(
            title_frame,
            text="v1.0 • MarketData Database",
            font=self.fonts['small'],
            bg=self.colors['bg'],
            fg=self.colors['secondary']
        )
        version_label.pack(side=tk.RIGHT)
    
    def setup_settings_panel(self, parent):
        """Setup download settings panel"""
        settings_frame = tk.LabelFrame(
            parent,
            text="📊 Download Settings",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            relief=tk.RAISED,
            bd=2
        )
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        
        content_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        content_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Symbol selection
        symbol_frame = tk.Frame(content_frame, bg=self.colors['card'])
        symbol_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            symbol_frame,
            text="Symbol:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=12,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        # Category selection
        self.symbol_category_var = tk.StringVar(value="Indices")
        category_combo = ttk.Combobox(
            symbol_frame,
            textvariable=self.symbol_category_var,
            values=["Indices", "Stocks"],
            width=10,
            state="readonly"
        )
        category_combo.pack(side=tk.LEFT, padx=(5, 10))
        category_combo.bind('<<ComboboxSelected>>', self.on_category_changed)
        
        # Symbol selection dropdown
        self.symbol_var = tk.StringVar(value=YFinanceConfig.DEFAULT_SYMBOL)
        self.symbol_combo = ttk.Combobox(
            symbol_frame,
            textvariable=self.symbol_var,
            values=["NIFTY", "BANKNIFTY", "SENSEX"],  # Default indices
            width=20,
            state="readonly"
        )
        self.symbol_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        # Load symbols button for stocks
        self.load_symbols_button = tk.Button(
            symbol_frame,
            text="🔄 Load Stocks",
            command=self.load_stock_symbols,
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=10,
            pady=2
        )
        
        # Symbol info
        self.symbol_info_label = tk.Label(
            symbol_frame,
            text="Select category to view symbols",
            font=self.fonts['small'],
            bg=self.colors['card'],
            fg=self.colors['secondary']
        )
        self.symbol_info_label.pack(side=tk.RIGHT)
        
        # Bulk download options
        bulk_frame = tk.Frame(content_frame, bg=self.colors['card'])
        bulk_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Bulk download checkbox
        self.bulk_download_var = tk.BooleanVar()
        self.bulk_download_checkbox = tk.Checkbutton(
            bulk_frame,
            text="Download All Symbols",
            variable=self.bulk_download_var,
            command=self.on_bulk_download_changed,
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            selectcolor=self.colors['accent'],
            activebackground=self.colors['card']
        )
        self.bulk_download_checkbox.pack(side=tk.LEFT, padx=(0, 20))
        
        # Duration selection for bulk downloads
        tk.Label(
            bulk_frame,
            text="Duration:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text']
        ).pack(side=tk.LEFT)
        
        self.duration_var = tk.StringVar(value="1 Year")
        self.duration_combo = ttk.Combobox(
            bulk_frame,
            textvariable=self.duration_var,
            values=["1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "5 Years", "Max"],
            width=12,
            state="readonly"
        )
        self.duration_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        # Quick action button for 5-year historical data
        self.quick_5year_button = tk.Button(
            bulk_frame,
            text="📥 5Y All Stocks",
            command=self.quick_download_5year_all_stocks,
            font=self.fonts['small'],
            bg=self.colors['primary'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        self.quick_5year_button.pack(side=tk.LEFT)
        
        # Timeframe selection
        timeframe_frame = tk.Frame(content_frame, bg=self.colors['card'])
        timeframe_frame.pack(fill=tk.X)
        
        tk.Label(
            timeframe_frame,
            text="Timeframe:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=12,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.timeframe_var = tk.StringVar(value=YFinanceConfig.DEFAULT_TIMEFRAME)
        timeframe_entry = tk.Entry(
            timeframe_frame,
            textvariable=self.timeframe_var,
            font=self.fonts['body'],
            width=15,
            state='readonly'  # Fixed for now
        )
        timeframe_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        tk.Label(
            timeframe_frame,
            text="(Future: Multiple timeframes)",
            font=self.fonts['small'],
            bg=self.colors['card'],
            fg=self.colors['secondary']
        ).pack(side=tk.LEFT)
    
    def setup_date_panel(self, parent):
        """Setup date range selection panel"""
        date_frame = tk.LabelFrame(
            parent,
            text="📅 Date Range Selection",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            relief=tk.RAISED,
            bd=2
        )
        date_frame.pack(fill=tk.X, pady=(0, 15))
        
        content_frame = tk.Frame(date_frame, bg=self.colors['card'])
        content_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Start date
        start_frame = tk.Frame(content_frame, bg=self.colors['card'])
        start_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            start_frame,
            text="Start Date:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=12,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        # Start date controls
        self.start_year_var = tk.StringVar(value="2024")
        self.start_month_var = tk.StringVar(value="1")
        self.start_day_var = tk.StringVar(value="1")
        
        self.start_year_combo = ttk.Combobox(
            start_frame,
            textvariable=self.start_year_var,
            values=[str(year) for year in range(2020, 2026)],
            width=6,
            state="readonly"
        )
        self.start_year_combo.pack(side=tk.LEFT, padx=(5, 2))
        
        tk.Label(start_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.start_month_combo = ttk.Combobox(
            start_frame,
            textvariable=self.start_month_var,
            values=[f"{i:02d}" for i in range(1, 13)],
            width=4,
            state="readonly"
        )
        self.start_month_combo.pack(side=tk.LEFT, padx=2)
        
        tk.Label(start_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.start_day_combo = ttk.Combobox(
            start_frame,
            textvariable=self.start_day_var,
            values=[f"{i:02d}" for i in range(1, 32)],
            width=4,
            state="readonly"
        )
        self.start_day_combo.pack(side=tk.LEFT, padx=(2, 10))
        
        # Quick start date buttons
        today = date.today()
        
        tk.Button(
            start_frame,
            text="1 Year Ago",
            command=lambda: self.set_start_date(today - timedelta(days=365)),
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=8,
            pady=2
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            start_frame,
            text="YTD",
            command=lambda: self.set_start_date(date(today.year, 1, 1)),
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=8,
            pady=2
        ).pack(side=tk.LEFT, padx=2)
        
        # End date
        end_frame = tk.Frame(content_frame, bg=self.colors['card'])
        end_frame.pack(fill=tk.X)
        
        tk.Label(
            end_frame,
            text="End Date:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=12,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        # End date controls
        self.end_year_var = tk.StringVar(value=str(today.year))
        self.end_month_var = tk.StringVar(value=f"{today.month:02d}")
        self.end_day_var = tk.StringVar(value=f"{today.day:02d}")
        
        self.end_year_combo = ttk.Combobox(
            end_frame,
            textvariable=self.end_year_var,
            values=[str(year) for year in range(2020, 2026)],
            width=6,
            state="readonly"
        )
        self.end_year_combo.pack(side=tk.LEFT, padx=(5, 2))
        
        tk.Label(end_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.end_month_combo = ttk.Combobox(
            end_frame,
            textvariable=self.end_month_var,
            values=[f"{i:02d}" for i in range(1, 13)],
            width=4,
            state="readonly"
        )
        self.end_month_combo.pack(side=tk.LEFT, padx=2)
        
        tk.Label(end_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.end_day_combo = ttk.Combobox(
            end_frame,
            textvariable=self.end_day_var,
            values=[f"{i:02d}" for i in range(1, 32)],
            width=4,
            state="readonly"
        )
        self.end_day_combo.pack(side=tk.LEFT, padx=(2, 10))
        
        # Quick end date buttons
        tk.Button(
            end_frame,
            text="Today",
            command=lambda: self.set_end_date(today),
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=8,
            pady=2
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            end_frame,
            text="Yesterday",
            command=lambda: self.set_end_date(today - timedelta(days=1)),
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=8,
            pady=2
        ).pack(side=tk.LEFT, padx=2)
    
    def set_start_date(self, date_value: date):
        """Set start date from date object"""
        self.start_year_var.set(str(date_value.year))
        self.start_month_var.set(f"{date_value.month:02d}")
        self.start_day_var.set(f"{date_value.day:02d}")
    
    def set_end_date(self, date_value: date):
        """Set end date from date object"""
        self.end_year_var.set(str(date_value.year))
        self.end_month_var.set(f"{date_value.month:02d}")
        self.end_day_var.set(f"{date_value.day:02d}")
    
    def get_selected_dates(self) -> tuple:
        """Get selected start and end dates"""
        try:
            start_date = date(
                int(self.start_year_var.get()),
                int(self.start_month_var.get()),
                int(self.start_day_var.get())
            )
            
            end_date = date(
                int(self.end_year_var.get()),
                int(self.end_month_var.get()),
                int(self.end_day_var.get())
            )
            
            return start_date, end_date
            
        except ValueError as e:
            raise ValueError(f"Invalid date selection: {e}")
    
    def setup_control_panel(self, parent):
        """Setup control buttons panel"""
        control_frame = tk.Frame(parent, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Download button
        self.download_button = tk.Button(
            control_frame,
            text="🔽 Download Data",
            command=self.start_download,
            font=self.fonts['subtitle'],
            bg=self.colors['primary'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Stop button
        self.stop_button = tk.Button(
            control_frame,
            text="⏹️ Stop",
            command=self.stop_download,
            font=self.fonts['body'],
            bg=self.colors['error'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # View data button
        self.view_button = tk.Button(
            control_frame,
            text="📊 View Data",
            command=self.open_data_viewer,
            font=self.fonts['body'],
            bg=self.colors['success'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=15,
            pady=8
        )
        self.view_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Database info
        self.db_info_label = tk.Label(
            control_frame,
            text="Database: Checking connection...",
            font=self.fonts['small'],
            bg=self.colors['bg'],
            fg=self.colors['secondary']
        )
        self.db_info_label.pack(side=tk.RIGHT)
    
    def setup_progress_panel(self, parent):
        """Setup progress tracking panel"""
        progress_frame = tk.LabelFrame(
            parent,
            text="📊 Download Progress",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            relief=tk.RAISED,
            bd=2
        )
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        content_frame = tk.Frame(progress_frame, bg=self.colors['card'])
        content_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            content_frame,
            variable=self.progress_var,
            maximum=100,
            length=500
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Progress text
        self.progress_text_var = tk.StringVar(value="Ready to download data")
        self.progress_text = tk.Label(
            content_frame,
            textvariable=self.progress_text_var,
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            anchor='w'
        )
        self.progress_text.pack(fill=tk.X)
    
    def setup_preview_panel(self, parent):
        """Setup data preview panel"""
        preview_frame = tk.LabelFrame(
            parent,
            text="📋 Data Preview",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            relief=tk.RAISED,
            bd=2
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create treeview for data display
        tree_frame = tk.Frame(preview_frame, bg=self.colors['card'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Treeview with scrollbar
        columns = ('Date', 'Open', 'High', 'Low', 'Close', 'Volume')
        self.preview_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)
        
        # Configure columns
        for col in columns:
            self.preview_tree.heading(col, text=col)
            self.preview_tree.column(col, width=80, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = tk.Frame(parent, bg=self.colors['accent'], relief=tk.SUNKEN, bd=1)
        status_frame.pack(fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready • Select date range and click Download Data")
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text'],
            anchor='w'
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=3)
    
    def check_database_connection(self):
        """Check and display database connection status"""
        try:
            # Get database status
            status = self.db_service.get_database_status()
            
            if status['connection_status'] == 'Connected':
                self.db_info_label.config(
                    text=f"Database: ✅ Connected • {status['total_quotes']:,} records",
                    fg=self.colors['success']
                )
                self.status_var.set(f"Connected to MarketData database • {status['total_quotes']:,} existing records")
            else:
                self.db_info_label.config(
                    text=f"Database: ❌ {status['connection_status']}",
                    fg=self.colors['error']
                )
                self.status_var.set("Database connection failed - check configuration")
                
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            self.db_info_label.config(
                text="Database: ❌ Connection failed",
                fg=self.colors['error']
            )
            self.status_var.set(f"Database error: {str(e)[:50]}...")
    
    def on_category_changed(self, event=None):
        """Handle symbol category selection change"""
        category = self.symbol_category_var.get()
        
        if category == "Indices":
            # Show indices symbols
            indices = ["NIFTY", "BANKNIFTY", "SENSEX"]
            self.symbol_combo.configure(values=indices)
            self.symbol_var.set("NIFTY")
            self.load_symbols_button.pack_forget()
            self.symbol_info_label.config(text="Market Indices Available")
        
        elif category == "Stocks":
            # Show stock loading option
            self.symbol_combo.configure(values=["Click 'Load Stocks' to view available stocks"])
            self.symbol_var.set("")
            self.load_symbols_button.pack(side=tk.LEFT, padx=(5, 10))
            self.symbol_info_label.config(text="Click Load Stocks to see mapped symbols")
    
    def get_date_range_from_duration(self, duration):
        """Get start and end dates from duration string"""
        end_date = datetime.now()
        
        if duration == "1 Week":
            start_date = end_date - timedelta(weeks=1)
        elif duration == "1 Month":
            start_date = end_date - timedelta(days=30)
        elif duration == "3 Months":
            start_date = end_date - timedelta(days=90)
        elif duration == "6 Months":
            start_date = end_date - timedelta(days=180)
        elif duration == "1 Year":
            start_date = end_date - timedelta(days=365)
        elif duration == "2 Years":
            start_date = end_date - timedelta(days=730)
        elif duration == "5 Years":
            start_date = end_date - timedelta(days=1825)  # 5 * 365
        else:  # "Max"
            start_date = end_date - timedelta(days=3650)  # 10 years
            
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def load_stock_symbols(self):
        """Load stock symbols from the database mapping"""
        try:
            self.status_var.set("Loading stock symbols...")
            self.load_symbols_button.config(text="Loading...", state=tk.DISABLED)
            
            # Get mapped stock symbols from database
            import mysql.connector
            from config import YFinanceConfig
            
            conn = mysql.connector.connect(**YFinanceConfig.get_db_config())
            cursor = conn.cursor()
            
            # Get active mapped symbols with their sector information
            cursor.execute("""
                SELECT nse_symbol, yahoo_symbol, sector 
                FROM nse_yahoo_symbol_map 
                WHERE is_active = 1 AND is_verified = 1
                ORDER BY sector, nse_symbol
            """)
            
            stocks = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if stocks:
                # Format symbols for dropdown (NSE Symbol - Sector)
                stock_options = []
                for nse_symbol, yahoo_symbol, sector in stocks:
                    display_name = f"{nse_symbol} - {sector}" if sector else nse_symbol
                    stock_options.append(display_name)
                
                self.symbol_combo.configure(values=stock_options)
                self.symbol_var.set(stock_options[0] if stock_options else "")
                
                self.symbol_info_label.config(
                    text=f"{len(stocks)} verified stocks loaded",
                    fg=self.colors['success']
                )
                self.status_var.set(f"Loaded {len(stocks)} stock symbols")
            else:
                messagebox.showwarning(
                    "No Stocks", 
                    "No verified stock symbols found. Please run symbol validation first."
                )
                self.symbol_info_label.config(
                    text="No verified symbols found",
                    fg=self.colors['warning']
                )
            
            self.load_symbols_button.config(text="🔄 Reload", state=tk.NORMAL)
            
        except Exception as e:
            logger.error(f"Error loading stock symbols: {e}")
            messagebox.showerror("Error", f"Failed to load stock symbols: {str(e)}")
            self.load_symbols_button.config(text="🔄 Load Stocks", state=tk.NORMAL)
            self.status_var.set("Failed to load stock symbols")
    
    def get_yahoo_symbol(self, display_symbol: str) -> str:
        """Get Yahoo Finance symbol for the selected symbol"""
        try:
            category = self.symbol_category_var.get()
            
            if category == "Indices":
                # Use existing mapping for indices
                symbol_mapping = {
                    'NIFTY': '^NSEI',
                    'BANKNIFTY': '^NSEBANK',
                    'SENSEX': '^BSESN'
                }
                return symbol_mapping.get(display_symbol, display_symbol)
            
            elif category == "Stocks":
                # Extract NSE symbol from display format (NSE Symbol - Sector)
                nse_symbol = display_symbol.split(' - ')[0] if ' - ' in display_symbol else display_symbol
                
                # Look up Yahoo symbol in mapping table
                import mysql.connector
                from config import YFinanceConfig
                
                conn = mysql.connector.connect(**YFinanceConfig.get_db_config())
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT yahoo_symbol FROM nse_yahoo_symbol_map 
                    WHERE nse_symbol = %s AND is_active = 1 AND is_verified = 1
                """, (nse_symbol,))
                
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if result:
                    return result[0]
                else:
                    # Fallback: assume NSE format (symbol.NS)
                    return f"{nse_symbol}.NS"
            
            return display_symbol
            
        except Exception as e:
            logger.error(f"Error getting Yahoo symbol: {e}")
            return display_symbol
    
    def start_download(self):
        """Start the download process"""
        if self.is_downloading or self.is_bulk_downloading:
            return
        
        try:
            # Check if bulk download is selected
            if self.bulk_download_var.get():
                self.start_bulk_download()
                return
            
            # Validate dates for single download
            start_date, end_date = self.get_selected_dates()
            
            if start_date > end_date:
                messagebox.showerror("Error", "Start date must be before end date")
                return
            
            if end_date > date.today():
                messagebox.showerror("Error", "End date cannot be in the future")
                return
            
            # Update UI state
            self.is_downloading = True
            self.download_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.progress_var.set(0)
            self.progress_text_var.set("Starting download...")
            
            # Clear preview
            for item in self.preview_tree.get_children():
                self.preview_tree.delete(item)
            
            # Start download in thread
            self.download_thread = threading.Thread(
                target=self.download_data,
                args=(start_date, end_date),
                daemon=True
            )
            self.download_thread.start()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            logger.error(f"Error starting download: {e}")
            messagebox.showerror("Error", f"Failed to start download: {str(e)}")
    
    def stop_download(self):
        """Stop the download process"""
        self.is_downloading = False
        self.is_bulk_downloading = False
        
        if self.bulk_download_var.get():
            self.progress_text_var.set(f"Bulk download stopped by user ({self.current_bulk_index}/{len(self.bulk_symbols_list) if self.bulk_symbols_list else 0})")
            self.status_var.set(f"Bulk download cancelled • Processed: {self.current_bulk_index} • Success: {self.bulk_success_count} • Failed: {self.bulk_failure_count}")
        else:
            self.progress_text_var.set("Stopping download...")
            self.status_var.set("Download stopped by user")
        
        self.download_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def download_data(self, start_date: date, end_date: date):
        """Download data in background thread"""
        display_symbol = self.symbol_var.get()
        start_time = time.time()
        
        # Get the actual symbols to use
        nse_symbol = display_symbol.split(' - ')[0] if ' - ' in display_symbol else display_symbol
        yahoo_symbol = self.get_yahoo_symbol(display_symbol)
        
        # Create download log
        download_log = DownloadLog(
            symbol=nse_symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=self.timeframe_var.get()
        )
        
        try:
            # Update progress
            self.progress_text_var.set(f"Downloading {nse_symbol} ({yahoo_symbol}) data from {start_date} to {end_date}...")
            self.status_var.set(f"Downloading data from Yahoo Finance for {nse_symbol}...")
            
            # Download quotes using Yahoo symbol but save with NSE symbol
            quotes = self.yahoo_client.download_daily_data_with_symbol(nse_symbol, yahoo_symbol, start_date, end_date)
            
            if not self.is_downloading:
                return
            
            self.progress_var.set(50)
            self.progress_text_var.set(f"Downloaded {len(quotes)} quotes. Saving to database...")
            
            # Save to database
            inserted, updated = self.db_service.insert_quotes(quotes)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Update download log
            download_log.records_downloaded = inserted
            download_log.records_updated = updated
            download_log.status = 'COMPLETED'
            download_log.download_duration_ms = duration_ms
            
            # Log the download
            self.db_service.log_download(download_log)
            
            # Update UI
            self.progress_var.set(100)
            self.progress_text_var.set(f"Completed: {inserted} new, {updated} updated in {duration_ms}ms")
            self.status_var.set(f"Download completed • {inserted} new records, {updated} updated for {nse_symbol}")
            
            # Update preview
            self.update_preview(quotes[-10:] if quotes else [])  # Show last 10 records
            
            # Update database info
            self.root.after(1000, self.check_database_connection)
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            
            # Update download log
            download_log.status = 'FAILED'
            download_log.error_message = str(e)
            download_log.download_duration_ms = int((time.time() - start_time) * 1000)
            
            self.db_service.log_download(download_log)
            
            # Update UI
            self.progress_text_var.set(f"Download failed: {str(e)[:50]}...")
            self.status_var.set(f"Download failed for {nse_symbol} - check logs for details")
            
            messagebox.showerror("Download Error", f"Failed to download data for {nse_symbol}:\n{str(e)}")
            
        finally:
            # Reset UI state
            self.is_downloading = False
            self.download_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def update_preview(self, quotes):
        """Update the data preview with latest quotes"""
        # Clear existing items
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        # Add new quotes
        for quote in reversed(quotes):  # Show newest first
            values = (
                quote.date.strftime('%Y-%m-%d'),
                f"{quote.open:.2f}" if quote.open else "--",
                f"{quote.high:.2f}" if quote.high else "--",
                f"{quote.low:.2f}" if quote.low else "--",
                f"{quote.close:.2f}" if quote.close else "--",
                f"{quote.volume:,}" if quote.volume else "--"
            )
            self.preview_tree.insert('', tk.END, values=values)
    
    def open_data_viewer(self):
        """Open the data viewer window"""
        try:
            # This would launch the data viewer GUI
            messagebox.showinfo("Info", "Data viewer will be implemented in the next phase")
        except Exception as e:
            logger.error(f"Error opening data viewer: {e}")
            messagebox.showerror("Error", f"Failed to open data viewer: {str(e)}")
    
    def on_bulk_download_changed(self):
        """Handle bulk download checkbox change"""
        if self.bulk_download_var.get():
            # Disable individual date selection
            self.start_year_combo.config(state="disabled")
            self.start_month_combo.config(state="disabled")  
            self.start_day_combo.config(state="disabled")
            self.end_year_combo.config(state="disabled")
            self.end_month_combo.config(state="disabled")
            self.end_day_combo.config(state="disabled")
            self.duration_combo.config(state="readonly")
        else:
            # Enable individual date selection
            self.start_year_combo.config(state="readonly")
            self.start_month_combo.config(state="readonly")
            self.start_day_combo.config(state="readonly") 
            self.end_year_combo.config(state="readonly")
            self.end_month_combo.config(state="readonly")
            self.end_day_combo.config(state="readonly")
            self.duration_combo.config(state="disabled")
    
    def get_date_range_from_duration(self, duration):
        """Get start and end dates from duration selection"""
        from datetime import timedelta
        end_date = date.today()
        
        if duration == "1 Month":
            start_date = end_date - timedelta(days=30)
        elif duration == "3 Months":
            start_date = end_date - timedelta(days=90)
        elif duration == "6 Months":
            start_date = end_date - timedelta(days=180)
        elif duration == "1 Year":
            start_date = end_date - timedelta(days=365)
        elif duration == "2 Years":
            start_date = end_date - timedelta(days=730)
        elif duration == "5 Years":
            start_date = end_date - timedelta(days=1825)
        elif duration == "Max":
            start_date = date(2000, 1, 1)  # Far back date
        else:
            start_date = end_date - timedelta(days=365)  # Default 1 year
        
        return start_date, end_date
    
    def start_bulk_download(self):
        """Start bulk download process"""
        try:
            # Get symbols to download based on category
            if self.symbol_category_var.get() == "Stocks":
                # Auto-load stocks if not already loaded
                if not hasattr(self, 'stock_symbols') or not self.stock_symbols or len(self.symbol_combo['values']) == 0:
                    self.status_var.set("Loading stock symbols for bulk download...")
                    self.load_stock_symbols()
                    
                symbols_to_download = [opt for opt in self.symbol_combo['values']]
                if not symbols_to_download:
                    messagebox.showerror("Error", "No verified stock symbols found in database. Please run symbol verification first.")
                    return
            else:
                # Use default indices
                symbols_to_download = ["^NSEI", "^NSEBANK", "^CNXIT", "^CNXAUTO", "^CNXPHARMA", "^CNXFMCG"]
            
            if not symbols_to_download:
                messagebox.showerror("Error", "No symbols available for bulk download")
                return
            
            # Confirm bulk download
            result = messagebox.askyesno(
                "Bulk Download Confirmation", 
                f"Download data for {len(symbols_to_download)} symbols?\\n\\n"
                f"Category: {self.symbol_category_var.get()}\\n"
                f"Duration: {self.duration_var.get()}\\n"
                f"This may take several minutes."
            )
            
            if not result:
                return
            
            # Reset counters
            self.bulk_symbols_list = symbols_to_download
            self.current_bulk_index = 0
            self.bulk_success_count = 0
            self.bulk_failure_count = 0
            
            # Start bulk download
            self.is_bulk_downloading = True
            self.download_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            self.download_thread = threading.Thread(
                target=self.bulk_download_worker,
                daemon=True
            )
            self.download_thread.start()
            
        except Exception as e:
            logger.error(f"Error starting bulk download: {e}")
            messagebox.showerror("Error", f"Failed to start bulk download: {e}")
    
    def bulk_download_worker(self):
        """Worker thread for bulk download"""
        start_date, end_date = self.get_date_range_from_duration(self.duration_var.get())
        
        for i, symbol_display in enumerate(self.bulk_symbols_list):
            if not self.is_bulk_downloading:
                break
            
            self.current_bulk_index = i
            
            try:
                # Update progress
                progress = int((i / len(self.bulk_symbols_list)) * 100)
                self.progress_var.set(progress)
                self.progress_text_var.set(
                    f"Downloading {i+1}/{len(self.bulk_symbols_list)}: {symbol_display.split(' - ')[0]}"
                )
                self.status_var.set(
                    f"Bulk Download Progress: {i+1}/{len(self.bulk_symbols_list)} • "
                    f"Success: {self.bulk_success_count} • Failed: {self.bulk_failure_count}"
                )
                
                # Download symbol data
                nse_symbol = symbol_display.split(' - ')[0] if ' - ' in symbol_display else symbol_display
                yahoo_symbol = self.get_yahoo_symbol(symbol_display)
                
                quotes = self.yahoo_client.download_daily_data_with_symbol(nse_symbol, yahoo_symbol, start_date, end_date)
                
                if quotes:
                    inserted, updated = self.db_service.insert_quotes(quotes)
                    self.bulk_success_count += 1
                    
                    # Log successful download
                    download_log = DownloadLog(
                        symbol=nse_symbol,
                        start_date=start_date,
                        end_date=end_date,
                        timeframe=self.timeframe_var.get(),
                        records_downloaded=inserted,
                        records_updated=updated,
                        status='COMPLETED'
                    )
                    self.db_service.log_download(download_log)
                else:
                    self.bulk_failure_count += 1
                    
            except Exception as e:
                logger.error(f"Error downloading {symbol_display}: {e}")
                self.bulk_failure_count += 1
                
                # Log failed download
                nse_symbol = symbol_display.split(' - ')[0] if ' - ' in symbol_display else symbol_display
                download_log = DownloadLog(
                    symbol=nse_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=self.timeframe_var.get(),
                    status='FAILED',
                    error_message=str(e)
                )
                self.db_service.log_download(download_log)
        
        # Bulk download complete
        if self.is_bulk_downloading:
            self.progress_var.set(100)
            self.progress_text_var.set(
                f"Bulk download completed: {self.bulk_success_count} successful, {self.bulk_failure_count} failed"
            )
            self.status_var.set(
                f"Bulk download completed • Success: {self.bulk_success_count} • Failed: {self.bulk_failure_count}"
            )
            
            messagebox.showinfo(
                "Bulk Download Complete",
                f"Download completed!\\n\\n"
                f"Successfully downloaded: {self.bulk_success_count}\\n"
                f"Failed downloads: {self.bulk_failure_count}\\n"
                f"Total processed: {len(self.bulk_symbols_list)}"
            )
        
        # Reset UI state
        self.is_bulk_downloading = False
        self.download_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # Update database info
        self.root.after(1000, self.check_database_connection)
    
    def quick_download_5year_all_stocks(self):
        """Quick method to download 5 years of data for all verified stocks"""
        try:
            # First, ensure we're in the right mode
            if self.symbol_category_var.get() != "Stocks":
                self.symbol_category_var.set("Stocks")
                self.on_category_changed()
            
            # Check if symbols are already loaded
            try:
                current_values = self.symbol_combo.cget('values')
                symbols_count = len(current_values) if current_values else 0
            except:
                symbols_count = 0
            
            # If no symbols loaded, try to load them
            if symbols_count == 0:
                self.status_var.set("Loading all verified stock symbols...")
                self.load_stock_symbols()
                self.root.update()
                
                # Check again after loading
                try:
                    current_values = self.symbol_combo.cget('values')
                    symbols_count = len(current_values) if current_values else 0
                except:
                    symbols_count = 0
            
            # Final check
            if symbols_count == 0:
                messagebox.showerror("Error", 
                    "Could not load stock symbols from the GUI.\\n\\n"
                    "Please try this sequence:\\n"
                    "1. Select 'Stocks' category\\n"
                    "2. Click 'Load Stocks' button\\n" 
                    "3. Wait for symbols to load\\n"
                    "4. Then click '5Y All Stocks' again")
                return
            
            # Set up for bulk download
            self.duration_var.set("5 Years")
            self.bulk_download_var.set(True)
            self.on_bulk_download_changed()
            
            # Confirm the download
            result = messagebox.askyesno(
                "Download 5 Years Historical Data",
                f"This will download 5 years of daily data for {symbols_count} stocks.\\n\\n"
                f"Estimated time: {symbols_count * 2} minutes\\n"
                f"Continue with the download?"
            )
            
            if result:
                # Create list of symbols for bulk download
                self.bulk_symbols_list = []
                for display_symbol in current_values:
                    # Extract NSE symbol from display format 
                    nse_symbol = display_symbol.split(' - ')[0] if ' - ' in display_symbol else display_symbol
                    yahoo_symbol = f"{nse_symbol}.NS"
                    self.bulk_symbols_list.append({
                        'display': display_symbol,
                        'nse': nse_symbol,
                        'yahoo': yahoo_symbol
                    })
                
                # Start the bulk download
                self.start_bulk_download()
            else:
                # Reset settings if user cancels
                self.bulk_download_var.set(False)
                self.on_bulk_download_changed()
                
        except Exception as e:
            logger.error(f"Error in quick 5-year download: {e}")
            messagebox.showerror("Error", f"Failed to start 5-year download: {e}")
            
            # Reset settings on error
            try:
                self.bulk_download_var.set(False)
                self.on_bulk_download_changed()
            except:
                pass
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            self.root.quit()

if __name__ == "__main__":
    app = YFinanceDownloaderGUI()
    app.run()