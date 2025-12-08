"""
Intraday Breadth Visualizer
===========================
Real-time PyQtGraph visualization for intraday SMA breadth analysis.

Features:
- Nifty 50 index 5-minute candlestick chart with SMA overlays (10, 20, 50)
- Multiple indicator panels showing % stocks above SMAs
- Synchronized crosshairs across all panels
- AUTO-REFRESH every 5 minutes during market hours
- Shows last 2 trading days of data
- 60% screen for price chart, 40% for indicators
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QGroupBox, QGridLayout,
    QSplitter, QFrame, QProgressBar, QStatusBar, QDateEdit, QSpinBox,
    QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QColor

import pyqtgraph as pg
from pyqtgraph import DateAxisItem

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intraday_breadth.data_fetcher import IntradayDataFetcher
from intraday_breadth.sma_calculator import IntradaySMACalculator


# Configure PyQtGraph
pg.setConfigOptions(antialias=True, background='w', foreground='k')


class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick chart item for PyQtGraph.
    
    Uses sequential indices for X-axis to avoid gaps between trading sessions.
    """
    
    def __init__(self, data):
        """
        Args:
            data: DataFrame with datetime index, open, high, low, close columns
        """
        super().__init__()
        self.data = data
        self.picture = None
        self._bounds = None
        self.generatePicture()
    
    def generatePicture(self):
        """Generate the candlestick picture using sequential indices."""
        from PyQt5.QtGui import QPainter, QPicture
        from PyQt5.QtCore import QRectF, QPointF
        
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        if self.data is None or self.data.empty:
            p.end()
            self._bounds = QRectF()
            return
        
        # Use sequential indices instead of timestamps
        n = len(self.data)
        y_min = self.data['low'].min()
        y_max = self.data['high'].max()
        
        # Bar width (0.8 of 1 unit)
        w = 0.4
        
        # Store bounds
        self._bounds = QRectF(-w, y_min, n + 2*w, y_max - y_min)
        
        for i, (ts, row) in enumerate(self.data.iterrows()):
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            
            if pd.isna(o) or pd.isna(c):
                continue
            
            # Color based on close vs open
            if c >= o:
                p.setPen(pg.mkPen('g', width=1))
                p.setBrush(pg.mkBrush('g'))
            else:
                p.setPen(pg.mkPen('r', width=1))
                p.setBrush(pg.mkBrush('r'))
            
            # Draw wick (high-low line) at index i
            p.drawLine(QPointF(i, l), QPointF(i, h))
            
            # Draw body
            p.drawRect(QRectF(i - w, o, w * 2, c - o))
        
        p.end()
    
    def paint(self, p, *args):
        if self.picture:
            self.picture.play(p)
    
    def boundingRect(self):
        if self._bounds:
            return self._bounds
        return pg.QtCore.QRectF()
    
    def setData(self, data):
        """Update the data and redraw."""
        self.data = data
        self.generatePicture()
        self.informViewBoundsChanged()
        self.update()


class TimeAxisItem(pg.AxisItem):
    """Custom axis for displaying datetime values using index mapping.
    
    This avoids gaps in the chart by using sequential indices instead of timestamps.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLabel('Time')
        self.datetime_map = {}  # Maps index -> datetime
    
    def set_datetime_map(self, datetimes):
        """Set the mapping from index to datetime.
        
        Args:
            datetimes: List or array of datetime objects
        """
        self.datetime_map = {i: dt for i, dt in enumerate(datetimes)}
    
    def tickStrings(self, values, scale, spacing):
        """Convert index values to datetime strings."""
        strings = []
        for v in values:
            idx = int(round(v))
            if idx in self.datetime_map:
                dt = self.datetime_map[idx]
                # Show date change or just time
                if spacing > 50:  # Wider spacing - show date
                    strings.append(dt.strftime('%d/%m %H:%M'))
                else:
                    strings.append(dt.strftime('%H:%M'))
            else:
                strings.append('')
        return strings


class DataLoaderThread(QThread):
    """Background thread for loading data - supports full and incremental modes."""
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(object, object, object)  # index_df, stock_data, breadth_df
    error = pyqtSignal(str)
    
    def __init__(self, fetcher, calculator, incremental: bool = False):
        super().__init__()
        self.fetcher = fetcher
        self.calculator = calculator
        self.incremental = incremental
    
    def run(self):
        try:
            if self.incremental:
                self._run_incremental()
            else:
                self._run_full()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def _run_full(self):
        """Full data fetch - used on initial load."""
        # Fetch index data
        self.progress.emit("Fetching Nifty index (5 days)...", 10)
        index_df = self.fetcher.fetch_nifty_index(force_refresh=True)
        
        if index_df.empty:
            self.error.emit("Failed to fetch Nifty index data")
            return
        
        # Fetch stock data
        self.progress.emit("Fetching Nifty 50 stocks (5 days)...", 20)
        
        def stock_progress(current, total, symbol):
            pct = 20 + int((current / total) * 60)
            self.progress.emit(f"Fetching {symbol}...", pct)
        
        stock_data = self.fetcher.fetch_all_stocks(
            force_refresh=True,
            progress_callback=stock_progress
        )
        
        if not stock_data:
            self.error.emit("Failed to fetch stock data")
            return
        
        # Mark initial load complete
        self.fetcher.mark_initial_load_done()
        
        # Calculate SMAs for index
        self.progress.emit("Calculating index SMAs...", 85)
        index_with_smas = self.calculator.calculate_index_smas(index_df)
        
        # Calculate breadth
        self.progress.emit("Calculating breadth indicators...", 90)
        breadth_df = self.calculator.calculate_breadth_fast(stock_data)
        
        self.progress.emit("Initial load complete!", 100)
        self.finished.emit(index_with_smas, stock_data, breadth_df)
    
    def _run_incremental(self):
        """Incremental update - fetch only latest candle and merge."""
        self.progress.emit("Fetching latest data...", 20)
        
        # Fetch only today's data
        latest_index, latest_stocks = self.fetcher.fetch_latest_only()
        
        if latest_index.empty and not latest_stocks:
            self.progress.emit("No new data available", 100)
            # Return existing cached data
            cached_index, cached_stocks = self.fetcher.get_cached_data()
            if cached_index is not None:
                index_with_smas = self.calculator.calculate_index_smas(cached_index)
                breadth_df = self.calculator.calculate_breadth_fast(cached_stocks)
                self.finished.emit(index_with_smas, cached_stocks, breadth_df)
            return
        
        # Merge with existing cache
        self.progress.emit("Merging with historical data...", 50)
        self.fetcher.update_cache_incremental(latest_index, latest_stocks)
        
        # Get merged data
        merged_index, merged_stocks = self.fetcher.get_cached_data()
        
        # Recalculate SMAs and breadth
        self.progress.emit("Recalculating indicators...", 70)
        index_with_smas, breadth_df = self.calculator.update_incremental(
            merged_index, merged_stocks
        )
        
        self.progress.emit("Update complete!", 100)
        self.finished.emit(index_with_smas, merged_stocks, breadth_df)


class IntradayBreadthVisualizer(QMainWindow):
    """Main visualization window with real-time updates."""
    
    # Colors for indicators
    SMA_COLORS = {
        10: '#FF6B6B',   # Red
        20: '#4ECDC4',   # Teal
        50: '#45B7D1',   # Blue
        200: '#96CEB4',  # Green
    }
    
    # Default refresh interval (5 minutes)
    DEFAULT_REFRESH_INTERVAL = 5
    
    # Number of trading days to display
    DISPLAY_DAYS = 2
    
    def __init__(self):
        super().__init__()
        
        self.fetcher = IntradayDataFetcher(use_cache=True, max_workers=10)
        self.calculator = IntradaySMACalculator()
        
        # Data
        self.index_df = None
        self.stock_data = None
        self.breadth_df = None
        
        # UI components
        self.plots = {}
        self.crosshairs = {}
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._auto_refresh)
        
        self._init_ui()
        
        # Auto-load data on startup (after UI is ready)
        QTimer.singleShot(100, self._auto_start)
        
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Intraday SMA Breadth Analyzer - Nifty 50 (5-min) [REAL-TIME]")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        main_layout.setSpacing(2)  # Reduce spacing
        
        # Top control bar (fixed height)
        self._create_control_bar(main_layout)
        
        # Chart area (expandable)
        self._create_chart_area(main_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Starting... Loading data automatically.")
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Market status label
        self.market_status_label = QLabel()
        self.market_status_label.setStyleSheet("font-weight: bold; padding: 0 10px;")
        self.status_bar.addPermanentWidget(self.market_status_label)
        self._update_market_status()
    
    def _create_control_bar(self, parent_layout):
        """Create the top control bar."""
        control_frame = QFrame()
        control_frame.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 5px; }")
        control_layout = QHBoxLayout(control_frame)
        
        # Load button
        self.load_btn = QPushButton("📊 Load Data")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.load_btn.clicked.connect(self._load_data)
        control_layout.addWidget(self.load_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._load_data)
        self.refresh_btn.setEnabled(False)
        control_layout.addWidget(self.refresh_btn)
        
        control_layout.addWidget(QLabel("│"))
        
        # Date selector
        control_layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        control_layout.addWidget(self.date_edit)
        
        control_layout.addWidget(QLabel("│"))
        
        # Indicator checkboxes
        control_layout.addWidget(QLabel("Show:"))
        
        self.indicator_checks = {}
        for period in [10, 20, 50, 200]:
            cb = QCheckBox(f"SMA{period}")
            cb.setChecked(period in [10, 20, 50])  # Default: show 10, 20, 50
            cb.setStyleSheet(f"QCheckBox {{ color: {self.SMA_COLORS[period]}; font-weight: bold; }}")
            cb.stateChanged.connect(self._update_indicators)
            self.indicator_checks[period] = cb
            control_layout.addWidget(cb)
        
        control_layout.addWidget(QLabel("│"))
        
        # Auto-refresh - enabled by default
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setChecked(True)  # Enabled by default
        self.auto_refresh_cb.stateChanged.connect(self._toggle_auto_refresh)
        control_layout.addWidget(self.auto_refresh_cb)
        
        control_layout.addWidget(QLabel("every"))
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1, 30)
        self.refresh_interval.setValue(self.DEFAULT_REFRESH_INTERVAL)  # 5 min default
        self.refresh_interval.setSuffix(" min")
        self.refresh_interval.valueChanged.connect(self._on_interval_changed)
        control_layout.addWidget(self.refresh_interval)
        
        # Countdown label
        self.countdown_label = QLabel("")
        self.countdown_label.setStyleSheet("color: blue; font-weight: bold;")
        control_layout.addWidget(self.countdown_label)
        
        # Countdown timer (updates every second)
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.countdown_seconds = 0
        
        control_layout.addStretch()
        
        # Current values display
        self.current_values_label = QLabel("")
        self.current_values_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        control_layout.addWidget(self.current_values_label)
        
        parent_layout.addWidget(control_frame)
    
    def _create_chart_area(self, parent_layout):
        """Create the main chart area with multiple plots.
        
        Layout: 50% price chart, 50% for indicator panels.
        Uses QSplitter for resizable panels that fill all space.
        """
        # Main splitter to divide price chart and indicators
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        
        # Price chart widget
        self.price_widget = pg.GraphicsLayoutWidget()
        self.price_widget.setBackground('w')
        
        self.price_plot = self.price_widget.addPlot(
            row=0, col=0,
            title="Nifty 50 Index (5-min) - Market Hours Only",
            axisItems={'bottom': TimeAxisItem(orientation='bottom')}
        )
        self.price_plot.setLabel('left', 'Price')
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Store plot items
        self.candlestick_item = None
        self.sma_lines = {}
        
        # Add crosshair to price chart
        self._add_crosshair(self.price_plot, 'price')
        
        main_splitter.addWidget(self.price_widget)
        
        # Indicator splitter (for the 3-4 indicator panels)
        indicator_splitter = QSplitter(Qt.Vertical)
        indicator_splitter.setChildrenCollapsible(False)
        
        # Breadth indicator plots
        self.indicator_plots = {}
        self.indicator_widgets = {}
        
        for i, period in enumerate([10, 20, 50, 200]):
            widget = pg.GraphicsLayoutWidget()
            widget.setBackground('w')
            
            plot = widget.addPlot(
                row=0, col=0,
                title=f"% Above SMA {period}",
                axisItems={'bottom': TimeAxisItem(orientation='bottom')}
            )
            plot.setLabel('left', '%')
            plot.setYRange(0, 100)
            plot.showGrid(x=True, y=True, alpha=0.3)
            
            # Link X axis to price chart
            plot.setXLink(self.price_plot)
            
            # Add reference lines at 20%, 50%, 80%
            for level in [20, 50, 80]:
                line = pg.InfiniteLine(
                    pos=level,
                    angle=0,
                    pen=pg.mkPen(color='gray', style=Qt.DashLine, width=1)
                )
                plot.addItem(line)
            
            # Add crosshair
            self._add_crosshair(plot, f'sma_{period}')
            
            self.indicator_plots[period] = {
                'plot': plot,
                'curve': None,
            }
            self.indicator_widgets[period] = widget
            indicator_splitter.addWidget(widget)
        
        main_splitter.addWidget(indicator_splitter)
        
        # Set initial sizes: 50% price, 50% indicators
        parent_layout.addWidget(main_splitter, stretch=1)
        
        # Set splitter sizes after widget is added
        QTimer.singleShot(100, lambda: self._set_splitter_sizes(main_splitter, indicator_splitter))
        
        # Store splitters for later adjustment
        self.main_splitter = main_splitter
        self.indicator_splitter = indicator_splitter
        
        # Initially hide plots based on checkbox state
        self._update_indicators()
    
    def _set_splitter_sizes(self, main_splitter, indicator_splitter):
        """Set splitter sizes for 50/50 layout."""
        total_height = main_splitter.height()
        if total_height > 100:
            # 50% for price chart, 50% for indicators
            main_splitter.setSizes([total_height // 2, total_height // 2])
            
            # Equal sizes for each visible indicator
            ind_height = indicator_splitter.height()
            visible_count = sum(1 for p in [10, 20, 50, 200] 
                              if self.indicator_checks.get(p, QCheckBox()).isChecked())
            if visible_count > 0:
                size_each = ind_height // visible_count
                indicator_splitter.setSizes([size_each] * 4)
    
    def _add_crosshair(self, plot, name):
        """Add synchronized crosshair to a plot."""
        vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1))
        hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1))
        
        plot.addItem(vLine, ignoreBounds=True)
        plot.addItem(hLine, ignoreBounds=True)
        
        self.crosshairs[name] = {'vLine': vLine, 'hLine': hLine, 'plot': plot}
        
        # Connect mouse move event
        plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
    
    def _on_mouse_moved(self, pos):
        """Handle mouse movement for synchronized crosshairs."""
        # Find which plot the mouse is in
        for name, ch in self.crosshairs.items():
            plot = ch['plot']
            if plot.sceneBoundingRect().contains(pos):
                mouse_point = plot.vb.mapSceneToView(pos)
                x = mouse_point.x()
                y = mouse_point.y()
                
                # Update all vertical lines (synchronized)
                for ch2 in self.crosshairs.values():
                    ch2['vLine'].setPos(x)
                
                # Update only this plot's horizontal line
                ch['hLine'].setPos(y)
                
                # Update status with current values
                self._update_crosshair_values(x, y, name)
                break
    
    def _update_crosshair_values(self, x, y, source):
        """Update displayed values based on crosshair position."""
        if self.breadth_df is None or self.breadth_df.empty:
            return
        
        try:
            # Convert timestamp to datetime
            dt = datetime.fromtimestamp(x)
            
            # Find closest data point
            closest_idx = None
            min_diff = float('inf')
            
            for idx in self.breadth_df.index:
                diff = abs((idx - dt).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = idx
            
            if closest_idx is not None and min_diff < 600:  # Within 10 minutes
                row = self.breadth_df.loc[closest_idx]
                
                values = []
                for period in [10, 20, 50, 200]:
                    col = f'pct_above_sma_{period}'
                    if col in row:
                        values.append(f"SMA{period}: {row[col]:.1f}%")
                
                time_str = closest_idx.strftime('%H:%M')
                self.status_bar.showMessage(f"Time: {time_str} | " + " | ".join(values))
                
        except Exception as e:
            pass
    
    def _load_data(self, incremental: bool = False):
        """Load data in background thread.
        
        Args:
            incremental: If True, only fetch latest data and merge with cache.
                        If False, fetch full 5-day history.
        """
        self.load_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.loader_thread = DataLoaderThread(self.fetcher, self.calculator, incremental=incremental)
        self.loader_thread.progress.connect(self._on_load_progress)
        self.loader_thread.finished.connect(self._on_load_finished)
        self.loader_thread.error.connect(self._on_load_error)
        self.loader_thread.start()
    
    def _on_load_progress(self, message, percentage):
        """Update progress bar."""
        self.progress_bar.setValue(percentage)
        self.status_bar.showMessage(message)
    
    def _on_load_finished(self, index_df, stock_data, breadth_df):
        """Handle successful data load."""
        self.index_df = index_df
        self.stock_data = stock_data
        self.breadth_df = breadth_df
        
        self.load_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Update market status
        self._update_market_status()
        
        # Update charts
        self._update_charts()
        
        # Update current values
        self._update_current_values()
        
        # Show trading days info with data freshness indicator
        trading_dates = self._get_last_trading_days(self.DISPLAY_DAYS)
        dates_str = ", ".join([d.strftime('%a %d-%b') for d in trading_dates])
        
        # Check if we have today's data
        today = date.today()
        has_today = today in trading_dates if trading_dates else False
        
        # Get latest data timestamp
        latest_data_time = ""
        if self.index_df is not None and not self.index_df.empty:
            latest_ts = self.index_df.index.max()
            latest_data_time = latest_ts.strftime('%d-%b %H:%M')
        
        freshness = "🟢 LIVE" if has_today else "🟡 Historical"
        
        # Determine if this was incremental or full load
        mode = "incremental" if self.fetcher.is_initial_load_done() else "initial"
        
        self.status_bar.showMessage(
            f"{freshness} | {len(self.stock_data)} stocks | Showing: {dates_str} | "
            f"Latest: {latest_data_time} | {mode.title()} update @ {datetime.now().strftime('%H:%M:%S')}"
        )
    
    def _on_load_error(self, error_msg):
        """Handle load error."""
        self.load_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Don't show popup for rate limit errors - just show in status bar
        error_lower = error_msg.lower()
        if 'rate' in error_lower or 'too many' in error_lower:
            self.status_bar.showMessage(f"⚠️ Rate limited - will retry on next refresh | {datetime.now().strftime('%H:%M:%S')}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to load data: {error_msg}")
            self.status_bar.showMessage(f"Error: {error_msg}")
    
    def _update_charts(self):
        """Update all charts with loaded data.
        
        Shows last 2 trading days of data, filtering to market hours only (9:15 AM - 3:30 PM).
        """
        if self.index_df is None or self.index_df.empty:
            return
        
        # Get the last N trading days
        trading_dates = self._get_last_trading_days(self.DISPLAY_DAYS)
        
        if not trading_dates:
            self.status_bar.showMessage("No trading data available")
            return
        
        # Convert trading_dates to set for faster lookup
        trading_dates_set = set(trading_dates)
        
        # Filter index data to only include these trading days
        # Use list comprehension since index.date returns numpy array
        index_mask = [d in trading_dates_set for d in self.index_df.index.date]
        index_filtered = self.index_df[index_mask]
        
        # Filter to market hours only (9:15 AM - 3:30 PM) to avoid overnight gaps
        index_filtered = index_filtered.between_time('09:15', '15:30')
        
        if index_filtered.empty:
            self.status_bar.showMessage("No data for selected trading days")
            return
        
        # Update the date selector to show the most recent date
        latest_date = max(trading_dates)
        self.date_edit.blockSignals(True)  # Prevent triggering date change event
        self.date_edit.setDate(QDate(latest_date.year, latest_date.month, latest_date.day))
        self.date_edit.blockSignals(False)
        
        # Update chart title with date range
        today = date.today()
        has_today = today in trading_dates
        title_prefix = "🟢 LIVE" if has_today else "🟡 HISTORICAL"
        dates_str = " & ".join([d.strftime('%a %d-%b') for d in trading_dates])
        self.price_plot.setTitle(f"{title_prefix}: Nifty 50 Index (5-min) - {dates_str}")
        
        # Update price chart
        self._update_price_chart(index_filtered)
        
        # Filter breadth data
        if self.breadth_df is not None:
            # Use list comprehension since index.date returns numpy array
            breadth_mask = [d in trading_dates_set for d in self.breadth_df.index.date]
            breadth_filtered = self.breadth_df[breadth_mask]
            
            # Filter to market hours only
            breadth_filtered = breadth_filtered.between_time('09:15', '15:30')
            
            if not breadth_filtered.empty:
                # Update indicator charts
                self._update_indicator_charts(breadth_filtered)
    
    def _update_price_chart(self, df):
        """Update the candlestick price chart using sequential indices."""
        if df.empty:
            return
        
        # Clear existing items
        self.price_plot.clear()
        
        # Re-add crosshair
        ch = self.crosshairs.get('price')
        if ch:
            self.price_plot.addItem(ch['vLine'], ignoreBounds=True)
            self.price_plot.addItem(ch['hLine'], ignoreBounds=True)
        
        # Store the datetime list for this data (used by all plots)
        self._current_datetimes = list(df.index)
        
        # Update the time axis mapping
        axis = self.price_plot.getAxis('bottom')
        if hasattr(axis, 'set_datetime_map'):
            axis.set_datetime_map(self._current_datetimes)
        
        # Create candlestick item (uses sequential indices internally)
        df_plot = df.copy()
        self.candlestick_item = CandlestickItem(df_plot)
        self.price_plot.addItem(self.candlestick_item)
        
        # Add SMA lines using sequential indices
        for period in [10, 20, 50]:
            col = f'sma_{period}'
            if col in df_plot.columns:
                sma_data = df_plot[col].dropna()
                if not sma_data.empty:
                    # Map SMA indices to sequential x values
                    x = [self._current_datetimes.index(ts) for ts in sma_data.index if ts in self._current_datetimes]
                    y = [sma_data.loc[self._current_datetimes[i]] for i in x]
                    
                    if x and y:
                        self.price_plot.plot(
                            x, y,
                            pen=pg.mkPen(self.SMA_COLORS[period], width=2),
                            name=f'SMA{period}'
                        )
        
        # Set Y range explicitly to ensure correct scaling
        y_min = df_plot['low'].min()
        y_max = df_plot['high'].max()
        y_padding = (y_max - y_min) * 0.05
        self.price_plot.setYRange(y_min - y_padding, y_max + y_padding)
        
        # Set X range using sequential indices
        n = len(df_plot)
        self.price_plot.setXRange(-1, n + 1)
    
    def _update_indicator_charts(self, breadth_df):
        """Update the indicator charts using sequential indices."""
        if breadth_df.empty:
            return
        
        # Build index mapping from breadth_df to price chart datetimes
        if not hasattr(self, '_current_datetimes') or not self._current_datetimes:
            return
        
        # Map breadth timestamps to sequential indices
        breadth_to_idx = {}
        for i, dt in enumerate(self._current_datetimes):
            breadth_to_idx[dt] = i
        
        # Get sequential x values for breadth data
        x_indices = []
        for ts in breadth_df.index:
            if ts in breadth_to_idx:
                x_indices.append(breadth_to_idx[ts])
            else:
                # Find closest match
                for dt in self._current_datetimes:
                    if abs((dt - ts).total_seconds()) < 60:
                        x_indices.append(breadth_to_idx[dt])
                        break
                else:
                    x_indices.append(len(x_indices))  # Fallback
        
        for period, items in self.indicator_plots.items():
            plot = items['plot']
            
            # Update time axis mapping
            axis = plot.getAxis('bottom')
            if hasattr(axis, 'set_datetime_map'):
                axis.set_datetime_map(self._current_datetimes)
            
            # Clear and re-add items
            plot.clear()
            
            # Add reference lines
            for level in [20, 50, 80]:
                line = pg.InfiniteLine(
                    pos=level,
                    angle=0,
                    pen=pg.mkPen(color='gray', style=Qt.DashLine, width=1)
                )
                plot.addItem(line)
            
            # Re-add crosshair
            ch = self.crosshairs.get(f'sma_{period}')
            if ch:
                plot.addItem(ch['vLine'], ignoreBounds=True)
                plot.addItem(ch['hLine'], ignoreBounds=True)
            
            # Add data curve using sequential indices
            col = f'pct_above_sma_{period}'
            if col in breadth_df.columns:
                y = breadth_df[col].values
                x = list(range(len(y)))  # Sequential indices
                
                # Fill under curve
                fill = pg.FillBetweenItem(
                    pg.PlotDataItem(x, y),
                    pg.PlotDataItem(x, np.zeros_like(y)),
                    brush=pg.mkBrush(self.SMA_COLORS[period] + '40')  # 40 = alpha
                )
                plot.addItem(fill)
                
                # Line on top
                plot.plot(
                    x, y,
                    pen=pg.mkPen(self.SMA_COLORS[period], width=2)
                )
            
            # Set Y range
            plot.setYRange(0, 100)
            
            # Set X range to match price chart
            n = len(self._current_datetimes)
            plot.setXRange(-1, n + 1)
    
    def _update_indicators(self):
        """Show/hide indicator panels based on checkboxes."""
        for period, cb in self.indicator_checks.items():
            if period in self.indicator_widgets:
                widget = self.indicator_widgets[period]
                widget.setVisible(cb.isChecked())
        
        # Readjust splitter sizes after visibility change
        if hasattr(self, 'indicator_splitter'):
            QTimer.singleShot(50, self._readjust_indicator_sizes)
    
    def _readjust_indicator_sizes(self):
        """Readjust indicator splitter sizes based on visible panels."""
        if not hasattr(self, 'indicator_splitter'):
            return
        
        visible_widgets = [p for p in [10, 20, 50, 200] 
                         if self.indicator_checks.get(p, QCheckBox()).isChecked()]
        
        if visible_widgets:
            total_height = self.indicator_splitter.height()
            size_each = total_height // len(visible_widgets)
            sizes = []
            for period in [10, 20, 50, 200]:
                if period in visible_widgets:
                    sizes.append(size_each)
                else:
                    sizes.append(0)
            self.indicator_splitter.setSizes(sizes)
    
    def _update_current_values(self):
        """Update the current values display."""
        current = self.calculator.get_current_breadth()
        if not current:
            return
        
        parts = []
        for period in [10, 20, 50, 200]:
            key = f'pct_above_sma_{period}'
            if key in current:
                color = self.SMA_COLORS[period]
                parts.append(f'<span style="color:{color}">SMA{period}: {current[key]:.1f}%</span>')
        
        self.current_values_label.setText(" | ".join(parts))
    
    def _on_date_changed(self, qdate):
        """Handle date selection change."""
        if self.index_df is not None:
            self._update_charts()
    
    def _get_last_trading_days(self, num_days: int) -> list:
        """Get the last N trading days from available data.
        
        Handles weekends by skipping to Friday if current day is Saturday/Sunday.
        
        Args:
            num_days: Number of trading days to return
            
        Returns:
            List of date objects for the last N trading days
        """
        if self.index_df is None or self.index_df.empty:
            return []
        
        # Get unique dates from the data
        available_dates = sorted(set(self.index_df.index.date))
        
        if not available_dates:
            return []
        
        # Return the last N dates (these are already trading days since they have data)
        return available_dates[-num_days:] if len(available_dates) >= num_days else available_dates
    
    def _auto_start(self):
        """Auto-load data and start refresh timer on startup."""
        # Load data automatically first
        self._load_data()
        
        # Start auto-refresh timer if checkbox is checked
        if self.auto_refresh_cb.isChecked():
            self._start_refresh_cycle()
    
    def _start_refresh_cycle(self):
        """Start the refresh cycle with countdown."""
        interval_min = self.refresh_interval.value()
        interval_ms = interval_min * 60 * 1000
        
        # Start the main refresh timer
        self.refresh_timer.start(interval_ms)
        
        # Start countdown
        self.countdown_seconds = interval_min * 60
        self.countdown_timer.start(1000)  # Update every second
        
        print(f"Refresh cycle started: {interval_min} min ({interval_ms} ms)")
    
    def _update_countdown(self):
        """Update the countdown display every second."""
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
            mins = self.countdown_seconds // 60
            secs = self.countdown_seconds % 60
            self.countdown_label.setText(f"Next: {mins:02d}:{secs:02d}")
        else:
            self.countdown_label.setText("Refreshing...")
    
    def _update_market_status(self):
        """Update the market status indicator."""
        now = datetime.now()
        
        if now.weekday() >= 5:  # Weekend
            self.market_status_label.setText("🔴 Market Closed (Weekend)")
            self.market_status_label.setStyleSheet("color: gray; font-weight: bold; padding: 0 10px;")
        elif now.hour < 9 or (now.hour == 9 and now.minute < 15):
            self.market_status_label.setText("🟡 Pre-Market")
            self.market_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 0 10px;")
        elif now.hour > 15 or (now.hour == 15 and now.minute >= 30):
            self.market_status_label.setText("🔴 Market Closed")
            self.market_status_label.setStyleSheet("color: gray; font-weight: bold; padding: 0 10px;")
        else:
            self.market_status_label.setText("🟢 Market Open")
            self.market_status_label.setStyleSheet("color: green; font-weight: bold; padding: 0 10px;")
    
    def _on_interval_changed(self, value):
        """Handle refresh interval change."""
        if self.auto_refresh_cb.isChecked():
            self.refresh_timer.stop()
            self.countdown_timer.stop()
            self._start_refresh_cycle()
            self.status_bar.showMessage(f"Refresh interval changed to {value} min")
    
    def _toggle_auto_refresh(self, state):
        """Toggle auto-refresh timer."""
        if state == Qt.Checked:
            self._start_refresh_cycle()
            self.status_bar.showMessage(f"Auto-refresh enabled ({self.refresh_interval.value()} min)")
        else:
            self.refresh_timer.stop()
            self.countdown_timer.stop()
            self.countdown_label.setText("")
            self.status_bar.showMessage("Auto-refresh disabled")
    
    def _auto_refresh(self):
        """Auto-refresh callback - runs every N minutes.
        
        Uses incremental updates (fetches only latest candle) after initial load.
        Full refresh only on first load or when cache is empty.
        """
        self._update_market_status()
        
        now = datetime.now()
        
        # Reset countdown for next cycle
        self.countdown_seconds = self.refresh_interval.value() * 60
        
        # Check if it's a trading day (Monday-Friday)
        if now.weekday() >= 5:
            self.status_bar.showMessage(f"Weekend - auto-refresh paused | {now.strftime('%H:%M:%S')}")
            return
        
        # Use incremental mode if initial load is already done
        use_incremental = self.fetcher.is_initial_load_done()
        mode = "incremental" if use_incremental else "full"
        
        print(f"Auto-refresh ({mode}) triggered at {now.strftime('%H:%M:%S')}")
        self.status_bar.showMessage(f"🔄 Auto-refreshing ({mode})... ({now.strftime('%H:%M:%S')})")
        
        self._load_data(incremental=use_incremental)
    
    def closeEvent(self, event):
        """Clean up on close."""
        self.refresh_timer.stop()
        self.countdown_timer.stop()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application-wide font
    font = QFont('Segoe UI', 10)
    app.setFont(font)
    
    window = IntradayBreadthVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
