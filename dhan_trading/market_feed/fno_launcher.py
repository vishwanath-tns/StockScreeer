"""
FNO Market Feed Service Launcher
=================================
Separate Dhan WebSocket connection for Futures & Options trading.

ARCHITECTURE:
- Independent launcher, not sharing with spot market feed
- Subscribes to: Nifty Futures, Bank Nifty Futures, Index Options
- Uses same Redis channels as main feed (for multiplexing)
- Separate database tables: dhan_fno_quotes, dhan_options_quotes
- Can run simultaneously with spot market feed

This allows parallel data collection without interfering with the running
equity (spot) market feed service.
"""

import os
import sys
import signal
import logging
import argparse
import asyncio
import threading
import time
import redis
from datetime import datetime, time as dt_time
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from dhan_trading.market_feed.feed_config import FeedConfig, FeedMode, ExchangeSegment
from dhan_trading.market_feed.feed_service import DhanFeedService
from dhan_trading.market_feed.redis_publisher import RedisPublisher
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

logger = logging.getLogger(__name__)


class FNOFeedLauncher:
    """
    Launches the FNO (Futures & Options) feed publisher service.
    
    Key differences from spot market feed:
    - Focuses on derivatives (NSE_FNO, MCX_COMM segments)
    - Can run independently without affecting spot data collection
    - Uses same Dhan WebSocket but separate subscription set
    - Publishes to same Redis (dhan:quotes channel for quotes)
    - Writes to separate tables (dhan_fno_quotes, dhan_options_quotes)
    
    Responsibilities:
    - Connect to Dhan WebSocket
    - Subscribe to Futures & Options instruments
    - Publish data to Redis
    
    NOT responsible for:
    - Database writes (separate FNO DB Writer subscriber)
    - Visualization (separate visualizers)
    """
    
    # Market hours (IST)
    MARKET_OPEN = dt_time(9, 15)
    MARKET_CLOSE = dt_time(15, 35)
    PRE_MARKET_START = dt_time(9, 15)
    
    def __init__(
        self,
        feed_mode: FeedMode = FeedMode.QUOTE,
        run_outside_market_hours: bool = False,
        include_nifty_options: bool = True,
        include_banknifty_options: bool = True,
        include_futures: bool = True,
        include_commodities: bool = True  # MCX commodities included by default
    ):
        """
        Initialize FNO launcher.
        
        Args:
            feed_mode: Type of market data (TICKER, QUOTE, FULL)
            run_outside_market_hours: If True, run outside market hours (testing)
            include_nifty_options: Subscribe to Nifty options
            include_banknifty_options: Subscribe to Bank Nifty options
            include_futures: Subscribe to Nifty/BankNifty futures
            include_commodities: Include MCX commodities in this feed
        """
        self.feed_mode = feed_mode
        self.run_outside_market_hours = run_outside_market_hours
        self.include_nifty_options = include_nifty_options
        self.include_banknifty_options = include_banknifty_options
        self.include_futures = include_futures
        self.include_commodities = include_commodities
        
        # Services
        self._feed_service: Optional[DhanFeedService] = None
        
        # State
        self._running = False
        self._shutdown_event = threading.Event()
        
        # Configuration
        self._feed_config = FeedConfig()
        
        # Redis for status reporting
        self._redis_client = None
        self._quote_count = 0
        self._start_time = None
    
    def _init_redis_status(self):
        """Initialize Redis connection for status reporting."""
        try:
            self._redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self._redis_client.ping()
            self._start_time = datetime.now()
            logger.info("Redis status reporting initialized")
        except Exception as e:
            logger.warning(f"Redis status reporting not available: {e}")
            self._redis_client = None
    
    def _publish_status(self, connected: bool, instruments_count: int):
        """Publish feed status to Redis."""
        if not self._redis_client:
            return
        
        try:
            uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            self._redis_client.hset(
                'fno:feed:status',
                mapping={
                    'connected': 'true' if connected else 'false',
                    'quotes_count': str(self._quote_count),
                    'instruments_count': str(instruments_count),
                    'last_update': datetime.now().isoformat(),
                    'uptime_seconds': str(int(uptime)),
                    'status': 'running' if connected else 'disconnected'
                }
            )
            self._redis_client.expire('fno:feed:status', 60)  # Expire after 60 seconds
        except Exception as e:
            logger.debug(f"Error publishing status: {e}")
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        if self.run_outside_market_hours:
            return True
        
        now = datetime.now().time()
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if datetime.now().weekday() >= 5:
            return False
        
        return self.PRE_MARKET_START <= now <= self.MARKET_CLOSE
    
    def _get_fno_instruments_to_subscribe(self) -> List[Dict]:
        """
        Get FNO instruments to subscribe.
        Returns list of dicts with 'security_id' and 'exchange_segment'.
        """
        selector = InstrumentSelector()
        instruments = []
        
        # Nifty Futures (current and next expiry)
        if self.include_futures:
            logger.info("Fetching Nifty Futures instruments...")
            nifty_futures = selector.get_nifty_futures(expiries=[0, 1])
            
            for inst in nifty_futures:
                instruments.append({
                    'security_id': inst['security_id'],
                    'exchange_segment': inst.get('exchange_segment', 'NSE_FNO')
                })
                logger.info(f"  Nifty Futures: {inst.get('display_name', inst['symbol'])} (ID: {inst['security_id']})")
            
            # Bank Nifty Futures
            logger.info("Fetching Bank Nifty Futures instruments...")
            banknifty_futures = selector.get_banknifty_futures(expiries=[0, 1])
            
            for inst in banknifty_futures:
                instruments.append({
                    'security_id': inst['security_id'],
                    'exchange_segment': inst.get('exchange_segment', 'NSE_FNO')
                })
                logger.info(f"  BankNifty Futures: {inst.get('display_name', inst['symbol'])} (ID: {inst['security_id']})")
        
        # Nifty Weekly Options (ATM ± 10 strike levels, next Thursday expiry)
        if self.include_nifty_options:
            logger.info("Fetching NIFTY Weekly Options instruments...")
            try:
                nifty_options = selector.get_nifty_weekly_options(
                    strike_offset_levels=10,  # ATM ± 10 levels (±1000 points)
                )
                
                for inst in nifty_options:
                    instruments.append({
                        'security_id': inst['security_id'],
                        'exchange_segment': inst.get('exchange_segment', 'NSE_FNO')
                    })
                
                logger.info(f"  Added {len(nifty_options)} NIFTY weekly option contracts")
            except Exception as e:
                logger.warning(f"Could not fetch NIFTY weekly options: {e}")
        
        # Bank Nifty Weekly Options (ATM ± 10 strike levels, next Thursday expiry)
        if self.include_banknifty_options:
            logger.info("Fetching BANKNIFTY Weekly Options instruments...")
            try:
                banknifty_options = selector.get_banknifty_weekly_options(
                    strike_offset_levels=10,  # ATM ± 10 levels (±1000 points)
                )
                
                for inst in banknifty_options:
                    instruments.append({
                        'security_id': inst['security_id'],
                        'exchange_segment': inst.get('exchange_segment', 'NSE_FNO')
                    })
                
                logger.info(f"  Added {len(banknifty_options)} BANKNIFTY weekly option contracts")
            except Exception as e:
                logger.warning(f"Could not fetch BANKNIFTY weekly options: {e}")
        
        # MCX Commodities (optional, can be run in parallel with spot feed)
        if self.include_commodities:
            logger.info("Fetching MCX Commodity Futures instruments...")
            commodity_futures = selector.get_major_commodity_futures(expiries=[0])
            
            for inst in commodity_futures:
                instruments.append({
                    'security_id': inst['security_id'],
                    'exchange_segment': inst.get('exchange_segment', 'MCX_COMM')
                })
                logger.info(f"  Commodity: {inst.get('display_name', inst['symbol'])} (ID: {inst['security_id']})")
        
        logger.info(f"Total FNO instruments to subscribe: {len(instruments)}")
        return instruments
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating FNO feed shutdown...")
            self._shutdown_event.set()
            self._running = False
            if self._feed_service:
                self._feed_service._running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _status_update_loop(self, instruments_count: int):
        """Background thread for updating Redis status."""
        while self._running:
            try:
                self._publish_status(True, instruments_count)
                time.sleep(2)
            except Exception as e:
                logger.debug(f"Error in status update: {e}")
                time.sleep(5)
    
    async def _run_async(self, instruments: List[Dict]):
        """Async main loop for FNO feed service."""
        mode_map = {
            FeedMode.TICKER: 'TICKER',
            FeedMode.QUOTE: 'QUOTE',
            FeedMode.FULL: 'FULL'
        }
        feed_type = mode_map.get(self.feed_mode, 'QUOTE')
        
        await self._feed_service.run(instruments, feed_type)
    
    def start(self):
        """Start the FNO feed publisher service."""
        logger.info("=" * 70)
        logger.info("Starting FNO (Futures & Options) Market Feed Publisher")
        logger.info("=" * 70)
        
        # Initialize Redis status reporting
        self._init_redis_status()
        
        # Check market hours
        if not self._is_market_hours():
            logger.warning("Outside market hours. Use --force to run anyway.")
            if not self.run_outside_market_hours:
                return
        
        # Validate configuration
        try:
            self._feed_config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Get instruments
        instruments = self._get_fno_instruments_to_subscribe()
        
        if not instruments:
            logger.error("No instruments to subscribe")
            self._publish_status(False, 0)
            return
        
        # Create and start feed service
        try:
            self._feed_service = DhanFeedService(config=self._feed_config)
            
            logger.info(f"\n[FEED CONFIG] Feed Service Configuration:")
            logger.info(f"  Feed Mode: {self.feed_mode.name}")
            logger.info(f"  Instruments: {len(instruments)}")
            logger.info(f"  Redis: {self._feed_config.REDIS_HOST}:{self._feed_config.REDIS_PORT}")
            logger.info(f"  Market Hours: {self.PRE_MARKET_START.strftime('%H:%M')} - {self.MARKET_CLOSE.strftime('%H:%M')}")
            logger.info("\n[WEBSOCKET] Starting WebSocket connection...")
            
            # Publish status
            self._publish_status(True, len(instruments))
            
            # Start status update thread
            status_thread = threading.Thread(
                target=self._status_update_loop,
                args=(len(instruments),),
                daemon=True
            )
            status_thread.start()
            
            # Run async event loop
            self._running = True
            asyncio.run(self._run_async(instruments))
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in FNO feed service: {e}", exc_info=True)
        finally:
            self._publish_status(False, 0)
            logger.info("FNO Feed Publisher stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FNO Market Feed Service - Futures & Options real-time data"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Run outside market hours (for testing)'
    )
    parser.add_argument(
        '--mode',
        choices=['TICKER', 'QUOTE', 'FULL'],
        default='QUOTE',
        help='Feed mode (default: QUOTE)'
    )
    parser.add_argument(
        '--no-futures',
        action='store_true',
        help='Skip Nifty/BankNifty futures'
    )
    parser.add_argument(
        '--no-nifty-options',
        action='store_true',
        help='Skip Nifty options'
    )
    parser.add_argument(
        '--no-banknifty-options',
        action='store_true',
        help='Skip Bank Nifty options'
    )
    parser.add_argument(
        '--no-commodities',
        action='store_true',
        help='Skip MCX commodity futures (included by default)'
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start launcher
    mode_map = {'TICKER': FeedMode.TICKER, 'QUOTE': FeedMode.QUOTE, 'FULL': FeedMode.FULL}
    
    launcher = FNOFeedLauncher(
        feed_mode=mode_map.get(args.mode, FeedMode.QUOTE),
        run_outside_market_hours=args.force,
        include_futures=not args.no_futures,
        include_nifty_options=not args.no_nifty_options,
        include_banknifty_options=not args.no_banknifty_options,
        include_commodities=not args.no_commodities
    )
    
    launcher.start()


if __name__ == '__main__':
    main()
