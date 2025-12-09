"""
Live Quote Visualizer
=====================
Terminal-based real-time quote display.

Subscribes to Redis pub/sub and displays quotes in a formatted table.

Usage:
    python -m dhan_trading.visualizers.quote_visualizer
"""
import os
import sys
import signal
import logging
from datetime import datetime
from typing import Dict, Optional
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.redis_subscriber import (
    RedisSubscriber, CHANNEL_QUOTES
)
from dhan_trading.market_feed.redis_publisher import QuoteData
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

logging.basicConfig(level=logging.WARNING)  # Quiet logging
logger = logging.getLogger(__name__)


class QuoteVisualizer(RedisSubscriber):
    """
    Real-time quote visualizer for terminal.
    
    Displays:
    - Symbol name
    - LTP with change
    - Volume
    - Bid/Ask quantities
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Instrument name mapping
        self._instrument_names: Dict[int, str] = {}
        
        # Store latest quotes per instrument
        self._latest_quotes: Dict[int, QuoteData] = {}
        
        # Display settings
        self._update_count = 0
        self._last_display_time = 0
        self._display_interval = 0.5  # Update display every 0.5 seconds
    
    def set_instrument_names(self, names: Dict[int, str]):
        """Set mapping from security_id to display name."""
        self._instrument_names = names
    
    def load_instrument_names(self):
        """Load instrument names from database."""
        try:
            selector = InstrumentSelector()
            
            # Get Nifty futures
            nifty_futures = selector.get_nifty_futures(expiries=[0, 1])
            for inst in nifty_futures:
                self._instrument_names[inst['security_id']] = inst.get('display_name', inst['symbol'])
            
            # Get Bank Nifty futures
            bnf_futures = selector.get_banknifty_futures(expiries=[0, 1])
            for inst in bnf_futures:
                self._instrument_names[inst['security_id']] = inst.get('display_name', inst['symbol'])
            
            logger.info(f"Loaded {len(self._instrument_names)} instrument names")
        except Exception as e:
            logger.error(f"Failed to load instrument names: {e}")
    
    def on_quote(self, quote: QuoteData):
        """Handle incoming quote."""
        self._update_count += 1
        self._latest_quotes[quote.security_id] = quote
        
        # Rate-limit display updates
        now = time.time()
        if now - self._last_display_time >= self._display_interval:
            self._display_quotes()
            self._last_display_time = now
    
    def _display_quotes(self):
        """Display all latest quotes in a formatted table."""
        # Clear screen (works on Windows and Unix)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 90)
        print(f"{'LIVE MARKET QUOTES':^90}")
        print(f"{'Updated: ' + datetime.now().strftime('%H:%M:%S'):^90}")
        print("=" * 90)
        print()
        
        # Table header
        print(f"{'Symbol':<25} {'LTP':>12} {'Change':>10} {'Change%':>8} {'Volume':>12} {'OI':>12}")
        print("-" * 90)
        
        # Sort by security_id for consistent display
        for sec_id in sorted(self._latest_quotes.keys()):
            quote = self._latest_quotes[sec_id]
            name = self._instrument_names.get(sec_id, str(sec_id))
            
            # Calculate change
            change = quote.ltp - quote.day_close if quote.day_close else 0
            change_pct = (change / quote.day_close * 100) if quote.day_close else 0
            
            # Color for change (ANSI codes)
            if change > 0:
                color = "\033[92m"  # Green
                sign = "+"
            elif change < 0:
                color = "\033[91m"  # Red
                sign = ""
            else:
                color = "\033[0m"   # Default
                sign = ""
            reset = "\033[0m"
            
            # Format volume
            vol_str = f"{quote.volume:,}" if quote.volume else "-"
            oi_str = f"{quote.open_interest:,}" if quote.open_interest else "-"
            
            print(f"{name:<25} {quote.ltp:>12.2f} "
                  f"{color}{sign}{change:>9.2f}{reset} "
                  f"{color}{sign}{change_pct:>7.2f}%{reset} "
                  f"{vol_str:>12} {oi_str:>12}")
        
        print()
        print("-" * 90)
        print(f"Total updates: {self._update_count} | Instruments: {len(self._latest_quotes)}")
        print()
        print("Press Ctrl+C to stop")
    
    def show_stream_history(self, count: int = 10):
        """Show recent quotes from Redis Stream (for catch-up)."""
        from dhan_trading.market_feed.redis_publisher import STREAM_QUOTES
        
        print(f"\nLast {count} quotes from stream:")
        print("-" * 60)
        
        entries = self.read_stream_latest(STREAM_QUOTES, count)
        for entry in reversed(entries):  # Show oldest first
            data = entry['data']
            sec_id = int(data.get('security_id', 0))
            name = self._instrument_names.get(sec_id, str(sec_id))
            ltp = float(data.get('ltp', 0))
            print(f"  {name}: LTP={ltp:.2f}")


def main():
    """Run the quote visualizer."""
    print("=" * 60)
    print("Live Quote Visualizer")
    print("=" * 60)
    print()
    print("Connecting to Redis...")
    
    visualizer = QuoteVisualizer()
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n\nStopping visualizer...")
        visualizer.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Load instrument names
    print("Loading instrument names...")
    visualizer.load_instrument_names()
    
    if visualizer.connect():
        print("Connected to Redis!")
        print()
        
        # Show recent history from stream
        visualizer.show_stream_history(5)
        print()
        
        # Subscribe and run
        print("Subscribing to quote channel...")
        print("Waiting for live quotes... (start the feed publisher if not running)")
        print()
        
        visualizer.subscribe([CHANNEL_QUOTES])
        visualizer.run(blocking=True)
    else:
        print("Failed to connect to Redis!")
        print("Make sure Redis is running on localhost:6379")
        sys.exit(1)


if __name__ == "__main__":
    main()
