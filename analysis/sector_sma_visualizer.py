"""
Sector SMA Breadth Visualizer
=============================
Interactive GUI to analyze sector rotation and find leading stocks.

Features:
1. Sector Heatmap: Shows % above SMA for each sector over time
2. Sector Rankings: Current sector strength rankings
3. Recovery Leaders: Stocks that recently crossed above SMA in strong sectors
4. Relative Strength: Sector RS vs market
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# PyQtGraph imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QComboBox,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QSplitter, QFrame, QHeaderView, QCheckBox,
                             QDateEdit, QSpinBox, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush, QFont
import pyqtgraph as pg

from analysis.sector_sma_analysis import (
    get_engine, calculate_sector_breadth, get_sector_summary,
    find_recovery_leaders, find_weak_stocks_to_avoid,
    analyze_sector_rotation, calculate_sector_relative_strength,
    get_sector_stocks_detail
)
from analysis.sma_breadth_analysis import load_breadth_data as get_sma_breadth_data, get_nifty_index_data


class SectorBreadthVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = get_engine()
        self.sector_breadth_df = None
        self.market_breadth_df = None
        self.nifty_df = None
        
        self.setWindowTitle("Sector SMA Breadth Analysis - Sector Rotation & Stock Picker")
        self.setGeometry(100, 100, 1600, 900)
        
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        # SMA Period
        controls_layout.addWidget(QLabel("SMA Period:"))
        self.sma_combo = QComboBox()
        self.sma_combo.addItems(['5', '10', '20', '50', '100', '150', '200'])
        self.sma_combo.setCurrentText('50')
        self.sma_combo.currentTextChanged.connect(self._load_data)
        controls_layout.addWidget(self.sma_combo)
        
        # Date range
        controls_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate(2024, 1, 1))
        self.from_date.setCalendarPopup(True)
        controls_layout.addWidget(self.from_date)
        
        controls_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        controls_layout.addWidget(self.to_date)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.clicked.connect(self._load_data)
        controls_layout.addWidget(refresh_btn)
        
        controls_layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Loading...")
        controls_layout.addWidget(self.status_label)
        
        main_layout.addLayout(controls_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Sector Heatmap
        self._create_heatmap_tab()
        
        # Tab 2: Sector Rankings
        self._create_rankings_tab()
        
        # Tab 3: Recovery Leaders
        self._create_leaders_tab()
        
        # Tab 4: Sector Time Series
        self._create_timeseries_tab()
    
    def _create_heatmap_tab(self):
        """Create sector heatmap visualization."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Info label
        info = QLabel("📊 Sector Heatmap: Green = High % above SMA (strong), Red = Low % above SMA (weak)")
        info.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info)
        
        # Heatmap table
        self.heatmap_table = QTableWidget()
        self.heatmap_table.setAlternatingRowColors(False)
        layout.addWidget(self.heatmap_table)
        
        self.tabs.addTab(tab, "🗺️ Sector Heatmap")
    
    def _create_rankings_tab(self):
        """Create current sector rankings view with stock details on click."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Main vertical splitter - top for sector tables, bottom for stock details
        main_splitter = QSplitter(Qt.Vertical)
        
        # Top section: Sector rankings
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Horizontal splitter for strong/weak sectors
        sector_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Strong sectors
        strong_frame = QFrame()
        strong_layout = QVBoxLayout(strong_frame)
        strong_layout.addWidget(QLabel("🏆 STRONGEST SECTORS (Click to see stocks)"))
        self.strong_table = QTableWidget()
        self.strong_table.setColumnCount(4)
        self.strong_table.setHorizontalHeaderLabels(['Sector', '% Above SMA', 'Stocks Above', 'Total'])
        self.strong_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.strong_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.strong_table.setSelectionMode(QTableWidget.SingleSelection)
        self.strong_table.cellClicked.connect(self._on_strong_sector_clicked)
        strong_layout.addWidget(self.strong_table)
        sector_splitter.addWidget(strong_frame)
        
        # Right: Weak sectors
        weak_frame = QFrame()
        weak_layout = QVBoxLayout(weak_frame)
        weak_layout.addWidget(QLabel("⚠️ WEAKEST SECTORS (Click to see stocks)"))
        self.weak_table = QTableWidget()
        self.weak_table.setColumnCount(4)
        self.weak_table.setHorizontalHeaderLabels(['Sector', '% Above SMA', 'Stocks Above', 'Total'])
        self.weak_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.weak_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.weak_table.setSelectionMode(QTableWidget.SingleSelection)
        self.weak_table.cellClicked.connect(self._on_weak_sector_clicked)
        weak_layout.addWidget(self.weak_table)
        sector_splitter.addWidget(weak_frame)
        
        top_layout.addWidget(sector_splitter)
        main_splitter.addWidget(top_widget)
        
        # Bottom section: Stock details for selected sector
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stock_detail_label = QLabel("📋 Click on a sector above to see stock details")
        self.stock_detail_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px; background: #e0e0e0;")
        bottom_layout.addWidget(self.stock_detail_label)
        
        self.stock_detail_table = QTableWidget()
        self.stock_detail_table.setColumnCount(10)
        self.stock_detail_table.setHorizontalHeaderLabels([
            'Symbol', 'Company', 'Price', 
            '% from SMA10', 'Days', 
            '% from SMA50', 'Days',
            '% from SMA200', 'Days',
            'Status'
        ])
        self.stock_detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.stock_detail_table.setAlternatingRowColors(True)
        self.stock_detail_table.setSortingEnabled(True)
        bottom_layout.addWidget(self.stock_detail_table)
        
        main_splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes (60% sectors, 40% stock details)
        main_splitter.setSizes([400, 300])
        
        layout.addWidget(main_splitter)
        
        self.tabs.addTab(tab, "📊 Sector Rankings")
    
    def _on_strong_sector_clicked(self, row, col):
        """Handle click on strong sector table."""
        sector_item = self.strong_table.item(row, 0)
        if sector_item:
            self._show_sector_stocks(sector_item.text())
    
    def _on_weak_sector_clicked(self, row, col):
        """Handle click on weak sector table."""
        sector_item = self.weak_table.item(row, 0)
        if sector_item:
            self._show_sector_stocks(sector_item.text())
    
    def _show_sector_stocks(self, sector):
        """Show stocks in selected sector with SMA details."""
        self.status_label.setText(f"Loading stocks for {sector}...")
        QApplication.processEvents()
        
        try:
            sma_period = int(self.sma_combo.currentText())
            
            # Get detailed stock info
            df = get_sector_stocks_detail(
                self.engine, sector, 
                sma_periods=[10, 50, 200],
                log_cb=lambda x: None
            )
            
            if df.empty:
                self.stock_detail_label.setText(f"📋 No stock data found for {sector}")
                self.stock_detail_table.setRowCount(0)
                return
            
            self.stock_detail_label.setText(f"📋 {sector} - {len(df)} stocks (sorted by % from SMA50)")
            
            # Fill table
            self.stock_detail_table.setSortingEnabled(False)
            self.stock_detail_table.setRowCount(len(df))
            
            for i, (_, row) in enumerate(df.iterrows()):
                # Symbol
                self.stock_detail_table.setItem(i, 0, QTableWidgetItem(row['symbol']))
                
                # Company name (truncated)
                company = str(row.get('company_name', ''))[:30] if pd.notna(row.get('company_name')) else ''
                self.stock_detail_table.setItem(i, 1, QTableWidgetItem(company))
                
                # Price
                price_item = QTableWidgetItem(f"{row['close']:.2f}")
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.stock_detail_table.setItem(i, 2, price_item)
                
                # SMA 10
                pct_10 = row.get('pct_from_sma_10', 0)
                days_10 = row.get('days_above_sma_10', 0)
                self._set_sma_cell(i, 3, pct_10)
                self._set_days_cell(i, 4, days_10)
                
                # SMA 50
                pct_50 = row.get('pct_from_sma_50', 0)
                days_50 = row.get('days_above_sma_50', 0)
                self._set_sma_cell(i, 5, pct_50)
                self._set_days_cell(i, 6, days_50)
                
                # SMA 200
                pct_200 = row.get('pct_from_sma_200', 0)
                days_200 = row.get('days_above_sma_200', 0)
                self._set_sma_cell(i, 7, pct_200)
                self._set_days_cell(i, 8, days_200)
                
                # Status - determine trend
                status = self._get_stock_status(pct_10, pct_50, pct_200, days_50)
                status_item = QTableWidgetItem(status)
                if '🟢' in status:
                    status_item.setBackground(QBrush(QColor(200, 255, 200)))
                elif '🔴' in status:
                    status_item.setBackground(QBrush(QColor(255, 200, 200)))
                self.stock_detail_table.setItem(i, 9, status_item)
            
            self.stock_detail_table.setSortingEnabled(True)
            self.stock_detail_table.resizeColumnsToContents()
            
            self.status_label.setText(f"Loaded {len(df)} stocks for {sector}")
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _set_sma_cell(self, row, col, pct_value):
        """Set SMA percentage cell with color coding."""
        if pd.isna(pct_value):
            item = QTableWidgetItem("N/A")
        else:
            item = QTableWidgetItem(f"{pct_value:+.1f}%")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if pct_value > 5:
                item.setBackground(QBrush(QColor(144, 238, 144)))  # Light green
            elif pct_value > 0:
                item.setBackground(QBrush(QColor(200, 255, 200)))  # Very light green
            elif pct_value > -5:
                item.setBackground(QBrush(QColor(255, 230, 200)))  # Light orange
            else:
                item.setBackground(QBrush(QColor(255, 180, 180)))  # Light red
        
        self.stock_detail_table.setItem(row, col, item)
    
    def _set_days_cell(self, row, col, days_value):
        """Set days above/below SMA cell with color coding."""
        if pd.isna(days_value) or days_value == 0:
            item = QTableWidgetItem("0")
        else:
            days_int = int(days_value)
            if days_int > 0:
                item = QTableWidgetItem(f"↑{days_int}d")
                item.setForeground(QBrush(QColor(0, 128, 0)))  # Green text
            else:
                item = QTableWidgetItem(f"↓{abs(days_int)}d")
                item.setForeground(QBrush(QColor(180, 0, 0)))  # Red text
        
        item.setTextAlignment(Qt.AlignCenter)
        self.stock_detail_table.setItem(row, col, item)
    
    def _get_stock_status(self, pct_10, pct_50, pct_200, days_50):
        """Determine stock status based on SMA positions."""
        above_10 = pct_10 > 0 if pd.notna(pct_10) else False
        above_50 = pct_50 > 0 if pd.notna(pct_50) else False
        above_200 = pct_200 > 0 if pd.notna(pct_200) else False
        
        if above_10 and above_50 and above_200:
            if days_50 > 20:
                return "🟢 Strong Uptrend"
            else:
                return "🟢 Bullish"
        elif above_50 and above_200:
            return "🟡 Consolidating"
        elif above_200 and not above_50:
            return "🟡 Pullback"
        elif not above_50 and not above_200:
            if days_50 < -20:
                return "🔴 Strong Downtrend"
            else:
                return "🔴 Bearish"
        else:
            return "🟡 Mixed"
    
    def _create_leaders_tab(self):
        """Create stock picker / leaders view."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        
        ctrl_layout.addWidget(QLabel("Lookback Days:"))
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(5, 60)
        self.lookback_spin.setValue(10)
        ctrl_layout.addWidget(self.lookback_spin)
        
        find_btn = QPushButton("🔍 Find Leaders")
        find_btn.clicked.connect(self._find_leaders)
        ctrl_layout.addWidget(find_btn)
        
        find_weak_btn = QPushButton("⚠️ Find Weak Stocks")
        find_weak_btn.clicked.connect(self._find_weak)
        ctrl_layout.addWidget(find_weak_btn)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # Split into leaders and weak
        splitter = QSplitter(Qt.Horizontal)
        
        # Leaders table
        leaders_frame = QFrame()
        leaders_layout = QVBoxLayout(leaders_frame)
        leaders_layout.addWidget(QLabel("🎯 RECOVERY LEADERS (Recent SMA crossovers in strong sectors)"))
        self.leaders_table = QTableWidget()
        self.leaders_table.setColumnCount(6)
        self.leaders_table.setHorizontalHeaderLabels([
            'Symbol', 'Sector', 'Days Since Cross', 'Price', '% Above SMA', 'Sector Breadth'
        ])
        self.leaders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        leaders_layout.addWidget(self.leaders_table)
        splitter.addWidget(leaders_frame)
        
        # Weak stocks table
        weak_frame = QFrame()
        weak_layout = QVBoxLayout(weak_frame)
        weak_layout.addWidget(QLabel("❌ WEAK STOCKS TO AVOID (Below SMA in weak sectors)"))
        self.avoid_table = QTableWidget()
        self.avoid_table.setColumnCount(5)
        self.avoid_table.setHorizontalHeaderLabels([
            'Symbol', 'Sector', 'Price', '% Below SMA', 'Sector Breadth'
        ])
        self.avoid_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        weak_layout.addWidget(self.avoid_table)
        splitter.addWidget(weak_frame)
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(tab, "🎯 Stock Picker")
    
    def _create_timeseries_tab(self):
        """Create time series chart for sector comparison with Nifty overlay."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Sector selection
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("Select Sectors:"))
        
        self.sector_checks = {}
        sectors_container = QWidget()
        sectors_layout = QGridLayout(sectors_container)
        sectors_layout.setSpacing(5)
        
        # Will populate checkboxes after data loads
        self.sectors_container = sectors_container
        self.sectors_layout = sectors_layout
        ctrl_layout.addWidget(sectors_container)
        
        ctrl_layout.addStretch()
        
        # Show Nifty checkbox
        self.show_nifty_check = QCheckBox("Show NIFTY 50")
        self.show_nifty_check.setChecked(True)
        self.show_nifty_check.setStyleSheet("font-weight: bold; color: #d62728;")
        ctrl_layout.addWidget(self.show_nifty_check)
        
        update_btn = QPushButton("📈 Update Chart")
        update_btn.clicked.connect(self._update_sector_chart)
        ctrl_layout.addWidget(update_btn)
        
        layout.addLayout(ctrl_layout)
        
        # Use splitter for sector chart and Nifty chart
        chart_splitter = QSplitter(Qt.Vertical)
        
        # Sector % Above SMA Chart (top)
        self.sector_chart = pg.PlotWidget(title="Sector % Above SMA Over Time")
        self.sector_chart.setBackground('w')
        self.sector_chart.showGrid(x=True, y=True, alpha=0.3)
        self.sector_chart.setLabel('left', '% Above SMA')
        self.sector_chart.addLegend()
        
        # Add 50% reference line
        self.sector_chart.addLine(y=50, pen=pg.mkPen('#888888', width=1, style=Qt.DashLine))
        
        chart_splitter.addWidget(self.sector_chart)
        
        # Nifty 50 Index Chart (bottom)
        self.nifty_chart = pg.PlotWidget(title="NIFTY 50 Index")
        self.nifty_chart.setBackground('w')
        self.nifty_chart.showGrid(x=True, y=True, alpha=0.3)
        self.nifty_chart.setLabel('left', 'Price')
        self.nifty_chart.setLabel('bottom', 'Date')
        chart_splitter.addWidget(self.nifty_chart)
        
        # Set splitter sizes (70% sector, 30% nifty)
        chart_splitter.setSizes([700, 300])
        
        layout.addWidget(chart_splitter)
        
        # Link X axes for synchronized panning/zooming
        self.sector_chart.setXLink(self.nifty_chart)
        
        # Add crosshairs
        self._setup_crosshairs()
        
        # Status label for hover info
        self.chart_info_label = QLabel("Hover over chart to see values")
        self.chart_info_label.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(self.chart_info_label)
        
        self.tabs.addTab(tab, "📈 Sector Trends")
    
    def _setup_crosshairs(self):
        """Setup synchronized crosshairs for both charts."""
        # Crosshairs for sector chart
        self.vLine_sector = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1))
        self.hLine_sector = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=1))
        self.sector_chart.addItem(self.vLine_sector, ignoreBounds=True)
        self.sector_chart.addItem(self.hLine_sector, ignoreBounds=True)
        
        # Crosshairs for nifty chart
        self.vLine_nifty = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=1))
        self.hLine_nifty = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=1))
        self.nifty_chart.addItem(self.vLine_nifty, ignoreBounds=True)
        self.nifty_chart.addItem(self.hLine_nifty, ignoreBounds=True)
        
        # Connect mouse move events
        self.sector_chart.scene().sigMouseMoved.connect(self._mouse_moved_sector)
        self.nifty_chart.scene().sigMouseMoved.connect(self._mouse_moved_nifty)
    
    def _mouse_moved_sector(self, pos):
        """Handle mouse move on sector chart."""
        if self.sector_chart.sceneBoundingRect().contains(pos):
            mouse_point = self.sector_chart.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            # Update both crosshairs
            self.vLine_sector.setPos(x)
            self.hLine_sector.setPos(y)
            self.vLine_nifty.setPos(x)
            
            # Update info label
            self._update_chart_info(x, y, 'sector')
    
    def _mouse_moved_nifty(self, pos):
        """Handle mouse move on nifty chart."""
        if self.nifty_chart.sceneBoundingRect().contains(pos):
            mouse_point = self.nifty_chart.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            # Update both crosshairs
            self.vLine_nifty.setPos(x)
            self.hLine_nifty.setPos(y)
            self.vLine_sector.setPos(x)
            
            # Update info label
            self._update_chart_info(x, y, 'nifty')
    
    def _update_chart_info(self, x, y, source):
        """Update the info label with current position data."""
        try:
            idx = int(round(x))
            if self.sector_breadth_df is not None and not self.sector_breadth_df.empty:
                dates = sorted(self.sector_breadth_df['date'].unique())
                if 0 <= idx < len(dates):
                    date = dates[idx]
                    
                    # Get Nifty value at this date
                    nifty_val = ""
                    if hasattr(self, 'nifty_df') and self.nifty_df is not None:
                        nifty_row = self.nifty_df[self.nifty_df['date'] == date]
                        if not nifty_row.empty:
                            nifty_val = f" | NIFTY: {nifty_row['close'].values[0]:,.0f}"
                    
                    if source == 'sector':
                        self.chart_info_label.setText(f"Date: {date.strftime('%Y-%m-%d')} | % Above SMA: {y:.1f}%{nifty_val}")
                    else:
                        self.chart_info_label.setText(f"Date: {date.strftime('%Y-%m-%d')} | NIFTY: {y:,.0f}")
        except:
            pass
    
    def _load_data(self):
        """Load sector breadth data."""
        self.status_label.setText("Loading data...")
        QApplication.processEvents()
        
        try:
            sma_period = int(self.sma_combo.currentText())
            start_date = self.from_date.date().toString('yyyy-MM-dd')
            end_date = self.to_date.date().toString('yyyy-MM-dd')
            
            # Load sector breadth
            self.sector_breadth_df = calculate_sector_breadth(
                self.engine, 'NIFTY500', sma_period, start_date, 
                log_cb=lambda x: None
            )
            
            # Load market breadth for comparison
            self.market_breadth_df = get_sma_breadth_data(
                self.engine, 'NIFTY 500', start_date
            )
            if not self.market_breadth_df.empty:
                self.market_breadth_df = self.market_breadth_df[
                    self.market_breadth_df['sma_period'] == sma_period
                ]
            
            if self.sector_breadth_df.empty:
                self.status_label.setText("No data found")
                return
            
            # Filter by date range
            self.sector_breadth_df = self.sector_breadth_df[
                self.sector_breadth_df['date'] <= end_date
            ]
            
            # Update all views
            self._update_heatmap()
            self._update_rankings()
            self._setup_sector_checkboxes()
            
            record_count = len(self.sector_breadth_df)
            sectors = self.sector_breadth_df['sector'].nunique()
            self.status_label.setText(f"Loaded {record_count:,} records for {sectors} sectors")
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _update_heatmap(self):
        """Update sector heatmap table."""
        if self.sector_breadth_df is None or self.sector_breadth_df.empty:
            return
        
        # Pivot data: rows = sectors, columns = dates
        pivot = self.sector_breadth_df.pivot_table(
            index='sector', columns='date', values='pct_above', aggfunc='first'
        )
        
        # Sample dates if too many (show last 30 dates)
        if len(pivot.columns) > 30:
            pivot = pivot[pivot.columns[-30:]]
        
        self.heatmap_table.setRowCount(len(pivot))
        self.heatmap_table.setColumnCount(len(pivot.columns))
        
        # Set headers
        self.heatmap_table.setVerticalHeaderLabels(pivot.index.tolist())
        date_labels = [d.strftime('%m/%d') for d in pivot.columns]
        self.heatmap_table.setHorizontalHeaderLabels(date_labels)
        
        # Fill cells with color coding
        for i, sector in enumerate(pivot.index):
            for j, date in enumerate(pivot.columns):
                value = pivot.loc[sector, date]
                if pd.isna(value):
                    continue
                
                item = QTableWidgetItem(f"{value:.0f}")
                item.setTextAlignment(Qt.AlignCenter)
                
                # Color based on value (0-100)
                if value >= 70:
                    color = QColor(0, 180, 0)  # Strong green
                elif value >= 50:
                    color = QColor(144, 238, 144)  # Light green
                elif value >= 30:
                    color = QColor(255, 255, 150)  # Yellow
                elif value >= 15:
                    color = QColor(255, 180, 100)  # Orange
                else:
                    color = QColor(255, 100, 100)  # Red
                
                item.setBackground(QBrush(color))
                self.heatmap_table.setItem(i, j, item)
        
        self.heatmap_table.resizeColumnsToContents()
    
    def _update_rankings(self):
        """Update sector rankings tables."""
        if self.sector_breadth_df is None or self.sector_breadth_df.empty:
            return
        
        # Get latest date
        latest_date = self.sector_breadth_df['date'].max()
        latest = self.sector_breadth_df[
            self.sector_breadth_df['date'] == latest_date
        ].sort_values('pct_above', ascending=False)
        
        # Top half = strong sectors
        mid = len(latest) // 2
        strong = latest.head(mid)
        weak = latest.tail(mid)
        
        # Fill strong table
        self.strong_table.setRowCount(len(strong))
        for i, (_, row) in enumerate(strong.iterrows()):
            self.strong_table.setItem(i, 0, QTableWidgetItem(row['sector']))
            
            pct_item = QTableWidgetItem(f"{row['pct_above']:.1f}%")
            if row['pct_above'] >= 50:
                pct_item.setBackground(QBrush(QColor(144, 238, 144)))
            self.strong_table.setItem(i, 1, pct_item)
            
            self.strong_table.setItem(i, 2, QTableWidgetItem(str(int(row['stocks_above']))))
            self.strong_table.setItem(i, 3, QTableWidgetItem(str(int(row['total_stocks']))))
        
        # Fill weak table
        self.weak_table.setRowCount(len(weak))
        for i, (_, row) in enumerate(weak.iterrows()):
            self.weak_table.setItem(i, 0, QTableWidgetItem(row['sector']))
            
            pct_item = QTableWidgetItem(f"{row['pct_above']:.1f}%")
            if row['pct_above'] < 30:
                pct_item.setBackground(QBrush(QColor(255, 150, 150)))
            self.weak_table.setItem(i, 1, pct_item)
            
            self.weak_table.setItem(i, 2, QTableWidgetItem(str(int(row['stocks_above']))))
            self.weak_table.setItem(i, 3, QTableWidgetItem(str(int(row['total_stocks']))))
    
    def _setup_sector_checkboxes(self):
        """Setup sector selection checkboxes."""
        # Clear existing
        for cb in self.sector_checks.values():
            cb.deleteLater()
        self.sector_checks.clear()
        
        if self.sector_breadth_df is None:
            return
        
        sectors = sorted(self.sector_breadth_df['sector'].unique())
        
        # Top 5 sectors by latest breadth
        latest = self.sector_breadth_df[
            self.sector_breadth_df['date'] == self.sector_breadth_df['date'].max()
        ].sort_values('pct_above', ascending=False)
        top_5 = latest.head(5)['sector'].tolist()
        
        for i, sector in enumerate(sectors):
            cb = QCheckBox(sector[:20])  # Truncate long names
            cb.setChecked(sector in top_5)  # Pre-select top 5
            self.sector_checks[sector] = cb
            row = i // 4
            col = i % 4
            self.sectors_layout.addWidget(cb, row, col)
    
    def _update_sector_chart(self):
        """Update sector time series chart and Nifty chart."""
        self.sector_chart.clear()
        self.nifty_chart.clear()
        
        # Re-add crosshairs after clear
        self.sector_chart.addItem(self.vLine_sector, ignoreBounds=True)
        self.sector_chart.addItem(self.hLine_sector, ignoreBounds=True)
        self.nifty_chart.addItem(self.vLine_nifty, ignoreBounds=True)
        self.nifty_chart.addItem(self.hLine_nifty, ignoreBounds=True)
        
        # Re-add 50% line
        self.sector_chart.addLine(y=50, pen=pg.mkPen('#888888', width=1, style=Qt.DashLine))
        
        if self.sector_breadth_df is None:
            return
        
        # Get selected sectors
        selected = [s for s, cb in self.sector_checks.items() if cb.isChecked()]
        
        if not selected:
            return
        
        # Color palette
        colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
        ]
        
        legend = self.sector_chart.addLegend()
        
        # Get all unique dates for consistent x-axis
        dates = sorted(self.sector_breadth_df['date'].unique())
        date_to_idx = {d: i for i, d in enumerate(dates)}
        
        for i, sector in enumerate(selected):
            sector_data = self.sector_breadth_df[
                self.sector_breadth_df['sector'] == sector
            ].sort_values('date')
            
            if sector_data.empty:
                continue
            
            # Map dates to x indices
            x = [date_to_idx[d] for d in sector_data['date']]
            y = sector_data['pct_above'].values
            
            color = colors[i % len(colors)]
            self.sector_chart.plot(
                x, y, 
                pen=pg.mkPen(color, width=2),
                name=sector[:15]
            )
        
        # Set x-axis labels for sector chart
        tick_positions = list(range(0, len(dates), max(1, len(dates)//10)))
        tick_labels = [(i, dates[i].strftime('%m/%d')) for i in tick_positions if i < len(dates)]
        
        axis = self.sector_chart.getAxis('bottom')
        axis.setTicks([tick_labels])
        
        # Plot Nifty 50 Index
        if self.show_nifty_check.isChecked():
            self._update_nifty_chart(dates, date_to_idx, tick_labels)
    
    def _update_nifty_chart(self, dates, date_to_idx, tick_labels):
        """Update the Nifty 50 chart."""
        try:
            # Load Nifty data
            start_date = min(dates).strftime('%Y-%m-%d')
            self.nifty_df = get_nifty_index_data(self.engine, start_date=start_date, use_yahoo=True)
            
            if self.nifty_df.empty:
                return
            
            # Filter to matching dates
            self.nifty_df = self.nifty_df[self.nifty_df['date'].isin(dates)]
            
            if self.nifty_df.empty:
                return
            
            # Map dates to x indices
            x = [date_to_idx.get(d, 0) for d in self.nifty_df['date']]
            y = self.nifty_df['close'].values
            
            # Plot Nifty with distinctive style
            self.nifty_chart.plot(
                x, y,
                pen=pg.mkPen('#d62728', width=2),  # Red color for Nifty
                name='NIFTY 50'
            )
            
            # Set x-axis labels
            axis = self.nifty_chart.getAxis('bottom')
            axis.setTicks([tick_labels])
            
        except Exception as e:
            print(f"Error loading Nifty data: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_leaders(self):
        """Find and display recovery leaders."""
        self.status_label.setText("Finding leaders...")
        QApplication.processEvents()
        
        try:
            sma_period = int(self.sma_combo.currentText())
            lookback = self.lookback_spin.value()
            
            leaders = find_recovery_leaders(
                self.engine, sma_period, lookback, 
                log_cb=lambda x: None
            )
            
            if leaders.empty:
                self.status_label.setText("No leaders found")
                self.leaders_table.setRowCount(0)
                return
            
            # Fill table
            self.leaders_table.setRowCount(len(leaders))
            for i, (_, row) in enumerate(leaders.iterrows()):
                self.leaders_table.setItem(i, 0, QTableWidgetItem(row['symbol']))
                self.leaders_table.setItem(i, 1, QTableWidgetItem(row['sector']))
                self.leaders_table.setItem(i, 2, QTableWidgetItem(str(row['days_since_cross'])))
                self.leaders_table.setItem(i, 3, QTableWidgetItem(f"{row['current_price']:.2f}"))
                
                pct_item = QTableWidgetItem(f"+{row['pct_above_sma']:.1f}%")
                pct_item.setBackground(QBrush(QColor(144, 238, 144)))
                self.leaders_table.setItem(i, 4, pct_item)
                
                self.leaders_table.setItem(i, 5, QTableWidgetItem(f"{row['sector_breadth']:.1f}%"))
            
            self.status_label.setText(f"Found {len(leaders)} recovery leaders")
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _find_weak(self):
        """Find and display weak stocks to avoid."""
        self.status_label.setText("Finding weak stocks...")
        QApplication.processEvents()
        
        try:
            sma_period = int(self.sma_combo.currentText())
            
            weak = find_weak_stocks_to_avoid(
                self.engine, sma_period, 
                log_cb=lambda x: None
            )
            
            if weak.empty:
                self.status_label.setText("No weak stocks found")
                self.avoid_table.setRowCount(0)
                return
            
            # Fill table
            self.avoid_table.setRowCount(min(50, len(weak)))  # Limit to 50
            for i, (_, row) in enumerate(weak.head(50).iterrows()):
                self.avoid_table.setItem(i, 0, QTableWidgetItem(row['symbol']))
                self.avoid_table.setItem(i, 1, QTableWidgetItem(row['sector']))
                self.avoid_table.setItem(i, 2, QTableWidgetItem(f"{row['close']:.2f}"))
                
                pct_item = QTableWidgetItem(f"{row['pct_from_sma']:.1f}%")
                pct_item.setBackground(QBrush(QColor(255, 150, 150)))
                self.avoid_table.setItem(i, 3, pct_item)
                
                self.avoid_table.setItem(i, 4, QTableWidgetItem(f"{row['sector_breadth']:.1f}%"))
            
            self.status_label.setText(f"Found {len(weak)} weak stocks")
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = SectorBreadthVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
