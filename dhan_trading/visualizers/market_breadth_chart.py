"""
Nifty 50 Market Breadth Chart
=============================
Real-time chart showing advances and declines count over time.

Features:
- Two lines: Green for advances, Red for declines
- Updates every second with current breadth
- Shows historical breadth for the session
- Displays current A/D ratio and counts
- Stores breadth history to database
- Scrollable chart to view past data

Usage:
    python -m dhan_trading.visualizers.market_breadth_chart
"""
import os
import sys
import signal
import logging
from datetime import datetime, date, time as dt_time
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from collections import deque
from urllib.parse import quote_plus

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QStatusBar, QSizePolicy, QSplitter, QScrollArea,
    QPushButton, QSlider, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPalette, QPainterPath

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.redis_subscriber import RedisSubscriber, CHANNEL_QUOTES
from dhan_trading.market_feed.redis_publisher import QuoteData
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Market timing
MARKET_OPEN_TIME = dt_time(9, 15)
MARKET_CLOSE_TIME = dt_time(15, 30)

# Chart settings
MAX_VISIBLE_POINTS = 300  # Points visible at once
DEFAULT_VISIBLE_POINTS = 120  # Default view (~2 minutes)


@dataclass
class BreadthPoint:
    """A single data point for the breadth chart."""
    timestamp: datetime
    advances: int
    declines: int
    unchanged: int


@dataclass
class StockState:
    """Track state of a single stock."""
    security_id: int
    symbol: str
    display_name: str = ""
    ltp: float = 0.0
    day_close: float = 0.0
    change_pct: float = 0.0
    status: str = "unchanged"  # "advance", "decline", "unchanged"
    
    def update(self, ltp: float, day_close: float) -> bool:
        """Update and return True if status changed."""
        self.ltp = ltp
        if day_close > 0:
            self.day_close = day_close
        
        old_status = self.status
        if self.day_close > 0:
            self.change_pct = ((self.ltp - self.day_close) / self.day_close) * 100
            if self.ltp > self.day_close:
                self.status = "advance"
            elif self.ltp < self.day_close:
                self.status = "decline"
            else:
                self.status = "unchanged"
        
        return self.status != old_status


class StockListWidget(QWidget):
    """Widget showing list of stocks with their status."""
    
    def __init__(self, title: str, color: QColor, parent=None):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.stocks: List[StockState] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Title
        self.title_label = QLabel(f"{self.title} (0)")
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.color.name()};
                font-size: 14px;
                font-weight: bold;
                padding: 3px;
            }}
        """)
        layout.addWidget(self.title_label)
        
        # Scroll area for stocks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e2e;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        
        self.stocks_container = QWidget()
        self.stocks_layout = QVBoxLayout(self.stocks_container)
        self.stocks_layout.setContentsMargins(3, 3, 3, 3)
        self.stocks_layout.setSpacing(2)
        self.stocks_layout.addStretch()
        
        scroll.setWidget(self.stocks_container)
        layout.addWidget(scroll)
    
    def update_stocks(self, stocks: List[StockState]):
        """Update the stock list."""
        # Sort by change_pct (descending for advances, ascending for declines)
        is_advances = "Advances" in self.title
        self.stocks = sorted(stocks, key=lambda x: x.change_pct, reverse=is_advances)
        self.title_label.setText(f"{self.title} ({len(stocks)})")
        
        # Clear existing items
        while self.stocks_layout.count() > 1:
            item = self.stocks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add stock items
        for stock in self.stocks:
            item = self._create_stock_item(stock)
            self.stocks_layout.insertWidget(self.stocks_layout.count() - 1, item)
    
    def _create_stock_item(self, stock: StockState) -> QWidget:
        """Create a widget for a single stock."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d44;
                border-radius: 3px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Symbol
        name = stock.display_name if stock.display_name else stock.symbol
        symbol_label = QLabel(name[:18])
        symbol_label.setStyleSheet("color: white; font-size: 11px;")
        symbol_label.setMinimumWidth(100)
        layout.addWidget(symbol_label)
        
        # LTP
        ltp_label = QLabel(f"₹{stock.ltp:,.2f}")
        ltp_label.setStyleSheet("color: #FFFF00; font-size: 11px;")
        ltp_label.setMinimumWidth(70)
        layout.addWidget(ltp_label)
        
        # Change %
        change_color = "#00C853" if stock.change_pct >= 0 else "#FF5252"
        sign = "+" if stock.change_pct >= 0 else ""
        change_label = QLabel(f"{sign}{stock.change_pct:.2f}%")
        change_label.setStyleSheet(f"color: {change_color}; font-size: 11px; font-weight: bold;")
        change_label.setMinimumWidth(55)
        layout.addWidget(change_label)
        
        return frame


class BreadthChartWidget(QWidget):
    """Widget that draws the breadth line chart with scroll support."""
    
    # Signal emitted when scroll position changes (offset, total_points, visible_range_start_time, visible_range_end_time)
    scroll_changed = pyqtSignal(int, int, str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_points: List[BreadthPoint] = []  # All data points (no limit)
        self.visible_points = DEFAULT_VISIBLE_POINTS  # How many points to show
        self.scroll_offset = 0  # 0 = latest data, positive = looking at older data
        self.auto_scroll = True  # Auto-scroll to latest
        self.setMinimumSize(600, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Colors
        self.advance_color = QColor(0, 200, 83)  # Green
        self.decline_color = QColor(255, 82, 82)  # Red
        self.grid_color = QColor(60, 60, 80)
        self.text_color = QColor(200, 200, 200)
        self.bg_color = QColor(26, 26, 46)
        
        # Enable mouse tracking for scroll
        self.setMouseTracking(True)
        
    def add_point(self, advances: int, declines: int, unchanged: int):
        """Add a new data point."""
        self.data_points.append(BreadthPoint(
            timestamp=datetime.now(),
            advances=advances,
            declines=declines,
            unchanged=unchanged
        ))
        if self.auto_scroll:
            self.scroll_offset = 0
        self.update()
    
    def load_historical(self, points: List[BreadthPoint]):
        """Load historical data points."""
        self.data_points = points + self.data_points
        self.update()
    
    def set_visible_points(self, count: int):
        """Set number of visible points."""
        self.visible_points = max(30, min(count, MAX_VISIBLE_POINTS))
        self.update()
    
    def scroll_to(self, offset: int):
        """Scroll to a specific offset (0 = latest)."""
        max_offset = max(0, len(self.data_points) - self.visible_points)
        self.scroll_offset = max(0, min(offset, max_offset))
        self.auto_scroll = (self.scroll_offset == 0)
        self._emit_scroll_changed()
        self.update()
    
    def scroll_by(self, delta: int):
        """Scroll by delta points."""
        self.scroll_to(self.scroll_offset + delta)
    
    def go_to_latest(self):
        """Jump to latest data."""
        self.scroll_offset = 0
        self.auto_scroll = True
        self._emit_scroll_changed()
        self.update()
    
    def _emit_scroll_changed(self):
        """Emit scroll_changed signal with current position info."""
        visible = self.get_visible_data()
        if visible:
            start_time = visible[0].timestamp.strftime("%H:%M:%S")
            end_time = visible[-1].timestamp.strftime("%H:%M:%S")
        else:
            start_time = "--:--:--"
            end_time = "--:--:--"
        self.scroll_changed.emit(self.scroll_offset, len(self.data_points), start_time, end_time)
    
    def wheelEvent(self, event):
        """Handle mouse wheel for scrolling."""
        delta = event.angleDelta().y()
        if delta > 0:
            self.scroll_by(10)  # Scroll back in time
        else:
            self.scroll_by(-10)  # Scroll forward
        event.accept()
    
    def get_visible_data(self) -> List[BreadthPoint]:
        """Get the currently visible data points."""
        if not self.data_points:
            return []
        
        end_idx = len(self.data_points) - self.scroll_offset
        start_idx = max(0, end_idx - self.visible_points)
        return self.data_points[start_idx:end_idx]
        
    def paintEvent(self, event):
        """Draw the chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background
        painter.fillRect(0, 0, width, height, self.bg_color)
        
        # Chart area with margins
        margin_left = 50
        margin_right = 20
        margin_top = 30
        margin_bottom = 40
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        if chart_width <= 0 or chart_height <= 0:
            return
        
        # Draw title
        painter.setPen(QPen(QColor(0, 229, 255)))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(margin_left, 22, "Nifty 50 Advances vs Declines")
        
        # Find max value for Y axis (max 50 for Nifty 50)
        max_val = 50
        
        # Draw grid lines
        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        num_grid_lines = 5
        for i in range(num_grid_lines + 1):
            y = margin_top + (chart_height * i / num_grid_lines)
            painter.drawLine(margin_left, int(y), width - margin_right, int(y))
            
            # Y axis labels
            value = max_val - (max_val * i / num_grid_lines)
            painter.setPen(QPen(self.text_color))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(5, int(y) + 4, f"{int(value)}")
            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        
        # Draw chart border
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.drawRect(margin_left, margin_top, chart_width, chart_height)
        
        # Draw data lines
        if len(self.data_points) < 2:
            # Show "Waiting for data" message
            painter.setPen(QPen(self.text_color))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(
                margin_left + chart_width // 2 - 80,
                margin_top + chart_height // 2,
                "Waiting for data..."
            )
            return
        
        # Get visible data
        visible_data = self.get_visible_data()
        if len(visible_data) < 2:
            return
        
        # Calculate x spacing based on visible points
        x_step = chart_width / (self.visible_points - 1) if self.visible_points > 1 else chart_width
        
        # Draw advances line (green)
        self._draw_line(painter, margin_left, margin_top, chart_width, chart_height, 
                       x_step, max_val, visible_data, "advances", self.advance_color)
        
        # Draw declines line (red)
        self._draw_line(painter, margin_left, margin_top, chart_width, chart_height,
                       x_step, max_val, visible_data, "declines", self.decline_color)
        
        # Draw legend
        legend_x = width - margin_right - 150
        legend_y = margin_top + 15
        
        # Advances legend
        painter.setPen(QPen(self.advance_color, 3))
        painter.drawLine(legend_x, legend_y, legend_x + 25, legend_y)
        painter.setPen(QPen(self.text_color))
        painter.setFont(QFont("Arial", 10))
        if visible_data:
            painter.drawText(legend_x + 30, legend_y + 4, f"Advances ({visible_data[-1].advances})")
        
        # Declines legend
        legend_y += 20
        painter.setPen(QPen(self.decline_color, 3))
        painter.drawLine(legend_x, legend_y, legend_x + 25, legend_y)
        painter.setPen(QPen(self.text_color))
        if visible_data:
            painter.drawText(legend_x + 30, legend_y + 4, f"Declines ({visible_data[-1].declines})")
        
        # Draw time labels on X axis
        painter.setPen(QPen(self.text_color))
        painter.setFont(QFont("Arial", 8))
        
        if len(visible_data) > 1:
            # Show first and last timestamps of visible data
            first_time = visible_data[0].timestamp.strftime("%H:%M:%S")
            last_time = visible_data[-1].timestamp.strftime("%H:%M:%S")
            
            painter.drawText(margin_left, height - 10, first_time)
            painter.drawText(width - margin_right - 50, height - 10, last_time)
        
        # Draw scroll indicator if not at latest
        if self.scroll_offset > 0:
            painter.setPen(QPen(QColor(255, 200, 0)))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(margin_left + chart_width // 2 - 60, height - 10, 
                           f"◄ {self.scroll_offset}s ago | Scroll or click 'Live' ►")
    
    def _draw_line(self, painter: QPainter, margin_left: int, margin_top: int,
                   chart_width: int, chart_height: int, x_step: float, 
                   max_val: int, data: List[BreadthPoint], field: str, color: QColor):
        """Draw a single data line."""
        if len(data) < 2:
            return
        
        path = QPainterPath()
        
        for i, point in enumerate(data):
            value = getattr(point, field)
            x = margin_left + i * x_step
            y = margin_top + chart_height - (value / max_val * chart_height)
            
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        painter.setPen(QPen(color, 2))
        painter.drawPath(path)


class BreadthSubscriber(RedisSubscriber):
    """Redis subscriber for market breadth."""
    
    def __init__(self, callback, config=None):
        super().__init__(config)
        self._callback = callback
    
    def on_quote(self, quote: QuoteData):
        """Forward quote to callback."""
        if self._callback:
            self._callback(quote)
    
    def start(self):
        """Connect, subscribe, and start listening."""
        if self.connect():
            self.subscribe([CHANNEL_QUOTES])
            self.run(blocking=False)


class SignalEmitter(QObject):
    """Signal emitter for thread-safe UI updates."""
    quote_received = pyqtSignal(object)


class MarketBreadthChart(QMainWindow):
    """Main window for market breadth chart."""
    
    def __init__(self):
        super().__init__()
        
        self.signals = SignalEmitter()
        self.signals.quote_received.connect(self._on_quote)
        
        # Stock tracking
        self.nifty50_stocks: Dict[int, StockState] = {}
        self.advances: Set[int] = set()
        self.declines: Set[int] = set()
        self.unchanged: Set[int] = set()
        
        # Load Nifty 50 stocks
        self._load_nifty50_stocks()
        
        # Setup UI
        self._setup_ui()
        
        # Redis subscriber
        self._subscriber = None
        self._start_subscriber()
        
        # Chart update timer (every 1 second)
        self._chart_timer = QTimer()
        self._chart_timer.timeout.connect(self._update_chart)
        self._chart_timer.start(1000)
        
        # Stats update timer (faster for responsive UI)
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(200)
        
        # Stats
        self.quote_count = 0
        self.last_quote_time = None
    
    def _load_nifty50_stocks(self):
        """Load Nifty 50 stocks from instrument selector."""
        try:
            selector = InstrumentSelector()
            stocks = selector.get_nifty50_stocks()
            
            for inst in stocks:
                sec_id = inst['security_id']
                self.nifty50_stocks[sec_id] = StockState(
                    security_id=sec_id,
                    symbol=inst.get('underlying_symbol', inst['symbol']),
                    display_name=inst.get('display_name', inst['symbol'])
                )
                self.unchanged.add(sec_id)
            
            logger.info(f"Loaded {len(self.nifty50_stocks)} Nifty 50 stocks")
        except Exception as e:
            logger.error(f"Failed to load Nifty 50 stocks: {e}")
    
    def _setup_ui(self):
        """Setup the UI."""
        self.setWindowTitle("📈 Nifty 50 Market Breadth Chart")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QLabel {
                color: white;
            }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Stats row at top
        stats_frame = self._create_stats_frame()
        main_layout.addWidget(stats_frame)
        
        # Horizontal splitter for chart and stock lists
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Chart widget (left side)
        self.chart_widget = BreadthChartWidget()
        self.chart_widget.setMinimumWidth(600)
        self.chart_widget.scroll_changed.connect(self._on_scroll_changed)
        h_splitter.addWidget(self.chart_widget)
        
        # Stock lists panel (right side)
        lists_panel = QWidget()
        lists_layout = QVBoxLayout(lists_panel)
        lists_layout.setContentsMargins(0, 0, 0, 0)
        lists_layout.setSpacing(5)
        
        # Vertical splitter for advances and declines lists
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Advances list
        self.advances_list = StockListWidget("▲ Advances", QColor(0, 200, 83))
        v_splitter.addWidget(self.advances_list)
        
        # Declines list
        self.declines_list = StockListWidget("▼ Declines", QColor(255, 82, 82))
        v_splitter.addWidget(self.declines_list)
        
        v_splitter.setSizes([350, 350])
        lists_layout.addWidget(v_splitter)
        
        lists_panel.setMinimumWidth(280)
        lists_panel.setMaximumWidth(350)
        h_splitter.addWidget(lists_panel)
        
        # Set splitter sizes (70% chart, 30% lists)
        h_splitter.setSizes([800, 300])
        h_splitter.setStretchFactor(0, 1)  # Chart stretches
        h_splitter.setStretchFactor(1, 0)  # Lists don't stretch
        
        main_layout.addWidget(h_splitter, stretch=1)
        
        # Navigation controls
        nav_frame = self._create_nav_controls()
        main_layout.addWidget(nav_frame)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #888;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Connecting to Redis...")
    
    def _create_nav_controls(self) -> QWidget:
        """Create navigation controls for chart scrolling."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #2d4a7c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d5a8c;
            }
            QPushButton:pressed {
                background-color: #1d3a6c;
            }
            QSlider::groove:horizontal {
                background: #444;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00E5FF;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
        """)
        frame.setMaximumHeight(50)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # Scroll back button
        btn_back = QPushButton("◄◄ -1min")
        btn_back.clicked.connect(lambda: self.chart_widget.scroll_by(60))
        layout.addWidget(btn_back)
        
        btn_back_10 = QPushButton("◄ -10s")
        btn_back_10.clicked.connect(lambda: self.chart_widget.scroll_by(10))
        layout.addWidget(btn_back_10)
        
        # Time position label
        self.time_pos_label = QLabel("Position: Live")
        self.time_pos_label.setStyleSheet("color: #00E5FF; font-size: 12px;")
        layout.addWidget(self.time_pos_label)
        
        # Scroll forward button
        btn_fwd_10 = QPushButton("► +10s")
        btn_fwd_10.clicked.connect(lambda: self.chart_widget.scroll_by(-10))
        layout.addWidget(btn_fwd_10)
        
        btn_fwd = QPushButton("►► +1min")
        btn_fwd.clicked.connect(lambda: self.chart_widget.scroll_by(-60))
        layout.addWidget(btn_fwd)
        
        layout.addStretch()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: white;")
        layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(30)
        self.zoom_slider.setMaximum(MAX_VISIBLE_POINTS)
        self.zoom_slider.setValue(DEFAULT_VISIBLE_POINTS)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel(f"{DEFAULT_VISIBLE_POINTS}s")
        self.zoom_label.setStyleSheet("color: white; min-width: 40px;")
        layout.addWidget(self.zoom_label)
        
        layout.addStretch()
        
        # Live button
        self.live_btn = QPushButton("🔴 LIVE")
        self.live_btn.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.live_btn.clicked.connect(self._go_to_live)
        layout.addWidget(self.live_btn)
        
        # Data points info
        self.data_info_label = QLabel("Data: 0 points")
        self.data_info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.data_info_label)
        
        return frame
    
    def _on_zoom_changed(self, value: int):
        """Handle zoom slider change."""
        self.chart_widget.set_visible_points(value)
        self.zoom_label.setText(f"{value}s")
    
    def _go_to_live(self):
        """Go to live data."""
        self.chart_widget.go_to_latest()
    
    def _on_scroll_changed(self, offset: int, total_points: int, start_time: str, end_time: str):
        """Handle scroll position change."""
        if offset == 0:
            self.time_pos_label.setText("Position: 🔴 LIVE")
            self.time_pos_label.setStyleSheet("color: #00E5FF; font-size: 12px; font-weight: bold;")
            self.live_btn.setEnabled(False)
        else:
            self.time_pos_label.setText(f"Viewing: {start_time} - {end_time} ({offset}s ago)")
            self.time_pos_label.setStyleSheet("color: #FFD700; font-size: 12px;")
            self.live_btn.setEnabled(True)
        
        # Update data info label
        self.data_info_label.setText(f"Data: {total_points} points")
    
    def _create_stats_frame(self) -> QWidget:
        """Create stats frame."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        frame.setMaximumHeight(80)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(30)
        
        # Advances
        self.adv_label = QLabel("▲ Advances: 0")
        self.adv_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #00C853;")
        layout.addWidget(self.adv_label)
        
        # Unchanged
        self.unc_label = QLabel("● Unchanged: 0")
        self.unc_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #888;")
        layout.addWidget(self.unc_label)
        
        # Declines
        self.dec_label = QLabel("▼ Declines: 0")
        self.dec_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF5252;")
        layout.addWidget(self.dec_label)
        
        layout.addStretch()
        
        # A/D Ratio
        self.ratio_label = QLabel("A/D Ratio: --")
        self.ratio_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(self.ratio_label)
        
        # Last update
        self.time_label = QLabel("--:--:--")
        self.time_label.setStyleSheet("font-size: 16px; color: #FFFF00;")
        layout.addWidget(self.time_label)
        
        return frame
    
    def _start_subscriber(self):
        """Start the Redis subscriber."""
        def quote_callback(quote: QuoteData):
            if quote.security_id in self.nifty50_stocks:
                self.signals.quote_received.emit(quote)
        
        self._subscriber = BreadthSubscriber(callback=quote_callback)
        self._subscriber.start()
        self.status_bar.showMessage("Connected to Redis. Waiting for quotes...")
    
    def _on_quote(self, quote: QuoteData):
        """Handle incoming quote."""
        sec_id = quote.security_id
        
        if sec_id not in self.nifty50_stocks:
            return
        
        stock = self.nifty50_stocks[sec_id]
        old_status = stock.status
        
        # Update stock with day_close (previous day's close)
        stock.update(quote.ltp, quote.day_close)
        
        # Update buckets if status changed
        if stock.status != old_status:
            # Remove from old bucket
            if old_status == "advance":
                self.advances.discard(sec_id)
            elif old_status == "decline":
                self.declines.discard(sec_id)
            else:
                self.unchanged.discard(sec_id)
            
            # Add to new bucket
            if stock.status == "advance":
                self.advances.add(sec_id)
            elif stock.status == "decline":
                self.declines.add(sec_id)
            else:
                self.unchanged.add(sec_id)
        
        self.quote_count += 1
        self.last_quote_time = datetime.now()
    
    def _update_chart(self):
        """Add new point to chart."""
        adv = len(self.advances)
        dec = len(self.declines)
        unc = len(self.unchanged)
        
        self.chart_widget.add_point(adv, dec, unc)
    
    def _update_stats(self):
        """Update stats display."""
        adv = len(self.advances)
        dec = len(self.declines)
        unc = len(self.unchanged)
        
        self.adv_label.setText(f"▲ Advances: {adv}")
        self.dec_label.setText(f"▼ Declines: {dec}")
        self.unc_label.setText(f"● Unchanged: {unc}")
        
        if dec > 0:
            ratio = adv / dec
            self.ratio_label.setText(f"A/D Ratio: {ratio:.2f}")
        else:
            self.ratio_label.setText(f"A/D Ratio: {adv}:0")
        
        if self.last_quote_time:
            self.time_label.setText(self.last_quote_time.strftime("%H:%M:%S"))
        
        # Update stock lists
        adv_stocks = [self.nifty50_stocks[sid] for sid in self.advances]
        dec_stocks = [self.nifty50_stocks[sid] for sid in self.declines]
        self.advances_list.update_stocks(adv_stocks)
        self.declines_list.update_stocks(dec_stocks)
        
        self.status_bar.showMessage(f"📊 Quotes: {self.quote_count:,} | Stocks tracked: {len(self.nifty50_stocks)}")
    
    def closeEvent(self, event):
        """Handle close event."""
        if self._subscriber:
            self._subscriber.stop()
        event.accept()


def main():
    """Main entry point."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark palette
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 46))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 46))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = MarketBreadthChart()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
