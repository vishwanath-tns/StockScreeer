"""
Market Feed Service Launcher
============================
Main entry point to run the Dhan market feed service.

This is a PURE PUBLISHER service:
- Connects to Dhan WebSocket
- Receives market data
- Publishes to Redis (Pub/Sub + Streams)

NO database writes - that's done by separate subscriber services.
"""

import os
import sys
import signal
import logging
import argparse
import asyncio
import threading
import time
from datetime import datetime, time as dt_time
from typing import List, Dict, Optional

# Add project root to path for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from dhan_trading.market_feed.feed_config import FeedConfig, FeedMode, ExchangeSegment
from dhan_trading.market_feed.feed_service import DhanFeedService
from dhan_trading.market_feed.redis_publisher import RedisPublisher
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

logger = logging.getLogger(__name__)


class MarketFeedLauncher:
    """
    Launches the market feed publisher service.
    
    Responsibilities:
    - Connect to Dhan WebSocket
    - Subscribe to instruments
    - Publish data to Redis
    
    NOT responsible for:
    - Database writes (separate DB Writer subscriber)
    - Visualization (separate visualizer subscribers)
    - Alerts (separate alert engine subscriber)
    """
    
    # Market hours (IST)
    MARKET_OPEN = dt_time(9, 0)    # 9:00 AM
    MARKET_CLOSE = dt_time(15, 35)  # 3:35 PM (with buffer)
    PRE_MARKET_START = dt_time(9, 0)
    
    def __init__(
        self,
        feed_mode: FeedMode = FeedMode.QUOTE,
        run_outside_market_hours: bool = False
    ):
        """
        Initialize the launcher.
        
        Args:
            feed_mode: Type of market data to subscribe (TICKER, QUOTE, FULL)
            run_outside_market_hours: If True, run even outside market hours (for testing)
        """
        self.feed_mode = feed_mode
        self.run_outside_market_hours = run_outside_market_hours
        
        # Services
        self._feed_service: Optional[DhanFeedService] = None
        
        # State
        self._running = False
        self._shutdown_event = threading.Event()
        
        # Configuration
        self._feed_config = FeedConfig()  # Uses env vars by default
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        if self.run_outside_market_hours:
            return True
        
        now = datetime.now().time()
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if datetime.now().weekday() >= 5:
            return False
        
        return self.PRE_MARKET_START <= now <= self.MARKET_CLOSE
    
    def _get_instruments_to_subscribe(self) -> List[Dict]:
        """
        Get list of instruments to subscribe.
        Returns list of dicts with 'security_id' and 'exchange_segment'.
        """
        selector = InstrumentSelector()
        instruments = []
        
        # Get Nifty Futures (current and next expiry)
        logger.info("Fetching Nifty Futures instruments...")
        nifty_futures = selector.get_nifty_futures(expiries=[0, 1])
        
        for inst in nifty_futures:
            instruments.append({
                'security_id': inst['security_id'],
                'exchange_segment': inst.get('exchange_segment', 'NSE_FNO')
            })
            logger.info(f"  Nifty: {inst.get('display_name', inst['symbol'])} (expiry: {inst.get('expiry_date', 'N/A')})")
        
        # Get Bank Nifty Futures
        logger.info("Fetching Bank Nifty Futures instruments...")
        banknifty_futures = selector.get_banknifty_futures(expiries=[0, 1])
        
        for inst in banknifty_futures:
            instruments.append({
                'security_id': inst['security_id'],
                'exchange_segment': inst.get('exchange_segment', 'NSE_FNO')
            })
            logger.info(f"  BankNifty: {inst.get('display_name', inst['symbol'])} (expiry: {inst.get('expiry_date', 'N/A')})")
        
        # Get MCX Commodity Futures (nearest expiry)
        logger.info("Fetching MCX Commodity Futures instruments...")
        commodity_futures = selector.get_major_commodity_futures(expiries=[0])
        
        for inst in commodity_futures:
            instruments.append({
                'security_id': inst['security_id'],
                'exchange_segment': inst.get('exchange_segment', 'MCX_COMM')
            })
            logger.info(f"  Commodity: {inst.get('display_name', inst['symbol'])} (expiry: {inst.get('expiry_date', 'N/A')})")
        
        # Get Nifty 50 stocks (equity)
        logger.info("Fetching Nifty 50 stocks...")
        nifty50_stocks = selector.get_nifty50_stocks()
        
        for inst in nifty50_stocks:
            instruments.append({
                'security_id': inst['security_id'],
                'exchange_segment': inst.get('exchange_segment', 'NSE_EQ')
            })
            logger.info(f"  Stock: {inst.get('symbol')} - {inst.get('display_name', '')}")
        
        logger.info(f"Total instruments to subscribe: {len(instruments)}")
        return instruments
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
            self._running = False
            # Also stop the feed service to break the receive loop
            if self._feed_service:
                self._feed_service._running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _run_async(self, instruments: List[Dict]):
        """Async main loop for the feed service."""
        # Map feed mode to string
        mode_map = {
            FeedMode.TICKER: 'TICKER',
            FeedMode.QUOTE: 'QUOTE',
            FeedMode.FULL: 'FULL'
        }
        feed_type = mode_map.get(self.feed_mode, 'QUOTE')
        
        # Run the feed service
        await self._feed_service.run(instruments, feed_type)
    
    def start(self):
        """Start the market feed publisher service."""
        logger.info("=" * 60)
        logger.info("Starting Market Feed Publisher")
        logger.info("=" * 60)
        
        # Check market hours
        if not self._is_market_hours():
            logger.warning("Outside market hours. Use --force to run anyway.")
            return
        
        # Validate configuration
        try:
            self._feed_config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Initialize feed service (it creates its own Redis publisher)
        logger.info("Initializing WebSocket feed service...")
        self._feed_service = DhanFeedService(self._feed_config)
        
        # Connect feed service's Redis publisher
        if not self._feed_service.redis.connect():
            logger.error("Failed to connect to Redis!")
            return
        logger.info("Redis publisher connected")
        
        # Get instruments to subscribe
        instruments = self._get_instruments_to_subscribe()
        
        if not instruments:
            logger.error("No instruments to subscribe!")
            self.stop()
            return
        
        self._running = True
        logger.info("=" * 60)
        logger.info("Market Feed Publisher is RUNNING")
        logger.info(f"  Feed Mode: {self.feed_mode.name}")
        logger.info(f"  Instruments: {len(instruments)}")
        logger.info("  Publishing to: Redis Pub/Sub + Streams")
        logger.info("  Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # Run async feed service
        try:
            asyncio.run(self._run_async(instruments))
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the publisher service gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping publisher...")
        self._running = False
        
        # Stop feed service
        if self._feed_service:
            try:
                asyncio.run(self._feed_service.disconnect())
            except:
                pass
            
            # Print final stats
            stats = self._feed_service.redis.get_stats()
            logger.info("=" * 60)
            logger.info("Final Statistics:")
            logger.info(f"  Quotes Published: {stats.get('quotes_published', 0)}")
            logger.info(f"  Ticks Published: {stats.get('ticks_published', 0)}")
            logger.info(f"  Errors: {stats.get('errors', 0)}")
            logger.info("=" * 60)
            
            # Disconnect Redis
            self._feed_service.redis.disconnect()
            logger.info("Redis publisher disconnected")
        
        logger.info("Market Feed Publisher stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Dhan Market Feed Publisher - Publishes data to Redis",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--mode',
        choices=['ticker', 'quote', 'full'],
        default='quote',
        help='Feed mode: ticker (LTP only), quote (full trade), full (with depth)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Run even outside market hours (for testing)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Map mode string to enum
    mode_map = {
        'ticker': FeedMode.TICKER,
        'quote': FeedMode.QUOTE,
        'full': FeedMode.FULL
    }
    feed_mode = mode_map[args.mode]
    
    # Create and start launcher
    launcher = MarketFeedLauncher(
        feed_mode=feed_mode,
        run_outside_market_hours=args.force
    )
    
    launcher.start()


if __name__ == "__main__":
    main()