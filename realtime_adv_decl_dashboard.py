"""
Real-Time Advance-Decline Dashboard v2.0.0
===========================================

Live dashboard showing NIFTY price + advance-decline metrics on single chart.
Displays 2 days of continuous data (yesterday + today).
Smart resume: downloads only missing data from last poll time on restart.
Auto-refreshes every 5 minutes during market hours.

Version: 2.0.0
Date: 2025-11-25

Changes from v1.0.0:
- Combined NIFTY price + A/D lines on single chart (dual y-axis)
- 2-day continuous view (yesterday + today)
- Smart resume: detects gaps and backfills missing data on restart
- Gap-free continuous chart across restarts
- Enhanced IST timezone handling
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta, time as dt_time
import threading
import time
import sys
import os
import multiprocessing as mp
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter, HourLocator
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from realtime_market_breadth.core.market_hours_monitor import MarketHoursMonitor
from realtime_market_breadth.core.realtime_data_fetcher import RealTimeDataFetcher
from realtime_market_breadth.core.realtime_adv_decl_calculator import IntradayAdvDeclCalculator
from realtime_market_breadth.services.async_data_logger import AsyncDataLogger
from realtime_market_breadth.services.candle_queue_processor import run_processor

load_dotenv()


class RealtimeAdvDeclDashboard:
    """Live dashboard for real-time advance-decline monitoring with NIFTY chart"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Market Breadth v2.0.0 - NIFTY + A/D Monitor")
        self.root.geometry("1200x900")
        
        # Database connection
        self.engine = self.create_db_engine()
        
        # Components
        self.monitor = MarketHoursMonitor()
        self.fetcher = RealTimeDataFetcher(batch_size=50, calls_per_minute=20)
        self.calculator = IntradayAdvDeclCalculator()
        self.logger = AsyncDataLogger(queue_size=1000)
        
        # IST timezone
        self.ist = pytz.timezone('Asia/Kolkata')
        
        # Multiprocessing queue for 1-minute candles
        self.candle_queue = mp.Queue(maxsize=100000)
        self.candle_processor = mp.Process(
            target=run_processor, 
            args=(self.candle_queue, 1000),
            daemon=False
        )
        self.candle_processor.start()
        
        # Polling settings
        self.polling_interval = 300  # 5 minutes
        self.auto_refresh = tk.BooleanVar(value=True)
        self.polling_thread = None
        self.stop_polling = threading.Event()
        
        # 2-day history dataframe (yesterday + today)
        self.history_df = pd.DataFrame(columns=[
            'poll_time', 'nifty_ltp', 'advances', 'declines', 'unchanged'
        ])
        
        # Track last poll time for smart resume
        self.last_poll_time = None
        
        # UI setup (creates status_text widget)
        self.setup_ui()
        
        # Now load data (after UI is ready so log_status works)
        # Load verified symbols from nse_yahoo_symbol_map
        self.symbols = self.load_yahoo_symbols_from_map()
        
        # Load 2-day historical data on startup
        self.log_status("Loading 2-day historical data...")
        self.load_2day_history()
        
        # Load previous close from yfinance_indices_daily_quotes (done once at startup)
        self.log_status(f"Loading previous close for {len(self.symbols)} symbols from yfinance_indices_daily_quotes...")
        prev_close_cache = self.load_previous_close_from_indices_table()
        
        # Set the cache in fetcher
        self.fetcher.prev_close_cache = prev_close_cache
        self.fetcher.cache_loaded = True
        self.log_status("✅ Previous close cache loaded from yfinance_indices_daily_quotes")
        
        # Start logger
        self.logger.start()
        
        # Smart resume: check for gaps and backfill
        self.root.after(1000, self.smart_resume_and_fetch)
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_db_engine(self):
        """Create database engine"""
        url = URL.create(
            drivername="mysql+pymysql",
            username=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            database=os.getenv('MYSQL_DB', 'marketdata'),
            query={"charset": "utf8mb4"}
        )
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600)
    
    def load_yahoo_symbols_from_map(self):
        """Load Yahoo symbols from nse_yahoo_symbol_map table"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT yahoo_symbol 
                    FROM nse_yahoo_symbol_map 
                    WHERE is_active = 1
                    ORDER BY nse_symbol
                """))
                symbols = [row[0] for row in result.fetchall()]
                self.log_status(f"✅ Loaded {len(symbols)} symbols from nse_yahoo_symbol_map")
                return symbols
        except Exception as e:
            self.log_status(f"❌ Error loading symbols: {e}")
            return []
    
    def load_previous_close_from_indices_table(self):
        """Load yesterday's closing prices from yfinance_daily_quotes (stocks) and yfinance_indices_daily_quotes (indices)"""
        try:
            with self.engine.connect() as conn:
                # Get most recent date before today
                result = conn.execute(text("""
                    SELECT MAX(date) 
                    FROM yfinance_daily_quotes 
                    WHERE date < CURDATE()
                """))
                prev_date = result.scalar()
                
                if not prev_date:
                    self.log_status("⚠️ No previous close data found")
                    return {}
                
                # Load from yfinance_daily_quotes (stocks)
                result = conn.execute(text("""
                    SELECT symbol, close
                    FROM yfinance_daily_quotes
                    WHERE date = :prev_date
                """), {'prev_date': prev_date})
                prev_close_cache = {row[0]: float(row[1]) for row in result if row[1]}
                
                # Also load from yfinance_indices_daily_quotes (indices like ^NSEI, ^BSESN)
                result = conn.execute(text("""
                    SELECT symbol, close
                    FROM yfinance_indices_daily_quotes
                    WHERE date = :prev_date
                """), {'prev_date': prev_date})
                for row in result:
                    if row[1]:
                        prev_close_cache[row[0]] = float(row[1])
                
                self.log_status(f"✅ Loaded prev close for {len(prev_close_cache)} symbols")
                self.log_status(f"   Previous date: {prev_date}")
                
                return prev_close_cache
                
        except Exception as e:
            self.log_status(f"❌ Error loading previous close: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Title bar
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="REAL-TIME MARKET BREADTH MONITOR v2.0.0",
            font=('Arial', 18, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # Market status bar
        status_frame = tk.Frame(self.root, bg='#34495e', height=30)
        status_frame.pack(fill=tk.X)
        status_frame.pack_propagate(False)
        
        self.market_status_label = tk.Label(
            status_frame,
            text="Market: LOADING...",
            font=('Arial', 9, 'bold'),
            bg='#34495e',
            fg='white'
        )
        self.market_status_label.pack(side=tk.LEFT, padx=15, pady=5)
        
        self.last_update_label = tk.Label(
            status_frame,
            text="Last Update: Never",
            font=('Arial', 8),
            bg='#34495e',
            fg='#ecf0f1'
        )
        self.last_update_label.pack(side=tk.RIGHT, padx=15, pady=5)
        
        # Main content frame
        main_frame = tk.Frame(self.root, bg='#ecf0f1')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Breadth metrics (top section)
        metrics_frame = tk.LabelFrame(
            main_frame,
            text="Market Breadth Metrics",
            font=('Arial', 9, 'bold'),
            bg='white',
            padx=10,
            pady=5
        )
        metrics_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Create 3 columns for metrics
        cols_frame = tk.Frame(metrics_frame, bg='white')
        cols_frame.pack(fill=tk.X)
        
        # Advances column
        adv_frame = tk.Frame(cols_frame, bg='white')
        adv_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        tk.Label(adv_frame, text="ADVANCES", font=('Arial', 8), bg='white', fg='#2c3e50').pack()
        self.advances_label = tk.Label(
            adv_frame,
            text="0",
            font=('Arial', 32, 'bold'),
            bg='white',
            fg='#27ae60'
        )
        self.advances_label.pack()
        self.adv_pct_label = tk.Label(
            adv_frame,
            text="(0.00%)",
            font=('Arial', 10),
            bg='white',
            fg='#27ae60'
        )
        self.adv_pct_label.pack()
        
        # Declines column
        decl_frame = tk.Frame(cols_frame, bg='white')
        decl_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        tk.Label(decl_frame, text="DECLINES", font=('Arial', 8), bg='white', fg='#2c3e50').pack()
        self.declines_label = tk.Label(
            decl_frame,
            text="0",
            font=('Arial', 32, 'bold'),
            bg='white',
            fg='#e74c3c'
        )
        self.declines_label.pack()
        self.decl_pct_label = tk.Label(
            decl_frame,
            text="(0.00%)",
            font=('Arial', 10),
            bg='white',
            fg='#e74c3c'
        )
        self.decl_pct_label.pack()
        
        # Unchanged column
        unch_frame = tk.Frame(cols_frame, bg='white')
        unch_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        tk.Label(unch_frame, text="UNCHANGED", font=('Arial', 8), bg='white', fg='#2c3e50').pack()
        self.unchanged_label = tk.Label(
            unch_frame,
            text="0",
            font=('Arial', 32, 'bold'),
            bg='white',
            fg='#95a5a6'
        )
        self.unchanged_label.pack()
        self.unch_pct_label = tk.Label(
            unch_frame,
            text="(0.00%)",
            font=('Arial', 10),
            bg='white',
            fg='#95a5a6'
        )
        self.unch_pct_label.pack()
        
        # Additional metrics
        info_frame = tk.Frame(metrics_frame, bg='white')
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        info_left = tk.Frame(info_frame, bg='white')
        info_left.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        self.ratio_label = tk.Label(
            info_left,
            text="A/D Ratio: N/A",
            font=('Arial', 9),
            bg='white',
            fg='#2c3e50'
        )
        self.ratio_label.pack()
        
        self.diff_label = tk.Label(
            info_left,
            text="A/D Difference: 0",
            font=('Arial', 9),
            bg='white',
            fg='#2c3e50'
        )
        self.diff_label.pack()
        
        info_right = tk.Frame(info_frame, bg='white')
        info_right.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        self.total_label = tk.Label(
            info_right,
            text="Total Stocks: 0",
            font=('Arial', 9),
            bg='white',
            fg='#2c3e50'
        )
        self.total_label.pack()
        
        self.sentiment_label = tk.Label(
            info_right,
            text="Sentiment: NEUTRAL",
            font=('Arial', 9, 'bold'),
            bg='white',
            fg='#f39c12'
        )
        self.sentiment_label.pack()
        
        # Top movers section
        movers_frame = tk.Frame(main_frame, bg='white')
        movers_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Top gainers
        gainers_frame = tk.LabelFrame(
            movers_frame,
            text="Top 5 Gainers",
            font=('Arial', 11, 'bold'),
            bg='white',
            fg='#27ae60'
        )
        gainers_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.gainers_text = tk.Text(
            gainers_frame,
            height=6,
            font=('Consolas', 10),
            bg='#f8f9fa',
            relief=tk.FLAT
        )
        self.gainers_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top losers
        losers_frame = tk.LabelFrame(
            movers_frame,
            text="Top 5 Losers",
            font=('Arial', 11, 'bold'),
            bg='white',
            fg='#e74c3c'
        )
        losers_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.losers_text = tk.Text(
            losers_frame,
            height=6,
            font=('Consolas', 10),
            bg='#f8f9fa',
            relief=tk.FLAT
        )
        self.losers_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control panel
        control_frame = tk.Frame(main_frame, bg='white', height=80)
        control_frame.pack(fill=tk.X)
        control_frame.pack_propagate(False)
        
        # Auto-refresh checkbox
        self.auto_refresh_check = tk.Checkbutton(
            control_frame,
            text="Auto-Refresh (5 min)",
            variable=self.auto_refresh,
            font=('Arial', 10),
            bg='white',
            command=self.toggle_auto_refresh
        )
        self.auto_refresh_check.pack(side=tk.LEFT, padx=20, pady=20)
        
        # Refresh button
        self.refresh_btn = tk.Button(
            control_frame,
            text="Refresh Now",
            font=('Arial', 10, 'bold'),
            bg='#3498db',
            fg='white',
            padx=20,
            pady=10,
            command=self.manual_refresh,
            cursor='hand2'
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=10, pady=20)
        
        # Countdown label
        self.countdown_label = tk.Label(
            control_frame,
            text="Next refresh in: --:--",
            font=('Arial', 10),
            bg='white',
            fg='#7f8c8d'
        )
        self.countdown_label.pack(side=tk.LEFT, padx=20, pady=20)
        
        # Status bar at bottom
        self.status_text = tk.Text(
            control_frame,
            height=2,
            font=('Consolas', 9),
            bg='#ecf0f1',
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.status_text.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        self.log_status("Dashboard initialized. Loading 2-day historical data...")
        
        # Add graph panel
        self.setup_graph(main_frame)
    
    def setup_graph(self, parent):
        """Setup matplotlib graphs: NIFTY candlestick + A/D lines (2-day continuous view)"""
        graph_frame = tk.LabelFrame(
            parent,
            text="NIFTY + Advance-Decline (2-Day Continuous)",
            font=('Arial', 11, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create matplotlib figure with 2 subplots (NIFTY candlestick on top, A/D lines below)
        self.fig = Figure(figsize=(14, 10), dpi=100, facecolor='white')
        self.ax_nifty = self.fig.add_subplot(211)  # Top: NIFTY candlestick
        self.ax_ad = self.fig.add_subplot(212, sharex=self.ax_nifty)  # Bottom: A/D lines
        
        # Initial empty plots
        self.ax_nifty.set_ylabel('NIFTY Price (₹)', fontsize=10, fontweight='bold', color='#2c3e50')
        self.ax_nifty.set_title('NIFTY 50 (Yesterday + Today)', fontsize=11, fontweight='bold')
        self.ax_nifty.grid(True, alpha=0.3, linestyle='--')
        
        self.ax_ad.set_xlabel('Time', fontsize=10, fontweight='bold')
        self.ax_ad.set_ylabel('Stock Count', fontsize=10, fontweight='bold', color='#27ae60')
        self.ax_ad.set_title('Advance-Decline Count', fontsize=11, fontweight='bold')
        self.ax_ad.grid(True, alpha=0.3, linestyle='--')
        
        self.fig.tight_layout()
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def log_status(self, message):
        """Log status message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        # Keep only last 3 lines
        lines = self.status_text.get("1.0", tk.END).split('\n')
        if len(lines) > 4:
            self.status_text.delete("1.0", "2.0")
    
    def load_2day_history(self):
        """Load 2 days of historical data (yesterday + today) from database on startup
        
        Ensures continuous display from yesterday 3:30 PM to today 9:15 AM without gaps
        """
        try:
            with self.engine.connect() as conn:
                # Get yesterday's date
                today = datetime.now(self.ist).date()
                yesterday = today - timedelta(days=1)
                
                # Load breadth snapshots from last 2 days
                result = conn.execute(text("""
                    SELECT 
                        poll_time,
                        advances,
                        declines,
                        unchanged
                    FROM intraday_advance_decline
                    WHERE trade_date >= :yesterday
                    ORDER BY poll_time
                """), {'yesterday': yesterday})
                
                breadth_data = result.fetchall()
                
                if not breadth_data:
                    self.log_status("No historical data found for last 2 days")
                    return
                
                # Load NIFTY candles for the same period (OHLC data for candlestick)
                result = conn.execute(text("""
                    SELECT 
                        candle_timestamp,
                        open_price,
                        high_price,
                        low_price,
                        close_price
                    FROM intraday_1min_candles
                    WHERE symbol = 'NIFTY'
                      AND trade_date >= :yesterday
                    ORDER BY candle_timestamp
                """), {'yesterday': yesterday})
                
                # Store all NIFTY candles as list of tuples (timestamp, open, high, low, close)
                nifty_candles = [
                    (row[0], 
                     float(row[1]) if row[1] else None,  # open
                     float(row[2]) if row[2] else None,  # high
                     float(row[3]) if row[3] else None,  # low
                     float(row[4]) if row[4] else None)  # close
                    for row in result
                ]
                
                # Function to find closest NIFTY OHLC for a given poll_time
                def find_closest_nifty(poll_time, candles):
                    if not candles:
                        return (None, None, None, None)
                    # Find candle with timestamp closest to poll_time (within 5 minutes)
                    closest = (None, None, None, None)
                    min_diff = timedelta(minutes=5)
                    for candle_time, open_p, high_p, low_p, close_p in candles:
                        if not candle_time.tzinfo:
                            candle_time = self.ist.localize(candle_time)
                        diff = abs(poll_time - candle_time)
                        if diff < min_diff:
                            min_diff = diff
                            closest = (open_p, high_p, low_p, close_p)
                    return closest
                
                # Merge data into history_df with NaN insertion to break line overnight
                history_list = []
                prev_row = None
                
                for row in breadth_data:
                    poll_time = row[0]
                    if not poll_time.tzinfo:
                        poll_time = self.ist.localize(poll_time)
                    
                    # Get NIFTY OHLC for this poll time (closest match within 5 min)
                    nifty_open, nifty_high, nifty_low, nifty_close = find_closest_nifty(poll_time, nifty_candles)
                    
                    # Check for overnight gap (yesterday close to today open)
                    if prev_row is not None:
                        prev_time = prev_row['poll_time']
                        time_diff = (poll_time - prev_time).total_seconds() / 3600  # hours
                        
                        # If gap > 5 hours, insert NaN row to break the line
                        if time_diff > 5:
                            # Insert NaN row with timestamp between prev and current
                            nan_time = prev_time + timedelta(minutes=1)
                            history_list.append({
                                'poll_time': nan_time,
                                'nifty_open': float('nan'),
                                'nifty_high': float('nan'),
                                'nifty_low': float('nan'),
                                'nifty_close': float('nan'),
                                'advances': float('nan'),
                                'declines': float('nan'),
                                'unchanged': float('nan')
                            })
                    
                    # Add current row
                    current_row = {
                        'poll_time': poll_time,
                        'nifty_open': nifty_open,
                        'nifty_high': nifty_high,
                        'nifty_low': nifty_low,
                        'nifty_close': nifty_close,
                        'advances': row[1],
                        'declines': row[2],
                        'unchanged': row[3]
                    }
                    history_list.append(current_row)
                    prev_row = current_row
                
                self.history_df = pd.DataFrame(history_list)
                
                # Track last poll time
                if not self.history_df.empty:
                    self.last_poll_time = self.history_df['poll_time'].max()
                    self.log_status(f"✅ Loaded {len(self.history_df)} historical snapshots")
                    self.log_status(f"Last poll: {self.last_poll_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Initial chart update
                    self.root.after(100, self.update_2day_chart)
                
        except Exception as e:
            self.log_status(f"Error loading history: {e}")
            import traceback
            traceback.print_exc()
    
    def smart_resume_and_fetch(self):
        """Smart resume: check for missing data gaps and backfill before starting real-time polling"""
        try:
            now = datetime.now(self.ist)
            
            # If we have last poll time, check for gaps
            if self.last_poll_time:
                time_since_last_poll = now - self.last_poll_time
                minutes_gap = time_since_last_poll.total_seconds() / 60
                
                self.log_status(f"Gap since last poll: {minutes_gap:.1f} minutes")
                
                # If gap > 5 minutes and market was/is open, backfill
                if minutes_gap > 5:
                    self.log_status("Detected data gap > 5 min. Backfilling...")
                    self.backfill_missing_data(self.last_poll_time, now)
            
            # Now do regular fetch
            self.fetch_data()
            
        except Exception as e:
            self.log_status(f"Error in smart resume: {e}")
            # Fallback to regular fetch
            self.fetch_data()
    
    def backfill_missing_data(self, start_time, end_time):
        """Backfill missing data between start_time and end_time"""
        try:
            # Generate timestamps for missing polls (5-min intervals)
            current = start_time + timedelta(minutes=5)
            backfill_count = 0
            
            while current <= end_time:
                # Only backfill if timestamp is more than 5 min in past
                if (end_time - current).total_seconds() > 300:
                    self.log_status(f"Backfilling {current.strftime('%H:%M')}...")
                    
                    # Note: We can't actually fetch historical 1-min data retroactively
                    # Yahoo Finance API doesn't support specific past timestamps
                    # So we skip backfilling and just note the gap
                    self.log_status(f"⚠️ Cannot backfill {current.strftime('%H:%M')} (historical data unavailable)")
                
                current += timedelta(minutes=5)
            
            if backfill_count > 0:
                self.log_status(f"✅ Backfilled {backfill_count} missing snapshots")
                self.update_2day_chart()
            else:
                self.log_status("ℹ️ No backfill possible - continuing with available data")
            
        except Exception as e:
            self.log_status(f"Backfill error: {e}")
    
    def update_market_status(self):
        """Update market status indicator"""
        status = self.monitor.get_market_status()
        
        if status['is_open']:
            self.market_status_label.config(
                text=f"Market: OPEN",
                fg='#27ae60'
            )
        else:
            self.market_status_label.config(
                text=f"Market: CLOSED",
                fg='#e74c3c'
            )
    
    def fetch_data(self):
        """Fetch real-time data and update display"""
        self.log_status(f"Fetching data for {len(self.symbols)} stocks...")
        self.refresh_btn.config(state=tk.DISABLED)
        
        # Run fetch in separate thread to avoid blocking UI
        thread = threading.Thread(target=self._fetch_and_update, daemon=True)
        thread.start()
    
    def _fetch_and_update(self):
        """Fetch data and update UI (runs in background thread)"""
        try:
            # Update market status
            self.root.after(0, self.update_market_status)
            
            # Fetch data
            start_time = time.time()
            data = self.fetcher.fetch_realtime_data(self.symbols)
            fetch_time = time.time() - start_time
            
            self.root.after(0, self.log_status, 
                          f"Fetched {len(data)}/{len(self.symbols)} stocks in {fetch_time:.1f}s")
            
            # Update calculator
            self.calculator.update_batch(data)
            breadth = self.calculator.calculate_breadth()
            
            # Get NIFTY OHLC
            nifty_data = data.get('NIFTY', {}) or data.get('^NSEI', {})
            nifty_open = nifty_data.get('open')
            nifty_high = nifty_data.get('high')
            nifty_low = nifty_data.get('low')
            nifty_close = nifty_data.get('ltp')
            
            # Add to 2-day history
            poll_time = datetime.now(self.ist)
            if not poll_time.tzinfo:
                poll_time = self.ist.localize(poll_time)
            
            new_row = pd.DataFrame([{
                'poll_time': poll_time,
                'nifty_open': nifty_open,
                'nifty_high': nifty_high,
                'nifty_low': nifty_low,
                'nifty_close': nifty_close,
                'advances': breadth['advances'],
                'declines': breadth['declines'],
                'unchanged': breadth['unchanged']
            }])
            
            self.history_df = pd.concat([self.history_df, new_row], ignore_index=True)
            
            # Keep only 2 days of data
            cutoff = datetime.now(self.ist) - timedelta(days=2)
            self.history_df = self.history_df[self.history_df['poll_time'] >= cutoff]
            
            # Update last poll time
            self.last_poll_time = poll_time
            
            # Log to database (non-blocking)
            trade_date = poll_time.date()
            
            # Log breadth snapshot to database (fast)
            stock_details = {
                symbol: {
                    'ltp': info.get('ltp'),
                    'prev_close': info.get('prev_close'),
                    'volume': info.get('volume', 0)
                }
                for symbol, info in data.items()
            }
            self.logger.log_breadth_snapshot(breadth, stock_details)
            
            # Queue 1-min candles to separate process (IN-MEMORY, fast)
            candles_queued = 0
            for symbol, info in data.items():
                all_candles = info.get('all_candles', [])
                prev_close = info.get('prev_close')
                
                if all_candles and prev_close:
                    for candle in all_candles:
                        candle_record = {
                            'poll_time': poll_time,
                            'trade_date': trade_date,
                            'symbol': symbol,
                            'candle_timestamp': candle.get('timestamp'),
                            'open_price': candle.get('open'),
                            'high_price': candle.get('high'),
                            'low_price': candle.get('low'),
                            'close_price': candle.get('ltp'),
                            'volume': candle.get('volume', 0),
                            'prev_close': prev_close
                        }
                        try:
                            self.candle_queue.put_nowait(candle_record)
                            candles_queued += 1
                        except:
                            pass  # Queue full, skip
            
            self.root.after(0, self.log_status, 
                          f"Queued {candles_queued} candles (in-memory, separate process)")
            
            # Update UI
            self.root.after(0, self._update_ui, breadth)
            self.root.after(0, self.update_2day_chart)
            self.root.after(0, self.log_status, "Display updated successfully")
            
        except Exception as e:
            self.root.after(0, self.log_status, f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.root.after(0, lambda: self.refresh_btn.config(state=tk.NORMAL))
    
    def _update_ui(self, breadth):
        """Update UI with breadth data"""
        # Update last update time
        self.last_update_label.config(
            text=f"Last Update: {datetime.now().strftime('%I:%M:%S %p')}"
        )
        
        # Update metrics
        self.advances_label.config(text=str(breadth['advances']))
        self.adv_pct_label.config(text=f"({breadth['adv_pct']:.2f}%)")
        
        self.declines_label.config(text=str(breadth['declines']))
        self.decl_pct_label.config(text=f"({breadth['decl_pct']:.2f}%)")
        
        self.unchanged_label.config(text=str(breadth['unchanged']))
        self.unch_pct_label.config(text=f"({breadth['unch_pct']:.2f}%)")
        
        # Update additional metrics
        ratio_text = f"A/D Ratio: {breadth['adv_decl_ratio']:.2f}" if breadth['adv_decl_ratio'] else "A/D Ratio: N/A"
        self.ratio_label.config(text=ratio_text)
        
        diff = breadth['adv_decl_diff']
        diff_color = '#27ae60' if diff > 0 else '#e74c3c' if diff < 0 else '#7f8c8d'
        self.diff_label.config(
            text=f"A/D Difference: {diff:+d}",
            fg=diff_color
        )
        
        self.total_label.config(text=f"Total Stocks: {breadth['total_stocks']}")
        
        # Update sentiment
        sentiment = breadth.get('market_sentiment', 'NEUTRAL')
        sentiment_colors = {
            'STRONG BULLISH': '#27ae60',
            'BULLISH': '#2ecc71',
            'SLIGHTLY BULLISH': '#52be80',
            'NEUTRAL': '#f39c12',
            'SLIGHTLY BEARISH': '#e67e22',
            'BEARISH': '#e74c3c',
            'STRONG BEARISH': '#c0392b'
        }
        self.sentiment_label.config(
            text=f"Sentiment: {sentiment}",
            fg=sentiment_colors.get(sentiment, '#f39c12')
        )
        
        # Update top movers
        self._update_movers()
    
    def update_2day_chart(self):
        """Update the 2-day continuous NIFTY candlestick + A/D line charts"""
        if self.history_df.empty:
            return
        
        try:
            # Clear previous plots
            self.ax_nifty.clear()
            self.ax_ad.clear()
            
            # Filter to 2 days only
            cutoff = datetime.now(self.ist) - timedelta(days=2)
            df = self.history_df[self.history_df['poll_time'] >= cutoff].copy()
            
            if len(df) < 2:
                self.ax_nifty.text(0.5, 0.5, 'Waiting for more data...', 
                            ha='center', va='center', fontsize=12, color='gray',
                            transform=self.ax_nifty.transAxes)
                self.canvas.draw()
                return
            
            # Sort by time
            df = df.sort_values('poll_time')
            
            # Extract data (skip NaN rows used for line breaks)
            df_valid = df[~df['advances'].isna()].copy()
            times = df_valid['poll_time'].tolist()
            nifty_open = df_valid['nifty_open'].tolist()
            nifty_high = df_valid['nifty_high'].tolist()
            nifty_low = df_valid['nifty_low'].tolist()
            nifty_close = df_valid['nifty_close'].tolist()
            advances = df_valid['advances'].tolist()
            declines = df_valid['declines'].tolist()
            
            # Use sequential indices instead of datetime for x-axis (removes gap)
            x_indices = list(range(len(times)))
            
            # ===== NIFTY CANDLESTICK CHART =====
            import math
            from matplotlib.patches import Rectangle
            
            # Draw candlesticks for NIFTY
            candle_width = 0.6
            for i, (o, h, l, c) in enumerate(zip(nifty_open, nifty_high, nifty_low, nifty_close)):
                if o is None or h is None or l is None or c is None:
                    continue
                if isinstance(o, float) and math.isnan(o):
                    continue
                
                # Color: green if close > open, red if close < open
                color = '#27ae60' if c >= o else '#e74c3c'
                
                # High-low line (wick)
                self.ax_nifty.plot([i, i], [l, h], color=color, linewidth=1.5, alpha=0.8)
                
                # Candlestick body
                body_height = abs(c - o) if c != o else h * 0.001  # Tiny height for doji
                body_bottom = min(o, c)
                rect = Rectangle((i - candle_width/2, body_bottom), candle_width, body_height,
                                facecolor=color, edgecolor=color, alpha=0.8, linewidth=1)
                self.ax_nifty.add_patch(rect)
            
            # NIFTY styling
            self.ax_nifty.set_ylabel('NIFTY Price (₹)', fontsize=10, fontweight='bold', color='#2c3e50')
            self.ax_nifty.set_title('NIFTY 50 (Yesterday + Today)', fontsize=11, fontweight='bold', pad=10)
            self.ax_nifty.grid(True, alpha=0.3, linestyle='--')
            
            # Add latest price as legend
            if nifty_close and not (isinstance(nifty_close[-1], float) and math.isnan(nifty_close[-1])):
                self.ax_nifty.legend([f'Last: ₹{nifty_close[-1]:.2f}'], loc='upper left', fontsize=9)
            
            # ===== ADVANCE-DECLINE LINE CHART =====
            line1 = self.ax_ad.plot(x_indices, advances, 
                                    color='#27ae60', linewidth=2, 
                                    marker='o', markersize=3,
                                    label=f'Advances ({int(advances[-1])})')
            line2 = self.ax_ad.plot(x_indices, declines, 
                                    color='#e74c3c', linewidth=2, 
                                    marker='s', markersize=3,
                                    label=f'Declines ({int(declines[-1])})')
            
            # A/D styling
            self.ax_ad.set_xlabel('Time (Yesterday + Today)', fontsize=10, fontweight='bold')
            self.ax_ad.set_ylabel('Stock Count', fontsize=10, fontweight='bold', color='#27ae60')
            self.ax_ad.set_title('Advance-Decline Count', fontsize=11, fontweight='bold', pad=10)
            self.ax_ad.grid(True, alpha=0.3, linestyle='--')
            self.ax_ad.legend(loc='upper left', fontsize=9, framealpha=0.9)
            
            # Add vertical line to separate yesterday/today on both charts
            today = datetime.now(self.ist).date()
            today_indices = [i for i, t in enumerate(times) if t.date() == today]
            if today_indices:
                first_today_idx = today_indices[0]
                self.ax_nifty.axvline(x=first_today_idx, color='gray', linestyle='--', 
                                     linewidth=1.5, alpha=0.7)
                self.ax_ad.axvline(x=first_today_idx, color='gray', linestyle='--', 
                                  linewidth=1.5, alpha=0.7)
            
            # Format x-axis with datetime labels at sparse intervals
            # Show every Nth label to avoid overcrowding
            tick_interval = max(1, len(times) // 10)  # Show ~10 labels
            tick_positions = list(range(0, len(times), tick_interval))
            tick_labels = [times[i].strftime('%d-%b %H:%M') for i in tick_positions]
            
            self.ax_ad.set_xticks(tick_positions)
            self.ax_ad.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
            
            # Set x-axis limits to remove padding
            self.ax_nifty.set_xlim(-0.5, len(times) - 0.5)
            self.ax_ad.set_xlim(-0.5, len(times) - 0.5)
            
            # Tight layout
            self.fig.tight_layout()
            
            # Redraw
            self.canvas.draw()
            
        except Exception as e:
            print(f"Chart update error: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_movers(self):
        """Update top gainers and losers"""
        # Gainers
        self.gainers_text.delete('1.0', tk.END)
        gainers = self.calculator.get_top_gainers(5)
        
        if gainers:
            for i, stock in enumerate(gainers, 1):
                symbol_short = stock.symbol.replace('.NS', '')
                self.gainers_text.insert(
                    tk.END,
                    f"{i}. {symbol_short:<12} Rs{stock.ltp:>8.2f}  {stock.change_pct:>+6.2f}%\n"
                )
        else:
            self.gainers_text.insert(tk.END, "No data available")
        
        # Losers
        self.losers_text.delete('1.0', tk.END)
        losers = self.calculator.get_top_losers(5)
        
        if losers:
            for i, stock in enumerate(losers, 1):
                symbol_short = stock.symbol.replace('.NS', '')
                self.losers_text.insert(
                    tk.END,
                    f"{i}. {symbol_short:<12} Rs{stock.ltp:>8.2f}  {stock.change_pct:>+6.2f}%\n"
                )
        else:
            self.losers_text.insert(tk.END, "No data available")
    
    def manual_refresh(self):
        """Manual refresh button clicked"""
        self.fetch_data()
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh polling"""
        if self.auto_refresh.get():
            self.start_polling()
        else:
            self.stop_polling_thread()
    
    def start_polling(self):
        """Start background polling thread"""
        if self.polling_thread and self.polling_thread.is_alive():
            return
        
        self.stop_polling.clear()
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        self.log_status("Auto-refresh enabled (5 min interval)")
    
    def stop_polling_thread(self):
        """Stop background polling thread"""
        self.stop_polling.set()
        self.log_status("Auto-refresh disabled")
    
    def _polling_loop(self):
        """Background polling loop"""
        while not self.stop_polling.is_set():
            # Wait for polling interval with countdown
            for remaining in range(self.polling_interval, 0, -1):
                if self.stop_polling.is_set():
                    return
                
                # Update countdown
                minutes, seconds = divmod(remaining, 60)
                self.root.after(0, self.countdown_label.config,
                              {'text': f"Next refresh in: {minutes:02d}:{seconds:02d}"})
                
                time.sleep(1)
            
            # Check if market is open
            if self.monitor.is_market_open():
                self.root.after(0, self.fetch_data)
            else:
                self.root.after(0, self.log_status, "Market closed - skipping refresh")
    
    def on_closing(self):
        """Handle window close event"""
        self.stop_polling.set()
        self.logger.stop(timeout=10)
        
        # Stop candle processor gracefully
        self.log_status("Stopping candle processor...")
        self.candle_queue.put(None)  # Poison pill
        self.candle_processor.join(timeout=30)
        if self.candle_processor.is_alive():
            self.candle_processor.terminate()
        
        # Close database connection
        self.engine.dispose()
        
        self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = RealtimeAdvDeclDashboard(root)
    
    # Start auto-refresh if enabled
    if app.auto_refresh.get():
        app.start_polling()
    
    root.mainloop()


if __name__ == "__main__":
    main()
