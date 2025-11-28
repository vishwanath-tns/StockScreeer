# Intraday 1-Minute Viewer - Charts Edition Guide

## Overview
Enhanced version of the intraday viewer with **candlestick charts** and **advance-decline line charts** for comprehensive technical and market breadth analysis.

## New Features

### 1. **Candlestick Chart (Top Panel)**
- **Visual representation** of 1-minute OHLC data
- **Color coding**:
  - Green candles: Close ≥ Open (bullish)
  - Red candles: Close < Open (bearish)
- **Wick/Shadow lines** show high-low range
- **Body** shows open-close range
- **Interactive zoom and pan** via matplotlib toolbar
- **Automatic scaling** to fit all price data

### 2. **Advance-Decline Line Chart (Bottom Panel)**
- **Real-time market breadth** visualization
- **Net difference line** (Advances - Declines) in blue
- **Filled areas**:
  - Green fill: Net Advance (positive territory)
  - Red fill: Net Decline (negative territory)
- **Zero line** (dashed gray) as reference
- **Legend** for easy interpretation
- **Synchronized time axis** with candlestick chart

### 3. **Tabbed Interface**
- **Charts Tab**: Primary view with both charts
- **Data Table Tab**: Detailed numerical data and breadth statistics

## Usage

### Starting the Viewer
```powershell
python intraday_1min_viewer_charts.py
```

### Loading Data
1. **Select Stock**: Choose from dropdown (511 stocks including NIFTY)
2. **Select Date Range**: Choose From Date and To Date
3. **Click "Load Data"**: Both charts update automatically

### Chart Interaction (Matplotlib Toolbar)
- **Home**: Reset view to original
- **Back/Forward**: Navigate zoom history
- **Pan**: Click and drag to pan
- **Zoom**: Draw rectangle to zoom in
- **Configure**: Adjust subplot spacing
- **Save**: Export chart as PNG/PDF/SVG

### Reading the Charts

#### Candlestick Patterns
```
Green Candle:        Red Candle:         Doji:
    │                    │                 ──
    ╭─╮                ╭─╮                 │
    │█│                │█│                 │
    ╰─╯                ╰─╯                ──
    │                    │              
```
- **Long body**: Strong momentum
- **Long wicks**: Volatility/rejection
- **Small body (doji)**: Indecision
- **Multiple green**: Bullish trend
- **Multiple red**: Bearish trend

#### Advance-Decline Interpretation
```
Positive (above zero):   Strong market breadth (more advances)
Negative (below zero):   Weak market breadth (more declines)
Rising line:             Improving sentiment
Falling line:            Deteriorating sentiment
Crossing zero:           Sentiment shift (watch for trend changes)
```

### Example Scenarios

#### Strong Bullish Day
- Candlesticks: Mostly green, rising prices
- A-D Line: Stays positive, trending upward
- Interpretation: Broad-based rally

#### Weak Bearish Day
- Candlesticks: Mostly red, falling prices
- A-D Line: Stays negative, trending downward
- Interpretation: Broad-based selloff

#### Divergence (Important!)
- Candlesticks: Rising (stock up)
- A-D Line: Falling (breadth weakening)
- Interpretation: **Warning sign** - rally lacks broad participation

## Technical Details

### Chart Configuration
- **Resolution**: 100 DPI, 14x10 inches (1400x1000 pixels)
- **Subplot ratio**: 2:1 (candlesticks:breadth)
- **Update frequency**: On-demand (click "Load Data")
- **Maximum candles**: ~2000 (5 trading days × ~375 candles/day)

### Performance Tips
1. **Single day**: Fast loading, detailed view
2. **Multi-day**: Slower loading, broader context
3. **Use zoom**: Focus on specific time periods
4. **Export charts**: Save analysis for reports

### Data Synchronization
- Candlestick data: Per-stock basis (symbol selected)
- Breadth data: Market-wide (all 511 stocks aggregated)
- Time alignment: Both charts share same time period

## Keyboard Shortcuts (Matplotlib)
- **Home**: `h` - Reset view
- **Back**: `left arrow` or `c` - Previous view
- **Forward**: `right arrow` or `v` - Next view
- **Pan/Zoom**: `p` - Toggle pan mode
- **Zoom**: `o` - Toggle zoom mode
- **Save**: `Ctrl+S` - Save figure

## Export Options

### CSV Export
- Click "Export CSV" button
- Contains all numerical data (timestamp, OHLC, volume, etc.)
- Use for further analysis in Excel/Python

### Chart Export
- Use matplotlib toolbar "Save" button
- Formats: PNG (high quality), PDF (vector), SVG (web)
- Resolution: Adjustable in save dialog

## Comparison with Original Viewer

| Feature | Original | Charts Edition |
|---------|----------|----------------|
| Data Table | ✅ | ✅ |
| Breadth Stats | ✅ | ✅ |
| Candlestick Chart | ❌ | ✅ |
| A-D Line Chart | ❌ | ✅ |
| Interactive Zoom | ❌ | ✅ |
| Chart Export | ❌ | ✅ |
| Tabbed Interface | ❌ | ✅ |

## Troubleshooting

### Charts Not Updating
- Check if data loaded successfully (status bar message)
- Verify date range has data (check Data Table tab)
- Try switching between tabs to force refresh

### Chart Too Crowded
- Use matplotlib zoom tool to focus on time range
- Load single day for detailed analysis
- Adjust window size (resize to larger screen)

### Missing Breadth Data
- Normal if no breadth snapshots in that period
- Bottom chart will show "No market breadth data available"
- Candlestick chart still displays normally

### Performance Issues
- Loading 5 days = ~2000 candles (can be slow)
- Reduce date range for faster response
- Close other applications to free memory

## Advanced Analysis Tips

### 1. **Identify Support/Resistance**
- Look for price levels where candles "bounce"
- Multiple touches = stronger level
- Use zoom to see wick details

### 2. **Volume Confirmation**
- Check Data Table tab for volume spikes
- High volume + green candle = strong buying
- High volume + red candle = strong selling

### 3. **Breadth Divergence**
- Stock rises but A-D line falls = weak rally
- Stock falls but A-D line rises = selling exhaustion
- Both aligned = trend confirmation

### 4. **Intraday Trends**
- Morning rally: Check if breadth supports it
- Afternoon fade: Look for breadth deterioration
- End-of-day surge: Confirm with breadth strength

## Future Enhancements (Planned)
- Volume bars overlay on candlestick chart
- Moving averages (5, 10, 20 period)
- Multiple timeframe aggregation (5-min, 15-min)
- Real-time updates (live data feed)
- Multi-stock comparison (overlay multiple symbols)
- Pattern detection (flags, triangles, head-shoulders)
- Alert system (price/breadth thresholds)

## Database Requirements
- Table: `intraday_1min_candles` (stock OHLCV data)
- Table: `intraday_advance_decline` (market breadth snapshots)
- Date range: Currently has Nov 18-24, 2025 (5 trading days)
- Stocks: 511 symbols (510 Nifty 500 + NIFTY index)

## File Locations
- Main script: `intraday_1min_viewer_charts.py`
- Original viewer: `intraday_1min_viewer.py`
- Configuration: `.env` (database credentials)
- This guide: `INTRADAY_CHARTS_GUIDE.md`

## Need Help?
Check the status bar at bottom of window for real-time feedback on operations.

---
**Version**: 2.0 (Charts Edition)  
**Last Updated**: November 24, 2025  
**Requires**: Python 3.x, matplotlib, tkinter, SQLAlchemy
