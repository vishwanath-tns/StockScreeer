"""
Bollinger Bands Analyzer GUI

Main GUI application for BB analysis.
"""

import logging
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QFrame, QSplitter, QGroupBox, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QProgressBar,
    QMessageBox, QHeaderView, QStatusBar, QToolBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QAction

import pandas as pd

from ..models.bb_models import BBConfig, BollingerBands, BBRating
from ..models.signal_models import BBSignal, SignalType
from ..models.scan_models import ScanType
from ..services.bb_orchestrator import BBOrchestrator


logger = logging.getLogger(__name__)


class BBAnalyzerGUI(QMainWindow):
    """
    Main Bollinger Bands Analyzer window.
    
    Features:
    - Symbol analysis with interactive charts
    - Multiple scanner tabs (squeeze, trend, pullback, etc.)
    - Signal list with filtering
    - Rating comparison table
    - Settings panel
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bollinger Bands Analyzer")
        self.setMinimumSize(1400, 900)
        
        # Initialize orchestrator
        self.orchestrator = BBOrchestrator()
        
        # Cache for data
        self._symbol_data: Dict[str, List[BollingerBands]] = {}
        self._current_symbol = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the main UI."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create toolbar
        self._create_toolbar()
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Symbol list and analysis
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Charts and details
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 1000])
        layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def _create_toolbar(self):
        """Create main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Refresh action
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self._on_refresh)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Scan buttons
        squeeze_btn = QPushButton("📊 Squeeze Scan")
        squeeze_btn.clicked.connect(lambda: self._run_scan(ScanType.SQUEEZE))
        toolbar.addWidget(squeeze_btn)
        
        trend_btn = QPushButton("📈 Trend Scan")
        trend_btn.clicked.connect(lambda: self._run_scan(ScanType.TREND_UP))
        toolbar.addWidget(trend_btn)
        
        pullback_btn = QPushButton("🎯 Pullback Scan")
        pullback_btn.clicked.connect(lambda: self._run_scan(ScanType.PULLBACK_BUY))
        toolbar.addWidget(pullback_btn)
        
        toolbar.addSeparator()
        
        # Symbol search
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Enter symbol...")
        self.symbol_input.setMaximumWidth(150)
        self.symbol_input.returnPressed.connect(self._on_symbol_search)
        toolbar.addWidget(self.symbol_input)
        
        analyze_btn = QPushButton("Analyze")
        analyze_btn.clicked.connect(self._on_symbol_search)
        toolbar.addWidget(analyze_btn)
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with scanner tabs."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Scanner tabs
        self.scanner_tabs = QTabWidget()
        
        # Squeeze tab
        squeeze_tab = self._create_scanner_tab("squeeze")
        self.scanner_tabs.addTab(squeeze_tab, "🔍 Squeeze")
        
        # Trend tab
        trend_tab = self._create_scanner_tab("trend")
        self.scanner_tabs.addTab(trend_tab, "📈 Trend")
        
        # Pullback tab
        pullback_tab = self._create_scanner_tab("pullback")
        self.scanner_tabs.addTab(pullback_tab, "🎯 Pullback")
        
        # Signals tab
        signals_tab = self._create_signals_tab()
        self.scanner_tabs.addTab(signals_tab, "⚡ Signals")
        
        # Ratings tab
        ratings_tab = self._create_ratings_tab()
        self.scanner_tabs.addTab(ratings_tab, "⭐ Ratings")
        
        layout.addWidget(self.scanner_tabs)
        
        return panel
    
    def _create_scanner_tab(self, scan_type: str) -> QWidget:
        """Create a scanner tab with results table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter controls
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        
        filter_layout.addWidget(QLabel("Min Score:"))
        min_score = QSpinBox()
        min_score.setRange(0, 100)
        min_score.setValue(50)
        filter_layout.addWidget(min_score)
        
        filter_btn = QPushButton("Filter")
        filter_layout.addWidget(filter_btn)
        filter_layout.addStretch()
        
        layout.addWidget(filter_frame)
        
        # Results table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Symbol", "Score", "%b", "BW", "Days", "Action"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.cellDoubleClicked.connect(self._on_table_double_click)
        
        layout.addWidget(table)
        
        # Store reference
        setattr(self, f"{scan_type}_table", table)
        
        return widget
    
    def _create_signals_tab(self) -> QWidget:
        """Create signals tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter controls
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        
        filter_layout.addWidget(QLabel("Type:"))
        self.signal_type_combo = QComboBox()
        self.signal_type_combo.addItems(["All", "Buy", "Sell"])
        filter_layout.addWidget(self.signal_type_combo)
        
        filter_layout.addWidget(QLabel("Min Confidence:"))
        self.min_confidence = QSpinBox()
        self.min_confidence.setRange(0, 100)
        self.min_confidence.setValue(60)
        filter_layout.addWidget(self.min_confidence)
        
        self.volume_check = QCheckBox("Volume Confirmed")
        filter_layout.addWidget(self.volume_check)
        
        filter_btn = QPushButton("Apply")
        filter_layout.addWidget(filter_btn)
        filter_layout.addStretch()
        
        layout.addWidget(filter_frame)
        
        # Signals table
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(8)
        self.signals_table.setHorizontalHeaderLabels([
            "Symbol", "Date", "Type", "Pattern", "Confidence",
            "Price", "Target", "Vol Conf"
        ])
        self.signals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.signals_table.cellDoubleClicked.connect(self._on_signal_click)
        
        layout.addWidget(self.signals_table)
        
        return widget
    
    def _create_ratings_tab(self) -> QWidget:
        """Create ratings comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Sort controls
        sort_frame = QFrame()
        sort_layout = QHBoxLayout(sort_frame)
        
        sort_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Score", "Symbol", "%b", "Squeeze", "Trend"])
        sort_layout.addWidget(self.sort_combo)
        
        refresh_btn = QPushButton("Refresh Ratings")
        refresh_btn.clicked.connect(self._refresh_ratings)
        sort_layout.addWidget(refresh_btn)
        sort_layout.addStretch()
        
        layout.addWidget(sort_frame)
        
        # Ratings table
        self.ratings_table = QTableWidget()
        self.ratings_table.setColumnCount(8)
        self.ratings_table.setHorizontalHeaderLabels([
            "Symbol", "Score", "Grade", "Squeeze", "Trend",
            "Momentum", "Pattern", "%b"
        ])
        self.ratings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ratings_table.cellDoubleClicked.connect(self._on_table_double_click)
        
        layout.addWidget(self.ratings_table)
        
        return widget
    
    def _create_right_panel(self) -> QWidget:
        """Create right panel with chart and details."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Symbol info header
        self.symbol_header = QLabel("Select a symbol to analyze")
        self.symbol_header.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.symbol_header)
        
        # Chart placeholder (will be replaced with actual chart)
        try:
            from .bb_chart_widget import BBChartWidget
            self.chart = BBChartWidget()
        except ImportError:
            self.chart = QLabel("Chart requires pyqtgraph.\nInstall with: pip install pyqtgraph")
            self.chart.setAlignment(Qt.AlignCenter)
            self.chart.setStyleSheet("background: #1E1E1E; color: white; padding: 20px;")
        
        layout.addWidget(self.chart, stretch=3)
        
        # Analysis details
        details_frame = self._create_details_frame()
        layout.addWidget(details_frame, stretch=1)
        
        return panel
    
    def _create_details_frame(self) -> QFrame:
        """Create analysis details frame."""
        frame = QGroupBox("Analysis Details")
        layout = QVBoxLayout(frame)
        
        # Stats grid
        stats_layout = QHBoxLayout()
        
        # Current BB values
        bb_group = QGroupBox("Current BB")
        bb_layout = QVBoxLayout(bb_group)
        self.pb_value = QLabel("%b: --")
        self.bw_value = QLabel("BandWidth: --")
        self.squeeze_value = QLabel("State: --")
        bb_layout.addWidget(self.pb_value)
        bb_layout.addWidget(self.bw_value)
        bb_layout.addWidget(self.squeeze_value)
        stats_layout.addWidget(bb_group)
        
        # Rating
        rating_group = QGroupBox("Rating")
        rating_layout = QVBoxLayout(rating_group)
        self.rating_value = QLabel("Score: --")
        self.grade_value = QLabel("Grade: --")
        self.trend_value = QLabel("Trend: --")
        rating_layout.addWidget(self.rating_value)
        rating_layout.addWidget(self.grade_value)
        rating_layout.addWidget(self.trend_value)
        stats_layout.addWidget(rating_group)
        
        # Active Signals
        signals_group = QGroupBox("Signals")
        signals_layout = QVBoxLayout(signals_group)
        self.buy_signals = QLabel("Buy: 0")
        self.sell_signals = QLabel("Sell: 0")
        self.signal_desc = QLabel("--")
        signals_layout.addWidget(self.buy_signals)
        signals_layout.addWidget(self.sell_signals)
        signals_layout.addWidget(self.signal_desc)
        stats_layout.addWidget(signals_group)
        
        layout.addLayout(stats_layout)
        
        return frame
    
    def _connect_signals(self):
        """Connect widget signals."""
        pass  # Connections made inline
    
    def _on_refresh(self):
        """Refresh all data."""
        self.status_bar.showMessage("Refreshing data...")
        # Trigger data reload
        self._load_data()
    
    def _on_symbol_search(self):
        """Handle symbol search."""
        symbol = self.symbol_input.text().strip().upper()
        if symbol:
            self._analyze_symbol(symbol)
    
    def _on_table_double_click(self, row: int, col: int):
        """Handle table row double-click."""
        sender = self.sender()
        if sender and sender.item(row, 0):
            symbol = sender.item(row, 0).text()
            self._analyze_symbol(symbol)
    
    def _on_signal_click(self, row: int, col: int):
        """Handle signal row click."""
        if self.signals_table.item(row, 0):
            symbol = self.signals_table.item(row, 0).text()
            self._analyze_symbol(symbol)
    
    def _run_scan(self, scan_type: ScanType):
        """Run a scan and display results."""
        self.status_bar.showMessage(f"Running {scan_type.value} scan...")
        self.progress_bar.show()
        self.progress_bar.setValue(50)
        
        try:
            # Get scan results
            # In real implementation, would fetch data and run scan
            results = []  # self.orchestrator.run_scan(scan_type, self._symbol_data)
            
            # Update appropriate table
            if scan_type == ScanType.SQUEEZE:
                self._populate_scan_table(self.squeeze_table, results)
            elif scan_type in (ScanType.TREND_UP, ScanType.TREND_DOWN):
                self._populate_scan_table(self.trend_table, results)
            elif scan_type in (ScanType.PULLBACK_BUY, ScanType.PULLBACK_SELL):
                self._populate_scan_table(self.pullback_table, results)
            
            self.status_bar.showMessage(f"Found {len(results)} results")
        except Exception as e:
            logger.error(f"Scan error: {e}")
            QMessageBox.warning(self, "Scan Error", str(e))
        finally:
            self.progress_bar.hide()
    
    def _populate_scan_table(self, table: QTableWidget, results: list):
        """Populate a scan results table."""
        table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            table.setItem(row, 0, QTableWidgetItem(getattr(result, 'symbol', '--')))
            # Add other columns based on result type
    
    def _analyze_symbol(self, symbol: str):
        """Analyze a specific symbol."""
        self._current_symbol = symbol
        self.symbol_header.setText(f"📊 {symbol}")
        self.status_bar.showMessage(f"Analyzing {symbol}...")
        
        try:
            # Get BB data for symbol
            if symbol in self._symbol_data:
                bb_data = self._symbol_data[symbol]
            else:
                # Would fetch from database
                bb_data = []
            
            if bb_data:
                # Update chart
                if hasattr(self.chart, 'set_data'):
                    self.chart.set_data(symbol, bb_data)
                
                # Get summary
                summary = self.orchestrator.get_symbol_summary(symbol, bb_data)
                self._update_details(summary)
                
                # Get signals
                signals = self.orchestrator.generate_signals(symbol, bb_data)
                if hasattr(self.chart, 'set_signals'):
                    self.chart.set_signals(signals)
            else:
                self.status_bar.showMessage(f"No data for {symbol}")
        
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            self.status_bar.showMessage(f"Error analyzing {symbol}")
    
    def _update_details(self, summary: dict):
        """Update the details panel."""
        self.pb_value.setText(f"%b: {summary.get('percent_b', 0):.3f}")
        self.bw_value.setText(f"BandWidth: {summary.get('bandwidth', 0):.4f}")
        self.squeeze_value.setText(f"State: {summary.get('squeeze_state', '--')}")
        
        self.rating_value.setText(f"Score: {summary.get('rating', '--')}")
        self.grade_value.setText(f"Grade: {summary.get('grade', '--')}")
        self.trend_value.setText(f"Trend: {summary.get('trend', '--')}")
        
        self.buy_signals.setText(f"Buy: {summary.get('buy_signals', 0)}")
        self.sell_signals.setText(f"Sell: {summary.get('sell_signals', 0)}")
    
    def _refresh_ratings(self):
        """Refresh all ratings."""
        self.status_bar.showMessage("Refreshing ratings...")
        # Would calculate and display all ratings
    
    def _load_data(self):
        """Load initial data."""
        # In real implementation, would load from database
        pass


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark theme
    palette = app.palette()
    palette.setColor(palette.Window, QColor(30, 30, 30))
    palette.setColor(palette.WindowText, QColor(255, 255, 255))
    palette.setColor(palette.Base, QColor(45, 45, 45))
    palette.setColor(palette.AlternateBase, QColor(35, 35, 35))
    palette.setColor(palette.Text, QColor(255, 255, 255))
    palette.setColor(palette.Button, QColor(50, 50, 50))
    palette.setColor(palette.ButtonText, QColor(255, 255, 255))
    palette.setColor(palette.Highlight, QColor(42, 130, 218))
    app.setPalette(palette)
    
    window = BBAnalyzerGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
