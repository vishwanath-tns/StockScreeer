#!/usr/bin/env python
"""
Launch FNO Market Feed Service
==============================
Wrapper script to start the FNO (Futures & Options) feed service.

Usage:
    python launch_fno_feed.py
    python launch_fno_feed.py --force
    python launch_fno_feed.py --mode QUOTE
    python launch_fno_feed.py --no-nifty-options --no-banknifty-options

Options:
    --force                    Run outside market hours
    --mode {TICKER,QUOTE,FULL} Feed mode (default: QUOTE)
    --no-futures              Skip Nifty/BankNifty futures
    --no-nifty-options        Skip Nifty options
    --no-banknifty-options    Skip BankNifty options
    --no-commodities          Skip MCX commodity futures (included by default)
    --debug                   Enable debug logging

Instruments Subscribed By Default:
    - NIFTY Futures (current + next expiry)
    - BANKNIFTY Futures (current + next expiry)  
    - NIFTY Weekly Options (ATM ± 10 strikes)
    - BANKNIFTY Weekly Options (ATM ± 10 strikes)
    - MCX Commodities (GOLD, SILVER, CRUDEOIL, NATURALGAS, COPPER - nearest expiry)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dhan_trading.market_feed.fno_launcher import main

if __name__ == '__main__':
    main()
