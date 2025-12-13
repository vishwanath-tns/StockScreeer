"""
Volume Profile Time Series Chart
================================
Displays 5-minute volume profiles along a time axis.

Features:
- Each 5-minute period gets its own volume profile
- Shows VAH, VAL, and POC for each profile
- POC line extends to the right until next profile
- Configurable number of price bins
- Real-time updates from database and Redis
- Scrollable chart

Usage:
    python -m dhan_trading.visualizers.volume_profile_chart
"""
import os
import sys
import signal
import logging
from datetime import datetime, date, time as dt_time, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFrame, QStatusBar, QSpinBox,
    QSlider, QSizePolicy
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

# Market timing
MARKET_OPEN_TIME = dt_time(9, 15)
MARKET_CLOSE_TIME = dt_time(15, 30)

# Chart settings
DEFAULT_INTERVAL_MINUTES = 5
DEFAULT_NUM_BINS = 20
MAX_VISIBLE_PROFILES = 50


def calculate_tick_size(price: float) -> float:
    """
    Calculate appropriate tick size based on instrument price.
    Similar to Volume Profile Visualizer's logic.
    
    This ensures reasonable number of bins for any price level.
    """
    if price <= 0:
        return 1.0
    
    # Determine tick size based on price magnitude
    if price > 50000:      # Bank Nifty futures, high-value stocks
        return 50.0
    elif price > 20000:    # Nifty futures, expensive stocks
        return 25.0
    elif price > 10000:
        return 10.0
    elif price > 5000:
        return 5.0
    elif price > 1000:
        return 2.0
    elif price > 500:
        return 1.0
    elif price > 100:
        return 0.5
    elif price > 50:
        return 0.25
    else:
        return 0.10


@dataclass
class VolumeProfile:
    """Volume profile for a time period."""
    start_time: datetime
    end_time: datetime
    
    # Price -> Volume mapping
    volume_at_price: Dict[float, int] = field(default_factory=dict)
    buy_volume_at_price: Dict[float, int] = field(default_factory=dict)
    sell_volume_at_price: Dict[float, int] = field(default_factory=dict)
    
    # Stats
    high_price: float = 0.0
    low_price: float = float('inf')
    open_price: float = 0.0
    close_price: float = 0.0
    total_volume: int = 0
    
    # POC and Value Area
    poc_price: float = 0.0
    poc_volume: int = 0
    vah_price: float = 0.0  # Value Area High
    val_price: float = 0.0  # Value Area Low
    
    # Tick tracking
    last_price: float = 0.0
    last_tick_direction: int = 0
    tick_count: int = 0
    
    # The tick size used for this profile's bins
    tick_size: float = 10.0
    
    def add_tick(self, price: float, quantity: int, tick_size: float):
        """Add a tick to the profile."""
        # Store tick_size for later reference
        self.tick_size = tick_size
        # Set open price
        if self.open_price == 0.0:
            self.open_price = price
        
        # Update OHLC
        self.high_price = max(self.high_price, price)
        if self.low_price == float('inf'):
            self.low_price = price
        else:
            self.low_price = min(self.low_price, price)
        self.close_price = price
        
        # Determine tick direction
        tick_dir = self._get_tick_direction(price)
        self.last_price = price
        
        # Bucket price
        bucketed_price = round(price / tick_size) * tick_size
        
        # Add volume
        self.volume_at_price[bucketed_price] = self.volume_at_price.get(bucketed_price, 0) + quantity
        self.total_volume += quantity
        self.tick_count += 1
        
        # Buy/Sell attribution
        if tick_dir >= 0:
            self.buy_volume_at_price[bucketed_price] = self.buy_volume_at_price.get(bucketed_price, 0) + quantity
        else:
            self.sell_volume_at_price[bucketed_price] = self.sell_volume_at_price.get(bucketed_price, 0) + quantity
    
    def _get_tick_direction(self, price: float) -> int:
        """Get tick direction (1=up, -1=down, 0=same)."""
        if self.last_price == 0.0:
            self.last_tick_direction = 1
            return 1
        if price > self.last_price:
            self.last_tick_direction = 1
            return 1
        elif price < self.last_price:
            self.last_tick_direction = -1
            return -1
        return self.last_tick_direction
    
    def finalize(self):
        """Calculate POC and Value Area."""
        if not self.volume_at_price:
            return
        
        # Find POC
        self.poc_price = max(self.volume_at_price.keys(), key=lambda p: self.volume_at_price[p])
        self.poc_volume = self.volume_at_price[self.poc_price]
        
        # Calculate Value Area (70%)
        self._calculate_value_area()
    
    def _calculate_value_area(self):
        """Calculate Value Area High and Low (70% of volume)."""
        if not self.volume_at_price or self.total_volume == 0:
            return
        
        target_volume = self.total_volume * 0.7
        sorted_prices = sorted(self.volume_at_price.keys())
        
        if not sorted_prices:
            return
        
        # Find POC index
        poc_idx = sorted_prices.index(self.poc_price) if self.poc_price in sorted_prices else len(sorted_prices) // 2
        
        # Expand from POC
        low_idx = poc_idx
        high_idx = poc_idx
        current_volume = self.volume_at_price.get(sorted_prices[poc_idx], 0)
        
        while current_volume < target_volume and (low_idx > 0 or high_idx < len(sorted_prices) - 1):
            # Get volume above and below
            vol_above = self.volume_at_price.get(sorted_prices[high_idx + 1], 0) if high_idx < len(sorted_prices) - 1 else 0
            vol_below = self.volume_at_price.get(sorted_prices[low_idx - 1], 0) if low_idx > 0 else 0
            
            # Expand in direction of higher volume
            if vol_above >= vol_below and high_idx < len(sorted_prices) - 1:
                high_idx += 1
                current_volume += vol_above
            elif low_idx > 0:
                low_idx -= 1
                current_volume += vol_below
            else:
                break
        
        self.val_price = sorted_prices[low_idx]
        self.vah_price = sorted_prices[high_idx]
    
    def get_normalized_bars(self, tick_size: float = None) -> List[Tuple[float, float, int, int, int]]:
        """
        Get volume bars with buy/sell split.
        Uses the profile's own tick_size if not specified.
        Returns: List of (price, total_vol, buy_vol, sell_vol, max_vol_for_scaling)
        """
        if not self.volume_at_price:
            return []
        
        # Use profile's tick_size if not specified
        ts = tick_size if tick_size is not None else self.tick_size
        
        max_vol = max(self.volume_at_price.values()) if self.volume_at_price else 1
        
        bars = []
        for price in sorted(self.volume_at_price.keys(), reverse=True):
            vol = self.volume_at_price[price]
            buy_vol = self.buy_volume_at_price.get(price, 0)
            sell_vol = self.sell_volume_at_price.get(price, 0)
            bars.append((price, vol, buy_vol, sell_vol, max_vol))
        
        return bars


class VolumeProfileChartWidget(QWidget):
    """Widget that draws multiple 5-minute volume profiles like Volume Profile Visualizer."""
    
    scroll_changed = pyqtSignal(int, int, str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profiles: List[VolumeProfile] = []
        self.visible_profiles = 12  # Show 12 profiles (1 hour)
        self.scroll_offset = 0
        self.auto_scroll = True
        self.num_bins = DEFAULT_NUM_BINS
        self.tick_size = 10.0
        self.current_price = 0.0  # Current market price for indicator
        
        self.setMinimumSize(800, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Colors matching Volume Profile Visualizer
        self.bg_color = QColor(26, 26, 46)
        self.grid_color = QColor(60, 60, 80)
        self.text_color = QColor(200, 200, 200)
        self.buy_color = QColor(0, 200, 83)  # Green
        self.sell_color = QColor(255, 82, 82)  # Red
        self.poc_color = QColor(255, 214, 0)  # Yellow
        self.vah_color = QColor(0, 188, 212)  # Cyan
        self.val_color = QColor(255, 152, 0)  # Orange
        self.current_price_color = QColor(255, 255, 255)  # White for current price
        
        self.setMouseTracking(True)
        self._hover_profile_idx = -1
    
    def set_current_price(self, price: float):
        """Set current market price for indicator."""
        self.current_price = price
        self.update()
    
    def set_profiles(self, profiles: List[VolumeProfile]):
        """Set all profiles."""
        self.profiles = profiles
        if self.auto_scroll:
            self.scroll_offset = 0
        self.update()
        self._emit_scroll_changed()
    
    def add_profile(self, profile: VolumeProfile):
        """Add a new profile."""
        self.profiles.append(profile)
        if self.auto_scroll:
            self.scroll_offset = 0
        self.update()
        self._emit_scroll_changed()
    
    def update_last_profile(self, profile: VolumeProfile):
        """Update the last (current) profile."""
        if self.profiles:
            self.profiles[-1] = profile
        else:
            self.profiles.append(profile)
        self.update()
    
    def set_visible_profiles(self, count: int):
        """Set number of visible profiles."""
        self.visible_profiles = max(4, min(count, MAX_VISIBLE_PROFILES))
        self.update()
        self._emit_scroll_changed()
    
    def set_num_bins(self, num: int):
        """Set number of price bins per profile."""
        self.num_bins = max(5, min(num, 50))
        self.update()
    
    def set_tick_size(self, size: float):
        """Set tick size for display."""
        self.tick_size = size
        self.update()
    
    def scroll_to(self, offset: int):
        """Scroll to specific offset."""
        max_offset = max(0, len(self.profiles) - self.visible_profiles)
        self.scroll_offset = max(0, min(offset, max_offset))
        self.auto_scroll = (self.scroll_offset == 0)
        self.update()
        self._emit_scroll_changed()
    
    def scroll_by(self, delta: int):
        """Scroll by delta profiles."""
        self.scroll_to(self.scroll_offset + delta)
    
    def go_to_latest(self):
        """Jump to latest."""
        self.scroll_offset = 0
        self.auto_scroll = True
        self.update()
        self._emit_scroll_changed()
    
    def _emit_scroll_changed(self):
        """Emit scroll changed signal."""
        visible = self._get_visible_profiles()
        if visible:
            start_time = visible[0].start_time.strftime("%H:%M")
            end_time = visible[-1].end_time.strftime("%H:%M")
        else:
            start_time = "--:--"
            end_time = "--:--"
        self.scroll_changed.emit(self.scroll_offset, len(self.profiles), start_time, end_time)
    
    def _format_volume(self, vol: int) -> str:
        """Format volume for display (K, M suffixes)."""
        if vol >= 1_000_000:
            return f"{vol/1_000_000:.1f}M"
        elif vol >= 1_000:
            return f"{vol/1_000:.0f}K"
        else:
            return str(vol)
    
    def _get_visible_profiles(self) -> List[VolumeProfile]:
        """Get currently visible profiles."""
        if not self.profiles:
            return []
        end_idx = len(self.profiles) - self.scroll_offset
        start_idx = max(0, end_idx - self.visible_profiles)
        return self.profiles[start_idx:end_idx]
    
    def wheelEvent(self, event):
        """Handle mouse wheel."""
        delta = event.angleDelta().y()
        if delta > 0:
            self.scroll_by(2)
        else:
            self.scroll_by(-2)
        event.accept()
    
    def paintEvent(self, event):
        """Paint the volume profile chart - styled like Volume Profile Visualizer."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background
        painter.fillRect(0, 0, width, height, self.bg_color)
        
        visible = self._get_visible_profiles()
        if not visible:
            painter.setPen(self.text_color)
            painter.setFont(QFont("Arial", 14))
            painter.drawText(width // 2 - 100, height // 2, "No volume profile data")
            return
        
        # Margins - space for price labels and time labels
        margin_left = 70
        margin_right = 80  # Space for CMP price label on right
        margin_top = 40
        margin_bottom = 45  # Space for time labels
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        # Find global price range across all visible profiles
        all_prices = []
        for p in visible:
            all_prices.extend(p.volume_at_price.keys())
        
        if not all_prices:
            return
        
        price_high = max(all_prices)
        price_low = min(all_prices)
        price_range = price_high - price_low
        if price_range == 0:
            price_range = price_high * 0.01
        
        # Add padding
        padding = price_range * 0.05
        price_high += padding
        price_low -= padding
        price_range = price_high - price_low
        
        # Profile width - leave gap between profiles for clarity
        profile_width = chart_width / len(visible)
        profile_padding = 8  # Padding on each side of profile
        usable_profile_width = profile_width - (profile_padding * 2)  # Width available for bars
        
        # Draw price grid
        self._draw_price_grid(painter, margin_left, margin_top, chart_width, chart_height,
                             price_low, price_high)
        
        # Draw each profile
        poc_points = []  # Track POC points for connecting line
        
        for i, profile in enumerate(visible):
            profile_x_start = margin_left + i * profile_width
            bar_x_start = profile_x_start + profile_padding  # Where bars actually start
            x_center = profile_x_start + profile_width / 2
            
            # Draw time label
            painter.setPen(self.text_color)
            painter.setFont(QFont("Arial", 9))
            time_str = profile.start_time.strftime("%H:%M")
            painter.drawText(int(x_center - 15), height - margin_bottom + 20, time_str)
            
            # Draw vertical separator line at profile boundary
            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DotLine))
            painter.drawLine(int(profile_x_start), margin_top, int(profile_x_start), height - margin_bottom)
            
            # Get bars using profile's own tick_size (auto-calculated from price)
            bars = profile.get_normalized_bars()  # Use profile's tick_size
            if not bars:
                continue
            
            # Find max volume for THIS profile (local scaling)
            local_max_vol = max(b[1] for b in bars) if bars else 1
            
            # Calculate bar height based on tick_size and price range
            # Each bar represents one tick_size worth of price
            # Leave just 1 pixel gap between bins for visual separation
            profile_tick_size = profile.tick_size
            pixels_per_point = chart_height / price_range if price_range > 0 else 1
            bar_height = max(3, pixels_per_point * profile_tick_size - 1)  # -1 for small gap
            
            # Left margin within profile for volume text
            bar_left_margin = 5
            bars_x_start = bar_x_start + bar_left_margin
            bars_usable_width = usable_profile_width - bar_left_margin
            
            # Draw volume bars - SPLIT into buy (green) and sell (red) portions
            for price, total_vol, buy_vol, sell_vol, _ in bars:
                # Price to Y position - center of the bar
                price_y = margin_top + chart_height - ((price - price_low) / price_range * chart_height)
                
                # Calculate bar dimensions - use integers consistently
                bar_h = max(3, int(bar_height))
                bar_y = int(price_y) - bar_h // 2  # Center vertically on price
                
                # Calculate bar width - STRICTLY within usable width
                vol_pct = total_vol / local_max_vol if local_max_vol > 0 else 0
                total_bar_width = max(4, int(vol_pct * bars_usable_width))
                
                # Split into buy and sell portions
                if total_vol > 0:
                    buy_pct = buy_vol / total_vol
                else:
                    buy_pct = 0.5
                
                buy_width = int(total_bar_width * buy_pct)
                sell_width = total_bar_width - buy_width  # Ensure they add up exactly
                
                # Calculate x positions as integers
                buy_x = int(bars_x_start)
                sell_x = buy_x + buy_width
                
                # Draw BUY portion (green) - left side
                if buy_width > 0:
                    painter.fillRect(buy_x, bar_y, buy_width, bar_h, self.buy_color)
                
                # Draw SELL portion (red) - immediately after buy, EXACT same bar_y
                if sell_width > 0:
                    painter.fillRect(sell_x, bar_y, sell_width, bar_h, self.sell_color)
                
                # Draw volume text on bar (white) - Buy x Sell format
                if bar_h >= 12:
                    # Format: Buy x Sell
                    buy_text = self._format_volume(buy_vol)
                    sell_text = self._format_volume(sell_vol)
                    vol_text = f"{buy_text}x{sell_text}"
                    painter.setPen(QColor(255, 255, 255))
                    painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                    # Position text inside the bar
                    text_x = buy_x + 3
                    text_y = bar_y + bar_h - 2
                    painter.drawText(text_x, text_y, vol_text)
            
            # Draw POC line (WHITE, THICKEST) - within profile, extends to end of screen
            if profile.poc_price > 0:
                poc_y = margin_top + chart_height - ((profile.poc_price - price_low) / price_range * chart_height)
                profile_x_end = width - margin_right  # Extend to end of screen
                poc_points.append((bars_x_start, poc_y, profile_x_end, profile.poc_price))
                
                # POC horizontal line - WHITE, THICK (4px) solid line - extends to right edge
                painter.setPen(QPen(QColor(255, 255, 255), 4, Qt.PenStyle.SolidLine))
                painter.drawLine(int(bars_x_start), int(poc_y), width - margin_right, int(poc_y))
            
            # Draw VAH line (cyan, solid, thinner than POC)
            if profile.vah_price > 0:
                vah_y = margin_top + chart_height - ((profile.vah_price - price_low) / price_range * chart_height)
                painter.setPen(QPen(self.vah_color, 2, Qt.PenStyle.SolidLine))
                painter.drawLine(int(bars_x_start), int(vah_y), int(bars_x_start + bars_usable_width), int(vah_y))
            
            # Draw VAL line (orange, solid, thinner than POC)
            if profile.val_price > 0:
                val_y = margin_top + chart_height - ((profile.val_price - price_low) / price_range * chart_height)
                painter.setPen(QPen(self.val_color, 2, Qt.PenStyle.SolidLine))
                painter.drawLine(int(bars_x_start), int(val_y), int(bars_x_start + bars_usable_width), int(val_y))
        
        # POC lines already extend to right edge, no need for separate extension
        
        # Draw CURRENT PRICE indicator line (dashed, less prominent than POC)
        if self.current_price > 0 and price_low <= self.current_price <= price_high:
            cmp_y = margin_top + chart_height - ((self.current_price - price_low) / price_range * chart_height)
            
            # Draw horizontal dashed line across chart (less intrusive)
            painter.setPen(QPen(self.current_price_color, 1, Qt.PenStyle.DashLine))
            painter.drawLine(margin_left, int(cmp_y), width - margin_right, int(cmp_y))
            
            # Draw price label box on right side (within margin area)
            price_text = f"{self.current_price:,.2f}"
            font = QFont("Arial", 9, QFont.Weight.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(price_text)
            text_height = fm.height()
            
            # Background box for price label - positioned in right margin
            label_x = width - margin_right + 5
            label_y = int(cmp_y) - text_height // 2
            
            # Ensure label stays within window bounds
            if label_y < margin_top:
                label_y = margin_top
            if label_y + text_height > height - margin_bottom:
                label_y = height - margin_bottom - text_height
            
            painter.fillRect(label_x - 2, label_y, text_width + 6, text_height, self.current_price_color)
            
            # Price text in black
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(label_x, label_y + text_height - 3, price_text)
            
            # Draw arrow pointing to the line from label
            painter.setBrush(QBrush(self.current_price_color))
            painter.setPen(Qt.PenStyle.NoPen)
            arrow = QPainterPath()
            arrow.moveTo(width - margin_right, cmp_y)
            arrow.lineTo(width - margin_right + 5, cmp_y - 4)
            arrow.lineTo(width - margin_right + 5, cmp_y + 4)
            arrow.closeSubpath()
            painter.drawPath(arrow)
        
        # Draw legend
        self._draw_legend(painter, margin_left, 10)
        
        # Scroll indicator - positioned above bottom margin
        if self.scroll_offset > 0:
            painter.setPen(QPen(QColor(255, 200, 0)))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(width // 2 - 80, height - margin_bottom + 35,
                           f"◄ {self.scroll_offset} profiles ago ►")
    
    def _draw_price_grid(self, painter: QPainter, margin_left: int, margin_top: int,
                        chart_width: int, chart_height: int, price_low: float, price_high: float):
        """Draw price grid lines."""
        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        
        price_range = price_high - price_low
        num_lines = 6
        
        for i in range(num_lines + 1):
            y = margin_top + (i / num_lines) * chart_height
            price = price_high - (i / num_lines) * price_range
            
            painter.drawLine(margin_left, int(y), margin_left + chart_width, int(y))
            
            # Price label
            painter.setPen(self.text_color)
            painter.setFont(QFont("Arial", 9))
            painter.drawText(5, int(y) + 4, f"{price:,.0f}")
            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
    
    def _draw_legend(self, painter: QPainter, x: int, y: int):
        """Draw legend."""
        painter.setFont(QFont("Arial", 9))
        
        # POC
        painter.setPen(self.poc_color)
        painter.drawLine(x, y + 5, x + 20, y + 5)
        painter.setPen(self.text_color)
        painter.drawText(x + 25, y + 9, "POC")
        
        # POC - WHITE thick line
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.drawLine(x, y + 5, x + 20, y + 5)
        painter.setPen(self.text_color)
        painter.drawText(x + 25, y + 9, "POC")
        
        # VAH
        painter.setPen(QPen(self.vah_color, 2))
        painter.drawLine(x + 60, y + 5, x + 80, y + 5)
        painter.setPen(self.text_color)
        painter.drawText(x + 85, y + 9, "VAH")
        
        # VAL
        painter.setPen(QPen(self.val_color, 2))
        painter.drawLine(x + 120, y + 5, x + 140, y + 5)
        painter.setPen(self.text_color)
        painter.drawText(x + 145, y + 9, "VAL")
        
        # CMP (Current Market Price) - dashed
        painter.setPen(QPen(self.current_price_color, 1, Qt.PenStyle.DashLine))
        painter.drawLine(x + 180, y + 5, x + 200, y + 5)
        painter.setPen(self.text_color)
        painter.drawText(x + 205, y + 9, "CMP")
        
        # Buy
        painter.fillRect(x + 245, y, 15, 10, self.buy_color)
        painter.setPen(self.text_color)
        painter.drawText(x + 265, y + 9, "Buy")
        
        # Sell
        painter.fillRect(x + 305, y, 15, 10, self.sell_color)
        painter.setPen(self.text_color)
        painter.drawText(x + 325, y + 9, "Sell")


class ProfileBuilder:
    """Builds volume profiles from ticks."""
    
    def __init__(self, interval_minutes: int = DEFAULT_INTERVAL_MINUTES, tick_size: float = None):
        self.interval_minutes = interval_minutes
        self.tick_size = tick_size  # None means auto-calculate from price
        self.auto_tick_size = tick_size is None
        self.profiles: List[VolumeProfile] = []
        self.current_profile: Optional[VolumeProfile] = None
        self.current_interval_end: Optional[datetime] = None
    
    def set_interval(self, minutes: int):
        """Set interval in minutes."""
        self.interval_minutes = minutes
    
    def set_tick_size(self, size: float):
        """Set tick size for price bucketing. Pass None for auto."""
        self.tick_size = size
        self.auto_tick_size = size is None
    
    def _get_interval_start(self, dt: datetime) -> datetime:
        """Get the start of the interval containing dt."""
        minutes = dt.minute
        interval_start_minute = (minutes // self.interval_minutes) * self.interval_minutes
        return dt.replace(minute=interval_start_minute, second=0, microsecond=0)
    
    def _get_interval_end(self, start: datetime) -> datetime:
        """Get the end of the interval."""
        return start + timedelta(minutes=self.interval_minutes)
    
    def add_tick(self, timestamp: datetime, price: float, quantity: int) -> Optional[VolumeProfile]:
        """
        Add a tick. Returns a completed profile if interval ended.
        """
        # Auto-calculate tick_size from first price if not set
        if self.auto_tick_size and self.tick_size is None:
            self.tick_size = calculate_tick_size(price)
        
        interval_start = self._get_interval_start(timestamp)
        interval_end = self._get_interval_end(interval_start)
        
        # Check if we need a new profile
        if self.current_profile is None or timestamp >= self.current_interval_end:
            # Finalize current profile if exists
            completed = None
            if self.current_profile is not None:
                self.current_profile.finalize()
                self.profiles.append(self.current_profile)
                completed = self.current_profile
            
            # Create new profile
            self.current_profile = VolumeProfile(
                start_time=interval_start,
                end_time=interval_end
            )
            self.current_interval_end = interval_end
            
            # Add tick to new profile
            self.current_profile.add_tick(price, quantity, self.tick_size)
            
            return completed
        
        # Add to current profile
        self.current_profile.add_tick(price, quantity, self.tick_size)
        return None
    
    def get_current_profile(self) -> Optional[VolumeProfile]:
        """Get the in-progress profile."""
        if self.current_profile:
            # Return a copy with finalized stats
            p = VolumeProfile(
                start_time=self.current_profile.start_time,
                end_time=self.current_profile.end_time,
                volume_at_price=self.current_profile.volume_at_price.copy(),
                buy_volume_at_price=self.current_profile.buy_volume_at_price.copy(),
                sell_volume_at_price=self.current_profile.sell_volume_at_price.copy(),
                high_price=self.current_profile.high_price,
                low_price=self.current_profile.low_price,
                open_price=self.current_profile.open_price,
                close_price=self.current_profile.close_price,
                total_volume=self.current_profile.total_volume,
                tick_count=self.current_profile.tick_count,
                tick_size=self.current_profile.tick_size  # Include tick_size
            )
            p.finalize()
            return p
        return None
    
    def get_all_profiles(self) -> List[VolumeProfile]:
        """Get all completed profiles plus current."""
        result = self.profiles.copy()
        current = self.get_current_profile()
        if current:
            result.append(current)
        return result


class VPChartSubscriber(RedisSubscriber):
    """Redis subscriber for volume profile chart."""
    
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


class VolumeProfileChartWindow(QMainWindow):
    """Main window for volume profile chart."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Volume Profile Time Chart")
        self.setMinimumSize(1200, 700)
        
        # State
        self.engine = get_engine(DHAN_DB_NAME)
        self.instruments: Dict[int, dict] = {}
        self.current_security_id: Optional[int] = None
        self.builder = ProfileBuilder()
        self._subscriber: Optional[VPChartSubscriber] = None
        self.signals = QuoteSignals()
        self.last_volume = 0
        
        # Setup
        self._load_instruments()
        self._setup_ui()
        self._setup_connections()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(1000)
        
        # Auto-select first instrument
        if self.instruments:
            self._on_instrument_changed(0)
    
    def _load_instruments(self):
        """Load available instruments."""
        try:
            with self.engine.connect() as conn:
                # First try: Get instruments with quotes TODAY (any amount)
                result = conn.execute(text("""
                    SELECT q.security_id, i.symbol, i.display_name, COUNT(*) as cnt
                    FROM dhan_quotes q
                    LEFT JOIN dhan_instruments i ON q.security_id = i.security_id
                    WHERE DATE(q.received_at) = CURDATE()
                    GROUP BY q.security_id, i.symbol, i.display_name
                    ORDER BY cnt DESC
                    LIMIT 100
                """))
                
                for row in result.fetchall():
                    sec_id = row[0]
                    self.instruments[sec_id] = {
                        'security_id': sec_id,
                        'symbol': row[1] or f'ID:{sec_id}',
                        'display_name': row[2] or row[1] or f'ID:{sec_id}',
                        'quote_count': row[3]
                    }
                
                # If no quotes found, load from dhan_instruments directly for testing
                if not self.instruments:
                    logger.info("No quotes found for today, loading from dhan_instruments...")
                    result = conn.execute(text("""
                        SELECT security_id, symbol, display_name
                        FROM dhan_instruments
                        WHERE segment = 'NSE_FNO' OR segment = 'MCX_COMM'
                        LIMIT 50
                    """))
                    
                    for row in result.fetchall():
                        sec_id = row[0]
                        self.instruments[sec_id] = {
                            'security_id': sec_id,
                            'symbol': row[1] or f'ID:{sec_id}',
                            'display_name': row[2] or row[1] or f'ID:{sec_id}',
                            'quote_count': 0
                        }
                
        except Exception as e:
            logger.error(f"Error loading instruments: {e}")
        
        logger.info(f"Loaded {len(self.instruments)} instruments")
    
    def _setup_ui(self):
        """Setup UI."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Dark theme
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
                min-width: 120px;
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
        controls = self._create_controls()
        main_layout.addWidget(controls)
        
        # Chart
        self.chart = VolumeProfileChartWidget()
        self.chart.scroll_changed.connect(self._on_scroll_changed)
        main_layout.addWidget(self.chart, stretch=1)
        
        # Navigation
        nav = self._create_nav_controls()
        main_layout.addWidget(nav)
        
        # Stats
        stats = self._create_stats_frame()
        main_layout.addWidget(stats)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Select an instrument to start")
    
    def _create_controls(self) -> QWidget:
        """Create top controls."""
        from PyQt6.QtWidgets import QCheckBox
        
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #16213e; border-radius: 10px; padding: 10px; }")
        layout = QHBoxLayout(frame)
        layout.setSpacing(20)
        
        # Instrument
        layout.addWidget(QLabel("Instrument:"))
        self.instrument_combo = QComboBox()
        for sec_id, info in self.instruments.items():
            self.instrument_combo.addItem(f"{info['display_name']} ({info['quote_count']:,})", sec_id)
        layout.addWidget(self.instrument_combo)
        
        layout.addStretch()
        
        # Interval
        layout.addWidget(QLabel("Interval:"))
        self.interval_combo = QComboBox()
        for mins in [1, 3, 5, 10, 15, 30]:
            self.interval_combo.addItem(f"{mins} min", mins)
        self.interval_combo.setCurrentIndex(2)  # Default 5 min
        layout.addWidget(self.interval_combo)
        
        # Auto Tick Size checkbox
        self.auto_tick_cb = QCheckBox("Auto Bin")
        self.auto_tick_cb.setChecked(True)  # Auto by default
        self.auto_tick_cb.setToolTip("Auto-calculate bin size based on instrument price")
        self.auto_tick_cb.stateChanged.connect(self._on_auto_tick_changed)
        layout.addWidget(self.auto_tick_cb)
        
        # Tick size (manual override)
        layout.addWidget(QLabel("Bin Size:"))
        self.tick_size_spin = QSpinBox()
        self.tick_size_spin.setRange(1, 100)
        self.tick_size_spin.setValue(10)
        self.tick_size_spin.setSuffix(" pts")
        self.tick_size_spin.setEnabled(False)  # Disabled when auto
        layout.addWidget(self.tick_size_spin)
        
        # Tick size info label
        self.tick_info_label = QLabel("")
        self.tick_info_label.setStyleSheet("color: #00E5FF;")
        layout.addWidget(self.tick_info_label)
        
        layout.addStretch()
        
        # Refresh
        self.refresh_btn = QPushButton("🔄 Reload")
        layout.addWidget(self.refresh_btn)
        
        return frame
    
    def _on_auto_tick_changed(self, state: int):
        """Handle auto tick checkbox change."""
        self.tick_size_spin.setEnabled(state == 0)  # Enable manual when auto unchecked
        self._load_historical_data()
    
    def _create_nav_controls(self) -> QWidget:
        """Create navigation controls."""
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #16213e; border-radius: 5px; }")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # Scroll buttons
        btn_back = QPushButton("◄◄ -5")
        btn_back.clicked.connect(lambda: self.chart.scroll_by(5))
        layout.addWidget(btn_back)
        
        btn_back_1 = QPushButton("◄ -1")
        btn_back_1.clicked.connect(lambda: self.chart.scroll_by(1))
        layout.addWidget(btn_back_1)
        
        # Position
        self.pos_label = QLabel("Position: Live")
        self.pos_label.setStyleSheet("color: #00E5FF; font-weight: bold;")
        layout.addWidget(self.pos_label)
        
        btn_fwd_1 = QPushButton("► +1")
        btn_fwd_1.clicked.connect(lambda: self.chart.scroll_by(-1))
        layout.addWidget(btn_fwd_1)
        
        btn_fwd = QPushButton("►► +5")
        btn_fwd.clicked.connect(lambda: self.chart.scroll_by(-5))
        layout.addWidget(btn_fwd)
        
        layout.addStretch()
        
        # Visible profiles
        layout.addWidget(QLabel("Visible:"))
        self.visible_slider = QSlider(Qt.Orientation.Horizontal)
        self.visible_slider.setMinimum(4)
        self.visible_slider.setMaximum(MAX_VISIBLE_PROFILES)
        self.visible_slider.setValue(12)
        self.visible_slider.setFixedWidth(150)
        self.visible_slider.valueChanged.connect(self._on_visible_changed)
        layout.addWidget(self.visible_slider)
        
        self.visible_label = QLabel("12")
        layout.addWidget(self.visible_label)
        
        layout.addStretch()
        
        # Live button
        self.live_btn = QPushButton("🔴 LIVE")
        self.live_btn.setStyleSheet("QPushButton { background-color: #c62828; }")
        self.live_btn.clicked.connect(self.chart.go_to_latest)
        layout.addWidget(self.live_btn)
        
        return frame
    
    def _create_stats_frame(self) -> QWidget:
        """Create stats frame."""
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #16213e; border-radius: 10px; padding: 10px; }")
        frame.setMaximumHeight(60)
        layout = QHBoxLayout(frame)
        layout.setSpacing(30)
        
        self.price_label = QLabel("LTP: --")
        self.price_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.price_label)
        
        self.profiles_label = QLabel("Profiles: 0")
        layout.addWidget(self.profiles_label)
        
        self.ticks_label = QLabel("Ticks: 0")
        layout.addWidget(self.ticks_label)
        
        layout.addStretch()
        
        self.time_label = QLabel("--:--:--")
        self.time_label.setStyleSheet("font-size: 14px; color: #FFFF00;")
        layout.addWidget(self.time_label)
        
        return frame
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.instrument_combo.currentIndexChanged.connect(self._on_instrument_changed)
        self.interval_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.tick_size_spin.valueChanged.connect(self._on_settings_changed)
        self.refresh_btn.clicked.connect(self._load_historical_data)
        self.signals.quote_received.connect(self._on_quote)
    
    def _on_instrument_changed(self, index: int):
        """Handle instrument change."""
        if index < 0:
            return
        
        # Stop subscriber
        if self._subscriber:
            self._subscriber.stop()
            self._subscriber = None
        
        self.current_security_id = self.instrument_combo.currentData()
        if not self.current_security_id:
            return
        
        info = self.instruments.get(self.current_security_id, {})
        self.setWindowTitle(f"📊 Volume Profile Chart - {info.get('display_name', 'Unknown')}")
        
        self._load_historical_data()
        self._start_subscriber()
    
    def _on_settings_changed(self):
        """Handle interval or tick size change."""
        interval = self.interval_combo.currentData() or DEFAULT_INTERVAL_MINUTES
        
        if self.auto_tick_cb.isChecked():
            tick_size = None
        else:
            tick_size = self.tick_size_spin.value()
        
        self.builder.set_interval(interval)
        self.builder.set_tick_size(tick_size)
        self._load_historical_data()
    
    def _on_bins_changed(self, value: int):
        """Handle bins change."""
        self.chart.set_num_bins(value)
    
    def _on_visible_changed(self, value: int):
        """Handle visible profiles change."""
        self.chart.set_visible_profiles(value)
        self.visible_label.setText(str(value))
    
    def _on_scroll_changed(self, offset: int, total: int, start_time: str, end_time: str):
        """Handle scroll change."""
        if offset == 0:
            self.pos_label.setText("Position: 🔴 LIVE")
            self.pos_label.setStyleSheet("color: #00E5FF; font-weight: bold;")
            self.live_btn.setEnabled(False)
        else:
            self.pos_label.setText(f"Viewing: {start_time} - {end_time} ({offset} ago)")
            self.pos_label.setStyleSheet("color: #FFD700;")
            self.live_btn.setEnabled(True)
        
        self.profiles_label.setText(f"Profiles: {total}")
    
    def _load_historical_data(self):
        """Load historical data from database."""
        if not self.current_security_id:
            return
        
        self.status_bar.showMessage("Loading historical data...")
        
        interval = self.interval_combo.currentData() or DEFAULT_INTERVAL_MINUTES
        
        # Auto tick size or manual
        if self.auto_tick_cb.isChecked():
            tick_size = None  # Auto-calculate from price
        else:
            tick_size = self.tick_size_spin.value()
        
        # Reset builder
        self.builder = ProfileBuilder(interval, tick_size)
        self.last_volume = 0
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT ltp, ltq, volume, received_at
                    FROM dhan_quotes
                    WHERE security_id = :sec_id
                      AND DATE(received_at) = CURDATE()
                    ORDER BY received_at ASC
                """), {'sec_id': self.current_security_id})
                
                tick_count = 0
                prev_volume = 0
                
                for row in result.fetchall():
                    price = float(row[0])
                    volume = int(row[2])
                    timestamp = row[3]
                    
                    # Calculate volume delta
                    if volume > prev_volume:
                        qty = volume - prev_volume
                        self.builder.add_tick(timestamp, price, qty)
                        tick_count += 1
                    
                    prev_volume = volume
                
                self.last_volume = prev_volume
                
                # Get all profiles
                profiles = self.builder.get_all_profiles()
                self.chart.set_profiles(profiles)
                
                # Get actual tick size used (may be auto-calculated)
                actual_tick_size = self.builder.tick_size
                tick_mode = "auto" if self.auto_tick_cb.isChecked() else "manual"
                
                if tick_count > 0:
                    self.status_bar.showMessage(
                        f"Loaded {tick_count:,} ticks → {len(profiles)} profiles "
                        f"({interval} min interval, {actual_tick_size:.2f} pts bin [{tick_mode}])"
                    )
                else:
                    self.status_bar.showMessage(
                        f"No quotes found for {self.instruments.get(self.current_security_id, {}).get('display_name', 'instrument')} today"
                    )
                
                # Update tick info label
                self.tick_info_label.setText(f"Bin: {actual_tick_size:.2f} pts")
                
                self.ticks_label.setText(f"Ticks: {tick_count:,}")
                
                # Set current price from last profile's close price
                if profiles:
                    last_profile = profiles[-1]
                    if last_profile.close_price > 0:
                        self.chart.set_current_price(last_profile.close_price)
                        self.price_label.setText(f"LTP: {last_profile.close_price:,.2f}")
        
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.status_bar.showMessage(f"Error: {e}")
    
    def _start_subscriber(self):
        """Start Redis subscriber."""
        if not self.current_security_id:
            return
        
        def callback(quote: QuoteData):
            self.signals.quote_received.emit(quote)
        
        self._subscriber = VPChartSubscriber(self.current_security_id, callback)
        self._subscriber.start()
        logger.info(f"Started subscriber for {self.current_security_id}")
    
    def _on_quote(self, quote: QuoteData):
        """Handle real-time quote."""
        volume = int(quote.volume)
        current_price = float(quote.ltp)
        
        # Update current price indicator
        self.chart.set_current_price(current_price)
        
        # Calculate volume delta
        if volume > self.last_volume:
            qty = volume - self.last_volume
            completed = self.builder.add_tick(datetime.now(), current_price, qty)
            
            if completed:
                # A new profile was completed
                profiles = self.builder.get_all_profiles()
                self.chart.set_profiles(profiles)
            else:
                # Update current profile
                current = self.builder.get_current_profile()
                if current:
                    self.chart.update_last_profile(current)
            
            self.last_volume = volume
        
        self.price_label.setText(f"LTP: {current_price:,.2f}")
    
    def _update_display(self):
        """Periodic display update."""
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))
        
        # Update current profile display
        current = self.builder.get_current_profile()
        if current:
            self.chart.update_last_profile(current)
    
    def closeEvent(self, event):
        """Handle close."""
        if self._subscriber:
            self._subscriber.stop()
        self.update_timer.stop()
        event.accept()


def main():
    """Main entry point."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = VolumeProfileChartWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
