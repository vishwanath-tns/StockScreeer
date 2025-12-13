#!/usr/bin/env python
"""
Buy/Sell Pressure Visualizer
=============================
Real-time visualization of total_buy_qty and total_sell_qty from FNO quotes.

Features:
- Chart 1: Buy Qty (green) and Sell Qty (red) lines
- Chart 2: Net Pressure (Buy - Sell) with positive/negative coloring
- Symbol selector dropdown
- Scrollable history for the day
- Real-time updates from Redis

Usage:
    python -m dhan_trading.visualizers.buy_sell_pressure
"""

import sys
import os
import time
import redis
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QLabel, QPushButton, QSplitter, QFrame, QCheckBox,
    QSpinBox, QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont

import pyqtgraph as pg
from pyqtgraph import DateAxisItem
import numpy as np

# Matplotlib for pie chart
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()


# Configure PyQtGraph
pg.setConfigOptions(antialias=True, background='k', foreground='w')


class QuoteHistory:
    """Store quote history for a single instrument."""
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.timestamps: deque = deque(maxlen=max_points)
        self.buy_qty: deque = deque(maxlen=max_points)
        self.sell_qty: deque = deque(maxlen=max_points)
        self.ltp: deque = deque(maxlen=max_points)
        self.volume: deque = deque(maxlen=max_points)
        self.last_update = 0
    
    def add_quote(self, timestamp: float, buy_qty: int, sell_qty: int, 
                  ltp: float = 0, volume: int = 0):
        """Add a new quote to history."""
        self.timestamps.append(timestamp)
        self.buy_qty.append(buy_qty)
        self.sell_qty.append(sell_qty)
        self.ltp.append(ltp)
        self.volume.append(volume)
        self.last_update = time.time()
    
    def get_arrays(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Get numpy arrays for plotting."""
        if not self.timestamps:
            empty = np.array([])
            return empty, empty, empty, empty, empty
        
        timestamps = np.array(self.timestamps)
        buy_qty = np.array(self.buy_qty)
        sell_qty = np.array(self.sell_qty)
        net_pressure = buy_qty - sell_qty
        ltp = np.array(self.ltp)
        
        return timestamps, buy_qty, sell_qty, net_pressure, ltp
    
    def __len__(self):
        return len(self.timestamps)


class RedisQuoteReader(QThread):
    """Background thread to read quotes from Redis."""
    
    quote_received = pyqtSignal(dict)  # Emits quote data
    connection_status = pyqtSignal(bool, str)  # connected, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._client = None
        self._pubsub = None
    
    def run(self):
        """Main thread loop - subscribe to Redis and emit quotes."""
        self._running = True
        
        try:
            self._client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self._client.ping()
            self.connection_status.emit(True, "Connected to Redis")
            
            # Subscribe to quotes channel
            self._pubsub = self._client.pubsub()
            self._pubsub.subscribe('dhan:quotes')
            
            while self._running:
                message = self._pubsub.get_message(timeout=0.1)
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        self.quote_received.emit(data)
                    except json.JSONDecodeError:
                        pass
                        
        except redis.ConnectionError as e:
            self.connection_status.emit(False, f"Redis connection failed: {e}")
        except Exception as e:
            self.connection_status.emit(False, f"Error: {e}")
        finally:
            if self._pubsub:
                self._pubsub.unsubscribe()
            self._running = False
    
    def stop(self):
        """Stop the reader thread."""
        self._running = False
        self.wait(2000)


class BuySellPressureVisualizer(QMainWindow):
    """Main visualizer window."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Buy/Sell Pressure Visualizer")
        self.setGeometry(100, 100, 1400, 900)
        
        # Data storage: security_id -> QuoteHistory
        self.history: Dict[int, QuoteHistory] = defaultdict(QuoteHistory)
        
        # Symbol mapping: security_id -> symbol name
        self.symbols: Dict[int, str] = {}
        
        # Currently selected instrument
        self.selected_security_id: Optional[int] = None
        
        # Quote reader thread
        self.quote_reader = RedisQuoteReader()
        self.quote_reader.quote_received.connect(self.on_quote_received)
        self.quote_reader.connection_status.connect(self.on_connection_status)
        
        # Stats
        self.quote_count = 0
        self.last_quote_time = None
        
        # Setup UI
        self._setup_ui()
        
        # Load instrument names from database
        self._load_instruments()
        
        # Start Redis reader
        self.quote_reader.start()
        
        # Update timer for charts
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_charts)
        self.update_timer.start(200)  # Update every 200ms
        
        # Stats update timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)
    
    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Top controls
        controls = QHBoxLayout()
        
        # Symbol selector
        controls.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setMinimumWidth(300)
        self.symbol_combo.currentIndexChanged.connect(self.on_symbol_changed)
        controls.addWidget(self.symbol_combo)
        
        # Auto-scroll checkbox
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        controls.addWidget(self.auto_scroll_check)
        
        # Points to show
        controls.addWidget(QLabel("Points:"))
        self.points_spin = QSpinBox()
        self.points_spin.setRange(100, 10000)
        self.points_spin.setValue(500)
        self.points_spin.setSingleStep(100)
        controls.addWidget(self.points_spin)
        
        controls.addStretch()
        
        # Connection status
        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        controls.addWidget(self.status_label)
        
        # Quote count
        self.count_label = QLabel("Quotes: 0")
        controls.addWidget(self.count_label)
        
        layout.addLayout(controls)
        
        # Main content area: Pie chart on left, line charts on right
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Pie chart for Buy/Sell quantities
        pie_frame = QFrame()
        pie_frame.setFrameStyle(QFrame.StyledPanel)
        pie_layout = QVBoxLayout(pie_frame)
        pie_layout.setContentsMargins(5, 5, 5, 5)
        
        pie_title = QLabel("Buy vs Sell Quantity")
        pie_title.setAlignment(Qt.AlignCenter)
        pie_title.setFont(QFont("Arial", 12, QFont.Bold))
        pie_title.setStyleSheet("color: white;")
        pie_layout.addWidget(pie_title)
        
        # Matplotlib pie chart
        self.pie_figure = Figure(figsize=(4, 4), facecolor='#1e1e1e')
        self.pie_canvas = FigureCanvas(self.pie_figure)
        self.pie_canvas.setMinimumWidth(300)
        self.pie_ax = self.pie_figure.add_subplot(111)
        self.pie_ax.set_facecolor('#1e1e1e')
        self._init_pie_chart()
        pie_layout.addWidget(self.pie_canvas)
        
        # Pie chart stats below
        self.pie_buy_label = QLabel("Buy: --")
        self.pie_buy_label.setStyleSheet("color: #00ff00; font-size: 14px; font-weight: bold;")
        self.pie_buy_label.setAlignment(Qt.AlignCenter)
        pie_layout.addWidget(self.pie_buy_label)
        
        self.pie_sell_label = QLabel("Sell: --")
        self.pie_sell_label.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold;")
        self.pie_sell_label.setAlignment(Qt.AlignCenter)
        pie_layout.addWidget(self.pie_sell_label)
        
        self.pie_ratio_label = QLabel("Ratio: --")
        self.pie_ratio_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.pie_ratio_label.setAlignment(Qt.AlignCenter)
        pie_layout.addWidget(self.pie_ratio_label)
        
        main_splitter.addWidget(pie_frame)
        
        # Right side: Line charts (vertical splitter)
        charts_splitter = QSplitter(Qt.Vertical)
        
        # Chart 1: LTP (Price) - Line chart
        self.ltp_chart = pg.PlotWidget(
            title="Last Traded Price (LTP)",
            axisItems={'bottom': DateAxisItem()}
        )
        self.ltp_chart.showGrid(x=True, y=True, alpha=0.3)
        self.ltp_chart.setLabel('left', 'Price')
        self.ltp_chart.setLabel('bottom', 'Time')
        
        # LTP line - yellow/gold color
        self.ltp_line = self.ltp_chart.plot(
            [], [], pen=pg.mkPen('#FFD700', width=2), name='LTP'
        )
        
        charts_splitter.addWidget(self.ltp_chart)
        
        # Chart 2: Net Pressure (Buy - Sell) - Line chart
        self.net_chart = pg.PlotWidget(
            title="Net Pressure (Buy - Sell)",
            axisItems={'bottom': DateAxisItem()}
        )
        self.net_chart.showGrid(x=True, y=True, alpha=0.3)
        self.net_chart.setLabel('left', 'Net Qty')
        self.net_chart.setLabel('bottom', 'Time')
        
        # Add zero line
        self.zero_line = pg.InfiniteLine(
            pos=0, angle=0, pen=pg.mkPen('w', width=1, style=Qt.DashLine)
        )
        self.net_chart.addItem(self.zero_line)
        
        # Net pressure line - cyan, with fill
        self.net_line = self.net_chart.plot(
            [], [], pen=pg.mkPen('#00ffff', width=2), name='Net Pressure'
        )
        # Fill between line and zero
        self.net_fill_pos = self.net_chart.plot([], [], pen=None, fillLevel=0, brush=pg.mkBrush(0, 255, 0, 80))
        self.net_fill_neg = self.net_chart.plot([], [], pen=None, fillLevel=0, brush=pg.mkBrush(255, 0, 0, 80))
        
        charts_splitter.addWidget(self.net_chart)
        
        # Link X axes for synchronized scrolling
        self.net_chart.setXLink(self.ltp_chart)
        
        main_splitter.addWidget(charts_splitter)
        
        # Set splitter proportions (pie chart smaller)
        main_splitter.setSizes([300, 900])
        
        layout.addWidget(main_splitter)
        
        # Bottom stats panel
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel)
        stats_layout = QHBoxLayout(stats_frame)
        
        self.ltp_label = QLabel("LTP: --")
        self.ltp_label.setFont(QFont("Consolas", 14, QFont.Bold))
        stats_layout.addWidget(self.ltp_label)
        
        self.buy_label = QLabel("Buy Qty: --")
        self.buy_label.setStyleSheet("color: #00ff00;")
        self.buy_label.setFont(QFont("Consolas", 12))
        stats_layout.addWidget(self.buy_label)
        
        self.sell_label = QLabel("Sell Qty: --")
        self.sell_label.setStyleSheet("color: #ff4444;")
        self.sell_label.setFont(QFont("Consolas", 12))
        stats_layout.addWidget(self.sell_label)
        
        self.net_label = QLabel("Net: --")
        self.net_label.setFont(QFont("Consolas", 12, QFont.Bold))
        stats_layout.addWidget(self.net_label)
        
        self.volume_label = QLabel("Volume: --")
        self.volume_label.setFont(QFont("Consolas", 12))
        stats_layout.addWidget(self.volume_label)
        
        stats_layout.addStretch()
        
        self.time_label = QLabel("Last Update: --")
        stats_layout.addWidget(self.time_label)
        
        layout.addWidget(stats_frame)
    
    def _load_instruments(self):
        """Load instrument names from database."""
        try:
            from sqlalchemy import create_engine, text
            from urllib.parse import quote_plus
            
            pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
            engine = create_engine(
                f"mysql+pymysql://root:{pw}@localhost:3306/dhan_trading"
            )
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT security_id, symbol, display_name 
                    FROM dhan_instruments 
                    WHERE exchange_segment IN ('NSE_FNO', 'MCX_COMM')
                """))
                
                for row in result:
                    sec_id = int(row[0])
                    symbol = row[1] or ''
                    display = row[2] or symbol
                    self.symbols[sec_id] = f"{display} ({sec_id})"
            
            print(f"Loaded {len(self.symbols)} instrument names")
            
        except Exception as e:
            print(f"Could not load instruments: {e}")
    
    def _init_pie_chart(self):
        """Initialize the pie chart with default values."""
        self.pie_ax.clear()
        self.pie_ax.set_facecolor('#1e1e1e')
        
        # Initial pie with equal values
        sizes = [50, 50]
        colors = ['#00ff00', '#ff4444']
        labels = ['Buy', 'Sell']
        
        wedges, texts, autotexts = self.pie_ax.pie(
            sizes, 
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'color': 'white', 'fontsize': 10}
        )
        
        # Style the percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')
        
        self.pie_ax.axis('equal')
        self.pie_figure.tight_layout()
        self.pie_canvas.draw()
    
    def _update_pie_chart(self, buy_qty: int, sell_qty: int):
        """Update the pie chart with current buy/sell quantities."""
        self.pie_ax.clear()
        self.pie_ax.set_facecolor('#1e1e1e')
        
        total = buy_qty + sell_qty
        if total == 0:
            sizes = [50, 50]
        else:
            sizes = [buy_qty, sell_qty]
        
        colors = ['#00ff00', '#ff4444']
        labels = ['Buy', 'Sell']
        
        wedges, texts, autotexts = self.pie_ax.pie(
            sizes, 
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'color': 'white', 'fontsize': 10},
            explode=(0.02, 0.02)  # Slight separation
        )
        
        # Style the percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')
        
        self.pie_ax.axis('equal')
        self.pie_figure.tight_layout()
        self.pie_canvas.draw()
        
        # Update pie labels
        self.pie_buy_label.setText(f"Buy: {buy_qty:,}")
        self.pie_sell_label.setText(f"Sell: {sell_qty:,}")
        
        if sell_qty > 0:
            ratio = buy_qty / sell_qty
            self.pie_ratio_label.setText(f"Buy/Sell Ratio: {ratio:.2f}")
        else:
            self.pie_ratio_label.setText("Buy/Sell Ratio: --")
    
    def on_quote_received(self, data: dict):
        """Handle incoming quote from Redis."""
        self.quote_count += 1
        self.last_quote_time = datetime.now()
        
        security_id = data.get('security_id')
        if not security_id:
            return
        
        security_id = int(security_id)
        
        # Get quote fields
        buy_qty = int(data.get('total_buy_qty', 0))
        sell_qty = int(data.get('total_sell_qty', 0))
        ltp = float(data.get('ltp', 0))
        volume = int(data.get('volume', 0))
        ltt = int(data.get('ltt', 0))
        
        # Use LTT as timestamp, or current time if invalid
        if ltt > 1000000000:  # Valid unix timestamp
            timestamp = ltt
        else:
            timestamp = time.time()
        
        # Add to history
        self.history[security_id].add_quote(timestamp, buy_qty, sell_qty, ltp, volume)
        
        # Add to symbol combo if new
        if security_id not in [self.symbol_combo.itemData(i) 
                               for i in range(self.symbol_combo.count())]:
            display_name = self.symbols.get(security_id, f"ID: {security_id}")
            self.symbol_combo.addItem(display_name, security_id)
            
            # Auto-select first instrument
            if self.selected_security_id is None:
                self.selected_security_id = security_id
                self.symbol_combo.setCurrentIndex(0)
    
    def on_symbol_changed(self, index):
        """Handle symbol selection change."""
        if index >= 0:
            self.selected_security_id = self.symbol_combo.itemData(index)
            self.update_charts()
    
    def on_connection_status(self, connected: bool, message: str):
        """Handle connection status updates."""
        if connected:
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        else:
            self.status_label.setText(f"● {message}")
            self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
    
    def update_charts(self):
        """Update chart data."""
        if self.selected_security_id is None:
            return
        
        history = self.history.get(self.selected_security_id)
        if not history or len(history) == 0:
            return
        
        timestamps, buy_qty, sell_qty, net_pressure, ltp = history.get_arrays()
        
        # Limit points shown
        max_points = self.points_spin.value()
        if len(timestamps) > max_points:
            timestamps = timestamps[-max_points:]
            buy_qty = buy_qty[-max_points:]
            sell_qty = sell_qty[-max_points:]
            net_pressure = net_pressure[-max_points:]
            ltp = ltp[-max_points:]
        
        # Update LTP Chart - line chart
        self.ltp_line.setData(timestamps, ltp)
        
        # Update Net Pressure Chart - line with fill
        # Main line
        self.net_line.setData(timestamps, net_pressure)
        
        # Create positive and negative fill data
        if len(timestamps) > 0:
            pos_pressure = np.where(net_pressure >= 0, net_pressure, 0)
            neg_pressure = np.where(net_pressure < 0, net_pressure, 0)
            self.net_fill_pos.setData(timestamps, pos_pressure)
            self.net_fill_neg.setData(timestamps, neg_pressure)
        
        # Update Pie Chart with latest values
        if len(history) > 0:
            latest_buy = int(history.buy_qty[-1])
            latest_sell = int(history.sell_qty[-1])
            self._update_pie_chart(latest_buy, latest_sell)
        
        # Auto-scroll to latest
        if self.auto_scroll_check.isChecked() and len(timestamps) > 0:
            # Show last portion of data
            x_range = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 60
            view_width = min(x_range, 300)  # Show last 5 minutes max
            self.ltp_chart.setXRange(timestamps[-1] - view_width, timestamps[-1])
        
        # Update stats
        if len(history) > 0:
            latest_buy = history.buy_qty[-1]
            latest_sell = history.sell_qty[-1]
            latest_ltp = history.ltp[-1]
            latest_vol = history.volume[-1]
            net = latest_buy - latest_sell
            
            self.ltp_label.setText(f"LTP: {latest_ltp:,.2f}")
            self.buy_label.setText(f"Buy Qty: {latest_buy:,}")
            self.sell_label.setText(f"Sell Qty: {latest_sell:,}")
            self.volume_label.setText(f"Volume: {latest_vol:,}")
            
            if net >= 0:
                self.net_label.setText(f"Net: +{net:,}")
                self.net_label.setStyleSheet("color: #00ff00; font-weight: bold;")
            else:
                self.net_label.setText(f"Net: {net:,}")
                self.net_label.setStyleSheet("color: #ff4444; font-weight: bold;")
    
    def update_stats(self):
        """Update statistics display."""
        self.count_label.setText(f"Quotes: {self.quote_count:,}")
        
        if self.last_quote_time:
            self.time_label.setText(
                f"Last Update: {self.last_quote_time.strftime('%H:%M:%S')}"
            )
    
    def closeEvent(self, event):
        """Handle window close."""
        self.quote_reader.stop()
        self.update_timer.stop()
        self.stats_timer.stop()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Dark theme
    app.setStyle('Fusion')
    
    # Dark palette
    from PyQt5.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.AlternateBase, QColor(60, 60, 60))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = BuySellPressureVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
