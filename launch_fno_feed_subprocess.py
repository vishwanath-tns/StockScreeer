#!/usr/bin/env python
"""
FNO Feed Launcher Subprocess Wrapper
=====================================
This wrapper ensures proper subprocess handling of the FNO feed launcher,
especially for Windows where asyncio can have issues in subprocesses.

Usage from Control Center:
    python launch_fno_feed_subprocess.py --force --debug
"""

import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to ensure it appears in Control Center logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point - wrap FNO launcher with proper subprocess handling."""
    try:
        from dhan_trading.market_feed.fno_launcher import FNOFeedLauncher, FeedMode
        import argparse
        
        # Parse arguments
        parser = argparse.ArgumentParser(description="FNO Feed Launcher Subprocess Wrapper")
        parser.add_argument('--force', action='store_true', help='Run outside market hours')
        parser.add_argument('--mode', choices=['TICKER', 'QUOTE', 'FULL'], default='QUOTE')
        parser.add_argument('--no-futures', action='store_true')
        parser.add_argument('--no-nifty-options', action='store_true')
        parser.add_argument('--no-banknifty-options', action='store_true')
        parser.add_argument('--no-commodities', action='store_true', help='Skip MCX commodities (included by default)')
        parser.add_argument('--debug', action='store_true')
        
        args = parser.parse_args()
        
        # Setup logging
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug(f"Arguments: {args}")
        
        # Create launcher
        mode_map = {'TICKER': FeedMode.TICKER, 'QUOTE': FeedMode.QUOTE, 'FULL': FeedMode.FULL}
        launcher = FNOFeedLauncher(
            feed_mode=mode_map.get(args.mode, FeedMode.QUOTE),
            run_outside_market_hours=args.force,
            include_futures=not args.no_futures,
            include_nifty_options=not args.no_nifty_options,
            include_banknifty_options=not args.no_banknifty_options,
            include_commodities=not args.no_commodities  # MCX included by default
        )
        
        logger.info("FNO Feed Launcher subprocess wrapper starting...")
        launcher.start()
        logger.info("FNO Feed Launcher subprocess wrapper completed")
        
    except Exception as e:
        logger.error(f"Error in FNO launcher subprocess: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
