"""
Bollinger Bands Chart Widget

Reusable chart component for displaying price with BB overlay.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen

import pandas as pd
import numpy as np

try:
    import pyqtgraph as pg
    from pyqtgraph import DateAxisItem
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

from ..models.bb_models import BollingerBands
from ..models.signal_models import BBSignal, SignalType


logger = logging.getLogger(__name__)


# Chart colors
COLORS = {
    'price': '#2196F3',           # Blue
    'upper_band': '#4CAF50',      # Green
    'middle_band': '#FF9800',     # Orange
    'lower_band': '#F44336',      # Red
    'fill': (100, 149, 237, 50),  # Light blue fill
    'percent_b': '#9C27B0',       # Purple
    'bandwidth': '#00BCD4',       # Cyan
    'volume': '#607D8B',          # Blue grey
    'buy_signal': '#4CAF50',      # Green
    'sell_signal': '#F44336',     # Red
    'squeeze': '#FFEB3B',         # Yellow
    'background': '#1E1E1E',      # Dark background
    'grid': '#333333'             # Grid lines
}


class BBChartWidget(QWidget):
    """
    Interactive Bollinger Bands chart widget.
    
    Features:
    - Price with BB overlay (upper, middle, lower bands)
    - %b indicator subplot
    - BandWidth indicator subplot
    - Volume bars (optional)
    - Buy/sell signal markers
    - Squeeze highlighting
    """
    
    # Signals
    dateSelected = pyqtSignal(date)
    signalClicked = pyqtSignal(object)  # BBSignal
    
    def __init__(self, parent=None, show_volume: bool = True):
        """
        Initialize chart widget.
        
        Args:
            parent: Parent widget
            show_volume: Show volume bars
        """
        super().__init__(parent)
        
        if not PYQTGRAPH_AVAILABLE:
            raise ImportError("pyqtgraph required for charts. Install with: pip install pyqtgraph")
        
        self.show_volume = show_volume
        self._data = None
        self._signals = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the chart UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create graphics layout widget
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.setBackground(COLORS['background'])
        
        # Enable antialiasing
        pg.setConfigOptions(antialias=True)
        
        # Create subplots
        self._create_price_plot()
        self._create_percent_b_plot()
        self._create_bandwidth_plot()
        
        if self.show_volume:
            self._create_volume_plot()
        
        # Link X axes
        self.pb_plot.setXLink(self.price_plot)
        self.bw_plot.setXLink(self.price_plot)
        if self.show_volume:
            self.volume_plot.setXLink(self.price_plot)
        
        layout.addWidget(self.graphics_widget)
        
        # Create info bar
        self.info_bar = self._create_info_bar()
        layout.addWidget(self.info_bar)
    
    def _create_price_plot(self):
        """Create main price chart with BB overlay."""
        self.price_plot = self.graphics_widget.addPlot(row=0, col=0)
        self.price_plot.setLabel('left', 'Price')
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Set relative height
        self.price_plot.setMinimumHeight(300)
        
        # Create plot items
        self.price_line = self.price_plot.plot(pen=pg.mkPen(COLORS['price'], width=2))
        self.upper_band = self.price_plot.plot(pen=pg.mkPen(COLORS['upper_band'], width=1, style=Qt.PenStyle.DashLine))
        self.middle_band = self.price_plot.plot(pen=pg.mkPen(COLORS['middle_band'], width=1))
        self.lower_band = self.price_plot.plot(pen=pg.mkPen(COLORS['lower_band'], width=1, style=Qt.PenStyle.DashLine))
        
        # Fill between bands
        self.band_fill = pg.FillBetweenItem(
            self.upper_band, self.lower_band,
            brush=pg.mkBrush(*COLORS['fill'])
        )
        self.price_plot.addItem(self.band_fill)
        
        # Signal markers
        self.buy_markers = pg.ScatterPlotItem(
            size=12, pen=pg.mkPen(None),
            brush=pg.mkBrush(COLORS['buy_signal']),
            symbol='t'  # Triangle up
        )
        self.sell_markers = pg.ScatterPlotItem(
            size=12, pen=pg.mkPen(None),
            brush=pg.mkBrush(COLORS['sell_signal']),
            symbol='t1'  # Triangle down
        )
        self.price_plot.addItem(self.buy_markers)
        self.price_plot.addItem(self.sell_markers)
        
        # Crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.price_plot.addItem(self.vLine, ignoreBounds=True)
        self.price_plot.addItem(self.hLine, ignoreBounds=True)
        
        # Mouse tracking
        self.price_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
    
    def _create_percent_b_plot(self):
        """Create %b indicator subplot."""
        self.graphics_widget.nextRow()
        self.pb_plot = self.graphics_widget.addPlot(row=1, col=0)
        self.pb_plot.setLabel('left', '%b')
        self.pb_plot.setMaximumHeight(100)
        self.pb_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Reference lines at 0, 0.5, 1
        self.pb_plot.addLine(y=0, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine))
        self.pb_plot.addLine(y=0.5, pen=pg.mkPen('gray', style=Qt.PenStyle.DotLine))
        self.pb_plot.addLine(y=1, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine))
        
        self.pb_line = self.pb_plot.plot(pen=pg.mkPen(COLORS['percent_b'], width=2))
    
    def _create_bandwidth_plot(self):
        """Create BandWidth indicator subplot."""
        self.graphics_widget.nextRow()
        self.bw_plot = self.graphics_widget.addPlot(row=2, col=0)
        self.bw_plot.setLabel('left', 'BW')
        self.bw_plot.setMaximumHeight(80)
        self.bw_plot.showGrid(x=True, y=True, alpha=0.3)
        
        self.bw_line = self.bw_plot.plot(pen=pg.mkPen(COLORS['bandwidth'], width=2))
        
        # Squeeze regions will be highlighted
        self.squeeze_regions = []
    
    def _create_volume_plot(self):
        """Create volume bars subplot."""
        self.graphics_widget.nextRow()
        self.volume_plot = self.graphics_widget.addPlot(row=3, col=0)
        self.volume_plot.setLabel('left', 'Vol')
        self.volume_plot.setMaximumHeight(60)
        self.volume_plot.showGrid(x=True, y=True, alpha=0.3)
        
        self.volume_bars = pg.BarGraphItem(
            x=[], height=[], width=0.8,
            brush=pg.mkBrush(COLORS['volume'])
        )
        self.volume_plot.addItem(self.volume_bars)
    
    def _create_info_bar(self) -> QFrame:
        """Create info bar at bottom."""
        frame = QFrame()
        frame.setStyleSheet(f"background: {COLORS['background']}; color: white; padding: 5px;")
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.date_label = QLabel("Date: --")
        self.price_label = QLabel("Close: --")
        self.pb_label = QLabel("%b: --")
        self.bw_label = QLabel("BW: --")
        self.band_label = QLabel("Bands: --")
        
        for label in [self.date_label, self.price_label, self.pb_label, 
                      self.bw_label, self.band_label]:
            layout.addWidget(label)
        
        layout.addStretch()
        
        return frame
    
    def set_data(self, symbol: str, 
                 bb_data: List[BollingerBands],
                 volume_data: List[Tuple[date, float]] = None):
        """
        Set chart data.
        
        Args:
            symbol: Stock symbol
            bb_data: List of BollingerBands (any order)
            volume_data: Optional list of (date, volume) tuples
        """
        if not bb_data:
            return
        
        # Sort by date (oldest first)
        sorted_data = sorted(bb_data, key=lambda x: x.date)
        
        # Convert to arrays
        dates = [datetime.combine(bb.date, datetime.min.time()).timestamp() 
                 for bb in sorted_data]
        close = [bb.close for bb in sorted_data]
        upper = [bb.upper for bb in sorted_data]
        middle = [bb.middle for bb in sorted_data]
        lower = [bb.lower for bb in sorted_data]
        percent_b = [bb.percent_b for bb in sorted_data]
        bandwidth = [bb.bandwidth for bb in sorted_data]
        
        # Update price plot
        self.price_line.setData(dates, close)
        self.upper_band.setData(dates, upper)
        self.middle_band.setData(dates, middle)
        self.lower_band.setData(dates, lower)
        
        # Update %b plot
        self.pb_line.setData(dates, percent_b)
        
        # Update bandwidth plot
        self.bw_line.setData(dates, bandwidth)
        
        # Update volume if provided
        if volume_data and self.show_volume:
            vol_dates = [datetime.combine(d, datetime.min.time()).timestamp() 
                        for d, v in volume_data]
            vol_values = [v for d, v in volume_data]
            self.volume_bars.setOpts(x=vol_dates, height=vol_values, width=86400*0.8)
        
        # Store data reference
        self._data = sorted_data
        
        # Highlight squeeze regions
        self._highlight_squeeze_regions(dates, sorted_data)
        
        # Set axis date format
        axis = DateAxisItem(orientation='bottom')
        self.price_plot.setAxisItems({'bottom': axis})
    
    def set_signals(self, signals: List[BBSignal]):
        """Set buy/sell signal markers."""
        if not signals or not self._data:
            return
        
        self._signals = signals
        
        # Create date lookup
        date_to_idx = {bb.date: i for i, bb in enumerate(self._data)}
        
        buy_x, buy_y = [], []
        sell_x, sell_y = [], []
        
        for signal in signals:
            if signal.signal_date in date_to_idx:
                idx = date_to_idx[signal.signal_date]
                bb = self._data[idx]
                timestamp = datetime.combine(bb.date, datetime.min.time()).timestamp()
                
                if signal.signal_type == SignalType.BUY:
                    buy_x.append(timestamp)
                    buy_y.append(bb.lower * 0.99)  # Below price
                else:
                    sell_x.append(timestamp)
                    sell_y.append(bb.upper * 1.01)  # Above price
        
        self.buy_markers.setData(buy_x, buy_y)
        self.sell_markers.setData(sell_x, sell_y)
    
    def _highlight_squeeze_regions(self, dates: List[float],
                                   data: List[BollingerBands]):
        """Highlight squeeze regions on bandwidth chart."""
        # Clear existing
        for region in self.squeeze_regions:
            self.bw_plot.removeItem(region)
        self.squeeze_regions.clear()
        
        # Find squeeze periods (bandwidth percentile < 10)
        in_squeeze = False
        squeeze_start = None
        
        for i, bb in enumerate(data):
            is_squeeze = getattr(bb, 'bandwidth_percentile', 50) < 10
            
            if is_squeeze and not in_squeeze:
                squeeze_start = dates[i]
                in_squeeze = True
            elif not is_squeeze and in_squeeze:
                # End of squeeze
                region = pg.LinearRegionItem(
                    [squeeze_start, dates[i]],
                    brush=pg.mkBrush(255, 235, 59, 30),  # Yellow tint
                    movable=False
                )
                self.bw_plot.addItem(region)
                self.squeeze_regions.append(region)
                in_squeeze = False
        
        # Handle if still in squeeze at end
        if in_squeeze and squeeze_start:
            region = pg.LinearRegionItem(
                [squeeze_start, dates[-1]],
                brush=pg.mkBrush(255, 235, 59, 30),
                movable=False
            )
            self.bw_plot.addItem(region)
            self.squeeze_regions.append(region)
    
    def _on_mouse_moved(self, pos):
        """Handle mouse movement for crosshair."""
        if not self._data:
            return
        
        mouse_point = self.price_plot.vb.mapSceneToView(pos)
        
        self.vLine.setPos(mouse_point.x())
        self.hLine.setPos(mouse_point.y())
        
        # Find nearest data point
        timestamp = mouse_point.x()
        nearest_bb = None
        min_diff = float('inf')
        
        for bb in self._data:
            dt = datetime.combine(bb.date, datetime.min.time()).timestamp()
            diff = abs(dt - timestamp)
            if diff < min_diff:
                min_diff = diff
                nearest_bb = bb
        
        if nearest_bb:
            self._update_info_bar(nearest_bb)
    
    def _update_info_bar(self, bb: BollingerBands):
        """Update info bar with data point info."""
        self.date_label.setText(f"Date: {bb.date}")
        self.price_label.setText(f"Close: {bb.close:.2f}")
        self.pb_label.setText(f"%b: {bb.percent_b:.3f}")
        self.bw_label.setText(f"BW: {bb.bandwidth:.4f}")
        self.band_label.setText(
            f"U:{bb.upper:.2f} M:{bb.middle:.2f} L:{bb.lower:.2f}"
        )
    
    def clear(self):
        """Clear all chart data."""
        self.price_line.clear()
        self.upper_band.clear()
        self.middle_band.clear()
        self.lower_band.clear()
        self.pb_line.clear()
        self.bw_line.clear()
        self.buy_markers.clear()
        self.sell_markers.clear()
        
        for region in self.squeeze_regions:
            self.bw_plot.removeItem(region)
        self.squeeze_regions.clear()
        
        if self.show_volume:
            self.volume_bars.setOpts(x=[], height=[])
        
        self._data = None
        self._signals = []
