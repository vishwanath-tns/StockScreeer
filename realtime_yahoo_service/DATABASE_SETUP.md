# Database Storage Configuration

## ⚠️ IMPORTANT: Separate Tables for Different Data Sources

This real-time Yahoo Finance service uses a **dedicated table** separate from existing NSE data:

### Tables and Their Purpose:

| Table Name | Purpose | Data Source |
|------------|---------|-------------|
| `nse_equity_bhavcopy_full` | ❌ **DO NOT USE** | NSE BHAV copy historical data |
| `realtime_market_data` | ✅ **USE THIS** | Yahoo Finance real-time streaming |

## Setup Instructions

### 1. Create the Database Table

Run the SQL script to create the dedicated table:

```bash
mysql -u root -p your_database < schema/realtime_market_data.sql
```

Or manually execute:
```sql
CREATE TABLE realtime_market_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    series VARCHAR(10) DEFAULT 'EQ',
    trade_date DATE NOT NULL,
    prev_close DECIMAL(20, 4) NOT NULL,
    open_price DECIMAL(20, 4) NOT NULL,
    high_price DECIMAL(20, 4) NOT NULL,
    low_price DECIMAL(20, 4) NOT NULL,
    close_price DECIMAL(20, 4) NOT NULL,
    volume BIGINT DEFAULT 0,
    deliv_qty BIGINT DEFAULT NULL,
    deliv_per DECIMAL(10, 2) DEFAULT NULL,
    timestamp BIGINT NOT NULL,
    data_source VARCHAR(50) DEFAULT 'yahoo_finance',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_symbol_date (symbol, trade_date, timestamp),
    INDEX idx_symbol (symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol_date (symbol, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. Configure Database Connection

Edit `config/local_test_with_db.yaml`:

```yaml
subscribers:
  - id: db_writer
    type: db_writer
    enabled: true
    db_url: "mysql+pymysql://YOUR_USER:YOUR_PASSWORD@localhost:3306/YOUR_DATABASE"
    table_name: realtime_market_data  # ✅ Dedicated table
    batch_size: 50
```

### 3. Run Service with Database Storage

```bash
python main.py --config config/local_test_with_db.yaml
```

## Data Flow

```
Yahoo Finance API
       ↓
  Publisher (fetch every 10s)
       ↓
  Event Broker (in-memory)
       ↓
  ├─ WebSocket Subscriber → Dashboard (real-time display)
  ├─ State Tracker → In-memory state
  └─ DB Writer → MySQL (realtime_market_data table)
```

## Querying the Data

### Get latest prices:
```sql
SELECT symbol, close_price, volume, trade_date, 
       FROM_UNIXTIME(timestamp) as fetch_time
FROM realtime_market_data
WHERE trade_date = CURDATE()
ORDER BY timestamp DESC;
```

### Get price history for a symbol:
```sql
SELECT trade_date, open_price, high_price, low_price, close_price, volume
FROM realtime_market_data
WHERE symbol = 'GC=F'
ORDER BY trade_date DESC, timestamp DESC
LIMIT 30;
```

### Get all futures data:
```sql
SELECT symbol, close_price, 
       ((close_price - prev_close) / prev_close * 100) as change_pct,
       volume,
       FROM_UNIXTIME(timestamp) as last_update
FROM realtime_market_data
WHERE symbol LIKE '%=F'
  AND trade_date = CURDATE()
GROUP BY symbol
ORDER BY timestamp DESC;
```

## Table Separation Benefits

✅ **Isolation**: Real-time data separate from historical BHAV copies
✅ **No Conflicts**: Different schemas and update patterns
✅ **Data Integrity**: NSE data remains untouched
✅ **Performance**: Separate indexes optimized for each use case
✅ **Flexibility**: Can delete/truncate real-time data without affecting historical records

## Monitoring

Check if data is being written:
```sql
SELECT COUNT(*) as total_records, 
       COUNT(DISTINCT symbol) as unique_symbols,
       MAX(FROM_UNIXTIME(timestamp)) as last_update
FROM realtime_market_data
WHERE trade_date = CURDATE();
```

## Maintenance

### Clear old data (optional):
```sql
-- Delete data older than 30 days
DELETE FROM realtime_market_data 
WHERE trade_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY);
```

### Optimize table:
```sql
OPTIMIZE TABLE realtime_market_data;
```
