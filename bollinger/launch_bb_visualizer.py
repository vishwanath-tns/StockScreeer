#!/usr/bin/env python3
"""
Bollinger Bands Visualization GUI

Interactive chart to visualize price with Bollinger Bands overlay and indicators.
Uses Yahoo Finance data from yfinance_daily_quotes table.

Features:
- Price chart with Upper, Middle, Lower bands
- %b indicator subplot
- BandWidth indicator subplot  
- Volume bars
- Symbol dropdown selection (searchable)
- 1Y, 2Y, 3Y, 5Y time range buttons
- Squeeze highlighting (yellow regions)
- Crosshair with data tooltip
- No weekend gaps in chart

Usage:
    python bollinger/launch_bb_visualizer.py
"""

import sys
import os
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFrame, QSplitter,
    QGroupBox, QStatusBar, QMessageBox, QLineEdit, QCompleter
)
from PyQt6.QtCore import Qt, QStringListModel, QRectF, QPointF
from PyQt6.QtGui import QFont, QColor, QPainter, QPicture, QPen, QBrush

import pandas as pd
import numpy as np

try:
    import pyqtgraph as pg
    from pyqtgraph import AxisItem
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    print("ERROR: pyqtgraph required. Install with: pip install pyqtgraph")
    sys.exit(1)

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Build version for tracking updates
BUILD_VERSION = "2025-12-03 01:00"


class TradingDateAxis(AxisItem):
    """Custom axis that maps sequential indices to trading dates (skips weekends)."""
    
    def __init__(self, dates: List[date] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dates = dates or []
    
    def set_dates(self, dates: List[date]):
        """Set the date list for mapping."""
        self.dates = dates
    
    def tickStrings(self, values, scale, spacing):
        """Convert index values to date strings."""
        strings = []
        for v in values:
            idx = int(round(v))
            if 0 <= idx < len(self.dates):
                d = self.dates[idx]
                strings.append(d.strftime('%b %d'))
            else:
                strings.append('')
        return strings


class CandlestickItem(pg.GraphicsObject):
    """
    Custom candlestick chart item for pyqtgraph.
    
    Displays OHLC data as traditional candlesticks with:
    - Green candles for up days (close > open)
    - Red candles for down days (close < open)
    - Wicks showing high/low
    """
    
    def __init__(self):
        super().__init__()
        self.data = []  # List of (index, open, high, low, close)
        self.picture = None
        self.bull_color = QColor('#00ff88')  # Green
        self.bear_color = QColor('#ff4466')  # Red
        self.wick_color = QColor('#ffffff')  # White wicks
    
    def set_data(self, data: List[Tuple[int, float, float, float, float]]):
        """
        Set candlestick data.
        
        Args:
            data: List of (index, open, high, low, close) tuples
        """
        self.data = data
        self.picture = None
        self.prepareGeometryChange()
        self.update()
    
    def generatePicture(self):
        """Generate the candlestick picture for rendering."""
        self.picture = QPicture()
        painter = QPainter(self.picture)
        
        # Candle width - smaller for gaps between candles
        candle_width = 0.35  # Reduced from 0.6 for better spacing
        
        for idx, o, h, l, c in self.data:
            # Determine if bullish or bearish
            if c >= o:
                color = self.bull_color
                body_top = c
                body_bottom = o
            else:
                color = self.bear_color
                body_top = o
                body_bottom = c
            
            # Draw wick (high-low line) - thinner
            wick_pen = QPen(self.wick_color)
            wick_pen.setWidthF(0.05)
            painter.setPen(wick_pen)
            painter.drawLine(QPointF(idx, l), QPointF(idx, h))
            
            # Draw body with thin border
            border_pen = QPen(color.darker(120))
            border_pen.setWidthF(0.02)
            painter.setPen(border_pen)
            painter.setBrush(QBrush(color))
            
            body_height = body_top - body_bottom
            if body_height < 0.001:  # Doji - very small body
                body_height = 0.001
            
            painter.drawRect(QRectF(
                idx - candle_width / 2,
                body_bottom,
                candle_width,
                body_height
            ))
        
        painter.end()
    
    def paint(self, painter, option, widget):
        """Paint the candlesticks."""
        if self.picture is None:
            self.generatePicture()
        if self.picture:
            self.picture.play(painter)
    
    def boundingRect(self):
        """Return bounding rectangle for the item."""
        if not self.data:
            return QRectF()
        
        if self.picture is None:
            self.generatePicture()
        
        return QRectF(self.picture.boundingRect())


# Chart colors
COLORS = {
    'background': '#1a1a2e',
    'grid': '#2d2d44',
    'price': '#00d4ff',           # Cyan
    'candle_up': '#00ff88',       # Green
    'candle_down': '#ff4466',     # Red
    'upper_band': '#00ff88',      # Green
    'middle_band': '#ffaa00',     # Orange
    'lower_band': '#ff4466',      # Red/Pink
    'fill': (0, 212, 255, 25),    # Light cyan fill
    'percent_b': '#aa66ff',       # Purple
    'bandwidth': '#00ccff',       # Cyan
    'volume_up': '#00ff88',       # Green
    'volume_down': '#ff4466',     # Red
    'squeeze': (255, 235, 59, 40),# Yellow highlight
    'overbought': '#ff4466',      # Red line
    'oversold': '#00ff88',        # Green line
}


@dataclass
class OHLCData:
    """OHLC + BB data for a single day."""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    upper: float = None
    middle: float = None
    lower: float = None
    percent_b: float = None
    bandwidth: float = None
    bandwidth_pct: float = None


class BBVisualizerGUI(QMainWindow):
    """Main GUI for Bollinger Bands visualization."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"📈 Bollinger Bands Visualizer  [Build: {BUILD_VERSION}]")
        self.setMinimumSize(1400, 900)
        
        self.engine = self._get_engine()
        self.symbols = []
        self.current_symbol = None
        self.current_data: List[OHLCData] = []
        self.current_years = 1
        self.index_to_data: Dict[int, OHLCData] = {}
        
        # Configure pyqtgraph
        pg.setConfigOptions(antialias=True)
        
        self._setup_ui()
        self._load_symbols()
        
        # Default: load first symbol with 1 year
        if self.symbols:
            self.symbol_combo.setCurrentIndex(0)
            self._on_symbol_changed()
    
    def _get_engine(self) -> Engine:
        """Create database engine."""
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_DB', 'stockdata')
        
        encoded_password = quote_plus(password)
        conn_str = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
        return create_engine(conn_str, pool_pre_ping=True)
    
    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Top control bar
        control_bar = self._create_control_bar()
        layout.addWidget(control_bar)
        
        # Charts area
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.setBackground(COLORS['background'])
        
        # Create all chart plots
        self._create_charts()
        
        layout.addWidget(self.graphics_widget)
        
        # Info bar at bottom
        self.info_bar = self._create_info_bar()
        layout.addWidget(self.info_bar)
        
        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready - Select a symbol to view Bollinger Bands")
    
    def _create_control_bar(self) -> QFrame:
        """Create top control bar with symbol selector and time buttons."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { 
                background: #16213e; 
                border-radius: 8px; 
                padding: 10px;
            }
            QLabel { color: white; font-weight: bold; }
            QComboBox { 
                background: #1a1a2e; 
                color: white; 
                border: 2px solid #00d4ff;
                border-radius: 4px;
                padding: 8px 12px;
                min-width: 200px;
                font-size: 14px;
                font-weight: bold;
            }
            QComboBox:drop-down { 
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid #00d4ff;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: #1a1a2e;
                color: white;
                selection-background-color: #00d4ff;
                selection-color: #1a1a2e;
                border: 1px solid #3d3d5c;
                padding: 5px;
            }
            QPushButton {
                background: #3d3d5c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #4d4d6c; }
            QPushButton:checked { 
                background: #00d4ff; 
                color: #1a1a2e;
            }
            QLineEdit {
                background: #1a1a2e;
                color: white;
                border: 1px solid #3d3d5c;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Symbol selection with prominent dropdown
        layout.addWidget(QLabel("📈 Symbol:"))
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.symbol_combo.setMaxVisibleItems(20)  # Show more items in dropdown
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        self.symbol_combo.lineEdit().setPlaceholderText("Type to search...")
        layout.addWidget(self.symbol_combo)
        
        layout.addSpacing(30)
        
        # Time range buttons
        layout.addWidget(QLabel("Period:"))
        
        self.time_buttons = {}
        for years, label in [(1, "1Y"), (2, "2Y"), (3, "3Y"), (5, "5Y")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(years == 1)  # Default 1Y
            btn.clicked.connect(lambda checked, y=years: self._on_time_range_clicked(y))
            self.time_buttons[years] = btn
            layout.addWidget(btn)
        
        layout.addSpacing(30)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_chart)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        # Current symbol info
        self.symbol_info = QLabel("")
        self.symbol_info.setStyleSheet("color: #00d4ff; font-size: 14px;")
        layout.addWidget(self.symbol_info)
        
        return frame
    
    def _create_charts(self):
        """Create all chart subplots."""
        # Custom date axis that skips weekends
        self.date_axis = TradingDateAxis(orientation='bottom')
        self.date_axis.setPen(pg.mkPen('white'))
        
        # Main price chart (largest)
        self.price_plot = self.graphics_widget.addPlot(row=0, col=0, axisItems={'bottom': self.date_axis})
        self.price_plot.setLabel('left', 'Price', color='white')
        self.price_plot.showGrid(x=True, y=True, alpha=0.2)
        self.price_plot.getAxis('left').setPen(pg.mkPen('white'))
        
        # Create candlestick chart item
        self.candlestick_item = CandlestickItem()
        self.price_plot.addItem(self.candlestick_item)
        
        # Bollinger Bands
        self.upper_band = self.price_plot.plot(
            pen=pg.mkPen(COLORS['upper_band'], width=1.5, style=Qt.PenStyle.DashLine),
            name='Upper Band'
        )
        self.middle_band = self.price_plot.plot(
            pen=pg.mkPen(COLORS['middle_band'], width=1.5),
            name='SMA 20'
        )
        self.lower_band = self.price_plot.plot(
            pen=pg.mkPen(COLORS['lower_band'], width=1.5, style=Qt.PenStyle.DashLine),
            name='Lower Band'
        )
        
        # Fill between bands
        self.band_fill = pg.FillBetweenItem(
            self.upper_band, self.lower_band,
            brush=pg.mkBrush(*COLORS['fill'])
        )
        self.price_plot.addItem(self.band_fill)
        
        # Legend
        self.price_plot.addLegend(offset=(10, 10))
        
        # %b indicator subplot
        self.graphics_widget.nextRow()
        self.pb_plot = self.graphics_widget.addPlot(row=1, col=0)
        self.pb_plot.setLabel('left', '%b', color='white')
        self.pb_plot.setMaximumHeight(120)
        self.pb_plot.showGrid(x=True, y=True, alpha=0.2)
        self.pb_plot.getAxis('left').setPen(pg.mkPen('white'))
        self.pb_plot.setXLink(self.price_plot)
        
        # %b reference lines
        self.pb_plot.addLine(y=0, pen=pg.mkPen(COLORS['oversold'], width=1, style=Qt.PenStyle.DashLine))
        self.pb_plot.addLine(y=0.5, pen=pg.mkPen('gray', width=1, style=Qt.PenStyle.DotLine))
        self.pb_plot.addLine(y=1, pen=pg.mkPen(COLORS['overbought'], width=1, style=Qt.PenStyle.DashLine))
        
        self.pb_line = self.pb_plot.plot(pen=pg.mkPen(COLORS['percent_b'], width=2))
        
        # BandWidth subplot
        self.graphics_widget.nextRow()
        self.bw_plot = self.graphics_widget.addPlot(row=2, col=0)
        self.bw_plot.setLabel('left', 'BandWidth', color='white')
        self.bw_plot.setMaximumHeight(100)
        self.bw_plot.showGrid(x=True, y=True, alpha=0.2)
        self.bw_plot.getAxis('left').setPen(pg.mkPen('white'))
        self.bw_plot.setXLink(self.price_plot)
        
        self.bw_line = self.bw_plot.plot(pen=pg.mkPen(COLORS['bandwidth'], width=2))
        self.squeeze_regions = []
        
        # Volume subplot
        self.graphics_widget.nextRow()
        self.volume_plot = self.graphics_widget.addPlot(row=3, col=0)
        self.volume_plot.setLabel('left', 'Volume', color='white')
        self.volume_plot.setMaximumHeight(80)
        self.volume_plot.showGrid(x=True, y=True, alpha=0.2)
        self.volume_plot.getAxis('left').setPen(pg.mkPen('white'))
        self.volume_plot.setXLink(self.price_plot)
        
        self.volume_bars = pg.BarGraphItem(x=[], height=[], width=0.8, brush='gray')
        self.volume_plot.addItem(self.volume_bars)
        
        # Crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('white', width=0.5))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('white', width=0.5))
        self.price_plot.addItem(self.vLine, ignoreBounds=True)
        self.price_plot.addItem(self.hLine, ignoreBounds=True)
        
        # Mouse tracking
        self.price_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
    
    def _create_info_bar(self) -> QFrame:
        """Create info bar showing data at cursor position."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { 
                background: #16213e; 
                border-radius: 6px;
                padding: 8px;
            }
            QLabel { 
                color: white; 
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 8, 15, 8)
        
        self.info_date = QLabel("Date: --")
        self.info_ohlc = QLabel("O: -- H: -- L: -- C: --")
        self.info_bands = QLabel("Upper: -- Middle: -- Lower: --")
        self.info_pb = QLabel("%b: --")
        self.info_bw = QLabel("BW: --")
        self.info_status = QLabel("")
        
        for lbl in [self.info_date, self.info_ohlc, self.info_bands, 
                    self.info_pb, self.info_bw, self.info_status]:
            layout.addWidget(lbl)
        
        layout.addStretch()
        
        return frame
    
    def _load_symbols(self):
        """Load Nifty 500 symbols from database."""
        try:
            # First try to get Nifty 500 symbols from nifty500_list table
            nifty500_query = """
                SELECT DISTINCT symbol 
                FROM nifty500_list 
                ORDER BY symbol
            """
            
            # Also get indices
            indices_query = """
                SELECT DISTINCT symbol 
                FROM yfinance_daily_quotes 
                WHERE symbol LIKE '^%%'
                ORDER BY symbol
            """
            
            with self.engine.connect() as conn:
                # Try Nifty 500 table first
                try:
                    result = conn.execute(text(nifty500_query))
                    nifty500_symbols = [row[0] for row in result]
                except:
                    nifty500_symbols = []
                
                # Get indices
                result = conn.execute(text(indices_query))
                indices = [row[0] for row in result]
                
                # If no Nifty 500 table, fall back to yahoo finance table
                if not nifty500_symbols:
                    fallback_query = """
                        SELECT DISTINCT symbol 
                        FROM yfinance_daily_quotes 
                        WHERE symbol NOT LIKE '^%%'
                        ORDER BY symbol
                    """
                    result = conn.execute(text(fallback_query))
                    nifty500_symbols = [row[0] for row in result]
            
            # Combine: indices first, then Nifty 500 stocks
            self.symbols = indices + nifty500_symbols
            
            self.symbol_combo.clear()
            self.symbol_combo.addItems(self.symbols)
            
            # Setup completer for search
            completer = QCompleter(self.symbols)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.symbol_combo.setCompleter(completer)
            
            self.statusBar().showMessage(f"Loaded {len(indices)} indices + {len(nifty500_symbols)} Nifty 500 stocks")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load symbols:\n{e}")
    
    def _on_symbol_changed(self):
        """Handle symbol selection change."""
        symbol = self.symbol_combo.currentText().strip()
        if symbol and symbol in self.symbols:
            self.current_symbol = symbol
            self._load_and_display_data()
    
    def _on_time_range_clicked(self, years: int):
        """Handle time range button click."""
        self.current_years = years
        
        # Update button states
        for y, btn in self.time_buttons.items():
            btn.setChecked(y == years)
        
        if self.current_symbol:
            self._load_and_display_data()
    
    def _refresh_chart(self):
        """Refresh current chart."""
        if self.current_symbol:
            self._load_and_display_data()
    
    def _load_and_display_data(self):
        """Load data from database and display on chart."""
        if not self.current_symbol:
            return
        
        self.statusBar().showMessage(f"Loading {self.current_symbol}...")
        
        try:
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=self.current_years * 365)
            
            # Fetch OHLC data
            query = """
                SELECT date, open, high, low, close, volume
                FROM yfinance_daily_quotes
                WHERE symbol = :symbol
                  AND date BETWEEN :start AND :end
                ORDER BY date ASC
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params={
                    'symbol': self.current_symbol,
                    'start': start_date,
                    'end': end_date
                })
            
            if df.empty:
                self.statusBar().showMessage(f"No data found for {self.current_symbol}")
                return
            
            # Calculate Bollinger Bands
            df = self._calculate_bollinger_bands(df)
            
            # Convert to OHLCData list
            self.current_data = []
            for _, row in df.iterrows():
                self.current_data.append(OHLCData(
                    date=row['date'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume']),
                    upper=float(row['upper']) if pd.notna(row['upper']) else None,
                    middle=float(row['middle']) if pd.notna(row['middle']) else None,
                    lower=float(row['lower']) if pd.notna(row['lower']) else None,
                    percent_b=float(row['percent_b']) if pd.notna(row['percent_b']) else None,
                    bandwidth=float(row['bandwidth']) if pd.notna(row['bandwidth']) else None,
                    bandwidth_pct=float(row['bandwidth_pct']) if pd.notna(row['bandwidth_pct']) else None
                ))
            
            # Update charts
            self._update_charts()
            
            # Update symbol info
            latest = self.current_data[-1] if self.current_data else None
            if latest and latest.close:
                change = ((latest.close - self.current_data[0].close) / self.current_data[0].close * 100) if self.current_data[0].close else 0
                self.symbol_info.setText(
                    f"{self.current_symbol}  |  ₹{latest.close:,.2f}  |  "
                    f"{self.current_years}Y: {change:+.1f}%"
                )
            
            self.statusBar().showMessage(
                f"Loaded {len(self.current_data)} days for {self.current_symbol}"
            )
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load data:\n{e}")
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Calculate Bollinger Bands indicators."""
        df = df.copy()
        
        # Middle band (SMA)
        df['middle'] = df['close'].rolling(window=period).mean()
        df['std'] = df['close'].rolling(window=period).std()
        
        # Upper and lower bands
        df['upper'] = df['middle'] + (std_dev * df['std'])
        df['lower'] = df['middle'] - (std_dev * df['std'])
        
        # %b = (close - lower) / (upper - lower)
        df['percent_b'] = (df['close'] - df['lower']) / (df['upper'] - df['lower'])
        
        # BandWidth = (upper - lower) / middle * 100
        df['bandwidth'] = ((df['upper'] - df['lower']) / df['middle']) * 100
        
        # Bandwidth percentile (126-day rolling)
        df['bandwidth_pct'] = df['bandwidth'].rolling(window=126, min_periods=20).apply(
            lambda x: (x.values < x.values[-1]).sum() / len(x) * 100 if len(x) > 0 else 50
        )
        
        return df
    
    def _update_charts(self):
        """Update all chart plots with current data (using sequential indices to skip weekends)."""
        if not self.current_data:
            return
        
        # Filter to data with BB values
        valid_data = [d for d in self.current_data if d.middle is not None]
        
        if not valid_data:
            return
        
        # Use sequential indices instead of timestamps (skips weekends/holidays)
        indices = list(range(len(valid_data)))
        dates = [d.date for d in valid_data]
        
        # Update the custom date axis with the date mapping
        self.date_axis.set_dates(dates)
        
        # Store index-to-data mapping for crosshair lookup
        self.index_to_data = {i: d for i, d in enumerate(valid_data)}
        
        # Candlestick data: (index, open, high, low, close)
        candle_data = [(i, d.open, d.high, d.low, d.close) for i, d in enumerate(valid_data)]
        self.candlestick_item.set_data(candle_data)
        
        # Bollinger Bands
        upper = [d.upper for d in valid_data]
        middle = [d.middle for d in valid_data]
        lower = [d.lower for d in valid_data]
        
        self.upper_band.setData(indices, upper)
        self.middle_band.setData(indices, middle)
        self.lower_band.setData(indices, lower)
        
        # %b
        pb = [d.percent_b if d.percent_b else 0.5 for d in valid_data]
        self.pb_line.setData(indices, pb)
        
        # BandWidth
        bw = [d.bandwidth if d.bandwidth else 0 for d in valid_data]
        self.bw_line.setData(indices, bw)
        
        # Highlight squeeze regions (bandwidth percentile < 10)
        self._highlight_squeeze_regions(indices, valid_data)
        
        # Volume bars with color based on price change
        # Use same valid_data and indices as candlesticks to keep alignment
        volumes = [d.volume for d in valid_data]
        
        # Color bars based on close vs open
        brushes = []
        for d in valid_data:
            if d.close >= d.open:
                brushes.append(pg.mkBrush(COLORS['volume_up']))
            else:
                brushes.append(pg.mkBrush(COLORS['volume_down']))
        
        self.volume_bars.setOpts(
            x=indices, 
            height=volumes, 
            width=0.7,
            brushes=brushes
        )
    
    def _highlight_squeeze_regions(self, indices: List[int], data: List[OHLCData]):
        """Highlight squeeze regions on bandwidth chart."""
        # Clear existing regions
        for region in self.squeeze_regions:
            self.bw_plot.removeItem(region)
        self.squeeze_regions.clear()
        
        # Find squeeze periods (bandwidth percentile < 10)
        in_squeeze = False
        squeeze_start = None
        
        for i, d in enumerate(data):
            is_squeeze = d.bandwidth_pct is not None and d.bandwidth_pct < 10
            
            if is_squeeze and not in_squeeze:
                squeeze_start = indices[i]
                in_squeeze = True
            elif not is_squeeze and in_squeeze:
                region = pg.LinearRegionItem(
                    [squeeze_start, indices[i]],
                    brush=pg.mkBrush(*COLORS['squeeze']),
                    movable=False
                )
                self.bw_plot.addItem(region)
                self.squeeze_regions.append(region)
                in_squeeze = False
        
        # Handle if still in squeeze at end
        if in_squeeze and squeeze_start:
            region = pg.LinearRegionItem(
                [squeeze_start, indices[-1]],
                brush=pg.mkBrush(*COLORS['squeeze']),
                movable=False
            )
            self.bw_plot.addItem(region)
            self.squeeze_regions.append(region)
    
    def _on_mouse_moved(self, pos):
        """Handle mouse movement for crosshair and info update."""
        if not hasattr(self, 'index_to_data') or not self.index_to_data:
            return
        
        mouse_point = self.price_plot.vb.mapSceneToView(pos)
        
        self.vLine.setPos(mouse_point.x())
        self.hLine.setPos(mouse_point.y())
        
        # Find nearest data point using index
        idx = int(round(mouse_point.x()))
        if idx in self.index_to_data:
            self._update_info_bar(self.index_to_data[idx])
    
    def _update_info_bar(self, d: OHLCData):
        """Update info bar with data point values."""
        self.info_date.setText(f"Date: {d.date.strftime('%Y-%m-%d')}")
        self.info_ohlc.setText(f"O: {d.open:.2f}  H: {d.high:.2f}  L: {d.low:.2f}  C: {d.close:.2f}")
        
        if d.upper and d.middle and d.lower:
            self.info_bands.setText(f"Upper: {d.upper:.2f}  Middle: {d.middle:.2f}  Lower: {d.lower:.2f}")
        else:
            self.info_bands.setText("Bands: --")
        
        if d.percent_b is not None:
            self.info_pb.setText(f"%b: {d.percent_b:.3f}")
            # Color based on value
            if d.percent_b > 1:
                self.info_pb.setStyleSheet("color: #ff4466;")  # Overbought
            elif d.percent_b < 0:
                self.info_pb.setStyleSheet("color: #00ff88;")  # Oversold
            else:
                self.info_pb.setStyleSheet("color: white;")
        else:
            self.info_pb.setText("%b: --")
        
        if d.bandwidth is not None:
            self.info_bw.setText(f"BW: {d.bandwidth:.2f}%")
        else:
            self.info_bw.setText("BW: --")
        
        # Status (squeeze indicator)
        if d.bandwidth_pct is not None and d.bandwidth_pct < 10:
            self.info_status.setText("⚡ SQUEEZE")
            self.info_status.setStyleSheet("color: #FFEB3B; font-weight: bold;")
        elif d.bandwidth_pct is not None and d.bandwidth_pct > 90:
            self.info_status.setText("📈 EXPANSION")
            self.info_status.setStyleSheet("color: #00d4ff;")
        else:
            self.info_status.setText("")


def main():
    app = QApplication(sys.argv)
    
    # Dark theme
    app.setStyle('Fusion')
    
    window = BBVisualizerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
