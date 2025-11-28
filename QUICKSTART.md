# 🎯 Quick Reference - Essential Commands

> **Jump to:** [TODAY.md](TODAY.md) | [MASTER_INDEX.md](MASTER_INDEX.md) | [DAILY_PROGRESS/](DAILY_PROGRESS/)

---

## 📝 Daily Progress Logging

### Quick Log (One-liner)
```powershell
# From anywhere in the project
python log.py create "new_file.py" "What you did and why" feature
```

### Interactive Log
```powershell
python log.py
# Follow the prompts
```

### From Code
```python
from progress_tracker import log_progress

log_progress("modify", "dashboard.py", "Fixed calculation bug", "bugfix")
```

---

## 🚀 Daily Workflow

### Morning Routine (Before Market)
```powershell
# 1. Check what you did yesterday
cat TODAY.md

# 2. Download latest market data
python quick_download_nifty500.py

# 3. Log it
python log.py modify "quick_download_nifty500.py" "Downloaded latest data" database

# 4. Start dashboard
python realtime_adv_decl_dashboard.py
```

### During Development
```powershell
# Create new file
# ... do your work ...

# Log it immediately
python log.py create "my_new_feature.py" "Added X feature for Y purpose" feature
```

### End of Day
```powershell
# Review today's work
cat DAILY_PROGRESS\2025-11-28_progress.md

# Add summary to top of file (optional)
code DAILY_PROGRESS\2025-11-28_progress.md
```

---

## 📊 View Progress

### Today
```powershell
cat TODAY.md
```

### This Week
```powershell
ls DAILY_PROGRESS
# Opens folder to see all logs
```

### Search Progress
```powershell
# Find all times you worked on a file
Select-String -Path "DAILY_PROGRESS\*.md" -Pattern "dashboard.py"

# Find all bugfixes
Select-String -Path "DAILY_PROGRESS\*.md" -Pattern "Category: bugfix"
```

---

## 🗂️ File Locations

### Documentation
- **MASTER_INDEX.md** - Complete project reference
- **TODAY.md** - Today's activity (auto-updated)
- **DAILY_PROGRESS/** - Historical logs (one file per day)

### Main Applications
- `realtime_adv_decl_dashboard.py` - Live market dashboard
- `quick_download_nifty500.py` - Data downloader
- `sync_bhav_gui.py` - BHAV data importer

### Utilities
- `progress_tracker.py` - Progress tracking core
- `log.py` - Quick logger CLI
- `check_data_size.py` - Database stats

---

## 💡 Tips

1. **Log as you go** - Don't wait until end of day
2. **Be specific** - "Fixed bug" → "Fixed advance-decline showing 0/0/0 by downloading prev_close data"
3. **Use categories** - Makes it easy to find feature work vs bugfixes later
4. **Check TODAY.md daily** - See what you accomplished
5. **Review weekly** - Look at DAILY_PROGRESS folder on Fridays

---

## 🔍 Examples

### Log a new feature
```powershell
python log.py create "volatility_scanner.py" "Created scanner to detect high volatility stocks based on ATR" feature
```

### Log a bug fix
```powershell
python log.py fix "dashboard.py" "Fixed memory leak in candle queue processor" bugfix
```

### Log cleanup work
```powershell
python log.py cleanup "ARCHIVE/" "Moved 115 test files to archive folder" cleanup
```

### Log database work
```powershell
python log.py modify "schema.sql" "Added indexes on symbol and date columns for faster queries" database
```

---

**Start here:** Run `python log.py` to log your first entry!
