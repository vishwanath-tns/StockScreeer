"""
Tick Chart Visualizer
=====================
Real-time and historical tick chart using Dhan quotes stored in database.

A tick chart displays price movement based on number of ticks (trades),
not time intervals. Each bar represents N ticks.

Features:
- Load historical ticks from database
- Real-time tick updates via Redis
- Configurable tick count per bar (10, 25, 50, 100, 200)
- OHLC candles based on tick count
- Volume per tick bar
- Scrollable chart
- Instrument selector dropdown

Usage:
    python -m dhan_trading.visualizers.tick_chart
"""
import os
import sys
import signal
import logging
from datetime import datetime, date, time as dt_time, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QStatusBar, QSizePolicy, QSplitter,
    QPushButton, QSlider, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.redis_subscriber import RedisSubscriber, CHANNEL_QUOTES
from dhan_trading.market_feed.redis_publisher import QuoteData
from dhan_trading.db_setup import get_engine, DHAN_DB_NAME

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chart settings
DEFAULT_TICKS_PER_BAR = 50
MAX_VISIBLE_BARS = 200
DEFAULT_VISIBLE_BARS = 100


@dataclass
class Tick:
    """A single tick (quote)."""
    timestamp: datetime
    price: float
    quantity: int
    volume: int


@dataclass
class TickBar:
    """A bar aggregated from N ticks."""
    start_time: datetime
    end_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    tick_count: int
    
    @property
    def is_bullish(self) -> bool:
        return self.close_price >= self.open_price


class TickChartWidget(QWidget):
    """Widget that draws the tick chart with OHLC candles."""
    
    # Signal when scroll changes
    scroll_changed = pyqtSignal(int, int, str, str)  # offset, total, start_time, end_time
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars: List[TickBar] = []
        self.visible_bars = DEFAULT_VISIBLE_BARS
        self.scroll_offset = 0
        self.auto_scroll = True
        
        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Colors
        self.bullish_color = QColor(0, 200, 83)  # Green
        self.bearish_color = QColor(255, 82, 82)  # Red
        self.grid_color = QColor(60, 60, 80)
        self.text_color = QColor(200, 200, 200)
        self.bg_color = QColor(26, 26, 46)
        self.volume_color = QColor(100, 100, 180, 100)
        
        self.setMouseTracking(True)
        self._hover_bar_idx = -1
    
    def set_bars(self, bars: List[TickBar]):
        """Set all bars."""
        self.bars = bars
        if self.auto_scroll:
            self.scroll_offset = 0
        self.update()
        self._emit_scroll_changed()
    
    def add_bar(self, bar: TickBar):
        """Add a new bar."""
        self.bars.append(bar)
        if self.auto_scroll:
            self.scroll_offset = 0
        self.update()
        self._emit_scroll_changed()
    
    def update_last_bar(self, bar: TickBar):
        """Update the last bar (for in-progress bar)."""
        if self.bars:
            self.bars[-1] = bar
        else:
            self.bars.append(bar)
        self.update()
    
    def set_visible_bars(self, count: int):
        """Set number of visible bars."""
        self.visible_bars = max(20, min(count, MAX_VISIBLE_BARS))
        self.update()
        self._emit_scroll_changed()
    
    def scroll_to(self, offset: int):
        """Scroll to specific offset."""
        max_offset = max(0, len(self.bars) - self.visible_bars)
        self.scroll_offset = max(0, min(offset, max_offset))
        self.auto_scroll = (self.scroll_offset == 0)
        self.update()
        self._emit_scroll_changed()
    
    def scroll_by(self, delta: int):
        """Scroll by delta bars."""
        self.scroll_to(self.scroll_offset + delta)
    
    def go_to_latest(self):
        """Jump to latest data."""
        self.scroll_offset = 0
        self.auto_scroll = True
        self.update()
        self._emit_scroll_changed()
    
    def _emit_scroll_changed(self):
        """Emit scroll changed signal."""
        visible = self._get_visible_bars()
        if visible:
            start_time = visible[0].start_time.strftime("%H:%M:%S")
            end_time = visible[-1].end_time.strftime("%H:%M:%S")
        else:
            start_time = "--:--:--"
            end_time = "--:--:--"
        self.scroll_changed.emit(self.scroll_offset, len(self.bars), start_time, end_time)
    
    def _get_visible_bars(self) -> List[TickBar]:
        """Get currently visible bars."""
        if not self.bars:
            return []
        end_idx = len(self.bars) - self.scroll_offset
        start_idx = max(0, end_idx - self.visible_bars)
        return self.bars[start_idx:end_idx]
    
    def wheelEvent(self, event):
        """Handle mouse wheel for scrolling."""
        delta = event.angleDelta().y()
        if delta > 0:
            self.scroll_by(5)  # Scroll back
        else:
            self.scroll_by(-5)  # Scroll forward
        event.accept()
    
    def mouseMoveEvent(self, event):
        """Track mouse for hover info."""
        visible = self._get_visible_bars()
        if not visible:
            return
        
        margin_left = 70
        margin_right = 20
        chart_width = self.width() - margin_left - margin_right
        bar_width = chart_width / max(1, len(visible))
        
        x = event.position().x()
        if x >= margin_left and x <= self.width() - margin_right:
            idx = int((x - margin_left) / bar_width)
            if 0 <= idx < len(visible):
                self._hover_bar_idx = idx
                self.update()
                return
        
        self._hover_bar_idx = -1
        self.update()
    
    def paintEvent(self, event):
        """Paint the tick chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background
        painter.fillRect(0, 0, width, height, self.bg_color)
        
        visible = self._get_visible_bars()
        if not visible:
            painter.setPen(self.text_color)
            painter.setFont(QFont("Arial", 14))
            painter.drawText(width // 2 - 100, height // 2, "No tick data available")
            return
        
        # Margins
        margin_left = 70
        margin_right = 20
        margin_top = 30
        margin_bottom = 60
        volume_height = 60
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom - volume_height
        
        # Find price range
        all_highs = [b.high_price for b in visible]
        all_lows = [b.low_price for b in visible]
        price_high = max(all_highs)
        price_low = min(all_lows)
        price_range = price_high - price_low
        if price_range == 0:
            price_range = price_high * 0.01  # 1% range if flat
        
        # Add padding
        padding = price_range * 0.05
        price_high += padding
        price_low -= padding
        price_range = price_high - price_low
        
        # Find volume range
        max_volume = max(b.volume for b in visible) if visible else 1
        
        # Draw grid
        self._draw_grid(painter, margin_left, margin_top, chart_width, chart_height,
                       price_low, price_high, len(visible))
        
        # Draw candles
        bar_width = chart_width / len(visible)
        candle_width = max(1, bar_width * 0.7)
        
        for i, bar in enumerate(visible):
            x = margin_left + i * bar_width + bar_width / 2
            
            # Price to Y
            def price_to_y(price):
                return margin_top + chart_height - ((price - price_low) / price_range * chart_height)
            
            open_y = price_to_y(bar.open_price)
            close_y = price_to_y(bar.close_price)
            high_y = price_to_y(bar.high_price)
            low_y = price_to_y(bar.low_price)
            
            color = self.bullish_color if bar.is_bullish else self.bearish_color
            
            # Draw wick
            painter.setPen(QPen(color, 1))
            painter.drawLine(int(x), int(high_y), int(x), int(low_y))
            
            # Draw body
            body_top = min(open_y, close_y)
            body_height = max(1, abs(close_y - open_y))
            
            if bar.is_bullish:
                painter.fillRect(int(x - candle_width/2), int(body_top), 
                               int(candle_width), int(body_height), color)
            else:
                painter.fillRect(int(x - candle_width/2), int(body_top),
                               int(candle_width), int(body_height), color)
            
            # Draw volume bar
            vol_y = height - margin_bottom
            vol_h = (bar.volume / max_volume) * volume_height if max_volume > 0 else 0
            vol_color = QColor(color)
            vol_color.setAlpha(100)
            painter.fillRect(int(x - candle_width/2), int(vol_y - vol_h),
                           int(candle_width), int(vol_h), vol_color)
        
        # Draw hover info
        if 0 <= self._hover_bar_idx < len(visible):
            self._draw_hover_info(painter, visible[self._hover_bar_idx], 
                                 margin_left, margin_top)
        
        # Draw scroll indicator
        if self.scroll_offset > 0:
            painter.setPen(QPen(QColor(255, 200, 0)))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            text = f"◄ {self.scroll_offset} bars ago | Scroll or click 'Live' ►"
            painter.drawText(width // 2 - 100, height - 10, text)
        
        # Draw title
        painter.setPen(self.text_color)
        painter.setFont(QFont("Arial", 10))
        first_time = visible[0].start_time.strftime("%H:%M:%S")
        last_time = visible[-1].end_time.strftime("%H:%M:%S")
        painter.drawText(margin_left, height - margin_bottom + 25, first_time)
        painter.drawText(width - margin_right - 60, height - margin_bottom + 25, last_time)
    
    def _draw_grid(self, painter: QPainter, margin_left: int, margin_top: int,
                   chart_width: int, chart_height: int, price_low: float, 
                   price_high: float, bar_count: int):
        """Draw price grid."""
        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        
        # Horizontal lines (price levels)
        price_range = price_high - price_low
        num_lines = 5
        for i in range(num_lines + 1):
            y = margin_top + (i / num_lines) * chart_height
            price = price_high - (i / num_lines) * price_range
            
            painter.drawLine(margin_left, int(y), margin_left + chart_width, int(y))
            
            # Price label
            painter.setPen(self.text_color)
            painter.setFont(QFont("Arial", 9))
            painter.drawText(5, int(y) + 4, f"{price:,.2f}")
            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        
        # Vertical lines
        num_v_lines = min(10, bar_count // 10)
        if num_v_lines > 0:
            for i in range(1, num_v_lines + 1):
                x = margin_left + (i / (num_v_lines + 1)) * chart_width
                painter.drawLine(int(x), margin_top, int(x), margin_top + chart_height)
    
    def _draw_hover_info(self, painter: QPainter, bar: TickBar, 
                         margin_left: int, margin_top: int):
        """Draw hover tooltip."""
        info_x = margin_left + 10
        info_y = margin_top + 10
        
        # Background
        painter.fillRect(info_x, info_y, 180, 100, QColor(30, 30, 50, 220))
        painter.setPen(QPen(QColor(100, 100, 150), 1))
        painter.drawRect(info_x, info_y, 180, 100)
        
        # Text
        painter.setPen(self.text_color)
        painter.setFont(QFont("Consolas", 9))
        
        lines = [
            f"Time: {bar.start_time.strftime('%H:%M:%S')}",
            f"O: {bar.open_price:,.2f}  H: {bar.high_price:,.2f}",
            f"L: {bar.low_price:,.2f}  C: {bar.close_price:,.2f}",
            f"Vol: {bar.volume:,}  Ticks: {bar.tick_count}",
            f"Change: {((bar.close_price - bar.open_price) / bar.open_price * 100):+.2f}%"
        ]
        
        for i, line in enumerate(lines):
            painter.drawText(info_x + 10, info_y + 18 + i * 16, line)


class TickAggregator:
    """Aggregates ticks into bars."""
    
    def __init__(self, ticks_per_bar: int = DEFAULT_TICKS_PER_BAR):
        self.ticks_per_bar = ticks_per_bar
        self.current_ticks: List[Tick] = []
        self.completed_bars: List[TickBar] = []
    
    def set_ticks_per_bar(self, count: int):
        """Change ticks per bar (resets current progress)."""
        self.ticks_per_bar = count
        self.current_ticks = []
    
    def add_tick(self, tick: Tick) -> Optional[TickBar]:
        """Add a tick and return a bar if one was completed."""
        self.current_ticks.append(tick)
        
        if len(self.current_ticks) >= self.ticks_per_bar:
            bar = self._create_bar(self.current_ticks)
            self.completed_bars.append(bar)
            self.current_ticks = []
            return bar
        
        return None
    
    def get_current_bar(self) -> Optional[TickBar]:
        """Get the in-progress bar (if any ticks)."""
        if not self.current_ticks:
            return None
        return self._create_bar(self.current_ticks)
    
    def _create_bar(self, ticks: List[Tick]) -> TickBar:
        """Create a bar from ticks."""
        return TickBar(
            start_time=ticks[0].timestamp,
            end_time=ticks[-1].timestamp,
            open_price=ticks[0].price,
            high_price=max(t.price for t in ticks),
            low_price=min(t.price for t in ticks),
            close_price=ticks[-1].price,
            volume=sum(t.quantity for t in ticks),
            tick_count=len(ticks)
        )
    
    def load_from_ticks(self, ticks: List[Tick]) -> List[TickBar]:
        """Load bars from a list of ticks."""
        self.current_ticks = []
        self.completed_bars = []
        
        bars = []
        for tick in ticks:
            bar = self.add_tick(tick)
            if bar:
                bars.append(bar)
        
        return bars


class TickSubscriber(RedisSubscriber):
    """Redis subscriber for tick data."""
    
    def __init__(self, security_id: int, callback, config=None):
        super().__init__(config)
        self._security_id = security_id
        self._callback = callback
    
    def on_quote(self, quote: QuoteData):
        """Handle incoming quote."""
        if quote.security_id == self._security_id:
            self._callback(quote)
    
    def start(self):
        """Connect, subscribe, and start listening."""
        if self.connect():
            self.subscribe([CHANNEL_QUOTES])
            self.run(blocking=False)

class QuoteSignals(QObject):
    """Signals for quote updates."""
    quote_received = pyqtSignal(object)


class TickChartWindow(QMainWindow):
    """Main window for tick chart."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Tick Chart - Dhan Quotes")
        self.setMinimumSize(1000, 700)
        
        # State
        self.engine = get_engine(DHAN_DB_NAME)
        self.instruments: Dict[int, dict] = {}
        self.current_security_id: Optional[int] = None
        self.aggregator = TickAggregator()
        self._subscriber: Optional[TickSubscriber] = None
        self.signals = QuoteSignals()
        
        # Setup
        self._load_instruments()
        self._setup_ui()
        self._setup_connections()
        
        # Auto-select first instrument
        if self.instruments:
            self._on_instrument_changed(0)
    
    def _load_instruments(self):
        """Load available instruments from database."""
        with self.engine.connect() as conn:
            # Get instruments with quotes today
            result = conn.execute(text("""
                SELECT q.security_id, i.symbol, i.display_name, COUNT(*) as cnt
                FROM dhan_quotes q
                LEFT JOIN dhan_instruments i ON q.security_id = i.security_id
                WHERE DATE(q.received_at) = CURDATE()
                GROUP BY q.security_id, i.symbol, i.display_name
                HAVING cnt >= 100
                ORDER BY cnt DESC
                LIMIT 50
            """))
            
            for row in result.fetchall():
                sec_id = row[0]
                self.instruments[sec_id] = {
                    'security_id': sec_id,
                    'symbol': row[1] or f'ID:{sec_id}',
                    'display_name': row[2] or row[1] or f'ID:{sec_id}',
                    'quote_count': row[3]
                }
        
        logger.info(f"Loaded {len(self.instruments)} instruments with quotes")
    
    def _setup_ui(self):
        """Setup the UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a2e;
                color: white;
            }
            QComboBox, QSpinBox {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }
            QPushButton {
                background-color: #0f3460;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a4f7a;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #16213e;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
        """)
        
        # Top controls
        controls_frame = self._create_controls_frame()
        main_layout.addWidget(controls_frame)
        
        # Chart
        self.chart_widget = TickChartWidget()
        self.chart_widget.scroll_changed.connect(self._on_scroll_changed)
        main_layout.addWidget(self.chart_widget, stretch=1)
        
        # Navigation controls
        nav_frame = self._create_nav_frame()
        main_layout.addWidget(nav_frame)
        
        # Stats bar
        stats_frame = self._create_stats_frame()
        main_layout.addWidget(stats_frame)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Select an instrument to start")
    
    def _create_controls_frame(self) -> QWidget:
        """Create top controls frame."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(20)
        
        # Instrument selector
        inst_label = QLabel("Instrument:")
        inst_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(inst_label)
        
        self.instrument_combo = QComboBox()
        for sec_id, info in self.instruments.items():
            self.instrument_combo.addItem(
                f"{info['display_name']} ({info['quote_count']:,} ticks)",
                sec_id
            )
        layout.addWidget(self.instrument_combo)
        
        layout.addStretch()
        
        # Ticks per bar selector
        ticks_label = QLabel("Ticks/Bar:")
        ticks_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(ticks_label)
        
        self.ticks_combo = QComboBox()
        for ticks in [10, 25, 50, 100, 200, 500]:
            self.ticks_combo.addItem(f"{ticks} ticks", ticks)
        self.ticks_combo.setCurrentIndex(2)  # Default 50
        layout.addWidget(self.ticks_combo)
        
        layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Reload Data")
        layout.addWidget(self.refresh_btn)
        
        return frame
    
    def _create_nav_frame(self) -> QWidget:
        """Create navigation frame."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 5px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # Scroll buttons
        btn_back_10 = QPushButton("◄◄ -10")
        btn_back_10.clicked.connect(lambda: self.chart_widget.scroll_by(10))
        layout.addWidget(btn_back_10)
        
        btn_back = QPushButton("◄ -5")
        btn_back.clicked.connect(lambda: self.chart_widget.scroll_by(5))
        layout.addWidget(btn_back)
        
        # Position label
        self.pos_label = QLabel("Position: Live")
        self.pos_label.setStyleSheet("color: #00E5FF; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.pos_label)
        
        btn_fwd = QPushButton("► +5")
        btn_fwd.clicked.connect(lambda: self.chart_widget.scroll_by(-5))
        layout.addWidget(btn_fwd)
        
        btn_fwd_10 = QPushButton("►► +10")
        btn_fwd_10.clicked.connect(lambda: self.chart_widget.scroll_by(-10))
        layout.addWidget(btn_fwd_10)
        
        layout.addStretch()
        
        # Zoom
        zoom_label = QLabel("Visible Bars:")
        layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(20)
        self.zoom_slider.setMaximum(MAX_VISIBLE_BARS)
        self.zoom_slider.setValue(DEFAULT_VISIBLE_BARS)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        layout.addWidget(self.zoom_slider)
        
        self.zoom_value_label = QLabel(f"{DEFAULT_VISIBLE_BARS}")
        self.zoom_value_label.setStyleSheet("min-width: 40px;")
        layout.addWidget(self.zoom_value_label)
        
        layout.addStretch()
        
        # Live button
        self.live_btn = QPushButton("🔴 LIVE")
        self.live_btn.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.live_btn.clicked.connect(self.chart_widget.go_to_latest)
        layout.addWidget(self.live_btn)
        
        return frame
    
    def _create_stats_frame(self) -> QWidget:
        """Create stats display frame."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        frame.setMaximumHeight(70)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(30)
        
        # Current price
        self.price_label = QLabel("LTP: --")
        self.price_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(self.price_label)
        
        # Change
        self.change_label = QLabel("Change: --")
        self.change_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.change_label)
        
        layout.addStretch()
        
        # Bars info
        self.bars_label = QLabel("Bars: 0")
        self.bars_label.setStyleSheet("font-size: 14px; color: #888;")
        layout.addWidget(self.bars_label)
        
        # Ticks info
        self.ticks_label = QLabel("Ticks: 0")
        self.ticks_label.setStyleSheet("font-size: 14px; color: #888;")
        layout.addWidget(self.ticks_label)
        
        # Time
        self.time_label = QLabel("--:--:--")
        self.time_label.setStyleSheet("font-size: 16px; color: #FFFF00;")
        layout.addWidget(self.time_label)
        
        return frame
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.instrument_combo.currentIndexChanged.connect(self._on_instrument_changed)
        self.ticks_combo.currentIndexChanged.connect(self._on_ticks_changed)
        self.refresh_btn.clicked.connect(self._load_historical_data)
        self.signals.quote_received.connect(self._on_quote)
    
    def _on_instrument_changed(self, index: int):
        """Handle instrument selection change."""
        if index < 0:
            return
        
        # Stop existing subscriber
        if self._subscriber:
            self._subscriber.stop()
            self._subscriber = None
        
        # Get selected security ID
        self.current_security_id = self.instrument_combo.currentData()
        if not self.current_security_id:
            return
        
        info = self.instruments.get(self.current_security_id, {})
        self.setWindowTitle(f"📊 Tick Chart - {info.get('display_name', 'Unknown')}")
        
        # Load historical data
        self._load_historical_data()
        
        # Start subscriber for real-time updates
        self._start_subscriber()
    
    def _on_ticks_changed(self, index: int):
        """Handle ticks per bar change."""
        ticks = self.ticks_combo.currentData()
        if ticks:
            self.aggregator.set_ticks_per_bar(ticks)
            self._load_historical_data()
    
    def _on_zoom_changed(self, value: int):
        """Handle zoom change."""
        self.chart_widget.set_visible_bars(value)
        self.zoom_value_label.setText(str(value))
    
    def _on_scroll_changed(self, offset: int, total: int, start_time: str, end_time: str):
        """Handle scroll position change."""
        if offset == 0:
            self.pos_label.setText("Position: 🔴 LIVE")
            self.pos_label.setStyleSheet("color: #00E5FF; font-size: 12px; font-weight: bold;")
            self.live_btn.setEnabled(False)
        else:
            self.pos_label.setText(f"Viewing: {start_time} - {end_time} ({offset} bars ago)")
            self.pos_label.setStyleSheet("color: #FFD700; font-size: 12px;")
            self.live_btn.setEnabled(True)
        
        self.bars_label.setText(f"Bars: {total}")
    
    def _load_historical_data(self):
        """Load historical ticks from database."""
        if not self.current_security_id:
            return
        
        self.status_bar.showMessage("Loading historical data...")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT ltp, ltq, volume, received_at
                    FROM dhan_quotes
                    WHERE security_id = :sec_id
                      AND DATE(received_at) = CURDATE()
                    ORDER BY received_at ASC
                """), {'sec_id': self.current_security_id})
                
                ticks = []
                for row in result.fetchall():
                    ticks.append(Tick(
                        timestamp=row[3],
                        price=float(row[0]),
                        quantity=int(row[1]),
                        volume=int(row[2])
                    ))
                
                if ticks:
                    # Reset aggregator with current ticks per bar
                    self.aggregator = TickAggregator(self.ticks_combo.currentData() or DEFAULT_TICKS_PER_BAR)
                    bars = self.aggregator.load_from_ticks(ticks)
                    
                    # Include current in-progress bar
                    current_bar = self.aggregator.get_current_bar()
                    if current_bar:
                        bars.append(current_bar)
                    
                    self.chart_widget.set_bars(bars)
                    
                    # Update stats
                    last_tick = ticks[-1]
                    first_tick = ticks[0]
                    self._update_stats(last_tick.price, first_tick.price, len(ticks))
                    
                    self.status_bar.showMessage(
                        f"Loaded {len(ticks):,} ticks → {len(bars)} bars "
                        f"({self.aggregator.ticks_per_bar} ticks/bar)"
                    )
                else:
                    self.chart_widget.set_bars([])
                    self.status_bar.showMessage("No data found for today")
        
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.status_bar.showMessage(f"Error: {e}")
    
    def _start_subscriber(self):
        """Start Redis subscriber for real-time updates."""
        if not self.current_security_id:
            return
        
        def quote_callback(quote: QuoteData):
            self.signals.quote_received.emit(quote)
        
        self._subscriber = TickSubscriber(self.current_security_id, quote_callback)
        self._subscriber.start()
        logger.info(f"Started subscriber for security_id={self.current_security_id}")
    
    def _on_quote(self, quote: QuoteData):
        """Handle real-time quote."""
        tick = Tick(
            timestamp=datetime.now(),
            price=float(quote.ltp),
            quantity=int(quote.ltq),
            volume=int(quote.volume)
        )
        
        # Add to aggregator
        completed_bar = self.aggregator.add_tick(tick)
        
        if completed_bar:
            # A new bar was completed
            self.chart_widget.add_bar(completed_bar)
        else:
            # Update in-progress bar
            current_bar = self.aggregator.get_current_bar()
            if current_bar:
                # Update last bar or add as new
                if self.chart_widget.bars:
                    self.chart_widget.update_last_bar(current_bar)
                else:
                    self.chart_widget.add_bar(current_bar)
        
        # Update stats
        self._update_stats(tick.price, None, None)
    
    def _update_stats(self, current_price: float, first_price: Optional[float], 
                      tick_count: Optional[int]):
        """Update stats display."""
        self.price_label.setText(f"LTP: {current_price:,.2f}")
        
        # Calculate change from first tick of day
        if first_price and first_price > 0:
            change = current_price - first_price
            change_pct = (change / first_price) * 100
            color = "#00C853" if change >= 0 else "#FF5252"
            self.change_label.setText(f"Change: {change:+,.2f} ({change_pct:+.2f}%)")
            self.change_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        
        if tick_count is not None:
            self.ticks_label.setText(f"Ticks: {tick_count:,}")
        
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))
    
    def closeEvent(self, event):
        """Handle close."""
        if self._subscriber:
            self._subscriber.stop()
        event.accept()


def main():
    """Main entry point."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = TickChartWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
