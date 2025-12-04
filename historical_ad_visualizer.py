#!/usr/bin/env python3
"""
Historical Advance/Decline Visualizer
=====================================

PyQtGraph-based visualizer showing:
- Top: NIFTY 50 daily candlestick chart
- Bottom: Advance/Decline indicators (Advances, Declines, Net A/D, A/D Ratio)

Features:
- Duration picker: 1M, 3M, 6M, 1Y, 2Y, 5Y, All
- Turning point detection (extreme A/D values)
- Post-turning-point NIFTY performance analysis
- Interactive crosshair cursor

Author: StockScreener Project
Date: December 2025
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# PyQtGraph imports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QFrame, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QStatusBar, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg

# SQLAlchemy for database
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Database Configuration
# ============================================================================

def get_engine():
    """Create SQLAlchemy engine with proper password handling."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DB", "stock_screener"),
        query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_nifty_data(engine, start_date=None, end_date=None):
    """Load NIFTY 50 daily OHLCV data from yfinance_indices_daily_quotes."""
    query = """
        SELECT date, open, high, low, close, volume
        FROM yfinance_indices_daily_quotes
        WHERE symbol = '^NSEI'
    """
    params = {}
    
    if start_date:
        query += " AND date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND date <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY date ASC"
    
    df = pd.read_sql(text(query), engine, params=params)
    df['date'] = pd.to_datetime(df['date'])
    return df


def load_ad_data(engine, start_date=None, end_date=None):
    """Load Advance/Decline data from yfinance_advance_decline table."""
    query = """
        SELECT 
            trade_date, advances, declines, unchanged, total_stocks,
            net_advance_decline, ad_ratio,
            gain_0_1, gain_1_2, gain_2_3, gain_3_5, gain_5_plus,
            loss_0_1, loss_1_2, loss_2_3, loss_3_5, loss_5_plus
        FROM yfinance_advance_decline
    """
    params = {}
    
    if start_date:
        query += " WHERE trade_date >= :start_date"
        params['start_date'] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params['end_date'] = end_date
    elif end_date:
        query += " WHERE trade_date <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY trade_date ASC"
    
    df = pd.read_sql(text(query), engine, params=params)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df


# ============================================================================
# Turning Point Detection
# ============================================================================

def detect_turning_points(ad_df, threshold_ratio_low=0.35, threshold_ratio_high=2.5):
    """
    Detect turning points where A/D ratio reaches extremes.
    
    Bearish turning point: A/D ratio < threshold_ratio_low (more declines than advances)
    Bullish turning point: A/D ratio > threshold_ratio_high (more advances than declines)
    
    Returns DataFrame with turning points and their characteristics.
    """
    turning_points = []
    
    for idx, row in ad_df.iterrows():
        tp_type = None
        if row['ad_ratio'] <= threshold_ratio_low:
            tp_type = 'bearish_extreme'  # Many declines - potential bottom
        elif row['ad_ratio'] >= threshold_ratio_high:
            tp_type = 'bullish_extreme'  # Many advances - potential top
        
        if tp_type:
            turning_points.append({
                'date': row['trade_date'],
                'type': tp_type,
                'ad_ratio': row['ad_ratio'],
                'advances': row['advances'],
                'declines': row['declines'],
                'net_ad': row['net_advance_decline']
            })
    
    return pd.DataFrame(turning_points)


def calculate_post_turning_performance(turning_points_df, nifty_df):
    """
    Calculate NIFTY performance after each turning point.
    
    Returns DataFrame with +1, +5, +10, +20 day returns after turning points.
    """
    if turning_points_df.empty:
        return pd.DataFrame()
    
    nifty_df = nifty_df.set_index('date')
    results = []
    
    for _, tp in turning_points_df.iterrows():
        tp_date = tp['date']
        
        # Find the close price on turning point date
        if tp_date not in nifty_df.index:
            # Find nearest date
            nearest = nifty_df.index[nifty_df.index.get_indexer([tp_date], method='nearest')[0]]
            tp_close = nifty_df.loc[nearest, 'close']
        else:
            tp_close = nifty_df.loc[tp_date, 'close']
        
        result = {
            'date': tp_date,
            'type': tp['type'],
            'ad_ratio': tp['ad_ratio'],
            'nifty_close': tp_close,
        }
        
        # Calculate returns for different periods
        for days in [1, 5, 10, 20]:
            future_date = tp_date + timedelta(days=days)
            
            # Find closest trading date
            future_dates = nifty_df.index[nifty_df.index >= future_date]
            if len(future_dates) > 0:
                future_close = nifty_df.loc[future_dates[0], 'close']
                return_pct = ((future_close - tp_close) / tp_close) * 100
                result[f'+{days}d_return'] = return_pct
            else:
                result[f'+{days}d_return'] = None
        
        results.append(result)
    
    return pd.DataFrame(results)


# ============================================================================
# Custom Candlestick Item
# ============================================================================

class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick chart item for PyQtGraph."""
    
    def __init__(self, data):
        """
        data: DataFrame with columns 'date', 'open', 'high', 'low', 'close'
        """
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.generatePicture()
    
    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.picture)
        
        w = 0.6  # width of candlestick body
        
        for i, row in self.data.iterrows():
            x = i  # Use index as x position
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            
            if c >= o:
                # Green/bullish candle
                p.setPen(pg.mkPen('#00aa00'))
                p.setBrush(pg.mkBrush('#00aa00'))
            else:
                # Red/bearish candle
                p.setPen(pg.mkPen('#ff0000'))
                p.setBrush(pg.mkBrush('#ff0000'))
            
            # Draw wick (high-low line)
            p.drawLine(pg.QtCore.QPointF(x, l), pg.QtCore.QPointF(x, h))
            
            # Draw body
            p.drawRect(pg.QtCore.QRectF(x - w/2, min(o, c), w, abs(c - o) or 0.01))
        
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())


# ============================================================================
# Main Visualizer Window
# ============================================================================

class HistoricalADVisualizer(QMainWindow):
    """Main window for Historical Advance/Decline Visualization."""
    
    DURATION_MAP = {
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365,
        '2Y': 730,
        '5Y': 1825,
        'All': None
    }
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Historical Advance/Decline Visualizer")
        self.setGeometry(100, 100, 1400, 900)
        
        # Database connection
        self.engine = get_engine()
        
        # Data containers
        self.nifty_df = pd.DataFrame()
        self.ad_df = pd.DataFrame()
        self.turning_points = pd.DataFrame()
        self.performance_df = pd.DataFrame()
        
        # Current duration
        self.current_duration = '1Y'
        
        # Setup UI
        self.setup_ui()
        
        # Setup crosshair (must be before load_data)
        self.setup_crosshair()
        
        # Load initial data
        self.load_data()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # ─────────────────────────────────────────────────────────────────
        # TOP: Controls Bar
        # ─────────────────────────────────────────────────────────────────
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_frame.setStyleSheet("QFrame { background-color: #2d2d2d; border-radius: 5px; }")
        controls_layout = QHBoxLayout(controls_frame)
        
        # Title
        title_label = QLabel("📊 Historical Advance/Decline Visualizer")
        title_label.setFont(QFont('Segoe UI', 14, QFont.Bold))
        title_label.setStyleSheet("color: #00ff88;")
        controls_layout.addWidget(title_label)
        
        controls_layout.addStretch()
        
        # Visibility toggles
        toggle_label = QLabel("Show:")
        toggle_label.setStyleSheet("color: #888;")
        controls_layout.addWidget(toggle_label)
        
        checkbox_style = """
            QCheckBox {
                color: white;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #00aaff;
                border: 1px solid #00aaff;
                border-radius: 3px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 3px;
            }
        """
        
        self.chk_advances = QCheckBox("Advances")
        self.chk_advances.setChecked(True)
        self.chk_advances.setStyleSheet(checkbox_style)
        self.chk_advances.toggled.connect(self.toggle_advances)
        controls_layout.addWidget(self.chk_advances)
        
        self.chk_declines = QCheckBox("Declines")
        self.chk_declines.setChecked(True)
        self.chk_declines.setStyleSheet(checkbox_style)
        self.chk_declines.toggled.connect(self.toggle_declines)
        controls_layout.addWidget(self.chk_declines)
        
        self.chk_ratio = QCheckBox("A/D Ratio")
        self.chk_ratio.setChecked(True)
        self.chk_ratio.setStyleSheet(checkbox_style)
        self.chk_ratio.toggled.connect(self.toggle_ratio)
        controls_layout.addWidget(self.chk_ratio)
        
        self.chk_cumulative = QCheckBox("Cumulative")
        self.chk_cumulative.setChecked(True)
        self.chk_cumulative.setStyleSheet(checkbox_style)
        self.chk_cumulative.toggled.connect(self.toggle_cumulative)
        controls_layout.addWidget(self.chk_cumulative)
        
        self.chk_turning_points = QCheckBox("Turning Pts")
        self.chk_turning_points.setChecked(True)
        self.chk_turning_points.setStyleSheet(checkbox_style)
        self.chk_turning_points.toggled.connect(self.toggle_turning_points)
        controls_layout.addWidget(self.chk_turning_points)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #555;")
        controls_layout.addWidget(sep)
        
        # Duration picker
        duration_label = QLabel("Duration:")
        duration_label.setStyleSheet("color: white;")
        controls_layout.addWidget(duration_label)
        
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(list(self.DURATION_MAP.keys()))
        self.duration_combo.setCurrentText(self.current_duration)
        self.duration_combo.currentTextChanged.connect(self.on_duration_changed)
        self.duration_combo.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                min-width: 80px;
            }
        """)
        controls_layout.addWidget(self.duration_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0077ee;
            }
        """)
        controls_layout.addWidget(refresh_btn)
        
        layout.addWidget(controls_frame)
        
        # ─────────────────────────────────────────────────────────────────
        # MIDDLE: Charts (Splitter)
        # ─────────────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Vertical)
        
        # PyQtGraph styling
        pg.setConfigOptions(antialias=True)
        
        # TOP CHART: NIFTY 50 Price
        self.nifty_widget = pg.PlotWidget()
        self.nifty_widget.setBackground('#1e1e1e')
        self.nifty_widget.showGrid(x=True, y=True, alpha=0.3)
        self.nifty_widget.setLabel('left', 'NIFTY 50', color='white')
        self.nifty_widget.setLabel('bottom', 'Date', color='white')
        self.nifty_plot = self.nifty_widget.getPlotItem()
        splitter.addWidget(self.nifty_widget)
        
        # BOTTOM CHART: A/D Indicators (stacked)
        ad_widget = QWidget()
        ad_layout = QVBoxLayout(ad_widget)
        ad_layout.setSpacing(2)
        ad_layout.setContentsMargins(0, 0, 0, 0)
        
        # A/D Line Chart (Advances vs Declines) - changed from bar to line
        self.ad_line_widget = pg.PlotWidget()
        self.ad_line_widget.setBackground('#1e1e1e')
        self.ad_line_widget.showGrid(x=True, y=True, alpha=0.3)
        self.ad_line_widget.setLabel('left', 'A/D Count', color='white')
        self.ad_line_widget.setXLink(self.nifty_widget)  # Link X axis
        self.ad_line_widget.addLegend(offset=(70, 10))
        ad_layout.addWidget(self.ad_line_widget, stretch=1)
        
        # A/D Ratio Line Chart
        self.ad_ratio_widget = pg.PlotWidget()
        self.ad_ratio_widget.setBackground('#1e1e1e')
        self.ad_ratio_widget.showGrid(x=True, y=True, alpha=0.3)
        self.ad_ratio_widget.setLabel('left', 'A/D Ratio', color='white')
        self.ad_ratio_widget.setXLink(self.nifty_widget)  # Link X axis
        ad_layout.addWidget(self.ad_ratio_widget, stretch=1)
        
        # Net A/D Cumulative
        self.net_ad_widget = pg.PlotWidget()
        self.net_ad_widget.setBackground('#1e1e1e')
        self.net_ad_widget.showGrid(x=True, y=True, alpha=0.3)
        self.net_ad_widget.setLabel('left', 'Cumulative Net A/D', color='white')
        self.net_ad_widget.setXLink(self.nifty_widget)
        ad_layout.addWidget(self.net_ad_widget, stretch=1)
        
        splitter.addWidget(ad_widget)
        
        # Set splitter proportions (60% nifty, 40% A/D)
        splitter.setSizes([500, 350])
        
        layout.addWidget(splitter, stretch=1)
        
        # ─────────────────────────────────────────────────────────────────
        # BOTTOM: Turning Points Table
        # ─────────────────────────────────────────────────────────────────
        tp_group = QGroupBox("📍 Turning Points & Post-Event NIFTY Performance")
        tp_group.setStyleSheet("""
            QGroupBox {
                color: #00aaff;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        tp_layout = QVBoxLayout(tp_group)
        
        self.tp_table = QTableWidget()
        self.tp_table.setColumnCount(9)
        self.tp_table.setHorizontalHeaderLabels([
            'Date', 'Type', 'A/D Ratio', 'Advances', 'Declines',
            'NIFTY Close', '+1d %', '+5d %', '+20d %'
        ])
        self.tp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tp_table.setAlternatingRowColors(True)
        self.tp_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                color: white;
                gridline-color: #444;
            }
            QTableWidget::item:alternate {
                background-color: #353535;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 5px;
                border: 1px solid #444;
            }
        """)
        tp_layout.addWidget(self.tp_table)
        
        layout.addWidget(tp_group)
        
        # ─────────────────────────────────────────────────────────────────
        # Status Bar
        # ─────────────────────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #2d2d2d; color: #888;")
        self.setStatusBar(self.status_bar)
        
        # Set dark theme for main window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
        """)
    
    def setup_crosshair(self):
        """Setup synchronized crosshair cursors for all charts."""
        crosshair_pen = pg.mkPen('#ffff00', width=1, style=Qt.DashLine)
        
        # Crosshairs for NIFTY chart
        self.vLine_nifty = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_nifty = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.nifty_widget.addItem(self.vLine_nifty, ignoreBounds=True)
        self.nifty_widget.addItem(self.hLine_nifty, ignoreBounds=True)
        
        # Crosshairs for A/D Line chart
        self.vLine_ad = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_ad = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.ad_line_widget.addItem(self.vLine_ad, ignoreBounds=True)
        self.ad_line_widget.addItem(self.hLine_ad, ignoreBounds=True)
        
        # Crosshairs for A/D Ratio chart
        self.vLine_ratio = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_ratio = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.ad_ratio_widget.addItem(self.vLine_ratio, ignoreBounds=True)
        self.ad_ratio_widget.addItem(self.hLine_ratio, ignoreBounds=True)
        
        # Crosshairs for Cumulative Net A/D chart
        self.vLine_cumulative = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_cumulative = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.net_ad_widget.addItem(self.vLine_cumulative, ignoreBounds=True)
        self.net_ad_widget.addItem(self.hLine_cumulative, ignoreBounds=True)
        
        # Connect mouse move for all charts
        self.nifty_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'nifty'))
        self.ad_line_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'ad'))
        self.ad_ratio_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'ratio'))
        self.net_ad_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'cumulative'))
    
    def mouse_moved(self, pos, source='nifty'):
        """Handle mouse movement for synchronized crosshairs."""
        # Determine which widget to use for coordinate mapping
        widget_map = {
            'nifty': self.nifty_widget,
            'ad': self.ad_line_widget,
            'ratio': self.ad_ratio_widget,
            'cumulative': self.net_ad_widget
        }
        
        source_widget = widget_map.get(source, self.nifty_widget)
        
        if source_widget.sceneBoundingRect().contains(pos):
            mouse_point = source_widget.getPlotItem().vb.mapSceneToView(pos)
            x_pos = mouse_point.x()
            
            # Update all vertical crosshairs to same X position (synchronized)
            self.vLine_nifty.setPos(x_pos)
            self.vLine_ad.setPos(x_pos)
            self.vLine_ratio.setPos(x_pos)
            self.vLine_cumulative.setPos(x_pos)
            
            # Update horizontal crosshair only for the source chart
            if source == 'nifty':
                self.hLine_nifty.setPos(mouse_point.y())
            elif source == 'ad':
                self.hLine_ad.setPos(mouse_point.y())
            elif source == 'ratio':
                self.hLine_ratio.setPos(mouse_point.y())
            elif source == 'cumulative':
                self.hLine_cumulative.setPos(mouse_point.y())
            
            # Update status bar with values at cursor position
            x_idx = int(round(x_pos))
            if 0 <= x_idx < len(self.nifty_df):
                row = self.nifty_df.iloc[x_idx]
                date_str = row['date'].strftime('%Y-%m-%d')
                
                # Build status message with OHLC
                status = f"Date: {date_str} | O:{row['open']:.0f} H:{row['high']:.0f} L:{row['low']:.0f} C:{row['close']:.0f}"
                
                # Get A/D data for same index
                if x_idx < len(self.ad_df):
                    ad_row = self.ad_df.iloc[x_idx]
                    status += f" | Adv:{ad_row['advances']} Dec:{ad_row['declines']} Ratio:{ad_row['ad_ratio']:.2f}"
                
                self.status_bar.showMessage(status)
    
    def on_duration_changed(self, duration):
        """Handle duration change."""
        self.current_duration = duration
        self.load_data()
    
    def load_data(self):
        """Load data based on selected duration."""
        self.status_bar.showMessage("Loading data...")
        
        # Calculate date range
        end_date = datetime.now().date()
        days = self.DURATION_MAP.get(self.current_duration)
        
        if days:
            start_date = end_date - timedelta(days=days)
        else:
            start_date = None
        
        try:
            # Load NIFTY data
            self.nifty_df = load_nifty_data(self.engine, start_date, end_date)
            
            # Load A/D data
            self.ad_df = load_ad_data(self.engine, start_date, end_date)
            
            # Detect turning points
            self.turning_points = detect_turning_points(self.ad_df)
            
            # Calculate post-turning-point performance
            if not self.turning_points.empty:
                self.performance_df = calculate_post_turning_performance(
                    self.turning_points, self.nifty_df
                )
            else:
                self.performance_df = pd.DataFrame()
            
            # Update charts
            self.update_charts()
            
            # Update turning points table
            self.update_tp_table()
            
            self.status_bar.showMessage(
                f"Loaded {len(self.nifty_df)} NIFTY records, {len(self.ad_df)} A/D records, "
                f"{len(self.turning_points)} turning points"
            )
            
        except Exception as e:
            self.status_bar.showMessage(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
    
    def update_charts(self):
        """Update all charts with loaded data."""
        # Clear existing plots
        self.nifty_widget.clear()
        self.ad_line_widget.clear()
        self.ad_ratio_widget.clear()
        self.net_ad_widget.clear()
        
        # Initialize plot item references
        self.plot_items = {
            'advances': None,
            'declines': None,
            'ratio': None,
            'cumulative': None,
            'cumulative_fill': None,
            'turning_points': []
        }
        
        if self.nifty_df.empty:
            return
        
        # Reset index for plotting
        self.nifty_df = self.nifty_df.reset_index(drop=True)
        if not self.ad_df.empty:
            self.ad_df = self.ad_df.reset_index(drop=True)
        
        x = np.arange(len(self.nifty_df))
        
        # ─────────────────────────────────────────────────────────────────
        # NIFTY Chart (Candlestick)
        # ─────────────────────────────────────────────────────────────────
        # Create candlestick chart
        candlestick = CandlestickItem(self.nifty_df)
        self.nifty_widget.addItem(candlestick)
        
        # Mark turning points on NIFTY chart
        if not self.turning_points.empty and self.chk_turning_points.isChecked():
            for _, tp in self.turning_points.iterrows():
                # Find index in nifty_df
                tp_date = tp['date']
                matches = self.nifty_df[self.nifty_df['date'] == tp_date]
                if not matches.empty:
                    idx = matches.index[0]
                    price = matches.iloc[0]['close']
                    
                    color = '#ff4444' if tp['type'] == 'bearish_extreme' else '#44ff44'
                    # Use 't' for triangle down (bullish extreme = top), 't1' for triangle up (bearish extreme = bottom)
                    symbol = 't' if tp['type'] == 'bullish_extreme' else 't1'
                    
                    tp_item = self.nifty_widget.plot(
                        [idx], [price],
                        pen=None,
                        symbol=symbol,
                        symbolSize=12,
                        symbolBrush=color
                    )
                    self.plot_items['turning_points'].append(tp_item)
        
        # Re-add crosshairs for all charts
        self.nifty_widget.addItem(self.vLine_nifty, ignoreBounds=True)
        self.nifty_widget.addItem(self.hLine_nifty, ignoreBounds=True)
        self.ad_line_widget.addItem(self.vLine_ad, ignoreBounds=True)
        self.ad_line_widget.addItem(self.hLine_ad, ignoreBounds=True)
        self.ad_ratio_widget.addItem(self.vLine_ratio, ignoreBounds=True)
        self.ad_ratio_widget.addItem(self.hLine_ratio, ignoreBounds=True)
        self.net_ad_widget.addItem(self.vLine_cumulative, ignoreBounds=True)
        self.net_ad_widget.addItem(self.hLine_cumulative, ignoreBounds=True)
        
        if self.ad_df.empty:
            return
        
        x_ad = np.arange(len(self.ad_df))
        
        # ─────────────────────────────────────────────────────────────────
        # A/D Line Chart (Advances vs Declines) - for crossover visibility
        # ─────────────────────────────────────────────────────────────────
        # Re-add legend
        self.ad_line_widget.addLegend(offset=(70, 10))
        
        # Advances (green line)
        if self.chk_advances.isChecked():
            self.plot_items['advances'] = self.ad_line_widget.plot(
                x_ad, self.ad_df['advances'].values,
                pen=pg.mkPen('#00ff00', width=2),
                name='Advances'
            )
        
        # Declines (red line)
        if self.chk_declines.isChecked():
            self.plot_items['declines'] = self.ad_line_widget.plot(
                x_ad, self.ad_df['declines'].values,
                pen=pg.mkPen('#ff4444', width=2),
                name='Declines'
            )
        
        # ─────────────────────────────────────────────────────────────────
        # A/D Ratio Chart
        # ─────────────────────────────────────────────────────────────────
        if self.chk_ratio.isChecked():
            self.plot_items['ratio'] = self.ad_ratio_widget.plot(
                x_ad, self.ad_df['ad_ratio'].values,
                pen=pg.mkPen('#ffaa00', width=2),
                name='A/D Ratio'
            )
            
            # Reference line at 1.0 (equal advances/declines)
            self.ad_ratio_widget.addLine(y=1.0, pen=pg.mkPen('#888888', width=1, style=Qt.DashLine))
            
            # Threshold lines
            self.ad_ratio_widget.addLine(y=0.35, pen=pg.mkPen('#ff4444', width=1, style=Qt.DotLine))
            self.ad_ratio_widget.addLine(y=2.5, pen=pg.mkPen('#44ff44', width=1, style=Qt.DotLine))
        
        # ─────────────────────────────────────────────────────────────────
        # Cumulative Net A/D Chart
        # ─────────────────────────────────────────────────────────────────
        if self.chk_cumulative.isChecked():
            cumulative_net_ad = self.ad_df['net_advance_decline'].cumsum()
            self.plot_items['cumulative'] = self.net_ad_widget.plot(
                x_ad, cumulative_net_ad.values,
                pen=pg.mkPen('#00aaff', width=2),
                name='Cumulative Net A/D'
            )
            
            # Fill area
            self.plot_items['cumulative_fill'] = pg.FillBetweenItem(
                pg.PlotCurveItem(x_ad, cumulative_net_ad.values),
                pg.PlotCurveItem(x_ad, np.zeros(len(x_ad))),
                brush=pg.mkBrush(0, 170, 255, 50)
            )
            self.net_ad_widget.addItem(self.plot_items['cumulative_fill'])
    
    # ─────────────────────────────────────────────────────────────────
    # Toggle visibility handlers
    # ─────────────────────────────────────────────────────────────────
    def toggle_advances(self, checked):
        """Toggle advances line visibility."""
        if hasattr(self, 'plot_items') and self.plot_items.get('advances'):
            self.plot_items['advances'].setVisible(checked)
        elif checked:
            self.update_charts()
    
    def toggle_declines(self, checked):
        """Toggle declines line visibility."""
        if hasattr(self, 'plot_items') and self.plot_items.get('declines'):
            self.plot_items['declines'].setVisible(checked)
        elif checked:
            self.update_charts()
    
    def toggle_ratio(self, checked):
        """Toggle A/D ratio visibility."""
        self.ad_ratio_widget.setVisible(checked)
    
    def toggle_cumulative(self, checked):
        """Toggle cumulative net A/D visibility."""
        self.net_ad_widget.setVisible(checked)
    
    def toggle_turning_points(self, checked):
        """Toggle turning point markers visibility."""
        if hasattr(self, 'plot_items'):
            for tp_item in self.plot_items.get('turning_points', []):
                tp_item.setVisible(checked)
    
    def update_tp_table(self):
        """Update turning points table."""
        self.tp_table.setRowCount(0)
        
        if self.performance_df.empty:
            return
        
        # Show most recent 20 turning points
        display_df = self.performance_df.tail(20).iloc[::-1]  # Reverse to show newest first
        
        self.tp_table.setRowCount(len(display_df))
        
        for i, (_, row) in enumerate(display_df.iterrows()):
            # Date
            self.tp_table.setItem(i, 0, QTableWidgetItem(row['date'].strftime('%Y-%m-%d')))
            
            # Type
            type_item = QTableWidgetItem(row['type'].replace('_', ' ').title())
            if 'bearish' in row['type']:
                type_item.setForeground(QColor('#ff4444'))
            else:
                type_item.setForeground(QColor('#44ff44'))
            self.tp_table.setItem(i, 1, type_item)
            
            # A/D Ratio
            self.tp_table.setItem(i, 2, QTableWidgetItem(f"{row['ad_ratio']:.2f}"))
            
            # Advances (from turning_points)
            tp_row = self.turning_points[self.turning_points['date'] == row['date']]
            if not tp_row.empty:
                self.tp_table.setItem(i, 3, QTableWidgetItem(str(tp_row.iloc[0]['advances'])))
                self.tp_table.setItem(i, 4, QTableWidgetItem(str(tp_row.iloc[0]['declines'])))
            
            # NIFTY Close
            self.tp_table.setItem(i, 5, QTableWidgetItem(f"{row['nifty_close']:.2f}"))
            
            # Returns
            for j, col in enumerate(['+1d_return', '+5d_return', '+20d_return']):
                val = row.get(col)
                if val is not None:
                    item = QTableWidgetItem(f"{val:+.2f}%")
                    if val > 0:
                        item.setForeground(QColor('#00ff00'))
                    elif val < 0:
                        item.setForeground(QColor('#ff4444'))
                    self.tp_table.setItem(i, 6 + j, item)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Launch the Historical A/D Visualizer."""
    app = QApplication(sys.argv)
    
    # Set application-wide dark palette
    app.setStyle('Fusion')
    
    window = HistoricalADVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
