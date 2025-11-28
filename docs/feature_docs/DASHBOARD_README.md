# Dashboard Tab - Database Status Monitor

## Overview

The Dashboard tab is the first tab that appears when the Scanner GUI is launched. It provides a comprehensive overview of the database status and data availability across all major components of the Stock Screener system.

## Features

### 🎯 Purpose
- **Database Health Monitoring**: Real-time status of all key database tables
- **Data Availability Overview**: Quick summary of data ranges and counts
- **Status Indicators**: Color-coded status cards for easy visual assessment
- **Auto-refresh**: Regular updates of database status information

### 📊 Status Cards

The dashboard displays four main status cards:

1. **BHAV Data** - NSE equity data status
   - Shows total days of data available
   - Date range (oldest to newest)
   - Color: Green (good), Yellow (partial), Red (missing)

2. **SMAs Data** - Simple Moving Averages status
   - Shows percentage of symbols with complete SMA calculations
   - Date range coverage
   - Color: Green (>95%), Yellow (50-95%), Red (<50%)

3. **RSI Data** - Relative Strength Index status
   - Shows percentage of symbols with RSI data
   - Date range coverage
   - Color: Green (>95%), Yellow (50-95%), Red (<50%)

4. **Trend Analysis** - Trend analysis data status
   - Shows latest trend calculations
   - Number of symbols analyzed
   - Color: Green (recent), Yellow (stale), Red (missing)

### 📋 Detailed Information Section

Below the status cards, there's a scrollable text area that provides:
- **Detailed Statistics**: Exact counts, percentages, and ranges
- **Data Quality Metrics**: Missing data indicators and gaps
- **Recommendations**: Suggested actions based on data status
- **Error Information**: Any database connection or query errors

### 🔄 Auto-Refresh

The dashboard automatically refreshes every 30 seconds to keep status information current. You can also manually refresh by clicking the "Refresh" button.

## Implementation

### Files
- `gui/tabs/dashboard.py` - Main dashboard implementation
- `scanner_gui.py` - Integration with main GUI (modified to include dashboard as first tab)
- `test_dashboard.py` - Validation and testing script

### Database Tables Monitored
- `nse_equity_bhavcopy_full` - BHAV data
- `moving_averages` - Moving averages calculations
- `nse_rsi_daily` - RSI calculations  
- `trend_analysis` - Trend analysis results

### Key Methods
- `DashboardTab.__init__()` - Initializes the dashboard
- `create_status_cards()` - Creates the visual status indicators
- `create_details_section()` - Creates the detailed info area
- `refresh_dashboard()` - Updates all status information
- `check_*_data()` - Individual status checkers for each data type

## Usage

### Automatic Display
The dashboard automatically appears as the first tab when launching:
```bash
python scanner_gui.py
```

### Manual Testing
You can test the dashboard implementation:
```bash
python test_dashboard.py
```

### Integration
The dashboard is integrated into the main Scanner GUI and will display database status immediately upon launch, giving users instant visibility into their data availability.

## Status Colors

- 🟢 **Green**: Good - Data is current and complete
- 🟡 **Yellow**: Warning - Data is partial or slightly stale
- 🔴 **Red**: Error - Data is missing or significantly out of date

## Dependencies

- tkinter/ttk for UI components
- sqlalchemy for database connections
- pandas for data analysis
- datetime for date calculations
- Environment variables for database connection (same as other components)

## Error Handling

The dashboard gracefully handles:
- Database connection failures
- Missing tables or columns
- Empty datasets
- Network connectivity issues

All errors are displayed in the detailed section with specific error messages and suggested actions.