# Dhan Trading System - Quick Visual Guide

## SERVICE LAYERS (Vertical Stack)

```
                         USER LAYER
                         ──────────
                    ┌─────────────────┐
                    │  Control Center │  ← Start/Stop all, Monitor health
                    │     (PyQt6)     │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐  ┌──────▼──────┐
    │   Scheduler │   │  Instrument │  │   Monitor   │
    │  (Auto on)  │   │   Display   │  │  Dashboard  │
    └─────────────┘   └─────────────┘  └─────────────┘


                      VISUALIZATION LAYER
                      ──────────────────
    ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
    │   Volume     │    Market    │     Tick     │   Volume     │    Quote     │
    │   Profile    │   Breadth    │    Chart     │  Prof Chart  │ Visualizer   │
    │  (PyQt6)     │   (PyQt6)    │   (PyQt6)    │   (PyQt6)    │  (Terminal)  │
    └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
           │              │             │             │             │
           └──────────────┼─────────────┴─────────────┴─────────────┘
                          │
                    ┌─────▼──────┐
                    │   Redis    │  ← In-memory message broker
                    │ Pub/Sub +  │    (dhan:quotes, dhan:ticks)
                    │  Streams   │
                    └─────┬──────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
    │                     │                     │
 ┌──▼───────────┐  ┌──────▼────────┐  ┌────────▼───┐
 │   Database   │  │  Feed Service │  │  Visualizer│
 │   Writer     │  │   (Publisher) │  │ (Subscriber│
 │ (Subscriber) │  │               │  │   Consumer)│
 └──┬───────────┘  └────────┬───────┘  └────────────┘
    │                       │
    │                   ┌───▼─────┐
    │                   │   Dhan   │
    │                   │ WebSocket│
    │                   │   API    │
    │                   └──────────┘
    │
 ┌──▼────────────────┐
 │   MySQL Database   │
 │  dhan_trading      │
 │                    │
 │ • dhan_quotes      │
 │ • dhan_ticks       │
 │ • dhan_depth       │
 │ • dhan_instruments │
 └────────────────────┘


                       DATA FLOW DIRECTION
                       ─────────────────

Dhan API (Market Data)
       │ (binary tick data, 100+ Hz)
       │
       ▼
Feed Service/Publisher
       │ (QuoteData object)
       │
       ├─────────────┬─────────────┬──────────────┐
       │             │             │              │
       ▼             ▼             ▼              ▼
    Redis Stream  Redis Pub/Sub   Monitor        (Ephemeral)
    (Persistent)  (Real-time)     Dashboard
       │             │             │
       ├─────────────┼─────────────┤
       │             │
       ▼             ▼
    DB Writer      Visualizers
    (Batch)        (Real-time UI)
       │             │
       ▼             ▼
    MySQL DB      PyQt6 Desktop
    (Storage)     (Charts)
```

---

## LAUNCH SEQUENCE (What happens when you click "Start All")

```
Time 0s:  ┌──────────────────┐
          │ User: "Start All"│
          └────────┬─────────┘
                   │
    0-2s: ┌────────▼──────────────────┐
          │ Feed Launcher Started     │
          │ • Connects to Dhan API    │
          │ • Subscribes to 128 inst. │
          │ • Begins publishing       │
          └────────┬──────────────────┘
                   │
    1-3s: ┌────────▼──────────────────┐
          │ Database Writer Started    │
          │ • Connects to MySQL        │
          │ • Subscribes to Redis      │
          │ • Begins batch writing     │
          └────────┬──────────────────┘
                   │
    2-4s: ┌────────▼──────────────────┐
          │ Visualizers (if selected)  │
          │ • Volume Profile UI ready  │
          │ • Market Breadth tracking  │
          │ • Tick Chart rendering     │
          │ • Quote display active     │
          └─────────────────────────────┘

    At 5s: SYSTEM READY ✓
           • 1000+ quotes flowing
           • Data writing to MySQL
           • Charts updating in real-time
```

---

## QUOTE JOURNEY (Tracing 1 quote)

```
Instrument: NIFTY DEC Fut
Time: 14:35:42.123

Step 1: Dhan Market (Source)
┌────────────────────────────┐
│ Dhan Exchange broadcasts   │
│ Quote: NIFTY DEC 25450.50  │
└────────────┬───────────────┘
             │ (binary WebSocket frame)
             │ ~0.5ms latency
             
Step 2: Feed Service (Parse)
┌────────────────────────────┐
│ Dhan Feed Service:         │
│ • Decompress binary        │
│ • Parse tick/quote/depth   │
│ • Create QuoteData object  │
│   sec_id: 49229            │
│   ltp: 25450.50            │
│   volume: 50000            │
│   timestamp: 14:35:42.123  │
└────────────┬───────────────┘
             │ (~1ms from source)
             │
Step 3: Redis Publisher
┌────────────────────────────┐
│ Publish to:                │
│ 1. Channel: "dhan:quotes"  │
│    (immediate, real-time)  │
│                            │
│ 2. Stream: "dhan:quotes:st"│
│    (persistent, queryable) │
└────────────┬───────────────┘
             │ (~1.5ms from source)
             │
       ┌─────┴──────────┬─────────────┬─────────────┐
       │                │             │             │
       ▼                ▼             ▼             ▼
  DB Writer          Vol Prof      Market       Quote
  Subscriber        Visualizer    Breadth       Visual
                                                 
Step 4A: DB Writer Path
┌────────────────────────────┐
│ Batch Queue:               │
│ • Collect 50 quotes        │
│ • Dedup (keep latest)      │
│ • Build INSERT statement   │
└────────────┬───────────────┘
             │ (wait max 1s)
             │
┌────────────▼───────────────┐
│ Write to MySQL:            │
│ INSERT dhan_quotes ...     │
│ ON DUPLICATE KEY UPDATE    │
└────────────┬───────────────┘
             │ (~2-3ms from source)
             ▼
        MySQL Storage
     (Available for analysis)

Step 4B: Visualizer Path (Real-time)
┌────────────────────────────┐
│ Visualizer receives quote  │
│ • Update profile bins      │
│ • Recalc POC/VA            │
│ • Trigger UI redraw        │
└────────────┬───────────────┘
             │ (~2-5ms from source)
             ▼
        PyQt6 Chart Update
     (User sees price change)

TOTAL LATENCY: Dhan → Screen: ~5-10ms
               Dhan → Database: ~3-4ms
```

---

## RESOURCE USAGE (Peak Market Hours)

```
Component              Memory      CPU      Network
─────────────────────────────────────────────────
Feed Launcher          120 MB      8%       2 Mbps (in)
Database Writer        80 MB       3%       200 Kbps
Redis                  150 MB      5%       1 Mbps
Volume Profile UI      100 MB      12%      500 Kbps
Market Breadth UI      80 MB       8%       300 Kbps
Tick Chart UI          100 MB      10%      400 Kbps
Volume Prof Chart UI   90 MB       9%       350 Kbps
Quote Visualizer       40 MB       2%       100 Kbps
Control Center         50 MB       3%       50 Kbps
─────────────────────────────────────────────────
TOTAL (All running)    ~800 MB     60%      5 Mbps

Typical config (Feed + DB + 2 Visualizers):
Total                  ~400 MB     35%      3 Mbps
```

---

## ERROR RECOVERY TIMELINE

```
Scenario: Redis disconnects

Time: 14:35:42 - Redis healthy
                 Quote flow: 1000/sec

Time: 14:35:43 - Redis connection lost!
                 ├─ DB Writer: ERROR buffering quotes
                 ├─ Visualizers: WARNING no new data
                 └─ Feed Launcher: ERROR can't publish

Time: 14:35:44 - Reconnect attempt 1
                 └─ All services retry...

Time: 14:35:46 - Reconnect attempt 2 (backoff)
                 └─ All services retry...

Time: 14:36:00 - Redis comes back online
                 ├─ Feed Launcher: RESUME publishing
                 ├─ DB Writer: FLUSH buffered quotes (500+)
                 ├─ Visualizers: RESUME real-time updates
                 └─ Quote flow: 1000/sec (normal)

Total downtime: ~20 seconds
Data loss: NONE (queued in memory)
Recovery: Automatic, no user intervention
```

---

## QUICK COMMANDS

```bash
# Start Feed Launcher
python launch_fno_feed.py --force

# Start Feed + Commodities
python launch_fno_feed.py --force --include-commodities

# Start Database Writer
python -m dhan_trading.subscribers.fno_db_writer

# Start Control Center (All-in-one)
python launch_dhan_control_center.py

# Start individual visualizers
python -m dhan_trading.visualizers.volume_profile
python -m dhan_trading.visualizers.market_breadth
python -m dhan_trading.visualizers.tick_chart
python -m dhan_trading.visualizers.volume_profile_chart
python -m dhan_trading.visualizers.quote_visualizer

# Show subscribed instruments
python display_fno_instruments.py

# Test all services (validation)
python -m dhan_trading.test_all_services

# Monitor in real-time
watch -n 1 'python -c "from dhan_trading.db_setup import get_engine, DHAN_DB_NAME; 
                        from sqlalchemy import text; 
                        e = get_engine(DHAN_DB_NAME); 
                        with e.connect() as c: 
                            r = c.execute(text(\"SELECT COUNT(*) FROM dhan_quotes\")); 
                            print(f\"Quotes in DB: {r.fetchone()[0]}\")"'
```

---

## DECISION TREE: Which Visualizer to Use?

```
Want to see...
│
├─ Volume distribution at price levels?
│  └─ USE: Volume Profile
│     (Shows POC, Value Area, Buy/Sell ratio)
│
├─ Market sentiment (advances vs declines)?
│  └─ USE: Market Breadth
│     (Nifty 50 stock performance tracking)
│
├─ Price movement by ticks (not time)?
│  └─ USE: Tick Chart
│     (Groups every 50 ticks into 1 candle)
│
├─ How volume profile evolved over time?
│  └─ USE: Volume Profile Chart
│     (5-min profiles from 9:15 AM to now)
│
├─ Quick quotes without heavy UI?
│  └─ USE: Quote Visualizer
│     (Terminal-based, lightweight)
│
└─ Control everything at once?
   └─ USE: Control Center Dashboard
      (Launch/monitor all 11 services)
```

---

## Files to Know

```
Core Architecture:
  📁 dhan_trading/config.py              ← Central configuration
  📁 dhan_trading/db_setup.py            ← Database connection pool
  📁 dhan_trading/market_feed/
     ├─ launcher.py                      ← Feed publisher
     ├─ feed_service.py                  ← Dhan API handler
     ├─ redis_publisher.py               ← Redis publisher
     └─ instrument_selector.py           ← Instrument management

Data Storage:
  📁 dhan_trading/fno_schema.py          ← Database schema
  📁 dhan_trading/market_feed/tick_models.py ← Table definitions

Subscribers:
  📁 dhan_trading/subscribers/db_writer.py   ← DB writer
  📁 dhan_trading/subscribers/fno_db_writer.py ← FNO-specific writer

Visualizers:
  📁 dhan_trading/visualizers/
     ├─ volume_profile.py                ← POC/Value Area chart
     ├─ market_breadth.py                ← Advances/Declines
     ├─ tick_chart.py                    ← Tick-based OHLC
     ├─ volume_profile_chart.py          ← Historical profiles
     └─ quote_visualizer.py              ← Terminal quotes

Control:
  📁 dhan_trading/dashboard/
     ├─ dhan_control_center.py           ← Main hub
     ├─ fno_services_monitor.py          ← Services monitor
     └─ service_manager.py               ← Service lifecycle

Scheduling:
  📁 dhan_trading/scheduler/market_scheduler.py ← Auto-start/stop

Launchers:
  📁 launch_dhan_control_center.py       ← Start Control Center
  📁 launch_fno_feed.py                  ← Start Feed
  📁 launch_market_scheduler.py           ← Start Scheduler
  📁 display_fno_instruments.py          ← Show instruments
```

