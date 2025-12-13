# Dhan Trading System - Architecture & Data Flow

## System Overview

The Dhan trading system follows a **loosely-coupled, event-driven architecture** with:
- **1 Publisher** (Market Feed Service) → publishes to Redis
- **6 Subscribers** (DB Writer, Visualizers, Alerts) → consume from Redis
- **Centralized Control** (Control Center Dashboard)

---

## 1. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DHAN CONTROL CENTER (PyQt5)                           │
│  Central hub to launch/monitor all services                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 11 Services: Start/Stop All, Monitor Health, View Logs, Config      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────────────────┐
         │                                                      │
         ▼                                                      ▼
    ┌─────────────────────┐                           ┌──────────────────┐
    │  PUBLISHER LAYER    │                           │  CONTROL SERVICES│
    └─────────────────────┘                           └──────────────────┘
         │                                                    │
         ├─ Market Feed Launcher                             ├─ Market Scheduler
         │  (Dhan WebSocket → Redis)                         │  (Auto-start/stop)
         │                                                    │
         ├─ FNO Feed Launcher                                └─ Instrument Display
         │  (128 instruments)                                   (Show subscribed)
         │
         └─ FNO+MCX Feed
            (+ Commodities)
            
            
         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    REDIS (Message Broker)                    │
    ├─────────────────────────────────────────────────────────────┤
    │ Streams:                    │ Pub/Sub Channels:             │
    │ • dhan:quotes:stream        │ • dhan:quotes                 │
    │ • dhan:ticks:stream         │ • dhan:ticks                  │
    │ • dhan:depth:stream         │ • dhan:depth                  │
    │ • dhan:fno_quotes:stream    │ • dhan:alerts                 │
    └─────────────────────────────────────────────────────────────┘
         │
         └──────────────────┬──────────────────┬──────────────────┐
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ DB WRITER    │   │ VISUALIZERS  │   │ VISUALIZERS  │   │ VISUALIZERS  │
    │ (MySQL)      │   │ (PyQt5)      │   │ (PyQt5)      │   │ (Terminal)   │
    └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
         │                  │                  │                  │
         ├─ dhan_quotes     ├─ Volume Profile  ├─ Tick Chart      └─ Quote
         ├─ dhan_ticks      ├─ Market Breadth  └─ Vol Prof Chart    Visualizer
         └─ dhan_depth      └─ (Real-time UI)     (Historical)


    ┌─────────────────────────────────────┐
    │      PERSISTENT STORAGE (MySQL)      │
    ├─────────────────────────────────────┤
    │  Database: dhan_trading             │
    │                                      │
    │  Tables:                            │
    │  • dhan_quotes (latest)             │
    │  • dhan_ticks (historical)          │
    │  • dhan_depth (order book)          │
    │  • dhan_instruments (reference)     │
    │  • dhan_options_greeks (analytics)  │
    └─────────────────────────────────────┘
```

---

## 2. SERVICE HIERARCHY

### **TIER 1: PUBLISHER SERVICES** (No storage, pure real-time)
```
Market Feed Services
│
├─ Dhan WebSocket Connection
│  ├─ Connects to Dhan API
│  ├─ Subscribes to instruments
│  └─ Receives binary tick data
│
├─ Feed Service (Dhan API Handler)
│  ├─ Decompresses binary data
│  ├─ Parses tick/quote/depth
│  └─ Creates QuoteData/TickData objects
│
├─ Redis Publisher
│  ├─ Publishes to streams (persistence)
│  ├─ Publishes to channels (real-time)
│  └─ Handles reconnection
│
└─ Instrument Selector
   ├─ Loads from MySQL database
   ├─ Filters by criteria (NIFTY, BankNifty, Options)
   └─ Manages subscriptions
```

### **TIER 2: SUBSCRIBER SERVICES** (Consume from Redis)

#### **2A. Database Writer** (Persistent Storage)
```
Database Writer Subscriber
│
├─ Redis Subscriber
│  ├─ Listens to dhan:quotes channel
│  ├─ Listens to dhan:ticks channel
│  └─ Listens to dhan:depth channel
│
├─ Batch Processor
│  ├─ Collects quotes
│  ├─ Groups by sec_id
│  └─ Deduplicates (keep latest)
│
└─ Database Writer
   ├─ Connects to dhan_trading DB
   ├─ Writes to dhan_quotes (UPSERT)
   ├─ Writes to dhan_ticks (INSERT)
   └─ Writes to dhan_depth (UPSERT)
```

#### **2B. Visualizers** (Real-time UI Analysis)
```
Visualizer Services (5 types)
│
├─ Volume Profile
│  ├─ Loads historical data from DB
│  ├─ Listens to real-time quotes
│  ├─ Builds volume bins
│  ├─ Calculates POC, Value Area
│  └─ Renders PyQt5 UI
│
├─ Market Breadth
│  ├─ Filters Nifty 50 stocks
│  ├─ Tracks advances/declines
│  ├─ Calculates breadth indicators
│  └─ Charts in real-time
│
├─ Tick Chart
│  ├─ Loads historical ticks from DB
│  ├─ Groups by tick count (10/25/50/100/200)
│  ├─ Builds OHLC bars
│  └─ Renders candlestick chart
│
├─ Volume Profile Chart
│  ├─ Loads 5-min profiles
│  ├─ Shows profile evolution
│  └─ Displays VAH/VAL/POC evolution
│
└─ Quote Visualizer (Terminal)
   ├─ Lightweight (no PyQt6)
   ├─ Shows live quotes in terminal
   └─ Low resource usage
```

### **TIER 3: CONTROL SERVICES** (Management & Automation)
```
Control Services
│
├─ Market Scheduler
│  ├─ Monitors market hours
│  ├─ Auto-starts feed at 8:55 AM IST
│  ├─ Auto-stops feed at 12:00 AM IST
│  └─ Holidays detection
│
├─ Instrument Display
│  ├─ Shows all subscribed instruments
│  ├─ Displays security IDs
│  ├─ Shows instrument details
│  └─ Terminal-based output
│
└─ Control Center Dashboard
   ├─ PyQt5 main window
   ├─ Starts/stops all services
   ├─ Monitors resource usage
   ├─ Shows service logs
   └─ Real-time quotes display
```

---

## 3. DATA FLOW DIAGRAM

### **Flow 1: Real-time Quote Flow** (Fastest path ~1-5ms latency)
```
┌────────────────────────────────────┐
│   Dhan Market Data (WebSocket)     │
│   Binary tick at 100+ Hz           │
└────────────────────────────────────┘
         │ (FNO Feed Launcher)
         ▼
┌────────────────────────────────────┐
│   Feed Service                      │
│   • Decompress binary              │
│   • Parse tick/quote/depth         │
│   • Create QuoteData object        │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│   Redis Publisher                   │
│   1. Publish to: dhan:quotes       │ ─┐ (Channel - Real-time)
│   2. Append to: dhan:quotes:stream │  │ (Stream - Persistence)
└────────────────────────────────────┘  │
         │                              │
         ├──────────────────────────────┼─────────────────┐
         │                              │                 │
         ▼                              ▼                 ▼
    ┌──────────────┐              ┌──────────────┐  ┌──────────────┐
    │ DB Writer    │              │ Visualizers  │  │ Visualizers  │
    │ (Subscribe   │              │ (Subscribe   │  │ (Subscribe   │
    │ to channel)  │              │ to channel)  │  │ to stream)   │
    │              │              │              │  │              │
    │ Batch writes │              │ Live updates │  │ Historical   │
    │ to MySQL     │              │ PyQt5 UI     │  │ loads from DB│
    └──────────────┘              └──────────────┘  └──────────────┘
         │                              │                  │
         ▼                              ▼                  ▼
    MySQL DB                   PyQt6 Desktop          PyQt6 Desktop
    (dhan_quotes)              (Real-time chart)      (Historical analysis)
    
    
Latency: Dhan → Redis: ~1ms
         Redis → Subscribers: ~2ms
         DB Write: ~3ms
         UI Update: ~5ms
```

### **Flow 2: Historical Data Load** (Cold start)
```
┌────────────────────────────────────┐
│   Visualizer Start                  │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│   Connect to dhan_trading DB        │
└────────────────────────────────────┘
         │
         ├─ Query dhan_quotes          ┐
         │  WHERE trade_date = today   │ If today is trading day
         │                             │
         ├─ Query dhan_ticks          │
         │  WHERE timestamp >= 9:15 AM│
         │                             ├─ Load into memory
         ├─ Query dhan_depth           │ (10,000-50,000 records)
         │  WHERE timestamp >= 9:15 AM │
         │                             │
         └─ Aggregate/Group            │
            Calculate statistics      ─┘
         │
         ▼
┌────────────────────────────────────┐
│   Build In-Memory Data Structures   │
│   • VolumeProfileData               │
│   • OHLC bars                       │
│   • Breadth counters                │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│   Render Initial Chart              │
│   (PyQt6 painting)                  │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│   Start Real-time Subscriber        │
│   (Listen to Redis for new quotes)  │
└────────────────────────────────────┘
         │
         ├─ Update with live data
         ├─ Recalculate POC/VA
         ├─ Redraw chart
         └─ Repeat every quote (~100Hz)

Load Time: ~500ms - 2s depending on data volume
          (300MB/day of quotes → 50k records)
```

### **Flow 3: Database Persistence** (Batch writes)
```
Redis Stream (dhan:quotes:stream)
├─ Entry 1: Quote for sec_id=49229 LTP=25450
├─ Entry 2: Quote for sec_id=49543 LTP=51200
├─ Entry 3: Quote for sec_id=49229 LTP=25451
├─ Entry 4: Quote for sec_id=49543 LTP=51201
└─ ...
         │
         ▼
┌────────────────────────────────────┐
│   DB Writer Subscriber              │
│   Batch Window: 50 quotes or 1s     │
│   whichever comes first             │
└────────────────────────────────────┘
         │
         ├─ Dedup: Keep latest per sec_id
         │         (49229: LTP=25451, 49543: LTP=51201)
         │
         ▼
┌────────────────────────────────────┐
│   Build SQL:                        │
│   INSERT INTO dhan_quotes           │
│   (sec_id, ltp, timestamp, ...)     │
│   VALUES (...), (...), (...)        │
│   ON DUPLICATE KEY UPDATE           │
│   ltp=VALUES(ltp), ...              │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│   Execute batch INSERT/UPDATE       │
│   • 50 records per batch            │
│   • Connection pooling              │
│   • Upsert logic (no duplicates)    │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│   MySQL dhan_trading.dhan_quotes    │
│   • sec_id (Primary key)            │
│   • ltp, ltq, volume, oi            │
│   • timestamp (latest quote time)   │
└────────────────────────────────────┘

Write Frequency: Every 1s (worst case)
                 Every 100ms (typical)
Throughput: 50-100 quotes/batch
            500-1000 quotes/sec sustained
```

### **Flow 4: Control Center Orchestration** (Service management)
```
┌────────────────────────────────────┐
│   Control Center GUI (PyQt6)        │
│   User clicks "Start All"           │
└────────────────────────────────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
    ┌──────────────┐                  ┌──────────────┐
    │ Start Feed   │                  │ Start Writer │
    │ Launcher     │                  │ & Monitors   │
    └──────────────┘                  └──────────────┘
         │                                     │
         ├─ Launch:                            ├─ Launch:
         │ python -m dhan_trading.             │ python -m dhan_trading.
         │   market_feed.launcher              │   subscribers.db_writer
         │                                     │
         └─ Monitor health:                    └─ Monitor health:
           • Redis publishing                 • MySQL connection
           • Dhan API connection              • Batch write frequency
           • Quote rate                       • Error tracking
         
    
    ┌────────────────────────────────────────┐
    │   Launch Visualizers (on demand)        │
    │   • Volume Profile                      │
    │   • Market Breadth                      │
    │   • Tick Chart                          │
    │   • Volume Profile Chart                │
    │   • Quote Visualizer                    │
    └────────────────────────────────────────┘
         │
         └─ Each visualizer:
            • Loads instruments
            • Connects to Redis
            • Loads historical data
            • Renders UI
            • Starts real-time updates
            
            
    ┌────────────────────────────────────────┐
    │   Service Health Monitoring              │
    │   Refresh every 1-2 seconds              │
    │   Track:                                │
    │   • Process status (running/stopped)    │
    │   • CPU usage                           │
    │   • Memory usage                        │
    │   • Error logs                          │
    │   • Data flowing (quote count)          │
    └────────────────────────────────────────┘
```

---

## 4. COMPONENT INTERACTION MATRIX

```
                    | Feed  | DB    | Volume | Market | Tick  | Chart | Quote | Ctrl  | Sched
                    | Launcher| Writer| Prof  | Breadth| Chart | Prof  | Vis   | Ctr   | Sched
────────────────────┼───────┼───────┼────────┼────────┼───────┼───────┼───────┼───────┼─────
Dhan API            │   ✓   │       │        │        │       │       │       │       │
Redis Pub/Sub       │   ✓   │   ✓   │   ✓    │   ✓    │   ✓   │   ✓   │   ✓   │       │
Redis Streams       │   ✓   │   ✓   │   ✓    │   ✓    │   ✓   │   ✓   │   ✓   │       │
MySQL Database      │       │   ✓   │   ✓    │   ✓    │   ✓   │   ✓   │       │       │
Instruments Table   │   ✓   │       │   ✓    │   ✓    │   ✓   │   ✓   │       │       │
Control Center      │   ✓   │   ✓   │   ✓    │   ✓    │   ✓   │   ✓   │   ✓   │       │
Market Scheduler    │   ✓   │   ✓   │        │        │       │       │       │       │
Instrument Display  │   ✓   │       │        │        │       │       │       │       │
────────────────────┴───────┴───────┴────────┴────────┴───────┴───────┴───────┴───────┴─────

Legend:
✓ = Directly interacts with component
(blank) = No direct interaction
```

---

## 5. DEPLOYMENT STARTUP SEQUENCE

```
Step 1: Initialize
┌───────────────────────────────────────┐
│ • Create dhan_trading database        │
│ • Create tables (dhan_quotes, etc.)   │
│ • Create Redis connection             │
│ • Load instruments into memory        │
└───────────────────────────────────────┘
         │
         ▼
Step 2: Start Market Feed (Terminal 1)
┌───────────────────────────────────────┐
│ $ python launch_fno_feed.py --force   │
│ OR                                    │
│ $ python -m dhan_trading.market_feed  │
│   .launcher --force --include-commodities
│                                       │
│ Output:                               │
│ ✓ Connected to Dhan WebSocket         │
│ ✓ Subscribed to 128 instruments       │
│ ✓ Publishing to Redis                 │
│ ✓ Quote rate: 1000+/sec               │
└───────────────────────────────────────┘
         │ (Market data flowing → Redis)
         │
         ▼
Step 3: Start Database Writer (Terminal 2)
┌───────────────────────────────────────┐
│ $ python -m dhan_trading.subscribers   │
│   .fno_db_writer                      │
│                                       │
│ Output:                               │
│ ✓ Connected to dhan_trading DB        │
│ ✓ Subscribed to dhan:quotes channel   │
│ ✓ Batch writing: 50 quotes/s          │
│ ✓ Upserting to dhan_quotes table      │
└───────────────────────────────────────┘
         │ (Data flowing → MySQL)
         │
         ▼
Step 4: Start Visualizers (Terminal 3+)
┌───────────────────────────────────────┐
│ $ python -m dhan_trading.visualizers   │
│   .volume_profile                     │
│ $ python -m dhan_trading.visualizers   │
│   .market_breadth                     │
│ ... (any/all visualizers)             │
│                                       │
│ Each visualizer:                      │
│ • Loads historical data               │
│ • Connects to Redis                   │
│ • Renders PyQt6 UI                    │
│ • Updates on new quotes               │
└───────────────────────────────────────┘
         │
         ▼
Step 5: (Optional) Control Center Dashboard
┌───────────────────────────────────────┐
│ $ python launch_dhan_control_center.py│
│                                       │
│ Unified hub:                          │
│ • Start/stop all services             │
│ • Monitor health                      │
│ • View logs                           │
│ • Auto-arrange services               │
└───────────────────────────────────────┘

Timeline:
• Feed Launcher: Ready in ~2s
• DB Writer: Ready in ~1s (after Feed)
• Visualizers: Ready in ~500ms-2s each
• Control Center: Ready in ~3s

Total startup time: ~5-10 seconds for full system
```

---

## 6. DATA VOLUME METRICS

```
Throughput (at peak market hours):
─────────────────────────────────
Dhan Feed Launcher:
  • 128 instruments subscribed
  • 100+ quotes/second (average)
  • 10KB per quote (with depth data)
  • Total: ~1 MB/second raw data
  
Redis:
  • Stream append rate: 100+ entries/sec
  • Channel publish rate: 100+ subscribers/sec
  • Memory footprint: ~50-100 MB/hour of trading

MySQL (dhan_trading):
  • Daily volume: 30-50M quotes/day
  • Table size: ~100 GB/year
  • Write rate: 500-1000 inserts/sec
  • Query response: <100ms for daily data
  
Visualizers (per instance):
  • Memory: 50-150 MB (depends on instrument count)
  • CPU: 5-15% (light processing)
  • Historical data load: 500ms-2s per startup
  
Control Center Dashboard:
  • Memory: 30-50 MB
  • CPU: 2-5% (monitoring only)
  • Update frequency: 1-2 seconds
```

---

## 7. FAILURE HANDLING & RECOVERY

```
Failure Scenarios & Recovery:

1. Redis Disconnection
   Feed Launcher:
   ├─ Detects connection loss
   ├─ Logs error
   ├─ Reconnects automatically (exponential backoff)
   └─ Resumes publishing on reconnect
   
   DB Writer:
   ├─ Queues batches in memory
   ├─ Retries on reconnect
   └─ Persists state to avoid data loss

2. MySQL Connection Loss
   DB Writer:
   ├─ Catches exception
   ├─ Logs error
   ├─ Keeps quotes in memory buffer
   ├─ Reconnects on interval
   └─ Catches up on reconnect
   
   Visualizers:
   ├─ Display "DB offline" message
   ├─ Continue with Redis live data
   ├─ Retry DB load on interval
   └─ Historical data becomes unavailable

3. Dhan WebSocket Disconnection
   Feed Launcher:
   ├─ Detects socket close
   ├─ Logs error with reason
   ├─ Attempts reconnect (with backoff)
   ├─ Resubscribes to instruments
   └─ Resumes publishing
   
   System Impact:
   ├─ Quote flow stops briefly
   ├─ Visualizers show "no new data"
   ├─ DB writer processes stale data
   └─ Auto-recover within 30-60s

4. Control Center Crash
   Other Services:
   ├─ Continue running unaffected
   ├─ Quotes flow to Redis
   ├─ Data written to MySQL
   └─ Visualizers remain functional
   
   Recovery:
   └─ Restart Control Center
      (Data loss: none, services uninterrupted)
```

---

## 8. CONFIGURATION & ENVIRONMENT

```
Key Configuration Files:
─────────────────────────

.env (Environment Variables):
  DHAN_CLIENT_ID=xxxxx
  DHAN_ACCESS_TOKEN=xxxxx
  MYSQL_HOST=localhost
  MYSQL_PORT=3306
  MYSQL_USER=root
  MYSQL_PASSWORD=Ganesh@@2283@@
  DHAN_DB_NAME=dhan_trading
  DHAN_DB_NAME=dhan_trading

dhan_trading/config.py (Python Config):
  DHAN_DB_HOST = 'localhost'
  DHAN_DB_PORT = 3306
  DHAN_DB_USER = 'root'
  DHAN_DB_PASSWORD = 'Ganesh@@2283@@'
  DHAN_DB_NAME = 'dhan_trading'

dhan_trading/market_feed/feed_config.py:
  FeedMode.QUOTE / TICK / DEPTH
  ExchangeSegment (NSE_EQ, NSE_FNO, MCX_COMM)
  Batch size, flush interval, reconnect timeout

Instrument Selection:
  • 2 NIFTY Futures (Current + Next month)
  • 2 BANKNIFTY Futures (Current + Next month)
  • 82 NIFTY Weekly Options (Dec 16, ATM ±10 strikes)
  • 42 BANKNIFTY Options (Nearest Tuesday expiry)
  • (Optional) Commodities: Gold, Crude, Silver, NatGas
```

---

## 9. MONITORING & OBSERVABILITY

```
Control Center Dashboard Metrics:
──────────────────────────────────

Service Status Tab:
├─ Feed Launcher: Running/Stopped, 1000 quotes/sec
├─ DB Writer: Running/Stopped, 50 quotes/batch, 20 batches/sec
├─ Volume Profile: Running/Stopped, 250 samples cached
├─ Market Breadth: Running/Stopped, 50 stocks tracked
├─ Tick Chart: Running/Stopped, 200 ticks processed
├─ Volume Prof Chart: Running/Stopped, 30 bins calculated
├─ Quote Visualizer: Running/Stopped, 128 quotes displayed
├─ Market Scheduler: Running/Stopped, Auto-start in 45min
└─ Instrument Display: Running/Stopped, 128 instruments

Real-time Monitor Tab:
├─ Redis Stream Length: dhan:quotes:stream = 5,000 entries
├─ Publish Rate: 1050 quotes/sec
├─ Subscribe Rate: 950 subscribers receiving
├─ Memory Usage: Redis 85 MB, MySQL conn pool 15 MB
└─ Latency: Dhan→Redis 1ms, Redis→DB 2ms, Total 3ms

Database Tab:
├─ Connected to: dhan_trading (1 connection)
├─ dhan_quotes Table: 1.2M rows, 150 MB
├─ Latest Quote: 2025-12-12 14:55:23 (fresh)
├─ Instruments Loaded: 128 active
└─ Last Error: None

System Health Tab:
├─ Market Hours: Open (9:15 AM - 3:35 PM)
├─ All Services: Healthy ✓
├─ Data Flow: Normal
├─ Errors in last hour: 0
└─ Uptime: 23h 45min
```

---

## Summary

This architecture provides:

✅ **Loose Coupling**: Services independent, Redis-mediated
✅ **High Throughput**: 1000+ quotes/sec with <5ms latency
✅ **Persistence**: All data to MySQL for analysis
✅ **Multiple Visualizations**: 5 different analytical views
✅ **Automatic Recovery**: Reconnection logic for all components
✅ **Centralized Control**: Single dashboard to manage 11 services
✅ **Scalability**: Add more subscribers without affecting feed
✅ **Observability**: Health monitoring, logs, metrics in dashboard

