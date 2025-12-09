"""
Volume Profile - Single Chart with 5 Days
==========================================
All profiles on one chart with shared price (Y) axis.
X-axis shows dates, each day has its own profile column.
"""
import sys
import os

# MUST create QApplication BEFORE importing pyqtgraph
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QLineEdit, QPushButton, QComboBox, QSpinBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from volume_profile.calculator import VolumeProfileCalculator

# Configure pyqtgraph
pg.setConfigOptions(antialias=True, background='#131722', foreground='#d1d4dc')


class VolumeProfileWindow(QMainWindow):
    """Single chart showing 5 days of volume profiles."""
    
    COLOR_UP = '#26a69a'
    COLOR_DOWN = '#ef5350'
    COLOR_VPOC = '#ffeb3b'
    COLOR_VAH = '#4caf50'
    COLOR_VAL = '#f44336'
    COLOR_BG = '#131722'
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Volume Profile - 5 Day Combined View")
        self.setGeometry(50, 50, 1400, 800)
        self.setStyleSheet(f"background-color: {self.COLOR_BG}; color: white;")
        
        self.profiles = []
        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Controls
        controls = QFrame()
        controls.setStyleSheet("background-color: #1e222d; border-radius: 8px;")
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(15, 10, 15, 10)
        
        # Symbol input
        ctrl_layout.addWidget(QLabel("Symbol:"))
        self.symbol_input = QLineEdit("RELIANCE.NS")
        self.symbol_input.setStyleSheet("background: #2a2e39; padding: 8px; border-radius: 4px; color: white;")
        self.symbol_input.setFixedWidth(150)
        self.symbol_input.returnPressed.connect(self.load_profiles)
        ctrl_layout.addWidget(self.symbol_input)
        
        # Quick symbols
        ctrl_layout.addWidget(QLabel("Quick:"))
        self.quick_combo = QComboBox()
        self.quick_combo.addItems([
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
            "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS", "ASIANPAINT.NS",
            "NIFTYBEES.NS", "BANKBEES.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "WIPRO.NS"
        ])
        self.quick_combo.setStyleSheet("background: #2a2e39; padding: 5px; color: white;")
        self.quick_combo.currentTextChanged.connect(lambda t: self.symbol_input.setText(t))
        ctrl_layout.addWidget(self.quick_combo)
        
        # Bins
        ctrl_layout.addWidget(QLabel("Bins:"))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(10, 100)
        self.bins_spin.setValue(30)
        self.bins_spin.setStyleSheet("background: #2a2e39; padding: 5px; color: white;")
        ctrl_layout.addWidget(self.bins_spin)
        
        # Days
        ctrl_layout.addWidget(QLabel("Days:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 7)
        self.days_spin.setValue(5)
        self.days_spin.setStyleSheet("background: #2a2e39; padding: 5px; color: white;")
        ctrl_layout.addWidget(self.days_spin)
        
        ctrl_layout.addStretch()
        
        # Load button
        self.load_btn = QPushButton("📊 Load Profiles")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background: #2962ff; color: white; padding: 10px 25px; 
                border-radius: 4px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background: #1e88e5; }
            QPushButton:disabled { background: #555; }
        """)
        self.load_btn.clicked.connect(self.load_profiles)
        ctrl_layout.addWidget(self.load_btn)
        
        layout.addWidget(controls)
        
        # Legend
        legend = QFrame()
        legend.setStyleSheet("background-color: #1e222d; border-radius: 4px; padding: 5px;")
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(10, 5, 10, 5)
        
        items = [
            ("● VPOC", self.COLOR_VPOC),
            ("● Value Area (Buyers)", self.COLOR_UP),
            ("● Value Area (Sellers)", self.COLOR_DOWN),
            ("— VAH", self.COLOR_VAH),
            ("— VAL", self.COLOR_VAL),
        ]
        for text, color in items:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
            legend_layout.addWidget(lbl)
        legend_layout.addStretch()
        
        layout.addWidget(legend)
        
        # Main chart
        self.plot = pg.PlotWidget()
        self.plot.setBackground(self.COLOR_BG)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel('left', 'Price', color='#d1d4dc')
        self.plot.setLabel('bottom', 'Date', color='#d1d4dc')
        
        # Enable mouse interaction
        self.plot.setMouseEnabled(x=True, y=True)
        
        layout.addWidget(self.plot)
        
        # Status
        self.status_label = QLabel("Enter a symbol and click Load")
        self.status_label.setStyleSheet("color: #787b86; font-size: 12px; padding: 5px;")
        layout.addWidget(self.status_label)
    
    def load_profiles(self):
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            self.status_label.setText("⚠️ Enter a symbol")
            return
        
        # Add .NS if missing
        if not symbol.endswith('.NS') and not symbol.startswith('^'):
            symbol += '.NS'
            self.symbol_input.setText(symbol)
        
        self.status_label.setText(f"Loading {symbol}...")
        self.load_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            num_days = self.days_spin.value()
            
            # Fetch data
            calc = VolumeProfileCalculator(value_area_pct=70, num_bins=self.bins_spin.value())
            raw_data = calc.fetch_intraday_data(symbol, num_days + 2)
            
            if raw_data.empty:
                self.status_label.setText(f"❌ No data for {symbol}")
                self.load_btn.setEnabled(True)
                return
            
            if raw_data['volume'].sum() == 0:
                self.status_label.setText(f"❌ {symbol} has no volume data (try a stock, not index)")
                self.load_btn.setEnabled(True)
                return
            
            # Get unique dates
            dates = sorted(raw_data['date'].unique())
            dates = dates[-num_days:]
            
            # Calculate profile for each day
            self.profiles = []
            for trade_date in dates:
                day_df = raw_data[raw_data['date'] == trade_date].copy()
                if day_df['volume'].sum() > 0:
                    profile = calc.calculate_profile(day_df)
                    self.profiles.append((trade_date, profile))
            
            # Draw combined chart
            self._draw_combined_chart(symbol)
            
            self.status_label.setText(f"✅ Loaded {len(self.profiles)} days for {symbol}")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.load_btn.setEnabled(True)
    
    def _draw_combined_chart(self, symbol: str):
        self.plot.clear()
        
        if not self.profiles:
            return
        
        num_days = len(self.profiles)
        
        # Find global price range
        global_min = min(p.low_price for _, p in self.profiles)
        global_max = max(p.high_price for _, p in self.profiles)
        
        # Find max volume for normalization (so bars are comparable width)
        all_max_vols = [p.volume_at_price.max() for _, p in self.profiles]
        global_max_vol = max(all_max_vols) if all_max_vols else 1
        
        # Width for each day's profile (in x-axis units)
        day_width = 1.0
        bar_width_scale = day_width * 0.8  # Bars take 80% of day width
        gap = 0.1  # Small gap between days
        
        # X-axis tick labels (dates)
        x_ticks = []
        
        for day_idx, (trade_date, profile) in enumerate(self.profiles):
            # X position for this day
            x_base = day_idx * (day_width + gap)
            x_ticks.append((x_base + day_width / 2, trade_date.strftime('%a\n%d %b')))
            
            price_levels = profile.price_levels
            volumes = profile.volume_at_price
            tick_size = profile.tick_size
            max_vol = volumes.max() if volumes.max() > 0 else 1
            
            bar_height = tick_size * 0.85
            
            # Group bars by color
            groups = {
                'vpoc': {'x': [], 'y': [], 'w': [], 'h': []},
                'va_up': {'x': [], 'y': [], 'w': [], 'h': []},
                'va_down': {'x': [], 'y': [], 'w': [], 'h': []},
                'out_up': {'x': [], 'y': [], 'w': [], 'h': []},
                'out_down': {'x': [], 'y': [], 'w': [], 'h': []},
            }
            
            for price, vol in zip(price_levels, volumes):
                if vol <= 0:
                    continue
                
                is_vpoc = abs(price - profile.vpoc) < tick_size / 2
                is_in_va = profile.val <= price <= profile.vah
                
                if is_vpoc:
                    group = 'vpoc'
                elif is_in_va:
                    group = 'va_down' if price >= profile.close_price else 'va_up'
                else:
                    group = 'out_down' if price >= profile.close_price else 'out_up'
                
                # Normalize bar width relative to global max volume
                normalized_width = (vol / global_max_vol) * bar_width_scale
                
                # X position: bars extend from left edge of day slot
                x_center = x_base + normalized_width / 2
                
                groups[group]['x'].append(x_center)
                groups[group]['y'].append(price)
                groups[group]['w'].append(normalized_width)
                groups[group]['h'].append(bar_height)
            
            # Colors
            colors = {
                'vpoc': self.COLOR_VPOC,
                'va_up': self.COLOR_UP,
                'va_down': self.COLOR_DOWN,
                'out_up': '#1a3a3a',
                'out_down': '#3a1a1a',
            }
            
            # Draw bars
            for group_name, data in groups.items():
                if not data['x']:
                    continue
                bar = pg.BarGraphItem(
                    x=np.array(data['x']),
                    y=np.array(data['y']),
                    width=np.array(data['w']),
                    height=np.array(data['h']),
                    brush=pg.mkBrush(colors[group_name]),
                    pen=None
                )
                self.plot.addItem(bar)
            
            # VPOC line for this day
            vpoc_line = pg.PlotDataItem(
                x=[x_base, x_base + day_width],
                y=[profile.vpoc, profile.vpoc],
                pen=pg.mkPen(self.COLOR_VPOC, width=2)
            )
            self.plot.addItem(vpoc_line)
            
            # VAH line
            vah_line = pg.PlotDataItem(
                x=[x_base, x_base + day_width],
                y=[profile.vah, profile.vah],
                pen=pg.mkPen(self.COLOR_VAH, width=1, style=Qt.DashLine)
            )
            self.plot.addItem(vah_line)
            
            # VAL line
            val_line = pg.PlotDataItem(
                x=[x_base, x_base + day_width],
                y=[profile.val, profile.val],
                pen=pg.mkPen(self.COLOR_VAL, width=1, style=Qt.DashLine)
            )
            self.plot.addItem(val_line)
            
            # Add VPOC label
            vpoc_label = pg.TextItem(
                f"{profile.vpoc:,.0f}",
                color=self.COLOR_VPOC,
                anchor=(0.5, 1)
            )
            vpoc_label.setPos(x_base + day_width / 2, profile.vpoc)
            font = vpoc_label.textItem.font()
            font.setPixelSize(10)
            font.setBold(True)
            vpoc_label.setFont(font)
            self.plot.addItem(vpoc_label)
            
            # Day change indicator at top
            change = profile.close_price - profile.open_price
            change_pct = (change / profile.open_price) * 100
            direction = "▲" if change >= 0 else "▼"
            color = self.COLOR_UP if change >= 0 else self.COLOR_DOWN
            
            change_label = pg.TextItem(
                f"{direction}{abs(change_pct):.1f}%",
                color=color,
                anchor=(0.5, 0)
            )
            change_label.setPos(x_base + day_width / 2, global_max + (global_max - global_min) * 0.02)
            font = change_label.textItem.font()
            font.setPixelSize(11)
            change_label.setFont(font)
            self.plot.addItem(change_label)
        
        # Set X-axis ticks
        ax = self.plot.getAxis('bottom')
        ax.setTicks([x_ticks])
        
        # Set ranges
        y_margin = (global_max - global_min) * 0.08
        self.plot.setYRange(global_min - y_margin, global_max + y_margin)
        self.plot.setXRange(-0.1, num_days * (day_width + gap))
        
        # Title
        self.setWindowTitle(f"📊 Volume Profile - {symbol} ({len(self.profiles)} Days)")


def main():
    win = VolumeProfileWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
