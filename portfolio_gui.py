#!/usr/bin/env python3
"""
Portfolio Manager GUI
=====================

Visual interface to manage portfolios created from scanners.

Usage:
    python portfolio_gui.py
"""

import sys
import logging
from datetime import datetime, date
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QProgressBar,
    QTabWidget, QGroupBox, QSpinBox, QComboBox, QSplitter, QStatusBar,
    QHeaderView, QMessageBox, QFrame, QLineEdit, QDialog, QFormLayout,
    QDialogButtonBox, QTextEdit, QListWidget, QListWidgetItem, QMenu,
    QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush, QAction

from portfolio import PortfolioTracker, Portfolio, Position, PortfolioType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Scanner Types for portfolio creation
SCANNER_TYPES = {
    "Volume Analysis": {
        "accumulation": "Top Accumulation (BUY)",
        "distribution": "Top Distribution (AVOID)",
    },
    "Stock Rankings": {
        "leaders": "Market Leaders (RS 80+, Composite 90%)",
        "momentum": "High Momentum (Top 20)",
        "trend_template": "Trend Template Passed",
    },
    "Bollinger Bands": {
        "squeeze": "Squeeze (Low Volatility Breakout)",
        "pullback": "Pullback to Middle Band",
        "bulge": "Bulge (High Volatility)",
    }
}


class PriceUpdateWorker(QThread):
    """Background worker for updating prices."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, tracker: PortfolioTracker):
        super().__init__()
        self.tracker = tracker
    
    def run(self):
        try:
            self.tracker.update_all_prices()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class CreatePortfolioDialog(QDialog):
    """Dialog to create a new portfolio."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Portfolio")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit()
        layout.addRow("Portfolio Name:", self.name_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([t.value for t in PortfolioType])
        layout.addRow("Type:", self.type_combo)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        layout.addRow("Description:", self.desc_edit)
        
        self.symbols_edit = QTextEdit()
        self.symbols_edit.setPlaceholderText("Enter symbols, one per line (e.g., RELIANCE.NS)")
        layout.addRow("Symbols:", self.symbols_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        symbols = [s.strip() for s in self.symbols_edit.toPlainText().split('\n') if s.strip()]
        return {
            'name': self.name_edit.text(),
            'type': PortfolioType(self.type_combo.currentText()),
            'description': self.desc_edit.toPlainText(),
            'symbols': symbols
        }


class ScannerSelectionDialog(QDialog):
    """Dialog to select scanner type for portfolio creation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Portfolio from Scanner")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel(
            "Select scanners to create portfolios. Each selected scanner will create a separate portfolio."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaa; padding: 5px;")
        layout.addWidget(info)
        
        # Scanner selection with checkboxes
        self.scanner_checks = {}
        
        for category, scanners in SCANNER_TYPES.items():
            group = QGroupBox(category)
            group_layout = QVBoxLayout(group)
            
            for key, name in scanners.items():
                check = QCheckBox(name)
                check.setProperty("scanner_key", f"{category}:{key}")
                self.scanner_checks[f"{category}:{key}"] = check
                group_layout.addWidget(check)
            
            layout.addWidget(group)
        
        # Max positions
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max positions per portfolio:"))
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(5, 50)
        self.max_positions_spin.setValue(15)
        max_layout.addWidget(self.max_positions_spin)
        max_layout.addStretch()
        layout.addLayout(max_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_selected_scanners(self):
        """Get list of selected scanner keys."""
        selected = []
        for key, check in self.scanner_checks.items():
            if check.isChecked():
                selected.append(key)
        return selected
    
    def get_max_positions(self):
        return self.max_positions_spin.value()


class PortfolioGUI(QMainWindow):
    """Main GUI window for portfolio management."""
    
    def __init__(self):
        super().__init__()
        self.tracker = PortfolioTracker()
        self.current_portfolio = None
        self.worker = None
        
        self.setup_ui()
        self.setWindowTitle("📊 Portfolio Manager")
        self.setMinimumSize(1200, 700)
        
        # Load portfolios
        self.refresh_portfolio_list()
        
        # Auto-update prices every 5 minutes
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_prices)
        self.update_timer.start(300000)  # 5 minutes
    
    def setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Left panel - Portfolio list
        left_panel = QGroupBox("📁 Portfolios")
        left_panel.setMaximumWidth(250)
        left_layout = QVBoxLayout(left_panel)
        
        # Portfolio list
        self.portfolio_list = QListWidget()
        self.portfolio_list.itemClicked.connect(self.on_portfolio_selected)
        self.portfolio_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.portfolio_list.customContextMenuRequested.connect(self.show_portfolio_context_menu)
        left_layout.addWidget(self.portfolio_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("➕ New")
        new_btn.clicked.connect(self.create_portfolio)
        btn_layout.addWidget(new_btn)
        
        from_scanner_btn = QPushButton("📊 From Scanner")
        from_scanner_btn.clicked.connect(self.create_from_scanner)
        btn_layout.addWidget(from_scanner_btn)
        
        left_layout.addLayout(btn_layout)
        
        refresh_btn = QPushButton("🔄 Update Prices")
        refresh_btn.clicked.connect(self.update_prices)
        left_layout.addWidget(refresh_btn)
        
        layout.addWidget(left_panel)
        
        # Right panel - Portfolio details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Summary bar
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border-radius: 5px;
                padding: 10px;
            }
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        
        self.portfolio_name_label = QLabel("Select a portfolio")
        self.portfolio_name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.portfolio_name_label.setStyleSheet("color: #00ccff;")
        summary_layout.addWidget(self.portfolio_name_label)
        
        summary_layout.addStretch()
        
        self.positions_label = QLabel("Positions: -")
        self.positions_label.setStyleSheet("color: white;")
        summary_layout.addWidget(self.positions_label)
        
        self.pnl_label = QLabel("P&L: -")
        self.pnl_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        summary_layout.addWidget(self.pnl_label)
        
        self.winrate_label = QLabel("Win Rate: -")
        self.winrate_label.setStyleSheet("color: white;")
        summary_layout.addWidget(self.winrate_label)
        
        right_layout.addWidget(self.summary_frame)
        
        # Positions table
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(8)
        self.positions_table.setHorizontalHeaderLabels([
            "Symbol", "Entry Date", "Entry Price", "Current Price", 
            "P&L %", "Score", "Signal", "Notes"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.verticalHeader().setDefaultSectionSize(25)
        self.positions_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #333;
                background-color: #1a1a1a;
                alternate-background-color: #222;
            }
            QHeaderView::section {
                background-color: #2d2d44;
                color: white;
                padding: 5px;
                font-weight: bold;
            }
        """)
        right_layout.addWidget(self.positions_table)
        
        # Stats panel
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background: #1a1a1a; border-radius: 5px; padding: 5px;")
        stats_frame.setMaximumHeight(80)
        stats_layout = QHBoxLayout(stats_frame)
        
        self.avg_gain_label = QLabel("Avg Gain: -")
        self.avg_gain_label.setStyleSheet("color: #00ff00;")
        stats_layout.addWidget(self.avg_gain_label)
        
        self.avg_loss_label = QLabel("Avg Loss: -")
        self.avg_loss_label.setStyleSheet("color: #ff4444;")
        stats_layout.addWidget(self.avg_loss_label)
        
        self.best_label = QLabel("Best: -")
        self.best_label.setStyleSheet("color: #00ff00;")
        stats_layout.addWidget(self.best_label)
        
        self.worst_label = QLabel("Worst: -")
        self.worst_label.setStyleSheet("color: #ff4444;")
        stats_layout.addWidget(self.worst_label)
        
        stats_layout.addStretch()
        
        export_btn = QPushButton("📥 Export CSV")
        export_btn.clicked.connect(self.export_portfolio)
        stats_layout.addWidget(export_btn)
        
        right_layout.addWidget(stats_frame)
        
        layout.addWidget(right_panel, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def refresh_portfolio_list(self):
        """Refresh the portfolio list."""
        self.portfolio_list.clear()
        
        for name in self.tracker.manager.list_portfolios():
            portfolio = self.tracker.manager.get_portfolio(name)
            
            # Create item with emoji based on P&L
            if portfolio.total_pnl_percent > 5:
                emoji = "🟢"
            elif portfolio.total_pnl_percent > 0:
                emoji = "🔵"
            elif portfolio.total_pnl_percent > -5:
                emoji = "🟡"
            else:
                emoji = "🔴"
            
            item = QListWidgetItem(f"{emoji} {name}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.portfolio_list.addItem(item)
    
    def on_portfolio_selected(self, item: QListWidgetItem):
        """Handle portfolio selection."""
        name = item.data(Qt.ItemDataRole.UserRole)
        self.current_portfolio = self.tracker.manager.get_portfolio(name)
        self.refresh_portfolio_view()
    
    def refresh_portfolio_view(self):
        """Refresh the portfolio details view."""
        if not self.current_portfolio:
            return
        
        portfolio = self.current_portfolio
        
        # Update summary
        self.portfolio_name_label.setText(f"📊 {portfolio.name}")
        self.positions_label.setText(f"Positions: {portfolio.total_positions}")
        
        pnl = portfolio.total_pnl_percent
        pnl_color = "#00ff00" if pnl > 0 else "#ff4444" if pnl < 0 else "white"
        self.pnl_label.setText(f"P&L: {pnl:+.2f}%")
        self.pnl_label.setStyleSheet(f"color: {pnl_color}; font-weight: bold;")
        
        self.winrate_label.setText(f"Win Rate: {portfolio.win_rate:.0f}%")
        
        # Update stats
        self.avg_gain_label.setText(f"Avg Gain: {portfolio.avg_gain:+.2f}%")
        self.avg_loss_label.setText(f"Avg Loss: {portfolio.avg_loss:+.2f}%")
        
        if portfolio.winners:
            best = max(portfolio.winners, key=lambda x: x.pnl_percent)
            self.best_label.setText(f"Best: {best.symbol} ({best.pnl_percent:+.1f}%)")
        
        if portfolio.losers:
            worst = min(portfolio.losers, key=lambda x: x.pnl_percent)
            self.worst_label.setText(f"Worst: {worst.symbol} ({worst.pnl_percent:+.1f}%)")
        
        # Update table
        self.positions_table.setRowCount(len(portfolio.positions))
        
        # Sort by P&L
        sorted_positions = sorted(portfolio.positions, key=lambda x: x.pnl_percent, reverse=True)
        
        for row, pos in enumerate(sorted_positions):
            # Symbol
            symbol_item = QTableWidgetItem(pos.symbol.replace('.NS', ''))
            symbol_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.positions_table.setItem(row, 0, symbol_item)
            
            # Entry Date
            self.positions_table.setItem(row, 1, QTableWidgetItem(pos.entry_date))
            
            # Entry Price
            entry_item = QTableWidgetItem(f"₹{pos.entry_price:.2f}")
            entry_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.positions_table.setItem(row, 2, entry_item)
            
            # Current Price
            current_item = QTableWidgetItem(f"₹{pos.current_price:.2f}")
            current_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.positions_table.setItem(row, 3, current_item)
            
            # P&L %
            pnl_item = QTableWidgetItem(f"{pos.pnl_percent:+.2f}%")
            pnl_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if pos.pnl_percent > 5:
                pnl_item.setBackground(QBrush(QColor("#004400")))
                pnl_item.setForeground(QBrush(QColor("#00ff00")))
            elif pos.pnl_percent > 0:
                pnl_item.setForeground(QBrush(QColor("#00ff00")))
            elif pos.pnl_percent < -5:
                pnl_item.setBackground(QBrush(QColor("#440000")))
                pnl_item.setForeground(QBrush(QColor("#ff4444")))
            elif pos.pnl_percent < 0:
                pnl_item.setForeground(QBrush(QColor("#ff4444")))
            self.positions_table.setItem(row, 4, pnl_item)
            
            # Score
            score_item = QTableWidgetItem(f"{pos.scanner_score:.1f}" if pos.scanner_score else "-")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.positions_table.setItem(row, 5, score_item)
            
            # Signal
            signal_item = QTableWidgetItem(pos.scanner_signal)
            self.positions_table.setItem(row, 6, signal_item)
            
            # Notes
            self.positions_table.setItem(row, 7, QTableWidgetItem(pos.notes))
    
    def create_portfolio(self):
        """Create a new portfolio manually."""
        dialog = CreatePortfolioDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data['name']:
                QMessageBox.warning(self, "Error", "Portfolio name is required")
                return
            
            if data['symbols']:
                portfolio = self.tracker.create_custom_portfolio(
                    symbols=data['symbols'],
                    name=data['name'],
                    description=data['description']
                )
            else:
                portfolio = self.tracker.manager.create_portfolio(
                    name=data['name'],
                    portfolio_type=data['type'],
                    description=data['description']
                )
            
            self.refresh_portfolio_list()
            self.status_bar.showMessage(f"Created portfolio: {data['name']}")
    
    def create_from_scanner(self):
        """Create portfolio from scanner results."""
        dialog = ScannerSelectionDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        selected = dialog.get_selected_scanners()
        max_positions = dialog.get_max_positions()
        
        if not selected:
            QMessageBox.warning(self, "Error", "Please select at least one scanner")
            return
        
        self.status_bar.showMessage("Running scanners...")
        QApplication.processEvents()
        
        created_portfolios = []
        
        for scanner_key in selected:
            try:
                category, scan_type = scanner_key.split(":")
                portfolio = self._run_scanner(category, scan_type, max_positions)
                if portfolio:
                    created_portfolios.append(portfolio.name)
            except Exception as e:
                logger.error(f"Scanner {scanner_key} failed: {e}")
                self.status_bar.showMessage(f"Error in {scanner_key}: {e}")
        
        self.refresh_portfolio_list()
        
        if created_portfolios:
            self.status_bar.showMessage(f"Created portfolios: {', '.join(created_portfolios)}")
        else:
            QMessageBox.warning(self, "No Results", "No portfolios were created. Check scanner data.")
    
    def _run_scanner(self, category: str, scan_type: str, max_positions: int):
        """Run a specific scanner and create portfolio."""
        today = date.today().strftime('%b %d')
        
        if category == "Volume Analysis":
            return self._run_volume_scanner(scan_type, max_positions, today)
        elif category == "Stock Rankings":
            return self._run_rankings_scanner(scan_type, max_positions, today)
        elif category == "Bollinger Bands":
            return self._run_bb_scanner(scan_type, max_positions, today)
        
        return None
    
    def _run_volume_scanner(self, scan_type: str, max_positions: int, today: str):
        """Run volume analysis scanner."""
        try:
            from volume_analysis import VolumeScanner
            
            self.status_bar.showMessage("Running Volume Analysis scanner...")
            QApplication.processEvents()
            
            scanner = VolumeScanner(lookback_days=180, min_volume=100000)
            results = scanner.scan_nifty500()
            
            if scan_type == "accumulation":
                return self.tracker.create_accumulation_portfolio(
                    results.accumulation[:max_positions],
                    name=f"Accumulation {today}",
                    min_score=60
                )
            elif scan_type == "distribution":
                return self.tracker.create_distribution_portfolio(
                    results.distribution[:max_positions],
                    name=f"Distribution {today}",
                    max_score=30
                )
        except ImportError:
            QMessageBox.warning(self, "Error", "Volume analysis module not available")
        except Exception as e:
            logger.error(f"Volume scanner error: {e}")
        
        return None
    
    def _run_rankings_scanner(self, scan_type: str, max_positions: int, today: str):
        """Run stock rankings scanner."""
        try:
            from sqlalchemy import text
            from ranking.db.schema import get_ranking_engine
            
            engine = get_ranking_engine()
            
            self.status_bar.showMessage("Fetching stock rankings...")
            QApplication.processEvents()
            
            # Get latest calculation date
            with engine.connect() as conn:
                date_result = conn.execute(text("SELECT MAX(calculation_date) FROM stock_rankings"))
                latest_date = date_result.scalar()
            
            if not latest_date:
                QMessageBox.warning(self, "Error", "No stock rankings data found")
                return None
            
            # Query based on scan type
            if scan_type == "leaders":
                query = """
                    SELECT symbol, rs_rating, momentum_score, trend_template_score, 
                           composite_score, composite_percentile
                    FROM stock_rankings
                    WHERE calculation_date = :calc_date
                    AND rs_rating >= 80 AND composite_percentile >= 90
                    ORDER BY composite_score DESC
                    LIMIT :limit
                """
                name = f"Market Leaders {today}"
            elif scan_type == "momentum":
                query = """
                    SELECT symbol, rs_rating, momentum_score, trend_template_score,
                           composite_score, composite_percentile
                    FROM stock_rankings
                    WHERE calculation_date = :calc_date
                    ORDER BY momentum_score DESC
                    LIMIT :limit
                """
                name = f"High Momentum {today}"
            elif scan_type == "trend_template":
                query = """
                    SELECT symbol, rs_rating, momentum_score, trend_template_score,
                           composite_score, composite_percentile
                    FROM stock_rankings
                    WHERE calculation_date = :calc_date
                    AND trend_template_score = 8
                    ORDER BY composite_score DESC
                    LIMIT :limit
                """
                name = f"Trend Template {today}"
            else:
                return None
            
            with engine.connect() as conn:
                result = conn.execute(text(query), {"calc_date": latest_date, "limit": max_positions})
                rows = result.fetchall()
            
            if not rows:
                logger.warning(f"No results for {scan_type} rankings")
                return None
            
            # Create portfolio
            portfolio = self.tracker.manager.create_portfolio(
                name=name,
                portfolio_type=PortfolioType.MOMENTUM,
                description=f"Created from {scan_type} rankings scanner"
            )
            
            for row in rows:
                symbol = row[0]
                price = self.tracker.get_price(symbol)
                
                # Convert Decimal to float for JSON serialization
                rs_rating = float(row[1]) if row[1] else 0
                momentum = float(row[2]) if row[2] else 0
                trend_template = float(row[3]) if row[3] else 0
                composite = float(row[4]) if row[4] else 0
                percentile = float(row[5]) if row[5] else 0
                
                position = Position(
                    symbol=symbol,
                    entry_date=date.today().isoformat(),
                    entry_price=price,
                    current_price=price,
                    scanner_score=composite,
                    scanner_signal=f"RS:{rs_rating:.0f} Mom:{momentum:.0f} TT:{trend_template:.0f}",
                    notes=f"Composite: {composite:.1f}, Percentile: {percentile:.0f}%"
                )
                portfolio.add_position(position)
            
            self.tracker.manager.save_portfolio(portfolio)
            return portfolio
            
        except Exception as e:
            logger.error(f"Rankings scanner error: {e}")
            QMessageBox.warning(self, "Error", f"Rankings scanner failed: {e}")
        
        return None
    
    def _run_bb_scanner(self, scan_type: str, max_positions: int, today: str):
        """Run Bollinger Bands scanner."""
        try:
            from sqlalchemy import text
            from bollinger.db.bb_schema import get_bb_engine
            
            engine = get_bb_engine()
            
            self.status_bar.showMessage("Running Bollinger Bands scanner...")
            QApplication.processEvents()
            
            # Get latest date
            with engine.connect() as conn:
                date_result = conn.execute(text("SELECT MAX(trade_date) FROM stock_bollinger_daily"))
                latest_date = date_result.scalar()
            
            if not latest_date:
                QMessageBox.warning(self, "Error", "No Bollinger Bands data found")
                return None
            
            # Query based on scan type
            if scan_type == "squeeze":
                # Squeeze: Low BandWidth percentile (volatility contraction)
                query = """
                    SELECT symbol, close, percent_b, bandwidth, bandwidth_percentile
                    FROM stock_bollinger_daily
                    WHERE trade_date = :latest_date
                    AND bandwidth_percentile <= 15
                    ORDER BY bandwidth_percentile ASC
                    LIMIT :limit
                """
                name = f"BB Squeeze {today}"
                signal_fmt = lambda r: f"Squeeze: BW%={r[4]:.1f}"
            elif scan_type == "pullback":
                # Pullback: Price near middle band (good entry)
                query = """
                    SELECT symbol, close, percent_b, bandwidth, bandwidth_percentile
                    FROM stock_bollinger_daily
                    WHERE trade_date = :latest_date
                    AND percent_b BETWEEN 0.4 AND 0.6
                    AND bandwidth_percentile > 30
                    ORDER BY ABS(percent_b - 0.5) ASC
                    LIMIT :limit
                """
                name = f"BB Pullback {today}"
                signal_fmt = lambda r: f"Pullback: %B={r[2]:.2f}"
            elif scan_type == "bulge":
                # Bulge: High BandWidth (volatility expansion)
                query = """
                    SELECT symbol, close, percent_b, bandwidth, bandwidth_percentile
                    FROM stock_bollinger_daily
                    WHERE trade_date = :latest_date
                    AND bandwidth_percentile >= 85
                    ORDER BY bandwidth_percentile DESC
                    LIMIT :limit
                """
                name = f"BB Bulge {today}"
                signal_fmt = lambda r: f"Bulge: BW%={r[4]:.1f}"
            else:
                return None
            
            with engine.connect() as conn:
                result = conn.execute(text(query), {"latest_date": latest_date, "limit": max_positions})
                rows = result.fetchall()
            
            if not rows:
                logger.warning(f"No results for {scan_type} BB scan")
                return None
            
            # Create portfolio
            portfolio = self.tracker.manager.create_portfolio(
                name=name,
                portfolio_type=PortfolioType.CUSTOM,
                description=f"Bollinger Bands {scan_type} scanner - {latest_date}"
            )
            
            for row in rows:
                symbol = row[0]
                price = float(row[1]) if row[1] else self.tracker.get_price(symbol)
                
                # Convert Decimal to float for JSON serialization
                percent_b = float(row[2]) if row[2] else 0
                bandwidth = float(row[3]) if row[3] else 0
                bw_percentile = float(row[4]) if row[4] else 0
                
                position = Position(
                    symbol=symbol,
                    entry_date=date.today().isoformat(),
                    entry_price=price,
                    current_price=price,
                    scanner_score=100 - bw_percentile if scan_type == "squeeze" else bw_percentile,
                    scanner_signal=f"BW%={bw_percentile:.1f}" if scan_type != "pullback" else f"%B={percent_b:.2f}",
                    notes=f"%B: {percent_b:.2f}, BW: {bandwidth:.2f}"
                )
                portfolio.add_position(position)
            
            self.tracker.manager.save_portfolio(portfolio)
            return portfolio
            
        except Exception as e:
            logger.error(f"BB scanner error: {e}")
            QMessageBox.warning(self, "Error", f"BB scanner failed: {e}")
        
        return None
    
    def update_prices(self):
        """Update prices for all portfolios."""
        if self.worker and self.worker.isRunning():
            return
        
        self.status_bar.showMessage("Updating prices...")
        
        self.worker = PriceUpdateWorker(self.tracker)
        self.worker.finished.connect(self.on_prices_updated)
        self.worker.error.connect(lambda e: self.status_bar.showMessage(f"Error: {e}"))
        self.worker.start()
    
    def on_prices_updated(self):
        """Handle price update completion."""
        self.refresh_portfolio_list()
        self.refresh_portfolio_view()
        self.status_bar.showMessage(f"Prices updated at {datetime.now().strftime('%H:%M:%S')}")
    
    def show_portfolio_context_menu(self, position):
        """Show context menu for portfolio list."""
        item = self.portfolio_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        delete_action = QAction("🗑️ Delete Portfolio", self)
        delete_action.triggered.connect(lambda: self.delete_portfolio(item))
        menu.addAction(delete_action)
        
        export_action = QAction("📥 Export to CSV", self)
        export_action.triggered.connect(self.export_portfolio)
        menu.addAction(export_action)
        
        menu.exec(self.portfolio_list.mapToGlobal(position))
    
    def delete_portfolio(self, item: QListWidgetItem):
        """Delete a portfolio."""
        name = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Delete Portfolio",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.tracker.delete_portfolio(name)
            self.refresh_portfolio_list()
            self.current_portfolio = None
            self.positions_table.setRowCount(0)
            self.status_bar.showMessage(f"Deleted portfolio: {name}")
    
    def export_portfolio(self):
        """Export current portfolio to CSV."""
        if not self.current_portfolio:
            QMessageBox.warning(self, "Error", "No portfolio selected")
            return
        
        filename = self.tracker.export_portfolio(self.current_portfolio.name, "csv")
        self.status_bar.showMessage(f"Exported to {filename}")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Dark theme
    app.setStyle("Fusion")
    
    from PyQt6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    app.setPalette(palette)
    
    window = PortfolioGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
