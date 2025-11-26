# Quick Start - Testing Locally on Windows

This guide will help you test the Real-Time Yahoo Finance Service on your Windows desktop in under 10 minutes.

## Prerequisites

✅ Python 3.11+ installed  
✅ MySQL running (for DBWriter subscriber)  
✅ Internet connection (for Yahoo Finance API)

## Option 1: Minimal Test (No External Dependencies)

This is the fastest way to test - uses in-memory broker, no database needed.

### Step 1: Install Dependencies

```powershell
cd D:\MyProjects\StockScreeer\realtime_yahoo_service

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Create Test Configuration

Create `config\local_test.yaml`:

```yaml
broker:
  type: inmemory  # No Redis needed

serializer:
  type: json  # Simple and readable

dlq:
  enabled: true
  file_path: ./test_dlq

publishers:
  - id: yahoo_test
    type: yahoo_finance
    enabled: true
    symbols: ['AAPL', 'GOOGL', 'MSFT']  # Just 3 symbols for testing
    publish_interval: 10.0  # Every 10 seconds
    batch_size: 10
    rate_limit: 10
    rate_limit_period: 60.0

subscribers:
  - id: state_tracker
    type: state_tracker
    enabled: true
    
  - id: websocket
    type: websocket
    enabled: true
    host: localhost
    port: 8765

health:
  check_interval: 30
  restart_on_failure: false  # Manual control for testing

logging:
  level: INFO
  file: test_service.log
```

### Step 3: Run the Service

```powershell
python main.py --config config\local_test.yaml
```

You should see output like:
```
2025-11-26 10:00:00 - INFO - Starting OrchestratorService...
2025-11-26 10:00:00 - INFO - Starting publisher: yahoo_test
2025-11-26 10:00:00 - INFO - Starting subscriber: state_tracker
2025-11-26 10:00:00 - INFO - Starting subscriber: websocket
2025-11-26 10:00:01 - INFO - WebSocket server started on ws://localhost:8765
2025-11-26 10:00:10 - INFO - Published 3 candle events for AAPL, GOOGL, MSFT
```

### Step 4: Test WebSocket Connection

Open `examples\test_websocket_client.html` in your browser, or use PowerShell:

```powershell
# Install wscat if not already installed
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8765
```

You should start receiving real-time market data messages!

### Step 5: Stop the Service

Press `Ctrl+C` in the terminal running the service.

---

## Option 2: Full Test (With Database)

Test with MySQL database to verify complete functionality.

### Step 1: Setup Database

```powershell
# Connect to MySQL
mysql -u root -p

# Create database and table
CREATE DATABASE IF NOT EXISTS marketdata;
USE marketdata;

CREATE TABLE IF NOT EXISTS nse_equity_bhavcopy_full (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    series VARCHAR(10),
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    last_price DECIMAL(10,2),
    prev_close DECIMAL(10,2),
    total_traded_qty BIGINT,
    total_traded_value DECIMAL(20,2),
    timestamp_52w_high DATE,
    timestamp_52w_low DATE,
    ttl_trades BIGINT,
    isin VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY idx_trade_symbol (trade_date, symbol, series),
    INDEX idx_symbol (symbol),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Step 2: Create Configuration with Database

Create `config\local_full_test.yaml`:

```yaml
broker:
  type: inmemory

serializer:
  type: msgpack  # More efficient

dlq:
  enabled: true
  file_path: ./test_dlq
  max_retries: 3

publishers:
  - id: yahoo_full
    type: yahoo_finance
    enabled: true
    symbols: ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    publish_interval: 10.0
    batch_size: 10

subscribers:
  - id: state_tracker
    type: state_tracker
    enabled: true
    
  - id: db_writer
    type: db_writer
    enabled: true
    db_url: mysql+pymysql://root:your_password@localhost/marketdata
    batch_size: 100
    
  - id: market_breadth
    type: market_breadth
    enabled: true
    
  - id: trend_analyzer
    type: trend_analyzer
    enabled: true
    
  - id: websocket
    type: websocket
    enabled: true
    host: localhost
    port: 8765

health:
  check_interval: 30
  restart_on_failure: true
  max_restart_attempts: 3

logging:
  level: INFO
  file: full_test_service.log
```

**Important**: Replace `your_password` with your MySQL root password.

### Step 3: Run Full Test

```powershell
python main.py --config config\local_full_test.yaml
```

### Step 4: Verify Database Writes

```sql
-- In MySQL
USE marketdata;
SELECT * FROM nse_equity_bhavcopy_full ORDER BY created_at DESC LIMIT 10;
```

### Step 5: Check Market Breadth

Create a test script `test_market_breadth.py`:

```python
import asyncio
from broker.inmemory_broker import InMemoryBroker
from subscribers.market_breadth import MarketBreadthSubscriber

async def test_breadth():
    broker = InMemoryBroker()
    breadth = MarketBreadthSubscriber("test_breadth", broker)
    
    await breadth.start()
    await asyncio.sleep(30)  # Wait for data
    
    metrics = breadth.get_metrics()
    print(f"Advancing: {metrics.get('advancing', 0)}")
    print(f"Declining: {metrics.get('declining', 0)}")
    print(f"Unchanged: {metrics.get('unchanged', 0)}")
    
    await breadth.stop()

if __name__ == "__main__":
    asyncio.run(test_breadth())
```

Run it:
```powershell
python test_market_breadth.py
```

---

## Option 3: Run Existing Tests

The fastest way to verify everything works:

```powershell
# Run all tests
pytest tests\ -v

# Run just integration tests
pytest tests\integration\ -v

# Run with coverage report
pytest tests\ --cov=. --cov-report=html
start htmlcov\index.html
```

Expected output:
```
tests\test_serializers.py::test_json_serializer PASSED
tests\test_brokers.py::test_inmemory_broker PASSED
tests\test_yahoo_publisher.py::test_fetch_data PASSED
...
======================== 146 passed in 45.23s =========================
```

---

## Quick Verification Checklist

After starting the service, verify these things are working:

### 1. Publisher is Running
```powershell
# Check logs
Get-Content test_service.log -Tail 20 -Wait
```

Look for: `Published X candle events`

### 2. WebSocket is Accessible
```powershell
# Test connection
Test-NetConnection -ComputerName localhost -Port 8765
```

Should show: `TcpTestSucceeded : True`

### 3. Data is Being Processed
Create `check_stats.py`:

```python
import asyncio
from orchestrator.orchestrator import OrchestratorService

async def check():
    # This would connect to running service
    # For now, check log file
    with open('test_service.log', 'r') as f:
        lines = f.readlines()[-10:]
        for line in lines:
            print(line.strip())

asyncio.run(check())
```

### 4. Database Writes (if enabled)
```sql
SELECT COUNT(*) as total_records FROM nse_equity_bhavcopy_full;
SELECT symbol, MAX(created_at) as last_update 
FROM nse_equity_bhavcopy_full 
GROUP BY symbol;
```

---

## Common Issues and Solutions

### Issue: "ModuleNotFoundError: No module named 'xyz'"

**Solution:**
```powershell
# Make sure virtual environment is activated
.\venv\Scripts\activate

# Reinstall requirements
pip install -r requirements.txt
```

### Issue: "Address already in use" (WebSocket port 8765)

**Solution:**
```powershell
# Find process using port
netstat -ano | findstr :8765

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F

# Or use a different port in config
```

### Issue: MySQL Connection Failed

**Solution:**
```powershell
# Check MySQL is running
Get-Service MySQL*

# Start if stopped
Start-Service MySQL80

# Test connection
mysql -u root -p -e "SELECT 1"
```

### Issue: No Data Being Published

**Solution:**
1. Check internet connection
2. Verify Yahoo Finance is accessible: `curl https://query1.finance.yahoo.com`
3. Check rate limits in config (might be too restrictive)
4. Look for errors in logs: `Get-Content test_service.log | Select-String "ERROR"`

### Issue: WebSocket Not Receiving Data

**Solution:**
```powershell
# Check WebSocket server is running
Get-Content test_service.log | Select-String "WebSocket"

# Verify publisher is sending data
Get-Content test_service.log | Select-String "Published"

# Test with simple client
wscat -c ws://localhost:8765
```

---

## Performance Testing

Test with more symbols and higher frequency:

```yaml
publishers:
  - id: yahoo_stress_test
    symbols: ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'INTC']
    publish_interval: 5.0  # Every 5 seconds
    batch_size: 50
```

Monitor performance:
```powershell
# Watch CPU and memory
Get-Process python | Select-Object CPU, PM, WS, ProcessName

# Monitor logs in real-time
Get-Content test_service.log -Tail 50 -Wait
```

---

## Next Steps After Testing

1. **Review logs** - Check for any errors or warnings
2. **Check database** - Verify data quality and completeness
3. **Test WebSocket clients** - Ensure real-time updates work
4. **Monitor performance** - CPU, memory, network usage
5. **Adjust configuration** - Tune batch sizes, intervals based on needs

---

## Quick Commands Reference

```powershell
# Start service
python main.py --config config\local_test.yaml

# Run tests
pytest tests\ -v

# Check service health
Get-Process python

# View logs
Get-Content test_service.log -Tail 20 -Wait

# Test WebSocket
wscat -c ws://localhost:8765

# Check database
mysql -u root -p marketdata -e "SELECT COUNT(*) FROM nse_equity_bhavcopy_full"

# Stop service
# Press Ctrl+C
```

---

## Production Deployment

Once local testing is successful, see `docs\DEPLOYMENT.md` for production setup with:
- Redis broker for distributed deployment
- Systemd service for auto-start
- Log rotation and monitoring
- Security hardening
