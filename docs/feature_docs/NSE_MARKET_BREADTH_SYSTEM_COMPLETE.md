# ✅ NSE Market Breadth Advance-Decline System - COMPLETE

## System Summary

**Purpose:** Interactive visualization of NSE market breadth using advance-decline analysis

**Data Sources:**
- **Stock Data:** 779 NSE stocks from `yfinance_daily_quotes` table
- **Index Data:** NIFTY index (1,459 records: 2020-01-01 to 2025-11-21) from Yahoo Finance
- **Breadth Data:** Computed advance-decline counts stored in `nifty500_advance_decline` table

---

## System Components

### 1. Data Collection ✅
- **`available_stocks_list.py`** - 779 actively traded NSE stocks with Yahoo Finance data
- **`yfinance_daily_quotes`** - Source table with OHLCV data for stocks and NIFTY index

### 2. Calculator Engine ✅
- **`nifty500_adv_decl_calculator.py`** - Computes daily advance/decline counts
- **Features:**
  - LAG() window function for price comparisons
  - Duplicate prevention (INSERT IGNORE)
  - Batch processing with progress tracking
  - CLI interface for automation
  - ~500 stocks analyzed per trading day

### 3. Visualization GUI ✅
- **`nifty500_adv_decl_visualizer.py`** - Interactive Tkinter application
- **Features:**
  - **Dual-panel chart:**
    - Top: NIFTY candlestick chart (manual rendering)
    - Bottom: Advance-decline indicator (bar + line)
  - **Date range selector** - Calendar widgets for from/to dates
  - **Quick range buttons** - 1M, 3M, 6M (default), 1Y
  - **No weekend gaps** - Business days only formatting
  - **Compute button** - Calculate missing A/D data on demand
  - **Interactive controls** - Zoom, pan, save chart (matplotlib toolbar)
  - **Status indicators** - Real-time feedback on operations

### 4. Database Schema ✅
- **Table:** `nifty500_advance_decline` (14 columns)
  - Trade date (UNIQUE key)
  - Advances, declines, unchanged counts
  - Total stocks, percentages
  - Advance-decline ratio and difference
  - Metadata (source, computed_at, updated_at)
- **Data:** 124 trading days (May 2025 - November 2025)

### 5. Diagnostic Tools ✅
- **`check_nifty500_coverage.py`** - Analyzes symbol coverage in database
- **`check_nifty_symbol.py`** - Verifies NIFTY index symbol format
- **`get_available_stocks.py`** - Regenerates stock list from database
- **`test_nifty500_adv_decl.py`** - 6-test suite (all passing)

---

## Current Data Quality

### Stock Coverage
| Metric | Value |
|--------|-------|
| Total stocks in list | 779 |
| Stocks per trading day | ~500 |
| Missing/inactive per day | ~279 |
| Data completeness | 100% for available stocks |

### Date Ranges
| Data | Start | End | Records |
|------|-------|-----|---------|
| NIFTY Index | 2020-01-01 | 2025-11-21 | 1,459 |
| Stock Data | 2020-11-23 | 2025-11-21 | Varies by stock |
| A/D Breadth | 2025-05-28 | 2025-11-21 | 124 trading days |

### Sample Recent Data
```
Date       Stocks  Advances  Declines  Adv%   Sentiment
2025-11-21  499      77        418     15.4%  BEARISH
2025-11-20  500     209        289     41.8%  WEAK
2025-11-19  500     230        266     46.0%  NEUTRAL
2025-11-18  500     105        395     21.0%  BEARISH
2025-11-17  500     347        151     69.4%  BULLISH
```

---

## How to Use

### 1. Initial Setup (One-time)
```bash
# Ensure Yahoo Finance data is current
# (Stock data should already be imported)

# Compute historical A/D data (6 months recommended)
python nifty500_adv_decl_calculator.py --days 180
```

### 2. Daily Updates
```bash
# Compute latest trading day
python nifty500_adv_decl_calculator.py --days 1

# Or compute last week
python nifty500_adv_decl_calculator.py --days 7
```

### 3. Launch Visualizer
```bash
python nifty500_adv_decl_visualizer.py
```

**Visualizer Controls:**
- **From/To dates:** Select date range (defaults to 6 months)
- **Quick buttons:** 1M, 3M, 6M, 1Y preset ranges
- **Plot button:** Refresh charts with selected date range
- **Compute A/D button:** Calculate missing breadth data
- **Matplotlib toolbar:** Zoom, pan, home, save chart

### 4. Automation (Optional)
Schedule daily computation:
```bash
# Windows Task Scheduler
# Action: python.exe
# Arguments: D:\MyProjects\StockScreeer\nifty500_adv_decl_calculator.py --days 1
# Trigger: Daily after market close (3:45 PM)
```

---

## Interpreting the Charts

### Top Panel: NIFTY Candlestick Chart
- **Green candles:** Closing price > opening price (bullish day)
- **Red candles:** Closing price < opening price (bearish day)
- **Wicks:** Show intraday high/low range
- **X-axis:** Business days only (no weekend gaps)

### Bottom Panel: Advance-Decline Indicator

**Bar Chart (Gray/Green/Red):**
- **Height:** Advances - Declines difference
- **Green bars:** More advances than declines (bullish breadth)
- **Red bars:** More declines than advances (bearish breadth)
- **Gray bars:** Neutral (advances ≈ declines)

**Blue Line:**
- **Advance percentage** (% of stocks that advanced)
- **Interpretation:**
  - **>70%:** Strong bullish breadth
  - **60-70%:** Moderate bullish
  - **50-60%:** Slight bullish bias
  - **40-50%:** Slight bearish bias
  - **30-40%:** Moderate bearish
  - **<30%:** Strong bearish breadth

**Divergence Analysis:**
- **Bullish divergence:** NIFTY down but A/D improving → Potential reversal
- **Bearish divergence:** NIFTY up but A/D weakening → Potential correction
- **Confirmation:** NIFTY and A/D moving together → Trend is strong

---

## Technical Details

### Data Flow
```
yfinance_daily_quotes (779 stocks)
         ↓
get_nifty500_symbols() → AVAILABLE_STOCKS
         ↓
compute_advance_decline_for_date()
    - LAG() window function
    - Compare close vs previous close
    - Count advances/declines/unchanged
         ↓
save_advance_decline()
    - INSERT IGNORE (duplicate prevention)
         ↓
nifty500_advance_decline table
         ↓
Visualizer:
    - load_nifty_data() → NIFTY OHLCV
    - load_advance_decline_data() → A/D counts
         ↓
Dual-panel matplotlib chart
```

### SQL Query Optimization
- **LAG() window function:** Single-pass price comparison
- **Indexes:** trade_date, computed_at for fast queries
- **Parameter binding:** `text()` wrapper for SQLAlchemy 2.0 compatibility
- **Batch processing:** 4-second average per trading day

### Performance
- **Computation:** ~8 minutes for 124 trading days (779 stocks)
- **Visualization:** Instant for 6 months of data
- **Memory:** Efficient pandas DataFrame operations
- **Database:** Connection pooling with pool_pre_ping

---

## Files Reference

### Core Files
| File | Lines | Purpose |
|------|-------|---------|
| `nifty500_adv_decl_calculator.py` | 453 | Computation engine |
| `nifty500_adv_decl_visualizer.py` | 549 | Interactive GUI |
| `available_stocks_list.py` | 89 | Stock symbol list |
| `nifty500_advance_decline_schema.sql` | 90 | Database schema |

### Support Files
| File | Lines | Purpose |
|------|-------|---------|
| `test_nifty500_adv_decl.py` | 300 | Test suite (6 tests) |
| `check_nifty500_coverage.py` | 70 | Coverage analysis |
| `check_nifty_symbol.py` | 25 | Symbol verification |
| `get_available_stocks.py` | 55 | Stock list generator |
| `create_nifty500_table.py` | 60 | Table creation |

### Documentation
| File | Purpose |
|------|---------|
| `NIFTY500_ADV_DECL_README.md` | Complete user guide (600+ lines) |
| `NIFTY500_ADV_DECL_IMPLEMENTATION_SUMMARY.md` | Implementation details |
| `NIFTY500_DATA_ISSUE_RESOLVED.md` | Data quality analysis |

---

## Issue Resolution History

### Issue 1: Limited Stock Coverage ✅ RESOLVED
- **Problem:** Only 155 stocks being analyzed instead of 500+
- **Root Cause:** `nifty500_stocks_list.py` had wrong symbols, many without Yahoo Finance data
- **Solution:** Created `available_stocks_list.py` with 779 verified stocks from database
- **Result:** Now analyzing ~500 stocks per trading day (3.2x improvement)

### Issue 2: SQL Parameter Binding ✅ RESOLVED
- **Problem:** SQLAlchemy 2.0 not binding `:trade_date` parameters
- **Root Cause:** Missing `text()` wrapper around SQL strings
- **Solution:** Added `text()` wrapper to all SQL queries with parameters
- **Result:** All queries working correctly, 6/6 tests passing

### Issue 3: Nifty Data Source ✅ RESOLVED
- **Problem:** Need to use Yahoo Finance data for NIFTY index
- **Root Cause:** Visualizer already coded for Yahoo Finance, just needed verification
- **Solution:** Confirmed 'NIFTY' symbol exists with 1,459 records (2020-2025)
- **Result:** Visualizer displays NIFTY candlesticks from Yahoo Finance data

---

## Future Enhancements (Optional)

### Short-term
- [ ] Export chart as PNG/PDF
- [ ] CSV export of A/D data
- [ ] Add McClellan Oscillator indicator
- [ ] Alert system for extreme breadth conditions (>80% or <20%)

### Medium-term
- [ ] Integrate with main scanner_gui.py (Market Breadth tab)
- [ ] Add sector-wise A/D analysis
- [ ] Volume-weighted breadth indicators
- [ ] Historical breadth divergence scanner

### Long-term
- [ ] Real-time intraday breadth (if data available)
- [ ] Correlation analysis (breadth vs NIFTY returns)
- [ ] Machine learning breadth prediction
- [ ] Multi-index breadth (NIFTY 50, 100, 200, 500)

---

## System Status

### ✅ FULLY OPERATIONAL

**All components working:**
- ✅ Data collection (779 stocks with Yahoo Finance data)
- ✅ Calculator engine (LAG function, duplicate prevention)
- ✅ Database storage (124 trading days computed)
- ✅ Visualization GUI (dual-panel charts launched)
- ✅ Test suite (6/6 tests passing)
- ✅ Documentation (comprehensive guides)

**Ready for:**
- Daily breadth analysis
- Historical pattern recognition
- Market sentiment tracking
- Divergence identification
- Integration with existing trading systems

---

## Support

### Troubleshooting

**Problem:** Visualizer shows "No Data"
- **Solution:** Run `python nifty500_adv_decl_calculator.py --days 180`

**Problem:** Computation slow
- **Solution:** Normal (4 sec/day for 779 stocks). Use `--days 7` for recent data only.

**Problem:** Chart not updating
- **Solution:** Click "Plot" button after changing date range

**Problem:** Missing recent days
- **Solution:** Run calculator with `--days 1` after market close daily

### Regenerate Stock List
If Yahoo Finance data changes:
```bash
python get_available_stocks.py
# This recreates available_stocks_list.py from current database
```

### Database Maintenance
```sql
-- Check latest data
SELECT trade_date, total_stocks, advance_pct 
FROM nifty500_advance_decline 
ORDER BY trade_date DESC LIMIT 10;

-- Clear all data (if needed)
DELETE FROM nifty500_advance_decline;

-- Recompute
python nifty500_adv_decl_calculator.py --days 180
```

---

**System Created:** November 23-24, 2025  
**Total Development Time:** ~3 hours  
**Total Lines of Code:** ~2,200  
**Status:** ✅ Production Ready  
**Maintainer:** GitHub Copilot (Claude Sonnet 4)
