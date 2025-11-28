# 📚 Master Index - StockScreeer Project

> **Last Updated:** November 28, 2025  
> **Active Files:** 114 Python files (183 archived)  
> **Status:** ✅ Reorganized & Clean!

---

## 🚀 START HERE: Central Launcher

```powershell
python launcher.py
```

Opens a **GUI launcher** with all features organized by category:
- 📊 Dashboards
- 📥 Data Download  
- 🔍 Scanners
- 📈 Charts & Analysis
- 📑 Reports
- 🛠️ Utilities
- 🔮 Vedic Astrology

---

## 📁 Project Organization

### Active Files (114)
| Category | Key Files | Purpose |
|----------|-----------|---------|
| **Launcher** | `launcher.py` | Central GUI for everything |
| **Dashboard** | `realtime_adv_decl_dashboard.py` | Live market tracking |
| **Download** | `quick_download_nifty500.py` | Bulk data download |
| **BHAV** | `sync_bhav_gui.py` | NSE official data import |
| **Progress** | `PROGRESS_HUB.py`, `progress_tracker.py` | Track all changes |
| **Charts** | `chart_window.py`, `chart_tool.py` | Stock visualization |
| **VCP** | `volatility_patterns/` | Pattern detection module |

### Archived Files (183)
All test, demo, debug, and duplicate files moved to `archive/`:
- `archive/test_files/` - 67 test files
- `archive/check_files/` - 32 check files
- `archive/demo_files/` - 11 demo files
- `archive/duplicate_vcp/` - 17 VCP duplicates
- `archive/duplicate_report/` - 8 report duplicates
- `archive/duplicate_download/` - 7 download duplicates
- `archive/duplicate_scanner/` - 7 scanner duplicates

---

## 🎯 Main Applications

### 1. Real-Time Market Dashboard
**File:** `realtime_adv_decl_dashboard.py`  
**Purpose:** Live advance-decline tracking for Nifty 500 stocks  
**How to Run:**
```powershell
python realtime_adv_decl_dashboard.py
```
**Features:**
- Real-time advance/decline/unchanged counts
- Live price updates from Yahoo Finance
- 1-minute candle data storage
- Historical breadth tracking

**Dependencies:** MySQL database with previous close data

---

### 2. Data Download Service
**File:** `quick_download_nifty500.py`  
**Purpose:** Bulk download historical data for all Nifty 500 stocks  
**How to Run:**
```powershell
python quick_download_nifty500.py
```
**Features:**
- Downloads last 7 days of data by default
- Handles 500 stocks efficiently
- Updates existing records
- Shows progress with timing

**Use When:** Need to update historical data (run daily before market hours)

---

### 3. BHAV Data Sync (NSE Official Data)
**File:** `sync_bhav_gui.py`  
**Purpose:** Import NSE BHAV copy files (CSV/ZIP) into database  
**How to Run:**
```powershell
$env:BHAV_FOLDER = 'path\to\bhav\files'
python sync_bhav_gui.py
```
**Features:**
- GUI-based file selection
- MD5 checksum tracking (avoid duplicates)
- Upsert logic (updates existing records)
- Validates trade dates

**Use When:** NSE releases new BHAV data files

---

## 📊 Database Schema

### Main Tables

#### `yfinance_daily_quotes`
**Purpose:** Historical daily OHLCV data from Yahoo Finance  
**Records:** 881,552+ rows  
**Symbols:** 1,049 unique stocks  
**Key Columns:**
- `symbol` (VARCHAR) - e.g., "RELIANCE.NS"
- `date` (DATE) - Trading date
- `open`, `high`, `low`, `close` (DECIMAL)
- `volume` (BIGINT)

#### `nse_equity_bhavcopy_full`
**Purpose:** Official NSE BHAV copy data  
**Key Columns:**
- `trade_date` (DATE)
- `symbol` (VARCHAR) - e.g., "RELIANCE"
- `series` (VARCHAR) - e.g., "EQ"
- `open_price`, `high_price`, `low_price`, `close_price`
- `deliv_qty`, `deliv_per` - Delivery data

#### `imports_log`
**Purpose:** Track imported BHAV files to prevent duplicates  
**Key Columns:**
- `trade_date` (DATE) - UNIQUE key
- `file_checksum` (VARCHAR) - MD5 hash
- `import_timestamp`

---

## 🔧 Utility Scripts

### Symbol Management
- `check_nifty500_symbol_mapping.py` - Verify Yahoo Finance symbol mappings
- `available_stocks_list.py` - Get list of stocks with data
- `auto_map_nifty500_to_yahoo.py` - Auto-map NSE symbols to Yahoo format

### Data Validation
- `check_data_size.py` - Check database size and record counts
- `complete_all_durations_report.py` - Data completeness analysis
- `check_table_structure.py` - Verify table schemas

### Database Operations
- `compute_moving_averages.py` - Calculate technical indicators
- `backfill_counts.py` - Fill missing data gaps
- `cleanup_and_import.py` - Clean and import bulk data

---

## 📁 Project Structure

### Core Directories

```
StockScreeer/
├── realtime_market_breadth/     # Real-time dashboard components
│   ├── core/                    # Data fetcher, calculator
│   ├── services/                # Background services
│   └── ui/                      # GUI components
│
├── yahoo_finance_service/       # Yahoo Finance data download
│   ├── download_service.py      # Main download logic
│   └── launch_downloader.py     # Launcher script
│
├── services/                    # Shared services
│   ├── market_breadth_service.py
│   └── realtime_data_fetcher.py
│
├── gui/                         # GUI applications
├── vedic_astrology/             # Astrological analysis features
├── volatility_patterns/         # Pattern detection
├── bhav_data/                   # Sample BHAV files
│
└── DAILY_PROGRESS/              # 📝 Daily progress logs (NEW)
```

---

## 🎯 Common Workflows

### Daily Routine (Before Market)
1. Download latest data:
   ```powershell
   python quick_download_nifty500.py
   ```
2. Verify data:
   ```powershell
   python check_data_size.py
   ```
3. Start dashboard:
   ```powershell
   python realtime_adv_decl_dashboard.py
   ```

### Weekly Maintenance
1. Import NSE BHAV files:
   ```powershell
   python sync_bhav_gui.py
   ```
2. Run completeness report:
   ```powershell
   python complete_all_durations_report.py
   ```
3. Archive old logs (manual)

---

## 🐛 Troubleshooting

### Dashboard Shows 0/0/0
**Problem:** All stocks showing prev_close=None  
**Solution:**
```powershell
# Download missing historical data
python quick_download_nifty500.py

# Verify data exists
python -c "from services.market_breadth_service import get_engine; import pandas as pd; eng = get_engine(); print(pd.read_sql('SELECT COUNT(*), MAX(date) FROM yfinance_daily_quotes', eng))"
```

### BHAV Import Fails
**Problem:** Column mismatch or parse errors  
**Check:**
- File format (CSV or ZIP containing CSV)
- Column names match COLMAP in `sync_bhav_gui.py`
- Table `nse_equity_bhavcopy_full` exists with correct schema

### Slow Database Queries
**Solution:**
- Check indexes on `symbol` and `date` columns
- Run `ANALYZE TABLE` for query optimization
- Consider partitioning large tables

---

## 📈 Statistics (As of Nov 28, 2025)

### Codebase
- **Total Python Files:** 566
- **Production Code:** 354 files (62%)
- **Test Files:** 115 files (20%)
- **Check/Validation:** 38 files (7%)
- **Demo Scripts:** 18 files (3%)
- **Other:** 41 files (7%)

### Database
- **Total Records:** 881,552+ daily quotes
- **Symbols Tracked:** 1,049 unique stocks
- **Date Range:** Multiple years of historical data
- **Latest Data:** November 27, 2025

### Recent Fixes
- ✅ Fixed advance-decline dashboard (Nov 28)
- ✅ Downloaded missing prev_close data (Nov 28)
- ✅ Created progress tracking system (Nov 28)
- ✅ Created master index (Nov 28)

---

## 📝 Progress Tracking

### Today's Progress
[View TODAY.md](TODAY.md) - Always shows current day's activity

### Weekly Progress
- [View DAILY_PROGRESS folder](DAILY_PROGRESS/) - All daily logs

### How to Log Progress
```python
from progress_tracker import log_progress

# Automatically log any change
log_progress("create", "new_file.py", "What it does and why", category="feature")
```

---

## 🔗 Related Documentation

- [PROJECT_CLEANUP_PLAN.md](PROJECT_CLEANUP_PLAN.md) - Full reorganization strategy
- [copilot-instructions.md](.github/copilot-instructions.md) - Development guidelines
- [DAILY_PROGRESS/](DAILY_PROGRESS/) - Historical progress logs

---

## 💡 Tips

1. **Always log changes:** Use `progress_tracker.py` to document what you do
2. **Check TODAY.md daily:** See what was done today
3. **Run data download before market:** Ensure prev_close data is current
4. **Keep this index updated:** Add new main features here
5. **Use descriptive names:** When creating new files, use clear names

---

**Need help?** Check [TODAY.md](TODAY.md) to see recent changes, or review [DAILY_PROGRESS](DAILY_PROGRESS/) folder for historical context.
