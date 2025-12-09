"""
Volume Profile Visualizer - TradingView Style
==============================================
PyQtGraph-based GUI for visualizing Volume Profiles with VPOC and Value Area.

Features:
- TradingView-style volume profile display
- Volume bars extend INTO the chart from the left edge
- Volume numbers displayed on each bar
- VPOC (Volume Point of Control) highlighted in yellow
- Value Area (VAH/VAL) highlighted
- Each day displayed as a separate column
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple
import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QSplitter, QScrollArea,
    QStatusBar, QSpinBox, QFrame, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush

import pyqtgraph as pg

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from volume_profile.calculator import VolumeProfileCalculator, VolumeProfile


# Configure PyQtGraph
pg.setConfigOptions(antialias=True, background='#131722', foreground='#ffffff')


class DataFetchWorker(QThread):
    """Background worker for fetching data."""
    finished = pyqtSignal(list, object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, symbol: str, days: int, num_bins: int = 50):
        super().__init__()
        self.symbol = symbol
        self.days = days
        self.num_bins = num_bins
    
    def run(self):
        try:
            self.progress.emit(f"Fetching {self.days} days of 1-min data...")
            
            calc = VolumeProfileCalculator(value_area_pct=70, num_bins=self.num_bins)
            raw_data = calc.fetch_intraday_data(self.symbol, self.days)
            
            if raw_data.empty:
                self.error.emit("No data available")
                return
            
            profiles = []
            for trade_date, day_df in raw_data.groupby('date'):
                try:
                    profile = calc.calculate_profile(day_df)
                    profiles.append((profile, day_df))
                except Exception as e:
                    pass
            
            profiles = sorted(profiles, key=lambda p: p[0].date)
            self.finished.emit(profiles, raw_data)
        except Exception as e:
            self.error.emit(str(e))


class VolumeProfileItem(pg.GraphicsObject):
    """
    Custom graphics item for TradingView-style volume profile.
    Volume bars extend from left edge into the chart.
    """
    
    # Colors matching TradingView
    COLOR_UP = QColor(38, 166, 154)      # Teal/Green for buying
    COLOR_DOWN = QColor(239, 83, 80)     # Red for selling  
    COLOR_VPOC = QColor(255, 235, 59)    # Yellow for VPOC
    COLOR_TEXT = QColor(255, 255, 255)   # White text
    
    def __init__(self, profile: VolumeProfile, x_offset: float = 0, width: float = 100):
        super().__init__()
        self.profile = profile
        self.x_offset = x_offset
        self.width = width
        self.generatePicture()
    
    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        painter = QPainter(self.picture)
        painter.setRenderHint(QPainter.Antialiasing)
        
        profile = self.profile
        price_levels = profile.price_levels
        volumes = profile.volume_at_price
        tick_size = profile.tick_size
        
        max_vol = volumes.max() if volumes.max() > 0 else 1
        
        # Scale factor for bar width
        bar_scale = self.width * 0.8 / max_vol
        
        for i, (price, vol) in enumerate(zip(price_levels, volumes)):
            if vol == 0:
                continue
            
            # Determine if this is VPOC or in Value Area
            is_vpoc = abs(price - profile.vpoc) < tick_size / 2
            is_in_va = profile.val <= price <= profile.vah
            
            # Bar dimensions
            bar_height = tick_size * 0.9
            bar_width = vol * bar_scale
            
            # Position: bars extend from left edge to the right
            x = self.x_offset
            y = price - bar_height / 2
            
            # Choose color
            if is_vpoc:
                color = self.COLOR_VPOC
            elif is_in_va:
                # Use green/red based on price position relative to close
                if price >= profile.close_price:
                    color = self.COLOR_DOWN  # Above close = selling pressure
                else:
                    color = self.COLOR_UP    # Below close = buying support
            else:
                # Outside VA - darker colors
                if price >= profile.close_price:
                    color = QColor(139, 69, 69)   # Dark red
                else:
                    color = QColor(47, 79, 79)    # Dark teal
            
            # Draw bar
            painter.setPen(QPen(Qt.NoPen))
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(x, y, bar_width, bar_height))
            
            # Draw volume text on bar if bar is wide enough
            if bar_width > 30:
                painter.setPen(QPen(self.COLOR_TEXT))
                font = painter.font()
                font.setPixelSize(int(tick_size * 0.6))
                painter.setFont(font)
                
                # Format volume
                if vol >= 1e6:
                    vol_text = f"{vol/1e6:.1f}M"
                elif vol >= 1e3:
                    vol_text = f"{vol/1e3:.1f}K"
                else:
                    vol_text = f"{int(vol)}"
                
                text_rect = QRectF(x + 2, y, bar_width - 4, bar_height)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, vol_text)
        
        # Draw VPOC line
        painter.setPen(QPen(self.COLOR_VPOC, 2, Qt.SolidLine))
        painter.drawLine(
            int(self.x_offset), int(profile.vpoc),
            int(self.x_offset + self.width), int(profile.vpoc)
        )
        
        # Draw VAH line
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1, Qt.DashLine))
        painter.drawLine(
            int(self.x_offset), int(profile.vah),
            int(self.x_offset + self.width), int(profile.vah)
        )
        
        # Draw VAL line
        painter.drawLine(
            int(self.x_offset), int(profile.val),
            int(self.x_offset + self.width), int(profile.val)
        )
        
        painter.end()
    
    def paint(self, painter, *args):
        painter.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return QRectF(
            self.x_offset,
            self.profile.low_price - self.profile.tick_size,
            self.width,
            self.profile.high_price - self.profile.low_price + 2 * self.profile.tick_size
        )


class DayProfileWidget(QWidget):
    """Widget for a single day's volume profile in TradingView style."""
    
    COLOR_UP = '#26a69a'
    COLOR_DOWN = '#ef5350'
    COLOR_VPOC = '#ffeb3b'
    COLOR_BG = '#131722'
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile: Optional[VolumeProfile] = None
        self.day_data: Optional[pd.DataFrame] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Date header
        self.date_label = QLabel("--")
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.date_label.setStyleSheet(f"""
            QLabel {{
                background-color: #1e222d;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.date_label)
        
        # Chart
        self.plot = pg.PlotWidget()
        self.plot.setBackground(self.COLOR_BG)
        self.plot.showGrid(x=False, y=True, alpha=0.3)
        self.plot.setMouseEnabled(x=False, y=True)
        self.plot.hideAxis('bottom')
        layout.addWidget(self.plot)
        
        # Info panel
        info_widget = QFrame()
        info_widget.setStyleSheet("background-color: #1e222d; border-radius: 4px;")
        info_layout = QGridLayout(info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(3)
        
        self.info_labels = {}
        labels = [
            ("VPOC", "vpoc", self.COLOR_VPOC, 0, 0),
            ("VAH", "vah", "#ffffff", 0, 1),
            ("VAL", "val", "#ffffff", 0, 2),
        ]
        
        for label_text, key, color, row, col in labels:
            frame = QFrame()
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(3, 2, 3, 2)
            frame_layout.setSpacing(0)
            
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #787b86; font-size: 10px;")
            lbl.setAlignment(Qt.AlignCenter)
            frame_layout.addWidget(lbl)
            
            val = QLabel("--")
            val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            val.setAlignment(Qt.AlignCenter)
            frame_layout.addWidget(val)
            
            self.info_labels[key] = val
            info_layout.addWidget(frame, row, col)
        
        layout.addWidget(info_widget)
    
    def set_data(self, profile: VolumeProfile, day_data: pd.DataFrame):
        self.profile = profile
        self.day_data = day_data
        
        # Update header
        change = profile.close_price - profile.open_price
        change_pct = (change / profile.open_price) * 100
        direction = "▲" if change >= 0 else "▼"
        color = self.COLOR_UP if change >= 0 else self.COLOR_DOWN
        
        self.date_label.setText(
            f"<span style='font-size: 12px;'>{profile.date.strftime('%a, %d %b %Y')}</span><br>"
            f"<span style='color:{color}; font-size: 14px;'>{direction} {change_pct:+.2f}%</span>"
        )
        
        # Update info
        self.info_labels['vpoc'].setText(f"{profile.vpoc:,.2f}")
        self.info_labels['vah'].setText(f"{profile.vah:,.2f}")
        self.info_labels['val'].setText(f"{profile.val:,.2f}")
        
        # Draw profile
        self._draw_profile()
    
    def _draw_profile(self):
        self.plot.clear()
        
        if not self.profile:
            return
        
        profile = self.profile
        price_levels = profile.price_levels
        volumes = profile.volume_at_price
        tick_size = profile.tick_size
        
        max_vol = volumes.max() if volumes.max() > 0 else 1
        bar_height = tick_size * 0.85
        
        # Group bars by color for efficient rendering
        groups = {
            'vpoc': {'x': [], 'y': [], 'w': [], 'h': []},
            'va_up': {'x': [], 'y': [], 'w': [], 'h': []},
            'va_down': {'x': [], 'y': [], 'w': [], 'h': []},
            'outside_up': {'x': [], 'y': [], 'w': [], 'h': []},
            'outside_down': {'x': [], 'y': [], 'w': [], 'h': []},
        }
        
        for price, vol in zip(price_levels, volumes):
            if vol == 0:
                continue
            
            is_vpoc = abs(price - profile.vpoc) < tick_size / 2
            is_in_va = profile.val <= price <= profile.vah
            
            # Determine group
            if is_vpoc:
                group = 'vpoc'
            elif is_in_va:
                group = 'va_down' if price >= profile.close_price else 'va_up'
            else:
                group = 'outside_down' if price >= profile.close_price else 'outside_up'
            
            # For horizontal bars: x is center, width is bar length
            groups[group]['x'].append(vol / 2)  # center x
            groups[group]['y'].append(price)     # y position
            groups[group]['w'].append(vol)       # width (volume)
            groups[group]['h'].append(bar_height)
        
        # Color mapping
        colors = {
            'vpoc': self.COLOR_VPOC,
            'va_up': self.COLOR_UP,
            'va_down': self.COLOR_DOWN,
            'outside_up': '#2f4f4f',
            'outside_down': '#5c3a3a',
        }
        
        # Draw each group as BarGraphItem
        import numpy as np
        for group_name, data in groups.items():
            if not data['x']:
                continue
            bar = pg.BarGraphItem(
                x=np.array(data['x']),
                y=np.array(data['y']),
                width=np.array(data['w']),
                height=np.array(data['h']),
                brush=pg.mkBrush(colors[group_name]),
                pen=pg.mkPen(None)
            )
            self.plot.addItem(bar)
        
        # Add volume text for significant bars
        for price, vol in zip(price_levels, volumes):
            if vol > max_vol * 0.15:  # Only show text for significant bars
                if vol >= 1e6:
                    vol_text = f"{vol/1e6:.1f}M"
                elif vol >= 1e3:
                    vol_text = f"{vol/1e3:.0f}K"
                else:
                    vol_text = f"{int(vol)}"
                
                text = pg.TextItem(vol_text, color='#ffffff', anchor=(0, 0.5))
                text.setPos(vol * 0.05, price)
                font = text.textItem.font()
                font.setPixelSize(9)
                text.setFont(font)
                self.plot.addItem(text)
        
        # Draw VPOC line
        vpoc_line = pg.InfiniteLine(
            pos=profile.vpoc, angle=0,
            pen=pg.mkPen(self.COLOR_VPOC, width=2)
        )
        self.plot.addItem(vpoc_line)
        
        # VPOC label
        vpoc_label = pg.TextItem(f"POC {profile.vpoc:,.0f}", color=self.COLOR_VPOC, anchor=(1, 0.5))
        vpoc_label.setPos(max_vol, profile.vpoc)
        self.plot.addItem(vpoc_label)
        
        # Draw VAH/VAL lines
        vah_line = pg.InfiniteLine(
            pos=profile.vah, angle=0,
            pen=pg.mkPen('#ffffff', width=1, style=Qt.DashLine)
        )
        self.plot.addItem(vah_line)
        
        val_line = pg.InfiniteLine(
            pos=profile.val, angle=0,
            pen=pg.mkPen('#ffffff', width=1, style=Qt.DashLine)
        )
        self.plot.addItem(val_line)
        
        # Set ranges
        y_margin = (profile.high_price - profile.low_price) * 0.05
        self.plot.setYRange(profile.low_price - y_margin, profile.high_price + y_margin)
        self.plot.setXRange(0, max_vol * 1.15)


class VolumeProfileVisualizer(QMainWindow):
    """Main GUI - TradingView style volume profiles side by side."""
    
    def __init__(self):
        super().__init__()
        
        self.profiles: List[tuple] = []
        self.day_widgets: List[DayProfileWidget] = []
        self.worker: Optional[DataFetchWorker] = None
        
        self.setWindowTitle("📊 Volume Profile - VPOC & Value Area (TradingView Style)")
        self.setMinimumSize(1400, 700)
        
        self._setup_ui()
        self._fetch_data()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        self._create_header(main_layout)
        
        # Legend
        self._create_legend(main_layout)
        
        # Scroll area for profiles
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #131722; }")
        
        self.panels_widget = QWidget()
        self.panels_widget.setStyleSheet("background-color: #131722;")
        self.panels_layout = QHBoxLayout(self.panels_widget)
        self.panels_layout.setSpacing(15)
        self.panels_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll.setWidget(self.panels_widget)
        main_layout.addWidget(scroll)
        
        self.statusBar().showMessage("Ready")
    
    def _create_header(self, layout: QVBoxLayout):
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1e222d;
                border-radius: 8px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        title = QLabel("📊 Volume Profile Analyzer")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #26a69a;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Controls
        header_layout.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems([
            "^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS", 
            "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"
        ])
        self.symbol_combo.setStyleSheet("min-width: 100px;")
        header_layout.addWidget(self.symbol_combo)
        
        header_layout.addWidget(QLabel("Days:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 7)
        self.days_spin.setValue(5)
        header_layout.addWidget(self.days_spin)
        
        header_layout.addWidget(QLabel("Bins:"))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(20, 100)
        self.bins_spin.setValue(30)
        self.bins_spin.setSingleStep(5)
        header_layout.addWidget(self.bins_spin)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._fetch_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #26a69a;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2bbd9e; }
        """)
        header_layout.addWidget(refresh_btn)
        
        layout.addWidget(header)
    
    def _create_legend(self, layout: QVBoxLayout):
        legend = QFrame()
        legend.setStyleSheet("background-color: #1e222d; border-radius: 4px;")
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(15, 8, 15, 8)
        
        items = [
            ("■ VPOC (Point of Control)", "#ffeb3b"),
            ("■ Value Area (Buyers)", "#26a69a"),
            ("■ Value Area (Sellers)", "#ef5350"),
            ("--- VAH/VAL Lines", "#ffffff"),
        ]
        
        for text, color in items:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
            legend_layout.addWidget(lbl)
            legend_layout.addSpacing(30)
        
        legend_layout.addStretch()
        layout.addWidget(legend)
    
    def _fetch_data(self):
        if self.worker and self.worker.isRunning():
            return
        
        symbol = self.symbol_combo.currentText()
        days = self.days_spin.value()
        bins = self.bins_spin.value()
        
        self.statusBar().showMessage(f"Fetching {days} days of 1-min data for {symbol}...")
        
        self.worker = DataFetchWorker(symbol, days, bins)
        self.worker.finished.connect(self._on_data_fetched)
        self.worker.error.connect(self._on_fetch_error)
        self.worker.progress.connect(lambda msg: self.statusBar().showMessage(msg))
        self.worker.start()
    
    def _on_data_fetched(self, profiles: List[tuple], raw_data):
        self.profiles = profiles
        
        if not profiles:
            self.statusBar().showMessage("No data available")
            return
        
        # Clear existing
        for w in self.day_widgets:
            w.deleteLater()
        self.day_widgets.clear()
        
        while self.panels_layout.count():
            item = self.panels_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create widgets for each day
        for profile, day_data in profiles:
            widget = DayProfileWidget()
            widget.setMinimumWidth(280)
            widget.setMaximumWidth(350)
            widget.set_data(profile, day_data)
            self.panels_layout.addWidget(widget)
            self.day_widgets.append(widget)
        
        self.panels_layout.addStretch()
        self.statusBar().showMessage(f"Loaded {len(profiles)} days of volume profiles")
    
    def _on_fetch_error(self, error: str):
        self.statusBar().showMessage(f"Error: {error}")
        QMessageBox.critical(self, "Error", f"Failed to fetch data:\n{error}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(19, 23, 34))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(30, 34, 45))
    palette.setColor(QPalette.AlternateBase, QColor(40, 44, 55))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(40, 44, 55))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.Highlight, QColor(38, 166, 154))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = VolumeProfileVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
