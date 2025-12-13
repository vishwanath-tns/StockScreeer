"""
Volume Profile Visualizer
=========================
Real-time volume profile display using quotes from Redis.

Shows volume distribution across price levels for today's trading session.

Features:
- Loads historical quotes from database (from 9:15 AM or available data)
- Horizontal bar chart showing volume at each price level
- Point of Control (POC) - price with highest volume
- Value Area (70% of volume)
- Real-time updates from Redis pub/sub
- Per-instrument volume profiles

Usage:
    python -m dhan_trading.visualizers.volume_profile
"""
import os
import sys
import signal
import logging
from datetime import datetime, date, time as dt_time
from typing import Dict, Optional, List, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import quote_plus
import threading
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QFrame, QSplitter,
    QStatusBar, QSpinBox, QCheckBox, QScrollArea, QSizePolicy,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPalette

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.redis_subscriber import RedisSubscriber, CHANNEL_QUOTES
from dhan_trading.market_feed.redis_publisher import QuoteData
from dhan_trading.market_feed.instrument_selector import InstrumentSelector
from dhan_trading.db_setup import get_engine, DHAN_DB_NAME

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Market timing
MARKET_OPEN_TIME = dt_time(9, 15)   # 9:15 AM IST (NSE equity market open)
MARKET_CLOSE_TIME = dt_time(15, 30) # 3:30 PM IST (NSE equity market close)


@dataclass
class VolumeProfileData:
    """Volume profile data for an instrument."""
    security_id: int
    symbol: str = ""
    
    # Price -> Volume mapping (total, buy, sell)
    volume_at_price: Dict[float, int] = field(default_factory=dict)
    buy_volume_at_price: Dict[float, int] = field(default_factory=dict)
    sell_volume_at_price: Dict[float, int] = field(default_factory=dict)
    
    # Stats
    total_volume: int = 0
    total_buy_volume: int = 0
    total_sell_volume: int = 0
    high_price: float = 0.0
    low_price: float = float('inf')
    last_price: float = 0.0
    previous_price: float = 0.0  # For tick direction
    open_price: float = 0.0
    
    # Tick direction tracking (1=uptick/buy, -1=downtick/sell, 0=unknown)
    last_tick_direction: int = 0
    
    # POC (Point of Control)
    poc_price: float = 0.0
    poc_volume: int = 0
    
    # Value Area
    value_area_high: float = 0.0
    value_area_low: float = 0.0
    
    # Tick size for price bucketing
    tick_size: float = 10.0  # Default 10 points for index futures
    
    # Update counter for visual feedback
    update_count: int = 0
    
    # Historical data loaded flag
    historical_loaded: bool = False
    historical_quote_count: int = 0
    
    def add_historical_quote(self, ltp: float, volume: int, prev_volume: int = 0):
        """
        Add a historical quote to build initial profile.
        Uses tick rule to determine buy/sell attribution:
        - Uptick (price up): volume attributed to BUY (buyer aggressor)
        - Downtick (price down): volume attributed to SELL (seller aggressor)
        - Zero-tick: use last known direction
        
        Args:
            ltp: Last traded price
            volume: Cumulative volume at this quote
            prev_volume: Previous cumulative volume (to calculate delta)
        """
        # Set open price (first quote)
        if self.open_price == 0.0:
            self.open_price = ltp
        
        # Update high/low
        self.high_price = max(self.high_price, ltp)
        if self.low_price == float('inf'):
            self.low_price = ltp
        else:
            self.low_price = min(self.low_price, ltp)
        
        # Determine tick direction for buy/sell attribution
        tick_direction = self._get_tick_direction(ltp)
        
        self.previous_price = self.last_price
        self.last_price = ltp
        
        # Bucket the price
        bucketed_price = self._bucket_price(ltp)
        
        # Calculate volume delta
        if volume > prev_volume:
            volume_delta = volume - prev_volume
            self.volume_at_price[bucketed_price] = self.volume_at_price.get(bucketed_price, 0) + volume_delta
            
            # Attribute to buy or sell based on tick direction
            if tick_direction >= 0:  # Uptick or zero-tick with buy bias
                self.buy_volume_at_price[bucketed_price] = self.buy_volume_at_price.get(bucketed_price, 0) + volume_delta
                self.total_buy_volume += volume_delta
            else:  # Downtick
                self.sell_volume_at_price[bucketed_price] = self.sell_volume_at_price.get(bucketed_price, 0) + volume_delta
                self.total_sell_volume += volume_delta
        
        # Track total volume (last cumulative value)
        self.total_volume = max(self.total_volume, volume)
        self.historical_quote_count += 1
    
    def _get_tick_direction(self, current_price: float) -> int:
        """
        Determine tick direction using tick rule.
        Returns: 1 for uptick (buy), -1 for downtick (sell), 0 for zero-tick
        """
        if self.last_price == 0.0:
            # First quote - assume neutral/buy
            self.last_tick_direction = 1
            return 1
        
        if current_price > self.last_price:
            # Uptick - buyer was aggressor
            self.last_tick_direction = 1
            return 1
        elif current_price < self.last_price:
            # Downtick - seller was aggressor
            self.last_tick_direction = -1
            return -1
        else:
            # Zero-tick - use last known direction
            return self.last_tick_direction if self.last_tick_direction != 0 else 1
    
    def finalize_historical_load(self):
        """Called after all historical quotes are loaded."""
        self.historical_loaded = True
        self._update_poc()
        logger.info(f"Historical load complete for {self.symbol}: {self.historical_quote_count} quotes, "
                   f"{len(self.volume_at_price)} price levels, volume={self.total_volume:,}")
    
    def add_quote(self, quote: QuoteData):
        """Add a real-time quote to the volume profile with tick-based buy/sell attribution."""
        price = quote.ltp
        volume = quote.volume
        
        # Increment update counter
        self.update_count += 1
        
        # Set open price (first quote)
        if self.open_price == 0.0:
            self.open_price = price
        
        # Update high/low
        self.high_price = max(self.high_price, price)
        if self.low_price == float('inf'):
            self.low_price = price
        else:
            self.low_price = min(self.low_price, price)
        
        # Determine tick direction for buy/sell attribution
        tick_direction = self._get_tick_direction(price)
        
        self.previous_price = self.last_price
        self.last_price = price
        
        # Bucket the price
        bucketed_price = self._bucket_price(price)
        
        # Calculate volume delta (difference from last total)
        # Note: volume in quote is cumulative, we want incremental
        if volume > self.total_volume:
            volume_delta = volume - self.total_volume
            self.volume_at_price[bucketed_price] = self.volume_at_price.get(bucketed_price, 0) + volume_delta
            
            # Attribute to buy or sell based on tick direction
            if tick_direction >= 0:  # Uptick or zero-tick with buy bias
                self.buy_volume_at_price[bucketed_price] = self.buy_volume_at_price.get(bucketed_price, 0) + volume_delta
                self.total_buy_volume += volume_delta
            else:  # Downtick
                self.sell_volume_at_price[bucketed_price] = self.sell_volume_at_price.get(bucketed_price, 0) + volume_delta
                self.total_sell_volume += volume_delta
            
            self.total_volume = volume
        
        # Update POC
        self._update_poc()
    
    def _bucket_price(self, price: float) -> float:
        """Bucket price to nearest tick size."""
        return round(price / self.tick_size) * self.tick_size
    
    def _update_poc(self):
        """Update Point of Control."""
        if not self.volume_at_price:
            return
        
        # Find price with max volume
        self.poc_price = max(self.volume_at_price.keys(), key=lambda p: self.volume_at_price[p])
        self.poc_volume = self.volume_at_price[self.poc_price]
        
        # Calculate Value Area (70% of volume)
        self._calculate_value_area()
    
    def _calculate_value_area(self):
        """Calculate Value Area (70% of total volume)."""
        if not self.volume_at_price or self.total_volume == 0:
            return
        
        target_volume = self.total_volume * 0.7
        
        # Start from POC and expand
        prices = sorted(self.volume_at_price.keys())
        if not prices:
            return
        
        poc_idx = prices.index(self.poc_price) if self.poc_price in prices else len(prices) // 2
        
        va_volume = self.volume_at_price.get(self.poc_price, 0)
        low_idx = poc_idx
        high_idx = poc_idx
        
        while va_volume < target_volume and (low_idx > 0 or high_idx < len(prices) - 1):
            # Check which direction to expand
            low_vol = self.volume_at_price.get(prices[low_idx - 1], 0) if low_idx > 0 else 0
            high_vol = self.volume_at_price.get(prices[high_idx + 1], 0) if high_idx < len(prices) - 1 else 0
            
            if low_vol >= high_vol and low_idx > 0:
                low_idx -= 1
                va_volume += low_vol
            elif high_idx < len(prices) - 1:
                high_idx += 1
                va_volume += high_vol
            elif low_idx > 0:
                low_idx -= 1
                va_volume += low_vol
            else:
                break
        
        self.value_area_low = prices[low_idx]
        self.value_area_high = prices[high_idx]
    
    def get_profile_bars(self) -> List[Tuple[float, int, float, int, int, int]]:
        """
        Get volume profile as list of (price, volume, percentage, buy_vol, sell_vol, side).
        side: 1 = buy dominant (green), -1 = sell dominant (red), 0 = neutral
        Returns sorted by price descending (high to low).
        """
        if not self.volume_at_price:
            return []
        
        max_vol = max(self.volume_at_price.values()) if self.volume_at_price else 1
        
        bars = []
        for price in sorted(self.volume_at_price.keys(), reverse=True):
            vol = self.volume_at_price[price]
            pct = vol / max_vol if max_vol > 0 else 0
            buy_vol = self.buy_volume_at_price.get(price, 0)
            sell_vol = self.sell_volume_at_price.get(price, 0)
            
            # Determine dominant side
            if buy_vol > sell_vol:
                side = 1  # Buy dominant - GREEN
            elif sell_vol > buy_vol:
                side = -1  # Sell dominant - RED
            else:
                side = 0  # Neutral
            
            bars.append((price, vol, pct, buy_vol, sell_vol, side))
        
        return bars


class VolumeProfileWidget(QWidget):
    """Widget to draw volume profile bars."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_data: Optional[VolumeProfileData] = None
        self.setMinimumHeight(400)
        self.setMinimumWidth(600)
        
        # Colors - clearly distinguishable (using RGB integers)
        self.buy_color = QColor(0, 200, 83)     # Bright Green for buy (uptick)
        self.sell_color = QColor(255, 23, 68)   # Bright Red for sell (downtick)
        self.neutral_color = QColor(158, 158, 158)  # Grey for neutral
        self.poc_color = QColor("#FFD600")  # Yellow for POC line
        self.vah_color = QColor("#00BCD4")  # Cyan for VAH line
        self.val_color = QColor("#FF9800")  # Orange for VAL line
        self.text_color = QColor("#333333")
        self.grid_color = QColor("#E0E0E0")
        self.current_price_color = QColor("#F44336")  # Red
        self.current_price_dot_color = QColor("#E91E63")  # Pink for LTP dot
        
        # Bar spacing
        self.bar_spacing = 3  # Pixels between bars
    
    def set_profile(self, profile: VolumeProfileData):
        """Set the profile data to display."""
        self.profile_data = profile
        self.update()
    
    def paintEvent(self, event):
        """Paint the volume profile."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor("#FAFAFA"))
        
        if not self.profile_data or not self.profile_data.volume_at_price:
            painter.setPen(QPen(self.text_color))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waiting for data...")
            return
        
        # Get dimensions
        width = self.width()
        height = self.height()
        margin_left = 100   # Space for price labels and dot
        margin_right = 100  # Space for volume labels
        margin_top = 40
        margin_bottom = 40
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        # Get profile bars
        bars = self.profile_data.get_profile_bars()
        if not bars:
            return
        
        # Calculate bar height with spacing
        num_bars = len(bars)
        total_spacing = (num_bars - 1) * self.bar_spacing
        bar_height = max(8, (chart_height - total_spacing) / num_bars)
        
        # Draw title
        painter.setPen(QPen(self.text_color))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title = f"{self.profile_data.symbol} - Volume Profile (Bin: {self.profile_data.tick_size:.0f} pts)"
        painter.drawText(10, 25, title)
        
        # Draw stats
        painter.setFont(QFont("Segoe UI", 10))
        buy_pct = (self.profile_data.total_buy_volume / self.profile_data.total_volume * 100) if self.profile_data.total_volume > 0 else 0
        sell_pct = (self.profile_data.total_sell_volume / self.profile_data.total_volume * 100) if self.profile_data.total_volume > 0 else 0
        stats = f"POC: {self.profile_data.poc_price:.2f} | VA: {self.profile_data.value_area_low:.2f} - {self.profile_data.value_area_high:.2f} | Vol: {self.profile_data.total_volume:,} | Buy: {buy_pct:.0f}% Sell: {sell_pct:.0f}%"
        painter.drawText(width - 550, 25, stats)
        
        # Find which bar contains current price
        current_price = self.profile_data.last_price
        tick_size = self.profile_data.tick_size
        
        # Track positions for POC and VA lines
        poc_y = None
        vah_y = None
        val_y = None
        
        # Draw bars
        y = margin_top
        for price, volume, pct, buy_vol, sell_vol, side in bars:
            # Check if current price is in this bin
            is_current_price_bin = (price - tick_size/2) <= current_price <= (price + tick_size/2)
            
            # Determine bar color based on buy/sell dominance
            if side == 1:  # Buy dominant
                bar_color = QColor(0, 200, 83)  # RGB Green
            elif side == -1:  # Sell dominant
                bar_color = QColor(255, 23, 68)  # RGB Red
            else:  # Neutral
                bar_color = QColor(158, 158, 158)  # RGB Grey
            
            # Bar width based on percentage
            bar_width = int(chart_width * pct * 0.9)  # 90% max width for visual appeal
            
            # Draw bar with rounded corners effect
            bar_rect_x = margin_left
            bar_rect_y = int(y)
            bar_rect_h = int(bar_height)
            
            # Draw filled bar using brush
            painter.setBrush(QBrush(bar_color))
            painter.setPen(QPen(bar_color.darker(120), 1))
            painter.drawRect(bar_rect_x, bar_rect_y, bar_width, bar_rect_h)
            
            # Reset brush
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Track POC position
            if price == self.profile_data.poc_price:
                poc_y = int(y + bar_height / 2)
            
            # Track VAH/VAL positions
            if price == self.profile_data.value_area_high:
                vah_y = int(y + bar_height / 2)
            if price == self.profile_data.value_area_low:
                val_y = int(y + bar_height / 2)
            
            # Draw current price DOT on left side
            if is_current_price_bin:
                dot_x = margin_left - 20  # Position dot to the left of bars
                dot_y = int(y + bar_height / 2)
                dot_radius = 8
                
                # Draw filled pink dot
                painter.setBrush(QBrush(self.current_price_dot_color))
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawEllipse(dot_x - dot_radius, dot_y - dot_radius, 
                                   dot_radius * 2, dot_radius * 2)
                
                # Draw "LTP" text next to dot
                painter.setPen(QPen(self.current_price_dot_color))
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.drawText(dot_x - dot_radius - 22, dot_y + 4, "LTP")
            
            # Price label (left)
            painter.setPen(QPen(self.text_color))
            painter.setFont(QFont("Consolas", 9))
            price_text = f"{price:.0f}"
            painter.drawText(margin_left - 50, int(y + bar_height - 2), price_text)
            
            # Volume label (right) with buy/sell breakdown
            if volume > 0:
                # Main volume
                painter.drawText(
                    margin_left + bar_width + 8, int(y + bar_height - 2),
                    f"{volume:,}"
                )
                # Buy x Sell breakdown (larger font)
                painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
                breakdown_x = margin_left + bar_width + 80
                if buy_vol > 0 or sell_vol > 0:
                    # Buy volume in green
                    painter.setPen(QPen(self.buy_color))
                    buy_text = f"{buy_vol:,}"
                    painter.drawText(breakdown_x, int(y + bar_height - 2), buy_text)
                    
                    # "x" separator
                    x_pos = breakdown_x + len(buy_text) * 7 + 5
                    painter.setPen(QPen(self.text_color))
                    painter.drawText(x_pos, int(y + bar_height - 2), "x")
                    
                    # Sell volume in red
                    painter.setPen(QPen(self.sell_color))
                    painter.drawText(x_pos + 12, int(y + bar_height - 2), f"{sell_vol:,}")
            
            # Move to next bar with spacing
            y += bar_height + self.bar_spacing
        
        # Draw POC horizontal line (yellow, dashed, extending to right edge)
        if poc_y is not None:
            pen = QPen(self.poc_color, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(margin_left, poc_y, width - 10, poc_y)
            # POC label on right
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QPen(self.poc_color))
            painter.drawText(width - 40, poc_y + 4, "POC")
        
        # Draw VAH horizontal line (cyan, dotted)
        if vah_y is not None:
            pen = QPen(self.vah_color, 2, Qt.PenStyle.DotLine)
            painter.setPen(pen)
            painter.drawLine(margin_left, vah_y, width - 10, vah_y)
            # VAH label on right
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QPen(self.vah_color))
            painter.drawText(width - 40, vah_y + 4, "VAH")
        
        # Draw VAL horizontal line (orange, dotted)
        if val_y is not None:
            pen = QPen(self.val_color, 2, Qt.PenStyle.DotLine)
            painter.setPen(pen)
            painter.drawLine(margin_left, val_y, width - 10, val_y)
            # VAL label on right
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QPen(self.val_color))
            painter.drawText(width - 40, val_y + 4, "VAL")
        
        # Draw legend
        self._draw_legend(painter, width, height)
    
    def _draw_legend(self, painter: QPainter, width: int, height: int):
        """Draw color legend."""
        painter.setFont(QFont("Segoe UI", 9))
        y = height - 25
        x = 15
        
        # LTP Dot
        painter.setBrush(QBrush(self.current_price_dot_color))
        painter.setPen(QPen(Qt.GlobalColor.white, 1))
        painter.drawEllipse(x, y + 2, 10, 10)
        painter.setPen(QPen(self.text_color))
        painter.drawText(x + 15, y + 11, "LTP")
        
        # Buy Volume (Green)
        x += 50
        painter.fillRect(x, y, 18, 12, self.buy_color)
        painter.setPen(QPen(self.text_color))
        painter.drawText(x + 22, y + 11, "Buy")
        
        # Sell Volume (Red)
        x += 55
        painter.fillRect(x, y, 18, 12, self.sell_color)
        painter.drawText(x + 22, y + 11, "Sell")
        
        # POC line (yellow dashed)
        x += 55
        painter.setPen(QPen(self.poc_color, 2, Qt.PenStyle.DashLine))
        painter.drawLine(x, y + 6, x + 25, y + 6)
        painter.setPen(QPen(self.text_color))
        painter.drawText(x + 30, y + 11, "POC")
        
        # VAH line (cyan dotted)
        x += 60
        painter.setPen(QPen(self.vah_color, 2, Qt.PenStyle.DotLine))
        painter.drawLine(x, y + 6, x + 25, y + 6)
        painter.setPen(QPen(self.text_color))
        painter.drawText(x + 30, y + 11, "VAH")
        
        # VAL line (orange dotted)
        x += 60
        painter.setPen(QPen(self.val_color, 2, Qt.PenStyle.DotLine))
        painter.drawLine(x, y + 6, x + 25, y + 6)
        painter.setPen(QPen(self.text_color))
        painter.drawText(x + 30, y + 11, "VAL")


class QuoteSignals(QObject):
    """Signals for quote updates."""
    quote_received = pyqtSignal(object)
    historical_load_complete = pyqtSignal(str)  # Signal when historical load is done


class VolumeProfileSubscriber(RedisSubscriber):
    """Subscriber that updates volume profiles from quotes."""
    
    def __init__(self, signals: QuoteSignals):
        super().__init__()
        self.signals = signals
    
    def on_quote(self, quote: QuoteData):
        """Handle incoming quote."""
        self.signals.quote_received.emit(quote)


class VolumeProfileVisualizer(QMainWindow):
    """Main window for volume profile visualization."""
    
    def __init__(self):
        super().__init__()
        
        # Data
        self.profiles: Dict[int, VolumeProfileData] = {}
        self.instrument_names: Dict[int, str] = {}
        self.current_instrument: Optional[int] = None
        
        # Database connection
        self._db_engine = None
        self._init_database()
        
        # Subscriber
        self.signals = QuoteSignals()
        self.signals.quote_received.connect(self._on_quote)
        self.signals.historical_load_complete.connect(self._on_historical_load_complete)
        self.subscriber = VolumeProfileSubscriber(self.signals)
        self.subscriber_thread: Optional[threading.Thread] = None
        
        # Load instruments
        self._load_instruments()
        
        # Setup UI
        self._setup_ui()
        
        # Load historical data first, then start real-time subscriber
        self._load_historical_data_all()
        
        # Start subscriber for real-time updates
        self._start_subscriber()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Update every 500ms
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            self._db_engine = get_engine(DHAN_DB_NAME)
            logger.info(f"Database connection initialized to '{DHAN_DB_NAME}'")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def _load_historical_data_all(self):
        """Load historical data for all instruments."""
        if not self._db_engine:
            logger.warning("No database connection, skipping historical load")
            return
        
        # Determine which date to load: today if market hours, else most recent trading day
        target_date = self._get_target_trading_date()
        market_open = datetime.combine(target_date, MARKET_OPEN_TIME)
        
        self.status_bar.showMessage(f"Loading data for {target_date.strftime('%Y-%m-%d')}...")
        QApplication.processEvents()
        
        for sec_id, profile in self.profiles.items():
            self._load_historical_for_instrument(sec_id, profile, target_date, market_open)
    
    def _get_target_trading_date(self) -> date:
        """
        Get the target date for historical data loading.
        - During market hours with significant data: use today
        - Otherwise: use the most recent date with substantial data in the database
        """
        today = date.today()
        now = datetime.now()
        
        # Check if we're in market hours
        market_open_dt = datetime.combine(today, MARKET_OPEN_TIME)
        market_close_dt = datetime.combine(today, MARKET_CLOSE_TIME)
        in_market_hours = market_open_dt <= now <= market_close_dt
        
        # Check how much data we have for today (only data after market open counts)
        try:
            with self._db_engine.connect() as conn:
                # Count only quotes from after market open today
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM dhan_quotes 
                    WHERE DATE(received_at) = CURDATE()
                      AND TIME(received_at) >= :market_open
                """), {"market_open": MARKET_OPEN_TIME})
                today_market_count = result.scalar() or 0
                
                # If in market hours and significant market data exists, use today
                if in_market_hours and today_market_count >= 100:
                    logger.info(f"Using today's date (in market hours, {today_market_count} market quotes)")
                    return today
                
                # If today has very significant data (>1000 quotes after market open), use today
                if today_market_count > 1000:
                    logger.info(f"Using today's date ({today_market_count} market quotes available)")
                    return today
                
                # Otherwise, find the most recent date with substantial data
                result = conn.execute(text("""
                    SELECT DATE(quote_time) as trade_date, COUNT(*) as cnt
                    FROM dhan_fno_quotes
                    GROUP BY DATE(quote_time)
                    HAVING cnt >= 1000
                    ORDER BY trade_date DESC
                    LIMIT 1
                """))
                row = result.fetchone()
                if row:
                    recent_date = row[0]
                    quote_count = row[1]
                    logger.info(f"Using most recent data date: {recent_date} ({quote_count:,} quotes)")
                    return recent_date
                
                # If no substantial data, try any data
                result = conn.execute(text("""
                    SELECT DATE(quote_time) as trade_date
                    FROM dhan_fno_quotes
                    GROUP BY DATE(quote_time)
                    ORDER BY trade_date DESC
                    LIMIT 1
                """))
                row = result.fetchone()
                if row:
                    recent_date = row[0]
                    logger.info(f"Using most recent data date (fallback): {recent_date}")
                    return recent_date
                
                # Fallback to today
                logger.info("No historical data found, using today")
                return today
                
        except Exception as e:
            logger.error(f"Error determining target date: {e}")
            return today
    
    def _load_historical_for_instrument(self, security_id: int, profile: VolumeProfileData,
                                        target_date: date, market_open: datetime):
        """Load historical quotes for a single instrument."""
        try:
            with self._db_engine.connect() as conn:
                # First, try to get data from market open (9:15 AM)
                # If not available, get all data from today
                result = conn.execute(text("""
                    SELECT ltp, volume, quote_time
                    FROM dhan_fno_quotes
                    WHERE security_id = :sec_id
                      AND DATE(quote_time) = :target_date
                      AND quote_time >= :market_open
                    ORDER BY quote_time ASC
                """), {"sec_id": security_id, "target_date": target_date, "market_open": market_open})
                
                rows = result.fetchall()
                
                # If no data from market open, try all data for target date
                if not rows:
                    result = conn.execute(text("""
                        SELECT ltp, volume, received_at
                        FROM dhan_quotes
                        WHERE security_id = :sec_id
                          AND DATE(received_at) = :target_date
                        ORDER BY received_at ASC
                    """), {"sec_id": security_id, "target_date": target_date})
                    rows = result.fetchall()
                
                if rows:
                    logger.info(f"Loading {len(rows)} historical quotes for {profile.symbol}")
                    
                    prev_volume = 0
                    for row in rows:
                        ltp = float(row[0])
                        volume = int(row[1]) if row[1] else 0
                        
                        profile.add_historical_quote(ltp, volume, prev_volume)
                        prev_volume = volume
                    
                    profile.finalize_historical_load()
                else:
                    logger.info(f"No historical data for {profile.symbol} on {target_date}")
                    profile.historical_loaded = True
                    
        except Exception as e:
            logger.error(f"Error loading historical data for {security_id}: {e}")
            profile.historical_loaded = True
    
    def _on_historical_load_complete(self, message: str):
        """Handle historical load complete signal."""
        self.status_bar.showMessage(message)
        self._update_display()

    def _load_instruments(self):
        """Load instrument names."""
        try:
            selector = InstrumentSelector()
            
            # Nifty futures
            for inst in selector.get_nifty_futures(expiries=[0, 1, 2]):
                sec_id = inst['security_id']
                name = inst.get('display_name', inst['symbol'])
                self.instrument_names[sec_id] = name
                
                # Initialize profile with 10 point bins for index futures
                profile = VolumeProfileData(security_id=sec_id, symbol=name)
                profile.tick_size = 10.0  # 10 point bins
                self.profiles[sec_id] = profile
            
            # Bank Nifty futures  
            for inst in selector.get_banknifty_futures(expiries=[0, 1, 2]):
                sec_id = inst['security_id']
                name = inst.get('display_name', inst['symbol'])
                self.instrument_names[sec_id] = name
                
                profile = VolumeProfileData(security_id=sec_id, symbol=name)
                profile.tick_size = 10.0  # 10 point bins
                self.profiles[sec_id] = profile
            
            # MCX Commodity futures
            for inst in selector.get_major_commodity_futures(expiries=[0, 1]):
                sec_id = inst['security_id']
                name = inst.get('display_name', inst['symbol'])
                underlying = inst.get('underlying_symbol', '')
                self.instrument_names[sec_id] = name
                
                profile = VolumeProfileData(security_id=sec_id, symbol=name)
                # Set appropriate tick sizes for different commodities
                if 'GOLD' in underlying:
                    profile.tick_size = 10.0  # Rs 10 bins for Gold
                elif 'SILVER' in underlying:
                    profile.tick_size = 100.0  # Rs 100 bins for Silver
                elif 'CRUDE' in underlying:
                    profile.tick_size = 10.0  # Rs 10 bins for Crude
                elif 'NATURAL' in underlying:
                    profile.tick_size = 1.0  # Rs 1 bins for Natural Gas
                elif 'COPPER' in underlying:
                    profile.tick_size = 1.0  # Rs 1 bins for Copper
                else:
                    profile.tick_size = 1.0  # Default Rs 1 bins
                self.profiles[sec_id] = profile
            
            # Nifty 50 stocks
            for inst in selector.get_nifty50_stocks():
                sec_id = inst['security_id']
                name = inst.get('display_name', inst['symbol'])
                self.instrument_names[sec_id] = name
                
                profile = VolumeProfileData(security_id=sec_id, symbol=name)
                profile.tick_size = 0.5  # Rs 0.50 bins for stocks
                self.profiles[sec_id] = profile
            
            logger.info(f"Loaded {len(self.instrument_names)} instruments")
            
        except Exception as e:
            logger.error(f"Failed to load instruments: {e}")
    
    def _setup_ui(self):
        """Setup the UI."""
        self.setWindowTitle("📊 Volume Profile Visualizer")
        self.setMinimumSize(1000, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Splitter for quote stream and volume profile
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Volume profile widget
        self.profile_widget = VolumeProfileWidget()
        splitter.addWidget(self.profile_widget)
        
        # Right: Quote stream panel
        quote_panel = self._create_quote_stream_panel()
        splitter.addWidget(quote_panel)
        
        # Set splitter sizes (80% for profile, 20% for quote stream)
        splitter.setSizes([800, 200])
        splitter.setStretchFactor(0, 1)  # Profile stretches
        splitter.setStretchFactor(1, 0)  # Quote panel doesn't stretch
        
        main_layout.addWidget(splitter, stretch=1)
        
        # Stats bar
        stats_bar = self._create_stats_bar()
        main_layout.addWidget(stats_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Connecting to Redis...")
    
    def _create_quote_stream_panel(self) -> QWidget:
        """Create the quote stream panel showing recent quotes."""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #2d2d44;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        panel.setMinimumWidth(250)
        panel.setMaximumWidth(320)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Title
        title = QLabel("📡 Quote Stream")
        title.setStyleSheet("color: #00E5FF; font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # Last update time
        self.last_update_label = QLabel("Last: --:--:--")
        self.last_update_label.setStyleSheet("color: #FFFF00; font-size: 14px; font-weight: bold; padding: 3px;")
        layout.addWidget(self.last_update_label)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #555;")
        layout.addWidget(sep)
        
        # Quote list (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #252538;
                border: none;
            }
            QScrollBar:vertical {
                width: 12px;
                background: #1a1a2e;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #666;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.quote_list_widget = QWidget()
        self.quote_list_widget.setStyleSheet("background-color: #252538;")
        self.quote_list_layout = QVBoxLayout(self.quote_list_widget)
        self.quote_list_layout.setContentsMargins(2, 2, 2, 2)
        self.quote_list_layout.setSpacing(3)
        self.quote_list_layout.addStretch()
        
        scroll.setWidget(self.quote_list_widget)
        layout.addWidget(scroll, stretch=1)
        
        # Store quote labels (max 100 recent quotes for scrolling)
        self.quote_labels = []
        self.max_quote_history = 100
        
        return panel
    
    def _add_quote_to_stream(self, ltp: float, buy_vol: int, sell_vol: int, timestamp: str):
        """Add a quote entry to the stream panel."""
        # Create label for this quote
        quote_text = f"{timestamp}\n{ltp:.2f}  {buy_vol:,} x {sell_vol:,}"
        
        label = QLabel(quote_text)
        
        # Color based on buy/sell - brighter colors for better visibility
        if buy_vol > sell_vol:
            bg_color = "rgba(0, 230, 118, 0.25)"  # Bright green tint
            border_color = "#00E676"
            text_color = "#E0FFE0"  # Light green text
        elif sell_vol > buy_vol:
            bg_color = "rgba(255, 82, 82, 0.25)"  # Bright red tint
            border_color = "#FF5252"
            text_color = "#FFE0E0"  # Light red text
        else:
            bg_color = "rgba(200, 200, 200, 0.2)"  # Grey tint
            border_color = "#AAAAAA"
            text_color = "#FFFFFF"  # White text
        
        label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: 13px;
                font-family: Consolas;
                font-weight: bold;
                padding: 6px;
                background-color: {bg_color};
                border-left: 4px solid {border_color};
                border-radius: 3px;
            }}
        """)
        
        # Insert at top (after removing stretch)
        self.quote_list_layout.insertWidget(0, label)
        self.quote_labels.insert(0, label)
        
        # Remove old quotes if exceeding max
        while len(self.quote_labels) > self.max_quote_history:
            old_label = self.quote_labels.pop()
            self.quote_list_layout.removeWidget(old_label)
            old_label.deleteLater()
        
        # Update last update time
        self.last_update_label.setText(f"Last: {timestamp}")
    
    def _create_header(self) -> QWidget:
        """Create header with controls."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("📊 Real-Time Volume Profile")
        title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Instrument selector
        layout.addWidget(QLabel("<span style='color: white;'>Instrument:</span>"))
        self.instrument_combo = QComboBox()
        self.instrument_combo.setMinimumWidth(250)
        self.instrument_combo.setMaxVisibleItems(30)  # Show more items in dropdown
        self.instrument_combo.setStyleSheet("""
            QComboBox {
                font-size: 13px;
                font-weight: bold;
                padding: 5px 10px;
                background-color: #2D2D30;
                color: #FFFFFF;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QComboBox:hover {
                border: 1px solid #00BCD4;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #00BCD4;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E1E;
                color: #FFFFFF;
                selection-background-color: #0078D4;
                selection-color: #FFFFFF;
                border: 1px solid #555;
                min-width: 280px;
                font-size: 13px;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3D3D40;
            }
        """)
        for sec_id, name in sorted(self.instrument_names.items(), key=lambda x: x[1]):
            self.instrument_combo.addItem(name, sec_id)
        self.instrument_combo.currentIndexChanged.connect(self._on_instrument_changed)
        layout.addWidget(self.instrument_combo)
        
        # Tick size spinner (bin size in points)
        layout.addWidget(QLabel("<span style='color: white;'>Bin Size:</span>"))
        self.tick_spin = QSpinBox()
        self.tick_spin.setRange(5, 100)
        self.tick_spin.setValue(10)  # Default 10 points
        self.tick_spin.setSingleStep(5)
        self.tick_spin.setSuffix(" pts")
        self.tick_spin.valueChanged.connect(self._on_tick_size_changed)
        layout.addWidget(self.tick_spin)
        
        # Reset button
        reset_btn = QPushButton("🔄 Reset")
        reset_btn.clicked.connect(self._reset_profile)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        layout.addWidget(reset_btn)
        
        return header
    
    def _create_stats_bar(self) -> QWidget:
        """Create stats bar."""
        stats = QFrame()
        stats.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        layout = QHBoxLayout(stats)
        
        self.ltp_label = QLabel("LTP: -")
        self.ltp_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.ltp_label)
        
        self.open_label = QLabel("Open: -")
        layout.addWidget(self.open_label)
        
        self.high_label = QLabel("High: -")
        self.high_label.setStyleSheet("color: #28a745;")
        layout.addWidget(self.high_label)
        
        self.low_label = QLabel("Low: -")
        self.low_label.setStyleSheet("color: #dc3545;")
        layout.addWidget(self.low_label)
        
        layout.addStretch()
        
        self.poc_label = QLabel("POC: -")
        self.poc_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        layout.addWidget(self.poc_label)
        
        self.va_label = QLabel("VA: -")
        self.va_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.va_label)
        
        self.volume_label = QLabel("Volume: -")
        layout.addWidget(self.volume_label)
        
        return stats
    
    def _start_subscriber(self):
        """Start the Redis subscriber in a background thread."""
        def run_subscriber():
            try:
                if self.subscriber.connect():
                    self.subscriber.subscribe([CHANNEL_QUOTES])
                    self.subscriber.run()
            except Exception as e:
                logger.error(f"Subscriber error: {e}")
        
        self.subscriber_thread = threading.Thread(target=run_subscriber, daemon=True)
        self.subscriber_thread.start()
    
    def _on_quote(self, quote: QuoteData):
        """Handle incoming quote."""
        sec_id = quote.security_id
        
        # Initialize profile if needed
        if sec_id not in self.profiles:
            name = self.instrument_names.get(sec_id, f"ID:{sec_id}")
            self.profiles[sec_id] = VolumeProfileData(security_id=sec_id, symbol=name)
        
        # Get profile before and after for delta calculation
        profile = self.profiles[sec_id]
        prev_buy = profile.total_buy_volume
        prev_sell = profile.total_sell_volume
        
        # Update profile
        profile.add_quote(quote)
        
        # Calculate deltas for this quote
        buy_delta = profile.total_buy_volume - prev_buy
        sell_delta = profile.total_sell_volume - prev_sell
        
        # Add to quote stream if this is the current instrument
        if sec_id == self.current_instrument and (buy_delta > 0 or sell_delta > 0):
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._add_quote_to_stream(quote.ltp, buy_delta, sell_delta, timestamp)
        
        # Set current instrument if none selected
        if self.current_instrument is None:
            self.current_instrument = sec_id
            # Update combo box
            idx = self.instrument_combo.findData(sec_id)
            if idx >= 0:
                self.instrument_combo.setCurrentIndex(idx)
    
    def _on_instrument_changed(self, index: int):
        """Handle instrument selection change."""
        sec_id = self.instrument_combo.currentData()
        self.current_instrument = sec_id
        # Update spinner to match current profile's tick size
        if sec_id in self.profiles:
            self.tick_spin.blockSignals(True)
            self.tick_spin.setValue(int(self.profiles[sec_id].tick_size))
            self.tick_spin.blockSignals(False)
        self._update_display()
    
    def _on_tick_size_changed(self, value: int):
        """Handle tick size (bin size) change."""
        if self.current_instrument and self.current_instrument in self.profiles:
            # Reset and rebuild profile with new tick size
            name = self.profiles[self.current_instrument].symbol
            self.profiles[self.current_instrument] = VolumeProfileData(
                security_id=self.current_instrument,
                symbol=name
            )
            self.profiles[self.current_instrument].tick_size = float(value)  # Direct point value
            self._update_display()
    
    def _reset_profile(self):
        """Reset current profile and reload historical data."""
        if self.current_instrument and self.current_instrument in self.profiles:
            name = self.profiles[self.current_instrument].symbol
            tick_size = self.profiles[self.current_instrument].tick_size
            
            # Create new profile
            self.profiles[self.current_instrument] = VolumeProfileData(
                security_id=self.current_instrument,
                symbol=name
            )
            self.profiles[self.current_instrument].tick_size = tick_size
            
            # Reload historical data
            self.status_bar.showMessage("📥 Reloading historical data...")
            QApplication.processEvents()
            
            today = date.today()
            market_open = datetime.combine(today, MARKET_OPEN_TIME)
            self._load_historical_for_instrument(
                self.current_instrument, 
                self.profiles[self.current_instrument],
                market_open
            )
            
            self._update_display()
    
    def _update_display(self):
        """Update the display."""
        if self.current_instrument and self.current_instrument in self.profiles:
            profile = self.profiles[self.current_instrument]
            
            # Update profile widget
            self.profile_widget.set_profile(profile)
            
            # Update stats
            self.ltp_label.setText(f"LTP: {profile.last_price:.2f}")
            self.open_label.setText(f"Open: {profile.open_price:.2f}")
            self.high_label.setText(f"High: {profile.high_price:.2f}")
            self.low_label.setText(f"Low: {profile.low_price:.2f}" if profile.low_price != float('inf') else "Low: -")
            self.poc_label.setText(f"POC: {profile.poc_price:.2f}")
            self.va_label.setText(f"VA: {profile.value_area_low:.2f} - {profile.value_area_high:.2f}")
            self.volume_label.setText(f"Volume: {profile.total_volume:,}")
            
            # Update status bar with historical and real-time info
            price_levels = len(profile.volume_at_price)
            hist_info = f"Hist: {profile.historical_quote_count:,}" if profile.historical_loaded else "Loading..."
            buy_pct = (profile.total_buy_volume / profile.total_volume * 100) if profile.total_volume > 0 else 0
            sell_pct = (profile.total_sell_volume / profile.total_volume * 100) if profile.total_volume > 0 else 0
            
            self.status_bar.showMessage(
                f"🟢 LIVE | {hist_info} | RT Updates: {profile.update_count:,} | "
                f"Levels: {price_levels} | "
                f"Buy: {buy_pct:.1f}% | Sell: {sell_pct:.1f}% | "
                f"Bins: {profile.tick_size:.0f} pts | "
                f"{datetime.now().strftime('%H:%M:%S')}"
            )
    
    def closeEvent(self, event):
        """Handle window close."""
        self.subscriber.stop()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    visualizer = VolumeProfileVisualizer()
    visualizer.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
