#!/usr/bin/env python3
"""
Crypto Data Wizard
==================

PyQt6 wizard for syncing crypto data from Yahoo Finance.

Steps:
1. Setup & Sync Daily Quotes (10 years of data)
2. Calculate Moving Averages (EMA21, SMA5/10/20/50/150/200)
3. Calculate RSI (9 and 14 period)
4. Calculate Advance/Decline Breadth

Usage:
    python -m crypto.wizards.crypto_data_wizard
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
import yfinance as yf

from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QGroupBox,
    QCheckBox, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crypto.services.crypto_db_service import CryptoDBService
from crypto.data.crypto_symbols import TOP_100_CRYPTOS, get_yahoo_symbols

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Worker Threads ====================

class SyncDailyWorker(QThread):
    """Worker thread for syncing daily quotes."""
    progress = pyqtSignal(int, str)  # progress %, message
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, db: CryptoDBService, years: int = 10):
        super().__init__()
        self.db = db
        self.years = years
        self.cancelled = False
    
    def run(self):
        try:
            # Get symbol list
            symbols = TOP_100_CRYPTOS
            total = len(symbols)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.years * 365)
            
            self.progress.emit(0, f"Syncing {total} cryptos ({self.years} years)...")
            
            success_count = 0
            fail_count = 0
            all_data = []
            
            for i, (symbol, yahoo_symbol, name, category, rank) in enumerate(symbols):
                if self.cancelled:
                    self.finished.emit(False, "Cancelled by user")
                    return
                
                try:
                    # Download from Yahoo Finance
                    ticker = yf.Ticker(yahoo_symbol)
                    df = ticker.history(start=start_date, end=end_date, interval="1d")
                    
                    if df.empty:
                        fail_count += 1
                        self.progress.emit(int((i + 1) / total * 100), f"⚠️ {symbol}: No data")
                        continue
                    
                    # Clean and prepare dataframe
                    df = df.reset_index()
                    df['symbol'] = symbol
                    df['trade_date'] = pd.to_datetime(df['Date']).dt.date
                    df['open_price'] = df['Open']
                    df['high_price'] = df['High']
                    df['low_price'] = df['Low']
                    df['close_price'] = df['Close']
                    df['volume'] = df['Volume']
                    
                    # Calculate pct_change
                    df['pct_change'] = df['close_price'].pct_change() * 100
                    
                    # Select only needed columns
                    df = df[['symbol', 'trade_date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'pct_change']]
                    df = df.dropna(subset=['close_price'])
                    
                    # Replace inf/-inf with None (MySQL doesn't accept inf)
                    df = df.replace([np.inf, -np.inf], np.nan)
                    
                    all_data.append(df)
                    success_count += 1
                    
                    self.progress.emit(int((i + 1) / total * 100), f"✅ {symbol}: {len(df)} days")
                    
                except Exception as e:
                    fail_count += 1
                    self.progress.emit(int((i + 1) / total * 100), f"❌ {symbol}: {str(e)[:50]}")
            
            # Combine all data and upsert
            if all_data:
                self.progress.emit(95, "Saving to database...")
                combined_df = pd.concat(all_data, ignore_index=True)
                self.db.upsert_daily_quotes(combined_df)
            
            self.progress.emit(100, f"Complete: {success_count} success, {fail_count} failed")
            self.finished.emit(True, f"Synced {success_count} cryptos with {len(combined_df) if all_data else 0:,} total records")
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
            self.finished.emit(False, f"Error: {e}")
    
    def cancel(self):
        self.cancelled = True


class CalculateMAWorker(QThread):
    """Worker thread for calculating moving averages."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, db: CryptoDBService):
        super().__init__()
        self.db = db
        self.cancelled = False
    
    def run(self):
        try:
            # Get all active symbols from database
            symbols = self.db.get_active_symbols()
            total = len(symbols)
            
            self.progress.emit(0, f"Calculating MAs for {total} cryptos...")
            
            all_ma_data = []
            
            for i, sym_info in enumerate(symbols):
                if self.cancelled:
                    self.finished.emit(False, "Cancelled")
                    return
                
                symbol = sym_info['symbol']
                
                try:
                    # Get daily quotes for symbol
                    df = self.db.get_daily_quotes(symbol)
                    
                    if df.empty or len(df) < 5:
                        self.progress.emit(int((i + 1) / total * 100), f"⚠️ {symbol}: Insufficient data")
                        continue
                    
                    df = df.sort_values('trade_date')
                    
                    # Calculate moving averages
                    df['ema_21'] = df['close_price'].ewm(span=21, adjust=False).mean()
                    df['sma_5'] = df['close_price'].rolling(window=5).mean()
                    df['sma_10'] = df['close_price'].rolling(window=10).mean()
                    df['sma_20'] = df['close_price'].rolling(window=20).mean()
                    df['sma_50'] = df['close_price'].rolling(window=50).mean()
                    df['sma_150'] = df['close_price'].rolling(window=150).mean()
                    df['sma_200'] = df['close_price'].rolling(window=200).mean()
                    
                    # Calculate relative metrics
                    df['price_vs_sma50'] = ((df['close_price'] - df['sma_50']) / df['sma_50'] * 100).round(4)
                    df['price_vs_sma200'] = ((df['close_price'] - df['sma_200']) / df['sma_200'] * 100).round(4)
                    df['sma50_vs_sma200'] = ((df['sma_50'] - df['sma_200']) / df['sma_200'] * 100).round(4)
                    
                    # Select columns for MA table
                    ma_df = df[['symbol', 'trade_date', 'ema_21', 'sma_5', 'sma_10', 'sma_20', 
                               'sma_50', 'sma_150', 'sma_200', 'price_vs_sma50', 'price_vs_sma200', 'sma50_vs_sma200']].copy()
                    ma_df = ma_df.dropna(subset=['sma_5'])  # At least SMA5 should be valid
                    
                    # Replace inf/-inf with None (MySQL doesn't accept inf)
                    ma_df = ma_df.replace([np.inf, -np.inf], np.nan)
                    
                    all_ma_data.append(ma_df)
                    self.progress.emit(int((i + 1) / total * 100), f"✅ {symbol}: {len(ma_df)} records")
                    
                except Exception as e:
                    self.progress.emit(int((i + 1) / total * 100), f"❌ {symbol}: {str(e)[:40]}")
            
            # Save to database
            if all_ma_data:
                self.progress.emit(95, "Saving MAs to database...")
                combined_df = pd.concat(all_ma_data, ignore_index=True)
                self.db.upsert_moving_averages(combined_df)
            
            self.progress.emit(100, "MA calculation complete")
            self.finished.emit(True, f"Calculated MAs for {len(all_ma_data)} cryptos")
            
        except Exception as e:
            logger.error(f"MA calculation error: {e}")
            self.finished.emit(False, f"Error: {e}")
    
    def cancel(self):
        self.cancelled = True


class CalculateRSIWorker(QThread):
    """Worker thread for calculating RSI."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, db: CryptoDBService):
        super().__init__()
        self.db = db
        self.cancelled = False
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI for a price series."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _get_rsi_zone(self, rsi: float) -> str:
        """Classify RSI into zones."""
        if pd.isna(rsi):
            return 'neutral'
        if rsi < 30:
            return 'oversold'
        elif rsi > 70:
            return 'overbought'
        return 'neutral'
    
    def run(self):
        try:
            symbols = self.db.get_active_symbols()
            total = len(symbols)
            
            self.progress.emit(0, f"Calculating RSI for {total} cryptos...")
            
            all_rsi_data = []
            
            for i, sym_info in enumerate(symbols):
                if self.cancelled:
                    self.finished.emit(False, "Cancelled")
                    return
                
                symbol = sym_info['symbol']
                
                try:
                    df = self.db.get_daily_quotes(symbol)
                    
                    if df.empty or len(df) < 15:
                        self.progress.emit(int((i + 1) / total * 100), f"⚠️ {symbol}: Insufficient data")
                        continue
                    
                    df = df.sort_values('trade_date')
                    
                    # Calculate RSI
                    df['rsi_9'] = self._calculate_rsi(df['close_price'], 9)
                    df['rsi_14'] = self._calculate_rsi(df['close_price'], 14)
                    df['rsi_zone'] = df['rsi_14'].apply(self._get_rsi_zone)
                    
                    # Select columns
                    rsi_df = df[['symbol', 'trade_date', 'rsi_9', 'rsi_14', 'rsi_zone']].copy()
                    rsi_df = rsi_df.dropna(subset=['rsi_9'])
                    
                    # Replace inf/-inf with None (MySQL doesn't accept inf)
                    rsi_df = rsi_df.replace([np.inf, -np.inf], np.nan)
                    
                    all_rsi_data.append(rsi_df)
                    self.progress.emit(int((i + 1) / total * 100), f"✅ {symbol}: {len(rsi_df)} records")
                    
                except Exception as e:
                    self.progress.emit(int((i + 1) / total * 100), f"❌ {symbol}: {str(e)[:40]}")
            
            # Save to database
            if all_rsi_data:
                self.progress.emit(95, "Saving RSI to database...")
                combined_df = pd.concat(all_rsi_data, ignore_index=True)
                self.db.upsert_rsi(combined_df)
            
            self.progress.emit(100, "RSI calculation complete")
            self.finished.emit(True, f"Calculated RSI for {len(all_rsi_data)} cryptos")
            
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            self.finished.emit(False, f"Error: {e}")
    
    def cancel(self):
        self.cancelled = True


class CalculateADWorker(QThread):
    """Worker thread for calculating Advance/Decline breadth."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, db: CryptoDBService):
        super().__init__()
        self.db = db
        self.cancelled = False
    
    def run(self):
        try:
            # Get all unique dates from quotes
            with self.db.engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT DISTINCT trade_date FROM crypto_daily_quotes ORDER BY trade_date"))
                dates = [row[0] for row in result]
            
            total = len(dates)
            self.progress.emit(0, f"Calculating A/D for {total} trading days...")
            
            # Get starting A/D line value
            ad_line = self.db.get_latest_ad_line()
            
            for i, trade_date in enumerate(dates):
                if self.cancelled:
                    self.finished.emit(False, "Cancelled")
                    return
                
                try:
                    # Get all quotes for this date
                    df = self.db.get_quotes_for_date(trade_date)
                    
                    if df.empty:
                        continue
                    
                    # Filter out rows with no pct_change
                    df = df.dropna(subset=['pct_change'])
                    
                    # Calculate A/D metrics
                    advances = len(df[df['pct_change'] > 0.01])
                    declines = len(df[df['pct_change'] < -0.01])
                    unchanged = len(df) - advances - declines
                    total_coins = len(df)
                    
                    ad_ratio = advances / declines if declines > 0 else advances if advances > 0 else 1.0
                    ad_diff = advances - declines
                    ad_line += ad_diff
                    
                    # Distribution buckets
                    gain_0_1 = len(df[(df['pct_change'] > 0) & (df['pct_change'] <= 1)])
                    gain_1_2 = len(df[(df['pct_change'] > 1) & (df['pct_change'] <= 2)])
                    gain_2_3 = len(df[(df['pct_change'] > 2) & (df['pct_change'] <= 3)])
                    gain_3_5 = len(df[(df['pct_change'] > 3) & (df['pct_change'] <= 5)])
                    gain_5_10 = len(df[(df['pct_change'] > 5) & (df['pct_change'] <= 10)])
                    gain_10_plus = len(df[df['pct_change'] > 10])
                    
                    loss_0_1 = len(df[(df['pct_change'] < 0) & (df['pct_change'] >= -1)])
                    loss_1_2 = len(df[(df['pct_change'] < -1) & (df['pct_change'] >= -2)])
                    loss_2_3 = len(df[(df['pct_change'] < -2) & (df['pct_change'] >= -3)])
                    loss_3_5 = len(df[(df['pct_change'] < -3) & (df['pct_change'] >= -5)])
                    loss_5_10 = len(df[(df['pct_change'] < -5) & (df['pct_change'] >= -10)])
                    loss_10_plus = len(df[df['pct_change'] < -10])
                    
                    # Stats (filter out inf values for safety)
                    clean_pct = df['pct_change'].replace([np.inf, -np.inf], np.nan)
                    avg_change = clean_pct.mean()
                    median_change = clean_pct.median()
                    total_volume = df['volume'].sum()
                    
                    # Save to database
                    data = {
                        'trade_date': trade_date,
                        'advances': advances,
                        'declines': declines,
                        'unchanged': unchanged,
                        'total_coins': total_coins,
                        'ad_ratio': round(ad_ratio, 4),
                        'ad_diff': ad_diff,
                        'ad_line': round(ad_line, 4),
                        'gain_0_1': gain_0_1,
                        'gain_1_2': gain_1_2,
                        'gain_2_3': gain_2_3,
                        'gain_3_5': gain_3_5,
                        'gain_5_10': gain_5_10,
                        'gain_10_plus': gain_10_plus,
                        'loss_0_1': loss_0_1,
                        'loss_1_2': loss_1_2,
                        'loss_2_3': loss_2_3,
                        'loss_3_5': loss_3_5,
                        'loss_5_10': loss_5_10,
                        'loss_10_plus': loss_10_plus,
                        'avg_change': round(avg_change, 4) if not pd.isna(avg_change) else 0,
                        'median_change': round(median_change, 4) if not pd.isna(median_change) else 0,
                        'total_volume': total_volume if not pd.isna(total_volume) else 0
                    }
                    
                    self.db.upsert_advance_decline(data)
                    
                    if i % 50 == 0:  # Update progress every 50 days
                        self.progress.emit(int((i + 1) / total * 100), f"Processing {trade_date}: A{advances}/D{declines}")
                    
                except Exception as e:
                    logger.error(f"A/D error for {trade_date}: {e}")
            
            self.progress.emit(100, "A/D calculation complete")
            self.finished.emit(True, f"Calculated A/D for {total} trading days")
            
        except Exception as e:
            logger.error(f"A/D calculation error: {e}")
            self.finished.emit(False, f"Error: {e}")
    
    def cancel(self):
        self.cancelled = True


# ==================== Wizard Pages ====================

class IntroPage(QWizardPage):
    """Introduction page."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("🪙 Crypto Data Wizard")
        self.setSubTitle("Download and analyze Top 100 cryptocurrencies")
        
        layout = QVBoxLayout()
        
        # Info text
        info = QLabel("""
This wizard will:

<b>Step 1:</b> Download 10 years of daily OHLCV data for Top 100 cryptos
<b>Step 2:</b> Calculate Moving Averages (EMA21, SMA 5/10/20/50/150/200)
<b>Step 3:</b> Calculate RSI (9 and 14 period)
<b>Step 4:</b> Calculate Advance/Decline breadth data

<b>Data Source:</b> Yahoo Finance (free)
<b>Database:</b> crypto_marketdata (MySQL)
<b>Symbols:</b> 100 cryptocurrencies by market cap

Estimated time: 5-10 minutes (first run)
        """)
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)
        
        # Category breakdown
        from crypto.data.crypto_symbols import get_category_counts
        cats = get_category_counts()
        cat_text = "📊 <b>Symbols by Category:</b><br>"
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            cat_text += f"&nbsp;&nbsp;• {cat}: {count}<br>"
        
        cat_label = QLabel(cat_text)
        cat_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(cat_label)
        
        layout.addStretch()
        self.setLayout(layout)


class SyncPage(QWizardPage):
    """Sync daily quotes page."""
    
    def __init__(self, db: CryptoDBService, parent=None):
        super().__init__(parent)
        self.db = db
        self.worker: Optional[SyncDailyWorker] = None
        self.completed = False
        
        self.setTitle("Step 1: Sync Daily Quotes")
        self.setSubTitle("Download historical data from Yahoo Finance")
        
        layout = QVBoxLayout()
        
        # Options
        options_box = QGroupBox("Options")
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("Years of data:"))
        self.years_spin = QSpinBox()
        self.years_spin.setRange(1, 15)
        self.years_spin.setValue(10)
        options_layout.addWidget(self.years_spin)
        
        options_layout.addStretch()
        options_box.setLayout(options_layout)
        layout.addWidget(options_box)
        
        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("background-color: #1a1a1a; color: #00ff88; font-family: Consolas;")
        layout.addWidget(self.log_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start Sync")
        self.start_btn.clicked.connect(self.start_sync)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.clicked.connect(self.cancel_sync)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def start_sync(self):
        """Start the sync process."""
        # Ensure database and tables exist
        self.log_text.append("🔧 Setting up database...")
        self.db.ensure_database()
        self.db.ensure_tables()
        
        # Insert symbols
        self.log_text.append("📋 Loading symbol list...")
        self.db.insert_symbols(TOP_100_CRYPTOS)
        
        # Start worker
        self.worker = SyncDailyWorker(self.db, self.years_spin.value())
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.years_spin.setEnabled(False)
        
        self.worker.start()
    
    def cancel_sync(self):
        """Cancel the sync."""
        if self.worker:
            self.worker.cancel()
    
    def on_progress(self, pct: int, msg: str):
        """Handle progress updates."""
        self.progress_bar.setValue(pct)
        self.log_text.append(msg)
        # Auto-scroll
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def on_finished(self, success: bool, msg: str):
        """Handle completion."""
        self.log_text.append(f"\n{'✅' if success else '❌'} {msg}")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.years_spin.setEnabled(True)
        
        if success:
            self.completed = True
            self.completeChanged.emit()
    
    def isComplete(self) -> bool:
        return self.completed


class CalculateMAPage(QWizardPage):
    """Calculate moving averages page."""
    
    def __init__(self, db: CryptoDBService, parent=None):
        super().__init__(parent)
        self.db = db
        self.worker: Optional[CalculateMAWorker] = None
        self.completed = False
        
        self.setTitle("Step 2: Calculate Moving Averages")
        self.setSubTitle("EMA21, SMA 5/10/20/50/150/200")
        
        layout = QVBoxLayout()
        
        # Info
        info = QLabel("""
<b>Moving Averages to Calculate:</b>
• EMA 21 - Short-term trend
• SMA 5, 10, 20 - Short-term momentum  
• SMA 50 - Medium-term trend
• SMA 150, 200 - Long-term trend

Also calculates:
• Price vs SMA50 (%)
• Price vs SMA200 (%)
• SMA50 vs SMA200 (Golden/Death Cross)
        """)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)
        
        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("background-color: #1a1a1a; color: #00ff88; font-family: Consolas;")
        layout.addWidget(self.log_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Calculate MAs")
        self.start_btn.clicked.connect(self.start_calc)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.clicked.connect(self.cancel_calc)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def start_calc(self):
        self.worker = CalculateMAWorker(self.db)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()
    
    def cancel_calc(self):
        if self.worker:
            self.worker.cancel()
    
    def on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def on_finished(self, success: bool, msg: str):
        self.log_text.append(f"\n{'✅' if success else '❌'} {msg}")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            self.completed = True
            self.completeChanged.emit()
    
    def isComplete(self) -> bool:
        return self.completed


class CalculateRSIPage(QWizardPage):
    """Calculate RSI page."""
    
    def __init__(self, db: CryptoDBService, parent=None):
        super().__init__(parent)
        self.db = db
        self.worker: Optional[CalculateRSIWorker] = None
        self.completed = False
        
        self.setTitle("Step 3: Calculate RSI")
        self.setSubTitle("Relative Strength Index (9 and 14 period)")
        
        layout = QVBoxLayout()
        
        info = QLabel("""
<b>RSI Calculation:</b>
• RSI 9 - Short-term momentum
• RSI 14 - Standard momentum indicator

<b>Zones:</b>
• Oversold: RSI < 30
• Neutral: 30 ≤ RSI ≤ 70
• Overbought: RSI > 70
        """)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("background-color: #1a1a1a; color: #00ff88; font-family: Consolas;")
        layout.addWidget(self.log_text)
        
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Calculate RSI")
        self.start_btn.clicked.connect(self.start_calc)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.clicked.connect(self.cancel_calc)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def start_calc(self):
        self.worker = CalculateRSIWorker(self.db)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()
    
    def cancel_calc(self):
        if self.worker:
            self.worker.cancel()
    
    def on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def on_finished(self, success: bool, msg: str):
        self.log_text.append(f"\n{'✅' if success else '❌'} {msg}")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            self.completed = True
            self.completeChanged.emit()
    
    def isComplete(self) -> bool:
        return self.completed


class CalculateADPage(QWizardPage):
    """Calculate Advance/Decline page."""
    
    def __init__(self, db: CryptoDBService, parent=None):
        super().__init__(parent)
        self.db = db
        self.worker: Optional[CalculateADWorker] = None
        self.completed = False
        
        self.setTitle("Step 4: Calculate Advance/Decline")
        self.setSubTitle("Market breadth analysis")
        
        layout = QVBoxLayout()
        
        info = QLabel("""
<b>Breadth Indicators:</b>
• Advances / Declines / Unchanged count
• A/D Ratio and Cumulative A/D Line
• Distribution buckets by % change

<b>Use Cases:</b>
• Market sentiment analysis
• Divergence detection (price vs breadth)
• Turning point identification
        """)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("background-color: #1a1a1a; color: #00ff88; font-family: Consolas;")
        layout.addWidget(self.log_text)
        
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Calculate A/D")
        self.start_btn.clicked.connect(self.start_calc)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.clicked.connect(self.cancel_calc)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def start_calc(self):
        self.worker = CalculateADWorker(self.db)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()
    
    def cancel_calc(self):
        if self.worker:
            self.worker.cancel()
    
    def on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def on_finished(self, success: bool, msg: str):
        self.log_text.append(f"\n{'✅' if success else '❌'} {msg}")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            self.completed = True
            self.completeChanged.emit()
    
    def isComplete(self) -> bool:
        return self.completed


class SummaryPage(QWizardPage):
    """Summary page showing database stats."""
    
    def __init__(self, db: CryptoDBService, parent=None):
        super().__init__(parent)
        self.db = db
        
        self.setTitle("✅ Wizard Complete")
        self.setSubTitle("Crypto data is ready for analysis")
        
        layout = QVBoxLayout()
        
        # Stats table
        self.stats_table = QTableWidget(5, 2)
        self.stats_table.setHorizontalHeaderLabels(["Table", "Records"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setMaximumHeight(200)
        layout.addWidget(self.stats_table)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Stats")
        refresh_btn.clicked.connect(self.refresh_stats)
        layout.addWidget(refresh_btn)
        
        # Next steps
        next_steps = QLabel("""
<b>🎯 Next Steps:</b>
<ul>
<li>Use the Crypto Dashboard for real-time market overview</li>
<li>Use the Crypto A/D Visualizer for breadth analysis</li>
<li>Run the wizard periodically to keep data updated</li>
</ul>

<b>💡 Tip:</b> Add crypto tools to the launcher for quick access!
        """)
        next_steps.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(next_steps)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def initializePage(self):
        """Called when page is shown."""
        self.refresh_stats()
    
    def refresh_stats(self):
        """Refresh table statistics."""
        stats = self.db.get_table_stats()
        
        table_names = ["crypto_symbols", "crypto_daily_quotes", "crypto_daily_ma", "crypto_daily_rsi", "crypto_advance_decline"]
        
        for i, table in enumerate(table_names):
            self.stats_table.setItem(i, 0, QTableWidgetItem(table))
            count = stats.get(table, 0)
            self.stats_table.setItem(i, 1, QTableWidgetItem(f"{count:,}"))


# ==================== Main Wizard ====================

class CryptoDataWizard(QWizard):
    """Main wizard window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.db = CryptoDBService()
        
        self.setWindowTitle("🪙 Crypto Data Wizard")
        self.setMinimumSize(700, 600)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Apply dark theme
        self.setStyleSheet("""
            QWizard {
                background-color: #1e1e1e;
                color: white;
            }
            QWizardPage {
                background-color: #1e1e1e;
                color: white;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: white;
                border: 1px solid #444;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #00ff88;
            }
            QPushButton {
                background-color: #2d5a27;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3d7a37;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #888;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                background-color: #2a2a2a;
            }
            QProgressBar::chunk {
                background-color: #00ff88;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff88;
                border: 1px solid #444;
            }
            QSpinBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                padding: 5px;
            }
            QTableWidget {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #444;
                gridline-color: #333;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: white;
                padding: 5px;
                border: 1px solid #333;
            }
        """)
        
        # Add pages
        self.addPage(IntroPage(self))
        self.addPage(SyncPage(self.db, self))
        self.addPage(CalculateMAPage(self.db, self))
        self.addPage(CalculateRSIPage(self.db, self))
        self.addPage(CalculateADPage(self.db, self))
        self.addPage(SummaryPage(self.db, self))


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Apply dark palette
    from PyQt6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 90, 39))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    wizard = CryptoDataWizard()
    wizard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
