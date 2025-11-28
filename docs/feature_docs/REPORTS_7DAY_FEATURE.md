# 7-Day RSI Divergence Reports Feature

## Overview
Added a new report type to filter RSI divergence signals to only show stocks with signals generated in the last 7 days, providing traders with more focused, recent opportunities.

## Implementation Details

### 1. GUI Updates (`gui/tabs/reports.py`)
- **Button Layout**: Reorganized button layout into two rows for better organization
- **New Button**: Added "📅 Generate Last 7 Days PDF" button alongside existing "🚀 Generate All Signals PDF"
- **Threading**: Implemented separate threading for 7-day report generation with proper UI updates
- **Progress Tracking**: Added specific progress messages and logging for 7-day report generation

### 2. Backend Function (`scripts/generate_enhanced_rsi_divergence_pdf.py`)
- **New Function**: `generate_enhanced_pdf_report_7days(max_stocks=15)`
- **Data Filtering**: `get_grouped_divergences_data_7days()` filters signals using `DATE()` comparison
- **Signal Selection**: Maintains bullish/bearish signal mix for comprehensive analysis
- **Chart Generation**: Reuses existing chart generation with proper parameter passing

### 3. Key Features
- **Time Filter**: Only includes signals from the last 7 days (since today - 7 days)
- **Signal Ordering**: Orders results by signal date (most recent first), then by volume
- **Professional Charts**: Same high-quality candlestick charts with RSI divergence lines
- **Trading Table**: Includes distance percentages and trading opportunity calculations
- **Error Handling**: Comprehensive error handling with detailed logging

### 4. Technical Specifications
```sql
-- 7-day filter query example
WHERE d.signal_date >= DATE(:seven_days_ago)
AND d.signal_type IN ('Hidden Bullish Divergence', 'Hidden Bearish Divergence')
ORDER BY MAX(d.signal_date) DESC, b.ttl_trd_qnty DESC
```

### 5. File Naming Convention
- **All Signals**: `Enhanced_RSI_Divergences_Grouped_YYYYMMDD_EQ_Series.pdf`
- **7-Day Filter**: `Enhanced_RSI_Divergences_7Days_YYYYMMDD_HHMM_EQ_Series.pdf`

## Usage

### From GUI
1. Open Scanner GUI
2. Navigate to Reports tab
3. Configure max stocks (5-50)
4. Choose report type:
   - **"🚀 Generate All Signals PDF"**: Latest divergence date signals (all stocks)
   - **"📅 Generate Last 7 Days PDF"**: Only stocks with signals in last 7 days

### From Code
```python
from scripts.generate_enhanced_rsi_divergence_pdf import (
    generate_enhanced_pdf_report,          # All signals
    generate_enhanced_pdf_report_7days     # Last 7 days only
)

# Generate all signals report
result1 = generate_enhanced_pdf_report(max_stocks=15)

# Generate 7-day filtered report  
result2 = generate_enhanced_pdf_report_7days(max_stocks=15)
```

## Testing Results
Both report types tested successfully:
- **All Signals Report**: 3 stocks, 5 total signals (387 buy, 75 sell opportunities)
- **7-Day Report**: 3 stocks, 5 signals (3 buy, 2 sell opportunities from recent period)

## Benefits
- **Focused Analysis**: Traders can focus on recent signals without older noise
- **Quick Decision Making**: Smaller, more relevant reports for immediate action
- **Flexible Options**: Choose between comprehensive analysis vs recent opportunities
- **Professional Quality**: Same chart quality and technical accuracy as full reports

## Files Modified
1. `gui/tabs/reports.py` - Added new button and 7-day generation method
2. `scripts/generate_enhanced_rsi_divergence_pdf.py` - Added 7-day filtering functions
3. `test_reports.py` - Created comprehensive test suite for both report types

## Future Enhancements
- Configurable time periods (3 days, 7 days, 14 days, 30 days)
- Signal strength filtering
- Sector-specific reports
- Custom date range selection