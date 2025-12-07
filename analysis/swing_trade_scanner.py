"""
Swing Trade Scanner - Weekly Stock Selection Tool
================================================
Selects stocks for swing trades based on volume analysis.

Selection Criteria:
1. Unusual turnover spike (volume > 2x 20-day average)
2. Positive price action on high volume day (accumulation signal)
3. Rarity factor (not a constant high-volume stock)
4. Technical setup (price near key levels)
5. Risk/Reward calculation

Usage:
    python -m analysis.swing_trade_scanner
    python -m analysis.swing_trade_scanner --days 5 --min-turnover 2.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv
import threading
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

load_dotenv()

CRORE = 10_000_000


def get_db_engine():
    """Create database engine."""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    db = os.getenv('MYSQL_DB', 'marketdata')
    user = os.getenv('MYSQL_USER', 'root')
    password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
    
    return create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}',
        pool_pre_ping=True,
        pool_recycle=3600
    )


def get_fno_engine():
    """Create database engine for FnO database."""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    user = os.getenv('MYSQL_USER', 'root')
    password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
    
    return create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/fno_marketdata',
        pool_pre_ping=True,
        pool_recycle=3600
    )


def get_fno_symbols():
    """Get list of FnO symbols from the database."""
    try:
        engine = get_fno_engine()
        with engine.connect() as conn:
            # Try fno_symbols table first
            result = conn.execute(text("SELECT DISTINCT symbol FROM fno_symbols WHERE is_active = 1"))
            symbols = {row[0] for row in result}
            if symbols:
                return symbols
            
            # Fallback: get from futures table
            result = conn.execute(text("""
                SELECT DISTINCT symbol FROM nse_futures 
                WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """))
            return {row[0] for row in result}
    except Exception as e:
        print(f"Could not load FnO symbols: {e}")
        # Return a hardcoded list of common FnO stocks as fallback
        return {
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'SBIN', 'BHARTIARTL',
            'KOTAKBANK', 'ITC', 'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI', 'BAJFINANCE', 'TITAN',
            'SUNPHARMA', 'ULTRACEMCO', 'NESTLEIND', 'WIPRO', 'HCLTECH', 'M&M', 'TATAMOTORS',
            'POWERGRID', 'NTPC', 'TECHM', 'BAJAJFINSV', 'ONGC', 'TATASTEEL', 'JSWSTEEL',
            'ADANIENT', 'ADANIPORTS', 'COALINDIA', 'HINDALCO', 'DRREDDY', 'CIPLA', 'EICHERMOT',
            'GRASIM', 'DIVISLAB', 'BRITANNIA', 'APOLLOHOSP', 'BPCL', 'TATACONSUM', 'HEROMOTOCO',
            'INDUSINDBK', 'SBILIFE', 'UPL', 'VEDL', 'HAVELLS', 'PIDILITIND', 'SIEMENS',
            'DLF', 'BANKBARODA', 'PNB', 'CANBK', 'FEDERALBNK', 'IDFCFIRSTB', 'INDIGO',
            'TRENT', 'ZOMATO', 'PAYTM', 'NYKAA', 'DELHIVERY', 'POLICYBZR', 'IRCTC',
            'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'
        }


class SwingTradeScanner:
    """Weekly Swing Trade Scanner based on Volume Analysis."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🎯 Swing Trade Scanner - Weekly Stock Selection")
        self.root.geometry("1400x900")
        
        self.engine = get_db_engine()
        self.scan_results = None
        self.fno_symbols = get_fno_symbols()  # Load FnO symbols
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        # Title
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            title_frame, 
            text="🎯 Swing Trade Scanner", 
            font=('Segoe UI', 16, 'bold')
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            title_frame,
            text="Find stocks with unusual volume for swing trades",
            font=('Segoe UI', 10)
        ).pack(side=tk.LEFT, padx=20)
        
        # Controls
        control_frame = ttk.LabelFrame(self.root, text="Scan Parameters", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Row 1: Basic filters
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="Lookback Days:").pack(side=tk.LEFT, padx=5)
        self.lookback_var = tk.StringVar(value="5")
        ttk.Combobox(
            row1, textvariable=self.lookback_var,
            values=["3", "5", "7", "10", "14"],
            width=5, state='readonly'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="Min Rel Turnover:").pack(side=tk.LEFT, padx=(20, 5))
        self.min_turnover_var = tk.StringVar(value="2.0")
        ttk.Combobox(
            row1, textvariable=self.min_turnover_var,
            values=["1.5", "2.0", "2.5", "3.0", "4.0", "5.0"],
            width=5, state='readonly'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="Min Avg Turnover (Cr):").pack(side=tk.LEFT, padx=(20, 5))
        self.min_avg_turnover_var = tk.StringVar(value="10")
        ttk.Combobox(
            row1, textvariable=self.min_avg_turnover_var,
            values=["1", "5", "10", "25", "50", "100"],
            width=5, state='readonly'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="Price Action:").pack(side=tk.LEFT, padx=(20, 5))
        self.price_action_var = tk.StringVar(value="Up Day Only")
        ttk.Combobox(
            row1, textvariable=self.price_action_var,
            values=["All", "Up Day Only", "Down Day Only"],
            width=12, state='readonly'
        ).pack(side=tk.LEFT, padx=5)
        
        # Row 2: Advanced filters
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="Min Price:").pack(side=tk.LEFT, padx=5)
        self.min_price_var = tk.StringVar(value="50")
        ttk.Entry(row2, textvariable=self.min_price_var, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row2, text="Max Price:").pack(side=tk.LEFT, padx=(20, 5))
        self.max_price_var = tk.StringVar(value="5000")
        ttk.Entry(row2, textvariable=self.max_price_var, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row2, text="Rarity:").pack(side=tk.LEFT, padx=(15, 5))
        self.rarity_var = tk.StringVar(value="All")
        ttk.Combobox(
            row2, textvariable=self.rarity_var,
            values=["All", "Rare Only", "Exclude Always Top100"],
            width=16, state='readonly'
        ).pack(side=tk.LEFT, padx=5)
        
        # FnO Filter
        self.fno_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row2, text="🔷 FnO Only", 
            variable=self.fno_only_var,
            command=self._on_fno_filter_change
        ).pack(side=tk.LEFT, padx=(15, 5))
        
        # Scan button
        ttk.Button(
            row2, text="🔍 SCAN", 
            command=self._run_scan,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=10)
        
        # Help button
        ttk.Button(
            row2, text="❓ Help",
            command=self._show_help
        ).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="Ready to scan")
        ttk.Label(row2, textvariable=self.status_var).pack(side=tk.RIGHT, padx=10)
        
        # Main content - PanedWindow
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Results table
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Results table
        table_frame = ttk.LabelFrame(left_frame, text="📋 Scan Results - Potential Swing Trades (🔷 = FnO Stock)", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = (
            'rank', 'fno', 'symbol', 'date', 'close', 'change_pct', 
            'turnover', 'rel_turn', 'rarity', 'score', 'setup'
        )
        self.results_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        headings = {
            'rank': ('#', 30),
            'fno': ('FnO', 35),
            'symbol': ('Symbol', 95),
            'date': ('Date', 80),
            'close': ('Close', 70),
            'change_pct': ('Day %', 60),
            'turnover': ('Turn', 65),
            'rel_turn': ('RelVol', 55),
            'rarity': ('Rare', 50),
            'score': ('Score', 55),
            'setup': ('Setup', 115)
        }
        
        for col, (text, width) in headings.items():
            self.results_tree.heading(col, text=text, command=lambda c=col: self._sort_results(c))
            self.results_tree.column(col, width=width, anchor=tk.CENTER if col not in ['symbol', 'setup'] else tk.W)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Color coding - FnO stocks get blue tint
        self.results_tree.tag_configure('excellent', background='#81C784')      # Strong buy
        self.results_tree.tag_configure('excellent_fno', background='#4DB6AC')  # FnO Strong buy (teal)
        self.results_tree.tag_configure('good', background='#C8E6C9')           # Good
        self.results_tree.tag_configure('good_fno', background='#80DEEA')       # FnO Good (cyan)
        self.results_tree.tag_configure('moderate', background='#FFF9C4')       # Moderate
        self.results_tree.tag_configure('moderate_fno', background='#B2EBF2')   # FnO Moderate
        self.results_tree.tag_configure('weak', background='#FFCDD2')           # Weak
        self.results_tree.tag_configure('weak_fno', background='#E1BEE7')       # FnO Weak (light purple)
        
        # Bind selection
        self.results_tree.bind('<<TreeviewSelect>>', self._on_select)
        self.results_tree.bind('<Double-1>', self._on_double_click)
        
        # Right: Charts and details
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # Stock detail panel
        detail_frame = ttk.LabelFrame(right_frame, text="📊 Stock Analysis", padding=5)
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        self.detail_fig = Figure(figsize=(8, 7), dpi=100)
        self.detail_canvas = FigureCanvasTkAgg(self.detail_fig, detail_frame)
        self.detail_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        toolbar_frame = ttk.Frame(detail_frame)
        toolbar_frame.pack(fill=tk.X)
        NavigationToolbar2Tk(self.detail_canvas, toolbar_frame)
        
        # Keyboard shortcuts
        self.root.bind('<F5>', lambda e: self._run_scan())
        self.root.bind('<F1>', lambda e: self._show_help())
        
        self.sort_reverse = {}
    
    def _show_help(self):
        """Show help window with signal explanations."""
        help_win = tk.Toplevel(self.root)
        help_win.title("📖 How to Understand and Use Signals")
        help_win.geometry("900x700")
        help_win.transient(self.root)
        
        # Make it modal
        help_win.grab_set()
        
        # Create notebook for organized help
        notebook = ttk.Notebook(help_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ============ TAB 1: Setup Types ============
        tab1 = ttk.Frame(notebook, padding=10)
        notebook.add(tab1, text="🎯 Setup Types")
        
        setup_content = """
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                              SETUP TYPES EXPLAINED                                    ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  🚀 BREAKOUT                                                                          ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  What: Price is near 20-day HIGH and showing unusual volume                          ║
║  Why:  High volume at highs = strong buying pressure, potential new uptrend          ║
║  How:  BUY on breakout above the high | STOP below recent swing low | TARGET +5-10% ║
║                                                                                       ║
║  📈 MOMENTUM                                                                          ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  What: Stock in strong uptrend, price above SMA 20                                   ║
║  Why:  Trend is your friend - momentum tends to continue                             ║
║  How:  BUY on dips to SMA 20 | STOP below SMA 20 | TARGET ride the trend            ║
║                                                                                       ║
║  🔄 PULLBACK BUY                                                                      ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  What: Healthy pullback in an uptrend with volume spike                              ║
║  Why:  Smart money buying the dip - good risk/reward entry                           ║
║  How:  BUY near SMA 20 support | STOP below recent low | TARGET previous high       ║
║                                                                                       ║
║  ⬆️ REVERSAL                                                                          ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  What: Bounce from 20-day LOW on unusual volume                                      ║
║  Why:  Volume at lows = potential bottom, smart money accumulating                   ║
║  How:  BUY on confirmation (higher low) | STOP below the low | TARGET SMA 20        ║
║                                                                                       ║
║  🔍 ACCUMULATION                                                                      ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  What: High volume with small price change (<1%)                                     ║
║  Why:  Institutions loading quietly without moving price much                        ║
║  How:  WATCH and set alert for breakout - don't buy yet, wait for move              ║
║                                                                                       ║
║  ⚠️ NEAR LOW                                                                          ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  What: Stock is near 20-day low (potentially falling knife)                          ║
║  Why:  May fall further - higher risk                                                ║
║  How:  AVOID or use very tight stop | Wait for reversal confirmation                ║
║                                                                                       ║
║  📊 WATCH                                                                             ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  What: No clear pattern yet, needs more data                                         ║
║  Why:  Don't force trades - wait for setup to develop                                ║
║  How:  Add to WATCHLIST | Check again in a few days                                  ║
║                                                                                       ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
        text1 = tk.Text(tab1, font=('Consolas', 10), wrap=tk.WORD, bg='#FAFAFA')
        text1.pack(fill=tk.BOTH, expand=True)
        text1.insert('1.0', setup_content)
        text1.config(state=tk.DISABLED)
        
        # ============ TAB 2: Score & Columns ============
        tab2 = ttk.Frame(notebook, padding=10)
        notebook.add(tab2, text="📊 Score & Columns")
        
        score_content = """
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                           UNDERSTANDING THE SCORE                                     ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  🎯 SCORE FORMULA:                                                                    ║
║  ────────────────                                                                     ║
║  Score = (Relative Turnover) × (Rarity Factor + 0.5) × (Price Action Bonus)          ║
║                                                                                       ║
║  • Relative Turnover: How many times higher than average (2x, 3x, etc.)              ║
║  • Rarity Factor: How unusual is this stock being in top 100 (0 to 1)                ║
║  • Price Action Bonus: +50% if up >2%, +20% if up, -20% if down <2%, -50% if down   ║
║                                                                                       ║
║  SCORE INTERPRETATION:                                                                ║
║  ─────────────────────                                                                ║
║  ┌────────────┬─────────────────┬─────────────────────────────────────────────────┐  ║
║  │   Score    │     Color       │                 Meaning                          │  ║
║  ├────────────┼─────────────────┼─────────────────────────────────────────────────┤  ║
║  │   ≥ 8      │  🟢 Dark Green  │  EXCELLENT - High priority, strong candidate    │  ║
║  │   5 - 8    │  🟡 Light Green │  GOOD - Worth considering for swing trade       │  ║
║  │   3 - 5    │  🟠 Yellow      │  MODERATE - Watch, needs more confirmation      │  ║
║  │   < 3      │  🔴 Light Red   │  WEAK - Lower probability, skip or watch only   │  ║
║  └────────────┴─────────────────┴─────────────────────────────────────────────────┘  ║
║                                                                                       ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                           COLUMN EXPLANATIONS                                         ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Symbol    : Stock ticker (without .NS suffix)                                       ║
║  Date      : Date of the high volume event                                           ║
║  Close     : Closing price on that day                                               ║
║  Day %     : Price change on the high volume day                                     ║
║              • Positive (green) = Accumulation (buying)                              ║
║              • Negative (red) = Distribution (selling)                               ║
║  Turn (Cr) : Turnover in Crores (Price × Volume ÷ 1 Crore)                          ║
║  Rel Vol   : Relative Volume = Today's turnover ÷ 20-day average                    ║
║              • 2x = Twice normal | 5x = Five times normal                            ║
║  Rarity    : How often the stock is NOT in top 100 turnover                         ║
║              • 100% = Very rare (strong signal)                                      ║
║              • 50% = Sometimes in top 100                                            ║
║              • 0% = Always in top 100 (weak signal)                                  ║
║  Score     : Combined quality score (higher = better)                                ║
║  Setup     : Technical pattern type (see Setup Types tab)                            ║
║                                                                                       ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
        text2 = tk.Text(tab2, font=('Consolas', 10), wrap=tk.WORD, bg='#FAFAFA')
        text2.pack(fill=tk.BOTH, expand=True)
        text2.insert('1.0', score_content)
        text2.config(state=tk.DISABLED)
        
        # ============ TAB 3: Weekly Process ============
        tab3 = ttk.Frame(notebook, padding=10)
        notebook.add(tab3, text="📅 Weekly Process")
        
        process_content = """
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                       WEEKLY SWING TRADE SELECTION PROCESS                            ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  📅 WHEN: Run this scan every WEEKEND (Saturday/Sunday)                              ║
║                                                                                       ║
║  ═══════════════════════════════════════════════════════════════════════════════════ ║
║                                                                                       ║
║  STEP 1️⃣  CONFIGURE FILTERS                                                          ║
║  ──────────────────────────                                                           ║
║  • Lookback Days: 5 (default - last week's signals)                                  ║
║  • Min Rel Turnover: 2.0 (at least 2x average volume)                                ║
║  • Price Action: "Up Day Only" (focus on accumulation)                               ║
║  • Rarity Filter: "Exclude Always Top100" (better signals)                           ║
║                                                                                       ║
║  STEP 2️⃣  RUN SCAN                                                                    ║
║  ──────────────────────────                                                           ║
║  • Click "SCAN FOR TRADES" button                                                    ║
║  • Wait for results to load                                                          ║
║                                                                                       ║
║  STEP 3️⃣  SORT BY SCORE                                                               ║
║  ──────────────────────────                                                           ║
║  • Click on "Score" column header to sort                                            ║
║  • Focus on stocks with Score > 5                                                    ║
║  • Best setups: 🚀 Breakout and 🔄 Pullback Buy                                      ║
║                                                                                       ║
║  STEP 4️⃣  ANALYZE CHARTS                                                              ║
║  ──────────────────────────                                                           ║
║  • Click on each stock to see the chart on the right                                 ║
║  • Check if price is near support/resistance levels                                  ║
║  • Look for clean technical setups                                                   ║
║                                                                                       ║
║  STEP 5️⃣  SHORTLIST                                                                   ║
║  ──────────────────────────                                                           ║
║  • Pick TOP 5-10 candidates with clearest setups                                     ║
║  • Write down: Entry price, Stop loss, Target                                        ║
║                                                                                       ║
║  STEP 6️⃣  EXECUTE ON MONDAY                                                           ║
║  ──────────────────────────                                                           ║
║  • Set price alerts for entry triggers                                               ║
║  • When triggered: Enter position                                                    ║
║  • IMMEDIATELY place stop loss order                                                 ║
║                                                                                       ║
║  ═══════════════════════════════════════════════════════════════════════════════════ ║
║                                                                                       ║
║  💡 PRO TIPS:                                                                         ║
║  • Volume precedes price - unusual volume often signals upcoming moves               ║
║  • Rare signals are stronger than frequent ones                                      ║
║  • Green (up) on high volume = accumulation = bullish                                ║
║  • Don't chase - wait for pullback if you missed the initial move                    ║
║                                                                                       ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
        text3 = tk.Text(tab3, font=('Consolas', 10), wrap=tk.WORD, bg='#FAFAFA')
        text3.pack(fill=tk.BOTH, expand=True)
        text3.insert('1.0', process_content)
        text3.config(state=tk.DISABLED)
        
        # ============ TAB 4: Risk Management ============
        tab4 = ttk.Frame(notebook, padding=10)
        notebook.add(tab4, text="⚠️ Risk Management")
        
        risk_content = """
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                              RISK MANAGEMENT RULES                                    ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  ⚠️  THESE RULES ARE NON-NEGOTIABLE - FOLLOW THEM ALWAYS                             ║
║                                                                                       ║
║  ═══════════════════════════════════════════════════════════════════════════════════ ║
║                                                                                       ║
║  📊 POSITION SIZING                                                                   ║
║  ──────────────────────────────────────────────────────────────────────────────────  ║
║  • Risk 2-5% of capital per trade (NEVER more than 5%)                               ║
║  • Example: ₹10L capital → Max ₹50,000 per trade                                     ║
║  • If unsure, start with 2%                                                          ║
║                                                                                       ║
║  🛑 STOP LOSS                                                                         ║
║  ──────────────────────────────────────────────────────────────────────────────────  ║
║  • Set stop at 2-3% from entry price OR below recent swing low                       ║
║  • ALWAYS place stop order immediately after entry                                   ║
║  • Never move stop further away - only trail it up                                   ║
║                                                                                       ║
║  🎯 PROFIT TARGET                                                                     ║
║  ──────────────────────────────────────────────────────────────────────────────────  ║
║  • Minimum 1:2 risk-reward ratio                                                     ║
║  • If risking 2%, target at least 4%                                                 ║
║  • If risking 3%, target at least 6%                                                 ║
║  • Book partial profits at target, trail rest                                        ║
║                                                                                       ║
║  📈 MAX POSITIONS                                                                     ║
║  ──────────────────────────────────────────────────────────────────────────────────  ║
║  • Hold 5-10 stocks maximum at a time                                                ║
║  • Don't put all eggs in one basket                                                  ║
║  • Spread across different sectors                                                   ║
║                                                                                       ║
║  ⏰ HOLDING PERIOD                                                                    ║
║  ──────────────────────────────────────────────────────────────────────────────────  ║
║  • Typical swing trade: 1-4 weeks                                                    ║
║  • If no momentum after 2 weeks, consider exiting                                    ║
║  • Don't turn swing trade into long-term investment                                  ║
║                                                                                       ║
║  ═══════════════════════════════════════════════════════════════════════════════════ ║
║                                                                                       ║
║  🔴 NEVER DO THESE:                                                                   ║
║  ──────────────────────────────────────────────────────────────────────────────────  ║
║  ✗ Average down on losing positions                                                  ║
║  ✗ Hold without a stop loss                                                          ║
║  ✗ Risk more than 5% on any single trade                                             ║
║  ✗ Revenge trade after a loss                                                        ║
║  ✗ Trade without a plan                                                              ║
║                                                                                       ║
║  ═══════════════════════════════════════════════════════════════════════════════════ ║
║                                                                                       ║
║  📝 EXAMPLE TRADE:                                                                    ║
║  ──────────────────────────────────────────────────────────────────────────────────  ║
║  Capital: ₹10,00,000 | Risk per trade: 2% = ₹20,000                                  ║
║  Stock: XYZ at ₹500 | Stop: ₹485 (3% down) | Target: ₹545 (9% up)                   ║
║  Position size: ₹20,000 ÷ (₹500-₹485) = 1,333 shares = ₹6,66,500                    ║
║  Risk: ₹20,000 | Reward: ₹60,000 | Risk-Reward: 1:3 ✓                               ║
║                                                                                       ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
        text4 = tk.Text(tab4, font=('Consolas', 10), wrap=tk.WORD, bg='#FAFAFA')
        text4.pack(fill=tk.BOTH, expand=True)
        text4.insert('1.0', risk_content)
        text4.config(state=tk.DISABLED)
        
        # Close button at bottom
        btn_frame = ttk.Frame(help_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Close (or press Escape)", 
            command=help_win.destroy
        ).pack(side=tk.RIGHT)
        
        ttk.Label(
            btn_frame,
            text="💡 Press F1 anytime to open this help",
            font=('Segoe UI', 9, 'italic')
        ).pack(side=tk.LEFT)
        
        # Bind Escape to close
        help_win.bind('<Escape>', lambda e: help_win.destroy())
        
        # Center the window
        help_win.update_idletasks()
        x = (help_win.winfo_screenwidth() - 900) // 2
        y = (help_win.winfo_screenheight() - 700) // 2
        help_win.geometry(f"900x700+{x}+{y}")
    
    def _run_scan(self):
        """Run the swing trade scan."""
        self.status_var.set("Scanning... Please wait")
        self.root.update()
        
        lookback = int(self.lookback_var.get())
        min_rel_turnover = float(self.min_turnover_var.get())
        min_avg_turnover = float(self.min_avg_turnover_var.get())
        price_action = self.price_action_var.get()
        min_price = float(self.min_price_var.get())
        max_price = float(self.max_price_var.get())
        rarity_filter = self.rarity_var.get()
        
        def scan():
            try:
                with self.engine.connect() as conn:
                    # Step 1: Get recent unusual turnover events
                    query = text("""
                        WITH recent_data AS (
                            SELECT 
                                symbol,
                                date,
                                open,
                                high,
                                low,
                                close,
                                volume,
                                (close * volume) / :crore as turnover_cr,
                                LAG(close) OVER (PARTITION BY symbol ORDER BY date) as prev_close
                            FROM yfinance_daily_quotes
                            WHERE timeframe = 'daily'
                            AND date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                        ),
                        with_metrics AS (
                            SELECT 
                                *,
                                AVG(turnover_cr) OVER (
                                    PARTITION BY symbol 
                                    ORDER BY date 
                                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                                ) as avg_turnover_20d,
                                AVG(close) OVER (
                                    PARTITION BY symbol 
                                    ORDER BY date 
                                    ROWS BETWEEN 20 PRECEDING AND CURRENT ROW
                                ) as sma_20,
                                MIN(low) OVER (
                                    PARTITION BY symbol 
                                    ORDER BY date 
                                    ROWS BETWEEN 20 PRECEDING AND CURRENT ROW
                                ) as low_20d,
                                MAX(high) OVER (
                                    PARTITION BY symbol 
                                    ORDER BY date 
                                    ROWS BETWEEN 20 PRECEDING AND CURRENT ROW
                                ) as high_20d
                            FROM recent_data
                            WHERE prev_close IS NOT NULL
                        )
                        SELECT 
                            symbol,
                            date,
                            open,
                            high,
                            low,
                            close,
                            volume,
                            prev_close,
                            turnover_cr,
                            avg_turnover_20d,
                            CASE WHEN avg_turnover_20d > 0 
                                 THEN turnover_cr / avg_turnover_20d 
                                 ELSE 0 END as rel_turnover,
                            ((close - prev_close) / prev_close) * 100 as day_change_pct,
                            sma_20,
                            low_20d,
                            high_20d
                        FROM with_metrics
                        WHERE date >= DATE_SUB(CURDATE(), INTERVAL :lookback DAY)
                        AND avg_turnover_20d >= :min_avg_turnover
                        AND close >= :min_price
                        AND close <= :max_price
                        AND turnover_cr / NULLIF(avg_turnover_20d, 0) >= :min_rel_turnover
                        ORDER BY date DESC, rel_turnover DESC
                    """)
                    
                    df = pd.read_sql(query, conn, params={
                        'crore': CRORE,
                        'lookback': lookback,
                        'min_avg_turnover': min_avg_turnover,
                        'min_price': min_price,
                        'max_price': max_price,
                        'min_rel_turnover': min_rel_turnover
                    })
                    
                    if df.empty:
                        self.root.after(0, lambda: self._show_no_results())
                        return
                    
                    # Step 2: Calculate rarity (how often in top 100 over last 60 days)
                    rarity_query = text("""
                        WITH daily_rankings AS (
                            SELECT 
                                date,
                                symbol,
                                (close * volume) / :crore as turnover_cr,
                                RANK() OVER (PARTITION BY date ORDER BY (close * volume) DESC) as daily_rank
                            FROM yfinance_daily_quotes
                            WHERE timeframe = 'daily'
                            AND date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                            AND volume > 0
                        )
                        SELECT 
                            symbol,
                            COUNT(*) as days_in_top100,
                            COUNT(DISTINCT date) as total_days
                        FROM daily_rankings
                        WHERE daily_rank <= 100
                        GROUP BY symbol
                    """)
                    
                    rarity_df = pd.read_sql(rarity_query, conn, params={'crore': CRORE})
                    
                    # Get total trading days
                    total_days_query = text("""
                        SELECT COUNT(DISTINCT date) as total_days
                        FROM yfinance_daily_quotes
                        WHERE timeframe = 'daily'
                        AND date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                    """)
                    total_days = pd.read_sql(total_days_query, conn).iloc[0]['total_days']
                    
                    # Calculate rarity factor
                    rarity_df['rarity_pct'] = (rarity_df['days_in_top100'] / total_days) * 100
                    rarity_df['rarity_factor'] = 1 - (rarity_df['days_in_top100'] / total_days)
                    rarity_map = dict(zip(rarity_df['symbol'], rarity_df['rarity_factor']))
                    rarity_pct_map = dict(zip(rarity_df['symbol'], rarity_df['rarity_pct']))
                    
                    # Merge rarity into main df
                    df['rarity_factor'] = df['symbol'].map(rarity_map).fillna(1.0)
                    df['rarity_pct'] = df['symbol'].map(rarity_pct_map).fillna(0)
                    
                    # Step 3: Apply filters
                    # Price action filter
                    if price_action == "Up Day Only":
                        df = df[df['day_change_pct'] > 0]
                    elif price_action == "Down Day Only":
                        df = df[df['day_change_pct'] < 0]
                    
                    # Rarity filter
                    if rarity_filter == "Rare Only (< 30% top100)":
                        df = df[df['rarity_pct'] < 30]
                    elif rarity_filter == "Exclude Always Top100":
                        df = df[df['rarity_pct'] < 80]
                    
                    if df.empty:
                        self.root.after(0, lambda: self._show_no_results())
                        return
                    
                    # Step 4: Calculate swing score and setup type
                    df['price_action_bonus'] = df['day_change_pct'].apply(
                        lambda x: 1.5 if x > 2 else (1.2 if x > 0 else (0.8 if x > -2 else 0.5))
                    )
                    
                    df['swing_score'] = (
                        df['rel_turnover'] * 
                        (df['rarity_factor'] + 0.5) * 
                        df['price_action_bonus']
                    )
                    
                    # Determine setup type
                    def get_setup_type(row):
                        close = row['close']
                        high_20 = row['high_20d']
                        low_20 = row['low_20d']
                        sma_20 = row['sma_20']
                        change = row['day_change_pct']
                        
                        range_20 = high_20 - low_20
                        if range_20 == 0:
                            return "Unknown"
                        
                        position = (close - low_20) / range_20
                        
                        if position > 0.9 and change > 0:
                            return "🚀 Breakout"
                        elif position > 0.7 and close > sma_20:
                            return "📈 Momentum"
                        elif 0.3 < position < 0.6 and close > sma_20 and change > 0:
                            return "🔄 Pullback Buy"
                        elif position < 0.3 and change > 0:
                            return "⬆️ Reversal"
                        elif position < 0.2:
                            return "⚠️ Near Low"
                        elif abs(change) < 1 and row['rel_turnover'] > 3:
                            return "🔍 Accumulation"
                        else:
                            return "📊 Watch"
                    
                    df['setup_type'] = df.apply(get_setup_type, axis=1)
                    
                    # Add FnO indicator for sorting
                    df['is_fno'] = df['symbol'].apply(
                        lambda x: x.replace('.NS', '').replace('.BO', '') in self.fno_symbols
                    )
                    
                    # Sort by score
                    df = df.sort_values('swing_score', ascending=False)
                    
                    # Keep best entry per symbol (most recent high-score day)
                    df_unique = df.groupby('symbol').first().reset_index()
                    df_unique = df_unique.sort_values('swing_score', ascending=False)
                    
                    self.scan_results = df_unique
                    self.full_scan_data = df  # Keep all for charts
                    
                    self.root.after(0, lambda: self._display_results(df_unique))
                    
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=scan, daemon=True).start()
    
    def _on_fno_filter_change(self):
        """Handle FnO filter checkbox change - refresh display."""
        if self.scan_results is not None and not self.scan_results.empty:
            self._display_results(self.scan_results)
    
    def _show_no_results(self):
        """Show no results message."""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.status_var.set("No stocks match criteria. Try relaxing filters.")
    
    def _display_results(self, df: pd.DataFrame):
        """Display scan results."""
        # Clear existing
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Apply FnO filter if checkbox is checked
        display_df = df.copy()
        fno_filter_active = self.fno_only_var.get()
        if fno_filter_active:
            display_df = display_df[display_df['is_fno'] == True]
            if display_df.empty:
                self.status_var.set("No FnO stocks found in results. Uncheck 'FnO Only' to see all.")
                return
        
        fno_count = 0
        for i, (_, row) in enumerate(display_df.iterrows(), 1):
            symbol_clean = row['symbol'].replace('.NS', '').replace('.BO', '')
            is_fno = symbol_clean in self.fno_symbols
            if is_fno:
                fno_count += 1
            
            values = (
                i,
                '🔷' if is_fno else '',  # FnO indicator
                symbol_clean,
                str(row['date'].date()) if hasattr(row['date'], 'date') else str(row['date'])[:10],
                f"₹{row['close']:.2f}",
                f"{row['day_change_pct']:+.2f}%",
                f"{row['turnover_cr']:.1f}",
                f"{row['rel_turnover']:.1f}x",
                f"{100 - row['rarity_pct']:.0f}%",
                f"{row['swing_score']:.1f}",
                row['setup_type']
            )
            
            # Color by score - FnO stocks get different color scheme
            score = row['swing_score']
            if score >= 8:
                tag = 'excellent_fno' if is_fno else 'excellent'
            elif score >= 5:
                tag = 'good_fno' if is_fno else 'good'
            elif score >= 3:
                tag = 'moderate_fno' if is_fno else 'moderate'
            else:
                tag = 'weak_fno' if is_fno else 'weak'
            
            self.results_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Update status
        total_in_df = len(df)
        displayed = len(display_df)
        excellent = len(display_df[display_df['swing_score'] >= 8])
        good = len(display_df[(display_df['swing_score'] >= 5) & (display_df['swing_score'] < 8)])
        
        filter_text = f" (filtered from {total_in_df})" if fno_filter_active else ""
        self.status_var.set(
            f"Found {displayed} candidates{filter_text} | 🔷 FnO: {fno_count} | 🎯 Excellent: {excellent} | ✅ Good: {good} | "
            f"Press F5 to refresh"
        )
    
    def _sort_results(self, col):
        """Sort results by column."""
        if self.scan_results is None or self.scan_results.empty:
            return
        
        reverse = self.sort_reverse.get(col, False)
        self.sort_reverse[col] = not reverse
        
        col_map = {
            'rank': 'swing_score',
            'fno': 'is_fno',
            'symbol': 'symbol',
            'date': 'date',
            'close': 'close',
            'change_pct': 'day_change_pct',
            'turnover': 'turnover_cr',
            'rel_turn': 'rel_turnover',
            'rarity': 'rarity_factor',
            'score': 'swing_score',
            'setup': 'setup_type'
        }
        
        sort_col = col_map.get(col, col)
        sorted_df = self.scan_results.sort_values(by=sort_col, ascending=not reverse)
        
        self._display_results(sorted_df)
    
    def _on_select(self, event):
        """Handle row selection."""
        selection = self.results_tree.selection()
        if not selection:
            return
        
        item = self.results_tree.item(selection[0])
        values = item.get('values', [])
        if values and len(values) > 2:
            # Symbol is now at index 2 (after rank and fno columns)
            symbol = values[2]
            if symbol and not symbol.endswith('.NS'):
                symbol = symbol + '.NS'
            self._draw_stock_chart(symbol)
    
    def _on_double_click(self, event):
        """Handle double-click - could open in Event Study."""
        pass  # Future: open in turnover analysis GUI
    
    def _draw_stock_chart(self, symbol: str):
        """Draw detailed chart for selected stock."""
        self.detail_fig.clear()
        
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT date, open, high, low, close, volume,
                           (close * volume) / :crore as turnover_cr
                    FROM yfinance_daily_quotes
                    WHERE symbol = :symbol
                    AND timeframe = 'daily'
                    AND date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                    ORDER BY date
                """)
                
                df = pd.read_sql(query, conn, params={'symbol': symbol, 'crore': CRORE})
                
                if df.empty:
                    return
                
                df['date'] = pd.to_datetime(df['date'])
                df['turnover_avg'] = df['turnover_cr'].rolling(20).mean()
                df['rel_turnover'] = df['turnover_cr'] / df['turnover_avg']
                df['sma_20'] = df['close'].rolling(20).mean()
                df['sma_50'] = df['close'].rolling(50).mean()
                
                # 3 subplots
                ax1 = self.detail_fig.add_subplot(311)
                ax2 = self.detail_fig.add_subplot(312, sharex=ax1)
                ax3 = self.detail_fig.add_subplot(313, sharex=ax1)
                
                # 1. Price with moving averages
                ax1.plot(df['date'], df['close'], 'k-', linewidth=1.5, label='Close')
                ax1.plot(df['date'], df['sma_20'], 'b--', linewidth=1, alpha=0.7, label='SMA 20')
                ax1.plot(df['date'], df['sma_50'], 'orange', linewidth=1, alpha=0.7, label='SMA 50')
                ax1.fill_between(df['date'], df['low'], df['high'], alpha=0.2, color='gray')
                ax1.set_ylabel('Price (₹)')
                ax1.set_title(f'{symbol} - Price & Moving Averages', fontsize=10, fontweight='bold')
                ax1.legend(loc='upper left', fontsize=8)
                ax1.grid(True, alpha=0.3)
                
                # Mark recent high volume days
                recent = df.tail(int(self.lookback_var.get()))
                high_vol = recent[recent['rel_turnover'] >= float(self.min_turnover_var.get())]
                if not high_vol.empty:
                    ax1.scatter(high_vol['date'], high_vol['close'], c='red', s=100, 
                               marker='^', zorder=5, label='High Volume')
                
                # 2. Turnover bars
                colors = ['#4CAF50' if r >= 1.5 else '#90CAF9' for r in df['rel_turnover'].fillna(1)]
                ax2.bar(df['date'], df['turnover_cr'], color=colors, alpha=0.7, width=0.8)
                ax2.plot(df['date'], df['turnover_avg'], 'r-', linewidth=1.5, label='20D Avg')
                ax2.set_ylabel('Turnover (Cr)')
                ax2.legend(loc='upper left', fontsize=8)
                ax2.grid(True, alpha=0.3)
                
                # 3. Relative turnover
                colors_rel = ['#4CAF50' if r >= 2 else ('#FFA726' if r >= 1.5 else '#90CAF9') 
                             for r in df['rel_turnover'].fillna(1)]
                ax3.bar(df['date'], df['rel_turnover'], color=colors_rel, alpha=0.7, width=0.8)
                ax3.axhline(y=2, color='red', linestyle='--', linewidth=1, label='2x threshold')
                ax3.axhline(y=1, color='gray', linestyle='--', linewidth=1)
                ax3.set_ylabel('Relative Turnover')
                ax3.set_xlabel('Date')
                ax3.legend(loc='upper left', fontsize=8)
                ax3.grid(True, alpha=0.3)
                
                # Format x-axis
                for ax in [ax1, ax2, ax3]:
                    ax.tick_params(axis='x', rotation=45)
                
                self.detail_fig.tight_layout()
                self.detail_canvas.draw()
                
        except Exception as e:
            print(f"Error drawing chart: {e}")


def main():
    root = tk.Tk()
    
    # Style
    style = ttk.Style()
    style.theme_use('clam')
    
    app = SwingTradeScanner(root)
    root.mainloop()


if __name__ == '__main__':
    main()
