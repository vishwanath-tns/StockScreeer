"""
DUAL FEED SERVICE ARCHITECTURE
==============================

TWO INDEPENDENT DHAN WEBSOCKET CONNECTIONS:

1. SPOT MARKET FEED (market_feed/launcher.py)
   └─ Purpose: Real-time equity prices
   └─ Instruments:
      ├─ Nifty 50 stocks (48 symbols from NSE_EQ)
      ├─ Nifty Futures
      └─ Bank Nifty Futures
      └─ MCX Commodities (optional)
   └─ Status: RUNNING (do not stop)

2. FNO FEED (market_feed/fno_launcher.py) ← NEW
   └─ Purpose: Futures & Options real-time data
   └─ Instruments:
      ├─ Nifty Futures (Dec, Jan expiry)
      ├─ Bank Nifty Futures (Dec, Jan expiry)
      ├─ Nifty Options (ATM ± 2 strikes)
      ├─ Bank Nifty Options (ATM ± 2 strikes)
      └─ MCX Commodities (if enabled)


SHARED INFRASTRUCTURE
====================

Both services use:
✅ Same Dhan API credentials (DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
✅ Same Redis server (localhost:6379)
✅ Same Redis channels (dhan:quotes, dhan:ticks, dhan:depth)
✅ Same database (dhan_trading)
✅ Same InstrumentSelector logic

Separation:
✅ Different WebSocket connections (each has own socket)
✅ Different data tables:
   - Spot feed → dhan_quotes table
   - FNO feed → dhan_fno_quotes table (new)
   - Options feed → dhan_options_quotes table (new)
✅ Different subscribers/db_writers


ARCHITECTURE DETAILS
====================

SPOT MARKET FEED (Currently Running):
────────────────────────────────────
WebSocket #1 (Spot)
    ↓
DhanFeedService
    ↓
RedisPublisher (dhan:quotes channel)
    ↓ (subscribers)
├─ DBWriter → dhan_quotes table
├─ Volume Profile Chart
├─ Market Breadth Chart
├─ Dashboard
└─ Tick Chart


FNO FEED (New - Independent):
────────────────────────────
WebSocket #2 (FNO)
    ↓
DhanFeedService (same class, different instruments)
    ↓
RedisPublisher (dhan:quotes channel - same for multiplexing)
    ↓ (subscribers)
├─ FNO DBWriter → dhan_fno_quotes table
├─ Options DBWriter → dhan_options_quotes table
├─ FNO Dashboard (future)
└─ Options Greeks Calculator (future)


KEY ADVANTAGES
==============

1. INDEPENDENT OPERATION
   - Stopping FNO feed doesn't affect equity data collection
   - Stopping equity feed doesn't affect FNO data collection

2. FOCUSED SUBSCRIPTIONS
   - Equity feed optimized for spot trading
   - FNO feed optimized for derivatives
   - Separate tables = separate analysis pipelines

3. SCALABILITY
   - Can add more feeds later (Crypto, Forex, etc.)
   - Each with independent configuration
   - Shared Redis = efficient multiplexing

4. FLEXIBILITY
   - Use --no-futures to skip futures
   - Use --no-nifty-options to skip options
   - Use --include-commodities to add MCX


DATABASE SCHEMA (New Tables)
============================

dhan_fno_quotes table:
  - Same structure as dhan_quotes
  - Tracks Nifty/BankNifty futures
  - Fields: security_id, ltp, bid_price, ask_price, volume, etc.

dhan_options_quotes table:
  - Same structure as dhan_quotes
  - Tracks option Greeks data
  - Fields: security_id, ltp, bid_price, ask_price, open_interest, etc.

Table creation scripts:
  - dhan_trading/db_setup.py (update with new tables)


HOW TO RUN
==========

Terminal 1: SPOT MARKET FEED (Already running - don't stop!)
────────────────────────────────
Currently active. Keep running to preserve today's data.

Terminal 2: FNO FEED (NEW - Independent)
────────────────────────────────────────

# Basic: Futures + Options
python -m dhan_trading.market_feed.fno_launcher --force

# Futures only
python -m dhan_trading.market_feed.fno_launcher --force --no-nifty-options --no-banknifty-options

# Options only
python -m dhan_trading.market_feed.fno_launcher --force --no-futures

# With commodities
python -m dhan_trading.market_feed.fno_launcher --force --include-commodities

# With debug logging
python -m dhan_trading.market_feed.fno_launcher --force --debug

# Outside market hours (testing)
python -m dhan_trading.market_feed.fno_launcher --force --mode QUOTE


COMMAND-LINE OPTIONS
====================

--force
  Run outside market hours (default checks IST market hours)

--mode {TICKER,QUOTE,FULL}
  TICKER: LTP only (minimal bandwidth)
  QUOTE: Full trade data (recommended)
  FULL: Include market depth (requires more bandwidth)

--no-futures
  Skip Nifty and BankNifty futures

--no-nifty-options
  Skip Nifty options

--no-banknifty-options
  Skip Bank Nifty options

--include-commodities
  Include MCX commodities in FNO feed
  (by default, commodities in spot feed)

--debug
  Enable DEBUG level logging


MONITORING
==========

Check running processes:
  ps aux | grep fno_launcher
  ps aux | grep launcher.py

Monitor Redis publishing:
  redis-cli SUBSCRIBE dhan:quotes
  redis-cli XREAD STREAMS dhan:quotes:stream 0

Check database:
  SELECT COUNT(*) FROM dhan_fno_quotes;
  SELECT MAX(received_at) FROM dhan_fno_quotes;

View logs:
  tail -f /var/log/dhan_fno_feed.log


FUTURE ENHANCEMENTS
===================

1. Options Greeks Calculation
   - Add IV calculation from bid/ask spreads
   - Calculate Delta, Gamma, Theta, Vega

2. Options Visualizer
   - IV smile/skew charts
   - Greeks dashboard
   - Open interest analysis

3. Order Book Depth Visualizer
   - Show bid/ask levels
   - Volume concentration
   - DOM (Depth of Market)

4. FNO Dashboard
   - Live futures prices
   - Open interest tracking
   - IV term structure

5. Database Partitioning
   - Partition by date for large tables
   - Archive old data for historical analysis


TROUBLESHOOTING
===============

"Configuration error: Missing DHAN_CLIENT_ID"
  → Set environment variables in .env file

"Connection refused"
  → Ensure Redis is running on localhost:6379
  → Check: redis-cli ping

"No instruments to subscribe"
  → Check database has instruments
  → Verify InstrumentSelector queries

"Missing nifty_options method"
  → Method not yet implemented
  → Use --no-nifty-options for now
  → Implement in instrument_selector.py


FILES CREATED/MODIFIED
======================

NEW:
  dhan_trading/market_feed/fno_launcher.py
  dhan_trading/subscribers/fno_db_writer.py (next step)
  ARCHITECTURE_REVIEW.md (this file)

EXISTING (unchanged):
  dhan_trading/market_feed/launcher.py (spot feed - do NOT modify)
  dhan_trading/market_feed/feed_service.py (reused)
  dhan_trading/market_feed/redis_publisher.py (reused)
  dhan_trading/market_feed/instrument_selector.py (will extend)


NEXT STEPS
==========

1. ✅ Create fno_launcher.py (DONE)
2. TODO: Implement get_nifty_options() and get_banknifty_options() in InstrumentSelector
3. TODO: Create dhan_fno_quotes and dhan_options_quotes tables
4. TODO: Create fno_db_writer.py (separate subscriber for FNO data)
5. TODO: Create FNO visualizers
6. TODO: Create options Greeks calculator


TESTING
=======

Step 1: Verify spot feed is running
  - Check Market Breadth Chart window (should show live data)
  - Check DBWriter terminal (should show "Wrote X quotes" messages)

Step 2: Start FNO feed in new terminal
  python -m dhan_trading.market_feed.fno_launcher --force --debug

Step 3: Monitor FNO feed
  - Should show "Total FNO instruments to subscribe: N"
  - Should show "Loaded N Nifty futures, M options"
  - Should start receiving data messages

Step 4: Verify data in database
  - Check dhan_fno_quotes table (after creating it)
  - Verify row count increasing
  - Verify timestamps are recent
"""

print(__doc__)
