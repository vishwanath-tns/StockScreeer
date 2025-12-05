"""
FNO Analysis Dashboard
Visualize option chain analysis, support/resistance levels, and futures buildup
"""

import os
import sys
from datetime import datetime, date
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QStatusBar, QTabWidget, QDateEdit
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor, QPalette

import pyqtgraph as pg
import numpy as np
import pandas as pd

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fno.services.fno_db_service import FNODBService


class FNOAnalysisDashboard(QMainWindow):
    """Main dashboard for FNO analysis visualization."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NSE F&O Analysis Dashboard")
        self.setMinimumSize(1400, 900)
        
        self.db_service = FNODBService()
        self.current_date = None
        self.current_symbol = 'NIFTY'
        
        self.setup_ui()
        self.load_available_dates()
    
    def setup_ui(self):
        """Setup the main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        
        # ─────────────────────────────────────────────────────────────────
        # TOP: Controls
        # ─────────────────────────────────────────────────────────────────
        controls = QHBoxLayout()
        
        # Date selector
        date_group = QGroupBox("📅 Trade Date")
        date_layout = QHBoxLayout(date_group)
        self.date_combo = QComboBox()
        self.date_combo.setMinimumWidth(150)
        self.date_combo.currentTextChanged.connect(self.on_date_changed)
        date_layout.addWidget(self.date_combo)
        controls.addWidget(date_group)
        
        # Symbol selector
        symbol_group = QGroupBox("📈 Symbol")
        symbol_layout = QHBoxLayout(symbol_group)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'])
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        symbol_layout.addWidget(self.symbol_combo)
        controls.addWidget(symbol_group)
        
        # Expiry selector
        expiry_group = QGroupBox("📆 Expiry")
        expiry_layout = QHBoxLayout(expiry_group)
        self.expiry_combo = QComboBox()
        self.expiry_combo.setMinimumWidth(120)
        self.expiry_combo.currentTextChanged.connect(self.on_expiry_changed)
        expiry_layout.addWidget(self.expiry_combo)
        controls.addWidget(expiry_group)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        controls.addWidget(refresh_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # ─────────────────────────────────────────────────────────────────
        # MIDDLE: Tabs
        # ─────────────────────────────────────────────────────────────────
        tabs = QTabWidget()
        
        # Tab 1: Option Chain Analysis
        option_tab = QWidget()
        self.setup_option_chain_tab(option_tab)
        tabs.addTab(option_tab, "📊 Option Chain")
        
        # Tab 2: Futures Analysis
        futures_tab = QWidget()
        self.setup_futures_tab(futures_tab)
        tabs.addTab(futures_tab, "📈 Futures Analysis")
        
        # Tab 3: Support/Resistance Summary
        sr_tab = QWidget()
        self.setup_sr_tab(sr_tab)
        tabs.addTab(sr_tab, "🎯 Support/Resistance")
        
        layout.addWidget(tabs)
        
        # ─────────────────────────────────────────────────────────────────
        # BOTTOM: Status Bar
        # ─────────────────────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Apply dark theme
        self.apply_dark_theme()
    
    def setup_option_chain_tab(self, parent: QWidget):
        """Setup option chain visualization tab."""
        layout = QVBoxLayout(parent)
        
        splitter = QSplitter(Qt.Vertical)
        
        # TOP: Summary cards
        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        
        # Key metrics cards
        self.card_underlying = self.create_card("Underlying", "-")
        summary_layout.addWidget(self.card_underlying)
        
        self.card_pcr = self.create_card("PCR (OI)", "-")
        summary_layout.addWidget(self.card_pcr)
        
        self.card_max_pain = self.create_card("Max Pain", "-")
        summary_layout.addWidget(self.card_max_pain)
        
        self.card_support = self.create_card("Support 1", "-")
        summary_layout.addWidget(self.card_support)
        
        self.card_resistance = self.create_card("Resistance 1", "-")
        summary_layout.addWidget(self.card_resistance)
        
        splitter.addWidget(summary_widget)
        
        # MIDDLE: OI Chart
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        
        self.oi_chart = pg.PlotWidget()
        self.oi_chart.setBackground('#1e1e1e')
        self.oi_chart.showGrid(x=True, y=True, alpha=0.3)
        self.oi_chart.setLabel('left', 'Open Interest', color='white')
        self.oi_chart.setLabel('bottom', 'Strike Price', color='white')
        self.oi_chart.addLegend()
        chart_layout.addWidget(self.oi_chart)
        
        splitter.addWidget(chart_widget)
        
        # BOTTOM: Option Chain Table
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        
        self.chain_table = QTableWidget()
        self.chain_table.setColumnCount(9)
        self.chain_table.setHorizontalHeaderLabels([
            'CE OI', 'CE OI Chg', 'CE LTP', 'CE Vol', 
            'Strike', 
            'PE Vol', 'PE LTP', 'PE OI Chg', 'PE OI'
        ])
        self.chain_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.style_table(self.chain_table)
        table_layout.addWidget(self.chain_table)
        
        splitter.addWidget(table_widget)
        
        splitter.setSizes([100, 300, 400])
        layout.addWidget(splitter)
    
    def setup_futures_tab(self, parent: QWidget):
        """Setup futures analysis tab."""
        layout = QVBoxLayout(parent)
        
        splitter = QSplitter(Qt.Vertical)
        
        # TOP: Interpretation counts
        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        
        self.card_long_buildup = self.create_card("Long Buildup", "0", "#28a745")
        summary_layout.addWidget(self.card_long_buildup)
        
        self.card_short_buildup = self.create_card("Short Buildup", "0", "#dc3545")
        summary_layout.addWidget(self.card_short_buildup)
        
        self.card_long_unwinding = self.create_card("Long Unwinding", "0", "#ffc107")
        summary_layout.addWidget(self.card_long_unwinding)
        
        self.card_short_covering = self.create_card("Short Covering", "0", "#17a2b8")
        summary_layout.addWidget(self.card_short_covering)
        
        splitter.addWidget(summary_widget)
        
        # BOTTOM: Futures table
        self.futures_table = QTableWidget()
        self.futures_table.setColumnCount(8)
        self.futures_table.setHorizontalHeaderLabels([
            'Symbol', 'Expiry', 'Close', 'Price Chg %', 
            'OI', 'OI Chg', 'OI Chg %', 'Interpretation'
        ])
        self.futures_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.style_table(self.futures_table)
        splitter.addWidget(self.futures_table)
        
        splitter.setSizes([100, 500])
        layout.addWidget(splitter)
    
    def setup_sr_tab(self, parent: QWidget):
        """Setup support/resistance summary tab."""
        layout = QVBoxLayout(parent)
        
        # Historical S/R table
        self.sr_table = QTableWidget()
        self.sr_table.setColumnCount(10)
        self.sr_table.setHorizontalHeaderLabels([
            'Date', 'Symbol', 'Underlying', 'PCR OI', 'Max Pain',
            'Support 1', 'Support 2', 'Resistance 1', 'Resistance 2', 'CE/PE OI Chg'
        ])
        self.sr_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.style_table(self.sr_table)
        layout.addWidget(self.sr_table)
    
    def create_card(self, title: str, value: str, color: str = "#007bff") -> QFrame:
        """Create a metric card widget."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888; font-size: 11px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        
        return card
    
    def update_card(self, card: QFrame, value: str, color: str = None):
        """Update a card's value."""
        label = card.findChild(QLabel, "value")
        if label:
            label.setText(value)
            if color:
                label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
    
    def style_table(self, table: QTableWidget):
        """Apply consistent styling to tables."""
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                color: white;
                gridline-color: #444;
            }
            QTableWidget::item:alternate {
                background-color: #353535;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 5px;
                border: 1px solid #444;
                font-weight: bold;
            }
        """)
    
    def apply_dark_theme(self):
        """Apply dark theme to the window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: #00aaff;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: white;
                padding: 8px 20px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background-color: #0d6efd;
            }
        """)
    
    def load_available_dates(self):
        """Load available trade dates from database."""
        try:
            dates = self.db_service.get_available_dates()
            self.date_combo.clear()
            for d in dates:
                self.date_combo.addItem(d.strftime('%Y-%m-%d'))
            
            if dates:
                self.current_date = dates[0]
                self.load_expiries()
        except Exception as e:
            self.status_bar.showMessage(f"Error loading dates: {e}")
    
    def load_expiries(self):
        """Load available expiries for current date and symbol."""
        if not self.current_date:
            return
        
        try:
            with self.db_service.get_connection() as conn:
                from sqlalchemy import text
                result = conn.execute(text("""
                    SELECT DISTINCT expiry_date FROM nse_options 
                    WHERE trade_date = :trade_date 
                    AND symbol = :symbol
                    ORDER BY expiry_date
                """), {'trade_date': self.current_date, 'symbol': self.current_symbol})
                expiries = [row[0] for row in result.fetchall()]
            
            self.expiry_combo.clear()
            for exp in expiries:
                self.expiry_combo.addItem(exp.strftime('%Y-%m-%d'))
            
            # Auto-select first expiry
            if expiries:
                self.expiry_combo.setCurrentIndex(0)
        except Exception as e:
            self.status_bar.showMessage(f"Error loading expiries: {e}")
    
    def on_date_changed(self, date_str: str):
        """Handle date selection change."""
        if date_str:
            self.current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            self.load_expiries()
            self.refresh_data()
    
    def on_symbol_changed(self, symbol: str):
        """Handle symbol selection change."""
        if symbol:
            self.current_symbol = symbol
            self.load_expiries()
            self.refresh_data()
    
    def on_expiry_changed(self, expiry_str: str):
        """Handle expiry selection change."""
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all data displays."""
        if not self.current_date:
            return
        
        self.status_bar.showMessage("Loading data...")
        
        try:
            # Get expiry
            expiry_str = self.expiry_combo.currentText()
            expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date() if expiry_str else None
            
            # Load option chain
            self.load_option_chain(expiry_date)
            
            # Load futures analysis
            self.load_futures_analysis()
            
            # Load S/R history
            self.load_sr_history()
            
            self.status_bar.showMessage(f"Data loaded for {self.current_date}")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error: {e}")
    
    def load_option_chain(self, expiry_date: Optional[date]):
        """Load and display option chain data."""
        # Get support/resistance analysis
        analysis = self.db_service.calculate_support_resistance(
            self.current_date, self.current_symbol, expiry_date
        )
        
        if analysis:
            # Convert Decimal to float for display
            underlying = float(analysis['underlying_price']) if analysis['underlying_price'] else 0
            pcr = float(analysis['pcr_oi']) if analysis['pcr_oi'] else 0
            max_pain = float(analysis['max_pain']) if analysis['max_pain'] else 0
            support1 = float(analysis['support_1']) if analysis['support_1'] else None
            resistance1 = float(analysis['resistance_1']) if analysis['resistance_1'] else None
            
            self.update_card(self.card_underlying, f"{underlying:,.2f}")
            self.update_card(self.card_pcr, f"{pcr:.2f}",
                           "#28a745" if pcr > 1 else "#dc3545")
            self.update_card(self.card_max_pain, f"{max_pain:,.0f}")
            self.update_card(self.card_support, f"{support1:,.0f}" if support1 else "-")
            self.update_card(self.card_resistance, f"{resistance1:,.0f}" if resistance1 else "-")
        else:
            underlying = 0
        
        # Get option chain
        chain = self.db_service.get_option_chain(self.current_date, self.current_symbol, expiry_date)
        
        if chain.empty:
            return
        
        # Filter chain to relevant strikes around ATM for cleaner display
        if underlying > 0:
            range_pct = 0.08  # 8% range
            min_strike = underlying * (1 - range_pct)
            max_strike = underlying * (1 + range_pct)
            chain = chain[(chain['strike_price'] >= min_strike) & (chain['strike_price'] <= max_strike)].copy()
        
        if chain.empty:
            return
        
        # Update chart
        self.oi_chart.clear()
        
        x = chain['strike_price'].values
        ce_oi = chain['ce_oi'].values
        pe_oi = chain['pe_oi'].values
        
        # Bar chart for OI
        bar_width = (x[1] - x[0]) * 0.35 if len(x) > 1 else 50
        
        # CE OI bars (red)
        ce_bars = pg.BarGraphItem(x=x - bar_width/2, height=ce_oi, width=bar_width,
                                   brush='#ff6b6b', pen='#ff4444', name='CE OI')
        self.oi_chart.addItem(ce_bars)
        
        # PE OI bars (green)
        pe_bars = pg.BarGraphItem(x=x + bar_width/2, height=pe_oi, width=bar_width,
                                   brush='#51cf66', pen='#40c057', name='PE OI')
        self.oi_chart.addItem(pe_bars)
        
        # Add underlying price line
        if underlying > 0:
            underlying_line = pg.InfiniteLine(
                pos=underlying,
                angle=90,
                pen=pg.mkPen('#ffd43b', width=2, style=Qt.DashLine),
                label=f"Spot: {underlying:,.0f}"
            )
            self.oi_chart.addItem(underlying_line)
        
        # Update table
        self.chain_table.setRowCount(len(chain))
        
        atm_row = 0
        
        for i, (_, row) in enumerate(chain.iterrows()):
            strike = float(row['strike_price'])
            
            # Highlight ATM row
            is_atm = underlying > 0 and abs(strike - underlying) < 100
            if is_atm:
                atm_row = i
            
            items = [
                f"{int(row['ce_oi']):,}",
                f"{int(row.get('ce_oi_change', 0)):+,}",
                f"{row['ce_ltp']:.2f}" if row['ce_ltp'] > 0 else "-",
                f"{int(row['ce_volume']):,}",
                f"{strike:,.0f}",
                f"{int(row['pe_volume']):,}",
                f"{row['pe_ltp']:.2f}" if row['pe_ltp'] > 0 else "-",
                f"{int(row.get('pe_oi_change', 0)):+,}",
                f"{int(row['pe_oi']):,}"
            ]
            
            for j, val in enumerate(items):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                
                if is_atm:
                    item.setBackground(QColor('#3d5a80'))
                
                # Color OI changes
                if j == 1:  # CE OI Change
                    chg = row.get('ce_oi_change', 0)
                    item.setForeground(QColor('#ff6b6b' if chg > 0 else '#51cf66'))
                elif j == 7:  # PE OI Change
                    chg = row.get('pe_oi_change', 0)
                    item.setForeground(QColor('#51cf66' if chg > 0 else '#ff6b6b'))
                
                self.chain_table.setItem(i, j, item)
        
        # Scroll to ATM row
        if atm_row > 0:
            self.chain_table.scrollToItem(
                self.chain_table.item(atm_row, 4),  # Strike column
                QTableWidget.PositionAtCenter
            )
    
    def load_futures_analysis(self):
        """Load and display futures analysis."""
        df = self.db_service.analyze_futures_buildup(self.current_date)
        
        if df.empty:
            return
        
        # Update summary cards
        counts = df['interpretation'].value_counts()
        self.update_card(self.card_long_buildup, str(counts.get('LONG_BUILDUP', 0)))
        self.update_card(self.card_short_buildup, str(counts.get('SHORT_BUILDUP', 0)))
        self.update_card(self.card_long_unwinding, str(counts.get('LONG_UNWINDING', 0)))
        self.update_card(self.card_short_covering, str(counts.get('SHORT_COVERING', 0)))
        
        # Update table
        self.futures_table.setRowCount(len(df))
        
        for i, (_, row) in enumerate(df.iterrows()):
            items = [
                row['symbol'],
                row['expiry_date'].strftime('%Y-%m-%d'),
                f"{row['close_price']:,.2f}",
                f"{row['price_change_pct']:+.2f}%",
                f"{int(row['open_interest']):,}",
                f"{int(row['oi_change']):+,}",
                f"{row['oi_change_pct']:+.2f}%",
                row['interpretation']
            ]
            
            for j, val in enumerate(items):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                
                # Color interpretation
                if j == 7:
                    interp = row['interpretation']
                    colors = {
                        'LONG_BUILDUP': '#28a745',
                        'SHORT_BUILDUP': '#dc3545',
                        'LONG_UNWINDING': '#ffc107',
                        'SHORT_COVERING': '#17a2b8'
                    }
                    item.setForeground(QColor(colors.get(interp, '#ffffff')))
                
                self.futures_table.setItem(i, j, item)
    
    def load_sr_history(self):
        """Load support/resistance history."""
        try:
            from sqlalchemy import text
            with self.db_service.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT * FROM option_chain_summary
                    WHERE symbol = :symbol
                    ORDER BY trade_date DESC
                    LIMIT 30
                """), {'symbol': self.current_symbol})
                
                columns = result.keys()
                rows = result.fetchall()
                
                if not rows:
                    return
                
                df = pd.DataFrame(rows, columns=columns)
            
            if df.empty:
                return
            
            self.sr_table.setRowCount(len(df))
            
            for i, (_, row) in enumerate(df.iterrows()):
                items = [
                    row['trade_date'].strftime('%Y-%m-%d') if hasattr(row['trade_date'], 'strftime') else str(row['trade_date']),
                    row['symbol'],
                    f"{row['underlying_price']:,.2f}" if row['underlying_price'] else "-",
                    f"{row['pcr_oi']:.2f}" if row['pcr_oi'] else "-",
                    f"{row['max_pain_strike']:,.0f}" if row['max_pain_strike'] else "-",
                    f"{row['support_1']:,.0f}" if row['support_1'] else "-",
                    f"{row['support_2']:,.0f}" if row['support_2'] else "-",
                    f"{row['resistance_1']:,.0f}" if row['resistance_1'] else "-",
                    f"{row['resistance_2']:,.0f}" if row['resistance_2'] else "-",
                    f"CE:{int(row['ce_oi_change'] or 0):+,} / PE:{int(row['pe_oi_change'] or 0):+,}"
                ]
                
                for j, val in enumerate(items):
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.sr_table.setItem(i, j, item)
                    
        except Exception as e:
            self.status_bar.showMessage(f"Error loading S/R history: {e}")


def main():
    """Run the analysis dashboard."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    dashboard = FNOAnalysisDashboard()
    dashboard.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
