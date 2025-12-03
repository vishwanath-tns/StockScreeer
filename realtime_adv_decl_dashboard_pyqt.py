#!/usr/bin/env python3
"""
Real-Time Market Breadth Monitor - PyQtGraph Version 4.1 (OPTIMIZED)
=====================================================================
Cleaner architecture with synchronized charts:
1. Download 2 days 1-min NIFTY data
2. Download 2 days 1-min data for all Nifty 500 stocks
3. Calculate A/D using VECTORIZED operations (fast!)
4. Plot synchronized NIFTY and A/D charts
5. Top gainers/losers based on previous close

OPTIMIZATIONS in v4.1:
- Reduced data period from 5d to 2d (60% less data to download)
- Vectorized A/D calculation using pandas (O(n) instead of O(n*m))
- Reduced refresh interval to 1 minute for faster updates
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, List, Tuple
import traceback

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFrame, QProgressBar, QStatusBar, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QRunnable, QThreadPool
from PyQt6.QtGui import QFont, QColor, QPalette

import pyqtgraph as pg
from pyqtgraph import GraphicsObject

import yfinance as yf

# Import Nifty 500 stocks list
try:
    from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
    NIFTY500_YAHOO_SYMBOLS = [f"{s}.NS" for s in NIFTY_500_STOCKS]
except ImportError:
    NIFTY500_YAHOO_SYMBOLS = None

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
IST = pytz.timezone('Asia/Kolkata')
REFRESH_INTERVAL_MS = 60 * 1000  # 1 minute - faster refresh

# Nifty 500 symbols - fallback if import fails
NIFTY500_SYMBOLS_FALLBACK = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "BHARTIARTL.NS", "SBIN.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "ULTRACEMCO.NS",
    "HDFCLIFE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS",
    "JSWSTEEL.NS", "TATAMOTORS.NS", "ADANIENT.NS", "ADANIPORTS.NS", "M&M.NS",
    "DRREDDY.NS", "CIPLA.NS", "TECHM.NS", "DIVISLAB.NS", "GRASIM.NS",
    "EICHERMOT.NS", "BPCL.NS", "HEROMOTOCO.NS", "BRITANNIA.NS", "APOLLOHOSP.NS",
    "TATACONSUM.NS", "NESTLEIND.NS", "HINDALCO.NS", "TATASTEEL.NS", "SBILIFE.NS",
    "VEDL.NS", "INDUSINDBK.NS", "UPL.NS", "SHRIRAMFIN.NS", "DABUR.NS",
]


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CANDLESTICK GRAPHICS ITEM
# ─────────────────────────────────────────────────────────────────────────────
class CandlestickItem(GraphicsObject):
    """Custom PyQtGraph graphics item for candlestick charts."""
    
    def __init__(self, data: pd.DataFrame):
        super().__init__()
        self.data = data
        self.picture = None
        self.generatePicture()
    
    def generatePicture(self):
        from PyQt6.QtGui import QPainter, QPicture, QPen, QBrush
        from PyQt6.QtCore import QRectF
        
        self.picture = QPicture()
        painter = QPainter(self.picture)
        
        if self.data.empty:
            painter.end()
            return
            
        n_candles = len(self.data)
        # Dynamic width based on candle count
        if n_candles > 200:
            w = 0.4
        elif n_candles > 100:
            w = 0.6
        else:
            w = 0.8
        
        for i, (idx, row) in enumerate(self.data.iterrows()):
            o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
            
            # Colors
            if c >= o:
                color = QColor(0, 200, 83)  # Green
                body_brush = QBrush(color)
            else:
                color = QColor(255, 82, 82)  # Red
                body_brush = QBrush(color)
            
            pen = QPen(color)
            pen.setWidthF(0.05)
            painter.setPen(pen)
            painter.setBrush(body_brush)
            
            # Draw wick
            painter.drawLine(pg.Point(i, l), pg.Point(i, h))
            
            # Draw body
            body_top = max(o, c)
            body_bottom = min(o, c)
            body_height = max(body_top - body_bottom, (h - l) * 0.01)  # Min height
            
            rect = QRectF(i - w/2, body_bottom, w, body_height)
            painter.drawRect(rect)
        
        painter.end()
    
    def paint(self, painter, option, widget):
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
    
    def setData(self, data: pd.DataFrame):
        self.data = data
        self.generatePicture()
        self.informViewBoundsChanged()
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHER WORKER
# ─────────────────────────────────────────────────────────────────────────────
class DataFetchWorker(QThread):
    """
    Background worker that fetches all data and calculates A/D synchronously.
    Returns fully synchronized data for both charts.
    Uses cached prev_close values for stability across refreshes.
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
            result = self.fetch_all_data()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"Fetch error: {str(e)}\n{traceback.format_exc()}")
    
    def fetch_all_data(self) -> Dict:
        """
        Fetch NIFTY and all stock data, calculate synchronized A/D.
        """
        self.progress.emit("Fetching NIFTY index data...")
        
        # 1. Fetch NIFTY 50 index data (2 days, 1-min)
        nifty_data = yf.download(
            "^NSEI",
            period="2d",
            interval="1m",
            progress=False
        )
        
        if nifty_data.empty:
            raise ValueError("Failed to fetch NIFTY data")
        
        # Flatten multi-index columns if present
        if isinstance(nifty_data.columns, pd.MultiIndex):
            nifty_data.columns = nifty_data.columns.get_level_values(0)
        
        # Convert index to IST
        if nifty_data.index.tz is None:
            nifty_data.index = nifty_data.index.tz_localize('UTC').tz_convert(IST)
        else:
            nifty_data.index = nifty_data.index.tz_convert(IST)
        
        # Filter to last 2 trading days only
        nifty_data = self._filter_last_2_days(nifty_data)
        
        self.progress.emit(f"NIFTY data: {len(nifty_data)} candles")
        
        # 2. Fetch all stock data in batches
        self.progress.emit(f"Fetching {len(self.symbols)} stocks...")
        
        all_stock_data = {}
        batch_size = 50
        
        for i in range(0, len(self.symbols), batch_size):
            batch = self.symbols[i:i+batch_size]
            self.progress.emit(f"Fetching batch {i//batch_size + 1}/{(len(self.symbols)-1)//batch_size + 1}...")
            
            try:
                batch_data = yf.download(
                    batch,
                    period="2d",
                    interval="1m",
                    progress=False,
                    group_by='ticker',
                    threads=True
                )
                
                if not batch_data.empty:
                    for symbol in batch:
                        try:
                            if len(batch) == 1:
                                # Single symbol - no multi-level columns
                                if isinstance(batch_data.columns, pd.MultiIndex):
                                    stock_df = batch_data[symbol].copy()
                                else:
                                    stock_df = batch_data.copy()
                            else:
                                if symbol in batch_data.columns.get_level_values(0):
                                    stock_df = batch_data[symbol].copy()
                                else:
                                    continue
                            
                            if not stock_df.empty and 'Close' in stock_df.columns:
                                # Convert timezone
                                if stock_df.index.tz is None:
                                    stock_df.index = stock_df.index.tz_localize('UTC').tz_convert(IST)
                                else:
                                    stock_df.index = stock_df.index.tz_convert(IST)
                                
                                all_stock_data[symbol] = stock_df
                        except Exception:
                            pass
                            
            except Exception as e:
                self.progress.emit(f"Batch error: {str(e)}")
        
        self.progress.emit(f"Fetched {len(all_stock_data)} stocks successfully")
        
        # 3. Calculate A/D for each minute in NIFTY data
        self.progress.emit("Calculating Advance/Decline for each minute...")
        
        ad_data, updated_cache = self._calculate_ad_per_minute(nifty_data, all_stock_data)
        
        # 4. Calculate top gainers/losers using previous day's close
        self.progress.emit("Calculating top gainers/losers...")
        gainers, losers, distribution = self._calculate_gainers_losers(all_stock_data)
        
        return {
            'nifty': nifty_data,
            'ad_data': ad_data,
            'gainers': gainers,
            'losers': losers,
            'distribution': distribution,
            'timestamp': datetime.now(IST),
            'stock_count': len(all_stock_data),
            'prev_close_cache': updated_cache  # Return updated cache
        }
    
    def _filter_last_2_days(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only the last 2 unique trading dates."""
        if df.empty:
            return df
        
        dates = df.index.date
        unique_dates = sorted(set(dates), reverse=True)[:2]
        
        mask = pd.Series(dates).isin(unique_dates).values
        return df[mask]
    
    def _calculate_ad_per_minute(self, nifty_data: pd.DataFrame, 
                                   all_stock_data: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict]:
        """
        Calculate advances, declines, unchanged for each minute in nifty_data.
        Uses VECTORIZED approach for speed - O(n) instead of O(n*m).
        Uses cached prev_close values for stability across refreshes.
        Returns (ad_df, updated_cache).
        """
        self.progress.emit("Building price matrix (vectorized)...")
        
        # Get NIFTY timestamps as the master index
        master_index = nifty_data.index
        
        # Get unique dates - we need today's date for proper prev_close
        nifty_dates = sorted(set(nifty_data.index.date))
        today = nifty_dates[-1] if nifty_dates else None
        
        # Build a DataFrame with all stock closes aligned to master index
        # This is done once, then we can vectorize the A/D calculation
        close_data = {}
        prev_close_data = {}
        updated_cache = dict(self.prev_close_cache)  # Start with existing cache
        
        for symbol, stock_df in all_stock_data.items():
            try:
                if stock_df.empty or 'Close' not in stock_df.columns:
                    continue
                
                # Reindex to master index using forward fill (last known price)
                aligned = stock_df['Close'].reindex(master_index, method='ffill')
                close_data[symbol] = aligned
                
                # Calculate previous day close
                dates_in_stock = sorted(set(stock_df.index.date))
                
                # Get the prev_close for today
                if len(dates_in_stock) >= 2:
                    # Have 2 days - use yesterday's last close
                    yesterday = dates_in_stock[-2]
                    prev_day_data = stock_df[stock_df.index.date == yesterday]
                    if not prev_day_data.empty:
                        prev_close = prev_day_data['Close'].iloc[-1]
                        updated_cache[symbol] = float(prev_close)  # Update cache
                elif symbol in self.prev_close_cache:
                    # Use cached value if only 1 day of data
                    prev_close = self.prev_close_cache[symbol]
                else:
                    # Fallback to today's open
                    today_data = stock_df[stock_df.index.date == dates_in_stock[-1]]
                    if not today_data.empty and 'Open' in today_data.columns:
                        prev_close = today_data['Open'].iloc[0]
                    else:
                        continue
                
                # Create a series with constant prev_close for all timestamps
                prev_close_series = pd.Series(prev_close, index=master_index)
                prev_close_data[symbol] = prev_close_series
                
            except Exception:
                pass
        
        self.progress.emit(f"Processing {len(close_data)} stocks vectorized...")
        
        if not close_data:
            # Return empty DataFrame with correct structure
            return pd.DataFrame({
                'advances': 0, 'declines': 0, 'unchanged': 0, 'net': 0
            }, index=master_index), updated_cache
        
        # Create DataFrames
        close_df = pd.DataFrame(close_data)
        prev_close_df = pd.DataFrame(prev_close_data)
        
        # Calculate percentage change for all stocks at once (vectorized!)
        pct_change_df = ((close_df - prev_close_df) / prev_close_df) * 100
        
        # Count advances, declines, unchanged per timestamp (vectorized!)
        advances = (pct_change_df > 0.01).sum(axis=1)
        declines = (pct_change_df < -0.01).sum(axis=1)
        unchanged = ((pct_change_df >= -0.01) & (pct_change_df <= 0.01)).sum(axis=1)
        
        # Build result DataFrame
        ad_df = pd.DataFrame({
            'advances': advances,
            'declines': declines,
            'unchanged': unchanged,
            'net': advances - declines
        }, index=master_index)
        
        self.progress.emit(f"A/D calculation complete: {len(ad_df)} data points, cache size: {len(updated_cache)}")
        
        return ad_df, updated_cache
    
    def _calculate_gainers_losers(self, all_stock_data: Dict[str, pd.DataFrame]) -> Tuple[List, List]:
        """
        Calculate top gainers and losers based on previous day's close.
        """
        changes = []
        
        for symbol, df in all_stock_data.items():
            try:
                if df.empty:
                    continue
                
                dates = sorted(set(df.index.date))
                
                if len(dates) >= 2:
                    # Have 2 days - use yesterday's close
                    today = dates[-1]
                    yesterday = dates[-2]
                    
                    df_today = df[df.index.date == today]
                    df_yesterday = df[df.index.date == yesterday]
                    
                    if df_today.empty or df_yesterday.empty:
                        continue
                    
                    current_price = df_today['Close'].iloc[-1]
                    prev_close = df_yesterday['Close'].iloc[-1]
                elif len(dates) == 1:
                    # Only 1 day - use today's open as reference
                    today = dates[0]
                    df_today = df[df.index.date == today]
                    
                    if df_today.empty or 'Open' not in df_today.columns:
                        continue
                    
                    current_price = df_today['Close'].iloc[-1]
                    prev_close = df_today['Open'].iloc[0]
                else:
                    continue
                
                if prev_close == 0 or pd.isna(prev_close) or pd.isna(current_price):
                    continue
                    
                pct_change = ((current_price - prev_close) / prev_close) * 100
                
                changes.append({
                    'symbol': symbol.replace('.NS', ''),
                    'current': float(current_price),
                    'prev_close': float(prev_close),
                    'change': float(pct_change)
                })
                
            except Exception as e:
                pass
        
        print(f"[DEBUG] Total changes calculated: {len(changes)}")
        
        # Calculate distribution buckets
        distribution = {
            'gain_0_1': 0, 'gain_1_2': 0, 'gain_2_3': 0, 'gain_3_5': 0, 'gain_5_plus': 0,
            'loss_0_1': 0, 'loss_1_2': 0, 'loss_2_3': 0, 'loss_3_5': 0, 'loss_5_plus': 0,
            'unchanged': 0
        }
        
        for item in changes:
            chg = item['change']
            if chg > 5:
                distribution['gain_5_plus'] += 1
            elif chg > 3:
                distribution['gain_3_5'] += 1
            elif chg > 2:
                distribution['gain_2_3'] += 1
            elif chg > 1:
                distribution['gain_1_2'] += 1
            elif chg > 0.01:
                distribution['gain_0_1'] += 1
            elif chg < -5:
                distribution['loss_5_plus'] += 1
            elif chg < -3:
                distribution['loss_3_5'] += 1
            elif chg < -2:
                distribution['loss_2_3'] += 1
            elif chg < -1:
                distribution['loss_1_2'] += 1
            elif chg < -0.01:
                distribution['loss_0_1'] += 1
            else:
                distribution['unchanged'] += 1
        
        # Sort for gainers and losers
        sorted_changes = sorted(changes, key=lambda x: x['change'], reverse=True)
        
        gainers = sorted_changes[:10]
        losers = sorted_changes[-10:][::-1]  # Reverse to show biggest loser first
        
        return gainers, losers, distribution


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DASHBOARD WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class RealtimeAdvDeclDashboardPyQt(QMainWindow):
    """Main dashboard window with synchronized NIFTY and A/D charts."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Nifty 500 Market Breadth Monitor v4.1 (PyQtGraph - OPTIMIZED)")
        self.setGeometry(100, 100, 1600, 900)
        
        # Dark theme
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: #ffffff; }
            QPushButton { 
                background-color: #0d6efd; 
                color: white; 
                border: none; 
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0b5ed7; }
            QPushButton:disabled { background-color: #6c757d; }
            QTableWidget { 
                background-color: #2d2d2d; 
                color: #ffffff;
                gridline-color: #404040;
                border: none;
            }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section { 
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 6px;
                border: none;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QStatusBar { background-color: #2d2d2d; color: #888; }
            QProgressBar {
                background-color: #3d3d3d;
                border: none;
                border-radius: 2px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #0d6efd;
            }
        """)
        
        # PyQtGraph configuration
        pg.setConfigOptions(antialias=True, background='#1e1e1e', foreground='#ffffff')
        
        # Data storage
        self.nifty_data = None
        self.ad_data = None
        self.gainers = []
        self.losers = []
        self.distribution = {}
        self.fetch_worker = None
        
        # Cache for previous day closes - persists across refreshes for stability
        self.prev_close_cache = {}  # symbol -> prev_day_close
        
        # Get Nifty 500 symbols
        self.symbols = self._load_symbols()
        
        # Setup UI
        self._setup_ui()
        
        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(REFRESH_INTERVAL_MS)
        
        # Initial fetch
        QTimer.singleShot(500, self.refresh_data)
    
    def _load_symbols(self) -> List[str]:
        """Load Nifty 500 symbols - use imported list first, then DB, then fallback."""
        # First try imported list (fastest and most reliable)
        if NIFTY500_YAHOO_SYMBOLS and len(NIFTY500_YAHOO_SYMBOLS) > 0:
            print(f"Using imported Nifty 500 list: {len(NIFTY500_YAHOO_SYMBOLS)} stocks")
            return NIFTY500_YAHOO_SYMBOLS
        
        # Try database as backup
        try:
            from sqlalchemy import create_engine, text
            from dotenv import load_dotenv
            import os
            
            load_dotenv()
            
            engine = create_engine(
                f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}@"
                f"{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}/"
                f"{os.getenv('MYSQL_DB', 'nse_data')}"
            )
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT yahoo_symbol FROM nifty500_yahoo_mapping WHERE yahoo_symbol IS NOT NULL"))
                symbols = [row[0] for row in result.fetchall()]
                
            if symbols:
                print(f"Loaded {len(symbols)} symbols from database")
                return symbols
        except Exception as e:
            print(f"Could not load symbols from DB: {e}")
        
        # Fallback to sample symbols
        print(f"Using fallback symbols: {len(NIFTY500_SYMBOLS_FALLBACK)} stocks")
        return NIFTY500_SYMBOLS_FALLBACK
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ─── Header ───
        header = QHBoxLayout()
        
        title = QLabel("📊 Real-Time Nifty 500 Market Breadth")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # NIFTY price label
        self.lbl_nifty = QLabel("NIFTY: --")
        self.lbl_nifty.setStyleSheet("color: #ffeb3b; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_nifty)
        
        # Separator
        sep1 = QLabel(" | ")
        sep1.setStyleSheet("color: #666666; font-size: 14px;")
        header.addWidget(sep1)
        
        # Summary labels
        self.lbl_advances = QLabel("Advances: --")
        self.lbl_advances.setStyleSheet("color: #00c853; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_advances)
        
        self.lbl_declines = QLabel("Declines: --")
        self.lbl_declines.setStyleSheet("color: #ff5252; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_declines)
        
        self.lbl_unchanged = QLabel("Unchanged: --")
        self.lbl_unchanged.setStyleSheet("color: #888888; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_unchanged)
        
        self.lbl_total = QLabel("Total: --")
        self.lbl_total.setStyleSheet("color: #aaaaaa; font-size: 14px;")
        header.addWidget(self.lbl_total)
        
        self.lbl_ratio = QLabel("A/D Ratio: --")
        self.lbl_ratio.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        header.addWidget(self.lbl_ratio)
        
        header.addStretch()
        
        self.btn_refresh = QPushButton("🔄 Refresh Now")
        self.btn_refresh.clicked.connect(self.refresh_data)
        header.addWidget(self.btn_refresh)
        
        main_layout.addLayout(header)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(4)
        main_layout.addWidget(self.progress_bar)
        
        # ─── Main content splitter ───
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Charts
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(5)
        
        # NIFTY Chart
        nifty_group = QGroupBox("NIFTY 50 Index")
        nifty_layout = QVBoxLayout(nifty_group)
        nifty_layout.setContentsMargins(5, 15, 5, 5)
        
        self.nifty_plot = pg.PlotWidget()
        self.nifty_plot.setLabel('left', 'Price')
        self.nifty_plot.showGrid(x=True, y=True, alpha=0.3)
        self.nifty_plot.setMinimumHeight(250)
        self.candlestick_item = None
        nifty_layout.addWidget(self.nifty_plot)
        
        charts_layout.addWidget(nifty_group)
        
        # A/D Chart
        ad_group = QGroupBox("Advance/Decline Line")
        ad_layout = QVBoxLayout(ad_group)
        ad_layout.setContentsMargins(5, 15, 5, 5)
        
        self.ad_plot = pg.PlotWidget()
        self.ad_plot.setLabel('left', 'Net A/D')
        self.ad_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ad_plot.setMinimumHeight(200)
        
        # Link X axes for synchronized zooming/panning
        self.ad_plot.setXLink(self.nifty_plot)
        
        ad_layout.addWidget(self.ad_plot)
        
        charts_layout.addWidget(ad_group)
        
        splitter.addWidget(charts_widget)
        
        # Right side: Tables
        tables_widget = QWidget()
        tables_layout = QVBoxLayout(tables_widget)
        tables_layout.setContentsMargins(0, 0, 0, 0)
        tables_layout.setSpacing(10)
        
        # Top Gainers
        gainers_group = QGroupBox("📈 Top Gainers")
        gainers_layout = QVBoxLayout(gainers_group)
        gainers_layout.setContentsMargins(5, 15, 5, 5)
        
        self.gainers_table = QTableWidget()
        self.gainers_table.setColumnCount(3)
        self.gainers_table.setHorizontalHeaderLabels(["Symbol", "Price", "Change %"])
        self.gainers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.gainers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        gainers_layout.addWidget(self.gainers_table)
        
        tables_layout.addWidget(gainers_group)
        
        # Top Losers
        losers_group = QGroupBox("📉 Top Losers")
        losers_layout = QVBoxLayout(losers_group)
        losers_layout.setContentsMargins(5, 15, 5, 5)
        
        self.losers_table = QTableWidget()
        self.losers_table.setColumnCount(3)
        self.losers_table.setHorizontalHeaderLabels(["Symbol", "Price", "Change %"])
        self.losers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.losers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        losers_layout.addWidget(self.losers_table)
        
        tables_layout.addWidget(losers_group)
        
        # Distribution Panel
        dist_group = QGroupBox("📊 Distribution by % Change")
        dist_layout = QGridLayout(dist_group)
        dist_layout.setContentsMargins(10, 20, 10, 10)
        dist_layout.setSpacing(5)
        
        # Headers
        gain_header = QLabel("GAINERS")
        gain_header.setStyleSheet("color: #00c853; font-weight: bold; font-size: 11px;")
        gain_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dist_layout.addWidget(gain_header, 0, 0)
        
        loss_header = QLabel("LOSERS")
        loss_header.setStyleSheet("color: #ff5252; font-weight: bold; font-size: 11px;")
        loss_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dist_layout.addWidget(loss_header, 0, 2)
        
        # Distribution labels - Gainers (left side)
        self.dist_labels = {}
        gain_ranges = [("5%+", "gain_5_plus"), ("3-5%", "gain_3_5"), ("2-3%", "gain_2_3"), 
                       ("1-2%", "gain_1_2"), ("0-1%", "gain_0_1")]
        
        for i, (label_text, key) in enumerate(gain_ranges):
            range_lbl = QLabel(f"{label_text}:")
            range_lbl.setStyleSheet("color: #888; font-size: 11px;")
            range_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            dist_layout.addWidget(range_lbl, i+1, 0)
            
            count_lbl = QLabel("--")
            count_lbl.setStyleSheet("color: #00c853; font-weight: bold; font-size: 11px;")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            dist_layout.addWidget(count_lbl, i+1, 1)
            self.dist_labels[key] = count_lbl
        
        # Distribution labels - Losers (right side)
        loss_ranges = [("5%+", "loss_5_plus"), ("3-5%", "loss_3_5"), ("2-3%", "loss_2_3"), 
                       ("1-2%", "loss_1_2"), ("0-1%", "loss_0_1")]
        
        for i, (label_text, key) in enumerate(loss_ranges):
            count_lbl = QLabel("--")
            count_lbl.setStyleSheet("color: #ff5252; font-weight: bold; font-size: 11px;")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            dist_layout.addWidget(count_lbl, i+1, 2)
            self.dist_labels[key] = count_lbl
            
            range_lbl = QLabel(f":{label_text}")
            range_lbl.setStyleSheet("color: #888; font-size: 11px;")
            range_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            dist_layout.addWidget(range_lbl, i+1, 3)
        
        tables_layout.addWidget(dist_group)
        
        splitter.addWidget(tables_widget)
        
        # Set splitter sizes (70% charts, 30% tables)
        splitter.setSizes([1100, 500])
        
        main_layout.addWidget(splitter)
        
        # ─── Status bar ───
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Click Refresh to fetch data.")
    
    def refresh_data(self):
        """Start data fetch in background thread."""
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.status_bar.showMessage("Fetch already in progress...")
            return
        
        self.btn_refresh.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_bar.showMessage("Fetching data...")
        
        self.fetch_worker = DataFetchWorker(self.symbols, self.prev_close_cache)
        self.fetch_worker.finished.connect(self._on_data_fetched)
        self.fetch_worker.progress.connect(self._on_progress)
        self.fetch_worker.error.connect(self._on_error)
        self.fetch_worker.start()
    
    def _on_progress(self, message: str):
        """Handle progress updates."""
        self.status_bar.showMessage(message)
    
    def _on_error(self, error: str):
        """Handle fetch errors."""
        self.btn_refresh.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Error: {error}")
        print(f"Fetch error: {error}")
    
    def _on_data_fetched(self, data: Dict):
        """Handle fetched data."""
        self.btn_refresh.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.nifty_data = data.get('nifty')
        self.ad_data = data.get('ad_data')
        self.gainers = data.get('gainers', [])
        self.losers = data.get('losers', [])
        self.distribution = data.get('distribution', {})
        
        timestamp = data.get('timestamp', datetime.now(IST))
        stock_count = data.get('stock_count', 0)
        
        # Update prev_close cache for future refreshes
        new_cache = data.get('prev_close_cache', {})
        if new_cache:
            self.prev_close_cache.update(new_cache)
        
        # Debug output
        print(f"[DEBUG] AD Data columns: {list(self.ad_data.columns) if self.ad_data is not None else 'None'}")
        print(f"[DEBUG] AD Data shape: {self.ad_data.shape if self.ad_data is not None else 'None'}")
        print(f"[DEBUG] Gainers count: {len(self.gainers)}, Losers count: {len(self.losers)}")
        print(f"[DEBUG] Distribution: {self.distribution}")
        if self.ad_data is not None and not self.ad_data.empty:
            print(f"[DEBUG] AD Data last row: {self.ad_data.iloc[-1].to_dict()}")
        
        # Update charts and tables
        self._update_charts()
        self._update_tables()
        self._update_summary()
        
        self.status_bar.showMessage(
            f"Last updated: {timestamp.strftime('%H:%M:%S')} IST | "
            f"NIFTY candles: {len(self.nifty_data) if self.nifty_data is not None else 0} | "
            f"Stocks tracked: {stock_count}"
        )
    
    def _update_charts(self):
        """Update both charts with synchronized data."""
        if self.nifty_data is None or self.nifty_data.empty:
            return
        
        # Clear existing items
        self.nifty_plot.clear()
        self.ad_plot.clear()
        
        # ─── NIFTY Candlestick Chart ───
        nifty_df = self.nifty_data.reset_index()
        
        # Debug: print columns to understand structure
        print(f"NIFTY columns after reset_index: {list(nifty_df.columns)}")
        
        # Handle various column structures from yfinance
        if 'index' in nifty_df.columns:
            nifty_df = nifty_df.rename(columns={'index': 'DateTime'})
        elif 'Datetime' in nifty_df.columns:
            nifty_df = nifty_df.rename(columns={'Datetime': 'DateTime'})
        elif nifty_df.columns[0] not in ['Open', 'High', 'Low', 'Close']:
            # First column is likely the datetime
            first_col = nifty_df.columns[0]
            nifty_df = nifty_df.rename(columns={first_col: 'DateTime'})
        
        print(f"NIFTY columns after rename: {list(nifty_df.columns)}")
        
        self.candlestick_item = CandlestickItem(nifty_df)
        self.nifty_plot.addItem(self.candlestick_item)
        
        # Add date labels on X axis
        self._setup_date_axis(self.nifty_plot, nifty_df['DateTime'])
        
        # Auto-range
        self.nifty_plot.autoRange()
        
        # ─── A/D Line Chart ───
        if self.ad_data is not None and not self.ad_data.empty:
            # Reset index to align with NIFTY
            ad_df = self.ad_data.reset_index()
            
            # Find the timestamp column (could be 'index', 'timestamp', or datetime-like)
            timestamp_col = ad_df.columns[0]  # First column after reset_index is the old index
            
            # Net A/D line
            x = np.arange(len(ad_df))
            y = ad_df['net'].values
            
            # Fill between zero and the line
            fill_brush_pos = pg.mkBrush(0, 200, 83, 50)
            fill_brush_neg = pg.mkBrush(255, 82, 82, 50)
            
            # Plot line
            pen = pg.mkPen(color='#00c853', width=2)
            self.ad_plot.plot(x, y, pen=pen, name='Net A/D')
            
            # Add zero line
            zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('#666666', width=1, style=Qt.PenStyle.DashLine))
            self.ad_plot.addItem(zero_line)
            
            # Fill areas
            pos_fill = pg.FillBetweenItem(
                pg.PlotDataItem(x, np.maximum(y, 0)),
                pg.PlotDataItem(x, np.zeros_like(y)),
                brush=fill_brush_pos
            )
            neg_fill = pg.FillBetweenItem(
                pg.PlotDataItem(x, np.minimum(y, 0)),
                pg.PlotDataItem(x, np.zeros_like(y)),
                brush=fill_brush_neg
            )
            self.ad_plot.addItem(pos_fill)
            self.ad_plot.addItem(neg_fill)
            
            # Setup same date axis
            self._setup_date_axis(self.ad_plot, ad_df[timestamp_col])
            
            self.ad_plot.autoRange()
    
    def _setup_date_axis(self, plot_widget, timestamps):
        """Setup date/time axis labels."""
        # Create tick labels at intervals
        n = len(timestamps)
        if n == 0:
            return
        
        # Show ~10 labels
        step = max(1, n // 10)
        ticks = []
        
        for i in range(0, n, step):
            ts = timestamps.iloc[i]
            if hasattr(ts, 'strftime'):
                label = ts.strftime('%H:%M\n%d-%b')
            else:
                label = str(ts)
            ticks.append((i, label))
        
        ax = plot_widget.getAxis('bottom')
        ax.setTicks([ticks])
    
    def _update_tables(self):
        """Update gainers and losers tables."""
        # Gainers
        self.gainers_table.setRowCount(len(self.gainers))
        for i, item in enumerate(self.gainers):
            self.gainers_table.setItem(i, 0, QTableWidgetItem(item['symbol']))
            self.gainers_table.setItem(i, 1, QTableWidgetItem(f"₹{item['current']:.2f}"))
            
            change_item = QTableWidgetItem(f"+{item['change']:.2f}%")
            change_item.setForeground(QColor(0, 200, 83))
            self.gainers_table.setItem(i, 2, change_item)
        
        # Losers
        self.losers_table.setRowCount(len(self.losers))
        for i, item in enumerate(self.losers):
            self.losers_table.setItem(i, 0, QTableWidgetItem(item['symbol']))
            self.losers_table.setItem(i, 1, QTableWidgetItem(f"₹{item['current']:.2f}"))
            
            change_item = QTableWidgetItem(f"{item['change']:.2f}%")
            change_item.setForeground(QColor(255, 82, 82))
            self.losers_table.setItem(i, 2, change_item)
        
        # Update Distribution
        if self.distribution:
            for key, label in self.dist_labels.items():
                count = self.distribution.get(key, 0)
                label.setText(str(count))
    
    def _update_summary(self):
        """Update summary labels."""
        # Update NIFTY price
        if self.nifty_data is not None and not self.nifty_data.empty:
            nifty_price = self.nifty_data['Close'].iloc[-1]
            nifty_open = self.nifty_data['Open'].iloc[0]
            nifty_change = ((nifty_price - nifty_open) / nifty_open) * 100
            
            if nifty_change >= 0:
                self.lbl_nifty.setText(f"NIFTY: {nifty_price:,.2f} (+{nifty_change:.2f}%)")
                self.lbl_nifty.setStyleSheet("color: #00c853; font-size: 14px; font-weight: bold;")
            else:
                self.lbl_nifty.setText(f"NIFTY: {nifty_price:,.2f} ({nifty_change:.2f}%)")
                self.lbl_nifty.setStyleSheet("color: #ff5252; font-size: 14px; font-weight: bold;")
        
        if self.ad_data is None or self.ad_data.empty:
            return
        
        # Get latest values
        latest = self.ad_data.iloc[-1]
        advances = int(latest['advances'])
        declines = int(latest['declines'])
        unchanged = int(latest['unchanged'])
        total = advances + declines + unchanged
        
        self.lbl_advances.setText(f"Advances: {advances}")
        self.lbl_declines.setText(f"Declines: {declines}")
        self.lbl_unchanged.setText(f"Unchanged: {unchanged}")
        self.lbl_total.setText(f"Total: {total}/500")
        
        if declines > 0:
            ratio = advances / declines
            self.lbl_ratio.setText(f"A/D Ratio: {ratio:.2f}")
        else:
            self.lbl_ratio.setText(f"A/D Ratio: ∞")
    
    def closeEvent(self, event):
        """Handle window close."""
        self.refresh_timer.stop()
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait()
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(13, 110, 253))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = RealtimeAdvDeclDashboardPyQt()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
