# DHAN Control Center - Service Orchestration Wizard

**Version 2.0** - Single Window, Intelligent Service Management

---

## 🎯 Overview

The enhanced DHAN Control Center includes a **Service Orchestration Wizard** that intelligently manages all 11 services from a single window. No more multiple terminals - all services run within the Control Center.

### Key Features

✅ **Single-Window Operation** - All services managed in one place  
✅ **Intelligent Startup Sequence** - Services start in optimal order  
✅ **Auto-Restart on Crash** - Failed services automatically recover  
✅ **Real-Time Monitoring** - Live health dashboard with CPU/Memory/Uptime  
✅ **Unified Logging** - All service logs in one interface  
✅ **Graceful Shutdown** - All services stop cleanly  
✅ **No Terminal Dependency** - If Control Center stays open, data keeps flowing  

---

## 🚀 Startup Wizard - Service Order

The wizard starts services in a carefully designed sequence:

### Phase 1: CRITICAL (Must succeed)
```
1. FNO Feed Launcher (Priority 1)
   └─ Connects to Dhan API WebSocket
   └─ Publishes quotes to Redis
   └─ Requirement for entire system

2. FNO Database Writer (Priority 2)
   └─ Subscribes to Redis
   └─ Writes quotes to MySQL
   └─ No data loss if Feed runs
```

### Phase 2: IMPORTANT (Should run)
```
3. FNO Services Monitor (Priority 3)
   └─ Dashboard for monitoring
   └─ Optional but recommended
```

### Phase 3: OPTIONAL (Enhanced features)
```
4. Volume Profile Visualizer (Priority 4)
5. Market Breadth Analyzer (Priority 4)
6. Tick Chart (Priority 4)
7. Volume Profile Chart (Priority 4)
8. Quote Visualizer (Priority 4)
   └─ All can be toggled on/off
   └─ Independent visualizations
```

### Phase 4: UTILITIES (Background services)
```
9. Market Scheduler (Priority 5)
   └─ Auto-starts/stops at market hours
   
10. Instrument Display (Priority 5)
    └─ Reference data viewer
    
11. FNO+MCX Feed (Priority 5)
    └─ Optional commodities data
```

---

## 📊 User Interface Tabs

### Tab 1: 🚀 Startup Wizard (NEW)

**Purpose:** Start all services in sequence

**Components:**
```
┌─────────────────────────────────────────┐
│ Service Startup Orchestration Wizard    │
├─────────────────────────────────────────┤
│                                         │
│ Instructions:                           │
│ • Feed Launcher (CRITICAL)              │
│ • Database Writer (CRITICAL)            │
│ • Services Monitor (IMPORTANT)          │
│ • Visualizations (OPTIONAL)             │
│ • All services run in this window!      │
│                                         │
├─────────────────────────────────────────┤
│ Startup Options:                        │
│ ☑ Include Visualization Services       │
│ ☑ Auto-Restart on Crash               │
│                                         │
├─────────────────────────────────────────┤
│ Startup Progress: ████████░░ 80%       │
│ Status: [6/11] services started        │
│                                         │
├─────────────────────────────────────────┤
│ [▶️  Start All Services] [⏹️  Stop All] │
│                                         │
├─────────────────────────────────────────┤
│ Service Startup Sequence:                │
│ ☑ FNO Feed Launcher                    │
│ ☑ FNO Database Writer                  │
│ ☑ FNO Services Monitor                 │
│ ☐ Volume Profile (disabled by default) │
│ ☐ Market Breadth (disabled)             │
│ ...                                     │
└─────────────────────────────────────────┘
```

**What happens when you click "Start All":**
1. Feed Launcher starts → waits for stability (2s)
2. Database Writer starts → waits (2s)
3. Services Monitor starts → waits (2s)
4. Visualization services start (if enabled)
5. Utility services start
6. All logs visible in real-time
7. Auto-restart enabled for failed services

**Options:**
- **Include Visualization Services:** Toggle all 5 visualizations on/off
- **Auto-Restart on Crash:** Automatically restart crashed services (up to 3 times)

---

### Tab 2: 📊 Service Status

**Real-time table of all running services:**

```
Service                      Status        PID    Memory   CPU    Uptime
─────────────────────────────────────────────────────────────────────
FNO Feed Launcher            RUNNING       5432   120 MB   8.5%   245 s
FNO Database Writer          RUNNING       5444   85 MB    2.1%   243 s
FNO Services Monitor         RUNNING       5456   95 MB    3.2%   240 s
Volume Profile               RUNNING       5468   110 MB   6.3%   235 s
Market Breadth               RUNNING       5480   75 MB    4.1%   232 s
Tick Chart                   STOPPED       ---    0        0      0
...
```

Updates every 2 seconds with:
- Service name
- Current status (RUNNING/STOPPED/RESTARTING/ERROR)
- Process ID
- Memory usage in MB
- CPU usage percentage
- Uptime in seconds

---

### Tab 3: 📈 System Monitor

**System health dashboard:**

```
=== DHAN System Health ===
Time: 2025-12-12 14:30:45

Services Status:
  ✓ FNO Feed Launcher          | PID:  5432 | Mem: 120MB | CPU: 8.5% | ⏱️ 245s
  ✓ FNO Database Writer        | PID:  5444 | Mem: 85MB  | CPU: 2.1% | ⏱️ 243s
  ✓ FNO Services Monitor       | PID:  5456 | Mem: 95MB  | CPU: 3.2% | ⏱️ 240s
  ✓ Volume Profile             | PID:  5468 | Mem:110MB  | CPU: 6.3% | ⏱️ 235s
  ✓ Market Breadth             | PID:  5480 | Mem: 75MB  | CPU: 4.1% | ⏱️ 232s
  ✗ Tick Chart                 | STOPPED

Running Services: 5/11

System Resources:
  CPU Usage: 32%
  Memory: 8.5GB / 16.0GB (53%)
```

**Updates every 2 seconds with:**
- Individual service stats
- Total running count
- System-wide CPU usage
- System-wide memory usage

---

### Tab 4: 📋 Logs

**Unified logging from all services:**

```
[14:30:45] SYSTEM                    | Starting service orchestration...
[14:30:45] SYSTEM                    | [1/11] Starting FNO Feed Launcher...
[14:30:45] FNO Feed Launcher         | Starting DhanFeedService...
[14:30:46] FNO Feed Launcher         | ✅ Started successfully (PID: 5432)
[14:30:48] SYSTEM                    | [2/11] Starting FNO Database Writer...
[14:30:48] FNO Database Writer       | Connecting to MySQL dhan_trading...
[14:30:49] FNO Database Writer       | ✅ Started successfully (PID: 5444)
[14:30:51] SYSTEM                    | [3/11] Starting FNO Services Monitor...
[14:30:52] FNO Services Monitor      | ✅ Started successfully (PID: 5456)
[14:30:53] SYSTEM                    | [4/11] Starting Volume Profile...
[14:30:54] Volume Profile            | PyQt5 window created
[14:30:54] Volume Profile            | ✅ Started successfully (PID: 5468)
[14:30:54] SYSTEM                    | ✅ All configured services started
```

**Features:**
- Filter by service (All / SYSTEM / Feed / DB Writer / etc.)
- All logs from all services in one place
- Timestamps for each message
- Auto-scroll to latest messages
- Search-friendly format

---

## 💡 How It Works

### Architecture

```
┌─────────────────────────┐
│ DHAN Control Center V2  │ (Main PyQt5 Window)
├─────────────────────────┤
│                         │
│ ┌───────────────────┐   │
│ │ Orchestrator Thrd │◄──┤─ Manages startup sequence
│ │ • Service start   │   │
│ │ • Health monitor  │   │
│ │ • Auto-restart    │   │
│ └───────────────────┘   │
│         │               │
│         ├─ Start────┐   │
│         │           │   │
│         ▼           ▼   │
│    ┌─────────┐  ┌─────────────┐
│    │ Process1│  │ Process2    │  ... (All services as subprocesses)
│    └─────────┘  └─────────────┘
│         │           │
│         └─────┬─────┘
│               │ (Monitor)
│        ┌──────▼──────┐
│        │Status/Logs  │
│        │ Real-time   │
│        └─────────────┘
│               │
│        ┌──────▼──────────┐
│        │ UI Tabs         │
│        │ • Wizard        │
│        │ • Status        │
│        │ • Monitor       │
│        │ • Logs          │
│        └─────────────────┘
│                         │
└─────────────────────────┘
        ▲
        │ Control Center window
        │ stays open
        │ = services keep running!
```

### Key Advantage

**If Control Center window is open → Services keep running**  
**If Control Center crashes → Services stay running** (independent processes)  
**If Control Center closes → Can restart and attach to running services**

---

## 🔄 Auto-Restart Feature

Services are automatically restarted if they crash:

```
Service crashes detected
         │
         ▼
[Auto-Restart Enabled?] 
         │
    ┌────┴────┐
    │ YES     │ NO
    ▼         ▼
  Wait     Service marked
  2 sec    as FAILED
    │
    ├─ Restart attempt 1/3
    │  │
    │  ├─ SUCCESS? → Resume running
    │  │
    │  └─ FAILURE → Wait, try again
    │
    ├─ Restart attempt 2/3
    │
    └─ Restart attempt 3/3
       │
       ├─ SUCCESS? → Resume
       │
       └─ FAILURE? → Mark as ERROR
```

**Configuration:**
- Max restart attempts: 3
- Wait between attempts: 2 seconds
- Toggle on/off: "Auto-Restart on Crash" checkbox

---

## 📋 Critical vs Optional Services

### CRITICAL (Must start for trading)
```
❌ If FNO Feed Launcher fails to start:
   → Wizard stops
   → Error message shown
   → Manual intervention required

❌ If FNO Database Writer fails:
   → Wizard stops
   → No data persistence possible
   → Manual intervention required
```

### OPTIONAL (Doesn't stop wizard)
```
⚠️  If Volume Profile fails:
   → Wizard continues
   → Other visualizations start
   → Service marked as FAILED
   → Auto-restart attempts (3x)
   → If still fails → Move to next service
```

---

## 🛑 Graceful Shutdown

When closing the Control Center:

```
User clicks [X] button
        │
        ▼
[Stop all services first?]
        │
    ┌───┴────┐
    │ YES    │ NO
    ▼        ▼
  Stop     Cancel
  All      Close
   │
   ├─ Send SIGTERM to each service
   │
   ├─ Wait 5 seconds for graceful shutdown
   │
   └─ If not closed: Send SIGKILL
   
All services stopped cleanly
Control Center closes
```

---

## 💾 Data Safety

### Scenario 1: Control Center Window Closed

```
User accidentally closes Control Center window
        │
        ▼
Services (independent processes) continue running!
        │
        ├─ Feed Launcher keeps publishing to Redis
        │
        ├─ Database Writer keeps writing to MySQL
        │
        └─ Data keeps flowing!

User can:
• Reopen Control Center V2 → see running services
• Or restart in new Control Center
• Or open visualizations independently
```

### Scenario 2: Feed Process Crashes

```
Feed process crashes
        │
        ▼
[Orchestrator detects crash]
        │
        ├─ Log: "❌ Feed crashed"
        │
        ├─ Check auto-restart: enabled
        │
        ├─ Attempt restart (1/3)
        │
        └─ Success → Resume publishing
        
Data loss: 0 quotes (Database Writer still running!)
```

### Scenario 3: Database Writer Crashes

```
DB Writer crashes
        │
        ▼
[Orchestrator detects crash]
        │
        ├─ Redis keeps buffering quotes (Stream)
        │
        ├─ Auto-restart DB Writer
        │
        └─ DB Writer catches up from Redis stream
        
Data loss: 0 quotes (all in Redis waiting)
```

---

## 🎮 Usage Example

### Start System for Day Trading

```
1. Open Command Prompt / PowerShell
   cd d:\MyProjects\StockScreeer
   python launch_dhan_control_center_v2.py

2. Control Center window opens with 4 tabs:
   • 🚀 Startup Wizard (CURRENT)
   • 📊 Service Status
   • 📈 System Monitor
   • 📋 Logs

3. Click [▶️  Start All Services (Wizard)]
   Control Center begins orchestration:
   
   [14:30:45] SYSTEM | Starting service orchestration...
   [14:30:45] SYSTEM | [1/11] Starting FNO Feed Launcher...
   [14:30:46] Feed Launcher | ✅ Started successfully (PID: 5432)
   [14:30:48] SYSTEM | [2/11] Starting FNO Database Writer...
   [14:30:49] DB Writer | ✅ Started successfully (PID: 5444)
   [14:30:51] SYSTEM | [3/11] Starting FNO Services Monitor...
   [14:30:52] Services Monitor | ✅ Started successfully (PID: 5456)
   [14:30:54] SYSTEM | ✅ All configured services started
   
   Progress bar: ████████████████████ 100%

4. Switch to 📊 Service Status tab:
   See all services running with PID, Memory, CPU, Uptime

5. Switch to 📈 System Monitor tab:
   Watch real-time health of all services

6. Switch to 📋 Logs tab:
   See all activity from all services

7. Keep Control Center window open during trading

8. At end of day, click [⏹️  Stop All Services]
   or just close the window (services stop cleanly)
```

---

## ⚙️ Configuration

### Enable/Disable Visualizations

**On Startup Wizard tab:**
```
☑ Include Visualization Services  ← Uncheck to skip visualizers
☑ Auto-Restart on Crash          ← Uncheck to disable auto-restart
```

### Modify Service List

**In code:** Edit `service_configs` list in `launch_dhan_control_center_v2.py`

```python
service_configs = [
    ("FNO Feed Launcher", "launch_fno_feed.py", 
     "Real-time NIFTY & BANKNIFTY futures/options feed", 1, "green"),
    
    # Add more services here...
]
```

### Max Restart Attempts

**In code:** Edit `DhanService` class:

```python
self.max_restarts = 3  # Change to desired number
```

---

## 🐛 Troubleshooting

### Control Center window won't open

```bash
python launch_dhan_control_center_v2.py
# Check if PyQt5 installed:
pip install PyQt5
```

### Services won't start

1. Check .env file has correct configuration
2. Check logs tab for error messages
3. Verify MongoDB/MySQL running
4. Try starting individual service manually

### Service keeps restarting in loop

```
[14:30:54] Service | ❌ Failed to start
[14:30:56] Service | 🔄 Auto-restarting (1/3)...
[14:30:58] Service | ❌ Failed to start
[14:30:60] Service | 🔄 Auto-restarting (2/3)...
```

Check logs for actual error, fix issue, restart Control Center

### Memory usage growing

1. Check logs for memory leaks
2. Restart individual service
3. Or restart all services from wizard

---

## 📊 Performance Impact

```
Overhead of Control Center:
• PyQt5 UI:          ~50 MB
• Orchestrator Thread: <1 MB
• Monitoring:        <1 MB
─────────────────────────────
Total Control Center: ~52 MB

Each Service (approx):
• Feed Launcher:  120 MB
• DB Writer:       80 MB
• Visualizers:     80-110 MB each

Total System (all 11 services): ~800-900 MB
```

---

## 🚀 Next Steps

1. **Start Control Center:**
   ```bash
   python launch_dhan_control_center_v2.py
   ```

2. **Click "Start All Services"** in Startup Wizard

3. **Watch logs** for real-time progress

4. **Monitor system health** in System Monitor tab

5. **Keep window open** during trading

6. **Data flows continuously** as long as window is open

---

## 📞 Support

For issues, check:
- 📋 Logs tab for error messages
- 📈 System Monitor for resource issues
- Configuration in `.env` file
- Previous documentation files in `dhan_trading/documentation/`

---

**Version:** 2.0 - Service Orchestration Wizard  
**Release Date:** December 12, 2025  
**Status:** ✅ Production Ready
