"""FNO Cumulative OI Report Generator GUI"""
import os
import sys
from datetime import datetime
import pandas as pd
from urllib.parse import quote_plus

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QTabWidget, QFrame, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Check for reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': 'fno_marketdata'
}


class ReportWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, num_days):
        super().__init__()
        self.num_days = num_days
        
    def run(self):
        try:
            self.progress.emit("Connecting to database...")
            encoded_password = quote_plus(DB_CONFIG['password'])
            connection_string = (
                f"mysql+pymysql://{DB_CONFIG['user']}:{encoded_password}"
                f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
            )
            engine = create_engine(connection_string)
            
            self.progress.emit("Fetching available dates...")
            with engine.connect() as conn:
                result = conn.execute(text("SELECT DISTINCT trade_date FROM nse_futures ORDER BY trade_date DESC"))
                all_dates = [row[0] for row in result.fetchall()]
            
            if len(all_dates) < 2:
                self.error.emit("Need at least 2 trading days of data")
                return
            
            dates_to_use = all_dates[:min(self.num_days, len(all_dates))]
            start_date, end_date = dates_to_use[-1], dates_to_use[0]
            
            self.progress.emit(f"Analyzing {start_date} to {end_date}...")
            
            query = '''
            SELECT f.trade_date, f.symbol, f.instrument_type, f.close_price, f.open_interest
            FROM nse_futures f
            WHERE f.trade_date BETWEEN :start_date AND :end_date
            AND f.expiry_date = (
                SELECT MIN(expiry_date) FROM nse_futures f2 
                WHERE f2.symbol = f.symbol AND f2.trade_date = f.trade_date 
                AND f2.expiry_date >= f2.trade_date
            )
            ORDER BY f.symbol, f.trade_date
            '''
            
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params={'start_date': start_date, 'end_date': end_date})
            
            results = []
            for symbol in df['symbol'].unique():
                sym_df = df[df['symbol'] == symbol].sort_values('trade_date')
                if len(sym_df) < 2:
                    continue
                
                first, last = sym_df.iloc[0], sym_df.iloc[-1]
                price_chg = last['close_price'] - first['close_price']
                price_pct = (price_chg / first['close_price'] * 100) if first['close_price'] > 0 else 0
                oi_chg = last['open_interest'] - first['open_interest']
                oi_pct = (oi_chg / first['open_interest'] * 100) if first['open_interest'] > 0 else 0
                
                if price_chg > 0 and oi_chg > 0:
                    interp = 'LONG_BUILDUP'
                elif price_chg < 0 and oi_chg > 0:
                    interp = 'SHORT_BUILDUP'
                elif price_chg < 0 and oi_chg < 0:
                    interp = 'LONG_UNWINDING'
                else:
                    interp = 'SHORT_COVERING'
                
                results.append({
                    'symbol': symbol, 'instrument_type': first['instrument_type'],
                    'first_price': float(first['close_price']), 'last_price': float(last['close_price']),
                    'price_pct': round(price_pct, 2), 'first_oi': int(first['open_interest']),
                    'last_oi': int(last['open_interest']), 'oi_pct': round(oi_pct, 2),
                    'oi_change': int(oi_chg), 'interpretation': interp
                })
            
            self.finished.emit({'data': results, 'start_date': str(start_date), 'end_date': str(end_date), 'num_days': len(dates_to_use)})
        except Exception as e:
            self.error.emit(str(e))


class FNOOIReportGUI(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FNO Cumulative OI Report Generator")
        self.setMinimumSize(1200, 800)
        self.report_data = None
        self.report_info = None
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        header = QLabel("FNO Cumulative Open Interest Report")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        controls_group = QGroupBox("Report Settings")
        controls_layout = QHBoxLayout(controls_group)
        controls_layout.addWidget(QLabel("Duration:"))
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["2 Days", "3 Days", "4 Days", "5 Days", "1 Week", "2 Weeks", "All Available"])
        self.duration_combo.setCurrentIndex(2)
        self.duration_combo.setMinimumWidth(150)
        controls_layout.addWidget(self.duration_combo)
        controls_layout.addSpacing(30)
        
        self.generate_btn = QPushButton("Generate Report")
        self.generate_btn.setMinimumWidth(150)
        self.generate_btn.clicked.connect(self.generate_report)
        controls_layout.addWidget(self.generate_btn)
        controls_layout.addSpacing(20)
        
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.clicked.connect(self.export_csv)
        controls_layout.addWidget(self.export_csv_btn)
        controls_layout.addSpacing(10)
        
        self.export_pdf_btn = QPushButton("Export PDF")
        self.export_pdf_btn.setEnabled(False)
        self.export_pdf_btn.setStyleSheet("""
            QPushButton { background-color: #dc3545; color: white; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; }
            QPushButton:hover { background-color: #c82333; }
            QPushButton:disabled { background-color: #333355; color: #666688; }
        """)
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        controls_layout.addWidget(self.export_pdf_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)
        
        self.summary_frame = QFrame()
        summary_layout = QHBoxLayout(self.summary_frame)
        self.card_long = self.create_card("Long Buildup", "0", "#28a745")
        self.card_short = self.create_card("Short Buildup", "0", "#dc3545")
        self.card_unwinding = self.create_card("Long Unwinding", "0", "#e6a800")
        self.card_covering = self.create_card("Short Covering", "0", "#17a2b8")
        summary_layout.addWidget(self.card_long)
        summary_layout.addWidget(self.card_short)
        summary_layout.addWidget(self.card_unwinding)
        summary_layout.addWidget(self.card_covering)
        layout.addWidget(self.summary_frame)
        
        self.tabs = QTabWidget()
        self.index_table = self.create_table()
        self.long_table = self.create_table()
        self.short_table = self.create_table()
        self.unwinding_table = self.create_table()
        self.covering_table = self.create_table()
        self.all_table = self.create_table()
        self.tabs.addTab(self.index_table, "Index Futures")
        self.tabs.addTab(self.long_table, "Long Buildup")
        self.tabs.addTab(self.short_table, "Short Buildup")
        self.tabs.addTab(self.unwinding_table, "Long Unwinding")
        self.tabs.addTab(self.covering_table, "Short Covering")
        self.tabs.addTab(self.all_table, "All Data")
        layout.addWidget(self.tabs)
        
        self.status_label = QLabel("Ready. Select duration and click Generate Report.")
        layout.addWidget(self.status_label)
    
    def create_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 8px; padding: 10px; }}")
        card_layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)
        return card
    
    def update_card(self, card, value):
        label = card.findChild(QLabel, "value")
        if label:
            label.setText(value)
    
    def create_table(self):
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["Symbol", "Interpretation", "Price %", "OI %", "OI Change", "First Price", "Last Price"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(False)
        table.setStyleSheet("""
            QTableWidget { background-color: #1a1a2e; color: #ffffff; gridline-color: #333355; border: 1px solid #333355; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #333355; }
            QTableWidget::item:selected { background-color: #0d6efd; }
            QHeaderView::section { background-color: #16213e; color: #00d4ff; padding: 10px; border: 1px solid #333355; font-weight: bold; }
        """)
        return table
    
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f23; }
            QLabel { color: #ffffff; }
            QGroupBox { color: #00d4ff; font-weight: bold; border: 2px solid #333355; border-radius: 8px; margin-top: 12px; padding-top: 15px; background-color: #1a1a2e; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; }
            QComboBox { background-color: #1a1a2e; color: #ffffff; border: 2px solid #333355; border-radius: 5px; padding: 8px; }
            QComboBox:hover { border-color: #00d4ff; }
            QComboBox QAbstractItemView { background-color: #1a1a2e; color: #ffffff; selection-background-color: #0d6efd; }
            QPushButton { background-color: #0d6efd; color: #ffffff; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; }
            QPushButton:hover { background-color: #0b5ed7; }
            QPushButton:disabled { background-color: #333355; color: #666688; }
            QTabWidget::pane { border: 2px solid #333355; background-color: #1a1a2e; border-radius: 5px; }
            QTabBar::tab { background-color: #16213e; color: #ffffff; padding: 12px 25px; border: 1px solid #333355; border-bottom: none; font-weight: bold; }
            QTabBar::tab:selected { background-color: #1a1a2e; color: #00d4ff; border-bottom: 2px solid #00d4ff; }
            QTabBar::tab:hover { background-color: #1f2b47; }
        """)
    
    def get_duration_days(self):
        text = self.duration_combo.currentText()
        if "2 Days" in text: return 2
        if "3 Days" in text: return 3
        if "4 Days" in text: return 4
        if "5 Days" in text: return 5
        if "1 Week" in text: return 7
        if "2 Week" in text: return 14
        return 999
    
    def generate_report(self):
        self.generate_btn.setEnabled(False)
        self.export_csv_btn.setEnabled(False)
        self.export_pdf_btn.setEnabled(False)
        self.progress_label.setText("Generating report...")
        self.progress_label.setStyleSheet("color: #00d4ff;")
        self.worker = ReportWorker(self.get_duration_days())
        self.worker.progress.connect(lambda m: self.progress_label.setText(m))
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(lambda e: (self.generate_btn.setEnabled(True), QMessageBox.critical(self, "Error", e)))
        self.worker.start()
    
    def on_finished(self, result):
        self.generate_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)
        self.export_pdf_btn.setEnabled(True)
        self.report_data = result['data']
        self.report_info = result
        df = pd.DataFrame(self.report_data)
        
        self.update_card(self.card_long, str(len(df[df['interpretation'] == 'LONG_BUILDUP'])))
        self.update_card(self.card_short, str(len(df[df['interpretation'] == 'SHORT_BUILDUP'])))
        self.update_card(self.card_unwinding, str(len(df[df['interpretation'] == 'LONG_UNWINDING'])))
        self.update_card(self.card_covering, str(len(df[df['interpretation'] == 'SHORT_COVERING'])))
        
        stocks = df[df['instrument_type'] == 'FUTSTK']
        indices = df[df['instrument_type'] == 'FUTIDX']
        
        self.populate_table(self.index_table, indices)
        self.populate_table(self.long_table, stocks[stocks['interpretation'] == 'LONG_BUILDUP'].sort_values('oi_pct', ascending=False))
        self.populate_table(self.short_table, stocks[stocks['interpretation'] == 'SHORT_BUILDUP'].sort_values('oi_pct', ascending=False))
        self.populate_table(self.unwinding_table, stocks[stocks['interpretation'] == 'LONG_UNWINDING'])
        self.populate_table(self.covering_table, stocks[stocks['interpretation'] == 'SHORT_COVERING'])
        self.populate_table(self.all_table, df)
        
        self.progress_label.setText("")
        self.status_label.setText(f"Report: {result['start_date']} to {result['end_date']} ({result['num_days']} days, {len(df)} symbols)")
        self.status_label.setStyleSheet("color: #00ff88;")
    
    def populate_table(self, table, df):
        table.setRowCount(0)
        for row_num, (_, row) in enumerate(df.iterrows()):
            idx = table.rowCount()
            table.insertRow(idx)
            row_color = QColor("#1a1a2e") if row_num % 2 == 0 else QColor("#12122a")
            
            symbol_item = QTableWidgetItem(row['symbol'])
            symbol_item.setForeground(QColor("#ffffff"))
            symbol_item.setBackground(row_color)
            table.setItem(idx, 0, symbol_item)
            
            interp_item = QTableWidgetItem(row['interpretation'])
            interp_colors = {'LONG_BUILDUP': "#00ff88", 'SHORT_BUILDUP': "#ff4466", 'LONG_UNWINDING': "#ffcc00", 'SHORT_COVERING': "#00ccff"}
            interp_item.setForeground(QColor(interp_colors.get(row['interpretation'], "#ffffff")))
            interp_item.setBackground(row_color)
            table.setItem(idx, 1, interp_item)
            
            price_item = QTableWidgetItem(f"{row['price_pct']:+.2f}%")
            price_item.setForeground(QColor("#00ff88" if row['price_pct'] > 0 else "#ff4466"))
            price_item.setBackground(row_color)
            table.setItem(idx, 2, price_item)
            
            oi_pct_item = QTableWidgetItem(f"{row['oi_pct']:+.2f}%")
            oi_pct_item.setForeground(QColor("#00ff88" if row['oi_pct'] > 0 else "#ff4466"))
            oi_pct_item.setBackground(row_color)
            table.setItem(idx, 3, oi_pct_item)
            
            for col, val in [(4, f"{row['oi_change']:+,}"), (5, f"{row['first_price']:,.2f}"), (6, f"{row['last_price']:,.2f}")]:
                item = QTableWidgetItem(val)
                item.setForeground(QColor("#cccccc"))
                item.setBackground(row_color)
                table.setItem(idx, col, item)
    
    def export_csv(self):
        if not self.report_data:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save CSV", f"fno_oi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV (*.csv)")
        if filename:
            pd.DataFrame(self.report_data).to_csv(filename, index=False)
            QMessageBox.information(self, "Success", f"Saved to {filename}")
    
    def export_pdf(self):
        if not self.report_data:
            return
        
        if not HAS_REPORTLAB:
            QMessageBox.warning(self, "Missing Package", "PDF export requires 'reportlab' package.\n\nInstall with: pip install reportlab")
            return
        
        filename, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"fno_oi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", "PDF (*.pdf)")
        if not filename:
            return
        
        try:
            self.generate_pdf(filename)
            QMessageBox.information(self, "Success", f"PDF saved to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")
    
    def generate_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4), leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, spaceAfter=20, alignment=1, textColor=colors.darkblue)
        elements.append(Paragraph("FNO Cumulative Open Interest Report", title_style))
        
        # Info
        info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=11, spaceAfter=10, alignment=1)
        elements.append(Paragraph(f"Period: {self.report_info['start_date']} to {self.report_info['end_date']} ({self.report_info['num_days']} trading days)", info_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style))
        elements.append(Spacer(1, 20))
        
        df = pd.DataFrame(self.report_data)
        stocks = df[df['instrument_type'] == 'FUTSTK']
        
        # Summary table
        elements.append(Paragraph("Summary", styles['Heading2']))
        summary_data = [
            ['Category', 'Count', 'Interpretation'],
            ['Long Buildup', str(len(stocks[stocks['interpretation'] == 'LONG_BUILDUP'])), 'Bullish - Fresh buying'],
            ['Short Buildup', str(len(stocks[stocks['interpretation'] == 'SHORT_BUILDUP'])), 'Bearish - Fresh selling'],
            ['Long Unwinding', str(len(stocks[stocks['interpretation'] == 'LONG_UNWINDING'])), 'Weak - Profit booking by longs'],
            ['Short Covering', str(len(stocks[stocks['interpretation'] == 'SHORT_COVERING'])), 'Recovery - Shorts exiting']
        ]
        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 25))
        
        # Category tables
        categories = [
            ('Long Buildup (Bullish)', 'LONG_BUILDUP', colors.green),
            ('Short Buildup (Bearish)', 'SHORT_BUILDUP', colors.red),
            ('Long Unwinding', 'LONG_UNWINDING', colors.orange),
            ('Short Covering', 'SHORT_COVERING', colors.blue)
        ]
        
        for title, interp, header_color in categories:
            cat_df = stocks[stocks['interpretation'] == interp].sort_values('oi_pct', ascending=(interp == 'LONG_UNWINDING'))
            if cat_df.empty:
                continue
            
            elements.append(Paragraph(f"{title} ({len(cat_df)} stocks)", styles['Heading2']))
            
            table_data = [['Symbol', 'Price %', 'OI %', 'OI Change', 'First Price', 'Last Price']]
            for _, row in cat_df.head(25).iterrows():
                table_data.append([
                    row['symbol'],
                    f"{row['price_pct']:+.2f}%",
                    f"{row['oi_pct']:+.2f}%",
                    f"{row['oi_change']:+,}",
                    f"{row['first_price']:,.2f}",
                    f"{row['last_price']:,.2f}"
                ])
            
            t = Table(table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1.2*inch, 1.2*inch, 1.2*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))
        
        doc.build(elements)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = FNOOIReportGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
