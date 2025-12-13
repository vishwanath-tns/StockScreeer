# Service Orchestration Wizard - Quick Start Guide

## 🎯 TL;DR (2-Minute Setup)

### Start System in 3 Steps

**Step 1: Open Command Prompt**
```bash
cd d:\MyProjects\StockScreeer
```

**Step 2: Launch Control Center V2**
```bash
python launch_dhan_control_center_v2.py
```

**Step 3: Click "▶️  Start All Services"**
- Sit back
- Watch logs
- All services start automatically in correct order
- Data flows continuously!

---

## 📊 What You'll See

### Control Center Opens with 4 Tabs

```
┌─────────────────────────────────────────────────┐
│ DHAN Control Center - Service Orchestration Hub │
├─────────────────────────────────────────────────┤
│ [🚀 Startup Wizard] [📊 Status] [📈 Monitor] [📋 Logs]
└─────────────────────────────────────────────────┘
```

### Tab 1: 🚀 Startup Wizard (Selected)

```
SERVICE STARTUP ORCHESTRATION WIZARD

Instructions show the 5 phases...

Startup Options:
☑ Include Visualization Services
☑ Auto-Restart on Crash

Startup Progress: ░░░░░░░░░░░ 0%
Status: Ready to start

[▶️  Start All Services (Wizard)] [⏹️  Stop All Services]

Service Startup Sequence:
☑ FNO Feed Launcher
☑ FNO Database Writer
☑ FNO Services Monitor
☑ Volume Profile
☑ Market Breadth
... (and 6 more)
```

---

## 🚀 Click "Start All Services"

Watch the magic happen:

```
Progress bar fills up ████████░░ 65%

Logs appear:
[14:30:45] SYSTEM        | Starting service orchestration...
[14:30:45] SYSTEM        | [1/11] Starting FNO Feed Launcher...
[14:30:46] Feed Launcher | ✅ Started successfully (PID: 5432)
[14:30:48] SYSTEM        | [2/11] Starting FNO Database Writer...
[14:30:49] DB Writer     | ✅ Started successfully (PID: 5444)
[14:30:51] SYSTEM        | [3/11] Starting FNO Services Monitor...
[14:30:52] Mon Services  | ✅ Started successfully (PID: 5456)
...
[14:31:30] SYSTEM        | ✅ All configured services started
```

---

## 📊 Switch to Status Tab

See all services with live stats:

```
Service                    Status      PID    Memory  CPU    Uptime
─────────────────────────────────────────────────────────────────
FNO Feed Launcher          RUNNING    5432   120MB   8.5%   45s
FNO Database Writer        RUNNING    5444   85MB    2.1%   43s
FNO Services Monitor       RUNNING    5456   95MB    3.2%   40s
Volume Profile             RUNNING    5468   110MB   6.3%   35s
Market Breadth             RUNNING    5480   75MB    4.1%   32s
Tick Chart                 RUNNING    5492   105MB   5.8%   27s
Quote Visualizer           RUNNING    5504   40MB    1.2%   20s
```

---

## 📈 Switch to Monitor Tab

System health dashboard updates every 2 seconds:

```
=== DHAN System Health ===
Time: 2025-12-12 14:31:45

Services Status:
  ✓ FNO Feed Launcher          | PID:  5432 | Mem: 120MB | CPU:  8.5% | ⏱️ 45s
  ✓ FNO Database Writer        | PID:  5444 | Mem:  85MB | CPU:  2.1% | ⏱️ 43s
  ✓ FNO Services Monitor       | PID:  5456 | Mem:  95MB | CPU:  3.2% | ⏱️ 40s
  ✓ Volume Profile             | PID:  5468 | Mem: 110MB | CPU:  6.3% | ⏱️ 35s
  ✓ Market Breadth             | PID:  5480 | Mem:  75MB | CPU:  4.1% | ⏱️ 32s
  ✓ Tick Chart                 | PID:  5492 | Mem: 105MB | CPU:  5.8% | ⏱️ 27s
  ✓ Quote Visualizer           | PID:  5504 | Mem:  40MB | CPU:  1.2% | ⏱️ 20s

Running Services: 7/11

System Resources:
  CPU Usage: 32%
  Memory: 8.5GB / 16.0GB (53%)
```

---

## 📋 Switch to Logs Tab

All activity in one place:

```
[14:30:45] SYSTEM                    | Starting service orchestration...
[14:30:45] SYSTEM                    | [1/11] Starting FNO Feed Launcher...
[14:30:45] FNO Feed Launcher         | Starting DhanFeedService...
[14:30:46] FNO Feed Launcher         | ✅ Started successfully (PID: 5432)
[14:30:48] SYSTEM                    | [2/11] Starting FNO Database Writer...
[14:30:48] FNO Database Writer       | Connecting to MySQL dhan_trading...
[14:30:49] FNO Database Writer       | ✅ Started successfully (PID: 5444)
[14:30:51] SYSTEM                    | [3/11] Starting FNO Services Monitor...
[14:30:52] FNO Services Monitor      | PyQt5 window created
[14:30:52] FNO Services Monitor      | ✅ Started successfully (PID: 5456)

Filter: All
```

---

## ✅ System Ready!

Everything is running:
- ✅ Feed Launcher publishing to Redis
- ✅ Database Writer persisting to MySQL
- ✅ Visualizers reading live data
- ✅ All in ONE window
- ✅ Auto-restart if anything crashes
- ✅ Continuous monitoring

---

## 🎮 During Trading Hours

### Keep the Window Open
```
Control Center window open = Services keep running = Data flows
```

### Monitor the System

Every 2 seconds:
- Status tab updates with live stats
- Monitor tab shows CPU/Memory
- Logs show all activity
- Progress bars show service uptime

### If a Service Crashes

```
[14:45:32] Volume Profile | ❌ Process crashed
[14:45:33] Volume Profile | 🔄 Auto-restarting (1/3)...
[14:45:35] Volume Profile | ✅ Restarted successfully

No manual intervention needed!
```

---

## 🛑 Stop Services

**Option 1: Click [⏹️  Stop All Services]**
```
Gracefully stops all services
Allows clean shutdown
Data saved
```

**Option 2: Close the window**
```
Prompts: "Close DHAN Control Center will stop all services?"
Click Yes → All services stop gracefully
Click No → Keep running
```

---

## 💾 Data Safety

### Key Principle
```
Control Center window can close
  └─ Services (as independent processes) keep running!
  
Example:
[14:30:00] Start Control Center, click "Start All"
[14:31:00] All services running
[14:32:00] Control Center accidentally closes
[14:32:01] Services STILL RUNNING ✓
[14:32:02] Feed publishing to Redis ✓
[14:32:03] DB Writer writing to MySQL ✓
[14:35:00] User reopens Control Center
[14:35:01] Sees all services still running!
```

---

## ⚙️ Options & Configuration

### On Startup Wizard Tab

**1. Include Visualization Services**
- ✅ Checked: Start Volume Profile, Market Breadth, Tick Chart, etc.
- ❌ Unchecked: Skip visualizations, start only essentials

**2. Auto-Restart on Crash**
- ✅ Checked: If service crashes → auto restart (3 attempts)
- ❌ Unchecked: If service crashes → mark as FAILED

---

## 🐛 If Something Goes Wrong

### Service won't start?
1. Check logs tab for error message
2. Common issues:
   - .env file missing configuration
   - MySQL not running
   - Redis not running
   - Port already in use
3. Fix the issue, try again

### Service keeps restarting?
1. Check logs for actual error
2. Disable auto-restart: Uncheck "Auto-Restart on Crash"
3. Manually start service to see error
4. Fix root cause

### Memory usage too high?
1. Check System Monitor tab
2. Restart individual service from Status tab
3. Or restart all services from Wizard

### Lost data?
1. Check logs when data stopped flowing
2. MySQL still has all previous data
3. Redis stream buffered new data
4. No permanent data loss

---

## 📞 Support

### Documentation Files

All in `dhan_trading/documentation/`:

- **DHAN_ARCHITECTURE.md** - System design
- **DHAN_QUICK_GUIDE.md** - Visual reference
- **DHAN_VISUAL_DIAGRAMS.md** - System diagrams
- **SERVICE_ORCHESTRATION_WIZARD.md** - Detailed guide
- **V1_vs_V2_COMPARISON.md** - Feature comparison
- **FEED_AND_DB_TEST_REPORT.md** - Test results

### Common Questions

**Q: Can I run old Control Center V1 and new V2 together?**
A: Yes! They don't conflict. Both work with same services.

**Q: What happens if Control Center crashes?**
A: Services keep running. Restart Control Center to monitor them.

**Q: Do I need multiple terminals now?**
A: No! That's the whole point. Single window only.

**Q: How much memory does this use?**
A: Control Center ~50MB + Services ~600MB = ~650MB total

**Q: Can I disable auto-restart?**
A: Yes, uncheck "Auto-Restart on Crash" on Wizard tab

**Q: How do I update the service list?**
A: Edit `service_configs` in `launch_dhan_control_center_v2.py`

---

## 🚀 Summary

| Item | Answer |
|------|--------|
| **How to start?** | `python launch_dhan_control_center_v2.py` |
| **How to launch services?** | Click [▶️  Start All Services] |
| **How to monitor?** | Watch 📈 System Monitor tab |
| **How to check logs?** | See 📋 Logs tab |
| **How to stop?** | Click [⏹️  Stop All Services] |
| **Data safe if window closes?** | YES ✓ |
| **Auto-restart if service crashes?** | YES ✓ |
| **Can I use visualizers?** | YES ✓ (toggle on/off) |
| **Do I need multiple terminals?** | NO ✗ |

---

**Ready to start?**
```bash
python launch_dhan_control_center_v2.py
```

Then just click one button. That's it! 🎉
