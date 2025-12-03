#!/usr/bin/env python3
"""
Real-Time Nifty 500 Market Breadth Monitor - FAST Version
==========================================================
Optimized for speed using real-time quotes instead of historical data.

Key optimizations:
1. Use yf.Ticker.info or fast_info for current price + prev_close
2. Batch download with minimal data
3. Incremental updates every 30 seconds
4. Cached previous close data
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time as dt_time
import pytz
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFrame, QProgressBar, QStatusBar, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

import pyqtgraph as pg

import yfinance as yf

# Import Nifty 500 stocks list
try:
    from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
    NIFTY500_YAHOO_SYMBOLS = [f"{s}.NS" for s in NIFTY_500_STOCKS]
except ImportError:
    NIFTY500_YAHOO_SYMBOLS = []

IST = pytz.timezone('Asia/Kolkata')
REFRESH_INTERVAL_MS = 30 * 1000  # 30 seconds - much faster!


@dataclass
class StockQuote:
    """Real-time stock quote data."""
    symbol: str
    current_price: float
    prev_close: float
    change_pct: float
    volume: int = 0


class FastDataFetcher(QThread):
    """
    Fast data fetcher using batch quotes.
    Much faster than downloading historical minute data.
    """
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, symbols: List[str], prev_close_cache: Dict[str, float] = None):
        super().__init__()
        self.symbols = symbols
        self.prev_close_cache = prev_close_cache or {}
    
    def run(self):
        try:
            result = self._fetch_realtime_data()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"Fetch error: {str(e)}")
    
    def _fetch_realtime_data(self) -> Dict:
        """Fetch real-time quotes for all stocks - FAST method."""
        start_time = time.time()
        
        self.progress.emit("Fetching NIFTY 50 index...")
        
        # 1. Fetch NIFTY index (just current price)
        nifty_data = self._fetch_nifty_intraday()
        
        # 2. Fetch all stock quotes in parallel batches
        self.progress.emit(f"Fetching {len(self.symbols)} stock quotes...")
        
        quotes = self._fetch_batch_quotes()
        
        # 3. Calculate A/D from quotes
        advances = 0
        declines = 0
        unchanged = 0
        
        gainers = []
        losers = []
        
        for quote in quotes:
            if quote.change_pct > 0.01:
                advances += 1
            elif quote.change_pct < -0.01:
                declines += 1
            else:
                unchanged += 1
            
            gainers.append(quote)
            losers.append(quote)
        
        # Sort for top gainers/losers
        gainers = sorted(gainers, key=lambda x: x.change_pct, reverse=True)[:10]
        losers = sorted(losers, key=lambda x: x.change_pct)[:10]
        
        elapsed = time.time() - start_time
        self.progress.emit(f"Fetched {len(quotes)} quotes in {elapsed:.1f}s")
        
        return {
            'nifty': nifty_data,
            'advances': advances,
            'declines': declines,
            'unchanged': unchanged,
            'gainers': gainers,
            'losers': losers,
            'timestamp': datetime.now(IST),
            'stock_count': len(quotes),
            'fetch_time': elapsed
        }
    
    def _fetch_nifty_intraday(self) -> pd.DataFrame:
        """Fetch NIFTY 50 intraday data (just today)."""
        try:
            nifty = yf.download(
                "^NSEI",
                period="1d",
                interval="1m",
                progress=False
            )
            
            if isinstance(nifty.columns, pd.MultiIndex):
                nifty.columns = nifty.columns.get_level_values(0)
            
            if nifty.index.tz is None:
                nifty.index = nifty.index.tz_localize('UTC').tz_convert(IST)
            else:
                nifty.index = nifty.index.tz_convert(IST)
            
            return nifty
        except Exception as e:
            self.progress.emit(f"NIFTY fetch error: {e}")
            return pd.DataFrame()
    
    def _fetch_batch_quotes(self) -> List[StockQuote]:
        """Fetch quotes for all symbols using fast batch download."""
        quotes = []
        batch_size = 100  # Larger batches for speed
        
        for i in range(0, len(self.symbols), batch_size):
            batch = self.symbols[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(self.symbols) + batch_size - 1) // batch_size
            
            self.progress.emit(f"Batch {batch_num}/{total_batches}...")
            
            try:
                # Download just 2 days of daily data to get prev_close and current
                data = yf.download(
                    batch,
                    period="2d",
                    interval="1d",
                    progress=False,
                    group_by='ticker',
                    threads=True
                )
                
                if data.empty:
                    continue
                
                for symbol in batch:
                    try:
                        if len(batch) == 1:
                            if isinstance(data.columns, pd.MultiIndex):
                                df = data[symbol]
                            else:
                                df = data
                        else:
                            if symbol not in data.columns.get_level_values(0):
                                continue
                            df = data[symbol]
                        
                        if df.empty or len(df) < 1:
                            continue
                        
                        # Get current and previous close
                        if len(df) >= 2:
                            current = float(df['Close'].iloc[-1])
                            prev_close = float(df['Close'].iloc[-2])
                        else:
                            current = float(df['Close'].iloc[-1])
                            prev_close = float(df['Open'].iloc[-1])
                        
                        if prev_close > 0:
                            change_pct = ((current - prev_close) / prev_close) * 100
                        else:
                            change_pct = 0
                        
                        quotes.append(StockQuote(
                            symbol=symbol.replace('.NS', ''),
                            current_price=current,
                            prev_close=prev_close,
                            change_pct=change_pct
                        ))
                        
                    except Exception:
                        pass
                        
            except Exception as e:
                self.progress.emit(f"Batch error: {e}")
        
        return quotes


class CandlestickItem(pg.GraphicsObject):
    """Fast candlestick graphics item."""
    
    def __init__(self, data: pd.DataFrame = None):
        super().__init__()
        self.data = data if data is not None else pd.DataFrame()
        self.picture = None
    
    def setData(self, data: pd.DataFrame):
        self.data = data
        self.picture = None
        self.prepareGeometryChange()
        self.update()
    
    def generatePicture(self):
        from PyQt6.QtGui import QPainter, QPicture, QPen, QBrush
        from PyQt6.QtCore import QRectF, QPointF
        
        self.picture = QPicture()
        painter = QPainter(self.picture)
        
        if self.data.empty:
            painter.end()
            return
        
        w = 0.6
        
        for i, (_, row) in enumerate(self.data.iterrows()):
            o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
            
            if c >= o:
                color = QColor(0, 200, 83)
            else:
                color = QColor(255, 82, 82)
            
            pen = QPen(color)
            pen.setWidthF(0.05)
            painter.setPen(pen)
            painter.setBrush(QBrush(color))
            
            # Wick
            painter.drawLine(QPointF(i, l), QPointF(i, h))
            
            # Body
            body_top = max(o, c)
            body_bottom = min(o, c)
            body_height = max(body_top - body_bottom, (h - l) * 0.01)
            
            painter.drawRect(QRectF(i - w/2, body_bottom, w, body_height))
        
        painter.end()
    
    def paint(self, painter, option, widget):
        if self.picture is None:
            self.generatePicture()
        if self.picture:
            self.picture.play(painter)
    
    def boundingRect(self):
        from PyQt6.QtCore import QRectF
        if self.data.empty:
            return QRectF(0, 0, 1, 1)
        n = len(self.data)
        y_min = self.data['Low'].min() if 'Low' in self.data.columns else 0
        y_max = self.data['High'].max() if 'High' in self.data.columns else 1
        margin = (y_max - y_min) * 0.1 or 1
        return QRectF(-1, y_min - margin, n + 2, (y_max - y_min) + 2 * margin)


class FastMarketBreadthDashboard(QMainWindow):
    """Fast real-time market breadth dashboard."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Nifty 500 Market Breadth - FAST")
        self.setGeometry(100, 100, 1500, 800)
        
        self._apply_dark_theme()
        pg.setConfigOptions(antialias=True, background='#1e1e1e', foreground='#ffffff')
        
        # Data
        self.symbols = NIFTY500_YAHOO_SYMBOLS or self._load_fallback_symbols()
        self.ad_history = []  # Store A/D history for chart
        self.fetch_worker = None
        
        self._setup_ui()
        
        # Fast refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(REFRESH_INTERVAL_MS)
        
        # Initial fetch
        QTimer.singleShot(100, self.refresh_data)
    
    def _load_fallback_symbols(self) -> List[str]:
        """Fallback symbols if import fails."""
        return [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "BHARTIARTL.NS", "SBIN.NS", "WIPRO.NS", "ITC.NS", "LT.NS",
        ]
    
    def _apply_dark_theme(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: #ffffff; }
            QPushButton { 
                background-color: #0d6efd; color: white; 
                border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0b5ed7; }
            QPushButton:disabled { background-color: #6c757d; }
            QTableWidget { background-color: #2d2d2d; color: #ffffff; gridline-color: #404040; border: none; }
            QHeaderView::section { background-color: #3d3d3d; color: #ffffff; padding: 6px; border: none; }
            QGroupBox { color: #ffffff; border: 1px solid #404040; border-radius: 4px; margin-top: 12px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QStatusBar { background-color: #2d2d2d; color: #888; }
        """)
    
    def _setup_ui(self):
        """Setup UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("📊 Real-Time Nifty 500 Market Breadth")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        
        self.lbl_advances = QLabel("Advances: --")
        self.lbl_advances.setStyleSheet("color: #00c853; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_advances)
        
        self.lbl_declines = QLabel("Declines: --")
        self.lbl_declines.setStyleSheet("color: #ff5252; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_declines)
        
        self.lbl_ratio = QLabel("A/D Ratio: --")
        self.lbl_ratio.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_ratio)
        
        header.addStretch()
        
        self.btn_refresh = QPushButton("🔄 Refresh Now")
        self.btn_refresh.clicked.connect(self.refresh_data)
        header.addWidget(self.btn_refresh)
        
        layout.addLayout(header)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Charts
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        
        # NIFTY chart
        nifty_group = QGroupBox("NIFTY 50 Index")
        nifty_layout = QVBoxLayout(nifty_group)
        self.nifty_plot = pg.PlotWidget()
        self.nifty_plot.setLabel('left', 'Price')
        self.nifty_plot.showGrid(x=True, y=True, alpha=0.3)
        self.candlestick_item = CandlestickItem()
        self.nifty_plot.addItem(self.candlestick_item)
        nifty_layout.addWidget(self.nifty_plot)
        charts_layout.addWidget(nifty_group)
        
        # A/D chart
        ad_group = QGroupBox("Advance/Decline Line")
        ad_layout = QVBoxLayout(ad_group)
        self.ad_plot = pg.PlotWidget()
        self.ad_plot.setLabel('left', 'Net A/D')
        self.ad_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ad_plot.setXLink(self.nifty_plot)
        ad_layout.addWidget(self.ad_plot)
        charts_layout.addWidget(ad_group)
        
        splitter.addWidget(charts_widget)
        
        # Tables
        tables_widget = QWidget()
        tables_layout = QVBoxLayout(tables_widget)
        
        # Gainers
        gainers_group = QGroupBox("📈 Top Gainers")
        gainers_layout = QVBoxLayout(gainers_group)
        self.gainers_table = QTableWidget()
        self.gainers_table.setColumnCount(3)
        self.gainers_table.setHorizontalHeaderLabels(["Symbol", "Price", "Change %"])
        self.gainers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.gainers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        gainers_layout.addWidget(self.gainers_table)
        tables_layout.addWidget(gainers_group)
        
        # Losers
        losers_group = QGroupBox("📉 Top Losers")
        losers_layout = QVBoxLayout(losers_group)
        self.losers_table = QTableWidget()
        self.losers_table.setColumnCount(3)
        self.losers_table.setHorizontalHeaderLabels(["Symbol", "Price", "Change %"])
        self.losers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.losers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        losers_layout.addWidget(self.losers_table)
        tables_layout.addWidget(losers_group)
        
        splitter.addWidget(tables_widget)
        splitter.setSizes([1000, 400])
        
        layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - fetching data...")
    
    def refresh_data(self):
        """Refresh data."""
        if self.fetch_worker and self.fetch_worker.isRunning():
            return
        
        self.btn_refresh.setEnabled(False)
        self.status_bar.showMessage("Fetching real-time quotes...")
        
        self.fetch_worker = FastDataFetcher(self.symbols)
        self.fetch_worker.finished.connect(self._on_data_fetched)
        self.fetch_worker.progress.connect(lambda m: self.status_bar.showMessage(m))
        self.fetch_worker.error.connect(self._on_error)
        self.fetch_worker.start()
    
    def _on_error(self, error: str):
        """Handle error."""
        self.btn_refresh.setEnabled(True)
        self.status_bar.showMessage(f"Error: {error}")
    
    def _on_data_fetched(self, data: Dict):
        """Handle fetched data."""
        self.btn_refresh.setEnabled(True)
        
        # Update summary
        advances = data.get('advances', 0)
        declines = data.get('declines', 0)
        
        self.lbl_advances.setText(f"Advances: {advances}")
        self.lbl_declines.setText(f"Declines: {declines}")
        
        if declines > 0:
            ratio = advances / declines
            self.lbl_ratio.setText(f"A/D Ratio: {ratio:.2f}")
        else:
            self.lbl_ratio.setText("A/D Ratio: ∞")
        
        # Store A/D history
        timestamp = data.get('timestamp', datetime.now(IST))
        net_ad = advances - declines
        self.ad_history.append({
            'timestamp': timestamp,
            'net': net_ad,
            'advances': advances,
            'declines': declines
        })
        
        # Keep only last 8 hours of data points
        max_points = 8 * 60 * 2  # 8 hours at 30-sec intervals
        if len(self.ad_history) > max_points:
            self.ad_history = self.ad_history[-max_points:]
        
        # Update charts
        nifty_data = data.get('nifty')
        if nifty_data is not None and not nifty_data.empty:
            self.candlestick_item.setData(nifty_data.reset_index())
            self.nifty_plot.autoRange()
        
        # Update A/D chart
        self._update_ad_chart()
        
        # Update tables
        self._update_tables(data.get('gainers', []), data.get('losers', []))
        
        # Status
        fetch_time = data.get('fetch_time', 0)
        stock_count = data.get('stock_count', 0)
        self.status_bar.showMessage(
            f"Updated: {timestamp.strftime('%H:%M:%S')} | "
            f"Stocks: {stock_count} | "
            f"Fetch: {fetch_time:.1f}s | "
            f"Next refresh in 30s"
        )
    
    def _update_ad_chart(self):
        """Update A/D history chart."""
        self.ad_plot.clear()
        
        if not self.ad_history:
            return
        
        x = np.arange(len(self.ad_history))
        y = np.array([d['net'] for d in self.ad_history])
        
        # Line
        pen = pg.mkPen(color='#00c853', width=2)
        self.ad_plot.plot(x, y, pen=pen)
        
        # Zero line
        zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('#666666', width=1, style=Qt.PenStyle.DashLine))
        self.ad_plot.addItem(zero_line)
        
        # Fill
        pos_fill = pg.FillBetweenItem(
            pg.PlotDataItem(x, np.maximum(y, 0)),
            pg.PlotDataItem(x, np.zeros_like(y)),
            brush=pg.mkBrush(0, 200, 83, 50)
        )
        neg_fill = pg.FillBetweenItem(
            pg.PlotDataItem(x, np.minimum(y, 0)),
            pg.PlotDataItem(x, np.zeros_like(y)),
            brush=pg.mkBrush(255, 82, 82, 50)
        )
        self.ad_plot.addItem(pos_fill)
        self.ad_plot.addItem(neg_fill)
        
        self.ad_plot.autoRange()
    
    def _update_tables(self, gainers: List[StockQuote], losers: List[StockQuote]):
        """Update gainers/losers tables."""
        self.gainers_table.setRowCount(len(gainers))
        for i, q in enumerate(gainers):
            self.gainers_table.setItem(i, 0, QTableWidgetItem(q.symbol))
            self.gainers_table.setItem(i, 1, QTableWidgetItem(f"₹{q.current_price:.2f}"))
            change_item = QTableWidgetItem(f"+{q.change_pct:.2f}%")
            change_item.setForeground(QColor(0, 200, 83))
            self.gainers_table.setItem(i, 2, change_item)
        
        self.losers_table.setRowCount(len(losers))
        for i, q in enumerate(losers):
            self.losers_table.setItem(i, 0, QTableWidgetItem(q.symbol))
            self.losers_table.setItem(i, 1, QTableWidgetItem(f"₹{q.current_price:.2f}"))
            change_item = QTableWidgetItem(f"{q.change_pct:.2f}%")
            change_item.setForeground(QColor(255, 82, 82))
            self.losers_table.setItem(i, 2, change_item)
    
    def closeEvent(self, event):
        """Handle close."""
        self.refresh_timer.stop()
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(13, 110, 253))
    app.setPalette(palette)
    
    window = FastMarketBreadthDashboard()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
