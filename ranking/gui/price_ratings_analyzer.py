#!/usr/bin/env python3
"""
Price & Ratings Correlation Analyzer

Visualize stock price alongside all rating components to analyze:
1. How price and ratings correlate
2. Whether ratings are leading indicators
3. Entry/exit signals for swing trades and investments

Key insights this tool provides:
- Overlay price with RS Rating, Momentum, Trend Template, Technical, Composite
- Calculate lead/lag correlations (do ratings predict price moves?)
- Identify divergences (ratings improving while price flat = potential breakout)
- Mark optimal entry points based on rating thresholds
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import threading

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from sqlalchemy import text

# Try to import tkcalendar for date picker
try:
    from tkcalendar import DateEntry
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available")

from ranking.db.schema import get_ranking_engine
from ranking.services.index_rating_service import IndexRatingService, get_letter_rating, INDEX_NAMES


class PriceRatingsAnalyzer:
    """Analyze price and ratings correlation for trading insights."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📈 Price & Ratings Correlation Analyzer")
        self.root.geometry("1400x900")
        self.root.state('zoomed')  # Maximize window
        
        self.engine = get_ranking_engine()
        self.current_data = None
        self.symbols_list = []
        
        self._load_symbols()
        self._create_ui()
    
    def _load_symbols(self):
        """Load list of symbols that have rankings data."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT symbol 
                    FROM stock_rankings_history 
                    ORDER BY symbol
                """)).fetchall()
                self.symbols_list = [r[0] for r in result]
        except Exception as e:
            print(f"Error loading symbols: {e}")
            self.symbols_list = []
    
    def _create_ui(self):
        """Create the GUI layout."""
        # Main container
        main = ttk.Frame(self.root, padding=5)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Top controls
        controls = ttk.Frame(main)
        controls.pack(fill=tk.X, pady=(0, 5))
        
        # Symbol input - Combobox with autocomplete
        ttk.Label(controls, text="Symbol:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.symbol_var = tk.StringVar(value="RELIANCE.NS")
        self.symbol_combo = ttk.Combobox(controls, textvariable=self.symbol_var, 
                                          values=self.symbols_list, width=18, font=("Segoe UI", 10))
        self.symbol_combo.pack(side=tk.LEFT, padx=5)
        self.symbol_combo.bind('<Return>', lambda e: self._analyze())
        self.symbol_combo.bind('<<ComboboxSelected>>', lambda e: self._analyze())
        self.symbol_combo.bind('<KeyRelease>', self._filter_symbols)
        
        # Period
        ttk.Label(controls, text="Period:").pack(side=tk.LEFT, padx=(15, 5))
        self.period_var = tk.StringVar(value="1Y")
        period_combo = ttk.Combobox(controls, textvariable=self.period_var, 
                                     values=["3M", "6M", "1Y", "2Y", "3Y", "5Y", "All"], width=6)
        period_combo.pack(side=tk.LEFT)
        
        # Analyze button
        ttk.Button(controls, text="📊 Analyze", command=self._analyze).pack(side=tk.LEFT, padx=15)
        
        # Quick symbols
        ttk.Label(controls, text="Quick:").pack(side=tk.LEFT, padx=(20, 5))
        for sym in ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]:
            btn = ttk.Button(controls, text=sym.replace(".NS", ""), width=10,
                            command=lambda s=sym: self._quick_analyze(s))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Price + Ratings Chart
        self._create_chart_tab(notebook)
        
        # Tab 2: Correlation Analysis
        self._create_correlation_tab(notebook)
        
        # Tab 3: Trading Signals (single stock)
        self._create_signals_tab(notebook)
        
        # Tab 4: Daily Signals Scanner (all stocks)
        self._create_daily_signals_tab(notebook)
        
        # Tab 5: Sector Rotation
        self._create_sector_rotation_tab(notebook)
        
        # Tab 6: Insights & Strategy
        self._create_insights_tab(notebook)
    
    def _create_chart_tab(self, notebook):
        """Create price + ratings chart tab."""
        tab = ttk.Frame(notebook, padding=5)
        notebook.add(tab, text="📈 Price & Ratings")
        
        # Controls frame for checkboxes
        controls_frame = ttk.LabelFrame(tab, text="Display Options", padding=5)
        controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Checkbox variables
        self.show_nifty = tk.BooleanVar(value=True)
        self.nifty_mode = tk.StringVar(value="overlay")  # "overlay" or "separate"
        self.show_rs = tk.BooleanVar(value=True)
        self.show_momentum = tk.BooleanVar(value=True)
        self.show_trend = tk.BooleanVar(value=True)
        self.show_technical = tk.BooleanVar(value=True)
        self.show_composite = tk.BooleanVar(value=True)
        
        # Nifty controls frame
        nifty_frame = ttk.Frame(controls_frame)
        nifty_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Checkbutton(nifty_frame, text="📊 Nifty 50", variable=self.show_nifty,
                        command=self._plot_price_ratings).pack(side=tk.LEFT)
        ttk.Radiobutton(nifty_frame, text="Overlay", variable=self.nifty_mode, value="overlay",
                        command=self._plot_price_ratings).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Radiobutton(nifty_frame, text="Separate", variable=self.nifty_mode, value="separate",
                        command=self._plot_price_ratings).pack(side=tk.LEFT)
        
        ttk.Separator(controls_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Rating checkboxes
        ttk.Checkbutton(controls_frame, text="📈 RS Rating", variable=self.show_rs,
                        command=self._plot_price_ratings).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(controls_frame, text="🚀 Momentum", variable=self.show_momentum,
                        command=self._plot_price_ratings).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(controls_frame, text="📐 Trend Template", variable=self.show_trend,
                        command=self._plot_price_ratings).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(controls_frame, text="🔧 Technical", variable=self.show_technical,
                        command=self._plot_price_ratings).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(controls_frame, text="⭐ Composite", variable=self.show_composite,
                        command=self._plot_price_ratings).pack(side=tk.LEFT, padx=5)
        
        # Select/Deselect all buttons
        ttk.Button(controls_frame, text="Select All", 
                   command=self._select_all_charts).pack(side=tk.LEFT, padx=20)
        ttk.Button(controls_frame, text="Deselect All", 
                   command=self._deselect_all_charts).pack(side=tk.LEFT, padx=5)
        
        if HAS_MATPLOTLIB:
            self.chart_figure = Figure(figsize=(14, 10), dpi=100)
            self.chart_canvas = FigureCanvasTkAgg(self.chart_figure, tab)
            self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            toolbar_frame = ttk.Frame(tab)
            toolbar_frame.pack(fill=tk.X)
            NavigationToolbar2Tk(self.chart_canvas, toolbar_frame)
        else:
            ttk.Label(tab, text="matplotlib not available").pack()
    
    def _select_all_charts(self):
        """Select all chart components."""
        self.show_nifty.set(True)
        self.show_rs.set(True)
        self.show_momentum.set(True)
        self.show_trend.set(True)
        self.show_technical.set(True)
        self.show_composite.set(True)
        self._plot_price_ratings()
    
    def _deselect_all_charts(self):
        """Deselect all chart components except price."""
        self.show_nifty.set(False)
        self.show_rs.set(False)
        self.show_momentum.set(False)
        self.show_trend.set(False)
        self.show_technical.set(False)
        self.show_composite.set(False)
        self._plot_price_ratings()
    
    def _create_correlation_tab(self, notebook):
        """Create correlation analysis tab."""
        tab = ttk.Frame(notebook, padding=5)
        notebook.add(tab, text="🔗 Correlation Analysis")
        
        # Split into left (chart) and right (text)
        paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left: correlation charts
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        if HAS_MATPLOTLIB:
            self.corr_figure = Figure(figsize=(8, 8), dpi=100)
            self.corr_canvas = FigureCanvasTkAgg(self.corr_figure, left_frame)
            self.corr_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Right: correlation text
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="📊 Lead/Lag Correlation Analysis", 
                  font=("Segoe UI", 11, "bold")).pack(pady=5)
        
        self.corr_text = tk.Text(right_frame, font=("Consolas", 10), wrap=tk.WORD)
        self.corr_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_signals_tab(self, notebook):
        """Create trading signals tab."""
        tab = ttk.Frame(notebook, padding=5)
        notebook.add(tab, text="🎯 Trading Signals")
        
        # Controls for signal parameters
        controls = ttk.LabelFrame(tab, text="Signal Parameters", padding=10)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        # RS threshold
        ttk.Label(controls, text="RS Rating ≥").pack(side=tk.LEFT)
        self.rs_threshold = tk.StringVar(value="70")
        ttk.Entry(controls, textvariable=self.rs_threshold, width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        # Trend threshold
        ttk.Label(controls, text="Trend Template ≥").pack(side=tk.LEFT)
        self.trend_threshold = tk.StringVar(value="6")
        ttk.Entry(controls, textvariable=self.trend_threshold, width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        # Composite threshold
        ttk.Label(controls, text="Composite ≥").pack(side=tk.LEFT)
        self.composite_threshold = tk.StringVar(value="70")
        ttk.Entry(controls, textvariable=self.composite_threshold, width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Button(controls, text="🔍 Find Signals", command=self._find_signals).pack(side=tk.LEFT, padx=15)
        
        # Signals display
        columns = ("Date", "Signal", "Price", "RS", "Mom", "Trend", "Tech", "Comp", "Future 20D%")
        self.signals_tree = ttk.Treeview(tab, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.signals_tree.heading(col, text=col)
            width = 90 if col not in ["Date", "Signal"] else 100
            self.signals_tree.column(col, width=width, anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.signals_tree.yview)
        self.signals_tree.configure(yscrollcommand=scrollbar.set)
        
        self.signals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tag colors
        self.signals_tree.tag_configure('buy', background='#d4edda')
        self.signals_tree.tag_configure('sell', background='#f8d7da')
    
    def _create_daily_signals_tab(self, notebook):
        """Create daily signals scanner tab - shows all stocks with signals on a date."""
        tab = ttk.Frame(notebook, padding=5)
        notebook.add(tab, text="📅 Daily Signals")
        
        # Controls
        controls = ttk.LabelFrame(tab, text="Signal Scanner", padding=10)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        # Date picker
        ttk.Label(controls, text="Date:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        if HAS_CALENDAR:
            self.scan_date_picker = DateEntry(controls, width=12, background='darkblue',
                                               foreground='white', borderwidth=2,
                                               date_pattern='yyyy-mm-dd')
            self.scan_date_picker.pack(side=tk.LEFT, padx=5)
        else:
            self.scan_date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
            ttk.Entry(controls, textvariable=self.scan_date_var, width=12).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # View mode: Signals vs Top Stocks
        ttk.Label(controls, text="View:").pack(side=tk.LEFT)
        self.view_mode_var = tk.StringVar(value="signals")
        ttk.Radiobutton(controls, text="📊 Signals", variable=self.view_mode_var, 
                        value="signals").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(controls, text="🏆 Top Stocks", variable=self.view_mode_var, 
                        value="top").pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Signal type filter (for signals mode)
        ttk.Label(controls, text="Filter:").pack(side=tk.LEFT)
        self.signal_filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(controls, text="All", variable=self.signal_filter_var, 
                        value="all").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(controls, text="🟢 Buy", variable=self.signal_filter_var, 
                        value="buy").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(controls, text="🔴 Sell", variable=self.signal_filter_var, 
                        value="sell").pack(side=tk.LEFT, padx=3)
        
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Top N for top stocks mode
        ttk.Label(controls, text="Top:").pack(side=tk.LEFT)
        self.top_n_var = tk.StringVar(value="50")
        top_combo = ttk.Combobox(controls, textvariable=self.top_n_var, 
                                  values=["10", "20", "50", "100", "All"], width=5)
        top_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls, text="🔍 Scan", command=self._scan_daily_signals).pack(side=tk.LEFT, padx=15)
        
        # Results summary
        self.scan_summary_var = tk.StringVar(value="Click 'Scan' to find signals")
        ttk.Label(controls, textvariable=self.scan_summary_var, 
                  font=("Segoe UI", 10, "italic")).pack(side=tk.RIGHT, padx=10)
        
        # Second row for thresholds
        controls2 = ttk.Frame(tab)
        controls2.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(controls2, text="Thresholds:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls2, text="RS≥").pack(side=tk.LEFT)
        self.scan_rs_var = tk.StringVar(value="70")
        ttk.Entry(controls2, textvariable=self.scan_rs_var, width=4).pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(controls2, text="Trend≥").pack(side=tk.LEFT)
        self.scan_trend_var = tk.StringVar(value="6")
        ttk.Entry(controls2, textvariable=self.scan_trend_var, width=4).pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(controls2, text="Composite≥").pack(side=tk.LEFT)
        self.scan_comp_var = tk.StringVar(value="70")
        ttk.Entry(controls2, textvariable=self.scan_comp_var, width=4).pack(side=tk.LEFT, padx=(2, 10))
        
        # Results treeview
        columns = ("Rank", "Symbol", "Signal", "Price", "RS", "Momentum", "Trend", "Technical", 
                   "Composite", "Percentile", "Rating")
        self.daily_signals_tree = ttk.Treeview(tab, columns=columns, show="headings", height=25)
        
        col_widths = {"Rank": 50, "Symbol": 110, "Signal": 70, "Price": 80, "RS": 50, 
                      "Momentum": 70, "Trend": 50, "Technical": 70, "Composite": 70, 
                      "Percentile": 70, "Rating": 80}
        
        for col in columns:
            self.daily_signals_tree.heading(col, text=col, 
                                            command=lambda c=col: self._sort_daily_signals(c))
            self.daily_signals_tree.column(col, width=col_widths.get(col, 70), anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.daily_signals_tree.yview)
        self.daily_signals_tree.configure(yscrollcommand=scrollbar.set)
        
        self.daily_signals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tag colors
        self.daily_signals_tree.tag_configure('buy', background='#d4edda')
        self.daily_signals_tree.tag_configure('sell', background='#f8d7da')
        self.daily_signals_tree.tag_configure('top10', background='#fff3cd')
        self.daily_signals_tree.tag_configure('excellent', background='#d1ecf1')
        
        # Double-click to analyze
        self.daily_signals_tree.bind('<Double-1>', self._on_signal_double_click)
        
        # Store sort state
        self.daily_signals_sort_col = None
        self.daily_signals_sort_reverse = False
    
    def _get_scan_date(self):
        """Get the selected scan date."""
        if HAS_CALENDAR:
            return self.scan_date_picker.get_date().strftime("%Y-%m-%d")
        else:
            return self.scan_date_var.get()
    
    def _get_stock_rating(self, composite_score):
        """Convert composite score to letter rating."""
        if composite_score >= 90:
            return "A+ ⭐"
        elif composite_score >= 80:
            return "A"
        elif composite_score >= 70:
            return "B+"
        elif composite_score >= 60:
            return "B"
        elif composite_score >= 50:
            return "C+"
        elif composite_score >= 40:
            return "C"
        elif composite_score >= 30:
            return "D"
        else:
            return "F"
    
    def _scan_daily_signals(self):
        """Scan all stocks for buy/sell signals on the selected date."""
        # Clear tree
        for item in self.daily_signals_tree.get_children():
            self.daily_signals_tree.delete(item)
        
        try:
            scan_date = self._get_scan_date()
            rs_thresh = float(self.scan_rs_var.get())
            trend_thresh = float(self.scan_trend_var.get())
            comp_thresh = float(self.scan_comp_var.get())
            signal_filter = self.signal_filter_var.get()
            view_mode = self.view_mode_var.get()  # "signals" or "top"
            
            # Get top N setting
            top_n_str = self.top_n_var.get()
            top_n = None if top_n_str == "All" else int(top_n_str)
            
            with self.engine.connect() as conn:
                # Get all rankings for the date with previous day's data for comparison
                df = pd.read_sql(text("""
                    SELECT 
                        r.symbol,
                        r.rs_rating,
                        r.momentum_score,
                        r.trend_template_score,
                        r.technical_score,
                        r.composite_score,
                        r.composite_rank,
                        r.composite_percentile,
                        p.close as price,
                        (SELECT composite_score FROM stock_rankings_history 
                         WHERE symbol = r.symbol AND ranking_date < r.ranking_date 
                         ORDER BY ranking_date DESC LIMIT 1) as prev_composite
                    FROM stock_rankings_history r
                    LEFT JOIN yfinance_daily_quotes p 
                        ON r.symbol = p.symbol AND r.ranking_date = p.date
                    WHERE r.ranking_date = :scan_date
                    ORDER BY r.composite_score DESC
                """), conn, params={"scan_date": scan_date})
            
            if df.empty:
                self.scan_summary_var.set(f"No data for {scan_date}")
                return
            
            # Calculate signals
            buy_count = 0
            sell_count = 0
            row_num = 0
            
            for _, row in df.iterrows():
                row_num += 1
                
                # Determine signal
                is_strong = (
                    row['rs_rating'] >= rs_thresh and
                    row['trend_template_score'] >= trend_thresh and
                    row['composite_score'] >= comp_thresh
                )
                
                prev_comp = row['prev_composite'] if pd.notna(row['prev_composite']) else 0
                is_improving = row['composite_score'] > prev_comp
                is_declining = row['composite_score'] < prev_comp
                
                signal = None
                tag = None
                
                if is_strong and is_improving:
                    signal = "🟢 BUY"
                    tag = 'buy'
                    buy_count += 1
                elif row['composite_score'] < comp_thresh - 10 and is_declining:
                    signal = "🔴 SELL"
                    tag = 'sell'
                    sell_count += 1
                
                # Get letter rating
                comp_score = row['composite_score'] if pd.notna(row['composite_score']) else 0
                rating = self._get_stock_rating(comp_score)
                
                # Apply view mode logic
                if view_mode == "signals":
                    # Signal mode - only show stocks with signals
                    if signal_filter == "buy" and tag != 'buy':
                        continue
                    if signal_filter == "sell" and tag != 'sell':
                        continue
                    if signal_filter == "all" and signal is None:
                        continue
                else:
                    # Top stocks mode - show top N by composite score
                    if top_n and row_num > top_n:
                        break
                    # Assign visual tag for top stocks
                    if row_num <= 10:
                        tag = 'top10'
                    elif comp_score >= 80:
                        tag = 'excellent'
                
                # Add to tree
                price_str = f"₹{row['price']:.2f}" if pd.notna(row['price']) else "-"
                rank_display = f"#{row_num}" if view_mode == "top" else "-"
                
                self.daily_signals_tree.insert("", tk.END, values=(
                    rank_display,
                    row['symbol'],
                    signal if signal else "-",
                    price_str,
                    f"{row['rs_rating']:.0f}" if pd.notna(row['rs_rating']) else "-",
                    f"{row['momentum_score']:.0f}" if pd.notna(row['momentum_score']) else "-",
                    f"{row['trend_template_score']:.0f}" if pd.notna(row['trend_template_score']) else "-",
                    f"{row['technical_score']:.0f}" if pd.notna(row['technical_score']) else "-",
                    f"{row['composite_score']:.0f}" if pd.notna(row['composite_score']) else "-",
                    f"{row['composite_percentile']:.1f}%" if pd.notna(row['composite_percentile']) else "-",
                    rating,
                ), tags=(tag,) if tag else ())
            
            # Update summary
            total_shown = len(self.daily_signals_tree.get_children())
            if view_mode == "signals":
                self.scan_summary_var.set(f"📊 {scan_date}: {buy_count} BUY, {sell_count} SELL signals ({total_shown} shown)")
            else:
                top_label = f"Top {top_n}" if top_n else "All"
                self.scan_summary_var.set(f"🏆 {scan_date}: {top_label} stocks by Composite Score ({total_shown} shown)")
            
        except Exception as e:
            self.scan_summary_var.set(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _sort_daily_signals(self, col):
        """Sort daily signals tree by column."""
        # Toggle sort direction if same column
        if self.daily_signals_sort_col == col:
            self.daily_signals_sort_reverse = not self.daily_signals_sort_reverse
        else:
            self.daily_signals_sort_col = col
            self.daily_signals_sort_reverse = False
        
        # Get all items
        items = [(self.daily_signals_tree.set(item, col), item) 
                 for item in self.daily_signals_tree.get_children('')]
        
        # Sort - try numeric first
        try:
            items.sort(key=lambda x: float(x[0].replace('₹', '').replace('%', '').replace('-', '0')),
                      reverse=self.daily_signals_sort_reverse)
        except ValueError:
            items.sort(key=lambda x: x[0], reverse=self.daily_signals_sort_reverse)
        
        # Rearrange items
        for index, (_, item) in enumerate(items):
            self.daily_signals_tree.move(item, '', index)
    
    def _on_signal_double_click(self, event):
        """Handle double-click on signal row to analyze that symbol."""
        selection = self.daily_signals_tree.selection()
        if selection:
            item = selection[0]
            symbol = self.daily_signals_tree.item(item)['values'][1]  # Symbol is in column 1 now
            self.symbol_var.set(symbol)
            self._analyze()
    
    def _create_sector_rotation_tab(self, notebook):
        """Create sector rotation analysis tab."""
        tab = ttk.Frame(notebook, padding=5)
        notebook.add(tab, text="🔄 Sector Rotation")
        
        # Controls
        controls = ttk.LabelFrame(tab, text="Sector Analysis", padding=10)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        # Date picker
        ttk.Label(controls, text="Date:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        if HAS_CALENDAR:
            self.sector_date_picker = DateEntry(controls, width=12, background='darkblue',
                                                 foreground='white', borderwidth=2,
                                                 date_pattern='yyyy-mm-dd')
            self.sector_date_picker.pack(side=tk.LEFT, padx=5)
        else:
            self.sector_date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
            ttk.Entry(controls, textvariable=self.sector_date_var, width=12).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls, text="🔍 Analyze Sectors", 
                   command=self._analyze_sectors).pack(side=tk.LEFT, padx=15)
        
        # Summary label
        self.sector_summary_var = tk.StringVar(value="Click 'Analyze Sectors' to see sector rotation")
        ttk.Label(controls, textvariable=self.sector_summary_var, 
                  font=("Segoe UI", 10, "italic")).pack(side=tk.RIGHT, padx=10)
        
        # Main content - split into tree and chart
        content = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Left: Sector ratings table
        left_frame = ttk.Frame(content)
        content.add(left_frame, weight=1)
        
        # Sector tree
        columns = ("Rank", "Sector", "RS", "Momentum", "Trend", "Composite", 
                   "1W%", "1M%", "3M%", "Rating")
        self.sector_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)
        
        col_widths = {"Rank": 45, "Sector": 130, "RS": 50, "Momentum": 70, "Trend": 50, 
                      "Composite": 70, "1W%": 60, "1M%": 60, "3M%": 60, "Rating": 70}
        
        for col in columns:
            self.sector_tree.heading(col, text=col, 
                                     command=lambda c=col: self._sort_sectors(c))
            self.sector_tree.column(col, width=col_widths.get(col, 60), anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.sector_tree.yview)
        self.sector_tree.configure(yscrollcommand=scrollbar.set)
        
        self.sector_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tag colors for sectors
        self.sector_tree.tag_configure('leading', background='#d4edda')  # Green
        self.sector_tree.tag_configure('improving', background='#fff3cd')  # Yellow
        self.sector_tree.tag_configure('lagging', background='#f8d7da')  # Red
        
        # Right: Rotation summary/chart
        right_frame = ttk.Frame(content)
        content.add(right_frame, weight=1)
        
        # Rotation summary text
        self.rotation_text = tk.Text(right_frame, font=("Segoe UI", 11), wrap=tk.WORD)
        self.rotation_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags
        self.rotation_text.tag_configure('header', font=("Segoe UI", 14, "bold"))
        self.rotation_text.tag_configure('subheader', font=("Segoe UI", 12, "bold"))
        self.rotation_text.tag_configure('leading', foreground='#155724', font=("Segoe UI", 11, "bold"))
        self.rotation_text.tag_configure('improving', foreground='#856404')
        self.rotation_text.tag_configure('lagging', foreground='#721c24')
        self.rotation_text.tag_configure('neutral', foreground='#383d41')
        
        # Sort state
        self.sector_sort_col = None
        self.sector_sort_reverse = False
        
        # Initialize index rating service
        self.index_service = IndexRatingService()
    
    def _get_sector_date(self):
        """Get the selected sector analysis date."""
        if HAS_CALENDAR:
            return self.sector_date_picker.get_date()
        else:
            return datetime.strptime(self.sector_date_var.get(), "%Y-%m-%d").date()
    
    def _analyze_sectors(self):
        """Analyze sector rotation."""
        # Clear tree
        for item in self.sector_tree.get_children():
            self.sector_tree.delete(item)
        
        self.rotation_text.delete(1.0, tk.END)
        
        try:
            target_date = self._get_sector_date()
            
            # Get sector ratings
            analysis = self.index_service.get_sector_rotation_analysis(target_date)
            
            if not analysis or not analysis.get("all_ratings"):
                self.sector_summary_var.set("No sector data available")
                return
            
            ratings = analysis["all_ratings"]
            
            # Populate tree
            for i, r in enumerate(ratings, 1):
                letter = get_letter_rating(r.composite_score)
                
                # Determine tag
                if r.composite_score >= 70:
                    tag = 'leading'
                elif r.composite_score < 50:
                    tag = 'lagging'
                elif r.return_1m > r.return_3m / 3:
                    tag = 'improving'
                else:
                    tag = ''
                
                self.sector_tree.insert("", tk.END, values=(
                    f"#{i}",
                    r.name,
                    f"{r.rs_rating:.0f}",
                    f"{r.momentum_score:.0f}",
                    f"{r.trend_score:.0f}",
                    f"{r.composite_score:.0f}",
                    f"{r.return_1w:+.1f}%",
                    f"{r.return_1m:+.1f}%",
                    f"{r.return_3m:+.1f}%",
                    letter,
                ), tags=(tag,) if tag else ())
            
            # Update summary
            leading_count = len(analysis.get("leading_sectors", []))
            lagging_count = len(analysis.get("lagging_sectors", []))
            top = analysis.get("top_sector")
            self.sector_summary_var.set(
                f"📊 {target_date}: {leading_count} leading, {lagging_count} lagging sectors | "
                f"Top: {top.name if top else 'N/A'}"
            )
            
            # Build rotation analysis text
            self._build_rotation_analysis(analysis)
            
        except Exception as e:
            self.sector_summary_var.set(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _build_rotation_analysis(self, analysis):
        """Build sector rotation analysis text."""
        text = self.rotation_text
        
        text.insert(tk.END, "🔄 SECTOR ROTATION ANALYSIS\n\n", 'header')
        
        analysis_date = analysis.get("date", date.today())
        text.insert(tk.END, f"Analysis Date: {analysis_date}\n\n", 'neutral')
        
        # Leading sectors
        leading = analysis.get("leading_sectors", [])
        if leading:
            text.insert(tk.END, "🚀 LEADING SECTORS (Score ≥ 70)\n", 'subheader')
            text.insert(tk.END, "Strong momentum, outperforming market. Consider overweight.\n\n", 'neutral')
            for r in leading:
                trend_str = "📈" if r.ma_aligned else "➡️"
                text.insert(tk.END, f"  {trend_str} {r.name}\n", 'leading')
                text.insert(tk.END, f"     Score: {r.composite_score:.0f} | RS: {r.rs_rating:.0f} | "
                                   f"1M: {r.return_1m:+.1f}% | 3M: {r.return_3m:+.1f}%\n", 'neutral')
            text.insert(tk.END, "\n")
        
        # Improving sectors
        improving = analysis.get("improving_sectors", [])
        if improving:
            text.insert(tk.END, "📈 IMPROVING SECTORS\n", 'subheader')
            text.insert(tk.END, "Recent momentum picking up. Watch for breakouts.\n\n", 'neutral')
            for r in improving:
                text.insert(tk.END, f"  ↗️ {r.name}\n", 'improving')
                text.insert(tk.END, f"     Score: {r.composite_score:.0f} | RS: {r.rs_rating:.0f} | "
                                   f"1M: {r.return_1m:+.1f}% | 3M: {r.return_3m:+.1f}%\n", 'neutral')
            text.insert(tk.END, "\n")
        
        # Weakening sectors
        weakening = analysis.get("weakening_sectors", [])
        if weakening:
            text.insert(tk.END, "⚠️ WEAKENING SECTORS\n", 'subheader')
            text.insert(tk.END, "Momentum fading. Consider reducing exposure.\n\n", 'neutral')
            for r in weakening:
                text.insert(tk.END, f"  ↘️ {r.name}\n", 'neutral')
                text.insert(tk.END, f"     Score: {r.composite_score:.0f} | RS: {r.rs_rating:.0f} | "
                                   f"1M: {r.return_1m:+.1f}% | 3M: {r.return_3m:+.1f}%\n", 'neutral')
            text.insert(tk.END, "\n")
        
        # Lagging sectors
        lagging = analysis.get("lagging_sectors", [])
        if lagging:
            text.insert(tk.END, "📉 LAGGING SECTORS (Score < 50)\n", 'subheader')
            text.insert(tk.END, "Underperforming market. Avoid or underweight.\n\n", 'neutral')
            for r in lagging:
                text.insert(tk.END, f"  ⬇️ {r.name}\n", 'lagging')
                text.insert(tk.END, f"     Score: {r.composite_score:.0f} | RS: {r.rs_rating:.0f} | "
                                   f"1M: {r.return_1m:+.1f}% | 3M: {r.return_3m:+.1f}%\n", 'neutral')
            text.insert(tk.END, "\n")
        
        # Strategy recommendations
        text.insert(tk.END, "\n💡 ROTATION STRATEGY\n", 'subheader')
        
        if leading:
            top = leading[0]
            text.insert(tk.END, f"\n• Focus on: {top.name} (strongest sector)\n", 'leading')
            text.insert(tk.END, f"  Look for leading stocks within this sector.\n", 'neutral')
        
        if improving:
            text.insert(tk.END, f"\n• Watch: ", 'neutral')
            text.insert(tk.END, ", ".join([r.name for r in improving]), 'improving')
            text.insert(tk.END, "\n  These sectors are gaining momentum.\n", 'neutral')
        
        if lagging:
            text.insert(tk.END, f"\n• Avoid: ", 'neutral')
            text.insert(tk.END, ", ".join([r.name for r in lagging]), 'lagging')
            text.insert(tk.END, "\n  Wait for trend reversal before entry.\n", 'neutral')
    
    def _sort_sectors(self, col):
        """Sort sector tree by column."""
        if self.sector_sort_col == col:
            self.sector_sort_reverse = not self.sector_sort_reverse
        else:
            self.sector_sort_col = col
            self.sector_sort_reverse = False
        
        items = [(self.sector_tree.set(item, col), item) 
                 for item in self.sector_tree.get_children('')]
        
        try:
            items.sort(key=lambda x: float(x[0].replace('#', '').replace('%', '').replace('+', '')),
                      reverse=self.sector_sort_reverse)
        except ValueError:
            items.sort(key=lambda x: x[0], reverse=self.sector_sort_reverse)
        
        for index, (_, item) in enumerate(items):
            self.sector_tree.move(item, '', index)
    
    def _create_insights_tab(self, notebook):
        """Create insights and strategy tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="💡 Insights & Strategy")
        
        self.insights_text = tk.Text(tab, font=("Segoe UI", 11), wrap=tk.WORD)
        self.insights_text.pack(fill=tk.BOTH, expand=True)
        
        # Insert default strategy guide
        self._show_strategy_guide()
    
    def _quick_analyze(self, symbol):
        """Quick analyze a symbol."""
        self.symbol_var.set(symbol)
        self._analyze()
    
    def _filter_symbols(self, event):
        """Filter symbol dropdown based on typing."""
        typed = self.symbol_var.get().upper()
        if typed:
            filtered = [s for s in self.symbols_list if typed in s]
            self.symbol_combo['values'] = filtered[:50]  # Limit to 50 for performance
        else:
            self.symbol_combo['values'] = self.symbols_list[:50]
    
    def _analyze(self):
        """Analyze price and ratings for selected symbol."""
        symbol = self.symbol_var.get().strip().upper()
        if not symbol:
            return
        
        # Ensure .NS suffix
        if not symbol.endswith('.NS'):
            symbol = symbol + '.NS'
            self.symbol_var.set(symbol)
        
        # Check if this is an index (starts with ^)
        is_index = symbol.startswith('^')
        if is_index:
            messagebox.showinfo("Index Symbol", 
                f"{symbol} is an index.\n\n"
                "Rankings are only calculated for individual stocks, not indices.\n\n"
                "Please select a stock symbol (e.g., RELIANCE.NS, TCS.NS) to view "
                "price and ratings correlation.")
            return
        
        # Get period in days
        period_map = {"3M": 90, "6M": 180, "1Y": 365, "2Y": 730, "3Y": 1095, "5Y": 1825, "All": 9999}
        days = period_map.get(self.period_var.get(), 365)
        
        try:
            # Load data
            self.current_data = self._load_data(symbol, days)
            
            if self.current_data is None or len(self.current_data) < 10:
                messagebox.showwarning("No Data", f"Insufficient data for {symbol}")
                return
            
            # Plot charts
            self._plot_price_ratings()
            self._plot_correlations()
            self._find_signals()
            self._generate_insights()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            import traceback
            traceback.print_exc()
    
    def _load_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Load price and ratings data for symbol."""
        with self.engine.connect() as conn:
            # Get price data - use correct column names: date, close, volume
            price_df = pd.read_sql(text("""
                SELECT date, close, volume
                FROM yfinance_daily_quotes
                WHERE symbol = :symbol
                ORDER BY date DESC
                LIMIT :days
            """), conn, params={"symbol": symbol, "days": days})
            
            if price_df.empty:
                return None
            
            # Get ratings data
            ratings_df = pd.read_sql(text("""
                SELECT ranking_date as date, rs_rating, momentum_score, 
                       trend_template_score, technical_score, composite_score,
                       composite_rank, composite_percentile
                FROM stock_rankings_history
                WHERE symbol = :symbol
                ORDER BY ranking_date DESC
                LIMIT :days
            """), conn, params={"symbol": symbol, "days": days})
            
            # Get Nifty 50 data for comparison - use yfinance_indices_daily_quotes table
            nifty_df = pd.read_sql(text("""
                SELECT date, close as nifty_close
                FROM yfinance_indices_daily_quotes
                WHERE symbol = '^NSEI'
                ORDER BY date DESC
                LIMIT :days
            """), conn, params={"days": days})
            
            # Fallback to indices_daily if yfinance has no data
            if nifty_df.empty:
                nifty_df = pd.read_sql(text("""
                    SELECT trade_date as date, close as nifty_close
                    FROM indices_daily
                    WHERE index_name = 'NIFTY 50'
                    ORDER BY trade_date DESC
                    LIMIT :days
                """), conn, params={"days": days})
        
        # Merge on date
        price_df['date'] = pd.to_datetime(price_df['date'])
        ratings_df['date'] = pd.to_datetime(ratings_df['date'])
        nifty_df['date'] = pd.to_datetime(nifty_df['date'])
        
        df = pd.merge(price_df, ratings_df, on='date', how='inner')
        df = pd.merge(df, nifty_df, on='date', how='left')
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate price returns
        df['returns'] = df['close'].pct_change() * 100
        df['future_5d'] = df['close'].shift(-5) / df['close'] * 100 - 100
        df['future_10d'] = df['close'].shift(-10) / df['close'] * 100 - 100
        df['future_20d'] = df['close'].shift(-20) / df['close'] * 100 - 100
        
        # Calculate SMAs
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        # Normalize prices for comparison (base 100)
        if not df.empty and df['close'].iloc[0] > 0:
            df['close_norm'] = df['close'] / df['close'].iloc[0] * 100
            if 'nifty_close' in df.columns and not df['nifty_close'].isna().all():
                # Find first non-null Nifty value for normalization
                first_nifty = df['nifty_close'].dropna().iloc[0] if not df['nifty_close'].dropna().empty else None
                if first_nifty and first_nifty > 0:
                    df['nifty_norm'] = df['nifty_close'] / first_nifty * 100
                else:
                    df['nifty_norm'] = np.nan
            else:
                df['nifty_norm'] = np.nan
        
        return df
    
    def _plot_price_ratings(self):
        """Plot price and selected rating components."""
        if not HAS_MATPLOTLIB or self.current_data is None:
            return
        
        df = self.current_data
        symbol = self.symbol_var.get()
        
        self.chart_figure.clear()
        
        # Count visible panels
        panels = ['price']  # Price always visible
        
        # Add Nifty as separate panel if selected and mode is "separate"
        if self.show_nifty.get() and self.nifty_mode.get() == "separate":
            panels.append('nifty')
        
        if self.show_rs.get():
            panels.append('rs')
        if self.show_momentum.get():
            panels.append('momentum')
        if self.show_trend.get():
            panels.append('trend')
        if self.show_technical.get():
            panels.append('technical')
        if self.show_composite.get():
            panels.append('composite')
        
        n_panels = len(panels)
        if n_panels == 0:
            n_panels = 1
            panels = ['price']
        
        # Height ratios: price and nifty get 3, others get 1
        height_ratios = [3 if p in ['price', 'nifty'] else 1 for p in panels]
        
        axes = self.chart_figure.subplots(n_panels, 1, sharex=True, 
                                           gridspec_kw={'height_ratios': height_ratios})
        
        # Handle single subplot case
        if n_panels == 1:
            axes = [axes]
        
        self.chart_figure.suptitle(f"{symbol} - Price & Ratings Analysis", fontsize=14, fontweight='bold')
        
        ax_idx = 0
        
        # Plot Price (always shown)
        if 'price' in panels:
            ax = axes[ax_idx]
            ax_idx += 1
            
            # Plot stock price
            ax.plot(df['date'], df['close'], label=f'{symbol.replace(".NS", "")}', 
                    color='#2c3e50', linewidth=1.5)
            ax.plot(df['date'], df['sma_20'], label='SMA 20', color='#3498db', linewidth=1, alpha=0.7)
            ax.plot(df['date'], df['sma_50'], label='SMA 50', color='#e74c3c', linewidth=1, alpha=0.7)
            
            # Overlay Nifty if checkbox is checked AND mode is "overlay"
            if self.show_nifty.get() and self.nifty_mode.get() == "overlay" and 'nifty_norm' in df.columns and not df['nifty_norm'].isna().all():
                ax2 = ax.twinx()
                # Normalize stock to same scale as Nifty for comparison
                stock_norm = df['close'] / df['close'].iloc[0] * 100
                ax2.plot(df['date'], df['nifty_norm'], label='Nifty 50', 
                        color='#9b59b6', linewidth=1.5, linestyle='--', alpha=0.8)
                ax2.plot(df['date'], stock_norm, label=f'{symbol.replace(".NS", "")} (Normalized)', 
                        color='#27ae60', linewidth=1, alpha=0.6)
                ax2.set_ylabel('Normalized (Base 100)', fontsize=9, color='#9b59b6')
                ax2.tick_params(axis='y', labelcolor='#9b59b6')
                ax2.legend(loc='upper right', fontsize=8)
            
            ax.set_ylabel('Price (₹)', fontsize=9)
            ax.legend(loc='upper left', fontsize=8)
            ax.grid(True, alpha=0.3)
            
            title = 'Stock Price'
            if self.show_nifty.get() and self.nifty_mode.get() == "overlay":
                title = 'Stock Price vs Nifty 50 (Overlay)'
            ax.set_title(title, fontsize=10, loc='left')
            
            # Highlight high composite score periods
            if self.show_composite.get():
                high_composite = df['composite_score'] >= 70
                for i in range(len(df)):
                    if high_composite.iloc[i]:
                        ax.axvspan(df['date'].iloc[i], df['date'].iloc[min(i+1, len(df)-1)], 
                                  alpha=0.1, color='green')
        
        # Plot Nifty 50 as separate panel
        if 'nifty' in panels:
            ax = axes[ax_idx]
            ax_idx += 1
            
            if 'nifty_close' in df.columns and not df['nifty_close'].isna().all():
                # Plot Nifty price
                ax.plot(df['date'], df['nifty_close'], label='Nifty 50', 
                        color='#9b59b6', linewidth=1.5)
                
                # Add Nifty SMAs
                nifty_sma20 = df['nifty_close'].rolling(20).mean()
                nifty_sma50 = df['nifty_close'].rolling(50).mean()
                ax.plot(df['date'], nifty_sma20, label='SMA 20', color='#3498db', linewidth=1, alpha=0.7)
                ax.plot(df['date'], nifty_sma50, label='SMA 50', color='#e74c3c', linewidth=1, alpha=0.7)
                
                ax.set_ylabel('Nifty 50', fontsize=9)
                ax.legend(loc='upper left', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.set_title('Nifty 50 Index', fontsize=10, loc='left')
            else:
                ax.text(0.5, 0.5, 'No Nifty data available', transform=ax.transAxes,
                       ha='center', va='center', fontsize=12, color='gray')
                ax.set_title('Nifty 50 Index (No Data)', fontsize=10, loc='left')
        
        # Plot RS Rating
        if 'rs' in panels:
            ax = axes[ax_idx]
            ax_idx += 1
            ax.fill_between(df['date'], df['rs_rating'], alpha=0.3, color='#3498db')
            ax.plot(df['date'], df['rs_rating'], color='#3498db', linewidth=1.5)
            ax.axhline(70, color='green', linestyle='--', alpha=0.5, linewidth=1)
            ax.axhline(30, color='red', linestyle='--', alpha=0.5, linewidth=1)
            ax.set_ylabel('RS', fontsize=9)
            ax.set_ylim(0, 100)
            ax.set_title('RS Rating (Relative Strength vs Market)', fontsize=10, loc='left')
            ax.grid(True, alpha=0.3)
        
        # Plot Momentum
        if 'momentum' in panels:
            ax = axes[ax_idx]
            ax_idx += 1
            ax.fill_between(df['date'], df['momentum_score'], alpha=0.3, color='#e67e22')
            ax.plot(df['date'], df['momentum_score'], color='#e67e22', linewidth=1.5)
            ax.axhline(60, color='green', linestyle='--', alpha=0.5, linewidth=1)
            ax.set_ylabel('Mom', fontsize=9)
            ax.set_ylim(0, 100)
            ax.set_title('Momentum Score (Price Momentum Strength)', fontsize=10, loc='left')
            ax.grid(True, alpha=0.3)
        
        # Plot Trend Template
        if 'trend' in panels:
            ax = axes[ax_idx]
            ax_idx += 1
            ax.fill_between(df['date'], df['trend_template_score'], alpha=0.3, color='#9b59b6')
            ax.plot(df['date'], df['trend_template_score'], color='#9b59b6', linewidth=1.5)
            ax.axhline(6, color='green', linestyle='--', alpha=0.5, linewidth=1)
            ax.set_ylabel('Trend', fontsize=9)
            ax.set_ylim(0, 8)
            ax.set_title('Trend Template (Mark Minervini Criteria: 6+ = Stage 2)', fontsize=10, loc='left')
            ax.grid(True, alpha=0.3)
        
        # Plot Technical
        if 'technical' in panels:
            ax = axes[ax_idx]
            ax_idx += 1
            ax.fill_between(df['date'], df['technical_score'], alpha=0.3, color='#27ae60')
            ax.plot(df['date'], df['technical_score'], color='#27ae60', linewidth=1.5)
            ax.axhline(60, color='green', linestyle='--', alpha=0.5, linewidth=1)
            ax.set_ylabel('Tech', fontsize=9)
            ax.set_ylim(0, 100)
            ax.set_title('Technical Score (RSI, Volume, Volatility)', fontsize=10, loc='left')
            ax.grid(True, alpha=0.3)
        
        # Plot Composite
        if 'composite' in panels:
            ax = axes[ax_idx]
            ax_idx += 1
            colors = ['#27ae60' if v >= 70 else '#f39c12' if v >= 50 else '#e74c3c' 
                      for v in df['composite_score']]
            ax.bar(df['date'], df['composite_score'], color=colors, alpha=0.7, width=1)
            ax.axhline(70, color='green', linestyle='--', alpha=0.7, linewidth=1, label='Strong (70)')
            ax.axhline(50, color='orange', linestyle='--', alpha=0.7, linewidth=1, label='Average (50)')
            ax.set_ylabel('Composite', fontsize=9)
            ax.set_ylim(0, 100)
            ax.set_title('Composite Score (Combined Rating)', fontsize=10, loc='left')
            ax.legend(loc='upper left', fontsize=8)
            ax.grid(True, alpha=0.3)
        
        # Format x-axis on last subplot
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        axes[-1].set_xlabel('Date')
        
        self.chart_figure.tight_layout()
        self.chart_canvas.draw()
    
    def _plot_correlations(self):
        """Plot correlation analysis."""
        if not HAS_MATPLOTLIB or self.current_data is None:
            return
        
        df = self.current_data.dropna()
        
        self.corr_figure.clear()
        axes = self.corr_figure.subplots(2, 2)
        
        # 1. Scatter: Composite vs Future Returns
        ax = axes[0, 0]
        sc = ax.scatter(df['composite_score'], df['future_20d'], 
                       c=df['rs_rating'], cmap='RdYlGn', alpha=0.6, s=20)
        ax.set_xlabel('Composite Score')
        ax.set_ylabel('Future 20-Day Return %')
        ax.set_title('Composite vs Future Returns')
        ax.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax.axvline(70, color='green', linestyle='--', alpha=0.5)
        ax.grid(True, alpha=0.3)
        
        # 2. Lead/Lag Correlation Plot
        ax = axes[0, 1]
        lags = range(-20, 21)
        correlations = {}
        
        for col in ['rs_rating', 'momentum_score', 'composite_score']:
            corrs = []
            for lag in lags:
                if lag >= 0:
                    corr = df[col].iloc[lag:].corr(df['returns'].iloc[:-lag] if lag > 0 else df['returns'])
                else:
                    corr = df[col].iloc[:lag].corr(df['returns'].iloc[-lag:])
                corrs.append(corr if not pd.isna(corr) else 0)
            correlations[col] = corrs
            ax.plot(lags, corrs, label=col.replace('_', ' ').title(), linewidth=1.5)
        
        ax.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax.axvline(0, color='black', linestyle='-', alpha=0.3)
        ax.set_xlabel('Lag (Days) - Negative = Ratings Lead')
        ax.set_ylabel('Correlation')
        ax.set_title('Lead/Lag Correlation with Returns')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # 3. Correlation Heatmap
        ax = axes[1, 0]
        corr_cols = ['close', 'rs_rating', 'momentum_score', 'trend_template_score', 
                     'technical_score', 'composite_score', 'future_20d']
        corr_matrix = df[corr_cols].corr()
        
        im = ax.imshow(corr_matrix, cmap='RdYlGn', vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr_cols)))
        ax.set_yticks(range(len(corr_cols)))
        labels = ['Price', 'RS', 'Mom', 'Trend', 'Tech', 'Comp', 'Fut20D']
        ax.set_xticklabels(labels, rotation=45, fontsize=8)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_title('Correlation Matrix')
        
        for i in range(len(corr_cols)):
            for j in range(len(corr_cols)):
                ax.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}", 
                       ha='center', va='center', fontsize=7)
        
        # 4. Composite Score Buckets vs Returns
        ax = axes[1, 1]
        df['comp_bucket'] = pd.cut(df['composite_score'], 
                                    bins=[0, 30, 50, 70, 100], 
                                    labels=['0-30', '30-50', '50-70', '70-100'])
        bucket_returns = df.groupby('comp_bucket')['future_20d'].agg(['mean', 'std', 'count'])
        
        colors = ['#e74c3c', '#f39c12', '#3498db', '#27ae60']
        bars = ax.bar(range(4), bucket_returns['mean'], 
                     yerr=bucket_returns['std']/np.sqrt(bucket_returns['count']),
                     color=colors, alpha=0.7, capsize=5)
        ax.set_xticks(range(4))
        ax.set_xticklabels(['0-30\n(Weak)', '30-50\n(Below Avg)', '50-70\n(Above Avg)', '70-100\n(Strong)'])
        ax.set_ylabel('Avg Future 20D Return %')
        ax.set_title('Returns by Composite Score Bucket')
        ax.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add count labels
        for i, (bar, count) in enumerate(zip(bars, bucket_returns['count'])):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                   f'n={int(count)}', ha='center', fontsize=8)
        
        self.corr_figure.tight_layout()
        self.corr_canvas.draw()
        
        # Update correlation text
        self._update_correlation_text(df, correlations)
    
    def _update_correlation_text(self, df, correlations):
        """Update correlation analysis text."""
        text = []
        text.append("=" * 40)
        text.append("CORRELATION INSIGHTS")
        text.append("=" * 40)
        
        # Find best lead/lag
        for col, corrs in correlations.items():
            max_idx = np.argmax(np.abs(corrs))
            lag = list(range(-20, 21))[max_idx]
            text.append(f"\n{col.replace('_', ' ').title()}:")
            text.append(f"  Best correlation at lag {lag} days")
            if lag < 0:
                text.append(f"  → Rating LEADS price by {-lag} days! ✅")
            elif lag > 0:
                text.append(f"  → Rating LAGS price by {lag} days")
            else:
                text.append(f"  → Concurrent relationship")
        
        # Bucket analysis
        text.append("\n" + "=" * 40)
        text.append("COMPOSITE SCORE → FUTURE RETURNS")
        text.append("=" * 40)
        
        for bucket in ['0-30', '30-50', '50-70', '70-100']:
            bucket_data = df[df['comp_bucket'] == bucket]['future_20d'].dropna()
            if len(bucket_data) > 0:
                text.append(f"\nScore {bucket}:")
                text.append(f"  Avg 20D Return: {bucket_data.mean():.2f}%")
                text.append(f"  Win Rate (>0%): {(bucket_data > 0).mean()*100:.1f}%")
                text.append(f"  Sample size: {len(bucket_data)}")
        
        # Key insight
        text.append("\n" + "=" * 40)
        text.append("KEY INSIGHT")
        text.append("=" * 40)
        
        high_score = df[df['composite_score'] >= 70]['future_20d'].dropna()
        low_score = df[df['composite_score'] < 30]['future_20d'].dropna()
        
        if len(high_score) > 0 and len(low_score) > 0:
            diff = high_score.mean() - low_score.mean()
            text.append(f"\nHigh Composite (≥70) outperforms")
            text.append(f"Low Composite (<30) by {diff:.2f}%")
            text.append(f"over the next 20 trading days.")
            
            if diff > 2:
                text.append("\n✅ STRONG predictive value!")
            elif diff > 0:
                text.append("\n⚠️ Moderate predictive value")
            else:
                text.append("\n❌ No predictive value for this stock")
        
        self.corr_text.delete("1.0", tk.END)
        self.corr_text.insert(tk.END, "\n".join(text))
    
    def _find_signals(self):
        """Find trading signals based on rating thresholds."""
        if self.current_data is None:
            return
        
        # Clear tree
        for item in self.signals_tree.get_children():
            self.signals_tree.delete(item)
        
        df = self.current_data.copy()
        
        try:
            rs_thresh = float(self.rs_threshold.get())
            trend_thresh = float(self.trend_threshold.get())
            comp_thresh = float(self.composite_threshold.get())
        except ValueError:
            return
        
        # Buy signals: All criteria met AND improving
        df['buy_signal'] = (
            (df['rs_rating'] >= rs_thresh) &
            (df['trend_template_score'] >= trend_thresh) &
            (df['composite_score'] >= comp_thresh) &
            (df['composite_score'] > df['composite_score'].shift(5))  # Improving
        )
        
        # Sell signals: Breaking down
        df['sell_signal'] = (
            (df['composite_score'] < comp_thresh - 10) &
            (df['composite_score'] < df['composite_score'].shift(5))  # Declining
        )
        
        # Find signal transitions (avoid consecutive signals)
        df['buy_entry'] = df['buy_signal'] & ~df['buy_signal'].shift(1).fillna(False)
        df['sell_entry'] = df['sell_signal'] & ~df['sell_signal'].shift(1).fillna(False)
        
        # Add to tree
        for _, row in df.iterrows():
            if row['buy_entry'] or row['sell_entry']:
                signal = "🟢 BUY" if row['buy_entry'] else "🔴 SELL"
                tag = 'buy' if row['buy_entry'] else 'sell'
                
                future_ret = f"{row['future_20d']:.1f}%" if not pd.isna(row['future_20d']) else "N/A"
                
                self.signals_tree.insert("", tk.END, values=(
                    row['date'].strftime('%Y-%m-%d'),
                    signal,
                    f"₹{row['close']:.2f}",
                    f"{row['rs_rating']:.0f}",
                    f"{row['momentum_score']:.0f}",
                    f"{row['trend_template_score']:.0f}",
                    f"{row['technical_score']:.0f}",
                    f"{row['composite_score']:.0f}",
                    future_ret
                ), tags=(tag,))
    
    def _generate_insights(self):
        """Generate trading insights based on current data."""
        if self.current_data is None:
            return
        
        df = self.current_data
        symbol = self.symbol_var.get()
        latest = df.iloc[-1]
        
        insights = []
        insights.append(f"{'='*60}")
        insights.append(f"📊 TRADING INSIGHTS FOR {symbol}")
        insights.append(f"{'='*60}")
        insights.append(f"\nLatest Data: {latest['date'].strftime('%Y-%m-%d')}")
        insights.append(f"Price: ₹{latest['close']:.2f}")
        
        # Current ratings
        insights.append(f"\n📈 CURRENT RATINGS:")
        insights.append(f"  • RS Rating: {latest['rs_rating']:.0f}/99")
        insights.append(f"  • Momentum: {latest['momentum_score']:.0f}/100")
        insights.append(f"  • Trend Template: {latest['trend_template_score']:.0f}/8")
        insights.append(f"  • Technical: {latest['technical_score']:.0f}/100")
        insights.append(f"  • Composite: {latest['composite_score']:.0f}/100")
        
        # Trend
        recent_5d = df.tail(5)['composite_score']
        trend = "📈 IMPROVING" if recent_5d.iloc[-1] > recent_5d.iloc[0] else "📉 DECLINING"
        insights.append(f"\n📊 5-DAY TREND: {trend}")
        insights.append(f"  Composite 5 days ago: {recent_5d.iloc[0]:.0f}")
        insights.append(f"  Composite today: {recent_5d.iloc[-1]:.0f}")
        
        # Trading recommendation
        insights.append(f"\n{'='*60}")
        insights.append("💡 TRADING RECOMMENDATION")
        insights.append(f"{'='*60}")
        
        rs = latest['rs_rating']
        trend_score = latest['trend_template_score']
        comp = latest['composite_score']
        
        if rs >= 70 and trend_score >= 6 and comp >= 70:
            insights.append("\n✅ STRONG BUY CANDIDATE")
            insights.append("   • High relative strength (outperforming market)")
            insights.append("   • Stage 2 uptrend (Minervini criteria)")
            insights.append("   • Strong composite score")
            insights.append("\n   STRATEGY: Look for pullback to 20 SMA for entry")
        elif rs >= 50 and trend_score >= 5 and comp >= 50:
            insights.append("\n⚠️ WATCHLIST CANDIDATE")
            insights.append("   • Moderate strength")
            insights.append("   • Wait for ratings to improve further")
            insights.append("\n   STRATEGY: Add to watchlist, wait for breakout")
        else:
            insights.append("\n❌ NOT RECOMMENDED")
            insights.append("   • Weak relative strength")
            insights.append("   • Not in proper uptrend")
            insights.append("\n   STRATEGY: Avoid or consider short")
        
        # Position sizing guidance
        insights.append(f"\n{'='*60}")
        insights.append("📐 POSITION SIZING GUIDANCE")
        insights.append(f"{'='*60}")
        
        if comp >= 80:
            insights.append("\n  Score 80-100: Full position (100%)")
        elif comp >= 70:
            insights.append("\n  Score 70-80: 3/4 position (75%)")
        elif comp >= 60:
            insights.append("\n  Score 60-70: 1/2 position (50%)")
        else:
            insights.append("\n  Score <60: 1/4 position or skip")
        
        # Stop loss guidance
        insights.append(f"\n{'='*60}")
        insights.append("🛡️ STOP LOSS GUIDANCE")
        insights.append(f"{'='*60}")
        
        sma_20 = latest['sma_20']
        sma_50 = latest['sma_50']
        
        if pd.notna(sma_20) and pd.notna(sma_50):
            insights.append(f"\n  Swing Trade Stop: Below 20 SMA (₹{sma_20:.2f})")
            insights.append(f"  Investment Stop: Below 50 SMA (₹{sma_50:.2f})")
            
            swing_risk = (latest['close'] - sma_20) / latest['close'] * 100
            invest_risk = (latest['close'] - sma_50) / latest['close'] * 100
            
            insights.append(f"\n  Swing Risk: {swing_risk:.1f}%")
            insights.append(f"  Investment Risk: {invest_risk:.1f}%")
        
        self.insights_text.delete("1.0", tk.END)
        self.insights_text.insert(tk.END, "\n".join(insights))
        
        # Append strategy guide
        self.insights_text.insert(tk.END, "\n\n")
        self._append_strategy_guide()
    
    def _show_strategy_guide(self):
        """Show default strategy guide."""
        guide = """
══════════════════════════════════════════════════════════════
📚 HOW TO USE RATINGS FOR TRADING & INVESTING
══════════════════════════════════════════════════════════════

🎯 SWING TRADING (1-4 weeks)
──────────────────────────────────────────────────────────────
Entry Criteria:
  ✓ RS Rating ≥ 70 (outperforming market)
  ✓ Trend Template ≥ 6 (Stage 2 uptrend)
  ✓ Momentum Score ≥ 60 (strong momentum)
  ✓ Composite Score ≥ 70 AND improving

Entry Timing:
  • Wait for pullback to 10 or 20 SMA
  • Look for tight consolidation patterns
  • Enter on breakout with volume

Exit Rules:
  • Take profits at +10-15%
  • Stop loss: 7-8% below entry OR below 20 SMA
  • Exit if Composite drops below 50


📈 INVESTING (3-12 months)
──────────────────────────────────────────────────────────────
Entry Criteria:
  ✓ RS Rating ≥ 80 (top performers)
  ✓ Trend Template = 8 (perfect Stage 2)
  ✓ Composite Score ≥ 75

Position Building:
  • Start with 25% position
  • Add 25% on each pullback to 50 SMA
  • Full position when all ratings peak

Exit Rules:
  • Reduce if RS Rating drops below 50
  • Exit if Trend Template drops to 4
  • Hard stop: 20% below highs OR below 50 SMA


🔍 USING RATINGS AS LEADING INDICATORS
──────────────────────────────────────────────────────────────
1. DIVERGENCE SIGNALS:
   • RS improving + Price flat = Potential breakout
   • RS declining + Price rising = Potential top

2. CONFIRMATION SIGNALS:
   • All ratings rising = Strong uptrend
   • All ratings falling = Avoid

3. EARLY WARNING:
   • Watch Trend Template score
   • Drop from 8 to 6 = Trend weakening
   • Drop below 5 = Exit signal


📊 BACKTESTING YOUR STRATEGY
──────────────────────────────────────────────────────────────
Use the Trading Signals tab to:
1. Set your threshold criteria
2. Review historical buy/sell signals
3. Check "Future 20D%" column for outcomes
4. Calculate win rate and average return

A good strategy should show:
  • Win rate > 55%
  • Avg winner > Avg loser
  • Consistent performance across time


⚠️ IMPORTANT NOTES
──────────────────────────────────────────────────────────────
• Ratings are based on PAST price data
• They show CURRENT strength, not guarantee future
• Always combine with chart analysis
• Use proper position sizing and stop losses
• Paper trade first before real money

══════════════════════════════════════════════════════════════
"""
        self.insights_text.delete("1.0", tk.END)
        self.insights_text.insert(tk.END, guide)
    
    def _append_strategy_guide(self):
        """Append strategy guide to insights."""
        guide = """
══════════════════════════════════════════════════════════════
📚 GENERAL STRATEGY GUIDE
══════════════════════════════════════════════════════════════

🎯 SWING TRADE CRITERIA:
  • RS ≥ 70, Trend ≥ 6, Composite ≥ 70
  • Entry: Pullback to 20 SMA
  • Stop: 7-8% or below 20 SMA
  • Target: +10-15%

📈 INVESTMENT CRITERIA:
  • RS ≥ 80, Trend = 8, Composite ≥ 75
  • Build position on pullbacks to 50 SMA
  • Stop: 20% below highs or below 50 SMA

🔍 RATING DIVERGENCES:
  • RS ↑ + Price → = Potential breakout
  • RS ↓ + Price ↑ = Potential top
"""
        self.insights_text.insert(tk.END, guide)
    
    def run(self):
        """Run the GUI."""
        self.root.mainloop()


def main():
    """Main entry point."""
    app = PriceRatingsAnalyzer()
    app.run()


if __name__ == "__main__":
    main()
