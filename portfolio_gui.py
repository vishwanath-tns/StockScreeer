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

# PyQtGraph for equity curve visualization
try:
    import pyqtgraph as pg
    from pyqtgraph import PlotWidget
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

import numpy as np

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
        
        # Real-time equity tracking
        self.intraday_equity = []  # List of (timestamp, pnl_percent) tuples
        self.max_intraday_points = 500  # Keep last 500 data points
        
        self.setup_ui()
        self.setWindowTitle("📊 Portfolio Manager")
        self.setMinimumSize(1200, 700)
        
        # Load portfolios
        self.refresh_portfolio_list()
        
        # Auto-update prices every 30 seconds for real-time tracking
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.realtime_update)
        self.update_timer.start(30000)  # 30 seconds
    
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
        
        # Equity Curve Panel
        equity_frame = QGroupBox("📈 Equity Curve")
        equity_frame.setStyleSheet("""
            QGroupBox {
                color: #00aaff;
                font-weight: bold;
                border: 1px solid #333;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        equity_layout = QVBoxLayout(equity_frame)
        equity_layout.setContentsMargins(5, 15, 5, 5)
        
        # Equity curve controls
        equity_controls = QHBoxLayout()
        
        record_btn = QPushButton("💾 Save to DB")
        record_btn.setToolTip("Save today's equity value to database for historical tracking")
        record_btn.clicked.connect(self.record_equity_point)
        record_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a27;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3d7a37;
            }
        """)
        equity_controls.addWidget(record_btn)
        
        # Real-time toggle
        self.realtime_check = QCheckBox("Real-time")
        self.realtime_check.setChecked(True)
        self.realtime_check.setStyleSheet("color: #00ff88;")
        self.realtime_check.setToolTip("Enable real-time equity updates every 30 seconds")
        equity_controls.addWidget(self.realtime_check)
        
        # Clear intraday button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setToolTip("Clear intraday equity data")
        clear_btn.clicked.connect(self.clear_intraday_equity)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a2727;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #7a3737;
            }
        """)
        equity_controls.addWidget(clear_btn)
        
        equity_controls.addStretch()
        
        self.equity_info_label = QLabel("Real-time tracking active")
        self.equity_info_label.setStyleSheet("color: #888;")
        equity_controls.addWidget(self.equity_info_label)
        
        equity_layout.addLayout(equity_controls)
        
        # Equity curve chart
        if HAS_PYQTGRAPH:
            self.equity_chart = pg.PlotWidget()
            self.equity_chart.setBackground('#1a1a1a')
            self.equity_chart.showGrid(x=True, y=True, alpha=0.3)
            self.equity_chart.setLabel('left', 'P&L %', color='white')
            self.equity_chart.setLabel('bottom', 'Time', color='white')
            self.equity_chart.setMinimumHeight(150)
            self.equity_chart.setMaximumHeight(200)
            
            # Add zero line
            self.equity_zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('#555555', width=1, style=Qt.PenStyle.DashLine))
            self.equity_chart.addItem(self.equity_zero_line)
            
            # Create plot items for real-time data
            self.equity_line = self.equity_chart.plot([], [], pen=pg.mkPen('#00ff88', width=2))
            self.equity_fill_pos = None
            self.equity_fill_neg = None
            
            equity_layout.addWidget(self.equity_chart)
        else:
            no_chart_label = QLabel("PyQtGraph not installed - equity chart unavailable")
            no_chart_label.setStyleSheet("color: #ff6666;")
            equity_layout.addWidget(no_chart_label)
            self.equity_chart = None
            self.equity_line = None
        
        right_layout.addWidget(equity_frame)
        
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
        
        # Clear intraday data when switching portfolios
        self.intraday_equity = []
        
        # Reset realtime checkbox when switching
        if hasattr(self, 'realtime_check') and self.realtime_check.isChecked():
            self.realtime_check.setChecked(False)
        
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
        
        # Update equity curve chart
        self.update_equity_curve()
    
    def update_equity_curve(self):
        """Update the equity curve chart with real-time intraday data."""
        if not self.current_portfolio or not HAS_PYQTGRAPH or not self.equity_chart:
            return
        
        # Clear existing plots but keep zero line
        self.equity_chart.clear()
        self.equity_chart.addItem(self.equity_zero_line)
        
        # Re-create the line plot
        self.equity_line = self.equity_chart.plot([], [], pen=pg.mkPen('#00ff88', width=2))
        
        # If we have intraday data, show it
        if self.intraday_equity:
            x = np.arange(len(self.intraday_equity))
            pnl_values = np.array([p[1] for p in self.intraday_equity])
            
            # Update line
            self.equity_line.setData(x, pnl_values)
            
            # Fill areas
            pos_fill = pg.FillBetweenItem(
                pg.PlotCurveItem(x, np.maximum(pnl_values, 0)),
                pg.PlotCurveItem(x, np.zeros(len(x))),
                brush=pg.mkBrush(0, 255, 136, 50)
            )
            self.equity_chart.addItem(pos_fill)
            
            neg_fill = pg.FillBetweenItem(
                pg.PlotCurveItem(x, np.minimum(pnl_values, 0)),
                pg.PlotCurveItem(x, np.zeros(len(x))),
                brush=pg.mkBrush(255, 68, 68, 50)
            )
            self.equity_chart.addItem(neg_fill)
            
            # Calculate stats
            current_pnl = pnl_values[-1]
            start_pnl = pnl_values[0]
            change = current_pnl - start_pnl
            high = np.max(pnl_values)
            low = np.min(pnl_values)
            
            # Format time range
            start_time = self.intraday_equity[0][0].strftime('%H:%M')
            end_time = self.intraday_equity[-1][0].strftime('%H:%M')
            
            self.equity_info_label.setText(
                f"📊 {len(self.intraday_equity)} pts ({start_time}-{end_time}) | "
                f"P&L: {current_pnl:+.2f}% | "
                f"Δ: {change:+.2f}% | "
                f"H: {high:+.2f}% L: {low:+.2f}%"
            )
        else:
            # No intraday data - try to load historical
            equity_data = self.tracker.manager.get_equity_curve(self.current_portfolio.name)
            
            if equity_data:
                x = np.arange(len(equity_data))
                pnl_values = np.array([d['total_pnl_percent'] for d in equity_data])
                
                self.equity_line.setData(x, pnl_values)
                
                # Fill areas
                pos_fill = pg.FillBetweenItem(
                    pg.PlotCurveItem(x, np.maximum(pnl_values, 0)),
                    pg.PlotCurveItem(x, np.zeros(len(x))),
                    brush=pg.mkBrush(0, 255, 136, 50)
                )
                self.equity_chart.addItem(pos_fill)
                
                neg_fill = pg.FillBetweenItem(
                    pg.PlotCurveItem(x, np.minimum(pnl_values, 0)),
                    pg.PlotCurveItem(x, np.zeros(len(x))),
                    brush=pg.mkBrush(255, 68, 68, 50)
                )
                self.equity_chart.addItem(neg_fill)
                
                self.equity_info_label.setText(
                    f"📅 {len(equity_data)} days historical | "
                    f"Current: {pnl_values[-1]:+.2f}%"
                )
            else:
                self.equity_info_label.setText("No data - waiting for real-time updates...")
    
    def add_intraday_equity_point(self):
        """Add current P&L to intraday equity data."""
        if not self.current_portfolio:
            return
        
        timestamp = datetime.now()
        pnl_percent = self.current_portfolio.total_pnl_percent
        
        self.intraday_equity.append((timestamp, pnl_percent))
        
        # Trim to max points
        if len(self.intraday_equity) > self.max_intraday_points:
            self.intraday_equity = self.intraday_equity[-self.max_intraday_points:]
    
    def clear_intraday_equity(self):
        """Clear intraday equity data."""
        self.intraday_equity = []
        self.update_equity_curve()
        self.status_bar.showMessage("Cleared intraday equity data")
    
    def realtime_update(self):
        """Real-time update for equity curve (called by timer)."""
        if not self.realtime_check.isChecked():
            return
        
        if not self.current_portfolio:
            return
        
        # Update prices silently
        self.status_bar.showMessage("Updating prices...")
        
        try:
            # Get all symbols in current portfolio
            symbols = [pos.symbol for pos in self.current_portfolio.positions]
            
            if symbols:
                # Get batch prices
                prices = self.tracker.get_prices_batch(symbols)
                
                # Update positions
                for pos in self.current_portfolio.positions:
                    if pos.symbol in prices:
                        pos.current_price = prices[pos.symbol]
                
                # Save updated portfolio
                self.tracker.manager.save_portfolio(self.current_portfolio)
                
                # Add equity point
                self.add_intraday_equity_point()
                
                # Refresh display
                self.refresh_portfolio_view()
                
                self.status_bar.showMessage(
                    f"Real-time update: {self.current_portfolio.total_pnl_percent:+.2f}% @ {datetime.now().strftime('%H:%M:%S')}"
                )
        except Exception as e:
            logger.error(f"Real-time update error: {e}")
            self.status_bar.showMessage(f"Update error: {e}")
    
    def record_equity_point(self):
        """Record current equity value to database."""
        if not self.current_portfolio:
            QMessageBox.warning(self, "No Portfolio", "Please select a portfolio first")
            return
        
        success = self.tracker.manager.record_equity_curve(self.current_portfolio.name)
        
        if success:
            self.status_bar.showMessage(f"Saved equity to database for {self.current_portfolio.name}")
            QMessageBox.information(self, "Saved", f"Equity data saved to database for {self.current_portfolio.name}")
        else:
            QMessageBox.warning(self, "Error", "Failed to record equity point")
    
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
        # Record equity curves for all portfolios after price update
        self.tracker.manager.record_all_equity_curves()
        
        self.refresh_portfolio_list()
        self.refresh_portfolio_view()
        self.status_bar.showMessage(f"Prices updated & equity recorded at {datetime.now().strftime('%H:%M:%S')}")
    
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
