"""
Swing Trade Scanner GUI
=======================
Finds swing trade candidates based on sector strength and SMA analysis.

Long Candidates: Strong sectors, stocks crossing above SMA50
Short Candidates: Weak sectors, stocks below SMA50 and SMA200
"""

import sys
import os
# Add parent directory for imports when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QComboBox,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QSplitter, QFrame, QHeaderView, QCheckBox,
                             QSpinBox, QGroupBox, QGridLayout, QProgressBar,
                             QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont

from analysis.sector_sma_analysis import (
    get_engine, get_sector_summary, get_sector_stocks_detail,
    calculate_sector_breadth
)


class ScannerThread(QThread):
    """Background thread for scanning stocks."""
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(object, object)
    
    def __init__(self, engine, sma_period, min_days_cross, max_pct_from_sma):
        super().__init__()
        self.engine = engine
        self.sma_period = sma_period
        self.min_days_cross = min_days_cross
        self.max_pct_from_sma = max_pct_from_sma
    
    def _calculate_long_score(self, row, sector_breadth, max_sector_breadth):
        """
        Calculate a composite score (0-100) for long candidates.
        Higher score = better long setup.
        
        Factors:
        - Sector strength (25 pts): Higher % above SMA = better
        - Fresh crossover (25 pts): Fewer days = fresher setup
        - Entry proximity (25 pts): Closer to SMA50 = better entry
        - Trend confirmation (25 pts): Above SMA200 = confirmed uptrend
        """
        score = 0
        
        # 1. Sector Strength (25 pts) - normalize to 0-25
        # Sectors with >60% above SMA get max points
        sector_score = min(25, (sector_breadth / 60) * 25)
        score += sector_score
        
        # 2. Fresh Crossover (25 pts) - fewer days = higher score
        days = row.get('days_above_sma_50', 0)
        if days > 0:
            # 1 day = 25 pts, 15 days = 5 pts, 30+ days = 0 pts
            freshness_score = max(0, 25 - (days - 1) * 1.5)
            score += freshness_score
        
        # 3. Entry Proximity (25 pts) - closer to SMA50 = better
        pct_50 = row.get('pct_from_sma_50', 0)
        if pct_50 > 0:
            # 0-2% = 25 pts, 2-5% = 15 pts, 5-10% = 5 pts, >10% = 0 pts
            if pct_50 <= 2:
                proximity_score = 25
            elif pct_50 <= 5:
                proximity_score = 25 - (pct_50 - 2) * 3.3
            elif pct_50 <= 10:
                proximity_score = 15 - (pct_50 - 5) * 2
            else:
                proximity_score = max(0, 5 - (pct_50 - 10) * 0.5)
            score += proximity_score
        
        # 4. Trend Confirmation (25 pts) - above SMA200
        pct_200 = row.get('pct_from_sma_200', 0)
        if pct_200 > 0:
            # Above SMA200 = full points, bonus for higher
            trend_score = min(25, 15 + min(10, pct_200))
        elif pct_200 > -5:
            # Near SMA200 = partial points
            trend_score = 10 + pct_200
        else:
            trend_score = max(0, 5 + pct_200 / 2)
        score += trend_score
        
        return round(score, 1)
    
    def _calculate_short_score(self, row, sector_breadth):
        """
        Calculate a composite score (0-100) for short candidates.
        Higher score = better short setup.
        
        Factors:
        - Sector weakness (25 pts): Lower % above SMA = weaker sector
        - Persistent downtrend (25 pts): More days below = confirmed
        - Breakdown magnitude (25 pts): Further below SMA50 = stronger
        - Trend confirmation (25 pts): Below SMA200 = confirmed downtrend
        """
        score = 0
        
        # 1. Sector Weakness (25 pts) - lower breadth = higher score
        # Sectors with <20% above SMA get max points
        weakness_score = max(0, 25 - (sector_breadth / 2))
        score += weakness_score
        
        # 2. Persistent Downtrend (25 pts) - more days below = higher score
        days = row.get('days_above_sma_50', 0)
        if days < 0:
            # 10 days below = 10 pts, 30 days = 20 pts, 60+ days = 25 pts
            persistence_score = min(25, abs(days) * 0.4)
            score += persistence_score
        
        # 3. Breakdown Magnitude (25 pts) - further below SMA50 = higher score
        pct_50 = row.get('pct_from_sma_50', 0)
        if pct_50 < 0:
            # 5% below = 5 pts, 15% below = 15 pts, 30%+ below = 25 pts
            magnitude_score = min(25, abs(pct_50) * 0.8)
            score += magnitude_score
        
        # 4. Trend Confirmation (25 pts) - below SMA200
        pct_200 = row.get('pct_from_sma_200', 0)
        if pct_200 < 0:
            # Below SMA200 = confirms downtrend
            trend_score = min(25, 10 + abs(pct_200) * 0.5)
        elif pct_200 < 5:
            # Near SMA200 = partial points
            trend_score = max(0, 5 - pct_200)
        else:
            trend_score = 0
        score += trend_score
        
        return round(score, 1)
    
    def _get_rating_stars(self, score):
        """Convert score to star rating."""
        if score >= 80:
            return "★★★★★"
        elif score >= 65:
            return "★★★★☆"
        elif score >= 50:
            return "★★★☆☆"
        elif score >= 35:
            return "★★☆☆☆"
        elif score >= 20:
            return "★☆☆☆☆"
        else:
            return "☆☆☆☆☆"
    
    def run(self):
        try:
            self.progress.emit("Getting sector rankings...", 10)
            sector_summary = get_sector_summary(self.engine, sma_period=self.sma_period, log_cb=lambda x: None)
            
            if sector_summary.empty:
                self.finished.emit(pd.DataFrame(), pd.DataFrame())
                return
            
            # Split into strong and weak sectors
            mid = len(sector_summary) // 2
            strong_sectors = sector_summary.head(mid)['sector'].tolist()
            weak_sectors = sector_summary.tail(mid)['sector'].tolist()
            
            all_longs = []
            all_shorts = []
            
            total_sectors = len(strong_sectors) + len(weak_sectors)
            processed = 0
            
            # Scan strong sectors for longs
            for sector in strong_sectors:
                processed += 1
                pct = int(10 + (processed / total_sectors) * 80)
                self.progress.emit(f"Scanning {sector}...", pct)
                
                df = get_sector_stocks_detail(
                    self.engine, sector, 
                    sma_periods=[10, 20, 50, 200],
                    log_cb=lambda x: None
                )
                
                if df.empty:
                    continue
                
                # Get sector breadth
                sector_breadth = sector_summary[sector_summary['sector'] == sector]['pct_above'].values[0]
                
                # Long candidates criteria
                for _, row in df.iterrows():
                    pct_50 = row.get('pct_from_sma_50', 0)
                    pct_200 = row.get('pct_from_sma_200', 0)
                    days_50 = row.get('days_above_sma_50', 0)
                    pct_10 = row.get('pct_from_sma_10', 0)
                    
                    if pd.isna(pct_50) or pd.isna(pct_200):
                        continue
                    
                    # Fresh crossover or pullback to SMA50 with SMA200 support
                    is_fresh_cross = 0 < days_50 <= self.min_days_cross and pct_50 > 0 and pct_50 < self.max_pct_from_sma
                    is_pullback = pct_50 > 0 and pct_50 < 5 and pct_200 > 0 and days_50 > 0
                    
                    if is_fresh_cross or is_pullback:
                        setup = "Fresh SMA50 cross" if is_fresh_cross else "Pullback to SMA50"
                        
                        # Calculate score
                        max_breadth = sector_summary['pct_above'].max()
                        score = self._calculate_long_score(row, sector_breadth, max_breadth)
                        rating = self._get_rating_stars(score)
                        
                        all_longs.append({
                            'symbol': row['symbol'],
                            'company': row.get('company_name', '')[:25] if pd.notna(row.get('company_name')) else '',
                            'sector': sector,
                            'sector_breadth': sector_breadth,
                            'price': row['close'],
                            'pct_from_sma10': pct_10,
                            'pct_from_sma50': pct_50,
                            'days_above_sma50': days_50,
                            'pct_from_sma200': pct_200,
                            'setup': setup,
                            'score': score,
                            'rating': rating
                        })
            
            # Scan weak sectors for shorts
            for sector in weak_sectors:
                processed += 1
                pct = int(10 + (processed / total_sectors) * 80)
                self.progress.emit(f"Scanning {sector}...", pct)
                
                df = get_sector_stocks_detail(
                    self.engine, sector, 
                    sma_periods=[10, 20, 50, 200],
                    log_cb=lambda x: None
                )
                
                if df.empty:
                    continue
                
                # Get sector breadth
                sector_breadth = sector_summary[sector_summary['sector'] == sector]['pct_above'].values[0]
                
                # Short candidates criteria
                for _, row in df.iterrows():
                    pct_50 = row.get('pct_from_sma_50', 0)
                    pct_200 = row.get('pct_from_sma_200', 0)
                    days_50 = row.get('days_above_sma_50', 0)
                    pct_10 = row.get('pct_from_sma_10', 0)
                    
                    if pd.isna(pct_50) or pd.isna(pct_200):
                        continue
                    
                    # Below both SMAs with persistent weakness
                    if pct_50 < -5 and pct_200 < 0 and days_50 < -5:
                        if days_50 < -50:
                            setup = "Long-term downtrend"
                        elif days_50 < -20:
                            setup = "Persistent weakness"
                        else:
                            setup = "Recent breakdown"
                        
                        # Calculate score
                        score = self._calculate_short_score(row, sector_breadth)
                        rating = self._get_rating_stars(score)
                        
                        all_shorts.append({
                            'symbol': row['symbol'],
                            'company': row.get('company_name', '')[:25] if pd.notna(row.get('company_name')) else '',
                            'sector': sector,
                            'sector_breadth': sector_breadth,
                            'price': row['close'],
                            'pct_from_sma10': pct_10,
                            'pct_from_sma50': pct_50,
                            'days_above_sma50': days_50,
                            'pct_from_sma200': pct_200,
                            'setup': setup,
                            'score': score,
                            'rating': rating
                        })
            
            self.progress.emit("Calculating scores & ranking...", 95)
            
            # Convert to DataFrames and sort by score (highest first)
            longs_df = pd.DataFrame(all_longs)
            shorts_df = pd.DataFrame(all_shorts)
            
            if not longs_df.empty:
                longs_df = longs_df.sort_values('score', ascending=False)
            
            if not shorts_df.empty:
                shorts_df = shorts_df.sort_values('score', ascending=False)
            
            self.progress.emit("Done!", 100)
            self.finished.emit(longs_df, shorts_df)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(pd.DataFrame(), pd.DataFrame())


class SwingTradeScannerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = get_engine()
        self.longs_df = pd.DataFrame()
        self.shorts_df = pd.DataFrame()
        
        self.setWindowTitle("Swing Trade Scanner - Long & Short Candidates")
        self.setGeometry(100, 100, 1400, 800)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top controls
        controls_frame = QFrame()
        controls_frame.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 5px; padding: 5px; }")
        controls_layout = QHBoxLayout(controls_frame)
        
        # SMA Period
        controls_layout.addWidget(QLabel("SMA Period:"))
        self.sma_combo = QComboBox()
        self.sma_combo.addItems(['20', '50', '100', '200'])
        self.sma_combo.setCurrentText('50')
        controls_layout.addWidget(self.sma_combo)
        
        # Max days since crossover (for longs)
        controls_layout.addWidget(QLabel("Max Days Since Cross:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 30)
        self.days_spin.setValue(15)
        controls_layout.addWidget(self.days_spin)
        
        # Max % from SMA (for longs)
        controls_layout.addWidget(QLabel("Max % from SMA:"))
        self.pct_spin = QSpinBox()
        self.pct_spin.setRange(1, 20)
        self.pct_spin.setValue(10)
        controls_layout.addWidget(self.pct_spin)
        
        controls_layout.addStretch()
        
        # Scan button
        self.scan_btn = QPushButton("🔍 Scan for Trades")
        self.scan_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }")
        self.scan_btn.clicked.connect(self._run_scan)
        controls_layout.addWidget(self.scan_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(controls_frame)
        
        # Status label
        self.status_label = QLabel("Click 'Scan for Trades' to find swing trade candidates")
        self.status_label.setStyleSheet("font-style: italic; color: #666;")
        main_layout.addWidget(self.status_label)
        
        # Main content - tabs for Long and Short
        self.tabs = QTabWidget()
        
        # Long candidates tab
        long_tab = QWidget()
        long_layout = QVBoxLayout(long_tab)
        
        long_header = QLabel("🟢 LONG CANDIDATES - Strong sectors, stocks crossing above SMA")
        long_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2e7d32; padding: 5px;")
        long_layout.addWidget(long_header)
        
        self.long_table = QTableWidget()
        self.long_table.setColumnCount(12)
        self.long_table.setHorizontalHeaderLabels([
            'Score', 'Rating', 'Symbol', 'Company', 'Sector', 'Sector %', 'Price', 
            'SMA50 %', 'Days', 'SMA200 %', 'SMA10 %', 'Setup'
        ])
        self.long_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.long_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.long_table.setAlternatingRowColors(True)
        self.long_table.setSortingEnabled(True)
        long_layout.addWidget(self.long_table)
        
        self.tabs.addTab(long_tab, "🟢 Long Candidates")
        
        # Short candidates tab
        short_tab = QWidget()
        short_layout = QVBoxLayout(short_tab)
        
        short_header = QLabel("🔴 SHORT CANDIDATES - Weak sectors, stocks in downtrend")
        short_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #c62828; padding: 5px;")
        short_layout.addWidget(short_header)
        
        self.short_table = QTableWidget()
        self.short_table.setColumnCount(12)
        self.short_table.setHorizontalHeaderLabels([
            'Score', 'Rating', 'Symbol', 'Company', 'Sector', 'Sector %', 'Price', 
            'SMA50 %', 'Days', 'SMA200 %', 'SMA10 %', 'Setup'
        ])
        self.short_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.short_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.short_table.setAlternatingRowColors(True)
        self.short_table.setSortingEnabled(True)
        short_layout.addWidget(self.short_table)
        
        self.tabs.addTab(short_tab, "🔴 Short Candidates")
        
        # Summary tab
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        
        self.summary_label = QLabel("Run a scan to see summary")
        self.summary_label.setStyleSheet("font-size: 12px; padding: 10px;")
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        
        self.tabs.addTab(summary_tab, "📊 Summary")
        
        main_layout.addWidget(self.tabs)
    
    def _run_scan(self):
        """Run the swing trade scan."""
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Scanning...")
        
        sma_period = int(self.sma_combo.currentText())
        min_days = self.days_spin.value()
        max_pct = self.pct_spin.value()
        
        self.scanner_thread = ScannerThread(self.engine, sma_period, min_days, max_pct)
        self.scanner_thread.progress.connect(self._update_progress)
        self.scanner_thread.finished.connect(self._scan_finished)
        self.scanner_thread.start()
    
    def _update_progress(self, message, value):
        """Update progress bar and status."""
        self.status_label.setText(message)
        self.progress_bar.setValue(value)
    
    def _scan_finished(self, longs_df, shorts_df):
        """Handle scan completion."""
        self.longs_df = longs_df
        self.shorts_df = shorts_df
        
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Populate tables
        self._populate_long_table()
        self._populate_short_table()
        self._update_summary()
        
        self.status_label.setText(f"Found {len(longs_df)} long and {len(shorts_df)} short candidates")
        
        # Switch to long tab
        self.tabs.setCurrentIndex(0)
    
    def _populate_long_table(self):
        """Populate the long candidates table."""
        self.long_table.setSortingEnabled(False)
        self.long_table.setRowCount(len(self.longs_df))
        
        for i, (_, row) in enumerate(self.longs_df.iterrows()):
            col = 0
            
            # Score (sortable numeric)
            score = row.get('score', 0)
            score_item = QTableWidgetItem()
            score_item.setData(Qt.DisplayRole, score)
            score_item.setTextAlignment(Qt.AlignCenter)
            # Color based on score
            if score >= 70:
                score_item.setBackground(QBrush(QColor(0, 200, 0)))
                score_item.setForeground(QBrush(QColor(255, 255, 255)))
            elif score >= 50:
                score_item.setBackground(QBrush(QColor(144, 238, 144)))
            elif score >= 35:
                score_item.setBackground(QBrush(QColor(255, 255, 200)))
            self.long_table.setItem(i, col, score_item)
            col += 1
            
            # Rating (stars)
            rating_item = QTableWidgetItem(row.get('rating', ''))
            rating_item.setTextAlignment(Qt.AlignCenter)
            rating_item.setFont(QFont("Arial", 11))
            self.long_table.setItem(i, col, rating_item)
            col += 1
            
            # Symbol
            item = QTableWidgetItem(row['symbol'])
            item.setFont(QFont("Arial", 10, QFont.Bold))
            self.long_table.setItem(i, col, item)
            col += 1
            
            # Company
            self.long_table.setItem(i, col, QTableWidgetItem(str(row['company'])))
            col += 1
            
            # Sector
            self.long_table.setItem(i, col, QTableWidgetItem(row['sector'][:20]))
            col += 1
            
            # Sector breadth
            breadth_item = QTableWidgetItem(f"{row['sector_breadth']:.1f}%")
            breadth_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if row['sector_breadth'] > 50:
                breadth_item.setBackground(QBrush(QColor(200, 255, 200)))
            self.long_table.setItem(i, col, breadth_item)
            col += 1
            
            # Price
            price_item = QTableWidgetItem(f"{row['price']:.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.long_table.setItem(i, col, price_item)
            col += 1
            
            # SMA50 %
            self._set_pct_cell(self.long_table, i, col, row['pct_from_sma50'])
            col += 1
            
            # Days
            days = int(row['days_above_sma50'])
            days_item = QTableWidgetItem(f"↑{days}d")
            days_item.setTextAlignment(Qt.AlignCenter)
            days_item.setForeground(QBrush(QColor(0, 128, 0)))
            self.long_table.setItem(i, col, days_item)
            col += 1
            
            # SMA200 %
            self._set_pct_cell(self.long_table, i, col, row['pct_from_sma200'])
            col += 1
            
            # SMA10 %
            self._set_pct_cell(self.long_table, i, col, row.get('pct_from_sma10', 0))
            col += 1
            
            # Setup
            setup_item = QTableWidgetItem(row['setup'])
            if 'Fresh' in row['setup']:
                setup_item.setBackground(QBrush(QColor(255, 255, 200)))
            self.long_table.setItem(i, col, setup_item)
        
        self.long_table.setSortingEnabled(True)
        self.long_table.resizeColumnsToContents()
        
        # Update tab title
        self.tabs.setTabText(0, f"🟢 Long Candidates ({len(self.longs_df)})")
    
    def _populate_short_table(self):
        """Populate the short candidates table."""
        self.short_table.setSortingEnabled(False)
        self.short_table.setRowCount(len(self.shorts_df))
        
        for i, (_, row) in enumerate(self.shorts_df.iterrows()):
            col = 0
            
            # Score (sortable numeric)
            score = row.get('score', 0)
            score_item = QTableWidgetItem()
            score_item.setData(Qt.DisplayRole, score)
            score_item.setTextAlignment(Qt.AlignCenter)
            # Color based on score (red shades for shorts)
            if score >= 70:
                score_item.setBackground(QBrush(QColor(200, 0, 0)))
                score_item.setForeground(QBrush(QColor(255, 255, 255)))
            elif score >= 50:
                score_item.setBackground(QBrush(QColor(255, 150, 150)))
            elif score >= 35:
                score_item.setBackground(QBrush(QColor(255, 200, 200)))
            self.short_table.setItem(i, col, score_item)
            col += 1
            
            # Rating (stars)
            rating_item = QTableWidgetItem(row.get('rating', ''))
            rating_item.setTextAlignment(Qt.AlignCenter)
            rating_item.setFont(QFont("Arial", 11))
            self.short_table.setItem(i, col, rating_item)
            col += 1
            
            # Symbol
            item = QTableWidgetItem(row['symbol'])
            item.setFont(QFont("Arial", 10, QFont.Bold))
            self.short_table.setItem(i, col, item)
            col += 1
            
            # Company
            self.short_table.setItem(i, col, QTableWidgetItem(str(row['company'])))
            col += 1
            
            # Sector
            self.short_table.setItem(i, col, QTableWidgetItem(row['sector'][:20]))
            col += 1
            
            # Sector breadth
            breadth_item = QTableWidgetItem(f"{row['sector_breadth']:.1f}%")
            breadth_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if row['sector_breadth'] < 30:
                breadth_item.setBackground(QBrush(QColor(255, 200, 200)))
            self.short_table.setItem(i, col, breadth_item)
            col += 1
            
            # Price
            price_item = QTableWidgetItem(f"{row['price']:.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.short_table.setItem(i, col, price_item)
            col += 1
            
            # SMA50 %
            self._set_pct_cell(self.short_table, i, col, row['pct_from_sma50'])
            col += 1
            
            # Days
            days = int(row['days_above_sma50'])
            days_item = QTableWidgetItem(f"↓{abs(days)}d")
            days_item.setTextAlignment(Qt.AlignCenter)
            days_item.setForeground(QBrush(QColor(180, 0, 0)))
            self.short_table.setItem(i, col, days_item)
            col += 1
            
            # SMA200 %
            self._set_pct_cell(self.short_table, i, col, row['pct_from_sma200'])
            col += 1
            
            # SMA10 %
            self._set_pct_cell(self.short_table, i, col, row.get('pct_from_sma10', 0))
            col += 1
            
            # Setup
            setup_item = QTableWidgetItem(row['setup'])
            if 'Long-term' in row['setup']:
                setup_item.setBackground(QBrush(QColor(255, 200, 200)))
            self.short_table.setItem(i, col, setup_item)
        
        self.short_table.setSortingEnabled(True)
        self.short_table.resizeColumnsToContents()
        
        # Update tab title
        self.tabs.setTabText(1, f"🔴 Short Candidates ({len(self.shorts_df)})")
    
    def _set_pct_cell(self, table, row, col, value):
        """Set a percentage cell with color coding."""
        if pd.isna(value):
            item = QTableWidgetItem("N/A")
        else:
            item = QTableWidgetItem(f"{value:+.1f}%")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if value > 5:
                item.setBackground(QBrush(QColor(144, 238, 144)))
            elif value > 0:
                item.setBackground(QBrush(QColor(200, 255, 200)))
            elif value > -5:
                item.setBackground(QBrush(QColor(255, 230, 200)))
            else:
                item.setBackground(QBrush(QColor(255, 180, 180)))
        
        table.setItem(row, col, item)
    
    def _update_summary(self):
        """Update the summary tab."""
        summary_text = f"""
<h2>Swing Trade Scan Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>

<h3>🟢 Long Candidates: {len(self.longs_df)}</h3>
<p>Stocks in strong sectors that have recently crossed above SMA{self.sma_combo.currentText()} 
or are pulling back to support.</p>
"""
        if not self.longs_df.empty:
            summary_text += "<b>⭐ Top Rated Longs:</b><br>"
            top_longs = self.longs_df.nlargest(5, 'score')
            for _, row in top_longs.iterrows():
                summary_text += f"• <b>{row['symbol']}</b> ({row['sector'][:15]}) - Score: {row['score']:.0f} {row['rating']}<br>"
            
            summary_text += "<br><b>Top Sectors for Longs:</b><br>"
            sector_counts = self.longs_df['sector'].value_counts().head(5)
            for sector, count in sector_counts.items():
                summary_text += f"• {sector}: {count} stocks<br>"
        
        summary_text += f"""
<br>
<h3>🔴 Short Candidates: {len(self.shorts_df)}</h3>
<p>Stocks in weak sectors that are below both SMA50 and SMA200 with persistent weakness.</p>
"""
        if not self.shorts_df.empty:
            summary_text += "<b>⭐ Top Rated Shorts:</b><br>"
            top_shorts = self.shorts_df.nlargest(5, 'score')
            for _, row in top_shorts.iterrows():
                summary_text += f"• <b>{row['symbol']}</b> ({row['sector'][:15]}) - Score: {row['score']:.0f} {row['rating']}<br>"
            
            summary_text += "<br><b>Top Sectors for Shorts:</b><br>"
            sector_counts = self.shorts_df['sector'].value_counts().head(5)
            for sector, count in sector_counts.items():
                summary_text += f"• {sector}: {count} stocks<br>"
        
        summary_text += """
<br>
<h3>📊 Score Breakdown (0-100 points):</h3>
<table border="1" cellpadding="5">
<tr><th>Factor</th><th>Long Score</th><th>Short Score</th></tr>
<tr><td>Sector Strength/Weakness</td><td>25 pts - Higher % above SMA</td><td>25 pts - Lower % above SMA</td></tr>
<tr><td>Entry Timing</td><td>25 pts - Fewer days since cross</td><td>25 pts - More days in downtrend</td></tr>
<tr><td>Entry Proximity</td><td>25 pts - Closer to SMA50</td><td>25 pts - Further below SMA50</td></tr>
<tr><td>Trend Confirmation</td><td>25 pts - Above SMA200</td><td>25 pts - Below SMA200</td></tr>
</table>

<br>
<h3>⭐ Rating Guide:</h3>
<ul>
<li>★★★★★ (80-100): Excellent setup - high conviction</li>
<li>★★★★☆ (65-79): Strong setup - good candidate</li>
<li>★★★☆☆ (50-64): Decent setup - worth watching</li>
<li>★★☆☆☆ (35-49): Weak setup - needs more confirmation</li>
<li>★☆☆☆☆ (20-34): Poor setup - avoid</li>
</ul>

<h3>📋 Trading Notes:</h3>
<ul>
<li><b>Long Entry:</b> Buy on pullbacks to SMA50, stop-loss below SMA50</li>
<li><b>Short Entry:</b> Short on rallies to SMA50, stop-loss above SMA50</li>
<li><b>Fresh Cross:</b> Stock just crossed above SMA - early entry opportunity</li>
<li><b>Pullback:</b> Stock pulling back to SMA support - safer entry</li>
<li><b>Days:</b> ↑ = days above SMA, ↓ = days below SMA</li>
</ul>
"""
        
        self.summary_label.setText(summary_text)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = SwingTradeScannerGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
