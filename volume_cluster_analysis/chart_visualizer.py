#!/usr/bin/env python3
"""
Volume Events Chart Visualizer
==============================
Simple candlestick chart with volume events overlay.
Uses PyQtGraph for rendering.
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QComboBox, QGroupBox, QSplitter, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import pyqtgraph as pg

from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

# Configure PyQtGraph
pg.setConfigOptions(antialias=True, background='w', foreground='k')


class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick chart item."""
    
    def __init__(self, data):
        """
        data: DataFrame with columns: x (index), open, high, low, close
        """
        super().__init__()
        self.data = data
        self.picture = None
        self.generatePicture()
        
    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.picture)
        
        if self.data is None or len(self.data) == 0:
            p.end()
            return
        
        w = 0.4  # Candle width
        
        for i, row in self.data.iterrows():
            x = row['x']
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            
            if c >= o:
                p.setPen(pg.mkPen('#26a69a', width=1))
                p.setBrush(pg.mkBrush('#26a69a'))
            else:
                p.setPen(pg.mkPen('#ef5350', width=1))
                p.setBrush(pg.mkBrush('#ef5350'))
            
            # Draw wick (high-low line)
            p.drawLine(pg.QtCore.QPointF(x, l), pg.QtCore.QPointF(x, h))
            
            # Draw body
            if abs(c - o) < 0.01:
                # Doji - draw horizontal line
                p.drawLine(pg.QtCore.QPointF(x - w, o), pg.QtCore.QPointF(x + w, o))
            else:
                p.drawRect(pg.QtCore.QRectF(x - w, min(o, c), w * 2, abs(c - o)))
        
        p.end()
    
    def paint(self, p, *args):
        if self.picture:
            p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        if self.picture:
            return pg.QtCore.QRectF(self.picture.boundingRect())
        return pg.QtCore.QRectF()


class SimpleChartWidget(QWidget):
    """Simple candlestick chart widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.symbol = None
        self.df = None
        self.events_df = None
        
        # Database connection
        self.engine = self._create_engine()
        
        # Setup UI
        self._setup_ui()
        
    def _create_engine(self):
        """Create database engine."""
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        db = os.getenv('MYSQL_DB', 'marketdata')
        user = os.getenv('MYSQL_USER', 'root')
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"
        return create_engine(conn_str, pool_pre_ping=True)
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Top control bar
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_layout = QHBoxLayout(control_frame)
        
        # Symbol label
        self.symbol_label = QLabel("No Symbol")
        self.symbol_label.setFont(QFont('Arial', 14, QFont.Bold))
        control_layout.addWidget(self.symbol_label)
        
        control_layout.addStretch()
        
        # Indicator toggles
        self.cb_sma20 = QCheckBox("SMA 20")
        self.cb_sma20.setChecked(True)
        self.cb_sma20.stateChanged.connect(self._redraw)
        control_layout.addWidget(self.cb_sma20)
        
        self.cb_sma50 = QCheckBox("SMA 50")
        self.cb_sma50.setChecked(True)
        self.cb_sma50.stateChanged.connect(self._redraw)
        control_layout.addWidget(self.cb_sma50)
        
        self.cb_bb = QCheckBox("Bollinger")
        self.cb_bb.setChecked(False)
        self.cb_bb.stateChanged.connect(self._redraw)
        control_layout.addWidget(self.cb_bb)
        
        self.cb_events = QCheckBox("Vol Events")
        self.cb_events.setChecked(True)
        self.cb_events.stateChanged.connect(self._redraw)
        control_layout.addWidget(self.cb_events)
        
        self.cb_rsi = QCheckBox("RSI (9)")
        self.cb_rsi.setChecked(True)
        self.cb_rsi.stateChanged.connect(self._toggle_rsi)
        control_layout.addWidget(self.cb_rsi)
        
        # Period selector
        control_layout.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["3 Months", "6 Months", "1 Year", "2 Years", "All"])
        self.period_combo.setCurrentIndex(2)  # Default: 1 Year
        self.period_combo.currentIndexChanged.connect(self._on_period_change)
        control_layout.addWidget(self.period_combo)
        
        layout.addWidget(control_frame)
        
        # Create splitter for charts
        self.splitter = QSplitter(Qt.Vertical)
        
        # Price chart
        self.price_widget = pg.PlotWidget()
        self.price_widget.showGrid(x=True, y=True, alpha=0.3)
        self.price_widget.setLabel('left', 'Price (₹)')
        self.price_widget.setMinimumHeight(400)
        self.price_widget.getAxis('left').enableAutoSIPrefix(False)
        
        # Add crosshair to price chart
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.price_widget.addItem(self.vLine, ignoreBounds=True)
        self.price_widget.addItem(self.hLine, ignoreBounds=True)
        
        self.splitter.addWidget(self.price_widget)
        
        # Volume chart
        self.volume_widget = pg.PlotWidget()
        self.volume_widget.showGrid(x=True, y=True, alpha=0.3)
        self.volume_widget.setLabel('left', 'Volume')
        self.volume_widget.setMaximumHeight(100)
        self.volume_widget.setXLink(self.price_widget)
        
        # Add vertical crosshair to volume chart (linked)
        self.vLine_vol = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.volume_widget.addItem(self.vLine_vol, ignoreBounds=True)
        
        self.splitter.addWidget(self.volume_widget)
        
        # RSI chart
        self.rsi_widget = pg.PlotWidget()
        self.rsi_widget.showGrid(x=True, y=True, alpha=0.3)
        self.rsi_widget.setLabel('left', 'RSI')
        self.rsi_widget.setYRange(0, 100)
        self.rsi_widget.setMaximumHeight(100)
        self.rsi_widget.setXLink(self.price_widget)
        
        # Add vertical crosshair to RSI chart (linked)
        self.vLine_rsi = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.rsi_widget.addItem(self.vLine_rsi, ignoreBounds=True)
        
        # Add overbought/oversold lines
        self.rsi_widget.addItem(pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('#ef5350', width=1, style=Qt.DashLine)))
        self.rsi_widget.addItem(pg.InfiniteLine(pos=30, angle=0, pen=pg.mkPen('#26a69a', width=1, style=Qt.DashLine)))
        self.rsi_widget.addItem(pg.InfiniteLine(pos=50, angle=0, pen=pg.mkPen('gray', width=1, style=Qt.DotLine)))
        self.splitter.addWidget(self.rsi_widget)
        
        self.splitter.setSizes([350, 80, 80])
        layout.addWidget(self.splitter)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setFont(QFont('Consolas', 10))
        layout.addWidget(self.info_label)
        
        # Legend
        legend_frame = QFrame()
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(10, 2, 10, 2)
        
        legend_layout.addWidget(QLabel("<b>Volume Events:</b>"))
        legend_layout.addWidget(QLabel("⭐ <span style='color:#FF0000'>Ultra High (4x+)</span>"))
        legend_layout.addWidget(QLabel("▲ <span style='color:#FF6600'>Very High (3x+)</span>"))
        legend_layout.addWidget(QLabel("● <span style='color:#CCAA00'>High (2x+)</span>"))
        legend_layout.addStretch()
        legend_layout.addWidget(QLabel("<b>Lines:</b>"))
        legend_layout.addWidget(QLabel("<span style='color:#2196F3'>━ SMA 20</span>"))
        legend_layout.addWidget(QLabel("<span style='color:#FF9800'>━ SMA 50</span>"))
        legend_layout.addWidget(QLabel("<span style='color:#E91E63'>┅ Bollinger</span>"))
        legend_layout.addWidget(QLabel("<span style='color:#673AB7'>━ RSI 9</span>"))
        
        layout.addWidget(legend_frame)
        
        # Mouse tracking
        self.price_widget.scene().sigMouseMoved.connect(self._on_mouse_move)
    
    def load_symbol(self, symbol: str):
        """Load and display data for a symbol."""
        self.symbol = symbol
        self.symbol_label.setText(f"📈 {symbol}")
        
        # Get period
        period_map = {0: 63, 1: 126, 2: 252, 3: 504, 4: 9999}
        limit = period_map.get(self.period_combo.currentIndex(), 252)
        
        # Load data
        self._load_data(limit)
        self._load_events()
        self._redraw()
    
    def _load_data(self, limit: int):
        """Load price data from database."""
        query = text("""
            SELECT date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol AND timeframe = 'daily'
            ORDER BY date DESC
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            self.df = pd.read_sql(query, conn, params={'symbol': self.symbol, 'limit': limit})
        
        if len(self.df) == 0:
            print(f"No data for {self.symbol}")
            return
        
        # Sort ascending and reset index
        self.df = self.df.sort_values('date').reset_index(drop=True)
        
        # Convert types
        for col in ['open', 'high', 'low', 'close']:
            self.df[col] = self.df[col].astype(float)
        self.df['volume'] = self.df['volume'].astype(float)
        self.df['date'] = pd.to_datetime(self.df['date'])
        
        # Add x-axis index (simple integer index for plotting)
        self.df['x'] = range(len(self.df))
        
        # Calculate indicators
        self.df['sma20'] = self.df['close'].rolling(20).mean()
        self.df['sma50'] = self.df['close'].rolling(50).mean()
        self.df['bb_mid'] = self.df['close'].rolling(20).mean()
        self.df['bb_std'] = self.df['close'].rolling(20).std()
        self.df['bb_upper'] = self.df['bb_mid'] + 2 * self.df['bb_std']
        self.df['bb_lower'] = self.df['bb_mid'] - 2 * self.df['bb_std']
        
        # RSI (9-period) using Wilder's smoothing method (same as TradingView)
        period = 9
        delta = self.df['close'].diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta.where(delta < 0, 0))
        
        # First average using SMA for initial value
        first_avg_gain = gain.iloc[:period+1].mean()
        first_avg_loss = loss.iloc[:period+1].mean()
        
        # Use Wilder's smoothing (EMA with alpha = 1/period)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        self.df['rsi'] = 100 - (100 / (1 + rs))
        
        print(f"Loaded {len(self.df)} rows: {self.df['date'].min().date()} to {self.df['date'].max().date()}")
    
    def _load_events(self):
        """Load volume events."""
        if self.df is None or len(self.df) == 0:
            return
        
        min_date = self.df['date'].min()
        
        query = text("""
            SELECT event_date, volume_quintile, relative_volume
            FROM volume_cluster_events
            WHERE symbol = :symbol AND event_date >= :min_date
        """)
        
        with self.engine.connect() as conn:
            self.events_df = pd.read_sql(query, conn, params={
                'symbol': self.symbol, 
                'min_date': min_date.strftime('%Y-%m-%d')
            })
        
        if len(self.events_df) > 0:
            self.events_df['event_date'] = pd.to_datetime(self.events_df['event_date'])
            print(f"Loaded {len(self.events_df)} volume events")
    
    def _redraw(self):
        """Redraw the chart."""
        if self.df is None or len(self.df) == 0:
            return
        
        self.price_widget.clear()
        self.volume_widget.clear()
        
        # Re-add crosshair lines after clear
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.price_widget.addItem(self.vLine, ignoreBounds=True)
        self.price_widget.addItem(self.hLine, ignoreBounds=True)
        
        self.vLine_vol = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.volume_widget.addItem(self.vLine_vol, ignoreBounds=True)
        
        x = self.df['x'].values
        
        # Draw candlesticks
        candle_item = CandlestickItem(self.df)
        self.price_widget.addItem(candle_item)
        
        # Draw SMAs
        if self.cb_sma20.isChecked():
            self.price_widget.plot(x, self.df['sma20'].values, pen=pg.mkPen('#2196F3', width=1.5))
        
        if self.cb_sma50.isChecked():
            self.price_widget.plot(x, self.df['sma50'].values, pen=pg.mkPen('#FF9800', width=1.5))
        
        # Draw Bollinger Bands
        if self.cb_bb.isChecked():
            self.price_widget.plot(x, self.df['bb_upper'].values, pen=pg.mkPen('#E91E63', width=1, style=Qt.DashLine))
            self.price_widget.plot(x, self.df['bb_lower'].values, pen=pg.mkPen('#E91E63', width=1, style=Qt.DashLine))
        
        # Draw volume events
        if self.cb_events.isChecked() and self.events_df is not None and len(self.events_df) > 0:
            self._draw_events()
        
        # Draw volume bars
        colors = ['#26a69a' if self.df['close'].iloc[i] >= self.df['open'].iloc[i] else '#ef5350' 
                  for i in range(len(self.df))]
        bargraph = pg.BarGraphItem(x=x, height=self.df['volume'].values, width=0.8,
                                    brushes=[pg.mkBrush(c) for c in colors])
        self.volume_widget.addItem(bargraph)
        
        # Set axis with date labels
        self._setup_date_axis()
        
        # Draw RSI
        if self.cb_rsi.isChecked():
            self._draw_rsi()
        
        # Auto range
        self.price_widget.autoRange()
        self.volume_widget.autoRange()
    
    def _draw_events(self):
        """Draw volume event markers."""
        for _, event in self.events_df.iterrows():
            # Find matching date in price data
            matches = self.df[self.df['date'].dt.date == event['event_date'].date()]
            if len(matches) == 0:
                continue
            
            row = matches.iloc[0]
            x_pos = row['x']
            price = row['high'] * 1.02  # Slightly above high
            
            quintile = event['volume_quintile']
            if quintile == 'Ultra High':
                color, size, symbol = '#FF0000', 15, 'star'
            elif quintile == 'Very High':
                color, size, symbol = '#FF6600', 12, 't'
            else:
                color, size, symbol = '#FFCC00', 10, 'o'
            
            scatter = pg.ScatterPlotItem(
                [x_pos], [price], symbol=symbol, size=size,
                pen=pg.mkPen(color, width=2), brush=pg.mkBrush(color + '80')
            )
            self.price_widget.addItem(scatter)
    
    def _setup_date_axis(self):
        """Setup x-axis with date labels."""
        if self.df is None or len(self.df) == 0:
            return
        
        # Create tick labels at regular intervals
        n = len(self.df)
        step = max(1, n // 10)  # About 10 labels
        
        ticks = []
        for i in range(0, n, step):
            date_str = self.df['date'].iloc[i].strftime('%b %d')
            ticks.append((i, date_str))
        
        # Add last date
        ticks.append((n-1, self.df['date'].iloc[-1].strftime('%b %d')))
        
        ax = self.price_widget.getAxis('bottom')
        ax.setTicks([ticks])
    
    def _on_period_change(self):
        """Handle period change."""
        if self.symbol:
            self.load_symbol(self.symbol)
    
    def _draw_rsi(self):
        """Draw RSI indicator."""
        if self.df is None or len(self.df) == 0:
            return
        
        # Clear RSI widget but keep the reference lines
        self.rsi_widget.clear()
        
        # Re-add crosshair for RSI
        self.vLine_rsi = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1, style=Qt.DashLine))
        self.rsi_widget.addItem(self.vLine_rsi, ignoreBounds=True)
        
        # Re-add overbought/oversold lines
        self.rsi_widget.addItem(pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('#ef5350', width=1, style=Qt.DashLine)))
        self.rsi_widget.addItem(pg.InfiniteLine(pos=30, angle=0, pen=pg.mkPen('#26a69a', width=1, style=Qt.DashLine)))
        self.rsi_widget.addItem(pg.InfiniteLine(pos=50, angle=0, pen=pg.mkPen('gray', width=1, style=Qt.DotLine)))
        
        x = self.df['x'].values
        rsi = self.df['rsi'].values
        
        # Plot RSI line
        self.rsi_widget.plot(x, rsi, pen=pg.mkPen('#673AB7', width=2))
        
        # Keep Y range fixed
        self.rsi_widget.setYRange(0, 100)
    
    def _toggle_rsi(self):
        """Toggle RSI panel visibility."""
        if self.cb_rsi.isChecked():
            self.rsi_widget.show()
            self.splitter.setSizes([350, 80, 80])
        else:
            self.rsi_widget.hide()
            self.splitter.setSizes([400, 100, 0])
        self._redraw()
    
    def _on_mouse_move(self, pos):
        """Handle mouse movement - update crosshair and info display."""
        if self.df is None or len(self.df) == 0:
            return
        
        if self.price_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.price_widget.plotItem.vb.mapSceneToView(pos)
            x_val = mouse_point.x()
            y_val = mouse_point.y()
            x_idx = int(round(x_val))
            
            # Update crosshair position on all charts
            self.vLine.setPos(x_val)
            self.hLine.setPos(y_val)
            self.vLine_vol.setPos(x_val)
            self.vLine_rsi.setPos(x_val)
            
            if 0 <= x_idx < len(self.df):
                row = self.df.iloc[x_idx]
                date_str = row['date'].strftime('%a, %d %b %Y')
                
                # Calculate change
                change = row['close'] - row['open']
                change_pct = (change / row['open']) * 100 if row['open'] > 0 else 0
                change_color = "green" if change >= 0 else "red"
                change_sign = "+" if change >= 0 else ""
                
                # RSI info
                rsi_str = ""
                if pd.notna(row['rsi']):
                    rsi_val = row['rsi']
                    if rsi_val >= 70:
                        rsi_str = f" | RSI: {rsi_val:.1f} (Overbought)"
                    elif rsi_val <= 30:
                        rsi_str = f" | RSI: {rsi_val:.1f} (Oversold)"
                    else:
                        rsi_str = f" | RSI: {rsi_val:.1f}"
                
                self.info_label.setText(
                    f"📅 {date_str} | Open: ₹{row['open']:.2f} | High: ₹{row['high']:.2f} | "
                    f"Low: ₹{row['low']:.2f} | Close: ₹{row['close']:.2f} | "
                    f"Chg: {change_sign}{change:.2f} ({change_sign}{change_pct:.2f}%) | "
                    f"Vol: {row['volume']:,.0f}{rsi_str}"
                )


class ChartWindow(QMainWindow):
    """Main window for chart visualizer."""
    
    def __init__(self, symbol: str = None):
        super().__init__()
        self.setWindowTitle("Volume Events Chart")
        self.setGeometry(100, 100, 1200, 700)
        
        self.chart = SimpleChartWidget()
        self.setCentralWidget(self.chart)
        
        if symbol:
            self.chart.load_symbol(symbol)
            self.setWindowTitle(f"Chart - {symbol}")


def launch_chart(symbol: str):
    """Launch chart for a symbol (callable from other modules)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
    
    window = ChartWindow(symbol)
    window.show()
    
    if not QApplication.instance().property('running'):
        QApplication.instance().setProperty('running', True)
        app.exec_()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    symbol = 'RELIANCE.NS'
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    
    window = ChartWindow(symbol)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
