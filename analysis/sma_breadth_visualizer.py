"""
SMA Breadth Visualizer
======================

Interactive visualization of percentage of stocks above various SMAs.
Compare with Nifty index to identify market turning points.

Features:
- Multi-SMA comparison (5, 10, 20, 50, 100, 150, 200)
- Nifty 50 vs Nifty 500 breadth
- Nifty index overlay
- Peak and trough markers
- Predictive power analysis

Author: Stock Screener Project
Date: 2025-12-07
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QCheckBox, QGroupBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QStatusBar, QFrame, QGridLayout, QSpinBox, QDateEdit
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont, QColor

import pyqtgraph as pg
from pyqtgraph import DateAxisItem

from analysis.sma_breadth_analysis import (
    get_engine, SMA_PERIODS, SMA_COLUMNS,
    load_breadth_data, get_nifty_index_data,
    detect_peaks_troughs, analyze_predictive_power,
    run_full_calculation
)

# Configure PyQtGraph
pg.setConfigOptions(antialias=True, background='w', foreground='k')


# ============================================================================
# Color Scheme
# ============================================================================

SMA_COLORS = {
    5: '#E91E63',    # Pink
    10: '#9C27B0',   # Purple
    20: '#3F51B5',   # Indigo
    50: '#2196F3',   # Blue
    100: '#009688',  # Teal
    150: '#4CAF50',  # Green
    200: '#FF9800',  # Orange
}

NIFTY_COLOR = '#212121'  # Dark gray for Nifty line
PEAK_COLOR = '#F44336'   # Red for peaks
TROUGH_COLOR = '#4CAF50' # Green for troughs


# ============================================================================
# Main Visualizer Window
# ============================================================================

class SMABreadthVisualizer(QMainWindow):
    """Main window for SMA breadth visualization."""
    
    def __init__(self):
        super().__init__()
        self.engine = get_engine()
        self.breadth_data = {}
        self.nifty_data = None
        self.current_index = 'NIFTY 500'
        
        self.setWindowTitle("📊 SMA Breadth Analysis - Market Turn Prediction")
        self.setGeometry(100, 100, 1600, 900)
        
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """Initialize the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Top controls
        controls = self._create_controls()
        layout.addWidget(controls)
        
        # Main content with tabs
        tabs = QTabWidget()
        
        # Tab 1: Multi-SMA Comparison
        tab1 = self._create_comparison_tab()
        tabs.addTab(tab1, "📈 SMA Comparison")
        
        # Tab 2: Single SMA Detail
        tab2 = self._create_detail_tab()
        tabs.addTab(tab2, "🔍 SMA Detail")
        
        # Tab 3: Predictive Analysis
        tab3 = self._create_analysis_tab()
        tabs.addTab(tab3, "🎯 Turn Prediction")
        
        # Tab 4: Data Table
        tab4 = self._create_data_tab()
        tabs.addTab(tab4, "📋 Data Table")
        
        layout.addWidget(tabs, 1)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def _create_controls(self) -> QWidget:
        """Create top control panel."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(frame)
        
        # Index selector
        layout.addWidget(QLabel("Index:"))
        self.index_combo = QComboBox()
        self.index_combo.addItems(['NIFTY 500', 'NIFTY 50'])
        self.index_combo.currentTextChanged.connect(self._on_index_changed)
        layout.addWidget(self.index_combo)
        
        layout.addSpacing(20)
        
        # Date range
        layout.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-12))
        self.start_date.dateChanged.connect(self._on_date_changed)
        layout.addWidget(self.start_date)
        
        layout.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self._on_date_changed)
        layout.addWidget(self.end_date)
        
        layout.addSpacing(20)
        
        # SMA checkboxes
        layout.addWidget(QLabel("SMAs:"))
        self.sma_checks = {}
        for period in SMA_PERIODS:
            cb = QCheckBox(str(period))
            cb.setChecked(period in [20, 50, 200])  # Default selection
            cb.stateChanged.connect(self._on_sma_changed)
            cb.setStyleSheet(f"color: {SMA_COLORS[period]};")
            self.sma_checks[period] = cb
            layout.addWidget(cb)
        
        layout.addSpacing(20)
        
        # Show peaks/troughs
        self.show_peaks = QCheckBox("Show Peaks/Troughs")
        self.show_peaks.setChecked(True)
        self.show_peaks.stateChanged.connect(self._update_charts)
        layout.addWidget(self.show_peaks)
        
        layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.clicked.connect(self._refresh_data)
        layout.addWidget(refresh_btn)
        
        # Recalculate button
        recalc_btn = QPushButton("⚡ Recalculate")
        recalc_btn.clicked.connect(self._recalculate_data)
        layout.addWidget(recalc_btn)
        
        return frame
    
    def _create_comparison_tab(self) -> QWidget:
        """Create multi-SMA comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create plot widget with custom date axis
        date_axis = DateAxisItem(orientation='bottom')
        self.comparison_plot = pg.PlotWidget(
            title="Percentage of Stocks Above SMA",
            axisItems={'bottom': date_axis}
        )
        self.comparison_plot.setLabel('left', '% Above SMA')
        self.comparison_plot.setLabel('bottom', 'Date')
        self.comparison_plot.addLegend()
        self.comparison_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Add crosshair (thicker lines for visibility)
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=2))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=2))
        self.comparison_plot.addItem(self.vLine, ignoreBounds=True)
        self.comparison_plot.addItem(self.hLine, ignoreBounds=True)
        
        # Mouse tracking for crosshair
        self.comparison_plot.scene().sigMouseMoved.connect(self._mouse_moved)
        
        layout.addWidget(self.comparison_plot, 2)
        
        # Nifty index chart (smaller, below)
        date_axis2 = DateAxisItem(orientation='bottom')
        self.nifty_plot = pg.PlotWidget(
            title="NIFTY 50 Index",
            axisItems={'bottom': date_axis2}
        )
        self.nifty_plot.setLabel('left', 'Price')
        self.nifty_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Link X axes
        self.nifty_plot.setXLink(self.comparison_plot)
        
        # Add crosshair to Nifty plot (synchronized, thicker lines)
        self.vLine_nifty = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#555555', width=2))
        self.hLine_nifty = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#555555', width=2))
        self.nifty_plot.addItem(self.vLine_nifty, ignoreBounds=True)
        self.nifty_plot.addItem(self.hLine_nifty, ignoreBounds=True)
        
        # Mouse tracking for Nifty plot crosshair
        self.nifty_plot.scene().sigMouseMoved.connect(self._mouse_moved_nifty)
        
        layout.addWidget(self.nifty_plot, 1)
        
        # Info label
        self.info_label = QLabel("Hover over chart for details")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 12px; padding: 5px; background: #f5f5f5;")
        layout.addWidget(self.info_label)
        
        return widget
    
    def _create_detail_tab(self) -> QWidget:
        """Create single SMA detail tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("Select SMA:"))
        
        self.detail_sma_combo = QComboBox()
        self.detail_sma_combo.addItems([str(p) for p in SMA_PERIODS])
        self.detail_sma_combo.setCurrentText('50')
        self.detail_sma_combo.currentTextChanged.connect(self._update_detail_chart)
        ctrl_layout.addWidget(self.detail_sma_combo)
        
        ctrl_layout.addSpacing(20)
        
        ctrl_layout.addWidget(QLabel("Peak Detection Window:"))
        self.peak_window = QSpinBox()
        self.peak_window.setRange(3, 20)
        self.peak_window.setValue(5)
        self.peak_window.valueChanged.connect(self._update_detail_chart)
        ctrl_layout.addWidget(self.peak_window)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # Detail chart
        date_axis = DateAxisItem(orientation='bottom')
        self.detail_plot = pg.PlotWidget(
            axisItems={'bottom': date_axis}
        )
        self.detail_plot.setLabel('left', '% Above SMA')
        self.detail_plot.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.detail_plot, 2)
        
        # Nifty overlay
        date_axis2 = DateAxisItem(orientation='bottom')
        self.detail_nifty_plot = pg.PlotWidget(
            title="NIFTY 50 with Turning Points",
            axisItems={'bottom': date_axis2}
        )
        self.detail_nifty_plot.showGrid(x=True, y=True, alpha=0.3)
        self.detail_nifty_plot.setXLink(self.detail_plot)
        layout.addWidget(self.detail_nifty_plot, 1)
        
        # Stats table
        self.detail_stats = QTableWidget()
        self.detail_stats.setMaximumHeight(150)
        layout.addWidget(self.detail_stats)
        
        return widget
    
    def _create_analysis_tab(self) -> QWidget:
        """Create predictive analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Description
        desc = QLabel(
            "📊 <b>Market Turn Prediction Analysis</b><br>"
            "This analysis tests which SMA breadth indicator best predicts market turns.<br>"
            "• <b>Peaks</b> in % above SMA may indicate market tops (overbought)<br>"
            "• <b>Troughs</b> in % above SMA may indicate market bottoms (oversold)"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("padding: 10px; background: #e3f2fd; border-radius: 5px;")
        layout.addWidget(desc)
        
        # Analysis controls
        ctrl = QHBoxLayout()
        
        run_btn = QPushButton("🔬 Run Analysis")
        run_btn.clicked.connect(self._run_prediction_analysis)
        ctrl.addWidget(run_btn)
        
        ctrl.addStretch()
        layout.addLayout(ctrl)
        
        # Results table
        self.analysis_table = QTableWidget()
        self.analysis_table.setColumnCount(9)
        self.analysis_table.setHorizontalHeaderLabels([
            'SMA', 'Forward Days', 'Term', '# Peaks', '# Troughs',
            'Avg Return After Peak', '% Decline After Peak',
            'Avg Return After Trough', '% Rally After Trough'
        ])
        self.analysis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.analysis_table)
        
        # Summary
        self.analysis_summary = QLabel("")
        self.analysis_summary.setWordWrap(True)
        self.analysis_summary.setStyleSheet("padding: 10px; background: #fff3e0; border-radius: 5px;")
        layout.addWidget(self.analysis_summary)
        
        return widget
    
    def _create_data_tab(self) -> QWidget:
        """Create data table tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter controls
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("SMA Filter:"))
        
        self.data_sma_combo = QComboBox()
        self.data_sma_combo.addItem("All SMAs")
        self.data_sma_combo.addItems([str(p) for p in SMA_PERIODS])
        self.data_sma_combo.currentTextChanged.connect(self._update_data_table)
        ctrl.addWidget(self.data_sma_combo)
        
        ctrl.addStretch()
        
        export_btn = QPushButton("📤 Export CSV")
        export_btn.clicked.connect(self._export_csv)
        ctrl.addWidget(export_btn)
        
        layout.addLayout(ctrl)
        
        # Data table
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(8)
        self.data_table.setHorizontalHeaderLabels([
            'Date', 'Index', 'SMA', 'Total Stocks', 'Above', 'Below', '% Above', '% Below'
        ])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setSortingEnabled(True)
        layout.addWidget(self.data_table)
        
        return widget
    
    # ========================================================================
    # Data Loading
    # ========================================================================
    
    def _load_data(self):
        """Load data from database."""
        self.statusBar.showMessage("Loading data...")
        
        try:
            start = self.start_date.date().toString('yyyy-MM-dd')
            end = self.end_date.date().toString('yyyy-MM-dd')
            
            # Load breadth data for both indices
            for idx in ['NIFTY 500', 'NIFTY 50']:
                self.breadth_data[idx] = load_breadth_data(
                    self.engine, idx, start_date=start, end_date=end
                )
            
            # Load Nifty index data
            self.nifty_data = get_nifty_index_data(self.engine, start, end)
            
            self._update_charts()
            self._update_data_table()
            
            total = sum(len(df) for df in self.breadth_data.values())
            self.statusBar.showMessage(f"Loaded {total:,} records")
            
        except Exception as e:
            self.statusBar.showMessage(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _refresh_data(self):
        """Refresh data from database."""
        self._load_data()
    
    def _recalculate_data(self):
        """Recalculate breadth data."""
        self.statusBar.showMessage("Recalculating... This may take a minute.")
        QApplication.processEvents()
        
        try:
            run_full_calculation(self.engine, 'NIFTY 500')
            run_full_calculation(self.engine, 'NIFTY 50')
            self._load_data()
            self.statusBar.showMessage("Recalculation complete!")
        except Exception as e:
            self.statusBar.showMessage(f"Error: {str(e)}")
    
    # ========================================================================
    # Chart Updates
    # ========================================================================
    
    def _update_charts(self):
        """Update all charts."""
        self._update_comparison_chart()
        self._update_detail_chart()
    
    def _update_comparison_chart(self):
        """Update the comparison chart."""
        self.comparison_plot.clear()
        self.comparison_plot.addItem(self.vLine, ignoreBounds=True)
        self.comparison_plot.addItem(self.hLine, ignoreBounds=True)
        
        df = self.breadth_data.get(self.current_index)
        if df is None or df.empty:
            return
        
        # Plot selected SMAs
        for period in SMA_PERIODS:
            if not self.sma_checks[period].isChecked():
                continue
            
            sma_df = df[df['sma_period'] == period].copy()
            if sma_df.empty:
                continue
            
            # Convert dates to timestamps
            x = np.array([d.timestamp() for d in sma_df['date']])
            y = sma_df['pct_above'].values
            
            color = SMA_COLORS[period]
            self.comparison_plot.plot(
                x, y, pen=pg.mkPen(color, width=2),
                name=f'SMA {period}'
            )
            
            # Add peaks and troughs if enabled
            if self.show_peaks.isChecked():
                sma_df = detect_peaks_troughs(sma_df, 'pct_above', window=5)
                
                # Plot peaks
                peaks = sma_df[sma_df['is_significant_peak']]
                if not peaks.empty:
                    px = np.array([d.timestamp() for d in peaks['date']])
                    py = peaks['pct_above'].values
                    self.comparison_plot.plot(
                        px, py, pen=None,
                        symbol='t', symbolBrush=PEAK_COLOR, symbolSize=10
                    )
                
                # Plot troughs
                troughs = sma_df[sma_df['is_significant_trough']]
                if not troughs.empty:
                    tx = np.array([d.timestamp() for d in troughs['date']])
                    ty = troughs['pct_above'].values
                    self.comparison_plot.plot(
                        tx, ty, pen=None,
                        symbol='t1', symbolBrush=TROUGH_COLOR, symbolSize=10
                    )
        
        # Add reference lines
        self.comparison_plot.addLine(y=50, pen=pg.mkPen('gray', width=1, style=Qt.DashLine))
        self.comparison_plot.addLine(y=80, pen=pg.mkPen(PEAK_COLOR, width=1, style=Qt.DotLine))
        self.comparison_plot.addLine(y=20, pen=pg.mkPen(TROUGH_COLOR, width=1, style=Qt.DotLine))
        
        # Update Nifty chart
        self._update_nifty_chart()
    
    def _update_nifty_chart(self):
        """Update the Nifty index chart."""
        self.nifty_plot.clear()
        
        # Re-add crosshair lines after clearing (clear() removes all items)
        self.nifty_plot.addItem(self.vLine_nifty, ignoreBounds=True)
        self.nifty_plot.addItem(self.hLine_nifty, ignoreBounds=True)
        
        if self.nifty_data is None or self.nifty_data.empty:
            return
        
        x = np.array([d.timestamp() for d in self.nifty_data['date']])
        y = self.nifty_data['close'].values
        
        self.nifty_plot.plot(x, y, pen=pg.mkPen(NIFTY_COLOR, width=2))
    
    def _update_detail_chart(self):
        """Update the detail chart."""
        self.detail_plot.clear()
        self.detail_nifty_plot.clear()
        
        df = self.breadth_data.get(self.current_index)
        if df is None or df.empty:
            return
        
        period = int(self.detail_sma_combo.currentText())
        sma_df = df[df['sma_period'] == period].copy()
        
        if sma_df.empty:
            return
        
        # Plot SMA breadth
        x = np.array([d.timestamp() for d in sma_df['date']])
        y = sma_df['pct_above'].values
        
        color = SMA_COLORS[period]
        self.detail_plot.plot(x, y, pen=pg.mkPen(color, width=2))
        self.detail_plot.setTitle(f"% Stocks Above SMA {period} - {self.current_index}")
        
        # Detect peaks and troughs
        window = self.peak_window.value()
        sma_df = detect_peaks_troughs(sma_df, 'pct_above', window=window)
        
        # Plot peaks
        peaks = sma_df[sma_df['is_significant_peak']]
        if not peaks.empty:
            px = np.array([d.timestamp() for d in peaks['date']])
            py = peaks['pct_above'].values
            self.detail_plot.plot(
                px, py, pen=None,
                symbol='o', symbolBrush=PEAK_COLOR, symbolSize=12
            )
        
        # Plot troughs
        troughs = sma_df[sma_df['is_significant_trough']]
        if not troughs.empty:
            tx = np.array([d.timestamp() for d in troughs['date']])
            ty = troughs['pct_above'].values
            self.detail_plot.plot(
                tx, ty, pen=None,
                symbol='o', symbolBrush=TROUGH_COLOR, symbolSize=12
            )
        
        # Reference lines
        self.detail_plot.addLine(y=50, pen=pg.mkPen('gray', style=Qt.DashLine))
        
        # Update Nifty chart with markers
        if self.nifty_data is not None and not self.nifty_data.empty:
            nx = np.array([d.timestamp() for d in self.nifty_data['date']])
            ny = self.nifty_data['close'].values
            self.detail_nifty_plot.plot(nx, ny, pen=pg.mkPen(NIFTY_COLOR, width=2))
            
            # Add vertical lines at peaks/troughs
            for _, peak in peaks.iterrows():
                ts = peak['date'].timestamp()
                self.detail_nifty_plot.addLine(
                    x=ts, pen=pg.mkPen(PEAK_COLOR, width=1, style=Qt.DashLine)
                )
            
            for _, trough in troughs.iterrows():
                ts = trough['date'].timestamp()
                self.detail_nifty_plot.addLine(
                    x=ts, pen=pg.mkPen(TROUGH_COLOR, width=1, style=Qt.DashLine)
                )
        
        # Update stats table
        self._update_detail_stats(sma_df, peaks, troughs)
    
    def _update_detail_stats(self, df, peaks, troughs):
        """Update the detail statistics table."""
        stats = [
            ('Current % Above', f"{df['pct_above'].iloc[-1]:.1f}%" if len(df) > 0 else 'N/A'),
            ('Max % Above', f"{df['pct_above'].max():.1f}%"),
            ('Min % Above', f"{df['pct_above'].min():.1f}%"),
            ('Mean % Above', f"{df['pct_above'].mean():.1f}%"),
            ('# Peaks Found', str(len(peaks))),
            ('# Troughs Found', str(len(troughs))),
        ]
        
        self.detail_stats.setRowCount(1)
        self.detail_stats.setColumnCount(len(stats))
        self.detail_stats.setHorizontalHeaderLabels([s[0] for s in stats])
        
        for i, (_, val) in enumerate(stats):
            self.detail_stats.setItem(0, i, QTableWidgetItem(val))
    
    def _update_data_table(self):
        """Update the data table."""
        df = self.breadth_data.get(self.current_index)
        if df is None or df.empty:
            self.data_table.setRowCount(0)
            return
        
        # Filter by SMA if selected
        sma_filter = self.data_sma_combo.currentText()
        if sma_filter != "All SMAs":
            df = df[df['sma_period'] == int(sma_filter)]
        
        # Sort by date descending
        df = df.sort_values('date', ascending=False)
        
        self.data_table.setRowCount(len(df))
        
        for i, (_, row) in enumerate(df.iterrows()):
            self.data_table.setItem(i, 0, QTableWidgetItem(str(row['date'].date())))
            self.data_table.setItem(i, 1, QTableWidgetItem(str(row['index_name'])))
            self.data_table.setItem(i, 2, QTableWidgetItem(str(row['sma_period'])))
            self.data_table.setItem(i, 3, QTableWidgetItem(str(row['total_stocks'])))
            self.data_table.setItem(i, 4, QTableWidgetItem(str(row['above_count'])))
            self.data_table.setItem(i, 5, QTableWidgetItem(str(row['below_count'])))
            self.data_table.setItem(i, 6, QTableWidgetItem(f"{row['pct_above']:.1f}%"))
            self.data_table.setItem(i, 7, QTableWidgetItem(f"{row['pct_below']:.1f}%"))
    
    # ========================================================================
    # Analysis
    # ========================================================================
    
    def _run_prediction_analysis(self):
        """Run the predictive power analysis."""
        self.statusBar.showMessage("Running analysis...")
        QApplication.processEvents()
        
        try:
            results = analyze_predictive_power(
                self.engine, self.current_index,
                forward_days=[5, 10, 20, 50]
            )
            
            if results.empty:
                self.statusBar.showMessage("No analysis results")
                return
            
            # Populate table
            self.analysis_table.setRowCount(len(results))
            
            for i, (_, row) in enumerate(results.iterrows()):
                self.analysis_table.setItem(i, 0, QTableWidgetItem(str(row['sma_period'])))
                self.analysis_table.setItem(i, 1, QTableWidgetItem(str(row['forward_days'])))
                self.analysis_table.setItem(i, 2, QTableWidgetItem(str(row['term'])))
                self.analysis_table.setItem(i, 3, QTableWidgetItem(str(row['num_peaks'])))
                self.analysis_table.setItem(i, 4, QTableWidgetItem(str(row['num_troughs'])))
                
                # Format returns
                avg_peak = row['avg_ret_after_peak']
                avg_peak_str = f"{avg_peak:.2f}%" if pd.notna(avg_peak) else 'N/A'
                self.analysis_table.setItem(i, 5, QTableWidgetItem(avg_peak_str))
                
                pct_dec = row['pct_decline_after_peak']
                pct_dec_str = f"{pct_dec:.1f}%" if pd.notna(pct_dec) else 'N/A'
                self.analysis_table.setItem(i, 6, QTableWidgetItem(pct_dec_str))
                
                avg_trough = row['avg_ret_after_trough']
                avg_trough_str = f"{avg_trough:.2f}%" if pd.notna(avg_trough) else 'N/A'
                self.analysis_table.setItem(i, 7, QTableWidgetItem(avg_trough_str))
                
                pct_rally = row['pct_rally_after_trough']
                pct_rally_str = f"{pct_rally:.1f}%" if pd.notna(pct_rally) else 'N/A'
                self.analysis_table.setItem(i, 8, QTableWidgetItem(pct_rally_str))
            
            # Generate summary
            self._generate_analysis_summary(results)
            
            self.statusBar.showMessage("Analysis complete!")
            
        except Exception as e:
            self.statusBar.showMessage(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _generate_analysis_summary(self, results: pd.DataFrame):
        """Generate analysis summary."""
        summary_parts = []
        
        # Find best predictor for each term
        for term in ['short', 'medium', 'long']:
            term_df = results[results['term'] == term]
            if term_df.empty:
                continue
            
            # Best for predicting decline (highest % decline after peak)
            best_decline = term_df.loc[term_df['pct_decline_after_peak'].idxmax()] if term_df['pct_decline_after_peak'].notna().any() else None
            
            # Best for predicting rally (highest % rally after trough)
            best_rally = term_df.loc[term_df['pct_rally_after_trough'].idxmax()] if term_df['pct_rally_after_trough'].notna().any() else None
            
            term_label = {'short': 'Short-term (5-10d)', 'medium': 'Medium-term (20d)', 'long': 'Long-term (50d)'}[term]
            
            if best_decline is not None:
                summary_parts.append(
                    f"<b>{term_label}:</b> SMA {int(best_decline['sma_period'])} peaks predict decline "
                    f"({best_decline['pct_decline_after_peak']:.0f}% accuracy)"
                )
            
            if best_rally is not None:
                summary_parts.append(
                    f"  SMA {int(best_rally['sma_period'])} troughs predict rally "
                    f"({best_rally['pct_rally_after_trough']:.0f}% accuracy)"
                )
        
        self.analysis_summary.setText("<br>".join(summary_parts) if summary_parts else "Insufficient data for analysis")
    
    # ========================================================================
    # Event Handlers
    # ========================================================================
    
    def _on_index_changed(self, index_name: str):
        """Handle index selection change."""
        self.current_index = index_name
        self._update_charts()
        self._update_data_table()
    
    def _on_date_changed(self):
        """Handle date range change."""
        self._load_data()
    
    def _on_sma_changed(self):
        """Handle SMA checkbox change."""
        self._update_comparison_chart()
    
    def _mouse_moved(self, pos):
        """Handle mouse movement for crosshair in comparison plot."""
        if self.comparison_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.comparison_plot.plotItem.vb.mapSceneToView(pos)
            x_val = mouse_point.x()
            
            # Update comparison plot crosshair
            self.vLine.setPos(x_val)
            self.hLine.setPos(mouse_point.y())
            
            # Synchronize Nifty plot vertical line (same X position)
            self.vLine_nifty.setPos(x_val)
            
            # Update horizontal line in Nifty plot based on Nifty price at this date
            if self.nifty_data is not None and not self.nifty_data.empty:
                try:
                    # Find closest Nifty price for this timestamp
                    date = datetime.fromtimestamp(x_val)
                    closest_idx = (self.nifty_data['date'] - date).abs().idxmin()
                    nifty_price = self.nifty_data.loc[closest_idx, 'close']
                    self.hLine_nifty.setPos(nifty_price)
                    
                    # Update info label with both values
                    self.info_label.setText(
                        f"Date: {date.strftime('%Y-%m-%d')} | % Above: {mouse_point.y():.1f}% | NIFTY: {nifty_price:,.0f}"
                    )
                except:
                    self.info_label.setText(
                        f"Date: {datetime.fromtimestamp(x_val).strftime('%Y-%m-%d')} | % Above: {mouse_point.y():.1f}%"
                    )
    
    def _mouse_moved_nifty(self, pos):
        """Handle mouse movement for crosshair in Nifty plot."""
        if self.nifty_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.nifty_plot.plotItem.vb.mapSceneToView(pos)
            x_val = mouse_point.x()
            
            # Update Nifty plot crosshair
            self.vLine_nifty.setPos(x_val)
            self.hLine_nifty.setPos(mouse_point.y())
            
            # Synchronize comparison plot vertical line
            self.vLine.setPos(x_val)
            
            # Update info label
            try:
                date = datetime.fromtimestamp(x_val)
                nifty_price = mouse_point.y()
                
                # Try to find % above for this date
                pct_above_str = ""
                df = self.breadth_data.get(self.current_index)
                if df is not None and not df.empty:
                    # Find closest date in breadth data for SMA 50
                    sma50_df = df[df['sma_period'] == 50]
                    if not sma50_df.empty:
                        closest_idx = (sma50_df['date'] - date).abs().idxmin()
                        pct_above = sma50_df.loc[closest_idx, 'pct_above']
                        pct_above_str = f" | % Above SMA50: {pct_above:.1f}%"
                
                self.info_label.setText(
                    f"Date: {date.strftime('%Y-%m-%d')} | NIFTY: {nifty_price:,.0f}{pct_above_str}"
                )
            except:
                pass
    
    def _export_csv(self):
        """Export data to CSV."""
        try:
            df = self.breadth_data.get(self.current_index)
            if df is not None and not df.empty:
                filename = f"sma_breadth_{self.current_index.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
                filepath = Path(__file__).parent.parent / 'reports_output' / filename
                filepath.parent.mkdir(exist_ok=True)
                df.to_csv(filepath, index=False)
                self.statusBar.showMessage(f"Exported to {filepath}")
        except Exception as e:
            self.statusBar.showMessage(f"Export error: {str(e)}")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application-wide font
    font = QFont('Segoe UI', 10)
    app.setFont(font)
    
    window = SMABreadthVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
