# Intraday 1-Minute Data Viewer - User Guide

## Overview
Interactive desktop application for viewing 1-minute intraday candle data for all Nifty 500 stocks and Nifty index, with real-time market breadth indicators.

## Features

### 1. Stock Selection
- **Dropdown list** with all 511 available stocks (510 Nifty 500 + NIFTY index)
- Alphabetically sorted for easy navigation
- Default selection: NIFTY index

### 2. Date Range Selection
- **From Date** and **To Date** dropdowns
- Shows all available trading days (Nov 18-24, 2025)
- Select single day or multi-day range
- Default: Latest trading day

### 3. Data Display
Displays complete OHLCV data with:
- **Timestamp**: Date and time of each 1-minute candle
- **Open/High/Low/Close**: Price levels
- **Volume**: Trading volume for that minute
- **Prev Close**: Previous day's closing price
- **Change**: Price change from previous close (₹)
- **Change %**: Percentage change from previous close
- **Status**: ADVANCE (green) / DECLINE (red) / UNCHANGED

### 4. Market Breadth Indicators
Shows advance-decline data for the selected period:
- **Latest Breadth**: Current market breadth snapshot
  - Advances count and percentage
  - Declines count and percentage
  - Unchanged stocks
  - Advance/Decline ratio
  - Net difference (Advances - Declines)
  - Market sentiment (BULLISH/BEARISH/NEUTRAL)

- **Period Average**: Average breadth metrics across selected timeframe

### 5. Summary Bar
Displays at-a-glance statistics:
- Stock name
- Number of candles loaded
- Time range
- Period Open/Close/High/Low prices
- Net change and percentage
- Total volume

### 6. Export to CSV
Export button saves current view to CSV file with format:
- Filename: `intraday_1min_{STOCK}_{FROM_DATE}_to_{TO_DATE}.csv`
- Contains all displayed columns

## How to Use

### Basic Workflow
1. **Launch** the application:
   ```
   python intraday_1min_viewer.py
   ```

2. **Select Stock**: Choose from dropdown (e.g., RELIANCE, TCS, NIFTY)

3. **Select Date Range**: 
   - From Date: Starting date
   - To Date: Ending date

4. **Load Data**: Click "Load Data" button

5. **View Results**:
   - Scroll through 1-minute candles in main table
   - Check market breadth in indicator panel
   - Review summary statistics

6. **Export** (optional): Click "Export CSV" to save data

### Example Use Cases

#### View Single Day Intraday Movement
```
Stock: RELIANCE
From Date: 2025-11-24
To Date: 2025-11-24
```
Shows 375 candles (9:15 AM - 3:29 PM)

#### Multi-Day Analysis
```
Stock: TCS
From Date: 2025-11-18
To Date: 2025-11-24
```
Shows 1,875 candles (5 trading days × 375 minutes)

#### Market Index Tracking
```
Stock: NIFTY
From Date: 2025-11-21
To Date: 2025-11-24
```
View NIFTY 50 index movement with market breadth

#### Compare with Market Breadth
```
Stock: Any stock
Date Range: Any range
```
The breadth panel always shows how many stocks were advancing vs declining during that period

## Color Coding
- **Green text**: ADVANCE (stock price above previous close)
- **Red text**: DECLINE (stock price below previous close)
- **Black text**: UNCHANGED (stock price equal to previous close)

## Data Details
- **Resolution**: 1-minute candles
- **Coverage**: 5 trading days (Nov 18-24, 2025)
- **Stocks**: 511 symbols (510 Nifty 500 + NIFTY index)
- **Market Hours**: 9:15 AM - 3:29 PM IST
- **Candles per Day**: 375 (one per minute)

## Market Breadth Indicators Explained

### Advances
Number of stocks trading above previous close

### Declines
Number of stocks trading below previous close

### A/D Ratio
Advances divided by Declines
- > 1.0 = More stocks advancing (bullish)
- < 1.0 = More stocks declining (bearish)
- = 1.0 = Equal advances and declines (neutral)

### Market Sentiment
Automatically calculated based on advance percentage:
- **STRONG BULLISH**: ≥70% advancing
- **BULLISH**: 60-69% advancing
- **SLIGHTLY BULLISH**: 55-59% advancing
- **NEUTRAL**: 45-54% advancing
- **SLIGHTLY BEARISH**: 40-44% advancing
- **BEARISH**: 30-39% advancing
- **STRONG BEARISH**: <30% advancing

## Performance Tips
- Loading single day is faster than multi-day
- Use date range wisely for large datasets
- Export to CSV for external analysis (Excel, Python, etc.)

## Troubleshooting

### No data displayed
- Check if stock symbol is correct
- Verify date range has data (use available dates only)
- Ensure database connection is working

### Application doesn't start
- Check if required packages are installed
- Verify `.env` file has correct database credentials
- Ensure MySQL database is running

### Export fails
- Check write permissions in current directory
- Ensure filename doesn't contain invalid characters
- Verify disk space available

## Technical Details
- **Database**: MySQL (marketdata database)
- **Tables Used**: 
  - `intraday_1min_candles` (OHLCV data)
  - `intraday_advance_decline` (breadth indicators)
- **GUI Framework**: Tkinter (Python standard library)
- **Dependencies**: sqlalchemy, pymysql, python-dotenv

## Future Enhancements (Planned)
- Charting capability (candlestick charts)
- Technical indicators (SMA, RSI, MACD)
- Real-time updates during market hours
- Compare multiple stocks
- Filter by time of day
- Volume profile analysis

---

**Version**: 1.0  
**Date**: November 24, 2025  
**Database**: 932,563 candles across 511 symbols
