# 📊 Yahoo Finance Chart Visualizer

Professional market data visualization tool with interactive candlestick charts, symbol selection, and flexible date ranges.

## 🌟 Features

### 📈 **Chart Types**
- **Candlestick Charts** - Professional OHLC candlestick visualization
- **OHLC Bar Charts** - Traditional bar-style OHLC representation  
- **Line Charts** - Simple price trend lines
- **Area Charts** - Filled area price visualization

### 🎯 **Symbol Selection**
- **NIFTY** (^NSEI) - NSE NIFTY 50 Index
- **BANKNIFTY** (^NSEBANK) - Bank Nifty Index
- **SENSEX** (^BSESN) - BSE Sensex Index
- Easy dropdown selection with validated symbols

### 📅 **Date Range Options**
- **Preset Periods**: 1 Month, 3 Months, 6 Months, 1 Year, 2 Years
- **Custom Range**: Flexible date picker for specific periods
- **Default View**: 3-month candlestick chart (as requested)

### 🎨 **Professional Design**
- **Dark Theme** - Easy on eyes for extended use
- **Interactive Charts** - Zoom, pan, and navigate with mouse
- **Real-time Data** - Automatic download if data missing
- **Export Options** - Save charts as PNG/PDF files

## 🚀 Quick Start

### Launch the Chart Visualizer
```bash
cd yahoo_finance_service
python launch_charts.py
```

### Default Behavior
- Opens with **NIFTY 3-month candlestick chart**
- Data loaded automatically from database or downloaded from Yahoo Finance
- Ready to use immediately

## 🎮 Usage Guide

### 1. **Symbol Selection**
- Choose from dropdown: NIFTY, BANKNIFTY, or SENSEX
- Default: NIFTY (most popular index)

### 2. **Chart Type Selection**
- **Candlestick** (default) - Best for price action analysis
- **OHLC** - Traditional bar charts
- **Line** - Simple price trends
- **Area** - Filled area visualization

### 3. **Time Period Selection**
- **Preset Periods**: Quick selection for common ranges
- **Custom**: Use date picker for specific ranges
- Default: 3 Months (as requested)

### 4. **Chart Controls**
- **📊 Update Chart** - Refresh with new settings
- **⬇️ Download Data** - Force download latest data
- **💾 Export Chart** - Save chart to file
- **Mouse Controls** - Zoom and pan within chart

## 🏗️ Technical Architecture

### Data Flow
```
Symbol Selection → Date Range → Database Check → Yahoo Finance API → Chart Rendering
```

### Components
- **chart_visualizer.py** - Main GUI application
- **launch_charts.py** - Application launcher
- **Integration** - Uses existing yahoo_finance_service modules

### Dependencies
- **mplfinance** - Financial charting library
- **matplotlib** - Core plotting functionality
- **tkinter** - GUI framework
- **pandas/numpy** - Data processing

## 🎯 Key Features Delivered

### ✅ **Symbol Selection**
Professional dropdown with validated market symbols

### ✅ **Date Range Control** 
Flexible date picker with preset options and custom ranges

### ✅ **3-Month Default**
Opens with 3-month NIFTY candlestick chart as requested

### ✅ **Professional Charting**
High-quality candlestick visualization with dark theme

### ✅ **Data Integration**
Seamless integration with existing Yahoo Finance database

## 🎨 Chart Examples

### Candlestick Chart Features
- **Green Candles** - Price increased (bullish)
- **Red Candles** - Price decreased (bearish) 
- **Wicks** - Show high/low ranges
- **Body** - Shows open/close range

### Interactive Features
- **Zoom** - Mouse wheel or toolbar
- **Pan** - Click and drag
- **Reset** - Toolbar home button
- **Export** - Save as high-quality image

## 🔧 Configuration

### Environment Variables
Uses existing Yahoo Finance service configuration:
- `MYSQL_HOST` - Database host
- `MYSQL_USER` - Database username
- `MYSQL_PASSWORD` - Database password
- `MYSQL_DATABASE` - Database name (marketdata)

### Default Settings
- **Symbol**: NIFTY
- **Chart Type**: Candlestick
- **Period**: 3 Months
- **Theme**: Dark mode for professional use

## 📋 Error Handling

### Data Validation
- Date range validation (start < end)
- Symbol validation against available data
- Database connectivity checks

### Automatic Fallbacks
- Downloads data if missing from database
- Falls back to line chart if candlestick fails
- Graceful error messages for user guidance

## 🚀 Future Enhancements

### Planned Features
- **Technical Indicators** - Moving averages, RSI, MACD
- **Volume Analysis** - Volume bars below price chart
- **Multiple Symbols** - Compare charts side-by-side
- **Real-time Updates** - Live data streaming
- **Pattern Recognition** - Automatic chart pattern detection

### Integration Options
- **Screening Tools** - Connect with existing stock scanners
- **Alert System** - Price level notifications
- **Portfolio Tracking** - Personal portfolio visualization
- **Backtesting** - Strategy testing framework

## 🎯 Perfect For

### Traders & Investors
- **Technical Analysis** - Professional candlestick charts
- **Trend Analysis** - Multiple timeframe views
- **Decision Making** - Clear visual data representation

### Analysts & Researchers  
- **Market Research** - Historical data visualization
- **Report Generation** - Export charts for presentations
- **Data Exploration** - Interactive chart navigation

### Developers
- **Integration Ready** - Modular architecture
- **Extensible** - Easy to add new features
- **Well Documented** - Clear code structure

---

**🎉 Ready to Use!** Launch the chart visualizer and start exploring market data with professional-grade visualizations!