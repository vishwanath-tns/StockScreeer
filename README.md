# 📈 StockScreener - Real-Time Market Analysis Platform

> **🚀 Launch Everything:** `python launcher.py` - Central launcher with all features!
> **📊 Progress Tracking:** Check [TODAY.md](TODAY.md) to see what's been done!

---

## 🎯 What is This?

A comprehensive stock market analysis platform focused on NSE stocks with:
- ✅ Real-time advance-decline tracking
- ✅ Historical data management (Yahoo Finance + NSE BHAV)
- ✅ Technical indicators and pattern detection
- ✅ Central launcher GUI for all features
- ✅ Automated daily progress tracking

**Current Status:** 114 active Python files, 183 archived, 881K+ daily quotes, tracking 1,049 symbols

---

## 🚀 Quick Start

### First Time Setup

1. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Configure Database**
   - Set environment variables in `.env`:
     ```
     MYSQL_HOST=localhost
     MYSQL_PORT=3306
     MYSQL_DB=stock_data
     MYSQL_USER=your_user
     MYSQL_PASSWORD=your_password
     ```

3. **Read the Index**
   ```powershell
   cat MASTER_INDEX.md
   ```

### Daily Usage

1. **🚀 Launch Everything (NEW!)**
   ```powershell
   python launcher.py
   ```
   Opens central GUI with all features organized by category!

2. **Check Yesterday's Work**
   ```powershell
   python start_work.py
   # Or: cat TODAY.md
   ```

3. **Download Latest Data** (before market)
   ```powershell
   python quick_download_nifty500.py
   ```

4. **Start Real-Time Dashboard**
   ```powershell
   python realtime_adv_decl_dashboard.py
   ```

5. **Log Your Work**
   ```powershell
   python log.py
   ```

---

## 📚 Documentation

### Essential Docs (Read These First)
1. **[QUICKSTART.md](QUICKSTART.md)** - Daily commands and workflows
2. **[MASTER_INDEX.md](MASTER_INDEX.md)** - Complete project reference
3. **[TODAY.md](TODAY.md)** - Today's activity log

### Progress Tracking
- **[DAILY_PROGRESS/](DAILY_PROGRESS/)** - Historical logs (one per day)
- Run `python progress_tracker.py` to see recent activity

### Advanced
- **[PROJECT_CLEANUP_PLAN.md](PROJECT_CLEANUP_PLAN.md)** - Full reorganization strategy
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Dev guidelines

---

## 🎮 Main Features

### 1. Real-Time Dashboard
**File:** `realtime_adv_decl_dashboard.py`
- Live advance/decline/unchanged tracking
- 500 Nifty stocks monitored
- Updates every minute
- Stores 1-min candle data

### 2. Data Management
**Files:** `quick_download_nifty500.py`, `sync_bhav_gui.py`
- Yahoo Finance historical data
- NSE BHAV official data
- Automated duplicate prevention
- Bulk update support

### 3. Progress Tracking (NEW!)
**Files:** `progress_tracker.py`, `log.py`
- Automatic daily logs
- Searchable history
- Category tagging
- Quick CLI tool

---

## 📊 Project Structure

```
StockScreener/
├── 📄 README.md                      ← You are here
├── 📄 QUICKSTART.md                  ← Daily commands
├── 📄 MASTER_INDEX.md                ← Complete reference
├── 📄 TODAY.md                       ← Today's progress
├── 📄 PROGRESS_HUB.py                ← Current status (Todo Tree!) ⭐
│
├── 🚀 launcher.py                    ← CENTRAL LAUNCHER (start here!) ⭐
├── 🐍 realtime_adv_decl_dashboard.py ← Market dashboard
├── 🐍 quick_download_nifty500.py     ← Data downloader
├── 🐍 sync_bhav_gui.py               ← BHAV importer
├── 🐍 progress_tracker.py            ← Progress logger
├── 🐍 start_work.py                  ← Morning summary ⭐
├── 🐍 ai_context.py                  ← AI context loader ⭐
│
├── 📁 DAILY_PROGRESS/                ← Historical logs
├── 📁 archive/                       ← Archived files (183 files) ⭐
│   ├── test_files/                   ← 67 test files
│   ├── check_files/                  ← 32 check files
│   ├── demo_files/                   ← 11 demo files
│   ├── duplicate_vcp/                ← 17 VCP duplicates
│   ├── duplicate_report/             ← 8 report duplicates
│   └── ...
│
├── 📁 volatility_patterns/           ← VCP module (canonical)
├── 📁 realtime_market_breadth/       ← Dashboard components
├── 📁 services/                      ← Shared utilities
└── 📁 vedic_astrology/               ← Analysis features
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=stock_data
MYSQL_USER=root
MYSQL_PASSWORD=your_password

# BHAV Data Location
BHAV_FOLDER=D:\path\to\bhav\files
```

### Database Tables
- `yfinance_daily_quotes` - Yahoo Finance data (881K+ records)
- `nse_equity_bhavcopy_full` - NSE BHAV data
- `imports_log` - Track imported files
- See [MASTER_INDEX.md](MASTER_INDEX.md#-database-schema) for complete schema

---

## 📝 Daily Workflow Example

```powershell
# Morning: Check yesterday's work
cat TODAY.md

# Morning: Update data before market
python quick_download_nifty500.py
python log.py modify "downloaded data" "Updated prev_close for all 500 stocks" database

# During market: Run dashboard
python realtime_adv_decl_dashboard.py

# During dev: Create new feature
code new_scanner.py
# ... write code ...
python log.py create "new_scanner.py" "Created volatility scanner using ATR" feature

# Afternoon: Fix a bug
code dashboard.py
# ... fix bug ...
python log.py fix "dashboard.py" "Fixed memory leak in candle processor" bugfix

# Evening: Review day's work
cat DAILY_PROGRESS\2025-11-28_progress.md
```

---

## 🐛 Troubleshooting

### Dashboard shows 0/0/0
**Cause:** Missing previous close data  
**Fix:**
```powershell
python quick_download_nifty500.py
```

### Import errors
**Cause:** Module not in Python path  
**Fix:**
```powershell
# Run from project root
cd D:\MyProjects\StockScreeer
python your_script.py
```

### Database connection failed
**Cause:** Wrong credentials or MySQL not running  
**Fix:**
1. Check `.env` file
2. Verify MySQL is running
3. Test connection:
   ```powershell
   python -c "from services.market_breadth_service import get_engine; get_engine()"
   ```

See [MASTER_INDEX.md](MASTER_INDEX.md#-troubleshooting) for more solutions.

---

## 📊 Statistics

| Metric | Value |
|--------|-------|
| Active Python Files | 114 |
| Archived Files | 183 |
| Database Records | 881,552+ |
| Symbols Tracked | 1,049 |
| Latest Data | Nov 28, 2025 |

---

## 🎯 Project Status

### ✅ Completed (Nov 28, 2025)
- ✅ Created central launcher GUI (`launcher.py`)
- ✅ Archived 136 test/demo/debug files
- ✅ Consolidated 47 duplicate files
- ✅ Created progress tracking system
- ✅ VS Code Todo Tree integration
- ✅ Updated all documentation

### Canonical Files (Use These!)
| Category | File | Purpose |
|----------|------|---------|
| **Launcher** | `launcher.py` | Start here! |
| **Dashboard** | `realtime_adv_decl_dashboard.py` | Market tracking |
| **Download** | `quick_download_nifty500.py` | Get latest data |
| **BHAV** | `sync_bhav_gui.py` | NSE official data |
| **Progress** | `PROGRESS_HUB.py` | View in Todo Tree |
| **Charts** | `chart_window.py` | Stock charts |
| **VCP** | `volatility_patterns/` | Pattern detection |

---

## 📞 Getting Help

1. **Lost?** → Read [QUICKSTART.md](QUICKSTART.md)
2. **Need feature info?** → Check [MASTER_INDEX.md](MASTER_INDEX.md)
3. **What did I do?** → View [TODAY.md](TODAY.md)
4. **Week's progress?** → Browse [DAILY_PROGRESS/](DAILY_PROGRESS/)

---

## 🎓 Learning Resources

### Understanding the Code
- Read copilot-instructions.md for architecture overview
- Check MASTER_INDEX.md for database schema
- Look at existing scripts in DAILY_PROGRESS logs

### Development Workflow
1. Always log your changes: `python log.py`
2. Update MASTER_INDEX.md when adding main features
3. Run data download before testing dashboard
4. Check TODAY.md daily to track progress

---

**Made with ❤️ for Stock Market Analysis**

*Last Updated: November 28, 2025*
