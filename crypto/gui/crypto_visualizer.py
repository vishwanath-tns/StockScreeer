#!/usr/bin/env python3
"""
Crypto Visualizer
=================

PyQtGraph-based cryptocurrency chart with price, SMAs, and RSI.

Features:
- Candlestick price chart
- Moving Averages overlay (SMA 20, 50, 200)
- RSI indicator panel
- Symbol selector for Top 100 cryptos
- Duration picker (1M, 3M, 6M, 1Y, 2Y, 5Y, All)
- Synchronized crosshair

Usage:
    python -m crypto.gui.crypto_visualizer
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import logging

import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QGroupBox, QSplitter,
    QStatusBar, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

import pyqtgraph as pg
from pyqtgraph import DateAxisItem

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crypto.services.crypto_db_service import CryptoDBService
from crypto.data.crypto_symbols import TOP_100_CRYPTOS, SYMBOL_TO_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick chart item."""
    
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # DataFrame with open, high, low, close, x (index)
        self.generatePicture()
    
    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.picture)
        
        if self.data is None or len(self.data) == 0:
            p.end()
            return
        
        # Calculate candle width based on data
        w = 0.6
        
        for i, row in self.data.iterrows():
            x = row['x']
            o, h, l, c = row['open_price'], row['high_price'], row['low_price'], row['close_price']
            
            if pd.isna(o) or pd.isna(c):
                continue
            
            # Green for up, red for down
            if c >= o:
                p.setPen(pg.mkPen('#00ff88', width=1))
                p.setBrush(pg.mkBrush('#00ff88'))
            else:
                p.setPen(pg.mkPen('#ff4444', width=1))
                p.setBrush(pg.mkBrush('#ff4444'))
            
            # Draw wick (high-low line)
            p.drawLine(pg.QtCore.QPointF(x, l), pg.QtCore.QPointF(x, h))
            
            # Draw body
            p.drawRect(pg.QtCore.QRectF(x - w/2, min(o, c), w, abs(c - o) if abs(c - o) > 0 else 0.01))
        
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())


class CryptoVisualizer(QMainWindow):
    """Main crypto visualization window."""
    
    def __init__(self):
        super().__init__()
        
        self.db = CryptoDBService()
        self.current_symbol = "BTC"
        self.current_duration = "1Y"
        
        # Data storage
        self.price_data: Optional[pd.DataFrame] = None
        self.ma_data: Optional[pd.DataFrame] = None
        self.rsi_data: Optional[pd.DataFrame] = None
        
        # Chart items
        self.candlestick_item = None
        self.sma_lines = {}
        self.rsi_line = None
        self.crosshair_price = None
        self.crosshair_rsi = None
        
        self.setup_ui()
        self.setWindowTitle("🪙 Crypto Visualizer")
        self.setMinimumSize(1200, 800)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: white; }
            QLabel { color: white; }
            QComboBox { 
                background-color: #2a2a2a; 
                color: white; 
                border: 1px solid #444; 
                padding: 5px;
                min-width: 120px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #3d7a37;
            }
            QCheckBox { color: white; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:checked { background-color: #00ff88; border: 1px solid #00ff88; }
            QCheckBox::indicator:unchecked { background-color: #2a2a2a; border: 1px solid #444; }
            QPushButton {
                background-color: #2d5a27;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3d7a37; }
            QPushButton:checked { background-color: #00ff88; color: black; }
            QGroupBox {
                color: #00ff88;
                border: 1px solid #444;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { color: #00ff88; }
            QStatusBar { background-color: #1a1a1a; color: #888; }
        """)
        
        # Load initial data
        QTimer.singleShot(100, self.load_data)
    
    def setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ========== Controls Bar ==========
        controls = QHBoxLayout()
        
        # Symbol selector
        controls.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        for sym, yahoo, name, cat, rank in TOP_100_CRYPTOS:
            self.symbol_combo.addItem(f"{sym} - {name}", sym)
        self.symbol_combo.currentIndexChanged.connect(self.on_symbol_changed)
        controls.addWidget(self.symbol_combo)
        
        controls.addSpacing(20)
        
        # Duration buttons
        controls.addWidget(QLabel("Duration:"))
        self.duration_buttons = {}
        for dur in ["1M", "3M", "6M", "1Y", "2Y", "5Y", "All"]:
            btn = QPushButton(dur)
            btn.setCheckable(True)
            btn.setChecked(dur == "1Y")
            btn.clicked.connect(lambda checked, d=dur: self.on_duration_changed(d))
            btn.setStyleSheet("""
                QPushButton { min-width: 40px; padding: 5px 10px; }
                QPushButton:checked { background-color: #00ff88; color: black; }
            """)
            self.duration_buttons[dur] = btn
            controls.addWidget(btn)
        
        controls.addSpacing(20)
        
        # SMA toggles
        controls.addWidget(QLabel("SMAs:"))
        self.sma_checks = {}
        sma_colors = {"SMA20": "#ffff00", "SMA50": "#00aaff", "SMA200": "#ff00ff"}
        for sma, color in sma_colors.items():
            cb = QCheckBox(sma)
            cb.setChecked(True)
            cb.setStyleSheet(f"QCheckBox {{ color: {color}; }}")
            cb.stateChanged.connect(self.update_sma_visibility)
            self.sma_checks[sma] = cb
            controls.addWidget(cb)
        
        controls.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        controls.addWidget(refresh_btn)
        
        layout.addLayout(controls)
        
        # ========== Charts ==========
        chart_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Price chart (70%)
        self.price_chart = pg.PlotWidget()
        self.price_chart.setBackground('#1a1a1a')
        self.price_chart.showGrid(x=True, y=True, alpha=0.3)
        self.price_chart.setLabel('left', 'Price (USD)', color='white')
        self.price_chart.setLabel('bottom', 'Date', color='white')
        self.price_chart.setMinimumHeight(400)
        
        # Add legend
        self.price_legend = self.price_chart.addLegend(offset=(10, 10))
        
        chart_splitter.addWidget(self.price_chart)
        
        # RSI chart (30%)
        self.rsi_chart = pg.PlotWidget()
        self.rsi_chart.setBackground('#1a1a1a')
        self.rsi_chart.showGrid(x=True, y=True, alpha=0.3)
        self.rsi_chart.setLabel('left', 'RSI', color='white')
        self.rsi_chart.setLabel('bottom', 'Date', color='white')
        self.rsi_chart.setYRange(0, 100)
        self.rsi_chart.setMinimumHeight(150)
        self.rsi_chart.setMaximumHeight(200)
        
        # RSI reference lines
        self.rsi_chart.addItem(pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('#ff4444', width=1, style=Qt.PenStyle.DashLine)))
        self.rsi_chart.addItem(pg.InfiniteLine(pos=30, angle=0, pen=pg.mkPen('#00ff88', width=1, style=Qt.PenStyle.DashLine)))
        self.rsi_chart.addItem(pg.InfiniteLine(pos=50, angle=0, pen=pg.mkPen('#888888', width=1, style=Qt.PenStyle.DotLine)))
        
        # RSI zone fills
        overbought_region = pg.LinearRegionItem([70, 100], orientation='horizontal', 
                                                 brush=pg.mkBrush(255, 68, 68, 30), movable=False)
        oversold_region = pg.LinearRegionItem([0, 30], orientation='horizontal',
                                               brush=pg.mkBrush(0, 255, 136, 30), movable=False)
        self.rsi_chart.addItem(overbought_region)
        self.rsi_chart.addItem(oversold_region)
        
        chart_splitter.addWidget(self.rsi_chart)
        
        # Set splitter sizes (70/30)
        chart_splitter.setSizes([700, 300])
        
        layout.addWidget(chart_splitter)
        
        # Link X axes
        self.rsi_chart.setXLink(self.price_chart)
        
        # ========== Crosshairs ==========
        self.setup_crosshairs()
        
        # ========== Info Bar ==========
        info_layout = QHBoxLayout()
        
        self.price_label = QLabel("Price: --")
        self.price_label.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(self.price_label)
        
        self.change_label = QLabel("Change: --")
        info_layout.addWidget(self.change_label)
        
        self.rsi_label = QLabel("RSI: --")
        info_layout.addWidget(self.rsi_label)
        
        self.sma_label = QLabel("SMA50: -- | SMA200: --")
        info_layout.addWidget(self.sma_label)
        
        info_layout.addStretch()
        
        self.date_label = QLabel("Date: --")
        self.date_label.setStyleSheet("color: #888;")
        info_layout.addWidget(self.date_label)
        
        layout.addLayout(info_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
    
    def setup_crosshairs(self):
        """Setup synchronized crosshairs."""
        # Price chart crosshair
        self.vline_price = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#888888', width=1))
        self.hline_price = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#888888', width=1))
        self.price_chart.addItem(self.vline_price, ignoreBounds=True)
        self.price_chart.addItem(self.hline_price, ignoreBounds=True)
        
        # RSI chart crosshair
        self.vline_rsi = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#888888', width=1))
        self.hline_rsi = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#888888', width=1))
        self.rsi_chart.addItem(self.vline_rsi, ignoreBounds=True)
        self.rsi_chart.addItem(self.hline_rsi, ignoreBounds=True)
        
        # Connect mouse move
        self.price_chart.scene().sigMouseMoved.connect(self.on_mouse_moved_price)
        self.rsi_chart.scene().sigMouseMoved.connect(self.on_mouse_moved_rsi)
    
    def on_mouse_moved_price(self, pos):
        """Handle mouse movement on price chart."""
        if self.price_chart.sceneBoundingRect().contains(pos):
            mouse_point = self.price_chart.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            self.vline_price.setPos(x)
            self.hline_price.setPos(y)
            self.vline_rsi.setPos(x)
            
            self.update_info_from_x(x)
    
    def on_mouse_moved_rsi(self, pos):
        """Handle mouse movement on RSI chart."""
        if self.rsi_chart.sceneBoundingRect().contains(pos):
            mouse_point = self.rsi_chart.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            self.vline_rsi.setPos(x)
            self.hline_rsi.setPos(y)
            self.vline_price.setPos(x)
            
            self.update_info_from_x(x)
    
    def update_info_from_x(self, x: float):
        """Update info labels based on x position."""
        if self.price_data is None or len(self.price_data) == 0:
            return
        
        # Find nearest data point
        idx = int(round(x))
        if idx < 0 or idx >= len(self.price_data):
            return
        
        row = self.price_data.iloc[idx]
        
        # Update labels
        price = row['close_price']
        self.price_label.setText(f"Price: ${price:,.2f}" if price < 1000 else f"Price: ${price:,.0f}")
        
        pct = row.get('pct_change', 0)
        if not pd.isna(pct):
            color = "#00ff88" if pct >= 0 else "#ff4444"
            self.change_label.setText(f"<span style='color:{color}'>Change: {pct:+.2f}%</span>")
            self.change_label.setTextFormat(Qt.TextFormat.RichText)
        
        trade_date = row['trade_date']
        if isinstance(trade_date, str):
            self.date_label.setText(f"Date: {trade_date}")
        else:
            self.date_label.setText(f"Date: {trade_date.strftime('%Y-%m-%d')}")
        
        # RSI
        if self.rsi_data is not None and idx < len(self.rsi_data):
            rsi_row = self.rsi_data.iloc[idx]
            rsi = rsi_row.get('rsi_14', None)
            if rsi and not pd.isna(rsi):
                if rsi > 70:
                    rsi_color = "#ff4444"
                elif rsi < 30:
                    rsi_color = "#00ff88"
                else:
                    rsi_color = "white"
                self.rsi_label.setText(f"<span style='color:{rsi_color}'>RSI: {rsi:.1f}</span>")
                self.rsi_label.setTextFormat(Qt.TextFormat.RichText)
        
        # SMAs
        if self.ma_data is not None and idx < len(self.ma_data):
            ma_row = self.ma_data.iloc[idx]
            sma50 = ma_row.get('sma_50', None)
            sma200 = ma_row.get('sma_200', None)
            
            sma_text = []
            if sma50 and not pd.isna(sma50):
                sma_text.append(f"SMA50: ${sma50:,.0f}" if sma50 > 100 else f"SMA50: ${sma50:.2f}")
            if sma200 and not pd.isna(sma200):
                sma_text.append(f"SMA200: ${sma200:,.0f}" if sma200 > 100 else f"SMA200: ${sma200:.2f}")
            
            if sma_text:
                self.sma_label.setText(" | ".join(sma_text))
    
    def on_symbol_changed(self, index):
        """Handle symbol selection change."""
        self.current_symbol = self.symbol_combo.currentData()
        self.load_data()
    
    def on_duration_changed(self, duration: str):
        """Handle duration button click."""
        # Update button states
        for dur, btn in self.duration_buttons.items():
            btn.setChecked(dur == duration)
        
        self.current_duration = duration
        self.load_data()
    
    def update_sma_visibility(self):
        """Update SMA line visibility based on checkboxes."""
        for sma_name, cb in self.sma_checks.items():
            if sma_name in self.sma_lines:
                self.sma_lines[sma_name].setVisible(cb.isChecked())
    
    def get_date_range(self) -> tuple:
        """Get start and end dates based on selected duration."""
        end_date = date.today()
        
        if self.current_duration == "1M":
            start_date = end_date - timedelta(days=30)
        elif self.current_duration == "3M":
            start_date = end_date - timedelta(days=90)
        elif self.current_duration == "6M":
            start_date = end_date - timedelta(days=180)
        elif self.current_duration == "1Y":
            start_date = end_date - timedelta(days=365)
        elif self.current_duration == "2Y":
            start_date = end_date - timedelta(days=730)
        elif self.current_duration == "5Y":
            start_date = end_date - timedelta(days=1825)
        else:  # All
            start_date = None
        
        return start_date, end_date
    
    def load_data(self):
        """Load data for current symbol and duration."""
        self.status_bar.showMessage(f"Loading {self.current_symbol}...")
        
        try:
            start_date, end_date = self.get_date_range()
            
            # Load price data
            self.price_data = self.db.get_daily_quotes(self.current_symbol, start_date, end_date)
            
            if self.price_data.empty:
                self.status_bar.showMessage(f"No data for {self.current_symbol}")
                return
            
            # Add x index
            self.price_data = self.price_data.sort_values('trade_date').reset_index(drop=True)
            self.price_data['x'] = self.price_data.index
            
            # Load MA data
            with self.db.engine.connect() as conn:
                from sqlalchemy import text
                sql = """
                    SELECT * FROM crypto_daily_ma 
                    WHERE symbol = :symbol
                """
                params = {"symbol": self.current_symbol}
                
                if start_date:
                    sql += " AND trade_date >= :start_date"
                    params["start_date"] = start_date
                
                sql += " ORDER BY trade_date"
                self.ma_data = pd.read_sql(text(sql), conn, params=params)
            
            # Load RSI data
            with self.db.engine.connect() as conn:
                sql = """
                    SELECT * FROM crypto_daily_rsi 
                    WHERE symbol = :symbol
                """
                params = {"symbol": self.current_symbol}
                
                if start_date:
                    sql += " AND trade_date >= :start_date"
                    params["start_date"] = start_date
                
                sql += " ORDER BY trade_date"
                self.rsi_data = pd.read_sql(text(sql), conn, params=params)
            
            # Update charts
            self.update_charts()
            
            # Update window title
            name = SYMBOL_TO_NAME.get(self.current_symbol, self.current_symbol)
            self.setWindowTitle(f"🪙 {self.current_symbol} - {name} | Crypto Visualizer")
            
            self.status_bar.showMessage(f"Loaded {len(self.price_data)} days for {self.current_symbol}")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.status_bar.showMessage(f"Error: {e}")
    
    def update_charts(self):
        """Update all chart displays."""
        # Clear existing items
        self.price_chart.clear()
        self.rsi_chart.clear()
        
        # Re-add crosshairs
        self.price_chart.addItem(self.vline_price, ignoreBounds=True)
        self.price_chart.addItem(self.hline_price, ignoreBounds=True)
        self.rsi_chart.addItem(self.vline_rsi, ignoreBounds=True)
        self.rsi_chart.addItem(self.hline_rsi, ignoreBounds=True)
        
        # Re-add RSI reference lines
        self.rsi_chart.addItem(pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('#ff4444', width=1, style=Qt.PenStyle.DashLine)))
        self.rsi_chart.addItem(pg.InfiniteLine(pos=30, angle=0, pen=pg.mkPen('#00ff88', width=1, style=Qt.PenStyle.DashLine)))
        self.rsi_chart.addItem(pg.InfiniteLine(pos=50, angle=0, pen=pg.mkPen('#888888', width=1, style=Qt.PenStyle.DotLine)))
        
        # RSI zone fills
        overbought_region = pg.LinearRegionItem([70, 100], orientation='horizontal', 
                                                 brush=pg.mkBrush(255, 68, 68, 30), movable=False)
        oversold_region = pg.LinearRegionItem([0, 30], orientation='horizontal',
                                               brush=pg.mkBrush(0, 255, 136, 30), movable=False)
        self.rsi_chart.addItem(overbought_region)
        self.rsi_chart.addItem(oversold_region)
        
        if self.price_data is None or len(self.price_data) == 0:
            return
        
        # ========== Price Chart ==========
        # Candlesticks
        self.candlestick_item = CandlestickItem(self.price_data)
        self.price_chart.addItem(self.candlestick_item)
        
        # SMAs from MA data
        x = self.price_data['x'].values
        
        if self.ma_data is not None and len(self.ma_data) > 0:
            # Align MA data with price data
            ma_merged = self.price_data[['trade_date', 'x']].merge(
                self.ma_data[['trade_date', 'sma_20', 'sma_50', 'sma_200']], 
                on='trade_date', 
                how='left'
            )
            
            sma_configs = [
                ("SMA20", "sma_20", "#ffff00"),
                ("SMA50", "sma_50", "#00aaff"),
                ("SMA200", "sma_200", "#ff00ff"),
            ]
            
            for name, col, color in sma_configs:
                if col in ma_merged.columns:
                    values = ma_merged[col].values
                    mask = ~np.isnan(values)
                    if mask.any():
                        line = self.price_chart.plot(
                            x[mask], values[mask],
                            pen=pg.mkPen(color, width=1.5),
                            name=name
                        )
                        self.sma_lines[name] = line
                        line.setVisible(self.sma_checks.get(name, QCheckBox()).isChecked())
        
        # ========== RSI Chart ==========
        if self.rsi_data is not None and len(self.rsi_data) > 0:
            # Align RSI data with price data
            rsi_merged = self.price_data[['trade_date', 'x']].merge(
                self.rsi_data[['trade_date', 'rsi_14']], 
                on='trade_date', 
                how='left'
            )
            
            rsi_values = rsi_merged['rsi_14'].values
            mask = ~np.isnan(rsi_values)
            
            if mask.any():
                self.rsi_chart.plot(
                    x[mask], rsi_values[mask],
                    pen=pg.mkPen('#ffaa00', width=2),
                    name="RSI(14)"
                )
        
        # Set Y range for RSI
        self.rsi_chart.setYRange(0, 100)
        
        # Auto-range price chart
        self.price_chart.autoRange()
        
        # Update info with latest values
        if len(self.price_data) > 0:
            self.update_info_from_x(len(self.price_data) - 1)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application-wide dark palette
    from PyQt6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 90, 39))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = CryptoVisualizer()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
