# NSE Block & Bulk Deals Downloader

Complete module for downloading and storing NSE Block and Bulk Deals data with anti-bot protection.

## Features

✅ **Anti-Bot Protection**
- Rotating User-Agents
- Random rate limiting variations
- Session cookie management
- Proper HTTP headers (Referer, sec-ch-ua, etc.)
- Periodic header updates

✅ **Data Management**
- MySQL database storage
- Duplicate prevention (unique constraints)
- Import logging
- Skip already downloaded dates
- Upsert logic for updates

✅ **User Interface**
- Tkinter GUI with progress tracking
- Real-time download logs
- Statistics viewer
- Date range selection
- Configurable rate limiting

## Installation

1. **Database Setup**
```bash
# Run the SQL setup script
python -c "from sync_bhav_gui import engine; sql=open('block_bulk_deals/setup_tables.sql').read(); conn=engine().connect(); [conn.execute(s) for s in sql.split(';') if s.strip()]; conn.close()"
```

Or manually:
```bash
mysql -u root -p marketdata < block_bulk_deals/setup_tables.sql
```

2. **Environment Variables** (already configured in your `.env`)
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=marketdata
MYSQL_USER=root
MYSQL_PASSWORD=your_password
```

## Usage

### GUI Application (Recommended)

```bash
python block_bulk_deals/sync_deals_gui.py
```

**Features:**
- Select date range (From/To)
- Choose deal types (Block/Bulk or both)
- Set rate limit (default: 2.0 seconds)
- Skip existing dates
- Real-time progress and logs
- View statistics

### Programmatic Usage

```python
from block_bulk_deals.nse_deals_downloader import NSEDealsDownloader, NSEDealsDatabase
from datetime import datetime

# Initialize
downloader = NSEDealsDownloader(rate_limit=2.0)
database = NSEDealsDatabase()

# Download for a specific date
date = datetime(2024, 11, 20)

# Block deals
block_df = downloader.download_block_deals(date)
if block_df is not None and not block_df.empty:
    new, updated = database.save_deals(block_df, "BLOCK")
    print(f"Saved {new} block deals")

# Bulk deals
bulk_df = downloader.download_bulk_deals(date)
if bulk_df is not None and not bulk_df.empty:
    new, updated = database.save_deals(bulk_df, "BULK")
    print(f"Saved {new} bulk deals")

# Get statistics
stats = database.get_import_stats()
print(stats)

# Cleanup
downloader.close()
```

## Database Schema

### Tables

1. **nse_block_deals**
   - Block deals (5 lakh+ shares)
   - Columns: trade_date, symbol, security_name, client_name, deal_type, quantity, trade_price, remarks
   - Unique constraint prevents duplicates

2. **nse_bulk_deals**
   - Bulk deals (≥0.5% of equity)
   - Same structure as block_deals

3. **block_bulk_deals_import_log**
   - Import history
   - Tracks success/failure per date per category

### Views

- `vw_top_block_clients` - Top clients by value
- `vw_top_bulk_clients` - Top clients by value
- `vw_recent_block_deals` - Last 30 days
- `vw_recent_bulk_deals` - Last 30 days
- `vw_symbol_block_summary` - Per-symbol aggregates
- `vw_symbol_bulk_summary` - Per-symbol aggregates

## Anti-Bot Protection Details

### 1. User-Agent Rotation
Randomly selects from 5 modern browser User-Agents:
- Chrome 120, 119
- Firefox 121
- Edge 120
- Safari (Mac)

### 2. Headers
Complete set of modern browser headers:
```python
'Accept': 'application/json, text/plain, */*'
'Accept-Language': 'en-US,en;q=0.9'
'Accept-Encoding': 'gzip, deflate, br'
'Referer': 'https://www.nseindia.com/market-data/bulk-block-deals'
'X-Requested-With': 'XMLHttpRequest'
'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"'
'Sec-Fetch-Mode': 'cors'
'Sec-Fetch-Site': 'same-origin'
```

### 3. Rate Limiting
- Configurable delay between requests (default: 2.0s)
- Enforced wait time prevents too-frequent requests
- Recommended: 2-3 seconds for safety

### 4. Cookie Management
- Fresh cookies obtained from homepage
- 10% chance to refresh cookies during download
- Session persistence

### 5. Random Variations
- 20% chance to update headers during download
- Natural variation in request patterns

## Download Recommendations

### For Historical Download (5 years)
- **Rate Limit:** 2.5-3.0 seconds
- **Time Required:** ~4-5 hours for 1,250 trading days
- **Best Time:** During off-market hours (evenings, weekends)
- **Batch Size:** Download 1 year at a time

### For Daily Updates
- **Rate Limit:** 2.0 seconds is fine
- **Time Required:** ~10 seconds per day
- **Schedule:** After 6 PM IST when data is finalized

## Sample Queries

```sql
-- Recent block deals
SELECT * FROM vw_recent_block_deals LIMIT 20;

-- Top clients
SELECT * FROM vw_top_block_clients LIMIT 10;

-- Deals for specific symbol
SELECT * FROM nse_block_deals 
WHERE symbol = 'RELIANCE' 
ORDER BY trade_date DESC 
LIMIT 20;

-- Daily summary
SELECT 
    trade_date,
    COUNT(*) as deals,
    SUM(quantity * trade_price) / 10000000 as value_cr
FROM nse_block_deals
WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY trade_date
ORDER BY trade_date DESC;

-- Import status
SELECT * FROM block_bulk_deals_import_log
ORDER BY trade_date DESC
LIMIT 20;
```

## Troubleshooting

### HTTP 403 Errors
- Increase rate limit to 3-4 seconds
- Check if NSE website is accessible
- Verify User-Agent is modern

### Empty Results
- Verify date is a trading day (not holiday/weekend)
- Some dates may genuinely have no deals
- Check NSE website directly to confirm

### Connection Errors
- Check MySQL credentials in `.env`
- Verify database `marketdata` exists
- Ensure tables are created

### Slow Downloads
- Normal for large date ranges
- 1 year = ~250 days × 2.5s = ~10 minutes
- Run during off-hours for better success

## API Endpoints Used

```
Block Deals:
GET https://www.nseindia.com/api/block-deal?from=DD-MM-YYYY&to=DD-MM-YYYY

Bulk Deals:
GET https://www.nseindia.com/api/bulk-deal?from=DD-MM-YYYY&to=DD-MM-YYYY
```

## Notes

- NSE limits API access - respect rate limits
- Data is finalized after market close (~6 PM IST)
- Holidays and weekends are automatically skipped
- Duplicate records are handled via unique constraints
- The module is completely separate from main codebase

## License

Part of Stock Screener project.
