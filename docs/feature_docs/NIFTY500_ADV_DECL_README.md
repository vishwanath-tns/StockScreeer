# Nifty 500 Advance-Decline Analysis System

## 📊 Overview

Complete system for analyzing daily advance/decline counts for Nifty 500 stocks using Yahoo Finance data. Features include automated calculation, database storage, and interactive visualization with dual-panel charts.

## ✨ Features

### 1. **Automated Calculation**
- ✅ Calculates advances, declines, and unchanged counts daily
- ✅ Prevents duplicate entries (smart caching)
- ✅ Batch processing for date ranges
- ✅ Progress tracking for long computations

### 2. **Database Storage**
- ✅ Dedicated MySQL table: `nifty500_advance_decline`
- ✅ Historical tracking with timestamps
- ✅ Breadth indicators (ratios, percentages, differences)
- ✅ Pre-built views for analysis

### 3. **Interactive Visualization**
- ✅ Dual-panel chart:
  - **Top**: Nifty 50 candlestick chart
  - **Bottom**: Advance-Decline indicator
- ✅ No weekend gaps (business days only)
- ✅ Date range selector (from/to dates)
- ✅ Quick range buttons (1M, 3M, 6M, 1Y)
- ✅ Default 6-month view
- ✅ Zoom and pan capabilities
- ✅ Professional styling with color-coded indicators

## 🗂️ File Structure

```
StockScreener/
├── nifty500_advance_decline_schema.sql    # Database schema
├── nifty500_adv_decl_calculator.py        # Core calculation engine
├── nifty500_adv_decl_visualizer.py        # Interactive GUI
├── nifty500_stocks_list.py                # Nifty 500 symbols list
└── NIFTY500_ADV_DECL_README.md            # This file
```

## 🚀 Quick Start

### Step 1: Create Database Table

Run the SQL schema to create the required table and views:

```bash
# From MySQL command line or workbench
mysql -u root -p marketdata < nifty500_advance_decline_schema.sql
```

Or from PowerShell:

```powershell
# Using Python to execute schema
python -c "from sync_bhav_gui import engine; import os; sql = open('nifty500_advance_decline_schema.sql').read(); conn = engine().connect(); 
for statement in [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]:
    try:
        if statement.upper().startswith('USE'):
            continue
        result = conn.execute(statement)
        print(f'✓ Executed: {statement[:60]}...')
    except Exception as e:
        print(f'✗ {statement[:60]}... -> {e}')
conn.close(); print('\n✓ Tables setup complete!')"
```

### Step 2: Compute Advance-Decline Data

**Option A: Using Python directly**

```bash
# Compute last 6 months
python nifty500_adv_decl_calculator.py --days 180

# Compute specific date range
python nifty500_adv_decl_calculator.py --start-date 2024-01-01 --end-date 2024-12-31

# Force recompute existing dates
python nifty500_adv_decl_calculator.py --days 90 --force
```

**Option B: Using GUI**

```bash
# Launch visualizer with compute button
python nifty500_adv_decl_visualizer.py
# Click "⚙️ Compute A/D" button
```

### Step 3: Visualize Data

```bash
# Launch interactive visualizer
python nifty500_adv_decl_visualizer.py
```

## 📈 Using the Visualizer

### Main Interface

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Nifty 500 Advance-Decline Analysis                       │
│ From: [2024-05-23] To: [2024-11-23] [Update Chart]         │
│ [1M] [3M] [6M] [1Y]  [⚙️ Compute A/D]          Status: ✓   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Nifty 50 Candlestick Chart (70%)             │  │
│  │                                                        │  │
│  │  [Candlestick chart with OHLC data]                  │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       Advance-Decline Indicator (30%)                │  │
│  │                                                        │  │
│  │  [Bar chart: Advances - Declines]                    │  │
│  │  [Line chart: Advance %]                             │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ 📅 Period: 2024-05-23 to 2024-11-23 | Nifty: 125 days    │
└─────────────────────────────────────────────────────────────┘
```

### Features:

1. **Date Selection**
   - Use calendar pickers to select date range
   - Click "Update Chart" to refresh

2. **Quick Range Buttons**
   - **1M**: Last 1 month
   - **3M**: Last 3 months
   - **6M**: Last 6 months (default)
   - **1Y**: Last 1 year

3. **Compute Button**
   - Click "⚙️ Compute A/D" to calculate missing data
   - Shows progress dialog during computation

4. **Chart Interactions**
   - **Zoom**: Use toolbar or scroll
   - **Pan**: Drag chart area
   - **Save**: Export chart as image
   - **Home**: Reset view

## 📊 Understanding the Charts

### Top Panel: Nifty 50 Index

- **Green candles**: Closing price > Opening price
- **Red candles**: Closing price < Opening price
- **Wicks**: High and low of the day
- **No gaps**: Weekends and holidays removed

### Bottom Panel: Advance-Decline Indicator

**Bar Chart (Advances - Declines):**
- **Green bars**: More advances than declines (bullish)
- **Red bars**: More declines than advances (bearish)
- **Zero line**: Equal advances and declines

**Blue Line (Advance %):**
- **Above 70%**: Very Bullish market
- **55-70%**: Bullish market
- **45-55%**: Neutral market
- **30-45%**: Bearish market
- **Below 30%**: Very Bearish market

## 🗄️ Database Schema

### Table: `nifty500_advance_decline`

```sql
Columns:
- id (PRIMARY KEY)
- trade_date (UNIQUE, indexed)
- advances (count of stocks closing up)
- declines (count of stocks closing down)
- unchanged (count of stocks unchanged)
- total_stocks (total stocks analyzed)
- advance_pct (percentage advancing)
- decline_pct (percentage declining)
- unchanged_pct (percentage unchanged)
- advance_decline_ratio (advances/declines)
- advance_decline_diff (advances - declines)
- source (data source tracking)
- computed_at (timestamp)
- updated_at (timestamp)
```

### Views:

1. **`v_nifty500_adv_decl_recent`**: Last 90 days with market sentiment
2. **`v_nifty500_adv_decl_monthly`**: Monthly aggregates

## 🔧 Technical Details

### Data Source

- **Nifty 50**: `yfinance_daily_quotes` (symbol='NIFTY')
- **Nifty 500 stocks**: 500 most liquid stocks from Yahoo Finance
- **A/D calculation**: Compares close vs previous close for each stock

### Calculation Logic

```python
For each trading day:
1. Get closing price for each Nifty 500 stock
2. Compare with previous day's close:
   - Close > Prev Close → ADVANCE
   - Close < Prev Close → DECLINE
   - Close = Prev Close → UNCHANGED
3. Count totals
4. Calculate percentages and ratios
5. Store in database (INSERT IGNORE for duplicates)
```

### Performance

- **Computation speed**: ~100-200 dates per minute
- **6 months data**: ~2-3 minutes
- **1 year data**: ~5-6 minutes

## 📋 Dependencies

```
Python 3.8+
pandas
sqlalchemy
pymysql
python-dotenv
matplotlib
mplfinance
tkcalendar
```

Install via:

```bash
pip install pandas sqlalchemy pymysql python-dotenv matplotlib mplfinance tkcalendar
```

## ⚙️ Configuration

Uses existing `.env` file:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=marketdata
MYSQL_USER=root
MYSQL_PASSWORD=your_password
```

## 🎯 Use Cases

### 1. Market Breadth Analysis
- Identify market-wide trends
- Detect breadth divergences (price up, breadth down)
- Confirm trend strength

### 2. Overbought/Oversold Detection
- >70% advances: Potential overbought
- <30% advances: Potential oversold

### 3. Trend Confirmation
- Rising Nifty + Rising A/D: Strong bullish trend
- Rising Nifty + Falling A/D: Weak/divergent trend
- Falling Nifty + Falling A/D: Strong bearish trend

### 4. Entry/Exit Timing
- High advance % → Consider profit booking
- Low advance % → Look for accumulation opportunities

## 🐛 Troubleshooting

### Issue: No Nifty data found

**Solution**: Ensure Nifty 50 data exists in `yfinance_daily_quotes`:

```sql
SELECT COUNT(*), MIN(date), MAX(date) 
FROM yfinance_daily_quotes 
WHERE symbol = 'NIFTY';
```

If empty, download Nifty data first.

### Issue: No A/D data

**Solution**: Compute using:

```bash
python nifty500_adv_decl_calculator.py --days 180
```

Or click "⚙️ Compute A/D" in visualizer.

### Issue: Missing dates in chart

**Cause**: Weekends/holidays automatically excluded (business days only).

**Expected behavior**: No gaps shown for non-trading days.

### Issue: Slow computation

**Solutions**:
- Reduce date range
- Ensure database indexes exist
- Check network/database connection
- Use `--force` only when needed

## 📊 Sample Queries

### Get recent advance-decline data

```sql
SELECT * FROM v_nifty500_adv_decl_recent;
```

### Find very bullish days (>70% advance)

```sql
SELECT trade_date, advance_pct, advances, declines
FROM nifty500_advance_decline
WHERE advance_pct >= 70
ORDER BY trade_date DESC
LIMIT 10;
```

### Monthly breadth summary

```sql
SELECT * FROM v_nifty500_adv_decl_monthly;
```

### Compare Nifty price with breadth

```sql
SELECT 
    a.trade_date,
    n.close as nifty_close,
    a.advance_pct,
    a.advance_decline_diff
FROM nifty500_advance_decline a
JOIN yfinance_daily_quotes n ON a.trade_date = n.date
WHERE n.symbol = 'NIFTY'
ORDER BY a.trade_date DESC
LIMIT 30;
```

## 🔄 Workflow Examples

### Daily Workflow

1. **Morning**: Check latest A/D reading
   ```bash
   python nifty500_adv_decl_calculator.py --days 1
   ```

2. **Analysis**: View on chart
   ```bash
   python nifty500_adv_decl_visualizer.py
   ```

3. **Decision**: Use breadth for confirmation

### Weekly Analysis

1. Compute full week
2. Analyze 3-month trend
3. Look for divergences
4. Generate insights

### Monthly Review

1. Update full month data
2. Review monthly summary view
3. Compare with Nifty performance
4. Identify patterns

## 📚 Additional Resources

### Related Systems

- **Market Breadth Analysis**: See `MARKET_BREADTH_FEATURES.md`
- **Advance-Declines (BHAV)**: See `reporting_adv_decl.py`
- **Nifty 500 Momentum**: See `NIFTY500_IMPLEMENTATION_COMPLETE.md`

### Documentation

- Main project summary: `PROJECT_ACHIEVEMENTS_SUMMARY.md`
- Database schema: `nifty500_advance_decline_schema.sql`

## ✅ Checklist

- [x] Database schema created
- [x] Calculator module implemented
- [x] Visualizer GUI created
- [x] Duplicate prevention
- [x] Date range selector
- [x] Business days only (no gaps)
- [x] Default 6 months view
- [x] Modular and scalable design
- [x] Professional styling
- [x] Comprehensive documentation

## 🎉 Features Summary

| Feature | Status | Description |
|---------|--------|-------------|
| Daily A/D Calculation | ✅ | Automated advance/decline counting |
| Database Storage | ✅ | MySQL table with indexes |
| Duplicate Prevention | ✅ | INSERT IGNORE for safe re-runs |
| Dual-Panel Chart | ✅ | Nifty (top) + A/D (bottom) |
| No Weekend Gaps | ✅ | Business days only display |
| Date Range Selector | ✅ | From/To calendar pickers |
| Quick Range Buttons | ✅ | 1M, 3M, 6M, 1Y shortcuts |
| Default 6M View | ✅ | Shows last 6 months by default |
| Progress Tracking | ✅ | Real-time computation progress |
| Interactive Zoom/Pan | ✅ | Full matplotlib toolbar |
| Modular Design | ✅ | Separate calculator & visualizer |
| Scalable Architecture | ✅ | Handles years of data |

---

**Status**: ✅ **COMPLETE & OPERATIONAL**  
**Created**: November 2024  
**Version**: 1.0

For questions or issues, refer to code comments or project documentation.
