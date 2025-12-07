#!/usr/bin/env python3
"""
Turnover Analysis GUI
=====================
Interactive GUI for analyzing stock turnover (Daily, Weekly, Monthly).

Features:
- Daily/Weekly/Monthly turnover tables
- Top turnover stocks scanner
- Unusual turnover detection
- Interactive charts
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
import threading

from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Try to import tkcalendar for date picker
try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates

load_dotenv()

# Constants
CRORE = 10_000_000


class TurnoverAnalysisGUI:
    """GUI for turnover analysis."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("📊 Turnover Analysis")
        self.root.geometry("1400x850")
        
        # Database connection
        self.engine = self._create_engine()
        
        # Data storage
        self.daily_df = None
        self.weekly_df = None
        self.monthly_df = None
        
        # Setup UI
        self._setup_styles()
        self._create_widgets()
        
        # Load initial data
        self.root.after(100, self._load_symbols)
    
    def _create_engine(self):
        """Create database engine."""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        return create_engine(
            f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{password}"
            f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
            f"/{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4",
            pool_pre_ping=True
        )
    
    def _setup_styles(self):
        """Setup ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Stats.TLabel', font=('Arial', 11))
        
        # Treeview style
        style.configure('Treeview', font=('Arial', 9), rowheight=22)
        style.configure('Treeview.Heading', font=('Arial', 9, 'bold'))
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top control bar
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Symbol selection
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        self.symbol_var = tk.StringVar(value="RELIANCE.NS")
        self.symbol_combo = ttk.Combobox(control_frame, textvariable=self.symbol_var, 
                                          width=20, state='normal')
        self.symbol_combo.pack(side=tk.LEFT, padx=5)
        self.symbol_combo.bind('<Return>', lambda e: self._load_stock_data())
        
        ttk.Button(control_frame, text="🔄 Load", command=self._load_stock_data).pack(side=tk.LEFT, padx=10)
        
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)
        
        # Quick actions
        ttk.Button(control_frame, text="📈 Top Turnover", command=self._show_top_turnover).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="⚡ Unusual", command=self._show_unusual_turnover).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.status_var, style='Stats.TLabel').pack(side=tk.RIGHT, padx=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Daily Turnover
        self.daily_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.daily_tab, text="📅 Daily")
        self._create_daily_tab()
        
        # Tab 2: Weekly Turnover
        self.weekly_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.weekly_tab, text="📆 Weekly")
        self._create_weekly_tab()
        
        # Tab 3: Monthly Turnover
        self.monthly_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.monthly_tab, text="📊 Monthly")
        self._create_monthly_tab()
        
        # Tab 4: Top Turnover
        self.top_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.top_tab, text="🏆 Top Stocks")
        self._create_top_tab()
        
        # Tab 5: Unusual Turnover
        self.unusual_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.unusual_tab, text="⚡ Unusual")
        self._create_unusual_tab()
        
        # Tab 6: Frequency Analysis (Top 100 appearances)
        self.frequency_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.frequency_tab, text="📈 Frequency")
        self._create_frequency_tab()
        
        # Tab 7: Event Analysis (Price after high turnover)
        self.event_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.event_tab, text="🎯 Event Study")
        self._create_event_tab()
    
    def _create_daily_tab(self):
        """Create daily turnover tab."""
        # Split into left (table) and right (chart)
        paned = ttk.PanedWindow(self.daily_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Table
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(left_frame, text="Summary", padding=5)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.daily_summary = ttk.Label(summary_frame, text="Load a stock to see summary", style='Stats.TLabel')
        self.daily_summary.pack(fill=tk.X)
        
        # Table
        table_frame = ttk.Frame(left_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('date', 'close', 'volume', 'turnover', 'avg_20', 'rel_turn', 'day_pct')
        self.daily_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        headings = {
            'date': ('Date', 90),
            'close': ('Close', 80),
            'volume': ('Volume', 100),
            'turnover': ('Turnover (Cr)', 100),
            'avg_20': ('Avg 20D (Cr)', 100),
            'rel_turn': ('Rel Turn', 70),
            'day_pct': ('Day %', 70)
        }
        
        for col, (text, width) in headings.items():
            self.daily_tree.heading(col, text=text)
            self.daily_tree.column(col, width=width, anchor=tk.CENTER if col != 'date' else tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.daily_tree.yview)
        self.daily_tree.configure(yscrollcommand=scrollbar.set)
        
        self.daily_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right: Chart
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        self.daily_fig = Figure(figsize=(7, 6), dpi=100)
        self.daily_canvas = FigureCanvasTkAgg(self.daily_fig, right_frame)
        self.daily_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure tags
        self.daily_tree.tag_configure('high', background='#C8E6C9')
        self.daily_tree.tag_configure('low', background='#FFCDD2')
    
    def _create_weekly_tab(self):
        """Create weekly turnover tab."""
        paned = ttk.PanedWindow(self.weekly_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Table
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Summary
        summary_frame = ttk.LabelFrame(left_frame, text="Weekly Summary", padding=5)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.weekly_summary = ttk.Label(summary_frame, text="Load a stock to see summary", style='Stats.TLabel')
        self.weekly_summary.pack(fill=tk.X)
        
        # Table
        table_frame = ttk.Frame(left_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('week', 'close', 'volume', 'turnover', 'avg_4w', 'rel_turn', 'week_pct')
        self.weekly_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        headings = {
            'week': ('Week Ending', 100),
            'close': ('Close', 80),
            'volume': ('Volume', 110),
            'turnover': ('Turnover (Cr)', 100),
            'avg_4w': ('Avg 4W (Cr)', 100),
            'rel_turn': ('Rel Turn', 70),
            'week_pct': ('Week %', 70)
        }
        
        for col, (text, width) in headings.items():
            self.weekly_tree.heading(col, text=text)
            self.weekly_tree.column(col, width=width, anchor=tk.CENTER if col != 'week' else tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.weekly_tree.yview)
        self.weekly_tree.configure(yscrollcommand=scrollbar.set)
        
        self.weekly_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right: Chart
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        self.weekly_fig = Figure(figsize=(7, 6), dpi=100)
        self.weekly_canvas = FigureCanvasTkAgg(self.weekly_fig, right_frame)
        self.weekly_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.weekly_tree.tag_configure('high', background='#C8E6C9')
        self.weekly_tree.tag_configure('low', background='#FFCDD2')
    
    def _create_monthly_tab(self):
        """Create monthly turnover tab."""
        paned = ttk.PanedWindow(self.monthly_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Table
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Summary
        summary_frame = ttk.LabelFrame(left_frame, text="Monthly Summary", padding=5)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.monthly_summary = ttk.Label(summary_frame, text="Load a stock to see summary", style='Stats.TLabel')
        self.monthly_summary.pack(fill=tk.X)
        
        # Table
        table_frame = ttk.Frame(left_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('month', 'close', 'volume', 'turnover', 'avg_3m', 'rel_turn', 'month_pct')
        self.monthly_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        headings = {
            'month': ('Month', 90),
            'close': ('Close', 80),
            'volume': ('Volume', 120),
            'turnover': ('Turnover (Cr)', 110),
            'avg_3m': ('Avg 3M (Cr)', 100),
            'rel_turn': ('Rel Turn', 70),
            'month_pct': ('Month %', 70)
        }
        
        for col, (text, width) in headings.items():
            self.monthly_tree.heading(col, text=text)
            self.monthly_tree.column(col, width=width, anchor=tk.CENTER if col != 'month' else tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.monthly_tree.yview)
        self.monthly_tree.configure(yscrollcommand=scrollbar.set)
        
        self.monthly_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right: Chart
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        self.monthly_fig = Figure(figsize=(7, 6), dpi=100)
        self.monthly_canvas = FigureCanvasTkAgg(self.monthly_fig, right_frame)
        self.monthly_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.monthly_tree.tag_configure('high', background='#C8E6C9')
        self.monthly_tree.tag_configure('low', background='#FFCDD2')
    
    def _create_top_tab(self):
        """Create top turnover stocks tab."""
        # Control frame
        control_frame = ttk.Frame(self.top_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Top N:").pack(side=tk.LEFT, padx=5)
        self.top_n_var = tk.StringVar(value="30")
        top_n_combo = ttk.Combobox(control_frame, textvariable=self.top_n_var,
                                    values=["10", "20", "30", "50", "100"], width=6, state='readonly')
        top_n_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Date:").pack(side=tk.LEFT, padx=(20, 5))
        
        # Use DateEntry if tkcalendar is available, otherwise use Entry
        if HAS_TKCALENDAR:
            self.top_date_picker = DateEntry(
                control_frame, 
                width=12, 
                date_pattern='yyyy-mm-dd',
                maxdate=datetime.now().date(),
                showweeknumbers=False
            )
            self.top_date_picker.pack(side=tk.LEFT, padx=5)
        else:
            self.top_date_var = tk.StringVar(value="Latest")
            self.top_date_entry = ttk.Entry(control_frame, textvariable=self.top_date_var, width=12)
            self.top_date_entry.pack(side=tk.LEFT, padx=5)
            ttk.Label(control_frame, text="(YYYY-MM-DD or Latest)", 
                     font=('Segoe UI', 8)).pack(side=tk.LEFT)
        
        ttk.Button(control_frame, text="🔄 Refresh", command=self._load_top_turnover).pack(side=tk.LEFT, padx=20)
        
        # Table
        table_frame = ttk.Frame(self.top_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('rank', 'symbol', 'close', 'volume', 'turnover')
        self.top_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=25)
        
        headings = {
            'rank': ('#', 40),
            'symbol': ('Symbol', 150),
            'close': ('Close', 100),
            'volume': ('Volume', 130),
            'turnover': ('Turnover (Cr)', 120)
        }
        
        for col, (text, width) in headings.items():
            self.top_tree.heading(col, text=text)
            self.top_tree.column(col, width=width, anchor=tk.CENTER if col != 'symbol' else tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=scrollbar.set)
        
        self.top_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to load stock
        self.top_tree.bind('<Double-1>', self._on_top_double_click)
    
    def _create_unusual_tab(self):
        """Create unusual turnover tab."""
        # Control frame
        control_frame = ttk.Frame(self.unusual_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Look Back Days:").pack(side=tk.LEFT, padx=5)
        self.unusual_days_var = tk.StringVar(value="5")
        days_combo = ttk.Combobox(control_frame, textvariable=self.unusual_days_var,
                                   values=["3", "5", "7", "10", "14"], width=5, state='readonly')
        days_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Min Relative:").pack(side=tk.LEFT, padx=(20, 5))
        self.unusual_threshold_var = tk.StringVar(value="2.0")
        threshold_combo = ttk.Combobox(control_frame, textvariable=self.unusual_threshold_var,
                                        values=["1.5", "2.0", "2.5", "3.0", "4.0"], width=5, state='readonly')
        threshold_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔄 Scan", command=self._load_unusual_turnover).pack(side=tk.LEFT, padx=20)
        
        self.unusual_count_label = ttk.Label(control_frame, text="", style='Stats.TLabel')
        self.unusual_count_label.pack(side=tk.RIGHT, padx=10)
        
        # Table
        table_frame = ttk.Frame(self.unusual_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('symbol', 'date', 'close', 'turnover', 'avg_turnover', 'rel_turn', 'volume')
        self.unusual_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=25)
        
        headings = {
            'symbol': ('Symbol', 120),
            'date': ('Date', 100),
            'close': ('Close', 90),
            'turnover': ('Turnover (Cr)', 110),
            'avg_turnover': ('Avg 20D (Cr)', 100),
            'rel_turn': ('Relative', 80),
            'volume': ('Volume', 120)
        }
        
        for col, (text, width) in headings.items():
            self.unusual_tree.heading(col, text=text)
            self.unusual_tree.column(col, width=width, anchor=tk.CENTER if col != 'symbol' else tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.unusual_tree.yview)
        self.unusual_tree.configure(yscrollcommand=scrollbar.set)
        
        self.unusual_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Color code by relative turnover
        self.unusual_tree.tag_configure('extreme', background='#FFCDD2')  # >5x
        self.unusual_tree.tag_configure('very_high', background='#FFE0B2')  # 3-5x
        self.unusual_tree.tag_configure('high', background='#FFF9C4')  # 2-3x
        
        # Double-click to load stock
        self.unusual_tree.bind('<Double-1>', self._on_unusual_double_click)
    
    def _create_frequency_tab(self):
        """Create frequency analysis tab - tracks stocks appearing in top 100 turnover."""
        # Control frame
        control_frame = ttk.Frame(self.frequency_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Duration:").pack(side=tk.LEFT, padx=5)
        self.freq_duration_var = tk.StringVar(value="3 Months")
        duration_combo = ttk.Combobox(
            control_frame, 
            textvariable=self.freq_duration_var,
            values=["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"],
            width=12, 
            state='readonly'
        )
        duration_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Min Appearances:").pack(side=tk.LEFT, padx=(20, 5))
        self.freq_min_appearances_var = tk.StringVar(value="10")
        min_app_combo = ttk.Combobox(
            control_frame,
            textvariable=self.freq_min_appearances_var,
            values=["5", "10", "20", "30", "50"],
            width=6,
            state='readonly'
        )
        min_app_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔄 Analyze", command=self._load_frequency_analysis).pack(side=tk.LEFT, padx=20)
        
        self.freq_status_label = ttk.Label(control_frame, text="", style='Stats.TLabel')
        self.freq_status_label.pack(side=tk.RIGHT, padx=10)
        
        # Split into table and chart
        paned = ttk.PanedWindow(self.frequency_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Table
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        table_frame = ttk.Frame(left_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('rank', 'symbol', 'appearances', 'pct_days', 'start_price', 'end_price', 'return_pct', 'avg_turnover', 'rarity_score')
        self.freq_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=25)
        
        headings = {
            'rank': ('#', 35),
            'symbol': ('Symbol', 110),
            'appearances': ('Apps', 60),
            'pct_days': ('% Days', 60),
            'start_price': ('Start ₹', 80),
            'end_price': ('End ₹', 80),
            'return_pct': ('Return %', 75),
            'avg_turnover': ('Avg Turn', 80),
            'rarity_score': ('🎯 Score', 70)
        }
        
        for col, (text, width) in headings.items():
            self.freq_tree.heading(col, text=text, command=lambda c=col: self._sort_freq_tree(c))
            self.freq_tree.column(col, width=width, anchor=tk.CENTER if col != 'symbol' else tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.freq_tree.yview)
        self.freq_tree.configure(yscrollcommand=scrollbar.set)
        
        self.freq_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Color code by returns
        self.freq_tree.tag_configure('positive', background='#C8E6C9')  # Green for positive returns
        self.freq_tree.tag_configure('negative', background='#FFCDD2')  # Red for negative returns
        self.freq_tree.tag_configure('neutral', background='#FFF9C4')  # Yellow for small returns
        
        # Right: Chart
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        self.freq_fig = Figure(figsize=(7, 6), dpi=100)
        self.freq_canvas = FigureCanvasTkAgg(self.freq_fig, right_frame)
        self.freq_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Double-click to load stock
        self.freq_tree.bind('<Double-1>', self._on_freq_double_click)
        
        # Store data for sorting
        self.freq_data = None
        self.freq_sort_reverse = {}
    
    def _load_frequency_analysis(self):
        """Analyze stocks appearing frequently in top 100 turnover."""
        duration = self.freq_duration_var.get()
        min_appearances = int(self.freq_min_appearances_var.get())
        
        # Convert duration to days
        duration_map = {
            "1 Month": 30,
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
            "2 Years": 730
        }
        days = duration_map.get(duration, 90)
        
        self.freq_status_label.config(text="Analyzing... Please wait")
        self.status_var.set(f"Analyzing top 100 turnover frequency for {duration}...")
        
        def analyze():
            try:
                with self.engine.connect() as conn:
                    # Step 1: Get all trading dates in the period
                    dates_query = text("""
                        SELECT DISTINCT date 
                        FROM yfinance_daily_quotes 
                        WHERE timeframe = 'daily'
                        AND date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                        ORDER BY date
                    """)
                    dates_df = pd.read_sql(dates_query, conn, params={'days': days})
                    trading_dates = dates_df['date'].tolist()
                    total_days = len(trading_dates)
                    
                    if total_days == 0:
                        self.root.after(0, lambda: self.freq_status_label.config(text="No data found"))
                        return
                    
                    # Step 2: For each date, get top 100 turnover stocks
                    appearances = {}  # symbol -> count
                    turnover_sum = {}  # symbol -> total turnover
                    
                    for trade_date in trading_dates:
                        top100_query = text("""
                            SELECT symbol, (close * volume) / 10000000 as turnover_cr
                            FROM yfinance_daily_quotes
                            WHERE timeframe = 'daily'
                            AND date = :trade_date
                            AND volume > 0
                            ORDER BY turnover_cr DESC
                            LIMIT 100
                        """)
                        top100_df = pd.read_sql(top100_query, conn, params={'trade_date': trade_date})
                        
                        for _, row in top100_df.iterrows():
                            symbol = row['symbol']
                            appearances[symbol] = appearances.get(symbol, 0) + 1
                            turnover_sum[symbol] = turnover_sum.get(symbol, 0) + row['turnover_cr']
                    
                    # Step 3: Filter by minimum appearances
                    qualified_symbols = [s for s, count in appearances.items() if count >= min_appearances]
                    
                    if not qualified_symbols:
                        self.root.after(0, lambda: self.freq_status_label.config(
                            text=f"No stocks with {min_appearances}+ appearances"))
                        return
                    
                    # Step 4: Get price returns for qualified symbols
                    start_date = trading_dates[0]
                    end_date = trading_dates[-1]
                    
                    results = []
                    for symbol in qualified_symbols:
                        # Get start and end prices
                        price_query = text("""
                            SELECT 
                                MIN(CASE WHEN date = :start_date THEN close END) as start_price,
                                MAX(CASE WHEN date = :end_date THEN close END) as end_price
                            FROM yfinance_daily_quotes
                            WHERE symbol = :symbol
                            AND timeframe = 'daily'
                            AND date IN (:start_date, :end_date)
                        """)
                        price_df = pd.read_sql(price_query, conn, params={
                            'symbol': symbol, 
                            'start_date': start_date, 
                            'end_date': end_date
                        })
                        
                        if price_df.empty or price_df['start_price'].iloc[0] is None:
                            continue
                        
                        start_price = float(price_df['start_price'].iloc[0])
                        end_price = float(price_df['end_price'].iloc[0]) if price_df['end_price'].iloc[0] else start_price
                        
                        if start_price > 0:
                            return_pct = ((end_price - start_price) / start_price) * 100
                        else:
                            return_pct = 0
                        
                        count = appearances[symbol]
                        avg_turnover = turnover_sum[symbol] / count
                        pct_days = (count / total_days) * 100
                        
                        results.append({
                            'symbol': symbol,
                            'appearances': count,
                            'pct_days': pct_days,
                            'start_price': start_price,
                            'end_price': end_price,
                            'return_pct': return_pct,
                            'avg_turnover': avg_turnover
                        })
                    
                    # Sort by appearances descending
                    results.sort(key=lambda x: x['appearances'], reverse=True)
                    
                    result_df = pd.DataFrame(results)
                    
                    # Calculate Rarity Score: combines LOW frequency with HIGH returns
                    # Formula: (max_appearances - appearances) / max_appearances * return_pct
                    # Higher score = rare stock with good returns
                    if not result_df.empty:
                        max_app = result_df['appearances'].max()
                        # Rarity factor: 1.0 for rarest, 0.0 for most frequent
                        result_df['rarity_factor'] = (max_app - result_df['appearances']) / max_app
                        # Rarity Score: rarity_factor * return (positive returns boost, negative hurt)
                        # Add 1 to rarity factor so even frequent stocks with huge returns show up
                        result_df['rarity_score'] = (result_df['rarity_factor'] + 0.5) * result_df['return_pct']
                    else:
                        result_df['rarity_factor'] = 0
                        result_df['rarity_score'] = 0
                    
                    self.root.after(0, lambda: self._display_frequency_results(result_df, total_days, duration))
                    
            except Exception as e:
                self.root.after(0, lambda: self.freq_status_label.config(text=f"Error: {e}"))
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
        
        threading.Thread(target=analyze, daemon=True).start()
    
    def _display_frequency_results(self, df: pd.DataFrame, total_days: int, duration: str):
        """Display frequency analysis results."""
        # Store data for sorting
        self.freq_data = df.copy()
        
        # Clear table
        for item in self.freq_tree.get_children():
            self.freq_tree.delete(item)
        
        # Add rows (sorted by rarity_score for most actionable insights)
        df_sorted = df.sort_values('rarity_score', ascending=False)
        
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            rarity_score = row.get('rarity_score', 0)
            values = (
                i,
                row['symbol'],
                row['appearances'],
                f"{row['pct_days']:.1f}%",
                f"₹{row['start_price']:.2f}",
                f"₹{row['end_price']:.2f}",
                f"{row['return_pct']:+.2f}%",
                f"₹{row['avg_turnover']:.2f}",
                f"{rarity_score:+.1f}"
            )
            
            # Color code by rarity score (high score = green)
            if rarity_score >= 20:
                tag = 'high_score'
            elif rarity_score >= 5:
                tag = 'positive'
            elif rarity_score <= -5:
                tag = 'negative'
            else:
                tag = 'neutral'
            
            self.freq_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Configure high score tag
        self.freq_tree.tag_configure('high_score', background='#81C784')  # Bright green
        
        # Update status with insights
        avg_return = df['return_pct'].mean()
        positive_pct = (df['return_pct'] > 0).sum() / len(df) * 100
        
        # Calculate insight: rare vs frequent returns
        median_app = df['appearances'].median()
        rare_avg = df[df['appearances'] <= median_app]['return_pct'].mean()
        frequent_avg = df[df['appearances'] > median_app]['return_pct'].mean()
        
        insight_text = f"💡 Rare stocks avg: {rare_avg:+.1f}% vs Frequent: {frequent_avg:+.1f}%"
        
        self.freq_status_label.config(
            text=f"{len(df)} stocks | {insight_text}"
        )
        self.status_var.set(f"Analyzed {len(df)} stocks over {total_days} days ({duration}). Sort by 🎯 Score for best opportunities!")
        
        # Draw chart
        self._draw_frequency_chart(df, duration)
    
    def _draw_frequency_chart(self, df: pd.DataFrame, duration: str):
        """Draw frequency vs returns charts with rarity bucket analysis."""
        self.freq_fig.clear()
        
        # 2x2 grid for comprehensive analysis
        ax1 = self.freq_fig.add_subplot(221)
        ax2 = self.freq_fig.add_subplot(222)
        ax3 = self.freq_fig.add_subplot(223)
        ax4 = self.freq_fig.add_subplot(224)
        
        # 1. Scatter: Appearances vs Returns
        colors = ['#4CAF50' if r >= 0 else '#F44336' for r in df['return_pct']]
        ax1.scatter(df['appearances'], df['return_pct'], c=colors, alpha=0.6, s=50)
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1)
        ax1.set_xlabel('Appearances in Top 100')
        ax1.set_ylabel('Return %')
        ax1.set_title(f'Frequency vs Returns ({duration})')
        ax1.grid(True, alpha=0.3)
        
        # Add trend line and correlation
        if len(df) > 2:
            z = np.polyfit(df['appearances'], df['return_pct'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(df['appearances'].min(), df['appearances'].max(), 100)
            ax1.plot(x_line, p(x_line), 'b--', alpha=0.5)
            corr = df['appearances'].corr(df['return_pct'])
            ax1.set_title(f'Frequency vs Returns (r={corr:.2f})')
        
        # 2. RARITY BUCKET ANALYSIS - This is KEY for your question!
        max_app = df['appearances'].max()
        # Create buckets: Rare (bottom 25%), Moderate (25-50%), Frequent (50-75%), Very Frequent (top 25%)
        q1, q2, q3 = df['appearances'].quantile([0.25, 0.5, 0.75])
        
        def assign_bucket(x):
            if x <= q1: return 'Rare\n(few appearances)'
            elif x <= q2: return 'Moderate'
            elif x <= q3: return 'Frequent'
            else: return 'Very Frequent\n(many appearances)'
        
        df_copy = df.copy()
        df_copy['bucket'] = df_copy['appearances'].apply(assign_bucket)
        
        # Calculate stats per bucket
        bucket_stats = df_copy.groupby('bucket').agg({
            'return_pct': ['mean', 'median', 'std', 'count'],
            'appearances': 'mean'
        }).round(2)
        
        buckets = ['Rare\n(few appearances)', 'Moderate', 'Frequent', 'Very Frequent\n(many appearances)']
        bucket_returns = [bucket_stats.loc[b, ('return_pct', 'mean')] if b in bucket_stats.index else 0 for b in buckets]
        bucket_counts = [bucket_stats.loc[b, ('return_pct', 'count')] if b in bucket_stats.index else 0 for b in buckets]
        
        colors_bucket = ['#2E7D32', '#66BB6A', '#FFA726', '#EF5350']  # Dark green to red
        bars = ax2.bar(range(4), bucket_returns, color=colors_bucket, alpha=0.8, edgecolor='black')
        ax2.set_xticks(range(4))
        ax2.set_xticklabels(buckets, fontsize=8)
        ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1)
        ax2.set_ylabel('Avg Return %')
        ax2.set_title('📊 KEY INSIGHT: Returns by Rarity')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add count and return value on bars
        for i, (bar, ret, cnt) in enumerate(zip(bars, bucket_returns, bucket_counts)):
            height = bar.get_height()
            ax2.annotate(f'{ret:+.1f}%\n(n={int(cnt)})', 
                        xy=(bar.get_x() + bar.get_width()/2, height),
                        xytext=(0, 5 if height >= 0 else -20),
                        textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # 3. Top 15 RARE stocks with HIGHEST returns (what you're looking for!)
        rare_winners = df_copy[df_copy['bucket'].isin(['Rare\n(few appearances)', 'Moderate'])]\
                        .nlargest(15, 'return_pct')
        
        if not rare_winners.empty:
            colors_bar = ['#4CAF50' if r >= 0 else '#F44336' for r in rare_winners['return_pct']]
            y_pos = range(len(rare_winners))
            bars3 = ax3.barh(y_pos, rare_winners['return_pct'], color=colors_bar, alpha=0.7)
            ax3.set_yticks(y_pos)
            ax3.set_yticklabels([f"{s.replace('.NS', '')} ({a})" 
                                for s, a in zip(rare_winners['symbol'], rare_winners['appearances'])], 
                                fontsize=8)
            ax3.axvline(x=0, color='gray', linestyle='--', linewidth=1)
            ax3.set_xlabel('Return %')
            ax3.set_title('🎯 BEST: Rare Stocks with High Returns')
            ax3.grid(True, alpha=0.3, axis='x')
            ax3.invert_yaxis()
        
        # 4. Win Rate by bucket
        win_rates = []
        for bucket in buckets:
            bucket_df = df_copy[df_copy['bucket'] == bucket]
            if len(bucket_df) > 0:
                win_rate = (bucket_df['return_pct'] > 0).sum() / len(bucket_df) * 100
            else:
                win_rate = 0
            win_rates.append(win_rate)
        
        bars4 = ax4.bar(range(4), win_rates, color=colors_bucket, alpha=0.8, edgecolor='black')
        ax4.set_xticks(range(4))
        ax4.set_xticklabels(buckets, fontsize=8)
        ax4.axhline(y=50, color='gray', linestyle='--', linewidth=1, label='50%')
        ax4.set_ylabel('Win Rate %')
        ax4.set_ylim(0, 100)
        ax4.set_title('Win Rate by Frequency Bucket')
        ax4.grid(True, alpha=0.3, axis='y')
        
        for i, (bar, wr) in enumerate(zip(bars4, win_rates)):
            ax4.annotate(f'{wr:.0f}%', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')
        
        self.freq_fig.tight_layout()
        self.freq_canvas.draw()
    
    def _sort_freq_tree(self, col):
        """Sort frequency treeview by column."""
        if self.freq_data is None or self.freq_data.empty:
            return
        
        # Toggle sort direction
        reverse = self.freq_sort_reverse.get(col, False)
        self.freq_sort_reverse[col] = not reverse
        
        # Map column to dataframe column
        col_map = {
            'rank': 'rarity_score',  # Re-sort by score when clicking rank
            'symbol': 'symbol',
            'appearances': 'appearances',
            'pct_days': 'pct_days',
            'start_price': 'start_price',
            'end_price': 'end_price',
            'return_pct': 'return_pct',
            'avg_turnover': 'avg_turnover',
            'rarity_score': 'rarity_score'
        }
        
        sort_col = col_map.get(col, col)
        
        # Sort dataframe
        sorted_df = self.freq_data.sort_values(by=sort_col, ascending=not reverse)
        
        # Redisplay
        for item in self.freq_tree.get_children():
            self.freq_tree.delete(item)
        
        for i, (_, row) in enumerate(sorted_df.iterrows(), 1):
            rarity_score = row.get('rarity_score', 0)
            values = (
                i,
                row['symbol'],
                row['appearances'],
                f"{row['pct_days']:.1f}%",
                f"₹{row['start_price']:.2f}",
                f"₹{row['end_price']:.2f}",
                f"{row['return_pct']:+.2f}%",
                f"₹{row['avg_turnover']:.2f}",
                f"{rarity_score:+.1f}"
            )
            
            # Color code by rarity score
            if rarity_score >= 20:
                tag = 'high_score'
            elif rarity_score >= 5:
                tag = 'positive'
            elif rarity_score <= -5:
                tag = 'negative'
            else:
                tag = 'neutral'
            
            self.freq_tree.insert('', tk.END, values=values, tags=(tag,))
    
    def _on_freq_double_click(self, event):
        """Handle double-click on frequency table."""
        selection = self.freq_tree.selection()
        if not selection:
            return
        
        item = self.freq_tree.item(selection[0])
        values = item.get('values', [])
        if values and len(values) > 1:
            symbol = values[1]
            self.symbol_var.set(symbol)
            self._load_stock_data()
            self.notebook.select(self.daily_tab)

    def _create_event_tab(self):
        """Create event study tab - analyze price action after high turnover days."""
        # Control frame
        control_frame = ttk.Frame(self.event_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        self.event_symbol_var = tk.StringVar()
        self.event_symbol_combo = ttk.Combobox(control_frame, textvariable=self.event_symbol_var, width=15)
        self.event_symbol_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Lookback:").pack(side=tk.LEFT, padx=(20, 5))
        self.event_lookback_var = tk.StringVar(value="1 Year")
        lookback_combo = ttk.Combobox(
            control_frame,
            textvariable=self.event_lookback_var,
            values=["3 Months", "6 Months", "1 Year", "2 Years", "3 Years"],
            width=10,
            state='readonly'
        )
        lookback_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Min Rel Turnover:").pack(side=tk.LEFT, padx=(20, 5))
        self.event_threshold_var = tk.StringVar(value="2.0")
        threshold_combo = ttk.Combobox(
            control_frame,
            textvariable=self.event_threshold_var,
            values=["1.5", "2.0", "2.5", "3.0", "4.0", "5.0"],
            width=6,
            state='readonly'
        )
        threshold_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔍 Analyze", command=self._run_event_study).pack(side=tk.LEFT, padx=20)
        
        self.event_status_label = ttk.Label(control_frame, text="", style='Stats.TLabel')
        self.event_status_label.pack(side=tk.RIGHT, padx=10)
        
        # Split into stats and charts
        paned = ttk.PanedWindow(self.event_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Event list and stats
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Stats frame
        stats_frame = ttk.LabelFrame(left_frame, text="Forward Returns Summary", padding=10)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.event_stats_text = tk.Text(stats_frame, height=8, width=40, font=('Consolas', 10))
        self.event_stats_text.pack(fill=tk.X)
        self.event_stats_text.config(state=tk.DISABLED)
        
        # Events table
        table_frame = ttk.LabelFrame(left_frame, text="High Turnover Events", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('date', 'close', 'rel_turn', 'ret_1d', 'ret_5d', 'ret_10d', 'ret_20d')
        self.event_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        headings = {
            'date': ('Date', 90),
            'close': ('Close', 80),
            'rel_turn': ('Rel Turn', 70),
            'ret_1d': ('1D %', 60),
            'ret_5d': ('5D %', 60),
            'ret_10d': ('10D %', 60),
            'ret_20d': ('20D %', 60)
        }
        
        for col, (text, width) in headings.items():
            self.event_tree.heading(col, text=text)
            self.event_tree.column(col, width=width, anchor=tk.CENTER if col != 'date' else tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.event_tree.yview)
        self.event_tree.configure(yscrollcommand=scrollbar.set)
        
        self.event_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Color coding
        self.event_tree.tag_configure('positive', background='#C8E6C9')
        self.event_tree.tag_configure('negative', background='#FFCDD2')
        
        # Right: Charts
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        self.event_fig = Figure(figsize=(10, 8), dpi=100)
        self.event_canvas = FigureCanvasTkAgg(self.event_fig, right_frame)
        self.event_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar for navigation
        toolbar_frame = ttk.Frame(right_frame)
        toolbar_frame.pack(fill=tk.X)
        NavigationToolbar2Tk(self.event_canvas, toolbar_frame)
    
    def _run_event_study(self):
        """Run event study analysis for high turnover days."""
        symbol = self.event_symbol_var.get().strip()
        if not symbol:
            symbol = self.symbol_var.get().strip()
            self.event_symbol_var.set(symbol)
        
        if not symbol:
            messagebox.showwarning("Warning", "Please enter a symbol")
            return
        
        lookback = self.event_lookback_var.get()
        threshold = float(self.event_threshold_var.get())
        
        # Convert lookback to days
        lookback_map = {
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
            "2 Years": 730,
            "3 Years": 1095
        }
        days = lookback_map.get(lookback, 365)
        
        self.event_status_label.config(text="Analyzing...")
        self.status_var.set(f"Running event study for {symbol}...")
        
        def analyze():
            try:
                with self.engine.connect() as conn:
                    # Get all price data with turnover metrics
                    query = text("""
                        WITH turnover_data AS (
                            SELECT 
                                date,
                                close,
                                volume,
                                (close * volume) / 10000000 as turnover_cr,
                                AVG((close * volume) / 10000000) OVER (
                                    ORDER BY date 
                                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                                ) as avg_turnover_20d
                            FROM yfinance_daily_quotes
                            WHERE symbol = :symbol
                            AND timeframe = 'daily'
                            AND date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                        )
                        SELECT 
                            date,
                            close,
                            turnover_cr,
                            avg_turnover_20d,
                            CASE WHEN avg_turnover_20d > 0 
                                 THEN turnover_cr / avg_turnover_20d 
                                 ELSE NULL END as relative_turnover
                        FROM turnover_data
                        ORDER BY date
                    """)
                    
                    df = pd.read_sql(query, conn, params={'symbol': symbol, 'days': days + 50})
                    
                    if df.empty:
                        self.root.after(0, lambda: self.event_status_label.config(text="No data found"))
                        return
                    
                    # Calculate forward returns
                    df['close_1d'] = df['close'].shift(-1)
                    df['close_5d'] = df['close'].shift(-5)
                    df['close_10d'] = df['close'].shift(-10)
                    df['close_20d'] = df['close'].shift(-20)
                    
                    df['ret_1d'] = ((df['close_1d'] - df['close']) / df['close']) * 100
                    df['ret_5d'] = ((df['close_5d'] - df['close']) / df['close']) * 100
                    df['ret_10d'] = ((df['close_10d'] - df['close']) / df['close']) * 100
                    df['ret_20d'] = ((df['close_20d'] - df['close']) / df['close']) * 100
                    
                    # Filter high turnover events
                    events = df[df['relative_turnover'] >= threshold].copy()
                    events = events.dropna(subset=['ret_1d'])  # Remove events without forward data
                    
                    self.root.after(0, lambda: self._display_event_study(df, events, symbol, threshold))
                    
            except Exception as e:
                self.root.after(0, lambda: self.event_status_label.config(text=f"Error: {e}"))
        
        threading.Thread(target=analyze, daemon=True).start()
    
    def _display_event_study(self, full_df: pd.DataFrame, events: pd.DataFrame, symbol: str, threshold: float):
        """Display event study results."""
        # Clear table
        for item in self.event_tree.get_children():
            self.event_tree.delete(item)
        
        if events.empty:
            self.event_status_label.config(text=f"No events with rel turnover >= {threshold}x")
            return
        
        # Add events to table
        for _, row in events.iterrows():
            values = (
                str(row['date'].date()) if hasattr(row['date'], 'date') else str(row['date']),
                f"₹{row['close']:.2f}",
                f"{row['relative_turnover']:.2f}x",
                f"{row['ret_1d']:+.2f}%" if pd.notna(row['ret_1d']) else "N/A",
                f"{row['ret_5d']:+.2f}%" if pd.notna(row['ret_5d']) else "N/A",
                f"{row['ret_10d']:+.2f}%" if pd.notna(row['ret_10d']) else "N/A",
                f"{row['ret_20d']:+.2f}%" if pd.notna(row['ret_20d']) else "N/A"
            )
            
            # Color by 5-day return
            tag = ''
            if pd.notna(row['ret_5d']):
                tag = 'positive' if row['ret_5d'] > 0 else 'negative'
            
            self.event_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Calculate statistics
        stats = self._calculate_event_stats(events)
        self._update_event_stats(stats, len(events), threshold)
        
        # Update status
        self.event_status_label.config(text=f"{len(events)} high turnover events found")
        self.status_var.set(f"Event study complete: {len(events)} events for {symbol}")
        
        # Draw charts
        self._draw_event_charts(full_df, events, symbol, threshold)
    
    def _calculate_event_stats(self, events: pd.DataFrame) -> dict:
        """Calculate statistics for event study."""
        stats = {}
        for period in ['1d', '5d', '10d', '20d']:
            col = f'ret_{period}'
            valid = events[col].dropna()
            if len(valid) > 0:
                stats[period] = {
                    'mean': valid.mean(),
                    'median': valid.median(),
                    'std': valid.std(),
                    'win_rate': (valid > 0).sum() / len(valid) * 100,
                    'avg_win': valid[valid > 0].mean() if (valid > 0).any() else 0,
                    'avg_loss': valid[valid < 0].mean() if (valid < 0).any() else 0,
                    'count': len(valid)
                }
            else:
                stats[period] = None
        return stats
    
    def _update_event_stats(self, stats: dict, num_events: int, threshold: float):
        """Update the statistics text box."""
        self.event_stats_text.config(state=tk.NORMAL)
        self.event_stats_text.delete(1.0, tk.END)
        
        text = f"High Turnover Events (>= {threshold}x): {num_events}\n"
        text += "=" * 45 + "\n"
        text += f"{'Period':<8} {'Mean':>8} {'Median':>8} {'Win%':>8} {'AvgWin':>8} {'AvgLoss':>8}\n"
        text += "-" * 45 + "\n"
        
        for period in ['1d', '5d', '10d', '20d']:
            s = stats.get(period)
            if s:
                text += f"{period.upper():<8} {s['mean']:>+7.2f}% {s['median']:>+7.2f}% "
                text += f"{s['win_rate']:>7.1f}% {s['avg_win']:>+7.2f}% {s['avg_loss']:>+7.2f}%\n"
            else:
                text += f"{period.upper():<8} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>8}\n"
        
        self.event_stats_text.insert(1.0, text)
        self.event_stats_text.config(state=tk.DISABLED)
    
    def _draw_event_charts(self, full_df: pd.DataFrame, events: pd.DataFrame, symbol: str, threshold: float):
        """Draw event study charts."""
        self.event_fig.clear()
        
        # 4 subplots: Price with events, Forward returns distribution, Overlaid returns, Win rate by period
        ax1 = self.event_fig.add_subplot(221)
        ax2 = self.event_fig.add_subplot(222)
        ax3 = self.event_fig.add_subplot(223)
        ax4 = self.event_fig.add_subplot(224)
        
        # 1. Price chart with high turnover events marked
        ax1.plot(full_df['date'], full_df['close'], 'k-', linewidth=1, alpha=0.7, label='Price')
        
        # Mark events
        event_dates = events['date'].tolist()
        event_prices = events['close'].tolist()
        event_colors = ['green' if r > 0 else 'red' for r in events['ret_5d'].fillna(0)]
        ax1.scatter(event_dates, event_prices, c=event_colors, s=80, marker='^', 
                   zorder=5, edgecolors='black', linewidth=0.5, label=f'High Turnover (>{threshold}x)')
        
        ax1.set_title(f'{symbol} - Price with High Turnover Events')
        ax1.set_ylabel('Price (₹)')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 2. Forward returns box plot
        returns_data = []
        labels = []
        for period in ['1d', '5d', '10d', '20d']:
            col = f'ret_{period}'
            valid = events[col].dropna()
            if len(valid) > 0:
                returns_data.append(valid.values)
                labels.append(period.upper())
        
        if returns_data:
            bp = ax2.boxplot(returns_data, labels=labels, patch_artist=True)
            colors = ['#90CAF9', '#81C784', '#FFE082', '#EF9A9A']
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
            ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1)
            ax2.set_title('Forward Returns Distribution')
            ax2.set_ylabel('Return %')
            ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. Overlaid price paths (normalized to event day = 100)
        # Show price movement from -5 days to +20 days around each event
        if not events.empty:
            full_df_indexed = full_df.set_index('date')
            
            for _, event in events.head(30).iterrows():  # Limit to 30 events for clarity
                event_date = event['date']
                try:
                    event_idx = full_df_indexed.index.get_loc(event_date)
                    # Get -5 to +20 days
                    start_idx = max(0, event_idx - 5)
                    end_idx = min(len(full_df_indexed), event_idx + 21)
                    
                    window = full_df_indexed.iloc[start_idx:end_idx].copy()
                    if len(window) > 5:
                        # Normalize to event day = 100
                        event_price = event['close']
                        window['normalized'] = (window['close'] / event_price) * 100
                        
                        # Create x-axis as days relative to event
                        days_relative = list(range(-min(5, event_idx - start_idx), len(window) - min(5, event_idx - start_idx)))
                        
                        color = 'green' if event['ret_5d'] > 0 else 'red' if pd.notna(event['ret_5d']) else 'gray'
                        ax3.plot(days_relative[:len(window)], window['normalized'].values, 
                                color=color, alpha=0.3, linewidth=1)
                except:
                    continue
            
            ax3.axvline(x=0, color='blue', linestyle='--', linewidth=2, label='Event Day')
            ax3.axhline(y=100, color='gray', linestyle='-', linewidth=1)
            ax3.set_xlim(-5, 20)
            ax3.set_title(f'Price Paths Around Events (Normalized)')
            ax3.set_xlabel('Days Relative to Event')
            ax3.set_ylabel('Normalized Price (Event Day = 100)')
            ax3.legend(loc='upper left', fontsize=8)
            ax3.grid(True, alpha=0.3)
        
        # 4. Average forward returns bar chart
        periods = ['1D', '5D', '10D', '20D']
        avg_returns = []
        win_rates = []
        
        for period in ['1d', '5d', '10d', '20d']:
            col = f'ret_{period}'
            valid = events[col].dropna()
            if len(valid) > 0:
                avg_returns.append(valid.mean())
                win_rates.append((valid > 0).sum() / len(valid) * 100)
            else:
                avg_returns.append(0)
                win_rates.append(50)
        
        x = np.arange(len(periods))
        width = 0.35
        
        colors = ['#4CAF50' if r >= 0 else '#F44336' for r in avg_returns]
        bars1 = ax4.bar(x - width/2, avg_returns, width, label='Avg Return %', color=colors, alpha=0.7)
        
        ax4_twin = ax4.twinx()
        bars2 = ax4_twin.bar(x + width/2, win_rates, width, label='Win Rate %', color='#2196F3', alpha=0.5)
        
        ax4.set_xticks(x)
        ax4.set_xticklabels(periods)
        ax4.axhline(y=0, color='gray', linestyle='--', linewidth=1)
        ax4.set_ylabel('Average Return %')
        ax4_twin.set_ylabel('Win Rate %')
        ax4_twin.set_ylim(0, 100)
        ax4.set_title('Forward Returns & Win Rates')
        
        # Combined legend
        ax4.legend(loc='upper left', fontsize=8)
        ax4_twin.legend(loc='upper right', fontsize=8)
        ax4.grid(True, alpha=0.3, axis='y')
        
        self.event_fig.tight_layout()
        self.event_canvas.draw()

    def _load_symbols(self):
        """Load available symbols."""
        query = text("""
            SELECT DISTINCT symbol 
            FROM yfinance_daily_quotes 
            WHERE timeframe = 'daily'
            ORDER BY symbol
        """)
        
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)
            
            symbols = df['symbol'].tolist()
            self.symbol_combo['values'] = symbols
            self.event_symbol_combo['values'] = symbols  # Also update event tab combo
            self.status_var.set(f"Loaded {len(symbols)} symbols")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
    
    def _load_stock_data(self):
        """Load turnover data for selected stock."""
        symbol = self.symbol_var.get().strip()
        if not symbol:
            messagebox.showwarning("Warning", "Please enter a symbol")
            return
        
        # Add .NS if not present
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = symbol + '.NS'
            self.symbol_var.set(symbol)
        
        self.status_var.set(f"Loading {symbol}...")
        self.root.update()
        
        def load():
            try:
                self._load_daily_data(symbol)
                self._load_weekly_data(symbol)
                self._load_monthly_data(symbol)
                self.root.after(0, lambda: self.status_var.set(f"Loaded {symbol}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
        
        threading.Thread(target=load, daemon=True).start()
    
    def _load_daily_data(self, symbol: str):
        """Load daily turnover data."""
        query = text("""
            SELECT date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol AND timeframe = 'daily'
            ORDER BY date DESC
            LIMIT 252
        """)
        
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'symbol': symbol})
        
        if df.empty:
            self.root.after(0, lambda: messagebox.showwarning("Warning", f"No data found for {symbol}"))
            return
        
        df = df.sort_values('date').reset_index(drop=True)
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate turnover
        df['turnover'] = (df['close'] * df['volume']) / CRORE
        df['turnover_avg_20'] = df['turnover'].rolling(20).mean()
        df['turnover_avg_50'] = df['turnover'].rolling(50).mean()
        df['relative_turnover'] = df['turnover'] / df['turnover_avg_20']
        
        df['prev_close'] = df['close'].shift(1)
        df['day_pct'] = ((df['close'] - df['prev_close']) / df['prev_close']) * 100
        
        self.daily_df = df
        
        # Update UI
        self.root.after(0, lambda: self._display_daily_data(df, symbol))
    
    def _display_daily_data(self, df: pd.DataFrame, symbol: str):
        """Display daily data in table and chart."""
        # Clear table
        for item in self.daily_tree.get_children():
            self.daily_tree.delete(item)
        
        # Add rows (most recent first)
        for _, row in df.tail(60).iloc[::-1].iterrows():
            rel = f"{row['relative_turnover']:.2f}x" if pd.notna(row['relative_turnover']) else "N/A"
            avg = f"{row['turnover_avg_20']:.2f}" if pd.notna(row['turnover_avg_20']) else "N/A"
            day_pct = f"{row['day_pct']:+.2f}%" if pd.notna(row['day_pct']) else "N/A"
            
            values = (
                str(row['date'].date()),
                f"₹{row['close']:.2f}",
                f"{row['volume']:,.0f}",
                f"{row['turnover']:.2f}",
                avg,
                rel,
                day_pct
            )
            
            tag = ''
            if pd.notna(row['relative_turnover']):
                if row['relative_turnover'] >= 2:
                    tag = 'high'
                elif row['relative_turnover'] <= 0.5:
                    tag = 'low'
            
            self.daily_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Update summary
        latest = df.iloc[-1]
        avg_20 = latest['turnover_avg_20'] if pd.notna(latest['turnover_avg_20']) else 0
        avg_50 = latest['turnover_avg_50'] if pd.notna(latest['turnover_avg_50']) else 0
        rel = latest['relative_turnover'] if pd.notna(latest['relative_turnover']) else 0
        
        summary_text = (f"{symbol} | Latest: ₹{latest['turnover']:.2f} Cr | "
                       f"Avg 20D: ₹{avg_20:.2f} Cr | Avg 50D: ₹{avg_50:.2f} Cr | "
                       f"Relative: {rel:.2f}x")
        self.daily_summary.config(text=summary_text)
        
        # Update chart
        self._draw_daily_chart(df, symbol)
    
    def _draw_daily_chart(self, df: pd.DataFrame, symbol: str):
        """Draw daily turnover chart."""
        self.daily_fig.clear()
        
        # Use last 60 days
        plot_df = df.tail(60)
        
        ax1 = self.daily_fig.add_subplot(211)
        ax2 = self.daily_fig.add_subplot(212, sharex=ax1)
        
        # Turnover bars
        colors = ['#4CAF50' if r >= 1 else '#F44336' 
                  for r in plot_df['relative_turnover'].fillna(1)]
        ax1.bar(plot_df['date'], plot_df['turnover'], color=colors, alpha=0.7, width=0.8)
        ax1.plot(plot_df['date'], plot_df['turnover_avg_20'], 'b-', linewidth=1.5, label='20D Avg')
        ax1.plot(plot_df['date'], plot_df['turnover_avg_50'], 'orange', linewidth=1.5, label='50D Avg')
        ax1.set_ylabel('Turnover (Cr)')
        ax1.set_title(f'{symbol} - Daily Turnover')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # Price
        ax2.plot(plot_df['date'], plot_df['close'], 'k-', linewidth=1.5)
        ax2.fill_between(plot_df['date'], plot_df['close'], alpha=0.3)
        ax2.set_ylabel('Price (₹)')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        
        self.daily_fig.tight_layout()
        self.daily_canvas.draw()
    
    def _load_weekly_data(self, symbol: str):
        """Load weekly turnover data."""
        # Get daily data and resample
        if self.daily_df is None or self.daily_df.empty:
            return
        
        df = self.daily_df.copy()
        df.set_index('date', inplace=True)
        
        weekly = df.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'turnover': 'sum'
        }).dropna()
        
        weekly = weekly.reset_index()
        weekly['turnover_avg_4'] = weekly['turnover'].rolling(4).mean()
        weekly['turnover_avg_12'] = weekly['turnover'].rolling(12).mean()
        weekly['relative_turnover'] = weekly['turnover'] / weekly['turnover_avg_4']
        
        weekly['prev_close'] = weekly['close'].shift(1)
        weekly['week_pct'] = ((weekly['close'] - weekly['prev_close']) / weekly['prev_close']) * 100
        
        self.weekly_df = weekly
        
        self.root.after(0, lambda: self._display_weekly_data(weekly, symbol))
    
    def _display_weekly_data(self, df: pd.DataFrame, symbol: str):
        """Display weekly data."""
        # Clear table
        for item in self.weekly_tree.get_children():
            self.weekly_tree.delete(item)
        
        # Add rows
        for _, row in df.tail(52).iloc[::-1].iterrows():
            rel = f"{row['relative_turnover']:.2f}x" if pd.notna(row['relative_turnover']) else "N/A"
            avg = f"{row['turnover_avg_4']:.2f}" if pd.notna(row['turnover_avg_4']) else "N/A"
            week_pct = f"{row['week_pct']:+.2f}%" if pd.notna(row['week_pct']) else "N/A"
            
            values = (
                str(row['date'].date()),
                f"₹{row['close']:.2f}",
                f"{row['volume']:,.0f}",
                f"{row['turnover']:.2f}",
                avg,
                rel,
                week_pct
            )
            
            tag = ''
            if pd.notna(row['relative_turnover']):
                if row['relative_turnover'] >= 1.5:
                    tag = 'high'
                elif row['relative_turnover'] <= 0.5:
                    tag = 'low'
            
            self.weekly_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Update summary
        if not df.empty:
            latest = df.iloc[-1]
            avg_4 = latest['turnover_avg_4'] if pd.notna(latest['turnover_avg_4']) else 0
            total_ytd = df['turnover'].sum()
            
            summary_text = (f"{symbol} | This Week: ₹{latest['turnover']:.2f} Cr | "
                           f"Avg 4W: ₹{avg_4:.2f} Cr | YTD Total: ₹{total_ytd:.2f} Cr")
            self.weekly_summary.config(text=summary_text)
        
        # Update chart
        self._draw_weekly_chart(df, symbol)
    
    def _draw_weekly_chart(self, df: pd.DataFrame, symbol: str):
        """Draw weekly turnover chart."""
        self.weekly_fig.clear()
        
        plot_df = df.tail(26)  # Last 6 months
        
        ax1 = self.weekly_fig.add_subplot(211)
        ax2 = self.weekly_fig.add_subplot(212, sharex=ax1)
        
        colors = ['#4CAF50' if r >= 1 else '#F44336' 
                  for r in plot_df['relative_turnover'].fillna(1)]
        ax1.bar(plot_df['date'], plot_df['turnover'], color=colors, alpha=0.7, width=5)
        ax1.plot(plot_df['date'], plot_df['turnover_avg_4'], 'b-', linewidth=1.5, label='4W Avg')
        ax1.plot(plot_df['date'], plot_df['turnover_avg_12'], 'orange', linewidth=1.5, label='12W Avg')
        ax1.set_ylabel('Turnover (Cr)')
        ax1.set_title(f'{symbol} - Weekly Turnover')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(plot_df['date'], plot_df['close'], 'k-', linewidth=1.5)
        ax2.fill_between(plot_df['date'], plot_df['close'], alpha=0.3)
        ax2.set_ylabel('Price (₹)')
        ax2.set_xlabel('Week')
        ax2.grid(True, alpha=0.3)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
        
        self.weekly_fig.tight_layout()
        self.weekly_canvas.draw()
    
    def _load_monthly_data(self, symbol: str):
        """Load monthly turnover data."""
        if self.daily_df is None or self.daily_df.empty:
            return
        
        df = self.daily_df.copy()
        df.set_index('date', inplace=True)
        
        monthly = df.resample('ME').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'turnover': 'sum'
        }).dropna()
        
        monthly = monthly.reset_index()
        monthly['turnover_avg_3'] = monthly['turnover'].rolling(3).mean()
        monthly['turnover_avg_6'] = monthly['turnover'].rolling(6).mean()
        monthly['relative_turnover'] = monthly['turnover'] / monthly['turnover_avg_3']
        
        monthly['prev_close'] = monthly['close'].shift(1)
        monthly['month_pct'] = ((monthly['close'] - monthly['prev_close']) / monthly['prev_close']) * 100
        
        self.monthly_df = monthly
        
        self.root.after(0, lambda: self._display_monthly_data(monthly, symbol))
    
    def _display_monthly_data(self, df: pd.DataFrame, symbol: str):
        """Display monthly data."""
        # Clear table
        for item in self.monthly_tree.get_children():
            self.monthly_tree.delete(item)
        
        # Add rows
        for _, row in df.tail(24).iloc[::-1].iterrows():
            rel = f"{row['relative_turnover']:.2f}x" if pd.notna(row['relative_turnover']) else "N/A"
            avg = f"{row['turnover_avg_3']:.2f}" if pd.notna(row['turnover_avg_3']) else "N/A"
            month_pct = f"{row['month_pct']:+.2f}%" if pd.notna(row['month_pct']) else "N/A"
            
            values = (
                row['date'].strftime('%Y-%m'),
                f"₹{row['close']:.2f}",
                f"{row['volume']:,.0f}",
                f"{row['turnover']:.2f}",
                avg,
                rel,
                month_pct
            )
            
            tag = ''
            if pd.notna(row['relative_turnover']):
                if row['relative_turnover'] >= 1.5:
                    tag = 'high'
                elif row['relative_turnover'] <= 0.5:
                    tag = 'low'
            
            self.monthly_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Update summary
        if not df.empty:
            latest = df.iloc[-1]
            total_ttm = df.tail(12)['turnover'].sum()
            avg_monthly = total_ttm / 12
            
            summary_text = (f"{symbol} | This Month: ₹{latest['turnover']:.2f} Cr | "
                           f"TTM Total: ₹{total_ttm:.2f} Cr | Avg Monthly: ₹{avg_monthly:.2f} Cr")
            self.monthly_summary.config(text=summary_text)
        
        # Update chart
        self._draw_monthly_chart(df, symbol)
    
    def _draw_monthly_chart(self, df: pd.DataFrame, symbol: str):
        """Draw monthly turnover chart."""
        self.monthly_fig.clear()
        
        plot_df = df.tail(12)
        
        ax1 = self.monthly_fig.add_subplot(211)
        ax2 = self.monthly_fig.add_subplot(212, sharex=ax1)
        
        colors = ['#4CAF50' if r >= 1 else '#F44336' 
                  for r in plot_df['relative_turnover'].fillna(1)]
        ax1.bar(plot_df['date'], plot_df['turnover'], color=colors, alpha=0.7, width=20)
        ax1.plot(plot_df['date'], plot_df['turnover_avg_3'], 'b-', linewidth=1.5, label='3M Avg')
        ax1.plot(plot_df['date'], plot_df['turnover_avg_6'], 'orange', linewidth=1.5, label='6M Avg')
        ax1.set_ylabel('Turnover (Cr)')
        ax1.set_title(f'{symbol} - Monthly Turnover')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(plot_df['date'], plot_df['close'], 'k-', linewidth=1.5, marker='o')
        ax2.fill_between(plot_df['date'], plot_df['close'], alpha=0.3)
        ax2.set_ylabel('Price (₹)')
        ax2.set_xlabel('Month')
        ax2.grid(True, alpha=0.3)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
        
        self.monthly_fig.tight_layout()
        self.monthly_canvas.draw()
    
    def _show_top_turnover(self):
        """Switch to top turnover tab and load data."""
        self.notebook.select(self.top_tab)
        self._load_top_turnover()
    
    def _load_top_turnover(self):
        """Load top turnover stocks."""
        top_n = int(self.top_n_var.get())
        
        # Get date from DateEntry or fallback Entry
        if HAS_TKCALENDAR:
            selected_date = self.top_date_picker.get_date()
            date_str = selected_date.strftime('%Y-%m-%d')
            date_clause = f"'{date_str}'"
        else:
            date_str = self.top_date_var.get().strip()
            # Handle empty or "Latest" - use max date
            if not date_str or date_str.lower() == 'latest':
                date_clause = "(SELECT MAX(date) FROM yfinance_daily_quotes WHERE timeframe = 'daily')"
            else:
                date_clause = f"'{date_str}'"
        
        query = text(f"""
            SELECT 
                symbol,
                date,
                close,
                volume,
                (close * volume) / 10000000 as turnover_cr
            FROM yfinance_daily_quotes
            WHERE timeframe = 'daily'
            AND date = {date_clause}
            AND volume > 0
            ORDER BY turnover_cr DESC
            LIMIT :top_n
        """)
        
        def load():
            try:
                with self.engine.connect() as conn:
                    df = pd.read_sql(query, conn, params={'top_n': top_n})
                self.root.after(0, lambda: self._display_top_turnover(df))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
        
        threading.Thread(target=load, daemon=True).start()
    
    def _display_top_turnover(self, df: pd.DataFrame):
        """Display top turnover stocks."""
        for item in self.top_tree.get_children():
            self.top_tree.delete(item)
        
        for i, (_, row) in enumerate(df.iterrows(), 1):
            values = (
                i,
                row['symbol'],
                f"₹{row['close']:.2f}",
                f"{row['volume']:,.0f}",
                f"₹{row['turnover_cr']:.2f}"
            )
            self.top_tree.insert('', tk.END, values=values)
        
        if not df.empty:
            self.status_var.set(f"Top {len(df)} stocks by turnover on {df['date'].iloc[0]}")
    
    def _show_unusual_turnover(self):
        """Switch to unusual turnover tab and load data."""
        self.notebook.select(self.unusual_tab)
        self._load_unusual_turnover()
    
    def _load_unusual_turnover(self):
        """Load unusual turnover stocks."""
        days = int(self.unusual_days_var.get())
        threshold = float(self.unusual_threshold_var.get())
        
        query = text("""
            WITH daily_data AS (
                SELECT 
                    symbol, date, close, volume,
                    (close * volume) / 10000000 as turnover_cr
                FROM yfinance_daily_quotes
                WHERE timeframe = 'daily'
                AND date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                AND volume > 0
            ),
            turnover_stats AS (
                SELECT 
                    symbol, date, close, volume, turnover_cr,
                    AVG(turnover_cr) OVER (
                        PARTITION BY symbol 
                        ORDER BY date 
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) as avg_turnover_20d
                FROM daily_data
            )
            SELECT 
                symbol, date, close, volume, turnover_cr, avg_turnover_20d,
                CASE WHEN avg_turnover_20d > 0 
                     THEN turnover_cr / avg_turnover_20d 
                     ELSE 0 END as relative_turnover
            FROM turnover_stats
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            AND avg_turnover_20d > 0
            AND turnover_cr / avg_turnover_20d >= :threshold
            ORDER BY relative_turnover DESC
        """)
        
        def load():
            try:
                with self.engine.connect() as conn:
                    df = pd.read_sql(query, conn, params={'days': days, 'threshold': threshold})
                self.root.after(0, lambda: self._display_unusual_turnover(df))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
        
        threading.Thread(target=load, daemon=True).start()
    
    def _display_unusual_turnover(self, df: pd.DataFrame):
        """Display unusual turnover stocks."""
        for item in self.unusual_tree.get_children():
            self.unusual_tree.delete(item)
        
        for _, row in df.head(100).iterrows():
            values = (
                row['symbol'],
                str(row['date'])[:10],
                f"₹{row['close']:.2f}",
                f"{row['turnover_cr']:.2f}",
                f"{row['avg_turnover_20d']:.2f}",
                f"{row['relative_turnover']:.2f}x",
                f"{row['volume']:,.0f}"
            )
            
            rel = row['relative_turnover']
            if rel >= 5:
                tag = 'extreme'
            elif rel >= 3:
                tag = 'very_high'
            else:
                tag = 'high'
            
            self.unusual_tree.insert('', tk.END, values=values, tags=(tag,))
        
        self.unusual_count_label.config(text=f"Found {len(df)} unusual turnover events")
        self.status_var.set(f"Found {len(df)} stocks with unusual turnover")
    
    def _on_top_double_click(self, event):
        """Handle double-click on top turnover table."""
        selection = self.top_tree.selection()
        if not selection:
            return
        
        item = self.top_tree.item(selection[0])
        values = item.get('values', [])
        if values and len(values) > 1:
            symbol = values[1]
            self.symbol_var.set(symbol)
            self._load_stock_data()
            self.notebook.select(self.daily_tab)
    
    def _on_unusual_double_click(self, event):
        """Handle double-click on unusual turnover table."""
        selection = self.unusual_tree.selection()
        if not selection:
            return
        
        item = self.unusual_tree.item(selection[0])
        values = item.get('values', [])
        if values:
            symbol = values[0]
            self.symbol_var.set(symbol)
            self._load_stock_data()
            self.notebook.select(self.daily_tab)


def main():
    """Main entry point."""
    root = tk.Tk()
    app = TurnoverAnalysisGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
