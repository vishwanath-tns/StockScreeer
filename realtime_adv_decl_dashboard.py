"""
Real-Time Advance-Decline Dashboard
====================================

Live dashboard showing intraday market breadth metrics.
Auto-refreshes every 5 minutes during market hours.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
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

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from realtime_market_breadth.core.market_hours_monitor import MarketHoursMonitor
from realtime_market_breadth.core.realtime_data_fetcher import RealTimeDataFetcher
from realtime_market_breadth.core.realtime_adv_decl_calculator import IntradayAdvDeclCalculator
from realtime_market_breadth.services.async_data_logger import AsyncDataLogger
from realtime_market_breadth.services.candle_queue_processor import run_processor
from load_verified_symbols import get_verified_yahoo_symbols


class RealtimeAdvDeclDashboard:
    """Live dashboard for real-time advance-decline monitoring"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Market Breadth - NSE Advance-Decline Monitor")
        self.root.geometry("900x700")
        
        # Components
        self.monitor = MarketHoursMonitor()
        self.fetcher = RealTimeDataFetcher(batch_size=50, calls_per_minute=20)
        self.calculator = IntradayAdvDeclCalculator()
        self.logger = AsyncDataLogger(queue_size=1000)  # Only for breadth snapshots
        
        # Multiprocessing queue for 1-minute candles (IN-MEMORY, separate process)
        self.candle_queue = mp.Queue(maxsize=100000)  # Large in-memory queue
        self.candle_processor = mp.Process(
            target=run_processor, 
            args=(self.candle_queue, 1000),  # Batch size = 1000
            daemon=False
        )
        self.candle_processor.start()
        
        # Polling settings
        self.polling_interval = 300  # 5 minutes in seconds
        self.auto_refresh = tk.BooleanVar(value=True)
        self.polling_thread = None
        self.stop_polling = threading.Event()
        
        # Load verified symbols from database
        self.symbols = get_verified_yahoo_symbols()
        
        # History for graphing
        self.history = {
            'timestamps': [],
            'advances': [],
            'declines': [],
            'unchanged': [],
            'adv_pct': [],
            'decl_pct': []
        }
        
        # UI setup
        self.setup_ui()
        
        # Load previous close cache after UI is ready (so we can log status)
        self.log_status(f"Loading previous close for {len(self.symbols)} symbols...")
        self.fetcher.load_previous_close_cache(self.symbols)
        self.log_status("✅ Previous close cache loaded")
        
        # Start logger
        self.logger.start()
        
        # Initial fetch
        self.root.after(1000, self.fetch_data)
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Title bar
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="REAL-TIME MARKET BREADTH MONITOR",
            font=('Arial', 18, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # Market status bar
        status_frame = tk.Frame(self.root, bg='#34495e', height=40)
        status_frame.pack(fill=tk.X)
        status_frame.pack_propagate(False)
        
        self.market_status_label = tk.Label(
            status_frame,
            text="Market: LOADING...",
            font=('Arial', 11, 'bold'),
            bg='#34495e',
            fg='white'
        )
        self.market_status_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.last_update_label = tk.Label(
            status_frame,
            text="Last Update: Never",
            font=('Arial', 10),
            bg='#34495e',
            fg='#ecf0f1'
        )
        self.last_update_label.pack(side=tk.RIGHT, padx=20, pady=10)
        
        # Main content frame
        main_frame = tk.Frame(self.root, bg='#ecf0f1')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Breadth metrics (top section)
        metrics_frame = tk.LabelFrame(
            main_frame,
            text="Market Breadth Metrics",
            font=('Arial', 12, 'bold'),
            bg='white',
            padx=20,
            pady=20
        )
        metrics_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create 3 columns for metrics
        cols_frame = tk.Frame(metrics_frame, bg='white')
        cols_frame.pack(fill=tk.X)
        
        # Advances column
        adv_frame = tk.Frame(cols_frame, bg='white')
        adv_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        tk.Label(adv_frame, text="ADVANCES", font=('Arial', 10), bg='white', fg='#2c3e50').pack()
        self.advances_label = tk.Label(
            adv_frame,
            text="0",
            font=('Arial', 48, 'bold'),
            bg='white',
            fg='#27ae60'
        )
        self.advances_label.pack()
        self.adv_pct_label = tk.Label(
            adv_frame,
            text="(0.00%)",
            font=('Arial', 14),
            bg='white',
            fg='#27ae60'
        )
        self.adv_pct_label.pack()
        
        # Declines column
        decl_frame = tk.Frame(cols_frame, bg='white')
        decl_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        tk.Label(decl_frame, text="DECLINES", font=('Arial', 10), bg='white', fg='#2c3e50').pack()
        self.declines_label = tk.Label(
            decl_frame,
            text="0",
            font=('Arial', 48, 'bold'),
            bg='white',
            fg='#e74c3c'
        )
        self.declines_label.pack()
        self.decl_pct_label = tk.Label(
            decl_frame,
            text="(0.00%)",
            font=('Arial', 14),
            bg='white',
            fg='#e74c3c'
        )
        self.decl_pct_label.pack()
        
        # Unchanged column
        unch_frame = tk.Frame(cols_frame, bg='white')
        unch_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        
        tk.Label(unch_frame, text="UNCHANGED", font=('Arial', 10), bg='white', fg='#2c3e50').pack()
        self.unchanged_label = tk.Label(
            unch_frame,
            text="0",
            font=('Arial', 48, 'bold'),
            bg='white',
            fg='#95a5a6'
        )
        self.unchanged_label.pack()
        self.unch_pct_label = tk.Label(
            unch_frame,
            text="(0.00%)",
            font=('Arial', 14),
            bg='white',
            fg='#95a5a6'
        )
        self.unch_pct_label.pack()
        
        # Additional metrics
        info_frame = tk.Frame(metrics_frame, bg='white')
        info_frame.pack(fill=tk.X, pady=(20, 0))
        
        info_left = tk.Frame(info_frame, bg='white')
        info_left.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        self.ratio_label = tk.Label(
            info_left,
            text="A/D Ratio: N/A",
            font=('Arial', 12),
            bg='white',
            fg='#2c3e50'
        )
        self.ratio_label.pack()
        
        self.diff_label = tk.Label(
            info_left,
            text="A/D Difference: 0",
            font=('Arial', 12),
            bg='white',
            fg='#2c3e50'
        )
        self.diff_label.pack()
        
        info_right = tk.Frame(info_frame, bg='white')
        info_right.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        self.total_label = tk.Label(
            info_right,
            text="Total Stocks: 0",
            font=('Arial', 12),
            bg='white',
            fg='#2c3e50'
        )
        self.total_label.pack()
        
        self.sentiment_label = tk.Label(
            info_right,
            text="Sentiment: NEUTRAL",
            font=('Arial', 12, 'bold'),
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
        self.log_status("Dashboard initialized. Waiting for first data fetch...")
        
        # Add graph panel
        self.setup_graph(main_frame)
    
    def setup_graph(self, parent):
        """Setup matplotlib graph for A/D trends"""
        graph_frame = tk.LabelFrame(
            parent,
            text="Advance-Decline Trend (Last 12 Updates)",
            font=('Arial', 11, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(8, 3), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Initial empty plot
        self.ax.set_xlabel('Time', fontsize=9)
        self.ax.set_ylabel('Count', fontsize=9)
        self.ax.set_title('Real-Time Advance-Decline Trend', fontsize=10, fontweight='bold')
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.legend(fontsize=8)
        
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
            
            # Log to database (non-blocking)
            poll_time = datetime.now()
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
            self.root.after(0, self.log_status, "Display updated successfully")
            
        except Exception as e:
            self.root.after(0, self.log_status, f"Error: {e}")
            self.root.after(0, messagebox.showerror, "Fetch Error", str(e))
        
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
        sentiment = breadth['market_sentiment']
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
        
        # Update graph with history
        self._update_graph(breadth)
    
    def _update_graph(self, breadth):
        """Update the advance-decline trend graph"""
        # Add current data to history
        now = datetime.now()
        self.history['timestamps'].append(now)
        self.history['advances'].append(breadth['advances'])
        self.history['declines'].append(breadth['declines'])
        self.history['unchanged'].append(breadth['unchanged'])
        self.history['adv_pct'].append(breadth['adv_pct'])
        self.history['decl_pct'].append(breadth['decl_pct'])
        
        # Keep only last 12 data points
        max_points = 12
        if len(self.history['timestamps']) > max_points:
            for key in self.history:
                self.history[key] = self.history[key][-max_points:]
        
        # Clear and redraw
        self.ax.clear()
        
        if len(self.history['timestamps']) >= 2:
            # Format timestamps for x-axis
            times = [t.strftime('%H:%M') for t in self.history['timestamps']]
            
            # Plot lines
            self.ax.plot(times, self.history['advances'], 
                        marker='o', linewidth=2, color='#27ae60', 
                        label=f"Advances ({self.history['advances'][-1]})")
            self.ax.plot(times, self.history['declines'], 
                        marker='s', linewidth=2, color='#e74c3c', 
                        label=f"Declines ({self.history['declines'][-1]})")
            self.ax.plot(times, self.history['unchanged'], 
                        marker='^', linewidth=1, color='#95a5a6', 
                        alpha=0.6, label=f"Unchanged ({self.history['unchanged'][-1]})")
            
            # Styling
            self.ax.set_xlabel('Time', fontsize=9)
            self.ax.set_ylabel('Stock Count', fontsize=9)
            self.ax.set_title('Intraday Advance-Decline Trend', fontsize=10, fontweight='bold')
            self.ax.grid(True, alpha=0.3, linestyle='--')
            self.ax.legend(loc='upper left', fontsize=8)
            
            # Rotate x labels
            plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
            
            # Tight layout
            self.fig.tight_layout()
        else:
            # Not enough data yet
            self.ax.text(0.5, 0.5, 'Waiting for data...', 
                        ha='center', va='center', fontsize=12, color='gray')
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
        
        self.canvas.draw()
    
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
