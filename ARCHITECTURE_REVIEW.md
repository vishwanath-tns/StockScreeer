"""
ARCHITECTURE REVIEW: Dhan Market Feed Service
==============================================

CURRENT ARCHITECTURE (market_feed service)
==========================================

1. LAUNCHER (launcher.py) - Entry Point
   ├─ MarketFeedLauncher class
   ├─ Market hours checking (9:00 AM - 3:35 PM IST)
   ├─ Instrument selection via InstrumentSelector
   └─ Signal handling for graceful shutdown

2. FEED SERVICE (feed_service.py) - Core WebSocket Handler
   ├─ DhanFeedService class
   ├─ Connects to Dhan WebSocket (ws://connect.dhan.co/feeds)
   ├─ Subscribes to instruments (NSE_EQ, NSE_FNO, MCX_COMM)
   ├─ Parses binary packets:
   │  ├─ Ticker packets (LTP only)
   │  ├─ Quote packets (full trade data)
   │  └─ Full packets (with market depth)
   ├─ Publishes to Redis (Pub/Sub + Streams)
   └─ Handles reconnection logic

3. INSTRUMENT SELECTOR (instrument_selector.py)
   ├─ Queries dhan_instruments table
   ├─ Provides methods:
   │  ├─ get_nifty50_stocks()
   │  ├─ get_nifty_futures(expiries=[0,1])
   │  ├─ get_banknifty_futures(expiries=[0,1])
   │  └─ get_major_commodity_futures(expiries=[0])
   └─ Returns list of instruments with security_id + exchange_segment

4. REDIS PUBLISHER (redis_publisher.py)
   ├─ RedisPublisher class
   ├─ Pub/Sub channels:
   │  ├─ dhan:ticks (ticker data)
   │  ├─ dhan:quotes (quote data)
   │  └─ dhan:depth (market depth data)
   ├─ Streams:
   │  ├─ dhan:ticks:stream
   │  ├─ dhan:quotes:stream
   │  └─ dhan:depth:stream
   └─ Data classes:
      ├─ TickData
      ├─ QuoteData
      └─ DepthData

5. FEED CONFIG (feed_config.py)
   ├─ FeedConfig class (loads from env vars)
   ├─ Exchange segments (NSE_EQ, NSE_FNO, MCX_COMM, BSE_EQ, etc.)
   ├─ Feed modes (TICKER, QUOTE, FULL)
   ├─ Request codes (subscription handshake)
   └─ Response codes (packet types)

6. REDIS SUBSCRIBER (redis_subscriber.py)
   ├─ RedisSubscriber base class
   ├─ Methods:
   │  ├─ on_tick(tick: TickData)
   │  ├─ on_quote(quote: QuoteData)
   │  └─ on_depth(depth: DepthData)
   └─ Subclasses: DatabaseWriterSubscriber, VisualizerSubscriber, etc.

7. DATABASE SUBSCRIBER (db_writer.py)
   ├─ DatabaseWriterSubscriber (extends RedisSubscriber)
   ├─ Writes quotes to dhan_quotes table
   ├─ Batch writes with configurable:
   │  ├─ batch_size (default 50)
   │  ├─ flush_interval (default 1.0s)
   └─ Background thread for periodic flush

DATA FLOW
=========
Dhan WebSocket → DhanFeedService → RedisPublisher → Redis
                                                      ├─ Pub/Sub channels
                                                      └─ Streams
                                                         │
                                                         ├→ DBWriter (dhan_quotes table)
                                                         ├→ Visualizers (UI)
                                                         └→ Alert Engine


KEY DESIGN PATTERNS
===================
1. Publisher-Subscriber decoupling
   - Market feed publishes only
   - Separate services consume via Redis
   - Multiple consumers can work independently

2. Signal handling for graceful shutdown
   - SIGINT/SIGTERM captured
   - Running flag to stop loops
   - Proper cleanup before exit

3. Batch writes for DB efficiency
   - Buffer quotes in memory
   - Periodic flush to DB
   - Lock-based thread safety

4. Reconnection logic
   - WebSocket reconnects on failure
   - Exponential backoff
   - Connection status monitoring

5. Configuration via environment variables
   - DHAN_CLIENT_ID
   - DHAN_ACCESS_TOKEN
   - REDIS_HOST, REDIS_PORT
   - MySQL credentials

6. Logging and monitoring
   - Structured logging with timestamps
   - Instrument count tracking
   - Quote/tick count monitoring


CURRENT SUBSCRIPTION LIST
=========================
✅ Nifty 50 stocks (48 symbols from NSE_EQ)
✅ Nifty Futures (current + next expiry from NSE_FNO)
✅ Bank Nifty Futures (current + next expiry from NSE_FNO)
✅ MCX Commodities (GOLD, SILVER, CRUDE OIL, NATGAS, COPPER)


FILES INVOLVED
==============
dhan_trading/market_feed/
├─ __init__.py
├─ feed_config.py
├─ feed_service.py
├─ instrument_selector.py
├─ launcher.py
├─ redis_publisher.py
├─ redis_queue.py
├─ redis_subscriber.py
├─ tick_models.py
└─ db_writer.py (in subscribers/)

dhan_trading/subscribers/
└─ db_writer.py

dhan_trading/visualizers/
├─ market_breadth.py
├─ market_breadth_chart.py
├─ volume_profile.py
├─ volume_profile_chart.py
└─ tick_chart.py
"""

print(__doc__)
