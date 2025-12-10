"""
Nifty 50 Market Breadth Visualizer
==================================
Real-time visualization of market breadth showing advances vs declines.

Features:
- Tracks all Nifty 50 stocks in real-time
- Shows advances (LTP > prev_close) and declines (LTP < prev_close)
- Horizontal bar chart with green (advances) and red (declines)
- Lists stocks in each category with their % change
- Updates dynamically as prices change

Usage:
    python -m dhan_trading.visualizers.market_breadth
"""
import os
import sys
import signal
import logging
from datetime import datetime, date, time as dt_time
from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSplitter, QStatusBar, QScrollArea, QSizePolicy,
    QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPalette

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.redis_subscriber import RedisSubscriber, CHANNEL_QUOTES
from dhan_trading.market_feed.redis_publisher import QuoteData
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Market timing
MARKET_OPEN_TIME = dt_time(9, 15)
MARKET_CLOSE_TIME = dt_time(15, 30)


@dataclass
class StockBreadthData:
    """Data for a single stock's breadth status."""
    security_id: int
    symbol: str
    display_name: str
    ltp: float = 0.0
    prev_close: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    status: str = "unchanged"  # "advance", "decline", "unchanged"
    last_update: datetime = field(default_factory=datetime.now)
    
    def update(self, ltp: float, prev_close: Optional[float] = None):
        """Update stock data with new quote."""
        self.ltp = ltp
        if prev_close is not None and prev_close > 0:
            self.prev_close = prev_close
        
        if self.prev_close > 0:
            self.change = self.ltp - self.prev_close
            self.change_pct = (self.change / self.prev_close) * 100
            
            if self.ltp > self.prev_close:
                self.status = "advance"
            elif self.ltp < self.prev_close:
                self.status = "decline"
            else:
                self.status = "unchanged"
        
        self.last_update = datetime.now()


class BreadthBarWidget(QWidget):
    """Widget showing the breadth bar (advances vs declines)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.advances = 0
        self.declines = 0
        self.unchanged = 0
        self.total = 50
        self.setMinimumHeight(80)
        self.setMinimumWidth(400)
    
    def update_breadth(self, advances: int, declines: int, unchanged: int):
        """Update the breadth data."""
        self.advances = advances
        self.declines = declines
        self.unchanged = unchanged
        self.total = advances + declines + unchanged
        self.update()
    
    def paintEvent(self, event):
        """Draw the breadth bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width() - 20
        height = 50
        x_start = 10
        y_start = 15
        
        # Background
        painter.fillRect(x_start, y_start, width, height, QColor(40, 40, 60))
        
        if self.total == 0:
            return
        
        # Calculate widths
        adv_width = int((self.advances / self.total) * width) if self.total > 0 else 0
        dec_width = int((self.declines / self.total) * width) if self.total > 0 else 0
        unc_width = width - adv_width - dec_width
        
        # Draw advances (green) from left
        if adv_width > 0:
            painter.fillRect(x_start, y_start, adv_width, height, QColor(0, 200, 83))
        
        # Draw unchanged (gray) in middle
        if unc_width > 0:
            painter.fillRect(x_start + adv_width, y_start, unc_width, height, QColor(100, 100, 100))
        
        # Draw declines (red) from right
        if dec_width > 0:
            painter.fillRect(x_start + adv_width + unc_width, y_start, dec_width, height, QColor(255, 82, 82))
        
        # Draw border
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(x_start, y_start, width, height)
        
        # Draw text labels
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        # Advances label (white on green)
        if adv_width > 40:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(x_start + 5, y_start + 32, f"▲ {self.advances}")
        
        # Declines label (white on red)
        if dec_width > 40:
            painter.setPen(QColor(255, 255, 255))
            dec_text = f"▼ {self.declines}"
            text_width = painter.fontMetrics().horizontalAdvance(dec_text)
            painter.drawText(x_start + width - text_width - 5, y_start + 32, dec_text)
        
        # Ratio in center
        painter.setPen(QColor(255, 255, 255))
        ratio_text = f"{self.advances}:{self.declines}"
        text_width = painter.fontMetrics().horizontalAdvance(ratio_text)
        painter.drawText(x_start + (width - text_width) // 2, y_start + 32, ratio_text)


class StockListWidget(QWidget):
    """Widget showing list of stocks with their status."""
    
    def __init__(self, title: str, color: QColor, parent=None):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.stocks: List[StockBreadthData] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Title
        self.title_label = QLabel(f"{self.title} (0)")
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.color.name()};
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
            }}
        """)
        layout.addWidget(self.title_label)
        
        # Scroll area for stocks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e2e;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        
        self.stocks_container = QWidget()
        self.stocks_layout = QVBoxLayout(self.stocks_container)
        self.stocks_layout.setContentsMargins(5, 5, 5, 5)
        self.stocks_layout.setSpacing(2)
        self.stocks_layout.addStretch()
        
        scroll.setWidget(self.stocks_container)
        layout.addWidget(scroll)
    
    def update_stocks(self, stocks: List[StockBreadthData]):
        """Update the stock list."""
        self.stocks = sorted(stocks, key=lambda x: x.change_pct, reverse=(self.title == "Advances"))
        self.title_label.setText(f"{self.title} ({len(stocks)})")
        
        # Clear existing items
        while self.stocks_layout.count() > 1:
            item = self.stocks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add stock items
        for stock in self.stocks:
            item = self._create_stock_item(stock)
            self.stocks_layout.insertWidget(self.stocks_layout.count() - 1, item)
    
    def _create_stock_item(self, stock: StockBreadthData) -> QWidget:
        """Create a widget for a single stock."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #2d2d44;
                border-radius: 3px;
                padding: 2px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(5)
        
        # Symbol
        symbol_label = QLabel(stock.display_name[:20])
        symbol_label.setStyleSheet("color: white; font-size: 12px;")
        symbol_label.setMinimumWidth(120)
        layout.addWidget(symbol_label)
        
        # LTP
        ltp_label = QLabel(f"₹{stock.ltp:,.2f}")
        ltp_label.setStyleSheet("color: #FFFF00; font-size: 12px;")
        ltp_label.setMinimumWidth(80)
        layout.addWidget(ltp_label)
        
        # Change %
        change_color = "#00C853" if stock.change_pct >= 0 else "#FF5252"
        sign = "+" if stock.change_pct >= 0 else ""
        change_label = QLabel(f"{sign}{stock.change_pct:.2f}%")
        change_label.setStyleSheet(f"color: {change_color}; font-size: 12px; font-weight: bold;")
        change_label.setMinimumWidth(60)
        layout.addWidget(change_label)
        
        return frame


class BreadthSubscriber(RedisSubscriber):
    """Redis subscriber for market breadth that forwards quotes to the callback."""
    
    def __init__(self, callback, config=None):
        super().__init__(config)
        self._callback = callback
    
    def on_quote(self, quote: QuoteData):
        """Forward quote to callback."""
        if self._callback:
            self._callback(quote)
    
    def start(self):
        """Connect, subscribe, and start listening."""
        if self.connect():
            self.subscribe([CHANNEL_QUOTES])
            self.run(blocking=False)


class SignalEmitter(QObject):
    """Signal emitter for thread-safe UI updates."""
    quote_received = pyqtSignal(object)
    status_update = pyqtSignal(str)


class MarketBreadthVisualizer(QMainWindow):
    """Main window for market breadth visualization."""
    
    def __init__(self):
        super().__init__()
        
        self.signals = SignalEmitter()
        self.signals.quote_received.connect(self._on_quote)
        self.signals.status_update.connect(self._on_status_update)
        
        # Stock tracking
        self.nifty50_stocks: Dict[int, StockBreadthData] = {}  # security_id -> data
        self.advances: Set[int] = set()
        self.declines: Set[int] = set()
        self.unchanged: Set[int] = set()
        
        # Database connection
        self._db_engine = None
        self._init_database()
        
        # Load Nifty 50 stocks
        self._load_nifty50_stocks()
        
        # Setup UI
        self._setup_ui()
        
        # Load previous close from database
        self._load_prev_close()
        
        # Redis subscriber
        self._subscriber = None
        self._start_subscriber()
        
        # Update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.start(500)  # Update display every 500ms
        
        # Stats
        self.quote_count = 0
        self.last_quote_time = None
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
            host = os.getenv('MYSQL_HOST', 'localhost')
            port = os.getenv('MYSQL_PORT', '3306')
            database = os.getenv('DHAN_DB', 'dhan_trading')
            
            connection_string = f"mysql+pymysql://root:{password}@{host}:{port}/{database}"
            self._db_engine = create_engine(connection_string, pool_pre_ping=True)
            logger.info("Database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def _load_nifty50_stocks(self):
        """Load Nifty 50 stocks from instrument selector."""
        try:
            selector = InstrumentSelector()
            stocks = selector.get_nifty50_stocks()
            
            for inst in stocks:
                sec_id = inst['security_id']
                self.nifty50_stocks[sec_id] = StockBreadthData(
                    security_id=sec_id,
                    symbol=inst.get('underlying_symbol', inst['symbol']),
                    display_name=inst.get('display_name', inst['symbol'])
                )
                self.unchanged.add(sec_id)
            
            logger.info(f"Loaded {len(self.nifty50_stocks)} Nifty 50 stocks")
        except Exception as e:
            logger.error(f"Failed to load Nifty 50 stocks: {e}")
    
    def _load_prev_close(self):
        """Load previous close prices from database."""
        if not self._db_engine:
            return
        
        try:
            with self._db_engine.connect() as conn:
                # Get latest quote with day_close (prev day's close) for each Nifty 50 stock
                for sec_id, stock in self.nifty50_stocks.items():
                    result = conn.execute(text("""
                        SELECT day_close, ltp
                        FROM dhan_quotes
                        WHERE security_id = :sec_id
                          AND day_close IS NOT NULL
                          AND day_close > 0
                        ORDER BY received_at DESC
                        LIMIT 1
                    """), {"sec_id": sec_id})
                    
                    row = result.fetchone()
                    if row:
                        stock.prev_close = float(row[0])
                        stock.ltp = float(row[1])
                        stock.update(stock.ltp, stock.prev_close)
                        logger.debug(f"Loaded prev_close for {stock.symbol}: {stock.prev_close}")
                
                # Update buckets based on loaded data
                self._update_buckets()
                
            logger.info(f"Loaded prev_close for {sum(1 for s in self.nifty50_stocks.values() if s.prev_close > 0)} stocks")
        except Exception as e:
            logger.error(f"Error loading prev_close: {e}")
    
    def _update_buckets(self):
        """Update advances/declines/unchanged buckets."""
        self.advances.clear()
        self.declines.clear()
        self.unchanged.clear()
        
        for sec_id, stock in self.nifty50_stocks.items():
            if stock.status == "advance":
                self.advances.add(sec_id)
            elif stock.status == "decline":
                self.declines.add(sec_id)
            else:
                self.unchanged.add(sec_id)
    
    def _setup_ui(self):
        """Setup the UI."""
        self.setWindowTitle("📊 Nifty 50 Market Breadth")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QLabel {
                color: white;
            }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Breadth bar
        self.breadth_bar = BreadthBarWidget()
        main_layout.addWidget(self.breadth_bar)
        
        # Stats row
        stats_row = self._create_stats_row()
        main_layout.addWidget(stats_row)
        
        # Splitter for advances and declines lists
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Advances list
        self.advances_list = StockListWidget("▲ Advances", QColor(0, 200, 83))
        splitter.addWidget(self.advances_list)
        
        # Declines list
        self.declines_list = StockListWidget("▼ Declines", QColor(255, 82, 82))
        splitter.addWidget(self.declines_list)
        
        splitter.setSizes([450, 450])
        main_layout.addWidget(splitter, stretch=1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #888;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Connecting to Redis...")
    
    def _create_header(self) -> QWidget:
        """Create header widget."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        
        # Title
        title = QLabel("📊 Nifty 50 Market Breadth")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00E5FF;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Last update time
        self.last_update_label = QLabel("Last Update: --:--:--")
        self.last_update_label.setStyleSheet("font-size: 14px; color: #FFFF00;")
        layout.addWidget(self.last_update_label)
        
        return frame
    
    def _create_stats_row(self) -> QWidget:
        """Create stats row widget."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(30)
        
        # Advances count
        self.adv_count_label = QLabel("▲ Advances: 0")
        self.adv_count_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00C853;")
        layout.addWidget(self.adv_count_label)
        
        # Unchanged count
        self.unc_count_label = QLabel("● Unchanged: 0")
        self.unc_count_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #888;")
        layout.addWidget(self.unc_count_label)
        
        # Declines count
        self.dec_count_label = QLabel("▼ Declines: 0")
        self.dec_count_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF5252;")
        layout.addWidget(self.dec_count_label)
        
        layout.addStretch()
        
        # A/D Ratio
        self.ratio_label = QLabel("A/D Ratio: --")
        self.ratio_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(self.ratio_label)
        
        return frame
    
    def _start_subscriber(self):
        """Start the Redis subscriber."""
        def quote_callback(quote: QuoteData):
            # Only process Nifty 50 stocks
            if quote.security_id in self.nifty50_stocks:
                self.signals.quote_received.emit(quote)
        
        self._subscriber = BreadthSubscriber(callback=quote_callback)
        self._subscriber.start()
        self.signals.status_update.emit("Connected to Redis. Waiting for quotes...")
    
    def _on_quote(self, quote: QuoteData):
        """Handle incoming quote."""
        sec_id = quote.security_id
        
        if sec_id not in self.nifty50_stocks:
            return
        
        stock = self.nifty50_stocks[sec_id]
        old_status = stock.status
        
        # Update stock data - use day_close as prev_close (day_close is previous day's close in Dhan API)
        prev_close_value = quote.prev_close if quote.prev_close and quote.prev_close > 0 else quote.day_close
        stock.update(quote.ltp, prev_close_value)
        
        # Update buckets if status changed
        if stock.status != old_status:
            # Remove from old bucket
            if old_status == "advance":
                self.advances.discard(sec_id)
            elif old_status == "decline":
                self.declines.discard(sec_id)
            else:
                self.unchanged.discard(sec_id)
            
            # Add to new bucket
            if stock.status == "advance":
                self.advances.add(sec_id)
            elif stock.status == "decline":
                self.declines.add(sec_id)
            else:
                self.unchanged.add(sec_id)
        
        self.quote_count += 1
        self.last_quote_time = datetime.now()
    
    def _on_status_update(self, message: str):
        """Handle status update."""
        self.status_bar.showMessage(message)
    
    def _update_display(self):
        """Update the display."""
        adv_count = len(self.advances)
        dec_count = len(self.declines)
        unc_count = len(self.unchanged)
        
        # Update breadth bar
        self.breadth_bar.update_breadth(adv_count, dec_count, unc_count)
        
        # Update labels
        self.adv_count_label.setText(f"▲ Advances: {adv_count}")
        self.dec_count_label.setText(f"▼ Declines: {dec_count}")
        self.unc_count_label.setText(f"● Unchanged: {unc_count}")
        
        # A/D Ratio
        if dec_count > 0:
            ratio = adv_count / dec_count
            self.ratio_label.setText(f"A/D Ratio: {ratio:.2f}")
        else:
            self.ratio_label.setText(f"A/D Ratio: {adv_count}:0")
        
        # Update stock lists
        adv_stocks = [self.nifty50_stocks[sid] for sid in self.advances]
        dec_stocks = [self.nifty50_stocks[sid] for sid in self.declines]
        
        self.advances_list.update_stocks(adv_stocks)
        self.declines_list.update_stocks(dec_stocks)
        
        # Update last update time
        if self.last_quote_time:
            self.last_update_label.setText(f"Last Update: {self.last_quote_time.strftime('%H:%M:%S')}")
        
        # Update status bar
        self.status_bar.showMessage(
            f"📊 Quotes: {self.quote_count:,} | "
            f"Advances: {adv_count} | Declines: {dec_count} | Unchanged: {unc_count}"
        )
    
    def closeEvent(self, event):
        """Handle close event."""
        if self._subscriber:
            self._subscriber.stop()
        event.accept()


def main():
    """Main entry point."""
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark palette
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 46))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 46))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = MarketBreadthVisualizer()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
