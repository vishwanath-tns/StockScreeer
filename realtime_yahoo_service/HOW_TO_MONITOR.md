# How to Check if Services are Running

## Quick Visual Check

### Option 1: Dashboard (Recommended 🌟)

**Double-click:** `view_dashboard.bat`

Or manually open: `dashboard.html` in your browser

**What you'll see:**
- 🟢 **Green "ONLINE"** = Service is running perfectly
- 🔴 **Red "OFFLINE"** = Service is not running
- **Live metrics**: Message count, candles processed, uptime
- **Real-time data feed**: Streaming market data for AAPL, GOOGL, MSFT

### Option 2: Command Line Status Check

```powershell
python check_service_status.py
```

**Output will show:**
- ✅ WebSocket server status (running/not running)
- 📄 Log file contents (last 5 entries)
- 🚀 Instructions on how to start if not running

### Option 3: Manual Port Check

```powershell
# Check if port 8765 is open (WebSocket server)
netstat -ano | findstr :8765

# If you see "LISTENING" -> Service is running
# If no output -> Service is not running
```

## How to Start the Service

### Method 1: Batch File (Easiest)
**Double-click:** `start_service.bat`

### Method 2: Command Line
```powershell
cd D:\MyProjects\StockScreeer\realtime_yahoo_service
python main.py --config config\local_test.yaml
```

### Method 3: PowerShell
```powershell
Set-Location D:\MyProjects\StockScreeer\realtime_yahoo_service
python main.py --config config\local_test.yaml
```

## How to Visualize Running Service

### 1. Live Dashboard (Best Experience)

**File:** `dashboard.html`

**Features:**
- 🎨 Beautiful modern UI with gradients
- 📊 Real-time metrics (messages, candles, uptime)
- 📡 Live data feed showing latest market prices
- 🟢 Connection status indicator
- 🔄 Auto-reconnect functionality
- 🗑️ Clear data button

**How to use:**
1. Start service (`start_service.bat`)
2. Open dashboard (`view_dashboard.bat` or open `dashboard.html`)
3. Dashboard auto-connects in 1 second
4. Watch real-time data streaming!

### 2. Simple WebSocket Client

**File:** `examples\test_websocket_client.html`

**Features:**
- Simple interface
- Color-coded event types
- Message statistics
- Manual connect/disconnect

### 3. Command Line Monitoring

```powershell
# Watch logs in real-time
Get-Content test_service.log -Tail 20 -Wait

# Check recent activity
Get-Content test_service.log -Tail 50
```

## What to Look For

### Service is Running Successfully ✅

**In Dashboard:**
- Status shows "ONLINE" in green
- Total Messages counter increasing
- Candle Events counter increasing
- Uptime timer counting up
- Data feed showing stock prices

**In Logs:**
- "Orchestrator service started successfully"
- "WebSocket server started on ws://localhost:8765"
- "Fetch cycle complete: 3 success, 0 failed"
- No ERROR messages

**In Command Line:**
```
✅ WebSocket server is RUNNING on ws://localhost:8765
📊 Service appears to be operational
```

### Service is NOT Running ❌

**In Dashboard:**
- Status shows "OFFLINE" in red
- All metrics show 0
- Empty data feed
- "Click Connect to start receiving data" message

**In Command Line:**
```
❌ WebSocket server is NOT running
🚀 To start the service: [instructions]
```

## Troubleshooting

### Dashboard shows "OFFLINE" but service is running

1. **Check if WebSocket port is accessible:**
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 8765
   ```

2. **Check firewall:**
   - Windows Firewall might be blocking port 8765
   - Add exception for Python or port 8765

3. **Restart service:**
   - Stop service (Ctrl+C in terminal)
   - Start again (`start_service.bat`)

### No data appearing in dashboard

1. **Check if publisher is active:**
   ```powershell
   Get-Content test_service.log | Select-String "Fetch cycle complete"
   ```

2. **Check for errors:**
   ```powershell
   Get-Content test_service.log | Select-String "ERROR"
   ```

3. **Verify internet connection:**
   - Service needs internet to fetch Yahoo Finance data
   - Check: `Test-NetConnection query1.finance.yahoo.com -Port 443`

### Port 8765 already in use

1. **Find process using the port:**
   ```powershell
   netstat -ano | findstr :8765
   # Note the PID (last column)
   ```

2. **Kill the process:**
   ```powershell
   taskkill /PID <PID> /F
   # Replace <PID> with actual number
   ```

3. **Or restart computer** (easier option)

## Quick Reference

| File | Purpose |
|------|---------|
| `start_service.bat` | Start the service |
| `view_dashboard.bat` | Open monitoring dashboard |
| `dashboard.html` | Live monitoring dashboard |
| `check_service_status.py` | Check service status |
| `test_service.log` | Service logs |
| `config\local_test.yaml` | Service configuration |

## Service Architecture

```
┌─────────────────────────────────────────┐
│     Yahoo Finance API (Data Source)     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      YahooFinancePublisher              │
│   (Fetches data every 10 seconds)       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│       InMemoryBroker (Event Bus)        │
└───┬─────────────────────────────────┬───┘
    │                                 │
    ▼                                 ▼
┌──────────────────┐      ┌──────────────────────┐
│  StateTracker    │      │   WebSocketServer    │
│  (In-memory)     │      │   (Port 8765)        │
└──────────────────┘      └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │   Your Dashboard     │
                          │   (Browser Client)   │
                          └──────────────────────┘
```

## Next Steps

1. **Start service** → `start_service.bat`
2. **Open dashboard** → `view_dashboard.bat`
3. **Watch magic happen** → Real-time market data streaming! 🎉

For more details, see:
- `QUICK_START.md` - Detailed testing guide
- `docs/DEPLOYMENT.md` - Production deployment
- `docs/API_REFERENCE.md` - API documentation
