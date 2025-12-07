#!/usr/bin/env python3
"""
Coppock Curve Indicator - PyQtGraph Version
============================================
High-performance interactive Coppock Curve indicator using PyQtGraph.

The Coppock Curve is a long-term momentum indicator:
- ROC1: 14 periods (default)
- ROC2: 11 periods (default)
- WMA: 10 periods (default)

Buy Signal: When Coppock turns up from below zero
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# Try to import yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("Warning: yfinance not installed. Run: pip install yfinance")

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSpinBox, QPushButton, QGroupBox, QTextEdit,
    QSplitter, QFrame, QMessageBox, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import pyqtgraph as pg
from pyqtgraph import DateAxisItem

# Configure PyQtGraph
pg.setConfigOptions(antialias=True, background='w', foreground='k')


def calculate_wma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Weighted Moving Average."""
    weights = np.arange(1, period + 1)
    
    def wma(x):
        return np.sum(weights * x) / weights.sum()
    
    return series.rolling(window=period).apply(wma, raw=True)


def calculate_coppock_curve(df: pd.DataFrame, 
                            roc1_period: int = 14, 
                            roc2_period: int = 11, 
                            wma_period: int = 10) -> pd.DataFrame:
    """
    Calculate Coppock Curve.
    
    Formula: Coppock = WMA(ROC1 + ROC2, WMA_period)
    """
    df = df.copy()
    
    # Calculate Rate of Change
    df['ROC1'] = ((df['close'] - df['close'].shift(roc1_period)) / df['close'].shift(roc1_period)) * 100
    df['ROC2'] = ((df['close'] - df['close'].shift(roc2_period)) / df['close'].shift(roc2_period)) * 100
    
    # Sum of ROCs
    df['ROC_Sum'] = df['ROC1'] + df['ROC2']
    
    # Weighted Moving Average of ROC Sum
    df['Coppock'] = calculate_wma(df['ROC_Sum'], wma_period)
    
    # Previous value for signal detection
    df['Coppock_Prev'] = df['Coppock'].shift(1)
    df['Coppock_Prev2'] = df['Coppock'].shift(2)
    
    # Detect signals
    df['Signal'] = 'None'
    
    # Buy: Turn up from below zero
    turn_up_below = (df['Coppock'] > df['Coppock_Prev']) & (df['Coppock'] < 0) & (df['Coppock_Prev'] <= df['Coppock_Prev2'])
    df.loc[turn_up_below, 'Signal'] = 'Buy'
    
    # Bullish cross above zero
    zero_cross_up = (df['Coppock'] > 0) & (df['Coppock_Prev'] <= 0)
    df.loc[zero_cross_up, 'Signal'] = 'Bullish Cross'
    
    # Bearish cross below zero
    zero_cross_down = (df['Coppock'] < 0) & (df['Coppock_Prev'] >= 0)
    df.loc[zero_cross_down, 'Signal'] = 'Bearish Cross'
    
    return df


class DataLoaderThread(QThread):
    """Thread for loading data from Yahoo Finance."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, symbol: str, years: str, timeframe: str, roc1: int, roc2: int, wma: int):
        super().__init__()
        self.symbol = symbol
        self.years = years
        self.timeframe = timeframe
        self.roc1 = roc1
        self.roc2 = roc2
        self.wma = wma
    
    def run(self):
        try:
            if not HAS_YFINANCE:
                self.error.emit("yfinance not installed")
                return
            
            self.progress.emit(f"Downloading {self.symbol} data...")
            
            # Calculate period
            period = "max" if self.years == "All" else f"{self.years}y"
            
            # Download from Yahoo Finance
            ticker = yf.Ticker(self.symbol)
            df = ticker.history(period=period, interval="1d")
            
            if df.empty:
                self.error.emit(f"No data found for {self.symbol}")
                return
            
            # Prepare data
            df.columns = [c.lower() for c in df.columns]
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'date'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            
            df.set_index('date', inplace=True)
            
            self.progress.emit("Resampling data...")
            
            # Resample based on timeframe
            if self.timeframe == 'monthly':
                df_resampled = df.resample('ME').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
            elif self.timeframe == 'weekly':
                df_resampled = df.resample('W-FRI').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
            else:  # daily - no resampling needed
                df_resampled = df[['open', 'high', 'low', 'close', 'volume']].dropna().copy()
            
            df_resampled.reset_index(inplace=True)
            
            # Check minimum data
            min_required = max(self.roc1, self.roc2) + self.wma
            if len(df_resampled) < min_required:
                self.error.emit(f"Need {min_required} bars, only have {len(df_resampled)}. Try longer lookback or smaller parameters.")
                return
            
            self.progress.emit("Calculating Coppock Curve...")
            
            # Calculate Coppock
            result = calculate_coppock_curve(df_resampled, self.roc1, self.roc2, self.wma)
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class CoppockCurveWindow(QMainWindow):
    """Main window for Coppock Curve indicator."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📈 Coppock Curve - PyQtGraph")
        self.setGeometry(100, 100, 1400, 900)
        
        self.data = None
        self.loader_thread = None
        
        self._setup_ui()
        
        # Auto-load on start
        self._load_data()
    
    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Control panel
        control_group = QGroupBox("Settings")
        control_layout = QHBoxLayout(control_group)
        
        # Index selection
        control_layout.addWidget(QLabel("Index:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["^NSEI", "^NSEBANK", "^BSESN", "^GSPC", "^DJI", "^IXIC"])
        self.symbol_combo.setCurrentText("^NSEI")
        control_layout.addWidget(self.symbol_combo)
        
        control_layout.addSpacing(20)
        
        # Timeframe
        control_layout.addWidget(QLabel("Timeframe:"))
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["Monthly", "Weekly", "Daily"])
        self.timeframe_combo.currentTextChanged.connect(self._on_timeframe_changed)
        control_layout.addWidget(self.timeframe_combo)
        
        control_layout.addSpacing(20)
        
        # Parameters
        control_layout.addWidget(QLabel("ROC1:"))
        self.roc1_spin = QSpinBox()
        self.roc1_spin.setRange(5, 300)
        self.roc1_spin.setValue(14)
        control_layout.addWidget(self.roc1_spin)
        
        control_layout.addWidget(QLabel("ROC2:"))
        self.roc2_spin = QSpinBox()
        self.roc2_spin.setRange(5, 250)
        self.roc2_spin.setValue(11)
        control_layout.addWidget(self.roc2_spin)
        
        control_layout.addWidget(QLabel("WMA:"))
        self.wma_spin = QSpinBox()
        self.wma_spin.setRange(5, 220)
        self.wma_spin.setValue(10)
        control_layout.addWidget(self.wma_spin)
        
        # Preset selector
        control_layout.addSpacing(10)
        control_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Classic (14,11,10)", "Fast (22,14,10)", "Custom"])
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        control_layout.addWidget(self.preset_combo)
        
        control_layout.addSpacing(20)
        
        # Years
        control_layout.addWidget(QLabel("Years:"))
        self.years_combo = QComboBox()
        self.years_combo.addItems(["1", "2", "3", "5", "10", "15", "20", "All"])
        self.years_combo.setCurrentText("10")
        control_layout.addWidget(self.years_combo)
        
        control_layout.addSpacing(20)
        
        # Calculate button
        self.calc_btn = QPushButton("🔄 Calculate")
        self.calc_btn.clicked.connect(self._load_data)
        self.calc_btn.setStyleSheet("QPushButton { padding: 5px 15px; font-weight: bold; }")
        control_layout.addWidget(self.calc_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        # Main content - splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Charts panel
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create PyQtGraph plots
        self.price_plot = pg.PlotWidget(
            title="Price",
            axisItems={'bottom': DateAxisItem()}
        )
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setLabel('left', 'Price')
        
        self.coppock_plot = pg.PlotWidget(
            title="Coppock Curve",
            axisItems={'bottom': DateAxisItem()}
        )
        self.coppock_plot.showGrid(x=True, y=True, alpha=0.3)
        self.coppock_plot.setLabel('left', 'Coppock')
        
        # Link X axes
        self.coppock_plot.setXLink(self.price_plot)
        
        charts_layout.addWidget(self.price_plot, stretch=2)
        charts_layout.addWidget(self.coppock_plot, stretch=1)
        
        splitter.addWidget(charts_widget)
        
        # Info panel
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Current status
        status_group = QGroupBox("Current Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFont(QFont("Consolas", 10))
        self.status_text.setMaximumHeight(200)
        status_layout.addWidget(self.status_text)
        
        info_layout.addWidget(status_group)
        
        # Signals info
        signals_group = QGroupBox("Historical Signals")
        signals_layout = QVBoxLayout(signals_group)
        
        self.signals_text = QTextEdit()
        self.signals_text.setReadOnly(True)
        self.signals_text.setFont(QFont("Consolas", 9))
        signals_layout.addWidget(self.signals_text)
        
        info_layout.addWidget(signals_group)
        
        splitter.addWidget(info_widget)
        splitter.setSizes([1000, 400])
        
        layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Crosshair
        self._setup_crosshair()
    
    def _setup_crosshair(self):
        """Setup crosshair for both plots."""
        self.vLine1 = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.hLine1 = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.price_plot.addItem(self.vLine1, ignoreBounds=True)
        self.price_plot.addItem(self.hLine1, ignoreBounds=True)
        
        self.vLine2 = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.hLine2 = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.coppock_plot.addItem(self.vLine2, ignoreBounds=True)
        self.coppock_plot.addItem(self.hLine2, ignoreBounds=True)
        
        # Mouse tracking - use proxy for better performance
        self.proxy = pg.SignalProxy(self.price_plot.scene().sigMouseMoved, rateLimit=60, slot=self._mouse_moved_proxy)
        self.proxy2 = pg.SignalProxy(self.coppock_plot.scene().sigMouseMoved, rateLimit=60, slot=self._mouse_moved_proxy)
        
        # Info label - positioned in view coordinates, not data coordinates
        self.info_label = pg.TextItem(anchor=(0, 0), color='k', fill=pg.mkBrush(255, 255, 200, 200))
        self.info_label.setZValue(1000)  # Keep on top
        self.price_plot.addItem(self.info_label, ignoreBounds=True)
    
    def _mouse_moved_proxy(self, args):
        """Proxy handler for mouse moved signal."""
        pos = args[0]
        self._mouse_moved(pos)
    
    def _mouse_moved(self, pos):
        """Handle mouse movement for crosshair."""
        if self.data is None or self.data.empty:
            return
        
        # Check which plot contains the mouse
        in_price = self.price_plot.sceneBoundingRect().contains(pos)
        in_coppock = self.coppock_plot.sceneBoundingRect().contains(pos)
        
        if not in_price and not in_coppock:
            return
        
        if in_price:
            mouse_point = self.price_plot.plotItem.vb.mapSceneToView(pos)
        else:
            mouse_point = self.coppock_plot.plotItem.vb.mapSceneToView(pos)
        
        x = mouse_point.x()
        
        # Update vertical crosshairs on both plots
        self.vLine1.setPos(x)
        self.vLine2.setPos(x)
        
        # Update horizontal crosshair only on the active plot
        if in_price:
            self.hLine1.setPos(mouse_point.y())
        else:
            self.hLine2.setPos(mouse_point.y())
        
        # Find nearest data point
        df = self.data.dropna(subset=['Coppock'])
        if df.empty:
            return
            
        timestamps = df['timestamp'].values
        idx = np.searchsorted(timestamps, x)
        idx = max(0, min(idx, len(df) - 1))
        
        row = df.iloc[idx]
        date_str = row['date'].strftime('%Y-%m-%d')
        coppock_val = f"{row['Coppock']:.2f}" if pd.notna(row['Coppock']) else "N/A"
        
        # Update info label text
        self.info_label.setText(f"{date_str}\nClose: {row['close']:,.2f}\nCoppock: {coppock_val}")
        
        # Position label in scene coordinates (top-left of visible area)
        view_range = self.price_plot.plotItem.vb.viewRange()
        label_x = view_range[0][0] + (view_range[0][1] - view_range[0][0]) * 0.01
        label_y = view_range[1][1] - (view_range[1][1] - view_range[1][0]) * 0.01
        self.info_label.setPos(label_x, label_y)
    
    def _on_timeframe_changed(self, timeframe: str):
        """Handle timeframe change - adjust presets."""
        # Update preset options based on timeframe
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        
        if timeframe == "Daily":
            self.preset_combo.addItems([
                "Scaled Monthly (294,231,210)",
                "Medium (65,50,45)", 
                "Fast (22,14,10)",
                "Custom"
            ])
            # Default to Medium for daily
            self.preset_combo.setCurrentText("Medium (65,50,45)")
            self._apply_preset("Medium (65,50,45)")
            # Suggest shorter lookback for daily
            if self.years_combo.currentText() in ["10", "15", "20", "All"]:
                self.years_combo.setCurrentText("3")
        else:
            self.preset_combo.addItems([
                "Classic (14,11,10)",
                "Fast (22,14,10)",
                "Custom"
            ])
            self.preset_combo.setCurrentText("Classic (14,11,10)")
            self._apply_preset("Classic (14,11,10)")
        
        self.preset_combo.blockSignals(False)
    
    def _on_preset_changed(self, preset: str):
        """Handle preset change."""
        self._apply_preset(preset)
    
    def _apply_preset(self, preset: str):
        """Apply parameter preset."""
        # Parse preset string to get values
        presets = {
            "Classic (14,11,10)": (14, 11, 10),
            "Fast (22,14,10)": (22, 14, 10),
            "Scaled Monthly (294,231,210)": (294, 231, 210),
            "Medium (65,50,45)": (65, 50, 45),
        }
        
        if preset in presets:
            roc1, roc2, wma = presets[preset]
            self.roc1_spin.setValue(roc1)
            self.roc2_spin.setValue(roc2)
            self.wma_spin.setValue(wma)
    
    def _load_data(self):
        """Load data from Yahoo Finance."""
        self.calc_btn.setEnabled(False)
        self.statusBar.showMessage("Loading data...")
        
        symbol = self.symbol_combo.currentText()
        years = self.years_combo.currentText()
        timeframe = self.timeframe_combo.currentText().lower()
        roc1 = self.roc1_spin.value()
        roc2 = self.roc2_spin.value()
        wma = self.wma_spin.value()
        
        self.loader_thread = DataLoaderThread(symbol, years, timeframe, roc1, roc2, wma)
        self.loader_thread.finished.connect(self._on_data_loaded)
        self.loader_thread.error.connect(self._on_error)
        self.loader_thread.progress.connect(lambda msg: self.statusBar.showMessage(msg))
        self.loader_thread.start()
    
    def _on_data_loaded(self, df: pd.DataFrame):
        """Handle loaded data."""
        self.calc_btn.setEnabled(True)
        self.data = df
        
        # Convert dates to timestamps for plotting
        self.data['timestamp'] = self.data['date'].astype(np.int64) // 10**9
        
        self._update_charts()
        self._update_info()
        
        timeframe = self.timeframe_combo.currentText().lower()
        self.statusBar.showMessage(f"Loaded {len(df)} {timeframe} bars")
    
    def _on_error(self, error: str):
        """Handle error."""
        self.calc_btn.setEnabled(True)
        self.statusBar.showMessage(f"Error: {error}")
        QMessageBox.warning(self, "Error", error)
    
    def _update_charts(self):
        """Update the charts."""
        if self.data is None:
            return
        
        df = self.data.dropna(subset=['Coppock'])
        
        if df.empty:
            return
        
        timestamps = df['timestamp'].values
        close_vals = df['close'].values
        coppock_vals = df['Coppock'].values
        
        # Clear plots
        self.price_plot.clear()
        self.coppock_plot.clear()
        
        # Re-add crosshair items with ignoreBounds=True
        self.vLine1 = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.hLine1 = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.price_plot.addItem(self.vLine1, ignoreBounds=True)
        self.price_plot.addItem(self.hLine1, ignoreBounds=True)
        
        self.vLine2 = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.hLine2 = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.coppock_plot.addItem(self.vLine2, ignoreBounds=True)
        self.coppock_plot.addItem(self.hLine2, ignoreBounds=True)
        
        # Re-add info label
        self.info_label = pg.TextItem(anchor=(0, 0), color='k', fill=pg.mkBrush(255, 255, 200, 200))
        self.info_label.setZValue(1000)
        self.price_plot.addItem(self.info_label, ignoreBounds=True)
        
        # Plot price line
        self.price_plot.plot(timestamps, close_vals, pen=pg.mkPen('#1976D2', width=2), name='Close')
        
        # Fill under price - use proper min value
        min_price = close_vals.min() * 0.95
        fill_curve1 = pg.PlotDataItem(timestamps, close_vals)
        fill_curve2 = pg.PlotDataItem(timestamps, np.full(len(timestamps), min_price))
        fill = pg.FillBetweenItem(fill_curve1, fill_curve2, brush=pg.mkBrush(100, 150, 255, 80))
        self.price_plot.addItem(fill)
        
        # Mark buy signals on price
        buy_signals = df[df['Signal'].isin(['Buy', 'Bullish Cross'])]
        if not buy_signals.empty:
            self.price_plot.plot(
                buy_signals['timestamp'].values,
                buy_signals['close'].values,
                pen=None,
                symbol='t',
                symbolSize=15,
                symbolBrush='g',
                symbolPen=pg.mkPen('darkgreen', width=1),
                name='Buy Signal'
            )
        
        # Mark bearish crosses
        bearish_signals = df[df['Signal'] == 'Bearish Cross']
        if not bearish_signals.empty:
            self.price_plot.plot(
                bearish_signals['timestamp'].values,
                bearish_signals['close'].values,
                pen=None,
                symbol='t1',  # downward triangle
                symbolSize=15,
                symbolBrush='r',
                symbolPen=pg.mkPen('darkred', width=1),
                name='Bearish Cross'
            )
        
        # Plot Coppock - use efficient bar chart
        # Bar width depends on timeframe
        timeframe = self.timeframe_combo.currentText()
        if timeframe == 'Monthly':
            bar_width = 86400 * 25  # ~25 days
        elif timeframe == 'Weekly':
            bar_width = 86400 * 6   # ~6 days
        else:  # Daily
            bar_width = 86400 * 0.8  # ~0.8 days
        
        # Separate positive and negative values for coloring
        pos_mask = coppock_vals >= 0
        neg_mask = coppock_vals < 0
        
        if pos_mask.any():
            pos_bars = pg.BarGraphItem(
                x=timestamps[pos_mask],
                height=coppock_vals[pos_mask],
                width=bar_width,
                brush=pg.mkBrush(76, 175, 80, 200),  # Green
                pen=pg.mkPen(56, 142, 60, width=1)
            )
            self.coppock_plot.addItem(pos_bars)
        
        if neg_mask.any():
            neg_bars = pg.BarGraphItem(
                x=timestamps[neg_mask],
                height=coppock_vals[neg_mask],
                width=bar_width,
                brush=pg.mkBrush(244, 67, 54, 200),  # Red
                pen=pg.mkPen(211, 47, 47, width=1)
            )
            self.coppock_plot.addItem(neg_bars)
        
        # Zero line
        zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('k', width=2))
        self.coppock_plot.addItem(zero_line)
        
        # Mark signals on Coppock
        if not buy_signals.empty:
            self.coppock_plot.plot(
                buy_signals['timestamp'].values,
                buy_signals['Coppock'].values,
                pen=None,
                symbol='t',
                symbolSize=12,
                symbolBrush='g',
                symbolPen=pg.mkPen('darkgreen', width=1)
            )
        
        # Current value annotation
        latest = df.iloc[-1]
        latest_text = pg.TextItem(
            f"{latest['Coppock']:.2f}",
            anchor=(0, 0.5),
            color='g' if latest['Coppock'] >= 0 else 'r'
        )
        latest_text.setFont(QFont("Arial", 12, QFont.Bold))
        latest_text.setPos(latest['timestamp'], latest['Coppock'])
        self.coppock_plot.addItem(latest_text, ignoreBounds=True)
        
        # Update titles
        symbol_name = {
            "^NSEI": "NIFTY 50",
            "^NSEBANK": "BANK NIFTY",
            "^BSESN": "SENSEX",
            "^GSPC": "S&P 500",
            "^DJI": "DOW JONES",
            "^IXIC": "NASDAQ"
        }.get(self.symbol_combo.currentText(), self.symbol_combo.currentText())
        
        timeframe = self.timeframe_combo.currentText()
        self.price_plot.setTitle(f"{symbol_name} - {timeframe} Close Price")
        
        roc1 = self.roc1_spin.value()
        roc2 = self.roc2_spin.value()
        wma = self.wma_spin.value()
        self.coppock_plot.setTitle(f"Coppock Curve ({roc1}, {roc2}, {wma})")
        
        # Set Y-axis range with some padding and disable auto-range
        price_min, price_max = close_vals.min(), close_vals.max()
        price_padding = (price_max - price_min) * 0.05
        self.price_plot.setYRange(price_min - price_padding, price_max + price_padding, padding=0)
        
        copp_min, copp_max = coppock_vals.min(), coppock_vals.max()
        copp_padding = max(abs(copp_min), abs(copp_max)) * 0.1
        self.coppock_plot.setYRange(copp_min - copp_padding, copp_max + copp_padding, padding=0)
        
        # Enable mouse interaction but prevent auto-range on mouse move
        self.price_plot.setMouseEnabled(x=True, y=True)
        self.coppock_plot.setMouseEnabled(x=True, y=True)
    
    def _update_info(self):
        """Update the info panels."""
        if self.data is None:
            return
        
        df = self.data.dropna(subset=['Coppock'])
        if df.empty:
            return
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Determine trend
        if latest['Coppock'] > prev['Coppock']:
            trend = "↑ Rising"
        else:
            trend = "↓ Falling"
        
        # Determine zone
        if latest['Coppock'] > 0:
            zone = "Bullish (Above Zero)"
        else:
            zone = "Bearish (Below Zero)"
        
        # Signal interpretation
        if latest['Coppock'] < 0 and latest['Coppock'] > prev['Coppock']:
            signal = "⚠️ WATCH - Potential Buy Signal Forming"
        elif latest['Coppock'] > 0 and latest['Coppock'] > prev['Coppock']:
            signal = "✅ Bullish Momentum"
        elif latest['Coppock'] > 0 and latest['Coppock'] < prev['Coppock']:
            signal = "⚡ Momentum Weakening"
        else:
            signal = "⏳ Bearish - Wait for Turn Up"
        
        symbol_name = {
            "^NSEI": "NIFTY 50",
            "^NSEBANK": "BANK NIFTY",
            "^BSESN": "SENSEX",
            "^GSPC": "S&P 500",
            "^DJI": "DOW JONES",
            "^IXIC": "NASDAQ"
        }.get(self.symbol_combo.currentText(), self.symbol_combo.currentText())
        
        status = f"""
{symbol_name} ({self.timeframe_combo.currentText()})
{'=' * 35}

Date:     {latest['date'].strftime('%Y-%m-%d')}
Close:    {latest['close']:,.2f}

Coppock:  {latest['Coppock']:.2f}
Previous: {prev['Coppock']:.2f}
Change:   {latest['Coppock'] - prev['Coppock']:+.2f}

Trend:    {trend}
Zone:     {zone}

Signal:   {signal}

ROC(14):  {latest['ROC1']:.2f}%
ROC(11):  {latest['ROC2']:.2f}%
"""
        self.status_text.setText(status)
        
        # Signals history
        signals_df = df[df['Signal'] != 'None'].tail(20)
        
        signals_text = "Recent Signals:\n" + "=" * 40 + "\n\n"
        signals_text += f"{'Date':<12} {'Close':>10} {'Coppock':>10} {'Signal':<15}\n"
        signals_text += "-" * 50 + "\n"
        
        for _, row in signals_df.iloc[::-1].iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            signals_text += f"{date_str:<12} {row['close']:>10,.0f} {row['Coppock']:>10.2f} {row['Signal']:<15}\n"
        
        self.signals_text.setText(signals_text)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = CoppockCurveWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
