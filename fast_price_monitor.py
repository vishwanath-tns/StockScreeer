#!/usr/bin/env python3
"""
Fast Price Monitor for Crypto/Volatile Assets
==============================================

Monitor BTC, ETH, and other volatile assets for rapid price moves.
Checks prices every 5-10 seconds and alerts on sudden % changes.

Usage:
    python fast_price_monitor.py                    # Default: BTC-USD, 2% threshold
    python fast_price_monitor.py --symbol ETH-USD   # Monitor ETH
    python fast_price_monitor.py --threshold 1.5    # Alert on 1.5% moves
    python fast_price_monitor.py --interval 5       # Check every 5 seconds

Alert Types:
    - Spike Up: Price jumped X% in the last interval
    - Spike Down: Price dropped X% in the last interval
    - Flash Move: Price moved X% within Y seconds
"""

import argparse
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Deque
from collections import deque
import sys

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QDoubleSpinBox, QSpinBox, QComboBox,
        QTableWidget, QTableWidgetItem, QGroupBox, QFrame, QTextEdit,
        QSystemTrayIcon, QMenu, QCheckBox
    )
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QBrush, QFont, QPalette, QAction
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PricePoint:
    """A single price observation."""
    timestamp: datetime
    price: float
    volume: float = 0


@dataclass 
class PriceAlert:
    """An alert that was triggered."""
    timestamp: datetime
    symbol: str
    alert_type: str  # spike_up, spike_down, flash_move
    price_from: float
    price_to: float
    change_pct: float
    timeframe_seconds: int
    message: str


class FastPriceTracker:
    """
    Track price history and detect rapid moves.
    
    Keeps a rolling window of price observations and calculates
    changes over various timeframes.
    """
    
    def __init__(self, symbol: str, window_minutes: int = 5):
        self.symbol = symbol
        self.window_minutes = window_minutes
        self.price_history: Deque[PricePoint] = deque(maxlen=1000)
        self.last_price: Optional[float] = None
        self.alerts: List[PriceAlert] = []
    
    def add_price(self, price: float, volume: float = 0) -> Optional[Dict]:
        """
        Add a new price observation.
        
        Returns dict with change metrics if price changed.
        """
        now = datetime.now()
        
        # Store the point
        point = PricePoint(timestamp=now, price=price, volume=volume)
        self.price_history.append(point)
        
        if self.last_price is None:
            self.last_price = price
            return None
        
        # Calculate instant change
        instant_change_pct = (price - self.last_price) / self.last_price * 100
        
        # Calculate changes over various windows
        changes = {
            'current_price': price,
            'last_price': self.last_price,
            'instant_change_pct': instant_change_pct,
            '10s_change_pct': self._get_change_over_seconds(10),
            '30s_change_pct': self._get_change_over_seconds(30),
            '1m_change_pct': self._get_change_over_seconds(60),
            '5m_change_pct': self._get_change_over_seconds(300),
            'high_1m': self._get_high_over_seconds(60),
            'low_1m': self._get_low_over_seconds(60),
            'range_1m_pct': 0,
        }
        
        # Calculate 1-minute range
        if changes['high_1m'] and changes['low_1m'] and changes['low_1m'] > 0:
            changes['range_1m_pct'] = (changes['high_1m'] - changes['low_1m']) / changes['low_1m'] * 100
        
        self.last_price = price
        
        # Clean old data
        self._cleanup_old_data()
        
        return changes
    
    def _get_change_over_seconds(self, seconds: int) -> float:
        """Get % change over the last N seconds."""
        if len(self.price_history) < 2:
            return 0.0
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=seconds)
        
        # Find the oldest price within the window
        old_price = None
        for point in self.price_history:
            if point.timestamp >= cutoff:
                old_price = point.price
                break
        
        if old_price is None or old_price == 0:
            return 0.0
        
        current_price = self.price_history[-1].price
        return (current_price - old_price) / old_price * 100
    
    def _get_high_over_seconds(self, seconds: int) -> Optional[float]:
        """Get highest price over the last N seconds."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=seconds)
        
        prices = [p.price for p in self.price_history if p.timestamp >= cutoff]
        return max(prices) if prices else None
    
    def _get_low_over_seconds(self, seconds: int) -> Optional[float]:
        """Get lowest price over the last N seconds."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=seconds)
        
        prices = [p.price for p in self.price_history if p.timestamp >= cutoff]
        return min(prices) if prices else None
    
    def _cleanup_old_data(self):
        """Remove data older than window_minutes."""
        cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
        while self.price_history and self.price_history[0].timestamp < cutoff:
            self.price_history.popleft()


def get_realtime_price(symbol: str) -> Optional[Dict]:
    """
    Get real-time price from Yahoo Finance.
    
    Returns dict with price, change, volume, etc.
    """
    if not HAS_YFINANCE:
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Try fast_info first (faster)
        try:
            info = ticker.fast_info
            return {
                'price': info.last_price,
                'previous_close': info.previous_close,
                'day_change_pct': ((info.last_price - info.previous_close) / info.previous_close * 100) if info.previous_close else 0,
                'volume': getattr(info, 'last_volume', 0) or 0,
            }
        except Exception:
            pass
        
        # Fallback to history
        hist = ticker.history(period='1d', interval='1m')
        if not hist.empty:
            latest = hist.iloc[-1]
            prev_close = ticker.info.get('previousClose', latest['Open'])
            return {
                'price': latest['Close'],
                'previous_close': prev_close,
                'day_change_pct': ((latest['Close'] - prev_close) / prev_close * 100) if prev_close else 0,
                'volume': latest['Volume'],
            }
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
    
    return None


class FastMonitorGUI(QMainWindow):
    """GUI for fast price monitoring."""
    
    def __init__(self):
        super().__init__()
        self.trackers: Dict[str, FastPriceTracker] = {}
        self.alerts: List[PriceAlert] = []
        
        self.setup_ui()
        self.setWindowTitle("⚡ Fast Price Monitor - Crypto Spike Detector")
        self.setMinimumSize(800, 600)
        
        # Timer for price updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_prices)
        
        # Start with BTC by default
        self.add_symbol("BTC-USD")
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        header = QLabel("⚡ FAST PRICE MONITOR - Detect Rapid Moves in Seconds")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("padding: 10px; background: #1a1a2e; color: #00ffff; border-radius: 5px;")
        layout.addWidget(header)
        
        # Controls
        controls = QGroupBox("⚙️ Settings")
        controls_layout = QHBoxLayout(controls)
        
        # Symbol selector
        controls_layout.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.addItems(["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "XRP-USD"])
        controls_layout.addWidget(self.symbol_combo)
        
        add_btn = QPushButton("➕ Add")
        add_btn.clicked.connect(lambda: self.add_symbol(self.symbol_combo.currentText()))
        controls_layout.addWidget(add_btn)
        
        # Threshold
        controls_layout.addWidget(QLabel("Alert Threshold %:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 20.0)
        self.threshold_spin.setValue(2.0)
        self.threshold_spin.setSingleStep(0.5)
        controls_layout.addWidget(self.threshold_spin)
        
        # Interval
        controls_layout.addWidget(QLabel("Check Interval (sec):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(3, 60)
        self.interval_spin.setValue(5)
        controls_layout.addWidget(self.interval_spin)
        
        # Start/Stop
        self.start_btn = QPushButton("▶️ Start Monitoring")
        self.start_btn.setStyleSheet("background: #00aa00; color: white; font-weight: bold; padding: 5px 15px;")
        self.start_btn.clicked.connect(self.toggle_monitoring)
        controls_layout.addWidget(self.start_btn)
        
        # Sound toggle
        self.sound_check = QCheckBox("🔊 Sound")
        self.sound_check.setChecked(True)
        controls_layout.addWidget(self.sound_check)
        
        layout.addWidget(controls)
        
        # Price display
        price_group = QGroupBox("📊 Live Prices")
        price_layout = QVBoxLayout(price_group)
        
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(8)
        self.price_table.setHorizontalHeaderLabels([
            "Symbol", "Price", "10s %", "30s %", "1m %", "5m %", "1m Range", "Status"
        ])
        self.price_table.horizontalHeader().setStretchLastSection(True)
        price_layout.addWidget(self.price_table)
        
        layout.addWidget(price_group)
        
        # Alert banner
        self.alert_banner = QFrame()
        self.alert_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff0066, stop:0.5 #ff3399, stop:1 #ff0066);
                border: 3px solid #ff0000;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        self.alert_banner.setVisible(False)
        
        banner_layout = QHBoxLayout(self.alert_banner)
        self.alert_banner_text = QLabel("")
        self.alert_banner_text.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.alert_banner_text.setWordWrap(True)
        banner_layout.addWidget(self.alert_banner_text)
        
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setStyleSheet("background: transparent; color: white; font-size: 20px;")
        dismiss_btn.clicked.connect(lambda: self.alert_banner.setVisible(False))
        banner_layout.addWidget(dismiss_btn)
        
        layout.addWidget(self.alert_banner)
        
        # Alerts log
        alerts_group = QGroupBox("🔔 Alert History")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_log = QTextEdit()
        self.alerts_log.setReadOnly(True)
        self.alerts_log.setMaximumHeight(150)
        self.alerts_log.setStyleSheet("font-family: Consolas; font-size: 11px;")
        alerts_layout.addWidget(self.alerts_log)
        
        layout.addWidget(alerts_group)
        
        # Status bar
        self.status_label = QLabel("Ready. Add symbols and click Start.")
        self.status_label.setStyleSheet("padding: 5px; background: #333; color: #aaa;")
        layout.addWidget(self.status_label)
    
    def add_symbol(self, symbol: str):
        """Add a symbol to track."""
        symbol = symbol.strip().upper()
        if not symbol:
            return
        
        if symbol not in self.trackers:
            self.trackers[symbol] = FastPriceTracker(symbol)
            
            # Add row to table
            row = self.price_table.rowCount()
            self.price_table.setRowCount(row + 1)
            self.price_table.setItem(row, 0, QTableWidgetItem(symbol))
            for col in range(1, 8):
                self.price_table.setItem(row, col, QTableWidgetItem("-"))
            
            self.status_label.setText(f"Added {symbol}")
    
    def toggle_monitoring(self):
        """Start or stop monitoring."""
        if self.update_timer.isActive():
            self.update_timer.stop()
            self.start_btn.setText("▶️ Start Monitoring")
            self.start_btn.setStyleSheet("background: #00aa00; color: white; font-weight: bold; padding: 5px 15px;")
            self.status_label.setText("Monitoring stopped")
        else:
            interval_ms = self.interval_spin.value() * 1000
            self.update_timer.start(interval_ms)
            self.start_btn.setText("⏹️ Stop Monitoring")
            self.start_btn.setStyleSheet("background: #aa0000; color: white; font-weight: bold; padding: 5px 15px;")
            self.status_label.setText(f"Monitoring every {self.interval_spin.value()}s...")
            self.update_prices()  # First update immediately
    
    def update_prices(self):
        """Fetch prices and check for alerts."""
        threshold = self.threshold_spin.value()
        
        for row, (symbol, tracker) in enumerate(self.trackers.items()):
            data = get_realtime_price(symbol)
            
            if data and data['price']:
                changes = tracker.add_price(data['price'], data.get('volume', 0))
                
                if changes:
                    self._update_table_row(row, symbol, data['price'], changes)
                    self._check_alerts(symbol, changes, threshold)
        
        self.status_label.setText(f"Updated at {datetime.now().strftime('%H:%M:%S')}")
    
    def _update_table_row(self, row: int, symbol: str, price: float, changes: Dict):
        """Update a row in the price table."""
        # Price
        price_item = QTableWidgetItem(f"${price:,.2f}")
        price_item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.price_table.setItem(row, 1, price_item)
        
        # Change columns
        change_cols = [
            (2, '10s_change_pct'),
            (3, '30s_change_pct'),
            (4, '1m_change_pct'),
            (5, '5m_change_pct'),
        ]
        
        for col, key in change_cols:
            change = changes.get(key, 0)
            item = QTableWidgetItem(f"{change:+.2f}%")
            
            # Color based on change
            if change >= 2:
                item.setBackground(QBrush(QColor("#00aa00")))
                item.setForeground(QBrush(QColor("white")))
            elif change >= 1:
                item.setBackground(QBrush(QColor("#006600")))
            elif change <= -2:
                item.setBackground(QBrush(QColor("#aa0000")))
                item.setForeground(QBrush(QColor("white")))
            elif change <= -1:
                item.setBackground(QBrush(QColor("#660000")))
            
            self.price_table.setItem(row, col, item)
        
        # 1m Range
        range_pct = changes.get('range_1m_pct', 0)
        range_item = QTableWidgetItem(f"{range_pct:.2f}%")
        if range_pct >= 3:
            range_item.setBackground(QBrush(QColor("#ff6600")))
        self.price_table.setItem(row, 6, range_item)
        
        # Status
        status = "Normal"
        if abs(changes.get('1m_change_pct', 0)) >= 2:
            status = "⚡ VOLATILE"
        self.price_table.setItem(row, 7, QTableWidgetItem(status))
    
    def _check_alerts(self, symbol: str, changes: Dict, threshold: float):
        """Check if any alert conditions are met."""
        now = datetime.now()
        
        # Check various timeframes
        checks = [
            ('10s_change_pct', 10, 'Flash'),
            ('30s_change_pct', 30, 'Spike'),
            ('1m_change_pct', 60, 'Move'),
        ]
        
        for key, seconds, alert_type in checks:
            change = changes.get(key, 0)
            
            if abs(change) >= threshold:
                direction = "UP 🚀" if change > 0 else "DOWN 📉"
                
                alert = PriceAlert(
                    timestamp=now,
                    symbol=symbol,
                    alert_type=f"{alert_type} {direction}",
                    price_from=changes['last_price'],
                    price_to=changes['current_price'],
                    change_pct=change,
                    timeframe_seconds=seconds,
                    message=f"{symbol} {direction} {abs(change):.2f}% in {seconds}s!"
                )
                
                self._trigger_alert(alert)
                break  # Only one alert per update
    
    def _trigger_alert(self, alert: PriceAlert):
        """Trigger an alert with visuals and sound."""
        self.alerts.append(alert)
        
        # Update banner
        color = "#00ff00" if alert.change_pct > 0 else "#ff0000"
        arrow = "🚀" if alert.change_pct > 0 else "📉"
        
        banner_text = (
            f"{arrow} {alert.symbol}: {alert.change_pct:+.2f}% in {alert.timeframe_seconds}s\n"
            f"${alert.price_from:,.2f} → ${alert.price_to:,.2f}"
        )
        self.alert_banner_text.setText(banner_text)
        self.alert_banner.setVisible(True)
        
        # Auto-hide after 5 seconds
        QTimer.singleShot(5000, lambda: self.alert_banner.setVisible(False))
        
        # Add to log
        timestamp = alert.timestamp.strftime("%H:%M:%S")
        log_entry = f"<span style='color: {color};'>[{timestamp}] {alert.message}</span>"
        self.alerts_log.append(log_entry)
        
        # Play sound
        if self.sound_check.isChecked():
            try:
                import winsound
                if alert.change_pct > 0:
                    winsound.Beep(1000, 200)  # High pitch for up
                    winsound.Beep(1200, 200)
                else:
                    winsound.Beep(500, 200)   # Low pitch for down
                    winsound.Beep(400, 200)
            except:
                pass
        
        # Bring window to front
        self.activateWindow()
        self.raise_()


def run_console_monitor(symbol: str, threshold: float, interval: int):
    """Run console-based monitoring."""
    print(f"\n⚡ Fast Price Monitor - {symbol}")
    print(f"   Threshold: {threshold}%")
    print(f"   Interval: {interval} seconds")
    print(f"   Press Ctrl+C to stop\n")
    print("-" * 60)
    
    tracker = FastPriceTracker(symbol)
    
    try:
        while True:
            data = get_realtime_price(symbol)
            
            if data and data['price']:
                changes = tracker.add_price(data['price'])
                
                if changes:
                    now = datetime.now().strftime("%H:%M:%S")
                    price = data['price']
                    c10 = changes['10s_change_pct']
                    c30 = changes['30s_change_pct']
                    c1m = changes['1m_change_pct']
                    
                    # Alert check
                    alert = ""
                    if abs(c10) >= threshold:
                        alert = f"  ⚡ ALERT: {c10:+.2f}% in 10s!"
                    elif abs(c30) >= threshold:
                        alert = f"  ⚡ ALERT: {c30:+.2f}% in 30s!"
                    elif abs(c1m) >= threshold:
                        alert = f"  ⚡ ALERT: {c1m:+.2f}% in 1m!"
                    
                    print(f"[{now}] ${price:,.2f}  10s:{c10:+.2f}%  30s:{c30:+.2f}%  1m:{c1m:+.2f}%{alert}")
                    
                    if alert:
                        try:
                            import winsound
                            winsound.Beep(1000, 300)
                        except:
                            print("\a")  # Terminal bell
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


def main():
    parser = argparse.ArgumentParser(description="Fast Price Monitor for Crypto")
    parser.add_argument('--symbol', '-s', default='BTC-USD', help='Symbol to monitor')
    parser.add_argument('--threshold', '-t', type=float, default=2.0, help='Alert threshold %')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Check interval in seconds')
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    parser.add_argument('--console', action='store_true', help='Run in console mode')
    
    args = parser.parse_args()
    
    if args.console or not HAS_PYQT:
        if not HAS_YFINANCE:
            print("Error: yfinance not installed. Run: pip install yfinance")
            sys.exit(1)
        run_console_monitor(args.symbol, args.threshold, args.interval)
    else:
        if not HAS_PYQT:
            print("PyQt6 not installed. Running in console mode...")
            run_console_monitor(args.symbol, args.threshold, args.interval)
            return
        
        app = QApplication(sys.argv)
        
        # Dark theme
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        app.setPalette(palette)
        
        window = FastMonitorGUI()
        window.show()
        
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
