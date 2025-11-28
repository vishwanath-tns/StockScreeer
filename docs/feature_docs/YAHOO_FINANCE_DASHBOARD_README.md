# Yahoo Finance Features Dashboard

## 📊 Overview

A centralized dashboard providing access to all Yahoo Finance related features, tools, and diagnostics implemented in this project.

## 🚀 Quick Start

Launch the dashboard:
```powershell
python yahoo_finance_dashboard.py
```

## 📑 Features Organized by Category

### 1. 📥 Download Data Tab

#### Main Download Tools
- **Yahoo Finance Data Downloader (GUI)** - Full-featured interface for downloading daily stock and index data
- **Chart Visualizer & Downloader** - Download data and visualize charts with technical indicators
- **Bulk Stock Downloader** - Download data for multiple stocks with progress tracking

#### Quick Download Scripts
- **Check & Update Daily Quotes** - Automatically check and download missing dates
- **Quick Download Today's Data** - Fast download of today's data for all symbols
- **Quick Download Nifty 500** - Download last 7 days for all Nifty 500 stocks
- **Download Nifty 500 Bulk (5 Years)** - Comprehensive 5-year historical download
- **Download Indices Data** - Historical data for NSE indices
- **Download Indices Today** - Today's data for all NSE indices

#### Smart Download Tools
- **Smart Download (CLI)** - Advanced downloader with duplicate prevention
- **Symbol Mapping Validator** - Validate NSE to Yahoo Finance mappings

### 2. 🔍 Diagnostics Tab

#### Data Completeness Checks
- **Check All Symbols Completeness** - Comprehensive data completeness analysis
- **Check Nifty 500 Yesterday's Data** - Verify yesterday's data availability
- **Check Previous Close Coverage** - Analyze previous close data coverage
- **Check Nifty 500 Coverage** - Overall coverage statistics

#### Symbol & Mapping Checks
- **Analyze Symbol Formats** - Review symbol format consistency
- **Check Symbol Mappings** - Verify NSE to Yahoo mappings
- **Check Active Symbols** - Review active symbol status
- **Find Optimal Symbol List** - Identify symbols with complete data

#### Database Checks
- **Check Indices Tables** - Verify indices table structure
- **Check Indices Download Status** - Review index download status
- **Check Data Size** - Analyze database table sizes
- **Check Table Structures** - Verify table integrity

#### Specific Symbol Checks
- **Check NIFTY Today** - Verify ^NSEI real-time data
- **Check YFinance Symbols** - List all symbols in database
- **Test Chart Data** - Test chart data retrieval

### 3. ⚡ Real-time Data Tab

#### Real-time Dashboards
- **Real-time Advance-Decline Dashboard** - Live market breadth tracking for Nifty 500
  - Updates every 1 minute during market hours
  - Tracks advancing, declining, unchanged stocks
  - Shows Advance-Decline ratio and spread
  - Historical trend visualization
  - 431+ stocks monitored (86.2% coverage)

- **Intraday Advance-Decline Viewer** - Historical intraday A/D analysis
- **Intraday 1-Min Viewer** - 1-minute candle data viewer
- **Intraday Charts Viewer** - Technical indicator charts

#### Real-time Services
- **Real-time Yahoo Finance Service** - Event-driven streaming service
  - WebSocket support
  - Multiple serialization formats (JSON, MessagePack, Protobuf)
  - Automatic error recovery
  - Database storage
  - Rate limiting and batching

- **Check Service Status** - Monitor service health
- **Real-time Dashboard (HTML)** - Web-based dashboard

#### Market Breadth Analysis
- **Nifty 500 Advance-Decline Calculator** - Calculate A/D metrics
- **Nifty 500 Advance-Decline Visualizer** - Visualize trends
- **Test Market Breadth Integration** - System integration testing

### 4. 📈 Analysis Tab

#### Chart Analysis
- **Chart Visualizer** - Advanced charting with technical indicators
  - Multiple timeframes (Daily, Weekly, Monthly, 1Y, 5Y)
  - 20+ technical indicators
  - Custom date range selection
  - Export capabilities

- **Stock Chart with Ratings** - Charts with trend ratings
- **Launch Stock Charts** - Quick chart access

#### Scanners & Screeners
- **Nifty 500 Momentum Scanner** - Momentum pattern detection
- **Scanner GUI** - Main pattern detection interface
- **VCP Market Scanner** - Volatility Contraction Pattern scanner

#### PDF Reports
- **Nifty 500 Momentum Report (PDF)** - Comprehensive momentum analysis
- **Nifty 50 Sector Report (PDF)** - Sectoral analysis
- **Demo PDF Reports** - Sample reports showcase

#### Data Verification
- **Verify Data Accuracy** - Comprehensive accuracy checks
- **Quick Accuracy Check** - Fast sample verification
- **Test YFinance Connectivity** - API connectivity test

### 5. 🔧 Maintenance Tab

#### Database Setup
- **Create YFinance Tables** - Initialize database tables
- **Setup YFinance Service** - Service configuration and testing
- **Create Indices Tables** - Initialize indices tables

#### Symbol Management
- **Create Symbol Mapping** - Create NSE to Yahoo mappings
- **Auto Map Nifty 500 to Yahoo** - Automatic Nifty 500 mapping
- **Update Symbol Mappings** - Update and verify mappings
- **Auto Verify Symbols** - Automatic verification

#### Data Cleanup
- **Rebuild Intraday Data** - Rebuild 1-minute candle data
- **Rebuild Intraday Full** - Complete intraday rebuild
- **Refetch NIFTY Today** - Refresh today's NIFTY data

#### Documentation
- **Duplicate Prevention Guide** - System documentation
- **Chart Visualizer README** - Charting documentation
- **Real-time Dashboard History** - Version history
- **Market Breadth Features** - Feature documentation

## 📊 Database Tables

### Main Tables
- `yfinance_daily_quotes` - Daily OHLCV data for stocks
- `yfinance_indices_daily_quotes` - Daily data for indices
- `yfinance_intraday_1min` - 1-minute intraday candles
- `nifty500_advance_decline` - Market breadth metrics
- `nse_yahoo_symbol_map` - Symbol mappings (726 total, 500 verified)

### Coverage Statistics
- **Total Records**: 881,552+ in yfinance_daily_quotes
- **Symbols**: 798 distinct symbols
- **Nifty 500 Coverage**: 486/500 (97.2%) - excluding 14 ETFs with delayed updates
- **Date Range**: Historical data from 2020 onwards
- **Update Frequency**: Daily downloads available

## 🔄 Daily Workflow

### Morning Routine (Before Market Opens)
1. Launch **Real-time Advance-Decline Dashboard**
2. Run **Check & Update Daily Quotes** to download yesterday's data
3. Verify coverage with **Check Nifty 500 Yesterday's Data**

### During Market Hours
1. Monitor **Real-time Advance-Decline Dashboard** (updates every 1 min)
2. Use **Intraday 1-Min Viewer** for detailed analysis
3. Access **Chart Visualizer** for technical analysis

### After Market Close
1. Run **Quick Download Today's Data** to fetch today's data
2. Check **Data Completeness** diagnostics
3. Generate **PDF Reports** for analysis

### Weekly Maintenance
1. Run **Check All Symbols Completeness**
2. Update symbol mappings with **Auto Verify Symbols**
3. Run **Check Data Size** to monitor growth

## 🛠️ Technical Details

### Symbol Format
- **NSE Format**: RELIANCE, INFY, TCS
- **Yahoo Format**: RELIANCE.NS, INFY.NS, TCS.NS
- **Indices**: ^NSEI (NIFTY 50), ^BSESN (SENSEX)

### Data Quality
- **Duplicate Prevention**: ON DUPLICATE KEY UPDATE in all downloads
- **Gap Detection**: Automatic missing date identification
- **Verification**: Symbol mapping validation before download
- **Error Handling**: Comprehensive error logging and recovery

### Real-time Features
- **Update Frequency**: 1-minute intervals during market hours
- **Market Hours**: 9:15 AM - 3:30 PM IST (automatic detection)
- **Data Storage**: SQLite queue + MySQL database
- **Performance**: Batch processing (50 symbols/batch), rate limiting (20 calls/min)

## 📈 Advanced Features

### Smart Download System
- Automatic gap detection and filling
- Duplicate prevention (database-level)
- Progress tracking and resumption
- Error recovery and retry logic

### Real-time Streaming Service
- Event-driven architecture
- WebSocket support for live updates
- Multiple serialization formats
- Automatic reconnection
- Database persistence

### Market Breadth Analysis
- Real-time advance-decline tracking
- Historical trend analysis
- Customizable timeframes
- Export to database and CSV

## 🔍 Troubleshooting

### Common Issues

**Issue**: Dashboard shows fewer than 500 stocks
- **Solution**: Run `Quick Download Nifty 500` to download missing data
- **Check**: Use `Check Nifty 500 Yesterday's Data` to identify gaps

**Issue**: Script fails to launch
- **Check**: Python is installed and in PATH
- **Check**: All dependencies installed (`pip install -r requirements.txt`)
- **Check**: Database connection is configured

**Issue**: Real-time dashboard not updating
- **Check**: Market hours (9:15 AM - 3:30 PM IST)
- **Check**: Internet connectivity
- **Check**: Yahoo Finance API is accessible
- **Solution**: Restart dashboard or refetch data

**Issue**: Symbol not found
- **Check**: Symbol exists in `nse_yahoo_symbol_map` table
- **Solution**: Run `Auto Verify Symbols` to update mappings

## 📚 Related Documentation

- `REALTIME_DASHBOARD_VERSION_HISTORY.md` - Dashboard development history
- `MARKET_BREADTH_FEATURES.md` - Market breadth system documentation
- `yahoo_finance_service/DUPLICATE_PREVENTION.md` - Duplicate prevention system
- `yahoo_finance_service/CHART_VISUALIZER_README.md` - Chart visualizer guide
- `realtime_yahoo_service/README.md` - Real-time service documentation
- `realtime_yahoo_service/QUICK_START.md` - Real-time service quick start

## 🎯 Quick Access

Launch the dashboard and click any feature to start. All tools open in new terminal windows for parallel operation.

```powershell
# Start the dashboard
python yahoo_finance_dashboard.py

# Or launch specific tools directly
python yahoo_finance_service/launch_downloader.py
python realtime_adv_decl_dashboard.py
python yahoo_finance_service/chart_visualizer.py
```

## 📊 Statistics & Achievements

- ✅ **726 symbol mappings** (500 verified Nifty 500 stocks)
- ✅ **881,552+ daily records** across 798 symbols
- ✅ **486/500 Nifty stocks** with real-time tracking (97.2%)
- ✅ **1-minute intraday data** for detailed analysis
- ✅ **Automatic daily updates** with gap filling
- ✅ **Real-time market breadth** every 1 minute
- ✅ **Event-driven architecture** for scalable streaming
- ✅ **Comprehensive diagnostics** for data quality

---

**Last Updated**: November 27, 2025
**Dashboard Version**: 1.0
**Total Features**: 70+ tools and scripts
