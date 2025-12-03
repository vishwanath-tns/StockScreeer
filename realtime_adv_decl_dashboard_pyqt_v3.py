#!/usr/bin/env python3
"""
Real-Time Advance-Decline Dashboard v3.0.0 (PyQtGraph Version)
===============================================================

High-performance live dashboard using PyQtGraph for smooth charting.
Shows NIFTY candlesticks + advance-decline metrics with real-time updates.

Version: 3.0.0
Date: 2025-12-01

Key Features:
- PyQtGraph for fast, interactive candlestick charts
- 2-day continuous view (yesterday + today)
- 1-minute granularity A/D calculation from candle data
- Smart resume: downloads only missing data from last poll time
- Auto-refreshes every 5 minutes during market hours
- GPU-accelerated rendering where available

Based on realtime_adv_decl_dashboard.py (Tkinter/Matplotlib version)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, time as dt_time
import threading
import time
import multiprocessing as mp
from collections import defaultdict

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import pytz

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QFrame, QTextEdit, QSplitter,
    QGroupBox, QGridLayout, QSizePolicy, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QFont, QColor, QPalette

import pyqtgraph as pg
from pyqtgraph import DateAxisItem

from realtime_market_breadth.core.market_hours_monitor import MarketHoursMonitor
from realtime_market_breadth.core.realtime_data_fetcher import RealTimeDataFetcher
from realtime_market_breadth.core.realtime_adv_decl_calculator import IntradayAdvDeclCalculator
from realtime_market_breadth.services.async_data_logger import AsyncDataLogger
from realtime_market_breadth.services.candle_queue_processor import run_processor
from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

load_dotenv()


# Configure PyQtGraph for best performance
pg.setConfigOptions(
    antialias=True,
    useOpenGL=True,
    enableExperimental=True
)


class CandlestickItem(pg.GraphicsObject):
    """Custom PyQtGraph item for candlestick charts - optimized for many candles"""
    
    def __init__(self, data=None):
        super().__init__()
        self.data = data  # List of (index, open, high, low, close)
        self.picture = None
        self.generatePicture()
    
    def setData(self, data):
        """Update the candlestick data"""
        self.data = data
        self.generatePicture()
        self.informViewBoundsChanged()
        self.update()
    
    def generatePicture(self):
        """Generate the picture for drawing"""
        from PyQt6.QtGui import QPainter, QPen, QBrush
        from PyQt6.QtCore import QRectF, QLineF
        
        self.picture = pg.QtGui.QPicture()
        
        if not self.data or len(self.data) == 0:
            return
        
        p = QPainter(self.picture)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Faster rendering
        
        # Colors
        green = QColor('#27ae60')
        red = QColor('#e74c3c')
        green_pen = QPen(green)
        red_pen = QPen(red)
        green_brush = QBrush(green)
        red_brush = QBrush(red)
        
        # Adjust candle width based on number of candles
        num_candles = len(self.data)
        if num_candles > 300:
            candle_width = 0.9
            wick_width = 1
        elif num_candles > 150:
            candle_width = 0.85
            wick_width = 1
        else:
            candle_width = 0.8
            wick_width = 2
        
        green_pen.setWidth(wick_width)
        red_pen.setWidth(wick_width)
        
        for i, (idx, o, h, l, c) in enumerate(self.data):
            if o is None or h is None or l is None or c is None:
                continue
            
            # Determine color
            is_bullish = c >= o
            if is_bullish:
                p.setPen(green_pen)
                p.setBrush(green_brush)
            else:
                p.setPen(red_pen)
                p.setBrush(red_brush)
            
            # Draw wick (high-low line)
            p.drawLine(QLineF(i, l, i, h))
            
            # Draw body - make sure it has minimum height for visibility
            body_height = abs(c - o)
            if body_height < (h - l) * 0.01:  # Minimum 1% of range
                body_height = (h - l) * 0.01 if h != l else 1
            body_bottom = min(o, c)
            
            rect = QRectF(i - candle_width/2, body_bottom, candle_width, body_height)
            p.drawRect(rect)
        
        p.end()
    
    def paint(self, p, *args):
        if self.picture:
            self.picture.play(p)
    
    def boundingRect(self):
        from PyQt6.QtCore import QRectF
        
        if not self.data or len(self.data) == 0:
            return QRectF(0, 0, 1, 1)
        
        lows = [d[3] for d in self.data if d[3] is not None]
        highs = [d[2] for d in self.data if d[2] is not None]
        
        if not lows or not highs:
            return QRectF(0, 0, 1, 1)
        
        min_low = min(lows)
        max_high = max(highs)
        
        return QRectF(-1, min_low - 10, len(self.data) + 2, max_high - min_low + 20)


class DataFetchWorker(QThread):
    """Background worker for fetching real-time data"""
    
    finished = pyqtSignal(dict)  # Emits breadth data
    status_update = pyqtSignal(str)  # Emits status messages
    error = pyqtSignal(str)
    
    def __init__(self, fetcher, calculator, symbols, candle_queue, ist, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.calculator = calculator
        self.symbols = symbols
        self.candle_queue = candle_queue
        self.ist = ist
    
    def run(self):
        try:
            # Fetch data
            start_time = time.time()
            data = self.fetcher.fetch_realtime_data(self.symbols)
            fetch_time = time.time() - start_time
            
            self.status_update.emit(f"Fetched {len(data)}/{len(self.symbols)} stocks in {fetch_time:.1f}s")
            
            # Update calculator
            self.calculator.update_batch(data)
            breadth = self.calculator.calculate_breadth()
            
            # Get poll time
            poll_time = datetime.now(self.ist)
            trade_date = poll_time.date()
            
            # Calculate 1-min A/D from candles
            minute_candles = defaultdict(list)
            candles_queued = 0
            symbols_with_candles = 0
            
            for symbol, info in data.items():
                all_candles = info.get('all_candles', [])
                prev_close = info.get('prev_close')
                
                if all_candles:
                    symbols_with_candles += 1
                
                if all_candles and prev_close:
                    for candle in all_candles:
                        candle_ts = candle.get('timestamp')
                        close_price = candle.get('ltp') or candle.get('close')
                        
                        if candle_ts and close_price:
                            # Normalize timestamp
                            if isinstance(candle_ts, str):
                                try:
                                    candle_ts = pd.to_datetime(candle_ts)
                                except:
                                    continue
                            
                            if hasattr(candle_ts, 'to_pydatetime'):
                                candle_ts = candle_ts.to_pydatetime()
                            
                            if candle_ts.tzinfo is None:
                                candle_ts = self.ist.localize(candle_ts)
                            else:
                                candle_ts = candle_ts.astimezone(self.ist)
                            
                            minute_key = candle_ts.replace(second=0, microsecond=0)
                            minute_candles[minute_key].append((symbol, float(close_price), float(prev_close)))
                        
                        # Queue to DB processor
                        candle_record = {
                            'poll_time': poll_time,
                            'trade_date': trade_date,
                            'symbol': symbol,
                            'candle_timestamp': candle.get('timestamp'),
                            'open_price': candle.get('open'),
                            'high_price': candle.get('high'),
                            'low_price': candle.get('low'),
                            'close_price': close_price,
                            'volume': candle.get('volume', 0),
                            'prev_close': prev_close
                        }
                        try:
                            self.candle_queue.put_nowait(candle_record)
                            candles_queued += 1
                        except:
                            pass
            
            # Calculate A/D per minute
            new_minute_rows = []
            for minute_time in sorted(minute_candles.keys()):
                candles_in_minute = minute_candles[minute_time]
                advances = sum(1 for _, c, pc in candles_in_minute if c > pc)
                declines = sum(1 for _, c, pc in candles_in_minute if c < pc)
                unchanged = sum(1 for _, c, pc in candles_in_minute if c == pc)
                
                new_minute_rows.append({
                    'candle_time': minute_time,
                    'advances': advances,
                    'declines': declines,
                    'unchanged': unchanged
                })
            
            if new_minute_rows:
                first_min = min(r['candle_time'] for r in new_minute_rows)
                last_min = max(r['candle_time'] for r in new_minute_rows)
                last_row = [r for r in new_minute_rows if r['candle_time'] == last_min][0]
                total_stocks = last_row['advances'] + last_row['declines'] + last_row['unchanged']
                self.status_update.emit(
                    f"📊 Candle A/D: {first_min.strftime('%H:%M')}-{last_min.strftime('%H:%M')}, "
                    f"Latest ({total_stocks}): Adv={last_row['advances']} Dec={last_row['declines']}"
                )
            
            if candles_queued > 0:
                self.status_update.emit(f"✅ Queued {candles_queued} candles from {symbols_with_candles} symbols")
            
            # Emit results
            result = {
                'breadth': breadth,
                'data': data,
                'poll_time': poll_time,
                'minute_ad_rows': new_minute_rows,
                'nifty_data': data.get('NIFTY', {}) or data.get('^NSEI', {})
            }
            self.finished.emit(result)
            
        except Exception as e:
            import traceback
            self.error.emit(f"Error: {e}\n{traceback.format_exc()}")


class RealtimeAdvDeclDashboardPyQt(QMainWindow):
    """High-performance Real-Time Market Breadth Monitor using PyQtGraph"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Market Breadth Monitor v3.0.0 (PyQtGraph)")
        self.setMinimumSize(1400, 900)
        
        # IST timezone
        self.ist = pytz.timezone('Asia/Kolkata')
        
        # Database connection
        self.engine = self.create_db_engine()
        
        # Components
        self.monitor = MarketHoursMonitor()
        self.fetcher = RealTimeDataFetcher(batch_size=50, calls_per_minute=20)
        self.calculator = IntradayAdvDeclCalculator()
        self.logger = AsyncDataLogger(queue_size=1000)
        
        # Multiprocessing queue for 1-minute candles
        self.candle_queue = mp.Queue(maxsize=100000)
        self.candle_processor = mp.Process(
            target=run_processor,
            args=(self.candle_queue, 1000),
            daemon=False
        )
        self.candle_processor.start()
        
        # Data storage
        self.history_df = pd.DataFrame(columns=[
            'poll_time', 'nifty_ltp', 'advances', 'declines', 'unchanged'
        ])
        self.minute_ad_df = pd.DataFrame(columns=[
            'candle_time', 'advances', 'declines', 'unchanged'
        ])
        
        # NIFTY candle data for chart
        self.nifty_candles = []  # List of (timestamp, open, high, low, close)
        self.ad_data = {'times': [], 'advances': [], 'declines': []}
        
        # Polling settings
        self.polling_interval = 300  # 5 minutes
        self.auto_refresh = True
        self.countdown_remaining = 0
        self.last_poll_time = None
        
        # Worker thread
        self.worker = None
        
        # Setup UI
        self.setup_ui()
        
        # Load symbols
        self.symbols = self.load_nifty500_symbols()
        
        # Load previous close cache
        self.log_status("Loading previous close data...")
        prev_close_cache = self.load_previous_close_from_db()
        self.fetcher.prev_close_cache = prev_close_cache
        self.fetcher.cache_loaded = True
        self.log_status(f"✅ Loaded prev close for {len(prev_close_cache)} symbols")
        
        # Load historical data
        self.log_status("Loading 2-day historical data...")
        self.load_2day_history()
        
        # Start logger
        self.logger.start()
        
        # Setup timers
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        
        self.market_status_timer = QTimer()
        self.market_status_timer.timeout.connect(self.update_market_status)
        self.market_status_timer.start(10000)  # Every 10 seconds
        
        # Initial fetch
        QTimer.singleShot(1000, self.fetch_data)
        
        # Start auto-refresh
        if self.auto_refresh:
            self.start_polling()
    
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
    
    def load_nifty500_symbols(self):
        """Load Nifty 500 symbols"""
        yahoo_symbols = [f"{symbol}.NS" for symbol in NIFTY_500_STOCKS]
        if '^NSEI' not in yahoo_symbols:
            yahoo_symbols.append('^NSEI')
        self.log_status(f"✅ Loaded {len(NIFTY_500_STOCKS)} Nifty 500 stocks + NIFTY index")
        return yahoo_symbols
    
    def load_previous_close_from_db(self):
        """Load previous close from database"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE()
                """))
                prev_date = result.scalar()
                
                if not prev_date:
                    return {}
                
                result = conn.execute(text("""
                    SELECT symbol, close FROM yfinance_daily_quotes WHERE date = :prev_date
                """), {'prev_date': prev_date})
                prev_close = {row[0]: float(row[1]) for row in result if row[1]}
                
                # Also load indices
                result = conn.execute(text("""
                    SELECT symbol, close FROM yfinance_indices_daily_quotes WHERE date = :prev_date
                """), {'prev_date': prev_date})
                for row in result:
                    if row[1]:
                        prev_close[row[0]] = float(row[1])
                
                return prev_close
        except Exception as e:
            self.log_status(f"❌ Error loading prev close: {e}")
            return {}
    
    def setup_ui(self):
        """Setup the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Main content - splitter for charts and metrics
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Charts
        charts_widget = self.create_charts_panel()
        splitter.addWidget(charts_widget)
        
        # Right: Metrics and controls
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([900, 400])
        layout.addWidget(splitter, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def create_header(self):
        """Create header bar"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 5px;
            }
            QLabel {
                color: white;
            }
        """)
        header.setFixedHeight(60)
        
        layout = QHBoxLayout(header)
        
        title = QLabel("📊 REAL-TIME MARKET BREADTH MONITOR v3.0.0")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addStretch()
        
        self.market_status_label = QLabel("Market: Loading...")
        self.market_status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.market_status_label)
        
        layout.addSpacing(30)
        
        self.last_update_label = QLabel("Last Update: Never")
        self.last_update_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.last_update_label)
        
        return header
    
    def create_charts_panel(self):
        """Create the charts panel with PyQtGraph"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Create graphics layout widget
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.setBackground('w')
        
        # NIFTY Candlestick Chart
        self.nifty_plot = self.graphics_widget.addPlot(row=0, col=0, title="NIFTY 50 (Intraday 1-min)")
        self.nifty_plot.setLabel('left', 'Price (₹)')
        self.nifty_plot.showGrid(x=True, y=True, alpha=0.3)
        self.nifty_plot.setMouseEnabled(x=True, y=True)
        
        # Create candlestick item
        self.candle_item = CandlestickItem()
        self.nifty_plot.addItem(self.candle_item)
        
        # Latest price text
        self.nifty_price_text = pg.TextItem(text="", anchor=(0, 0), color='#2c3e50')
        self.nifty_plot.addItem(self.nifty_price_text)
        
        # A/D Line Chart
        self.ad_plot = self.graphics_widget.addPlot(row=1, col=0, title="Advance-Decline Count")
        self.ad_plot.setLabel('left', 'Stock Count')
        self.ad_plot.setLabel('bottom', 'Time')
        self.ad_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ad_plot.addLegend()
        
        # A/D lines
        self.advances_line = self.ad_plot.plot(
            [], [], pen=pg.mkPen('#27ae60', width=2),
            symbol='o', symbolSize=5, symbolBrush='#27ae60',
            name='Advances'
        )
        self.declines_line = self.ad_plot.plot(
            [], [], pen=pg.mkPen('#e74c3c', width=2),
            symbol='s', symbolSize=5, symbolBrush='#e74c3c',
            name='Declines'
        )
        
        # NOTE: NOT linking X axes because NIFTY and A/D have different data sources
        # NIFTY comes from Yahoo Finance (full 1-min data)
        # A/D comes from our calculations (may have gaps)
        
        layout.addWidget(self.graphics_widget)
        
        return widget
    
    def create_right_panel(self):
        """Create right panel with metrics and controls"""
        widget = QWidget()
        widget.setMaximumWidth(450)
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Breadth Metrics
        metrics_group = QGroupBox("Market Breadth Metrics")
        metrics_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        metrics_layout = QGridLayout(metrics_group)
        
        # Advances
        self.advances_label = self.create_metric_display("ADVANCES", "0", "#27ae60")
        metrics_layout.addWidget(self.advances_label, 0, 0)
        
        # Declines
        self.declines_label = self.create_metric_display("DECLINES", "0", "#e74c3c")
        metrics_layout.addWidget(self.declines_label, 0, 1)
        
        # Unchanged
        self.unchanged_label = self.create_metric_display("UNCHANGED", "0", "#95a5a6")
        metrics_layout.addWidget(self.unchanged_label, 0, 2)
        
        # Additional metrics row
        self.ratio_label = QLabel("A/D Ratio: N/A")
        self.ratio_label.setFont(QFont("Arial", 10))
        metrics_layout.addWidget(self.ratio_label, 1, 0)
        
        self.diff_label = QLabel("A/D Diff: 0")
        self.diff_label.setFont(QFont("Arial", 10))
        metrics_layout.addWidget(self.diff_label, 1, 1)
        
        self.sentiment_label = QLabel("Sentiment: NEUTRAL")
        self.sentiment_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.sentiment_label.setStyleSheet("color: #f39c12")
        metrics_layout.addWidget(self.sentiment_label, 1, 2)
        
        layout.addWidget(metrics_group)
        
        # Top Movers
        movers_group = QGroupBox("Top Movers")
        movers_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        movers_layout = QVBoxLayout(movers_group)
        
        gainers_label = QLabel("Top 5 Gainers")
        gainers_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        movers_layout.addWidget(gainers_label)
        
        self.gainers_text = QTextEdit()
        self.gainers_text.setReadOnly(True)
        self.gainers_text.setMaximumHeight(100)
        self.gainers_text.setFont(QFont("Consolas", 9))
        movers_layout.addWidget(self.gainers_text)
        
        losers_label = QLabel("Top 5 Losers")
        losers_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        movers_layout.addWidget(losers_label)
        
        self.losers_text = QTextEdit()
        self.losers_text.setReadOnly(True)
        self.losers_text.setMaximumHeight(100)
        self.losers_text.setFont(QFont("Consolas", 9))
        movers_layout.addWidget(self.losers_text)
        
        layout.addWidget(movers_group)
        
        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        self.auto_refresh_check = QCheckBox("Auto-Refresh (5 min)")
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.stateChanged.connect(self.toggle_auto_refresh)
        controls_layout.addWidget(self.auto_refresh_check)
        
        self.refresh_btn = QPushButton("🔄 Refresh Now")
        self.refresh_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.refresh_btn.clicked.connect(self.fetch_data)
        controls_layout.addWidget(self.refresh_btn)
        
        self.countdown_label = QLabel("Next refresh in: --:--")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self.countdown_label)
        
        layout.addWidget(controls_group)
        
        # Status Log
        log_group = QGroupBox("Status Log")
        log_layout = QVBoxLayout(log_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(80)
        self.status_text.setFont(QFont("Consolas", 8))
        log_layout.addWidget(self.status_text)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        return widget
    
    def create_metric_display(self, title, value, color):
        """Create a metric display widget"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 9))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {color};")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        
        pct_label = QLabel("(0.00%)")
        pct_label.setFont(QFont("Arial", 9))
        pct_label.setStyleSheet(f"color: {color};")
        pct_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pct_label.setObjectName("pct")
        layout.addWidget(pct_label)
        
        return widget
    
    def log_status(self, message):
        """Log a status message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.status_text.append(f"[{timestamp}] {message}")
        # Keep only last 5 lines
        text = self.status_text.toPlainText()
        lines = text.split('\n')
        if len(lines) > 5:
            self.status_text.setPlainText('\n'.join(lines[-5:]))
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def update_market_status(self):
        """Update market status indicator"""
        if self.monitor.is_market_open():
            self.market_status_label.setText("Market: OPEN")
            self.market_status_label.setStyleSheet("color: #27ae60;")
        else:
            self.market_status_label.setText("Market: CLOSED")
            self.market_status_label.setStyleSheet("color: #e74c3c;")
    
    def load_2day_history(self):
        """Load historical data for today + last session only"""
        try:
            with self.engine.connect() as conn:
                # Get the last 2 trading days from database
                result = conn.execute(text("""
                    SELECT DISTINCT trade_date 
                    FROM intraday_advance_decline 
                    WHERE advances > 0 AND declines > 0
                    ORDER BY trade_date DESC 
                    LIMIT 2
                """))
                trading_days = [row[0] for row in result.fetchall()]
                
                if not trading_days:
                    self.log_status("No historical A/D data found")
                    return
                
                oldest_date = min(trading_days)
                
                # Load breadth snapshots for only these 2 days
                result = conn.execute(text("""
                    SELECT poll_time, advances, declines, unchanged
                    FROM intraday_advance_decline
                    WHERE trade_date >= :oldest_date
                      AND advances > 0 AND declines > 0
                    ORDER BY poll_time
                """), {'oldest_date': oldest_date})
                
                breadth_data = result.fetchall()
                self.log_status(f"Loaded {len(breadth_data)} breadth snapshots")
                
                if breadth_data:
                    history_list = []
                    for row in breadth_data:
                        poll_time = row[0]
                        if not poll_time.tzinfo:
                            poll_time = self.ist.localize(poll_time)
                        history_list.append({
                            'poll_time': poll_time,
                            'advances': row[1],
                            'declines': row[2],
                            'unchanged': row[3]
                        })
                    self.history_df = pd.DataFrame(history_list)
                    self.last_poll_time = self.history_df['poll_time'].max()
                    self.log_status(f"Last poll: {self.last_poll_time.strftime('%Y-%m-%d %H:%M')}")
        
        except Exception as e:
            self.log_status(f"❌ Error loading history: {e}")
    
    def fetch_data(self):
        """Fetch real-time data"""
        if self.worker and self.worker.isRunning():
            self.log_status("⚠️ Fetch already in progress...")
            return
        
        self.log_status(f"Fetching data for {len(self.symbols)} stocks...")
        self.refresh_btn.setEnabled(False)
        
        self.worker = DataFetchWorker(
            self.fetcher, self.calculator, self.symbols,
            self.candle_queue, self.ist
        )
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.status_update.connect(self.log_status)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.start()
    
    def on_fetch_finished(self, result):
        """Handle fetch completion"""
        self.refresh_btn.setEnabled(True)
        
        breadth = result['breadth']
        poll_time = result['poll_time']
        minute_ad_rows = result['minute_ad_rows']
        nifty_data = result['nifty_data']
        
        # Update last update time
        self.last_update_label.setText(f"Last Update: {datetime.now().strftime('%I:%M:%S %p')}")
        self.last_poll_time = poll_time
        
        # Update metrics display
        self.update_metrics(breadth)
        
        # Update top movers
        self.update_movers()
        
        # Update minute A/D data from candles
        if minute_ad_rows:
            new_df = pd.DataFrame(minute_ad_rows)
            self.minute_ad_df = pd.concat([self.minute_ad_df, new_df], ignore_index=True)
            self.minute_ad_df = self.minute_ad_df.drop_duplicates(subset=['candle_time'], keep='last')
            self.minute_ad_df = self.minute_ad_df.sort_values('candle_time')
            
            # Keep only last 2 trading days
            if 'candle_time' in self.minute_ad_df.columns and len(self.minute_ad_df) > 0:
                self.minute_ad_df['date'] = self.minute_ad_df['candle_time'].apply(
                    lambda x: x.date() if hasattr(x, 'date') else x
                )
                unique_dates = sorted(self.minute_ad_df['date'].unique(), reverse=True)[:2]
                self.minute_ad_df = self.minute_ad_df[self.minute_ad_df['date'].isin(unique_dates)]
                self.minute_ad_df = self.minute_ad_df.drop(columns=['date'])
        
        # IMPORTANT: Add current real-time breadth as the latest data point
        # This ensures the chart shows the most up-to-date A/D values
        current_minute = poll_time.replace(second=0, microsecond=0)
        current_row = pd.DataFrame([{
            'candle_time': current_minute,
            'advances': breadth['advances'],
            'declines': breadth['declines'],
            'unchanged': breadth['unchanged']
        }])
        self.minute_ad_df = pd.concat([self.minute_ad_df, current_row], ignore_index=True)
        self.minute_ad_df = self.minute_ad_df.drop_duplicates(subset=['candle_time'], keep='last')
        self.minute_ad_df = self.minute_ad_df.sort_values('candle_time')
        
        self.log_status(f"📊 minute_ad_df: {len(self.minute_ad_df)} rows")
        
        # Update charts
        self.update_charts()
        
        self.log_status("✅ Display updated successfully")
    
    def on_fetch_error(self, error_msg):
        """Handle fetch error"""
        self.refresh_btn.setEnabled(True)
        self.log_status(f"❌ {error_msg}")
    
    def update_metrics(self, breadth):
        """Update the metrics display"""
        # Advances
        adv_value = self.advances_label.findChild(QLabel, "value")
        adv_pct = self.advances_label.findChild(QLabel, "pct")
        if adv_value:
            adv_value.setText(str(breadth['advances']))
        if adv_pct:
            adv_pct.setText(f"({breadth['adv_pct']:.2f}%)")
        
        # Declines
        dec_value = self.declines_label.findChild(QLabel, "value")
        dec_pct = self.declines_label.findChild(QLabel, "pct")
        if dec_value:
            dec_value.setText(str(breadth['declines']))
        if dec_pct:
            dec_pct.setText(f"({breadth['decl_pct']:.2f}%)")
        
        # Unchanged
        unch_value = self.unchanged_label.findChild(QLabel, "value")
        unch_pct = self.unchanged_label.findChild(QLabel, "pct")
        if unch_value:
            unch_value.setText(str(breadth['unchanged']))
        if unch_pct:
            unch_pct.setText(f"({breadth['unch_pct']:.2f}%)")
        
        # Ratio and diff
        ratio = breadth.get('adv_decl_ratio')
        self.ratio_label.setText(f"A/D Ratio: {ratio:.2f}" if ratio else "A/D Ratio: N/A")
        
        diff = breadth.get('adv_decl_diff', 0)
        diff_color = '#27ae60' if diff > 0 else '#e74c3c' if diff < 0 else '#7f8c8d'
        self.diff_label.setText(f"A/D Diff: {diff:+d}")
        self.diff_label.setStyleSheet(f"color: {diff_color};")
        
        # Sentiment
        sentiment = breadth.get('market_sentiment', 'NEUTRAL')
        sentiment_colors = {
            'STRONG BULLISH': '#27ae60',
            'BULLISH': '#2ecc71',
            'NEUTRAL': '#f39c12',
            'BEARISH': '#e74c3c',
            'STRONG BEARISH': '#c0392b'
        }
        self.sentiment_label.setText(f"Sentiment: {sentiment}")
        self.sentiment_label.setStyleSheet(f"color: {sentiment_colors.get(sentiment, '#f39c12')};")
    
    def update_movers(self):
        """Update top gainers and losers"""
        # Gainers
        gainers = self.calculator.get_top_gainers(5)
        gainers_text = ""
        if gainers:
            for i, stock in enumerate(gainers, 1):
                symbol_short = stock.symbol.replace('.NS', '')
                gainers_text += f"{i}. {symbol_short:<12} ₹{stock.ltp:>8.2f}  {stock.change_pct:>+6.2f}%\n"
        else:
            gainers_text = "No data available"
        self.gainers_text.setPlainText(gainers_text)
        
        # Losers
        losers = self.calculator.get_top_losers(5)
        losers_text = ""
        if losers:
            for i, stock in enumerate(losers, 1):
                symbol_short = stock.symbol.replace('.NS', '')
                losers_text += f"{i}. {symbol_short:<12} ₹{stock.ltp:>8.2f}  {stock.change_pct:>+6.2f}%\n"
        else:
            losers_text = "No data available"
        self.losers_text.setPlainText(losers_text)
    
    def update_charts(self):
        """Update the PyQtGraph charts - shows today + last session only"""
        try:
            # Fetch NIFTY data from Yahoo Finance - only today + last session
            import yfinance as yf
            
            nifty_ticker = yf.Ticker("^NSEI")
            # Use 1d to get today's data, but we need last session too
            # So fetch 2d and filter to keep only last 2 trading days
            nifty_data = nifty_ticker.history(period="5d", interval="1m")
            
            if not nifty_data.empty:
                # Filter to only last 2 trading days (today + last session)
                nifty_data.index = pd.to_datetime(nifty_data.index)
                unique_dates = nifty_data.index.date
                trading_days = sorted(set(unique_dates), reverse=True)[:2]  # Last 2 trading days
                
                # Filter data to only these days
                mask = nifty_data.index.map(lambda x: x.date() in trading_days)
                nifty_data = nifty_data[mask]
                
                candles = []
                for i, (idx, row) in enumerate(nifty_data.iterrows()):
                    ts = idx.to_pydatetime()
                    if ts.tzinfo is None:
                        ts = self.ist.localize(ts)
                    else:
                        ts = ts.astimezone(self.ist)
                    candles.append((i, row['Open'], row['High'], row['Low'], row['Close']))
                
                self.nifty_candles = candles
                self.candle_item.setData(candles)
                
                # Update price text
                if candles:
                    last_close = candles[-1][4]
                    self.nifty_price_text.setText(f"Last: ₹{last_close:.2f}")
                    self.nifty_price_text.setPos(len(candles) - 1, max(c[2] for c in candles if c[2]))
                
                # Set axis range
                lows = [c[3] for c in candles if c[3] is not None]
                highs = [c[2] for c in candles if c[2] is not None]
                if lows and highs:
                    margin = (max(highs) - min(lows)) * 0.05
                    self.nifty_plot.setYRange(min(lows) - margin, max(highs) + margin)
                self.nifty_plot.setXRange(-1, len(candles) + 1)
                
                self.log_status(f"NIFTY candles: {len(candles)}")
            
            # Update A/D chart - filter to last 2 trading days only
            if not self.minute_ad_df.empty:
                df = self.minute_ad_df.copy()
                df = df.sort_values('candle_time')
                
                # Filter to only last 2 trading days (today + last session)
                if 'candle_time' in df.columns and len(df) > 0:
                    df['date'] = df['candle_time'].apply(lambda x: x.date() if hasattr(x, 'date') else x)
                    unique_dates = sorted(df['date'].unique(), reverse=True)[:2]
                    df = df[df['date'].isin(unique_dates)]
                    df = df.drop(columns=['date'])
                
                x = list(range(len(df)))
                advances = df['advances'].tolist()
                declines = df['declines'].tolist()
                
                self.advances_line.setData(x, advances)
                self.declines_line.setData(x, declines)
                
                self.ad_plot.setXRange(-1, len(x) + 1)
                
                # Update legend with latest values
                if advances and declines:
                    last_time = df['candle_time'].iloc[-1]
                    if hasattr(last_time, 'strftime'):
                        time_str = last_time.strftime('%H:%M')
                    else:
                        time_str = str(last_time)
                    self.ad_plot.setTitle(
                        f"Advance-Decline Count (Latest @ {time_str}: Adv={advances[-1]}, Dec={declines[-1]})"
                    )
        
        except Exception as e:
            self.log_status(f"Chart update error: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_auto_refresh(self, state):
        """Toggle auto-refresh"""
        self.auto_refresh = bool(state)
        if self.auto_refresh:
            self.start_polling()
        else:
            self.stop_polling()
    
    def start_polling(self):
        """Start auto-refresh polling"""
        self.countdown_remaining = self.polling_interval
        self.countdown_timer.start(1000)  # Every second
        self.log_status("Auto-refresh enabled (5 min interval)")
    
    def stop_polling(self):
        """Stop auto-refresh polling"""
        self.countdown_timer.stop()
        self.countdown_label.setText("Next refresh in: --:--")
        self.log_status("Auto-refresh disabled")
    
    def update_countdown(self):
        """Update countdown timer"""
        self.countdown_remaining -= 1
        
        if self.countdown_remaining <= 0:
            self.countdown_remaining = self.polling_interval
            if self.monitor.is_market_open():
                self.fetch_data()
            else:
                self.log_status("Market closed - skipping refresh")
        
        minutes, seconds = divmod(self.countdown_remaining, 60)
        self.countdown_label.setText(f"Next refresh in: {minutes:02d}:{seconds:02d}")
    
    def closeEvent(self, event):
        """Handle window close"""
        self.countdown_timer.stop()
        self.market_status_timer.stop()
        
        self.logger.stop(timeout=5)
        
        # Stop candle processor
        self.log_status("Stopping candle processor...")
        try:
            self.candle_queue.put(None)  # Poison pill
            self.candle_processor.join(timeout=5)
            if self.candle_processor.is_alive():
                self.candle_processor.terminate()
        except:
            pass
        
        self.engine.dispose()
        
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show window
    window = RealtimeAdvDeclDashboardPyQt()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
