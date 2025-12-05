#!/usr/bin/env python3
"""
Crypto Market Breadth Visualizer
================================

PyQtGraph-based visualizer for crypto market breadth showing:
- Top: BTC price chart (as market proxy)
- Middle: Advance/Decline indicators (advances, declines, A/D line)
- Bottom: Distribution heatmap (gain/loss buckets)

Features:
- Duration picker: 1M, 3M, 6M, 1Y, 2Y, All
- A/D Line (cumulative)
- % Gainers/Losers distribution
- Interactive crosshair cursor

Author: StockScreener Project
Date: December 2025
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# PyQt6/PyQt5 compatibility
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QComboBox, QPushButton, QFrame, QSplitter, QGroupBox,
        QStatusBar, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont, QColor
    PYQT_VERSION = 6
except ImportError:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QComboBox, QPushButton, QFrame, QSplitter, QGroupBox,
        QStatusBar, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont, QColor
    PYQT_VERSION = 5

import pyqtgraph as pg

# Import crypto services
from crypto.services.crypto_db_service import CryptoDBService


# ============================================================================
# Custom Candlestick Item
# ============================================================================

class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick chart item for PyQtGraph."""
    
    def __init__(self, data):
        """
        data: DataFrame with columns 'open_price', 'high_price', 'low_price', 'close_price'
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
            o = row['open_price']
            h = row['high_price']
            l = row['low_price']
            c = row['close_price']
            
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

class CryptoBreadthVisualizer(QMainWindow):
    """Main window for Crypto Market Breadth Visualization."""
    
    DURATION_MAP = {
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365,
        '2Y': 730,
        'All': None
    }
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🪙 Crypto Market Breadth Visualizer")
        self.setGeometry(100, 100, 1400, 900)
        
        # Database connection
        self.db = CryptoDBService()
        
        # Data containers
        self.btc_df = pd.DataFrame()
        self.ad_df = pd.DataFrame()
        self.pct_sma_df = pd.DataFrame()
        
        # Current duration
        self.current_duration = '6M'
        
        # Setup UI
        self.setup_ui()
        
        # Setup crosshair
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
        controls_frame.setFrameStyle(QFrame.Shape.StyledPanel if PYQT_VERSION == 6 else QFrame.StyledPanel)
        controls_frame.setStyleSheet("QFrame { background-color: #2d2d2d; border-radius: 5px; }")
        controls_layout = QHBoxLayout(controls_frame)
        
        # Title
        title_label = QLabel("🪙 Crypto Market Breadth Visualizer")
        title_label.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold if PYQT_VERSION == 6 else QFont.Bold))
        title_label.setStyleSheet("color: #f7931a;")  # Bitcoin orange
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
                background-color: #f7931a;
                border: 1px solid #f7931a;
                border-radius: 3px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 3px;
            }
        """
        
        self.chk_advances = QCheckBox("A/D Count")
        self.chk_advances.setChecked(True)
        self.chk_advances.setStyleSheet(checkbox_style)
        self.chk_advances.toggled.connect(self.toggle_ad_count_panel)
        controls_layout.addWidget(self.chk_advances)
        
        self.chk_ad_line = QCheckBox("A/D Line")
        self.chk_ad_line.setChecked(True)
        self.chk_ad_line.setStyleSheet(checkbox_style)
        self.chk_ad_line.toggled.connect(self.toggle_ad_line_panel)
        controls_layout.addWidget(self.chk_ad_line)
        
        self.chk_pct_above_sma = QCheckBox("% Above SMA")
        self.chk_pct_above_sma.setChecked(True)
        self.chk_pct_above_sma.setStyleSheet(checkbox_style)
        self.chk_pct_above_sma.toggled.connect(self.toggle_pct_above_sma_panel)
        controls_layout.addWidget(self.chk_pct_above_sma)
        
        self.chk_distribution = QCheckBox("Distribution")
        self.chk_distribution.setChecked(False)  # Off by default
        self.chk_distribution.setStyleSheet(checkbox_style)
        self.chk_distribution.toggled.connect(self.toggle_distribution_panel)
        controls_layout.addWidget(self.chk_distribution)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine if PYQT_VERSION == 6 else QFrame.VLine)
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
                background-color: #f7931a;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ffa64d;
            }
        """)
        controls_layout.addWidget(refresh_btn)
        
        layout.addWidget(controls_frame)
        
        # ─────────────────────────────────────────────────────────────────
        # MIDDLE: Charts (Splitter)
        # ─────────────────────────────────────────────────────────────────
        self.chart_splitter = QSplitter(Qt.Orientation.Vertical if PYQT_VERSION == 6 else Qt.Vertical)
        
        # PyQtGraph styling
        pg.setConfigOptions(antialias=True)
        
        # TOP CHART: BTC Price (as market proxy)
        self.btc_widget = pg.PlotWidget()
        self.btc_widget.setBackground('#1e1e1e')
        self.btc_widget.showGrid(x=True, y=True, alpha=0.3)
        self.btc_widget.setLabel('left', 'BTC Price ($)', color='white')
        self.btc_widget.setLabel('bottom', 'Date', color='white')
        self.btc_plot = self.btc_widget.getPlotItem()
        self.chart_splitter.addWidget(self.btc_widget)
        
        # A/D Count Chart (Advances vs Declines)
        self.ad_count_widget = pg.PlotWidget()
        self.ad_count_widget.setBackground('#1e1e1e')
        self.ad_count_widget.showGrid(x=True, y=True, alpha=0.3)
        self.ad_count_widget.setLabel('left', 'A/D Count', color='white')
        self.ad_count_widget.setXLink(self.btc_widget)
        self.ad_count_widget.addLegend(offset=(70, 10))
        self.chart_splitter.addWidget(self.ad_count_widget)
        
        # A/D Line Chart (Cumulative)
        self.ad_line_widget = pg.PlotWidget()
        self.ad_line_widget.setBackground('#1e1e1e')
        self.ad_line_widget.showGrid(x=True, y=True, alpha=0.3)
        self.ad_line_widget.setLabel('left', 'A/D Line', color='white')
        self.ad_line_widget.setXLink(self.btc_widget)
        self.chart_splitter.addWidget(self.ad_line_widget)
        
        # % Above SMA Chart
        self.pct_sma_widget = pg.PlotWidget()
        self.pct_sma_widget.setBackground('#1e1e1e')
        self.pct_sma_widget.showGrid(x=True, y=True, alpha=0.3)
        self.pct_sma_widget.setLabel('left', '% Above SMA', color='white')
        self.pct_sma_widget.setXLink(self.btc_widget)
        self.pct_sma_widget.addLegend(offset=(70, 10))
        self.chart_splitter.addWidget(self.pct_sma_widget)
        
        # Distribution Stacked Area Chart
        self.dist_widget = pg.PlotWidget()
        self.dist_widget.setBackground('#1e1e1e')
        self.dist_widget.showGrid(x=True, y=True, alpha=0.3)
        self.dist_widget.setLabel('left', 'Distribution', color='white')
        self.dist_widget.setXLink(self.btc_widget)
        self.dist_widget.addLegend(offset=(70, 10))
        self.dist_widget.setVisible(False)  # Hidden by default
        self.chart_splitter.addWidget(self.dist_widget)
        
        # Set splitter proportions (BTC gets more space)
        self.chart_splitter.setSizes([300, 150, 150, 150, 0])
        
        layout.addWidget(self.chart_splitter, stretch=1)
        
        # ─────────────────────────────────────────────────────────────────
        # BOTTOM: Summary Stats
        # ─────────────────────────────────────────────────────────────────
        stats_group = QGroupBox("📊 Market Breadth Summary")
        stats_group.setStyleSheet("""
            QGroupBox {
                color: #f7931a;
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
        stats_layout = QHBoxLayout(stats_group)
        
        # Summary cards
        self.stat_labels = {}
        stat_names = [
            ('total_coins', '🪙 Total Coins'),
            ('today_advances', '📈 Advances'),
            ('today_declines', '📉 Declines'),
            ('today_ratio', '⚖️ A/D Ratio'),
            ('avg_change', '📊 Avg Change'),
            ('pct_above_sma50', '📈 % > SMA50'),
            ('pct_above_sma200', '📈 % > SMA200'),
        ]
        
        card_style = """
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 10px;
            }
        """
        
        for key, title in stat_names:
            card = QFrame()
            card.setStyleSheet(card_style)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(2)
            
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("color: #888; font-size: 10px;")
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if PYQT_VERSION == 6 else Qt.AlignCenter)
            card_layout.addWidget(title_lbl)
            
            value_lbl = QLabel("--")
            value_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
            value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if PYQT_VERSION == 6 else Qt.AlignCenter)
            card_layout.addWidget(value_lbl)
            
            self.stat_labels[key] = value_lbl
            stats_layout.addWidget(card)
        
        layout.addWidget(stats_group)
        
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
        crosshair_pen = pg.mkPen('#ffff00', width=1, style=Qt.PenStyle.DashLine if PYQT_VERSION == 6 else Qt.DashLine)
        
        # Crosshairs for BTC chart
        self.vLine_btc = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_btc = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.btc_widget.addItem(self.vLine_btc, ignoreBounds=True)
        self.btc_widget.addItem(self.hLine_btc, ignoreBounds=True)
        
        # Crosshairs for A/D Count chart
        self.vLine_count = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_count = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.ad_count_widget.addItem(self.vLine_count, ignoreBounds=True)
        self.ad_count_widget.addItem(self.hLine_count, ignoreBounds=True)
        
        # Crosshairs for A/D Line chart
        self.vLine_line = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_line = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.ad_line_widget.addItem(self.vLine_line, ignoreBounds=True)
        self.ad_line_widget.addItem(self.hLine_line, ignoreBounds=True)
        
        # Crosshairs for % Above SMA chart
        self.vLine_sma = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_sma = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.pct_sma_widget.addItem(self.vLine_sma, ignoreBounds=True)
        self.pct_sma_widget.addItem(self.hLine_sma, ignoreBounds=True)
        
        # Crosshairs for Distribution chart
        self.vLine_dist = pg.InfiniteLine(angle=90, movable=False, pen=crosshair_pen)
        self.hLine_dist = pg.InfiniteLine(angle=0, movable=False, pen=crosshair_pen)
        self.dist_widget.addItem(self.vLine_dist, ignoreBounds=True)
        self.dist_widget.addItem(self.hLine_dist, ignoreBounds=True)
        
        # Connect mouse move for all charts
        self.btc_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'btc'))
        self.ad_count_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'count'))
        self.ad_line_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'line'))
        self.pct_sma_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'sma'))
        self.dist_widget.scene().sigMouseMoved.connect(lambda pos: self.mouse_moved(pos, 'dist'))
    
    def mouse_moved(self, pos, source='btc'):
        """Handle mouse movement for synchronized crosshairs."""
        widget_map = {
            'btc': self.btc_widget,
            'count': self.ad_count_widget,
            'line': self.ad_line_widget,
            'sma': self.pct_sma_widget,
            'dist': self.dist_widget
        }
        
        source_widget = widget_map.get(source, self.btc_widget)
        
        if source_widget.sceneBoundingRect().contains(pos):
            mouse_point = source_widget.getPlotItem().vb.mapSceneToView(pos)
            x_pos = mouse_point.x()
            
            # Update all vertical crosshairs
            self.vLine_btc.setPos(x_pos)
            self.vLine_count.setPos(x_pos)
            self.vLine_line.setPos(x_pos)
            self.vLine_sma.setPos(x_pos)
            self.vLine_dist.setPos(x_pos)
            
            # Update horizontal crosshair only for source chart
            if source == 'btc':
                self.hLine_btc.setPos(mouse_point.y())
            elif source == 'count':
                self.hLine_count.setPos(mouse_point.y())
            elif source == 'line':
                self.hLine_line.setPos(mouse_point.y())
            elif source == 'sma':
                self.hLine_sma.setPos(mouse_point.y())
            elif source == 'dist':
                self.hLine_dist.setPos(mouse_point.y())
            
            # Update status bar
            x_idx = int(round(x_pos))
            if 0 <= x_idx < len(self.btc_df):
                row = self.btc_df.iloc[x_idx]
                date_str = row['trade_date'].strftime('%Y-%m-%d') if hasattr(row['trade_date'], 'strftime') else str(row['trade_date'])
                status = f"Date: {date_str} | BTC: ${row['close_price']:,.0f}"
                
                if x_idx < len(self.ad_df):
                    ad_row = self.ad_df.iloc[x_idx]
                    status += f" | Adv: {ad_row['advances']:.0f} Dec: {ad_row['declines']:.0f} Ratio: {ad_row['ad_ratio']:.2f}"
                
                # Add % above SMA info if available
                if x_idx < len(self.pct_sma_df):
                    sma_row = self.pct_sma_df.iloc[x_idx]
                    status += f" | >SMA50: {sma_row['pct_above_sma50']:.1f}% >SMA200: {sma_row['pct_above_sma200']:.1f}%"
                
                self.status_bar.showMessage(status)
    
    def on_duration_changed(self, duration):
        """Handle duration change."""
        self.current_duration = duration
        self.load_data()
    
    def toggle_ad_count_panel(self, checked):
        """Show/hide A/D Count panel."""
        self.ad_count_widget.setVisible(checked)
        self.update_charts()
    
    def toggle_ad_line_panel(self, checked):
        """Show/hide A/D Line panel."""
        self.ad_line_widget.setVisible(checked)
        self.update_charts()
    
    def toggle_pct_above_sma_panel(self, checked):
        """Show/hide % Above SMA panel."""
        self.pct_sma_widget.setVisible(checked)
        self.update_charts()
    
    def toggle_distribution_panel(self, checked):
        """Show/hide Distribution panel."""
        self.dist_widget.setVisible(checked)
        self.update_charts()
    
    def load_data(self):
        """Load data based on selected duration."""
        self.status_bar.showMessage("Loading crypto data...")
        
        # Calculate date range
        end_date = datetime.now().date()
        days = self.DURATION_MAP.get(self.current_duration)
        
        if days:
            start_date = end_date - timedelta(days=days)
        else:
            start_date = None
        
        try:
            # Load BTC data (as market proxy)
            self.btc_df = self.db.get_daily_quotes('BTC', start_date, end_date)
            
            # Load A/D data
            self.ad_df = self.db.get_advance_decline(start_date, end_date)
            
            # Load % Above SMA data
            self.pct_sma_df = self.db.get_pct_above_sma(start_date, end_date)
            
            # Update charts
            self.update_charts()
            
            # Update summary stats
            self.update_stats()
            
            btc_count = len(self.btc_df)
            ad_count = len(self.ad_df)
            self.status_bar.showMessage(f"Loaded {btc_count} BTC records, {ad_count} A/D records")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
    
    def update_charts(self):
        """Update all charts with loaded data."""
        # Clear existing plots
        self.btc_widget.clear()
        self.ad_count_widget.clear()
        self.ad_line_widget.clear()
        self.pct_sma_widget.clear()
        self.dist_widget.clear()
        
        # Re-add crosshairs
        self.btc_widget.addItem(self.vLine_btc, ignoreBounds=True)
        self.btc_widget.addItem(self.hLine_btc, ignoreBounds=True)
        self.ad_count_widget.addItem(self.vLine_count, ignoreBounds=True)
        self.ad_count_widget.addItem(self.hLine_count, ignoreBounds=True)
        self.ad_line_widget.addItem(self.vLine_line, ignoreBounds=True)
        self.ad_line_widget.addItem(self.hLine_line, ignoreBounds=True)
        self.pct_sma_widget.addItem(self.vLine_sma, ignoreBounds=True)
        self.pct_sma_widget.addItem(self.hLine_sma, ignoreBounds=True)
        self.dist_widget.addItem(self.vLine_dist, ignoreBounds=True)
        self.dist_widget.addItem(self.hLine_dist, ignoreBounds=True)
        
        if self.btc_df.empty:
            self.status_bar.showMessage("No BTC data available. Run Crypto Data Wizard first.")
            return
        
        # Reset index for plotting
        self.btc_df = self.btc_df.reset_index(drop=True)
        if not self.ad_df.empty:
            self.ad_df = self.ad_df.reset_index(drop=True)
        if not self.pct_sma_df.empty:
            self.pct_sma_df = self.pct_sma_df.reset_index(drop=True)
        
        x = np.arange(len(self.btc_df))
        
        # ─────────────────────────────────────────────────────────────────
        # BTC Chart (Candlestick)
        # ─────────────────────────────────────────────────────────────────
        candlestick = CandlestickItem(self.btc_df)
        self.btc_widget.addItem(candlestick)
        
        # Also plot SMA if available
        if 'sma_50' in self.btc_df.columns:
            sma50 = self.btc_df['sma_50'].values
            self.btc_widget.plot(x, sma50, pen=pg.mkPen('#ffaa00', width=1), name='SMA50')
        
        if self.ad_df.empty:
            self.status_bar.showMessage("No A/D data available. Run Crypto Data Wizard to calculate breadth.")
            return
        
        x_ad = np.arange(len(self.ad_df))
        
        # ─────────────────────────────────────────────────────────────────
        # A/D Count Chart (Advances vs Declines) - always show both when visible
        # ─────────────────────────────────────────────────────────────────
        if self.ad_count_widget.isVisible():
            self.ad_count_widget.addLegend(offset=(70, 10))
            
            advances = self.ad_df['advances'].values
            # Line with scatter points for advances
            self.ad_count_widget.plot(x_ad, advances, pen=pg.mkPen('#00ff88', width=2), 
                                      symbol='o', symbolSize=6, symbolBrush='#00ff88', 
                                      symbolPen=pg.mkPen('#00ff88'), name='Advances')
            
            declines = self.ad_df['declines'].values
            # Line with scatter points for declines
            self.ad_count_widget.plot(x_ad, declines, pen=pg.mkPen('#ff4444', width=2),
                                      symbol='o', symbolSize=6, symbolBrush='#ff4444',
                                      symbolPen=pg.mkPen('#ff4444'), name='Declines')
            
            # Add midpoint line
            self.ad_count_widget.addLine(y=50, pen=pg.mkPen('#555', width=1, style=Qt.PenStyle.DashLine if PYQT_VERSION == 6 else Qt.DashLine))
        
        # ─────────────────────────────────────────────────────────────────
        # A/D Line Chart (Cumulative)
        # ─────────────────────────────────────────────────────────────────
        if self.ad_line_widget.isVisible() and 'ad_line' in self.ad_df.columns:
            ad_line = self.ad_df['ad_line'].values
            
            # Create fill between line and zero
            fill = pg.FillBetweenItem(
                pg.PlotDataItem(x_ad, ad_line),
                pg.PlotDataItem(x_ad, np.zeros(len(x_ad))),
                brush=pg.mkBrush('#00ff8840')
            )
            self.ad_line_widget.addItem(fill)
            
            # Plot A/D line
            self.ad_line_widget.plot(x_ad, ad_line, pen=pg.mkPen('#00ff88', width=2))
            
            # Add zero line
            self.ad_line_widget.addLine(y=0, pen=pg.mkPen('#888', width=1))
        
        # ─────────────────────────────────────────────────────────────────
        # % Above SMA Chart
        # ─────────────────────────────────────────────────────────────────
        if self.pct_sma_widget.isVisible() and not self.pct_sma_df.empty:
            self.pct_sma_widget.addLegend(offset=(70, 10))
            x_sma = np.arange(len(self.pct_sma_df))
            
            # % Above SMA50
            pct50 = self.pct_sma_df['pct_above_sma50'].values
            self.pct_sma_widget.plot(x_sma, pct50, pen=pg.mkPen('#00aaff', width=2),
                                     symbol='o', symbolSize=5, symbolBrush='#00aaff',
                                     symbolPen=pg.mkPen('#00aaff'), name='% > SMA50')
            
            # % Above SMA200
            pct200 = self.pct_sma_df['pct_above_sma200'].values
            self.pct_sma_widget.plot(x_sma, pct200, pen=pg.mkPen('#ffaa00', width=2),
                                     symbol='o', symbolSize=5, symbolBrush='#ffaa00',
                                     symbolPen=pg.mkPen('#ffaa00'), name='% > SMA200')
            
            # Reference lines
            self.pct_sma_widget.addLine(y=50, pen=pg.mkPen('#888', width=1, style=Qt.PenStyle.DashLine if PYQT_VERSION == 6 else Qt.DashLine))
            self.pct_sma_widget.addLine(y=80, pen=pg.mkPen('#00ff88', width=1, style=Qt.PenStyle.DotLine if PYQT_VERSION == 6 else Qt.DotLine))
            self.pct_sma_widget.addLine(y=20, pen=pg.mkPen('#ff4444', width=1, style=Qt.PenStyle.DotLine if PYQT_VERSION == 6 else Qt.DotLine))
            
            # Set Y range 0-100
            self.pct_sma_widget.setYRange(0, 100)
        
        # ─────────────────────────────────────────────────────────────────
        # Distribution Chart (Gain/Loss buckets)
        # ─────────────────────────────────────────────────────────────────
        if self.dist_widget.isVisible():
            self.dist_widget.addLegend(offset=(70, 10))
            
            # Check if distribution columns exist
            dist_cols = ['gain_0_1', 'gain_1_2', 'gain_2_3', 'gain_3_5', 'gain_5_10', 'gain_10_plus',
                        'loss_0_1', 'loss_1_2', 'loss_2_3', 'loss_3_5', 'loss_5_10', 'loss_10_plus']
            
            if all(col in self.ad_df.columns for col in dist_cols):
                # Sum gains and losses for simplified view
                gains = (self.ad_df['gain_0_1'] + self.ad_df['gain_1_2'] + self.ad_df['gain_2_3'] + 
                        self.ad_df['gain_3_5'] + self.ad_df['gain_5_10'] + self.ad_df['gain_10_plus']).values
                losses = (self.ad_df['loss_0_1'] + self.ad_df['loss_1_2'] + self.ad_df['loss_2_3'] + 
                         self.ad_df['loss_3_5'] + self.ad_df['loss_5_10'] + self.ad_df['loss_10_plus']).values
                
                # Big movers (>5%)
                big_gains = (self.ad_df['gain_5_10'] + self.ad_df['gain_10_plus']).values
                big_losses = (self.ad_df['loss_5_10'] + self.ad_df['loss_10_plus']).values
                
                # Plot stacked areas
                self.dist_widget.plot(x_ad, gains, pen=pg.mkPen('#00ff88', width=1.5), 
                                      fillLevel=0, brush=pg.mkBrush('#00ff8840'), name='Gainers')
                self.dist_widget.plot(x_ad, -losses, pen=pg.mkPen('#ff4444', width=1.5), 
                                      fillLevel=0, brush=pg.mkBrush('#ff444440'), name='Losers')
                
                # Highlight big movers
                self.dist_widget.plot(x_ad, big_gains, pen=pg.mkPen('#00ff00', width=2), name='>5% Up')
                self.dist_widget.plot(x_ad, -big_losses, pen=pg.mkPen('#ff0000', width=2), name='>5% Down')
                
                # Zero line
                self.dist_widget.addLine(y=0, pen=pg.mkPen('#888', width=1))
    
    def update_stats(self):
        """Update summary statistics."""
        if self.ad_df.empty:
            for key in self.stat_labels:
                self.stat_labels[key].setText("--")
            return
        
        # Get latest row
        latest = self.ad_df.iloc[-1]
        
        # Update stat cards
        self.stat_labels['total_coins'].setText(f"{latest.get('total_coins', 0):.0f}")
        
        advances = latest.get('advances', 0)
        declines = latest.get('declines', 0)
        
        self.stat_labels['today_advances'].setText(f"{advances:.0f}")
        self.stat_labels['today_advances'].setStyleSheet("color: #00ff88; font-size: 16px; font-weight: bold;")
        
        self.stat_labels['today_declines'].setText(f"{declines:.0f}")
        self.stat_labels['today_declines'].setStyleSheet("color: #ff4444; font-size: 16px; font-weight: bold;")
        
        ratio = latest.get('ad_ratio', 0)
        ratio_color = '#00ff88' if ratio > 1 else '#ff4444' if ratio < 1 else 'white'
        self.stat_labels['today_ratio'].setText(f"{ratio:.2f}")
        self.stat_labels['today_ratio'].setStyleSheet(f"color: {ratio_color}; font-size: 16px; font-weight: bold;")
        
        avg_change = latest.get('avg_change', 0)
        change_color = '#00ff88' if avg_change > 0 else '#ff4444' if avg_change < 0 else 'white'
        self.stat_labels['avg_change'].setText(f"{avg_change:+.2f}%")
        self.stat_labels['avg_change'].setStyleSheet(f"color: {change_color}; font-size: 16px; font-weight: bold;")
        
        # % Above SMA stats
        if not self.pct_sma_df.empty:
            sma_latest = self.pct_sma_df.iloc[-1]
            
            pct50 = sma_latest.get('pct_above_sma50', 0)
            pct50_color = '#00ff88' if pct50 > 50 else '#ff4444' if pct50 < 50 else 'white'
            self.stat_labels['pct_above_sma50'].setText(f"{pct50:.1f}%")
            self.stat_labels['pct_above_sma50'].setStyleSheet(f"color: {pct50_color}; font-size: 16px; font-weight: bold;")
            
            pct200 = sma_latest.get('pct_above_sma200', 0)
            pct200_color = '#00ff88' if pct200 > 50 else '#ff4444' if pct200 < 50 else 'white'
            self.stat_labels['pct_above_sma200'].setText(f"{pct200:.1f}%")
            self.stat_labels['pct_above_sma200'].setStyleSheet(f"color: {pct200_color}; font-size: 16px; font-weight: bold;")
    
    def closeEvent(self, event):
        """Cleanup on close."""
        self.db.dispose()
        event.accept()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Launch the Crypto Breadth Visualizer."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark palette
    if PYQT_VERSION == 6:
        from PyQt6.QtGui import QPalette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        app.setPalette(palette)
    else:
        from PyQt5.QtGui import QPalette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        app.setPalette(palette)
    
    window = CryptoBreadthVisualizer()
    window.show()
    
    sys.exit(app.exec() if PYQT_VERSION == 6 else app.exec_())


if __name__ == '__main__':
    main()
