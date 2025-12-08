"""
Market Exhaustion Visualizer
============================
PyQtGraph-based visualization for market exhaustion indicators.

Features:
- Price chart with index
- Breadth indicators with overbought/oversold zones
- Divergence detection visualization
- Risk score gauge
- Portfolio protection dashboard
"""

import sys
from datetime import datetime, date
from typing import Optional, Dict

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar, QStatusBar,
    QApplication, QSplitter, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from .daily_detector import (
    DailyExhaustionDetector, ExhaustionReading, ProtectionSignal,
    MarketSignal, DivergenceType
)


# Color scheme
COLORS = {
    'extreme_overbought': '#FF0000',  # Red
    'overbought': '#FF6B00',          # Orange
    'neutral': '#00AA00',             # Green
    'oversold': '#FFD700',            # Yellow
    'extreme_oversold': '#0066FF',    # Blue
    'bullish_div': '#00FF00',         # Bright green
    'bearish_div': '#FF0066',         # Pink
    'background': '#1E1E1E',
    'text': '#FFFFFF',
    'grid': '#333333',
}


class DataLoaderThread(QThread):
    """Background thread for loading data."""
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(object, object, object)  # breadth_df, reading, signal
    error = pyqtSignal(str)
    
    def __init__(self, detector):
        super().__init__()
        self.detector = detector
    
    def run(self):
        try:
            self.progress.emit("Fetching data...", 10)
            index_df, stock_data = self.detector.fetch_daily_data(days=250)
            
            self.progress.emit("Calculating breadth...", 50)
            breadth_df = self.detector.calculate_daily_breadth(index_df, stock_data)
            
            self.progress.emit("Analyzing signals...", 80)
            reading = self.detector.get_current_reading()
            signal = self.detector.generate_protection_signal()
            
            self.progress.emit("Done!", 100)
            self.finished.emit(breadth_df, reading, signal)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class RiskGauge(QWidget):
    """Visual risk score gauge."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.risk_score = 50
        self.setMinimumSize(200, 120)
        
    def set_risk(self, score: int):
        self.risk_score = max(0, min(100, score))
        self.update()
        
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QBrush, QPen, QLinearGradient
        from PyQt5.QtCore import QRectF
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor('#2D2D2D'))
        
        # Draw gauge background
        w, h = self.width(), self.height()
        bar_height = 30
        bar_y = h // 2 - bar_height // 2
        margin = 20
        bar_width = w - 2 * margin
        
        # Gradient bar
        gradient = QLinearGradient(margin, 0, margin + bar_width, 0)
        gradient.setColorAt(0.0, QColor('#00AA00'))   # Green (low risk)
        gradient.setColorAt(0.5, QColor('#FFD700'))   # Yellow (medium)
        gradient.setColorAt(0.8, QColor('#FF6600'))   # Orange (high)
        gradient.setColorAt(1.0, QColor('#FF0000'))   # Red (extreme)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(margin, bar_y, bar_width, bar_height, 5, 5)
        
        # Draw position indicator
        pos_x = margin + (self.risk_score / 100) * bar_width
        painter.setBrush(QBrush(QColor('#FFFFFF')))
        painter.setPen(QPen(QColor('#000000'), 2))
        painter.drawEllipse(int(pos_x) - 8, bar_y - 5, 16, bar_height + 10)
        
        # Draw score text
        painter.setPen(QColor('#FFFFFF'))
        font = QFont('Segoe UI', 14, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignHCenter | Qt.AlignTop, f"Risk Score: {self.risk_score}")
        
        # Draw labels
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(margin, bar_y + bar_height + 20, "LOW")
        painter.drawText(w - margin - 50, bar_y + bar_height + 20, "EXTREME")


class ExhaustionVisualizer(QMainWindow):
    """Main visualization window for market exhaustion detection."""
    
    def __init__(self):
        super().__init__()
        
        self.detector = DailyExhaustionDetector(use_db=False)
        self.breadth_df = None
        self.current_reading = None
        self.protection_signal = None
        
        self._init_ui()
        
        # Auto-load on startup
        QTimer.singleShot(100, self._load_data)
    
    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("📊 Market Exhaustion Detector - Portfolio Protection")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("🛡️ MARKET EXHAUSTION DETECTOR - PORTFOLIO PROTECTION SYSTEM")
        title.setFont(QFont('Segoe UI', 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FFD700; padding: 10px;")
        main_layout.addWidget(title)
        
        # Main splitter (left: charts, right: signals)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, stretch=1)
        
        # Left panel - Charts
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create charts
        self._create_charts(charts_layout)
        splitter.addWidget(charts_widget)
        
        # Right panel - Signals
        signals_widget = QWidget()
        signals_layout = QVBoxLayout(signals_widget)
        signals_layout.setContentsMargins(5, 5, 5, 5)
        
        self._create_signals_panel(signals_layout)
        splitter.addWidget(signals_widget)
        
        # Set splitter sizes (70% charts, 30% signals)
        splitter.setSizes([980, 420])
        
        # Control bar
        self._create_control_bar(main_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Click 'Refresh' to load data")
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def _create_charts(self, layout):
        """Create the chart panels."""
        # Graphics layout for multiple charts
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.setBackground(COLORS['background'])
        layout.addWidget(self.graphics_widget)
        
        # Price chart
        self.price_plot = self.graphics_widget.addPlot(row=0, col=0, title="Nifty 50 Index")
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setLabel('left', 'Price')
        
        # Breadth chart - % above 20 SMA
        self.breadth_plot = self.graphics_widget.addPlot(row=1, col=0, title="% Stocks Above 20 SMA")
        self.breadth_plot.showGrid(x=True, y=True, alpha=0.3)
        self.breadth_plot.setLabel('left', '%')
        self.breadth_plot.setYRange(0, 100)
        
        # Add overbought/oversold zones
        self._add_zones(self.breadth_plot)
        
        # All SMAs chart
        self.all_sma_plot = self.graphics_widget.addPlot(row=2, col=0, title="All Breadth Indicators")
        self.all_sma_plot.showGrid(x=True, y=True, alpha=0.3)
        self.all_sma_plot.setLabel('left', '%')
        self.all_sma_plot.setYRange(0, 100)
        self.all_sma_plot.addLegend()
        
        # Link X axes
        self.breadth_plot.setXLink(self.price_plot)
        self.all_sma_plot.setXLink(self.price_plot)
    
    def _add_zones(self, plot):
        """Add overbought/oversold zones to a plot."""
        # Extreme overbought zone (85-100)
        zone_extreme_ob = pg.LinearRegionItem(
            values=[85, 100], orientation='horizontal',
            brush=pg.mkBrush(255, 0, 0, 30), movable=False
        )
        plot.addItem(zone_extreme_ob)
        
        # Overbought zone (75-85)
        zone_ob = pg.LinearRegionItem(
            values=[75, 85], orientation='horizontal',
            brush=pg.mkBrush(255, 165, 0, 30), movable=False
        )
        plot.addItem(zone_ob)
        
        # Oversold zone (15-25)
        zone_os = pg.LinearRegionItem(
            values=[15, 25], orientation='horizontal',
            brush=pg.mkBrush(255, 215, 0, 30), movable=False
        )
        plot.addItem(zone_os)
        
        # Extreme oversold zone (0-15)
        zone_extreme_os = pg.LinearRegionItem(
            values=[0, 15], orientation='horizontal',
            brush=pg.mkBrush(0, 100, 255, 30), movable=False
        )
        plot.addItem(zone_extreme_os)
    
    def _create_signals_panel(self, layout):
        """Create the signals and recommendations panel."""
        # Current Reading group
        reading_group = QGroupBox("📊 CURRENT READING")
        reading_group.setFont(QFont('Segoe UI', 11, QFont.Bold))
        reading_layout = QVBoxLayout(reading_group)
        
        self.reading_labels = {}
        for name in ['date', 'index', 'signal', 'divergence', 'action']:
            label = QLabel("--")
            label.setFont(QFont('Segoe UI', 10))
            label.setWordWrap(True)
            reading_layout.addWidget(label)
            self.reading_labels[name] = label
        
        layout.addWidget(reading_group)
        
        # Risk Gauge
        risk_group = QGroupBox("⚠️ RISK LEVEL")
        risk_group.setFont(QFont('Segoe UI', 11, QFont.Bold))
        risk_layout = QVBoxLayout(risk_group)
        
        self.risk_gauge = RiskGauge()
        risk_layout.addWidget(self.risk_gauge)
        
        layout.addWidget(risk_group)
        
        # Breadth Table
        breadth_group = QGroupBox("📈 BREADTH BREAKDOWN")
        breadth_group.setFont(QFont('Segoe UI', 11, QFont.Bold))
        breadth_layout = QVBoxLayout(breadth_group)
        
        self.breadth_table = QTableWidget(4, 2)
        self.breadth_table.setHorizontalHeaderLabels(['SMA Period', '% Above'])
        self.breadth_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.breadth_table.setMaximumHeight(150)
        
        for i, period in enumerate([10, 20, 50, 200]):
            self.breadth_table.setItem(i, 0, QTableWidgetItem(f"SMA {period}"))
            self.breadth_table.setItem(i, 1, QTableWidgetItem("--"))
        
        breadth_layout.addWidget(self.breadth_table)
        layout.addWidget(breadth_group)
        
        # Protection Signal
        protection_group = QGroupBox("🛡️ PORTFOLIO PROTECTION")
        protection_group.setFont(QFont('Segoe UI', 11, QFont.Bold))
        protection_layout = QVBoxLayout(protection_group)
        
        self.protection_label = QLabel("Loading...")
        self.protection_label.setWordWrap(True)
        self.protection_label.setFont(QFont('Consolas', 9))
        self.protection_label.setStyleSheet("background-color: #2D2D2D; padding: 10px; border-radius: 5px;")
        protection_layout.addWidget(self.protection_label)
        
        layout.addWidget(protection_group)
        
        # Spacer
        layout.addStretch()
    
    def _create_control_bar(self, layout):
        """Create the bottom control bar."""
        control_frame = QFrame()
        control_frame.setStyleSheet("background-color: #2D2D2D; border-radius: 5px; padding: 5px;")
        control_layout = QHBoxLayout(control_frame)
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh Data")
        self.refresh_btn.setFont(QFont('Segoe UI', 10))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.refresh_btn.clicked.connect(self._load_data)
        control_layout.addWidget(self.refresh_btn)
        
        control_layout.addStretch()
        
        # Zone legend
        legend_layout = QHBoxLayout()
        zones = [
            ("🔴 Extreme OB (>85%)", COLORS['extreme_overbought']),
            ("🟠 Overbought (75-85%)", COLORS['overbought']),
            ("🟢 Neutral", COLORS['neutral']),
            ("🟡 Oversold (15-25%)", COLORS['oversold']),
            ("🔵 Extreme OS (<15%)", COLORS['extreme_oversold']),
        ]
        for text, color in zones:
            lbl = QLabel(text)
            lbl.setFont(QFont('Segoe UI', 8))
            legend_layout.addWidget(lbl)
        
        control_layout.addLayout(legend_layout)
        
        layout.addWidget(control_frame)
    
    def _load_data(self):
        """Load data in background."""
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.loader_thread = DataLoaderThread(self.detector)
        self.loader_thread.progress.connect(self._on_progress)
        self.loader_thread.finished.connect(self._on_load_finished)
        self.loader_thread.error.connect(self._on_error)
        self.loader_thread.start()
    
    def _on_progress(self, message, pct):
        self.progress_bar.setValue(pct)
        self.status_bar.showMessage(message)
    
    def _on_load_finished(self, breadth_df, reading, signal):
        self.breadth_df = breadth_df
        self.current_reading = reading
        self.protection_signal = signal
        
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self._update_charts()
        self._update_signals_panel()
        
        self.status_bar.showMessage(f"Data loaded - {len(breadth_df)} days | Last: {breadth_df.index[-1].strftime('%Y-%m-%d')}")
    
    def _on_error(self, error_msg):
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Error: {error_msg}")
    
    def _update_charts(self):
        """Update all charts."""
        if self.breadth_df is None or self.breadth_df.empty:
            return
        
        # Use sequential indices for x-axis
        x = np.arange(len(self.breadth_df))
        
        # Price chart
        self.price_plot.clear()
        self.price_plot.plot(x, self.breadth_df['index_close'].values, pen=pg.mkPen('#00BFFF', width=2))
        
        # Breadth chart (20 SMA)
        self.breadth_plot.clear()
        self._add_zones(self.breadth_plot)
        pct_20 = self.breadth_df['pct_above_sma_20'].values
        
        # Color line by zone
        pen = pg.mkPen('#FFFFFF', width=2)
        self.breadth_plot.plot(x, pct_20, pen=pen)
        
        # Fill below line
        fill = pg.FillBetweenItem(
            pg.PlotCurveItem(x, pct_20),
            pg.PlotCurveItem(x, np.zeros_like(pct_20)),
            brush=pg.mkBrush(0, 150, 255, 50)
        )
        self.breadth_plot.addItem(fill)
        
        # All SMAs chart
        self.all_sma_plot.clear()
        colors = {'10': '#FF6B6B', '20': '#4ECDC4', '50': '#45B7D1', '200': '#96CEB4'}
        
        for period, color in colors.items():
            col = f'pct_above_sma_{period}'
            if col in self.breadth_df.columns:
                self.all_sma_plot.plot(
                    x, self.breadth_df[col].values,
                    pen=pg.mkPen(color, width=2),
                    name=f"SMA {period}"
                )
    
    def _update_signals_panel(self):
        """Update the signals panel."""
        reading = self.current_reading
        signal = self.protection_signal
        
        if reading is None:
            return
        
        # Update reading labels
        self.reading_labels['date'].setText(f"📅 Date: {reading.date}")
        self.reading_labels['index'].setText(
            f"📈 Nifty 50: {reading.index_close:,.2f} ({reading.index_change_pct:+.2f}%)"
        )
        self.reading_labels['signal'].setText(f"Signal: {reading.market_signal.value}")
        self.reading_labels['divergence'].setText(f"Divergence: {reading.divergence.value}")
        self.reading_labels['action'].setText(f"🎯 ACTION: {reading.action}")
        
        # Color based on signal
        signal_colors = {
            MarketSignal.EXTREME_OVERBOUGHT: COLORS['extreme_overbought'],
            MarketSignal.OVERBOUGHT: COLORS['overbought'],
            MarketSignal.NEUTRAL: COLORS['neutral'],
            MarketSignal.OVERSOLD: COLORS['oversold'],
            MarketSignal.EXTREME_OVERSOLD: COLORS['extreme_oversold'],
        }
        color = signal_colors.get(reading.market_signal, COLORS['neutral'])
        self.reading_labels['signal'].setStyleSheet(f"color: {color}; font-weight: bold;")
        
        # Update risk gauge
        self.risk_gauge.set_risk(reading.risk_score)
        
        # Update breadth table
        for i, period in enumerate([10, 20, 50, 200]):
            pct = getattr(reading, f'pct_above_{period}_sma')
            item = QTableWidgetItem(f"{pct:.1f}%")
            
            # Color based on level
            if pct >= 85:
                item.setBackground(QColor(COLORS['extreme_overbought']))
            elif pct >= 75:
                item.setBackground(QColor(COLORS['overbought']))
            elif pct <= 15:
                item.setBackground(QColor(COLORS['extreme_oversold']))
            elif pct <= 25:
                item.setBackground(QColor(COLORS['oversold']))
            
            self.breadth_table.setItem(i, 1, item)
        
        # Update protection signal
        if signal:
            protection_text = f"""
RISK LEVEL: {signal.risk_level} (Score: {signal.risk_score}/100)

RECOMMENDED ACTIONS:
• Reduce Equity: {signal.reduce_exposure_pct}%
• Target Cash: {signal.increase_cash_pct}%
• Hedging: {signal.hedge_recommendation}

ANALYSIS:
"""
            for reason in signal.reasons[:6]:  # Limit to 6 reasons
                protection_text += f"• {reason}\n"
            
            self.protection_label.setText(protection_text)
            
            # Color based on risk level
            risk_colors = {
                'EXTREME': '#FF0000',
                'HIGH': '#FF6600',
                'MEDIUM': '#FFD700',
                'LOW': '#00AA00',
            }
            border_color = risk_colors.get(signal.risk_level, '#666666')
            self.protection_label.setStyleSheet(
                f"background-color: #2D2D2D; padding: 10px; border: 2px solid {border_color}; border-radius: 5px;"
            )


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS['background']))
    palette.setColor(QPalette.WindowText, QColor(COLORS['text']))
    palette.setColor(QPalette.Base, QColor('#2D2D2D'))
    palette.setColor(QPalette.AlternateBase, QColor('#3D3D3D'))
    palette.setColor(QPalette.Text, QColor(COLORS['text']))
    palette.setColor(QPalette.Button, QColor('#3D3D3D'))
    palette.setColor(QPalette.ButtonText, QColor(COLORS['text']))
    app.setPalette(palette)
    
    window = ExhaustionVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
