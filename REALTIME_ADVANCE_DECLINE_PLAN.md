# Real-Time Advance-Decline System - Implementation Plan

## 📊 Goal
Create live market screens showing real-time changes in Nifty 500 advance-decline statistics during market hours.

---

## ⚠️ Yahoo Finance Limitations & Constraints

### **Critical Constraints:**
1. **No Official Real-Time WebSocket API**
   - Yahoo Finance doesn't provide official WebSocket streaming
   - No push-based real-time data API

2. **Rate Limiting**
   - Aggressive rate limiting on requests
   - Too many requests = IP ban (temporary or permanent)
   - Limit: ~2000 requests/hour (~1 request every 2 seconds)

3. **Delay in Data**
   - Free Yahoo Finance data has 15-20 minute delay
   - Real-time data requires paid subscription (not available via yfinance library)

4. **Batch Query Limitations**
   - Cannot query all 500+ stocks in single API call
   - Need to batch requests (10-50 stocks per request)
   - Full scan of 500 stocks = 10-50 API calls

### **Realistic Expectations:**
- **Not true real-time** (tick-by-tick) like exchange feeds
- **Polling-based** with 1-5 minute intervals
- **Best case:** Near real-time with 1-minute refresh
- **Practical:** 2-5 minute refresh to avoid rate limits

---

## 🎯 Proposed Solution: Hybrid Approach

### **Phase 1: Intraday Polling System** (Recommended First Implementation)

#### **Architecture:**
```
┌─────────────────────────────────────────────────┐
│  Market Hours Monitor (9:15 AM - 3:30 PM IST)  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Polling Engine (Every 2-5 minutes)            │
│  - Query Yahoo Finance for all 779 stocks      │
│  - Batch requests: 50 stocks per call          │
│  - Total time per cycle: ~30-60 seconds        │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  In-Memory Cache (Redis/Dict)                  │
│  - Store last known price for each stock       │
│  - Compare current price vs previous price     │
│  - Calculate advances/declines in real-time    │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Live Dashboard (Tkinter/Web)                  │
│  - Real-time A/D counts                        │
│  - Advance %                                    │
│  - Market breadth gauge                         │
│  - Auto-refresh every cycle                    │
└─────────────────────────────────────────────────┘
```

#### **Key Features:**
1. **Smart Polling:**
   - Only during market hours (9:15 AM - 3:30 PM IST)
   - Configurable interval (default: 3 minutes)
   - Exponential backoff on rate limit errors

2. **Efficient Data Fetching:**
   - Use `yfinance.download()` with batch symbols
   - Fetch only current price + previous close
   - Minimize API calls

3. **Real-Time Calculation:**
   - Compare current LTP (Last Traded Price) vs previous close
   - Update advances/declines instantly
   - Track changes from market open

4. **Live Display:**
   - Auto-updating dashboard
   - Advance-decline counters
   - Percentage gauges
   - Last update timestamp

---

## 📋 Implementation Plan - Step by Step

### **Step 1: Market Hours Detector** ⏰
**File:** `market_hours_monitor.py`

**Features:**
- Detect if market is open (9:15 AM - 3:30 PM IST, Mon-Fri)
- Skip weekends and NSE holidays
- Timezone handling (IST)

**Complexity:** Low
**Time:** 30 minutes
**Priority:** HIGH (Foundation)

---

### **Step 2: Real-Time Data Fetcher** 📡
**File:** `realtime_data_fetcher.py`

**Features:**
- Query Yahoo Finance for current prices
- Batch processing (50 stocks per request)
- Rate limit handling with retry logic
- Error handling for failed stocks
- Cache mechanism (store last successful data)

**Functions:**
```python
def fetch_current_prices(symbols: List[str]) -> Dict[str, float]
def fetch_in_batches(symbols: List[str], batch_size=50) -> Dict
def get_previous_close_prices(symbols: List[str]) -> Dict[str, float]
```

**Complexity:** Medium
**Time:** 1-2 hours
**Priority:** HIGH (Core functionality)

---

### **Step 3: Advance-Decline Calculator (Live)** 🧮
**File:** `realtime_adv_decl_calculator.py`

**Features:**
- Compare current price vs previous close
- Categorize: Advance / Decline / Unchanged
- Calculate percentages
- Track intraday changes
- Store in-memory state

**Data Structure:**
```python
{
    'timestamp': datetime,
    'advances': int,
    'declines': int,
    'unchanged': int,
    'total_stocks': int,
    'advance_pct': float,
    'advance_decline_ratio': float,
    'stocks_data': {
        'RELIANCE.NS': {'ltp': 2500, 'prev_close': 2480, 'change': +20, 'status': 'ADVANCE'},
        ...
    }
}
```

**Complexity:** Medium
**Time:** 1 hour
**Priority:** HIGH

---

### **Step 4: Live Dashboard (Tkinter)** 🖥️
**File:** `realtime_adv_decl_dashboard.py`

**Features:**
- Large display of advance-decline counts
- Color-coded indicators (green/red)
- Advance percentage gauge
- Market breadth strength meter
- Last update timestamp
- Auto-refresh (every poll cycle)
- Manual refresh button

**UI Layout:**
```
┌──────────────────────────────────────────────────────┐
│  NSE Market Breadth - LIVE                           │
│  Last Update: 11:23:45 AM                            │
├──────────────────────────────────────────────────────┤
│                                                       │
│    ADVANCES        DECLINES        UNCHANGED         │
│       342             156              2             │
│    (GREEN)          (RED)          (GRAY)            │
│                                                       │
│    Advance %: 68.4% ████████████░░░░                │
│                                                       │
│    Market Breadth: BULLISH                           │
│                                                       │
│    Total Stocks: 500                                 │
│    A/D Ratio: 2.19                                   │
│    Net A-D: +186                                     │
│                                                       │
│  [⟳ Refresh] [⚙️ Settings] [📊 History] [❌ Exit]  │
└──────────────────────────────────────────────────────┘
```

**Complexity:** Medium-High
**Time:** 2-3 hours
**Priority:** HIGH

---

### **Step 5: Polling Engine & Scheduler** ⚙️
**File:** `realtime_polling_engine.py`

**Features:**
- Background polling loop
- Configurable interval (1-5 minutes)
- Start/Stop controls
- Rate limit management
- Error recovery
- Logging

**Threading:**
- Separate thread for polling (non-blocking UI)
- Queue for data updates
- Signal to UI for refresh

**Complexity:** Medium
**Time:** 1-2 hours
**Priority:** HIGH

---

### **Step 6: Historical Intraday Logger** 📝
**File:** `intraday_adv_decl_logger.py`

**Features:**
- Store each polling cycle data
- Create intraday time-series
- Save to database (optional)
- CSV export for day's data

**Schema:**
```sql
CREATE TABLE intraday_advance_decline (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    trade_date DATE NOT NULL,
    advances INT NOT NULL,
    declines INT NOT NULL,
    unchanged INT NOT NULL,
    total_stocks INT NOT NULL,
    advance_pct DECIMAL(5,2),
    advance_decline_ratio DECIMAL(10,4),
    INDEX idx_date_time (trade_date, timestamp)
);
```

**Complexity:** Low-Medium
**Time:** 1 hour
**Priority:** MEDIUM

---

### **Step 7: Intraday Chart Visualizer** 📈
**File:** `intraday_adv_decl_chart.py`

**Features:**
- Plot intraday advance % over time
- Show Nifty price overlay
- Mark market open/close
- Update chart as new data arrives

**Complexity:** Medium
**Time:** 1-2 hours
**Priority:** MEDIUM

---

### **Step 8: Web Dashboard (Optional)** 🌐
**File:** `web_dashboard_flask.py`

**Features:**
- Flask/FastAPI web server
- WebSocket for real-time updates
- Browser-based dashboard
- Mobile-friendly responsive design
- Multiple user support

**Tech Stack:**
- Backend: Flask + SocketIO
- Frontend: HTML + Chart.js + Bootstrap
- Real-time: WebSocket

**Complexity:** High
**Time:** 4-6 hours
**Priority:** LOW (Phase 2)

---

## 🛠️ Technical Implementation Details

### **1. Yahoo Finance Data Fetching**

**Option A: yfinance Library (Recommended)**
```python
import yfinance as yf

# Single stock
ticker = yf.Ticker("RELIANCE.NS")
data = ticker.info  # Has 'regularMarketPrice' and 'previousClose'

# Multiple stocks (batch)
symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
data = yf.download(symbols, period="1d", interval="1m", progress=False)
# Returns last minute data
```

**Option B: Yahoo Finance API (Direct)**
```python
import requests

url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"
response = requests.get(url)
data = response.json()
```

**Recommended:** Use yfinance with error handling and retries.

---

### **2. Rate Limit Strategy**

```python
import time
from functools import wraps

def rate_limit(calls_per_minute=30):
    """Decorator to limit API calls"""
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait_time = min_interval - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(calls_per_minute=20)  # Max 20 calls per minute
def fetch_quotes(symbols):
    return yf.download(symbols, period="1d", interval="1m", progress=False)
```

---

### **3. Market Hours Detection**

```python
from datetime import datetime, time
import pytz

def is_market_open():
    """Check if NSE market is currently open"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Check if weekend
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Market hours: 9:15 AM - 3:30 PM IST
    market_open = time(9, 15)
    market_close = time(15, 30)
    current_time = now.time()
    
    return market_open <= current_time <= market_close
```

---

### **4. In-Memory Cache**

```python
class MarketDataCache:
    def __init__(self):
        self.last_prices = {}  # {symbol: price}
        self.previous_close = {}
        self.last_update = None
    
    def update(self, symbol, current_price, prev_close):
        self.last_prices[symbol] = current_price
        self.previous_close[symbol] = prev_close
        self.last_update = datetime.now()
    
    def get_change_status(self, symbol):
        if symbol not in self.last_prices:
            return 'UNKNOWN'
        
        current = self.last_prices[symbol]
        prev = self.previous_close.get(symbol, current)
        
        if current > prev:
            return 'ADVANCE'
        elif current < prev:
            return 'DECLINE'
        else:
            return 'UNCHANGED'
    
    def calculate_breadth(self):
        advances = sum(1 for s in self.last_prices if self.get_change_status(s) == 'ADVANCE')
        declines = sum(1 for s in self.last_prices if self.get_change_status(s) == 'DECLINE')
        unchanged = sum(1 for s in self.last_prices if self.get_change_status(s) == 'UNCHANGED')
        
        return {
            'advances': advances,
            'declines': declines,
            'unchanged': unchanged,
            'total': len(self.last_prices),
            'advance_pct': (advances / len(self.last_prices) * 100) if self.last_prices else 0
        }
```

---

## ⚡ Performance Optimization

### **1. Parallel Fetching**
```python
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf

def fetch_batch(symbols):
    return yf.download(symbols, period="1d", interval="1m", progress=False)

def fetch_all_parallel(symbols, batch_size=50):
    batches = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_batch, batches))
    
    return results
```

### **2. Caching Strategy**
- Cache successful responses for 1 minute
- Retry failed stocks in next cycle
- Skip repeatedly failing stocks (after 3 failures)

### **3. Progressive Loading**
- Show cached data immediately
- Update incrementally as new data arrives
- Don't block UI waiting for all data

---

## 📊 Data Flow Diagram

```
┌─────────────┐
│ Market Open │
│  Detector   │
└──────┬──────┘
       │ YES (9:15 AM - 3:30 PM)
       ▼
┌─────────────────────┐
│  Start Polling Loop │
│  (Every 3 minutes)  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Fetch Current Prices       │
│  (779 stocks in 16 batches) │
│  Duration: ~30-45 seconds   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Compare vs Previous Close  │
│  Classify: A/D/U            │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Update In-Memory Cache     │
└──────┬──────────────────────┘
       │
       ├─────────────────┬────────────────┐
       ▼                 ▼                ▼
┌──────────────┐  ┌──────────┐  ┌──────────────┐
│ Live Dash    │  │ Database │  │ WebSocket    │
│ (Tkinter)    │  │ Logger   │  │ (Web Users)  │
└──────────────┘  └──────────┘  └──────────────┘
       │
       │ Wait 3 minutes
       │
       └──────► Next Cycle
```

---

## 🎯 Recommended Implementation Order

### **Phase 1: Core Foundation (Day 1-2)**
1. ✅ Market Hours Monitor
2. ✅ Real-Time Data Fetcher
3. ✅ Advance-Decline Calculator
4. ✅ Basic Live Dashboard

**Deliverable:** Working live dashboard showing A/D during market hours

### **Phase 2: Enhancement (Day 3-4)**
5. ✅ Polling Engine with threading
6. ✅ Historical Logger
7. ✅ Error handling & rate limit management
8. ✅ Configuration file (intervals, stocks list, etc.)

**Deliverable:** Robust polling system with logging

### **Phase 3: Visualization (Day 5)**
9. ✅ Intraday chart visualizer
10. ✅ Dashboard improvements (gauges, alerts)

**Deliverable:** Professional live monitoring system

### **Phase 4: Web Interface (Day 6-7, Optional)**
11. ⏳ Flask web server
12. ⏳ WebSocket integration
13. ⏳ Web dashboard UI

**Deliverable:** Web-based multi-user system

---

## 📁 Project Structure

```
realtime_market_breadth/
│
├── core/
│   ├── __init__.py
│   ├── market_hours_monitor.py      # Step 1
│   ├── realtime_data_fetcher.py     # Step 2
│   └── realtime_adv_decl_calculator.py  # Step 3
│
├── ui/
│   ├── __init__.py
│   ├── realtime_adv_decl_dashboard.py   # Step 4 (Tkinter)
│   └── intraday_adv_decl_chart.py       # Step 7
│
├── services/
│   ├── __init__.py
│   ├── realtime_polling_engine.py   # Step 5
│   └── intraday_adv_decl_logger.py  # Step 6
│
├── web/ (Optional)
│   ├── __init__.py
│   ├── web_dashboard_flask.py       # Step 8
│   ├── templates/
│   │   └── dashboard.html
│   └── static/
│       ├── css/
│       └── js/
│
├── config/
│   ├── settings.py
│   └── config.yaml
│
├── tests/
│   ├── test_market_hours.py
│   ├── test_data_fetcher.py
│   └── test_calculator.py
│
├── logs/
│   └── realtime_market.log
│
├── data/
│   └── intraday_cache/
│
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration File

**config/config.yaml:**
```yaml
market:
  timezone: 'Asia/Kolkata'
  market_open_time: '09:15'
  market_close_time: '15:30'
  
polling:
  interval_seconds: 180  # 3 minutes
  batch_size: 50
  max_retries: 3
  retry_delay: 5
  
rate_limit:
  calls_per_minute: 20
  max_requests_per_hour: 1000
  
stocks:
  source: 'available_stocks_list.py'
  total_stocks: 779
  
dashboard:
  auto_refresh: true
  window_width: 800
  window_height: 600
  theme: 'light'  # 'light' or 'dark'
  
logging:
  level: 'INFO'
  file: 'logs/realtime_market.log'
  enable_database: true
  
database:
  host: '127.0.0.1'
  port: 3306
  database: 'marketdata'
  table: 'intraday_advance_decline'
```

---

## ⚠️ Important Considerations

### **1. Legal & Compliance**
- ✅ Yahoo Finance data is for personal use
- ⚠️ Don't redistribute real-time data commercially
- ⚠️ Check Yahoo Finance Terms of Service
- ✅ This is for educational/personal trading analysis

### **2. Reliability**
- ❌ Not suitable for HFT (High-Frequency Trading)
- ✅ Good for: Position tracking, market sentiment, swing trading
- ⚠️ Expect occasional failures/delays
- ✅ Always have fallback/cached data

### **3. Cost**
- ✅ 100% FREE using Yahoo Finance
- ✅ No subscription needed
- ⚠️ But rate-limited

### **4. Accuracy**
- ⚠️ 15-20 minute delay on free tier
- ⚠️ Occasional stale data
- ✅ Good enough for breadth analysis (not price execution)

---

## 🚀 Quick Start Commands

```bash
# Step 1: Setup environment
pip install yfinance pandas pytz pyyaml

# Step 2: Create project structure
mkdir -p realtime_market_breadth/{core,ui,services,config,logs,data}

# Step 3: Implement Step 1 (Market Hours Monitor)
# Copy market_hours_monitor.py template

# Step 4: Test market hours
python test_market_hours.py

# Step 5: Implement Step 2 (Data Fetcher)
# Copy realtime_data_fetcher.py template

# Step 6: Test data fetching
python test_data_fetcher.py

# Step 7-10: Continue implementing remaining steps...

# Final: Launch live dashboard
python ui/realtime_adv_decl_dashboard.py
```

---

## 📈 Expected Performance

### **Single Polling Cycle:**
- 779 stocks ÷ 50 per batch = 16 API calls
- Rate limit: 1 call every 3 seconds
- **Total time: ~48 seconds per full scan**

### **Refresh Rate:**
- Practical: **Every 3 minutes** (safe from rate limits)
- Aggressive: Every 1 minute (risk of rate limit)
- Conservative: Every 5 minutes (very safe)

### **Data Freshness:**
- Yahoo Finance: 15-20 min delay
- Our system: Additional 3 min polling delay
- **Total delay: ~18-23 minutes from real-time**

### **Workaround for True Real-Time:**
If you need actual real-time (0 delay), you would need:
1. NSE API access (institutional, paid)
2. WebSocket from brokers (Zerodha Kite, etc.)
3. Data vendor (Bloomberg, Refinitiv, etc.)

---

## 🎯 Success Criteria

### **MVP (Minimum Viable Product):**
- ✅ Dashboard launches successfully
- ✅ Fetches data for 779 stocks
- ✅ Updates A/D counts every 3 minutes during market hours
- ✅ Shows advance %, decline %, unchanged %
- ✅ Manual refresh button works
- ✅ No crashes or freezes

### **Production Ready:**
- ✅ All MVP features
- ✅ Error handling for API failures
- ✅ Logging of all activities
- ✅ Historical data storage
- ✅ Intraday chart visualization
- ✅ Configurable settings
- ✅ Rate limit protection

---

## 📝 Next Steps

1. **Review this plan** - Confirm approach meets your needs
2. **Start with Step 1** - Implement Market Hours Monitor
3. **Test each step** - Validate before moving to next
4. **Iterate** - Add features incrementally
5. **Deploy** - Use during live market hours

---

## ❓ Decision Points

**Before we start implementing, please confirm:**

1. **Refresh Interval:** 
   - 3 minutes (recommended) ✓
   - 1 minute (aggressive, risk rate limits)
   - 5 minutes (safe, less live)

2. **UI Preference:**
   - Tkinter Desktop App (Phase 1) ✓
   - Web Dashboard (Phase 2)
   - Both

3. **Data Logging:**
   - Yes, save all intraday data ✓
   - No, just live view

4. **Stock Coverage:**
   - All 779 stocks (complete breadth) ✓
   - Top 200 stocks (faster polling)
   - Nifty 500 only (if better list available)

5. **Priority Features:**
   - Basic live dashboard first ✓
   - Include intraday chart immediately
   - Add web interface from start

---

**Ready to start? Let me know and we'll begin with Step 1!** 🚀
