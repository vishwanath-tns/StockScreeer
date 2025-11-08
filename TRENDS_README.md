# Trend Analysis Scanner

## Overview

The Trend Analysis Scanner is a new feature that analyzes daily, weekly, and monthly trends for stocks to provide a comprehensive trend rating system.

## How It Works

### Trend Determination Rules

For each timeframe (daily, weekly, monthly), the scanner determines the trend based on candle colors:

- **UP Trend**: If the current candle is GREEN (close > open)
- **DOWN Trend**: If the current candle is RED (close ≤ open)

### Trend Rating System

The rating system combines all three trends to provide a score from **-3 to +3**:

- **+3**: All trends are UP (Daily=UP, Weekly=UP, Monthly=UP)
- **+2**: Two trends UP, one DOWN
- **+1**: Two trends UP, one DOWN (or one UP, two DOWN)
- **0**: Mixed/neutral trends
- **-1**: Two trends DOWN, one UP
- **-2**: Two trends DOWN, one UP
- **-3**: All trends are DOWN (Daily=DOWN, Weekly=DOWN, Monthly=DOWN)

### Data Calculation

- **Daily Trend**: Uses the current day's open and close prices
- **Weekly Trend**: Calculates weekly OHLC where:
  - Open = First day's open of the week
  - Close = Last day's close of the week
  - High/Low = Week's highest/lowest prices
- **Monthly Trend**: Calculates monthly OHLC where:
  - Open = First day's open of the month
  - Close = Last day's close of the month
  - High/Low = Month's highest/lowest prices

## Database Storage

Results are stored in the `trend_analysis` table with the following structure:

```sql
CREATE TABLE trend_analysis (
  id              BIGINT      AUTO_INCREMENT PRIMARY KEY,
  symbol          VARCHAR(64) NOT NULL,
  trade_date      DATE        NOT NULL,
  daily_trend     VARCHAR(10) NOT NULL,    -- 'UP' or 'DOWN'
  weekly_trend    VARCHAR(10) NOT NULL,    -- 'UP' or 'DOWN'  
  monthly_trend   VARCHAR(10) NOT NULL,    -- 'UP' or 'DOWN'
  trend_rating    TINYINT     NOT NULL,    -- -3 to +3
  created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  UNIQUE KEY uk_symbol_date (symbol, trade_date),
  KEY idx_trade_date (trade_date),
  KEY idx_trend_rating (trend_rating)
);
```

## Using the Trend Analysis Tab

### Access
1. Open the Stock Scanner GUI: `python scanner_gui.py`
2. Navigate to the **"Trend Analysis"** tab

### Features

#### 1. Scan Current Day Trends
- Analyzes trends for all symbols on the latest available trading date
- Stores results in the database
- Displays results in the sortable table

#### 2. Scan All Historical Data
- **Warning**: This is a comprehensive scan that processes all historical data
- Analyzes trends for every symbol on every available trading date
- Can take significant time depending on data volume
- Progress is shown during the scan

#### 3. Results Display
- **Sortable Columns**: Click any column header to sort
- **Color Coding**:
  - 🟢 **Green**: Positive trend ratings (+1 to +3)
  - 🔴 **Red**: Negative trend ratings (-1 to -3)
  - 🟡 **Yellow**: Neutral trend rating (0)

#### 4. Summary Statistics
Shows real-time statistics including:
- Total records processed
- Unique symbols and dates
- Average trend rating
- Distribution of positive/negative/neutral ratings

### Column Descriptions

| Column | Description |
|--------|-------------|
| **Symbol** | Stock symbol (e.g., SBIN, RELIANCE) |
| **Trade Date** | Date of the analysis |
| **Daily Trend** | UP or DOWN based on daily candle |
| **Weekly Trend** | UP or DOWN based on weekly candle |
| **Monthly Trend** | UP or DOWN based on monthly candle |
| **Rating** | Combined trend score (-3 to +3) |

## Implementation Files

### Core Components
- `services/trends_service.py` - Business logic for trend analysis
- `db/trends_repo.py` - Database operations
- `gui/tabs/trends.py` - User interface
- `trends_table.sql` - Database table creation script

### Integration
- Added to `scanner_gui.py` as a new tab
- Integrated with existing database connection system

## Usage Examples

### Finding Strong Bullish Stocks
Filter results by **Rating = +3** to find stocks where all trends are aligned upward.

### Finding Strong Bearish Stocks
Filter results by **Rating = -3** to find stocks where all trends are aligned downward.

### Finding Reversal Candidates
Look for stocks with **Rating = 0** where trends are mixed, potentially indicating trend changes.

## Performance Considerations

- **Current Day Scan**: Fast, processes only latest date
- **Historical Scan**: Resource-intensive, processes all historical data
- **Database**: Optimized with indexes on commonly filtered columns
- **Memory**: Processes data in batches to manage memory usage

## Error Handling

The system includes robust error handling for:
- Missing OHLC data
- Database connectivity issues
- Invalid date ranges
- Calculation errors

Errors are logged to both the GUI log area and can be monitored during processing.

## Future Enhancements

Potential improvements could include:
- Trend strength indicators (volume confirmation)
- Moving average trend alignment
- Sector-wise trend analysis
- Export functionality for results
- Alert system for trend changes
- Historical trend pattern recognition