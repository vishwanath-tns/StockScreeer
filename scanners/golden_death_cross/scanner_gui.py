"""
Golden Cross / Death Cross Scanner GUI
======================================
PyQt5 GUI for viewing and analyzing crossover signals.

Features:
- View recent Golden Cross and Death Cross signals
- Filter by date range, signal type, symbol
- Historical signal lookup
- Track performance metrics
- Run incremental scans
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Optional, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QGroupBox,
    QDateEdit, QComboBox, QLineEdit, QTabWidget, QProgressBar,
    QMessageBox, QHeaderView, QSplitter, QTextEdit, QStatusBar,
    QCheckBox, QSpinBox, QFrame
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scanners.golden_death_cross.detector import (
    CrossoverDetector, CrossoverType, CrossoverSignal, run_daily_scan
)


class ScanWorker(QThread):
    """Background worker for scanning operations."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int)  # signals_found, signals_saved
    error = pyqtSignal(str)
    
    def __init__(self, detector: CrossoverDetector, scan_type: str, 
                 start_date: date = None, end_date: date = None):
        super().__init__()
        self.detector = detector
        self.scan_type = scan_type
        self.start_date = start_date
        self.end_date = end_date
    
    def run(self):
        try:
            if self.scan_type == "daily":
                self.progress.emit(f"Scanning for today's crossovers...")
                signals = self.detector.scan_for_date(date.today())
            elif self.scan_type == "historical":
                def progress_cb(current, total, symbol):
                    self.progress.emit(f"Scanning {current}/{total}: {symbol}")
                
                signals = self.detector.scan_all_stocks(
                    start_date=self.start_date,
                    end_date=self.end_date,
                    progress_callback=progress_cb
                )
            else:
                signals = []
            
            self.progress.emit(f"Saving {len(signals)} signals...")
            saved = self.detector.save_signals(signals)
            
            self.progress.emit("Updating performance metrics...")
            self.detector.update_performance()
            
            self.finished.emit(len(signals), saved)
            
        except Exception as e:
            self.error.emit(str(e))


class CrossoverScannerGUI(QMainWindow):
    """Main GUI window for crossover scanner."""
    
    def __init__(self):
        super().__init__()
        self.detector = CrossoverDetector()
        self.worker = None
        
        self.setWindowTitle("🔄 Golden Cross / Death Cross Scanner")
        self.setMinimumSize(1200, 800)
        
        self._setup_ui()
        self._refresh_data()
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _setup_ui(self):
        """Setup the main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Title and summary
        self._create_header(layout)
        
        # Main content with tabs
        tabs = QTabWidget()
        
        # Tab 1: Today's Signals
        tabs.addTab(self._create_today_tab(), "📊 Today's Signals")
        
        # Tab 2: Recent Signals
        tabs.addTab(self._create_recent_tab(), "📈 Recent Signals")
        
        # Tab 3: Historical Search
        tabs.addTab(self._create_search_tab(), "🔍 Search")
        
        # Tab 4: Scan
        tabs.addTab(self._create_scan_tab(), "⚡ Run Scan")
        
        layout.addWidget(tabs)
    
    def _create_header(self, layout: QVBoxLayout):
        """Create header with summary stats."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
            }
        """)
        header_layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("🔄 Golden Cross / Death Cross Scanner")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Summary boxes
        self.summary_labels = {}
        
        for label, key, color in [
            ("Today 🟢", "today_gc", "#00c853"),
            ("Today 🔴", "today_dc", "#ff1744"),
            ("30 Days 🟢", "month_gc", "#69f0ae"),
            ("30 Days 🔴", "month_dc", "#ff8a80"),
        ]:
            box = QFrame()
            box.setStyleSheet(f"""
                QFrame {{
                    background-color: #2d2d2d;
                    border-radius: 4px;
                    padding: 5px 15px;
                }}
            """)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(5, 5, 5, 5)
            
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #888; font-size: 11px;")
            box_layout.addWidget(lbl)
            
            val = QLabel("--")
            val.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
            box_layout.addWidget(val)
            self.summary_labels[key] = val
            
            header_layout.addWidget(box)
        
        layout.addWidget(header)
    
    def _create_today_tab(self) -> QWidget:
        """Create tab for today's signals."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_data)
        controls.addWidget(refresh_btn)
        
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Splitter for Golden/Death Cross tables
        splitter = QSplitter(Qt.Horizontal)
        
        # Golden Cross table
        gc_group = QGroupBox("🟢 Golden Cross (Bullish)")
        gc_layout = QVBoxLayout(gc_group)
        self.gc_table = self._create_signals_table()
        gc_layout.addWidget(self.gc_table)
        splitter.addWidget(gc_group)
        
        # Death Cross table
        dc_group = QGroupBox("🔴 Death Cross (Bearish)")
        dc_layout = QVBoxLayout(dc_group)
        self.dc_table = self._create_signals_table()
        dc_layout.addWidget(self.dc_table)
        splitter.addWidget(dc_group)
        
        layout.addWidget(splitter)
        
        return widget
    
    def _create_recent_tab(self) -> QWidget:
        """Create tab for recent signals."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls = QHBoxLayout()
        
        controls.addWidget(QLabel("Days:"))
        self.recent_days = QSpinBox()
        self.recent_days.setRange(1, 90)
        self.recent_days.setValue(7)
        self.recent_days.valueChanged.connect(self._refresh_recent)
        controls.addWidget(self.recent_days)
        
        controls.addWidget(QLabel("Type:"))
        self.recent_type = QComboBox()
        self.recent_type.addItems(["All", "Golden Cross", "Death Cross"])
        self.recent_type.currentIndexChanged.connect(self._refresh_recent)
        controls.addWidget(self.recent_type)
        
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Table
        self.recent_table = self._create_signals_table(extended=True)
        layout.addWidget(self.recent_table)
        
        return widget
    
    def _create_search_tab(self) -> QWidget:
        """Create search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search controls
        controls = QHBoxLayout()
        
        controls.addWidget(QLabel("Symbol:"))
        self.search_symbol = QLineEdit()
        self.search_symbol.setPlaceholderText("e.g., RELIANCE.NS")
        self.search_symbol.setMaximumWidth(200)
        controls.addWidget(self.search_symbol)
        
        controls.addWidget(QLabel("From:"))
        self.search_from = QDateEdit()
        self.search_from.setDate(QDate.currentDate().addDays(-365))
        self.search_from.setCalendarPopup(True)
        controls.addWidget(self.search_from)
        
        controls.addWidget(QLabel("To:"))
        self.search_to = QDateEdit()
        self.search_to.setDate(QDate.currentDate())
        self.search_to.setCalendarPopup(True)
        controls.addWidget(self.search_to)
        
        controls.addWidget(QLabel("Type:"))
        self.search_type = QComboBox()
        self.search_type.addItems(["All", "Golden Cross", "Death Cross"])
        controls.addWidget(self.search_type)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self._run_search)
        controls.addWidget(search_btn)
        
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Results table
        self.search_table = self._create_signals_table(extended=True)
        layout.addWidget(self.search_table)
        
        return widget
    
    def _create_scan_tab(self) -> QWidget:
        """Create scan tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Instructions
        info = QLabel(
            "Run scans to find Golden Cross and Death Cross signals.\n"
            "• Daily Scan: Quick scan for today's signals only\n"
            "• Historical Scan: Full scan of all stocks for date range"
        )
        info.setStyleSheet("color: #888; padding: 10px;")
        layout.addWidget(info)
        
        # Daily scan
        daily_group = QGroupBox("⚡ Daily Scan")
        daily_layout = QVBoxLayout(daily_group)
        
        self.daily_scan_btn = QPushButton("🔄 Run Daily Scan")
        self.daily_scan_btn.setMinimumHeight(40)
        self.daily_scan_btn.clicked.connect(lambda: self._run_scan("daily"))
        daily_layout.addWidget(self.daily_scan_btn)
        
        layout.addWidget(daily_group)
        
        # Historical scan
        hist_group = QGroupBox("📚 Historical Scan")
        hist_layout = QVBoxLayout(hist_group)
        
        hist_controls = QHBoxLayout()
        hist_controls.addWidget(QLabel("From:"))
        self.hist_from = QDateEdit()
        self.hist_from.setDate(QDate.currentDate().addDays(-365))
        self.hist_from.setCalendarPopup(True)
        hist_controls.addWidget(self.hist_from)
        
        hist_controls.addWidget(QLabel("To:"))
        self.hist_to = QDateEdit()
        self.hist_to.setDate(QDate.currentDate())
        self.hist_to.setCalendarPopup(True)
        hist_controls.addWidget(self.hist_to)
        
        hist_controls.addStretch()
        hist_layout.addLayout(hist_controls)
        
        self.hist_scan_btn = QPushButton("📊 Run Historical Scan")
        self.hist_scan_btn.setMinimumHeight(40)
        self.hist_scan_btn.clicked.connect(lambda: self._run_scan("historical"))
        hist_layout.addWidget(self.hist_scan_btn)
        
        layout.addWidget(hist_group)
        
        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("font-family: Consolas; font-size: 11px;")
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
        layout.addStretch()
        
        return widget
    
    def _create_signals_table(self, extended: bool = False) -> QTableWidget:
        """Create a signals table widget."""
        table = QTableWidget()
        
        if extended:
            columns = ["Symbol", "Date", "Type", "Close", "SMA 50", "SMA 200", 
                      "Prev Signal", "Days Since", "1D %", "5D %", "20D %"]
        else:
            columns = ["Symbol", "Date", "Close", "SMA 50", "SMA 200", "Days Since Last"]
        
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        
        return table
    
    def _refresh_data(self):
        """Refresh all data displays."""
        self._refresh_summary()
        self._refresh_today()
        self._refresh_recent()
    
    def _refresh_summary(self):
        """Refresh summary statistics."""
        try:
            summary = self.detector.get_signals_summary()
            
            self.summary_labels['today_gc'].setText(str(summary['today']['golden_cross']))
            self.summary_labels['today_dc'].setText(str(summary['today']['death_cross']))
            self.summary_labels['month_gc'].setText(str(summary['last_30_days']['golden_cross']))
            self.summary_labels['month_dc'].setText(str(summary['last_30_days']['death_cross']))
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}")
    
    def _refresh_today(self):
        """Refresh today's signals tables."""
        try:
            today_signals = self.detector.load_signals(
                start_date=date.today(),
                end_date=date.today()
            )
            
            # Golden Cross
            gc_df = today_signals[today_signals['signal_type'] == 'GOLDEN_CROSS']
            self._populate_table(self.gc_table, gc_df, extended=False)
            
            # Death Cross
            dc_df = today_signals[today_signals['signal_type'] == 'DEATH_CROSS']
            self._populate_table(self.dc_table, dc_df, extended=False)
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}")
    
    def _refresh_recent(self):
        """Refresh recent signals table."""
        try:
            days = self.recent_days.value()
            start = date.today() - timedelta(days=days)
            
            type_filter = None
            type_text = self.recent_type.currentText()
            if type_text == "Golden Cross":
                type_filter = CrossoverType.GOLDEN_CROSS
            elif type_text == "Death Cross":
                type_filter = CrossoverType.DEATH_CROSS
            
            df = self.detector.load_signals(
                start_date=start,
                signal_type=type_filter,
                limit=500
            )
            
            self._populate_table(self.recent_table, df, extended=True)
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}")
    
    def _run_search(self):
        """Run search query."""
        try:
            symbol = self.search_symbol.text().strip() or None
            start = self.search_from.date().toPyDate()
            end = self.search_to.date().toPyDate()
            
            type_filter = None
            type_text = self.search_type.currentText()
            if type_text == "Golden Cross":
                type_filter = CrossoverType.GOLDEN_CROSS
            elif type_text == "Death Cross":
                type_filter = CrossoverType.DEATH_CROSS
            
            df = self.detector.load_signals(
                symbol=symbol,
                start_date=start,
                end_date=end,
                signal_type=type_filter,
                limit=1000
            )
            
            self._populate_table(self.search_table, df, extended=True)
            self.statusBar().showMessage(f"Found {len(df)} signals")
            
        except Exception as e:
            QMessageBox.warning(self, "Search Error", str(e))
    
    def _populate_table(self, table: QTableWidget, df, extended: bool = False):
        """Populate a table with signal data."""
        table.setRowCount(0)
        
        if df.empty:
            return
        
        for _, row in df.iterrows():
            row_idx = table.rowCount()
            table.insertRow(row_idx)
            
            if extended:
                items = [
                    str(row['symbol']),
                    str(row['signal_date']),
                    row['signal_type'].replace('_', ' '),
                    f"₹{row['close_price']:,.2f}" if row['close_price'] else "--",
                    f"{row['sma_short']:,.2f}" if row['sma_short'] else "--",
                    f"{row['sma_long']:,.2f}" if row['sma_long'] else "--",
                    str(row['previous_signal_type'] or '--').replace('_', ' '),
                    str(row['days_since_previous'] or '--'),
                    f"{row['pct_change_1d']:.1f}%" if row['pct_change_1d'] else "--",
                    f"{row['pct_change_5d']:.1f}%" if row['pct_change_5d'] else "--",
                    f"{row['pct_change_20d']:.1f}%" if row['pct_change_20d'] else "--",
                ]
            else:
                items = [
                    str(row['symbol']),
                    str(row['signal_date']),
                    f"₹{row['close_price']:,.2f}" if row['close_price'] else "--",
                    f"{row['sma_short']:,.2f}" if row['sma_short'] else "--",
                    f"{row['sma_long']:,.2f}" if row['sma_long'] else "--",
                    str(row['days_since_previous'] or '--'),
                ]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                
                # Color coding
                if extended and col == 2:  # Type column
                    if "GOLDEN" in text:
                        item.setForeground(QColor("#00c853"))
                    elif "DEATH" in text:
                        item.setForeground(QColor("#ff1744"))
                
                # Performance coloring
                if extended and col >= 8:  # Performance columns
                    if "--" not in text:
                        pct = float(text.replace('%', '').replace(',', ''))
                        if pct > 0:
                            item.setForeground(QColor("#00c853"))
                        elif pct < 0:
                            item.setForeground(QColor("#ff1744"))
                
                table.setItem(row_idx, col, item)
    
    def _run_scan(self, scan_type: str):
        """Run a scan operation."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "A scan is already running")
            return
        
        self.log_text.clear()
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.daily_scan_btn.setEnabled(False)
        self.hist_scan_btn.setEnabled(False)
        
        start_date = None
        end_date = None
        
        if scan_type == "historical":
            start_date = self.hist_from.date().toPyDate()
            end_date = self.hist_to.date().toPyDate()
        
        self.worker = ScanWorker(self.detector, scan_type, start_date, end_date)
        self.worker.progress.connect(self._on_scan_progress)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()
    
    def _on_scan_progress(self, message: str):
        """Handle scan progress."""
        self.progress_label.setText(message)
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def _on_scan_finished(self, found: int, saved: int):
        """Handle scan completion."""
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Complete! Found {found} signals, saved {saved}")
        self.log_text.append(f"\n✅ Scan complete: {found} signals found, {saved} saved")
        
        self.daily_scan_btn.setEnabled(True)
        self.hist_scan_btn.setEnabled(True)
        
        self._refresh_data()
        
        QMessageBox.information(
            self, "Scan Complete",
            f"Found {found} crossover signals\nSaved {saved} to database"
        )
    
    def _on_scan_error(self, error: str):
        """Handle scan error."""
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Error: {error}")
        self.log_text.append(f"\n❌ Error: {error}")
        
        self.daily_scan_btn.setEnabled(True)
        self.hist_scan_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Scan Error", str(error))


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Dark theme
    app.setStyle('Fusion')
    
    window = CrossoverScannerGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
