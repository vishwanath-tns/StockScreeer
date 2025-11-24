# Stock Screener - Version History

## v2.0.0 - Intraday Data Viewer with Charts (November 24, 2025)

### Major Features Added
- **Intraday 1-Minute Data Viewer with Interactive Charts**
  - Candlestick chart visualization for price action (50% screen)
  - Market breadth indicators with dual chart display (50% screen)
  - Three-panel layout: Candlesticks, A-D Difference, Separate A-D Lines
  - Interactive matplotlib charts with zoom, pan, and export capabilities
  - Tabbed interface: Charts tab and Data Table tab

### New Files Created
- `intraday_1min_viewer_charts.py` - Main viewer application with charting
- `intraday_1min_viewer.py` - Original table-only viewer (legacy)
- `INTRADAY_CHARTS_GUIDE.md` - Comprehensive user guide for chart viewer
- `INTRADAY_VIEWER_GUIDE.md` - Documentation for table viewer

### Database & Data Management
- `rebuild_intraday_data.py` - Bulk download 1-minute candles from Yahoo Finance
- `download_tatamotors.py` - Handle TATAMOTORS symbol change (TMCV.NS)
- `check_intraday_data.py` - Comprehensive data verification script
- `verify_nifty50.py` - Verify Nifty 50 stock coverage

### Chart Features
- **Candlestick Chart (Top 50%)**
  - Traditional OHLC candlestick rendering
  - Color-coded: Green (bullish), Red (bearish)
  - High-low wicks showing full price range
  - Interactive zoom and pan via matplotlib toolbar

- **Advance-Decline Difference Chart (Middle 25%)**
  - Net difference line (Advances - Declines)
  - Filled areas: Green (net advance), Red (net decline)
  - Zero-line reference for sentiment tracking

- **Separate A-D Lines Chart (Bottom 25%)**
  - Individual lines for Advances (green) and Declines (red)
  - Direct comparison of absolute stock counts
  - Crossover detection for sentiment shifts

### Real-time Market Breadth System
- `realtime_market_breadth/` - Complete real-time breadth tracking system
  - 16 files, ~200k lines of code
  - WebSocket integration for live data
  - Advance-decline calculations and storage
  - Dashboard and monitoring tools

### Supporting Scripts
- `check_nifty50_coverage.py` - Check Nifty 50 data coverage
- `check_symbol_format.py` - Verify database symbol format
- `check_table_struct.py` - Inspect table structure
- `realtime_adv_decl_dashboard.py` - Real-time breadth dashboard
- `run_queue_processor.py` - Background queue processing

### Data Coverage
- **932,563 total 1-minute candles**
- **511 symbols** (510 Nifty 500 stocks + NIFTY index)
- **5 trading days** (November 18-24, 2025)
- **100% Nifty 50 coverage** (all 50 stocks included)
- **~375 candles per day** per stock (9:15 AM - 3:29 PM IST)

### Technical Improvements
- SQLAlchemy 2.x with URL.create for secure connections
- Matplotlib integration with TkAgg backend
- GridSpec for precise subplot height ratios (2:1:1)
- Navigation toolbar for chart interaction
- CSV export functionality
- Multi-threaded data download (10 workers)

### Dependencies Added
- matplotlib 3.10.7 (already present)
- yfinance (for Yahoo Finance API)
- pytz (for IST timezone handling)

---

## v1.x - Previous Features (Before November 24, 2025)

### Existing Core Features
- BHAV data synchronization (`sync_bhav_gui.py`)
- VCP pattern detection and scanning
- Cup-and-handle pattern analysis
- Sectoral analysis and reports
- Nifty 50/500 scanners
- PDF report generation
- Chart tools and visualization
- Vedic astrology integration
- Technical indicator calculations
- Moving average computations
- Trend analysis and rating systems
- MySQL database integration
- Data completeness reporting

### Key Files (Pre-v2.0)
- Multiple scanner scripts (VCP, momentum, sectoral)
- Chart generation tools
- Database management utilities
- Verification and validation scripts
- PDF report generators
- Analysis and computation engines

---

## Version Naming Convention
- **Major version** (X.0.0): Significant new features or architecture changes
- **Minor version** (x.Y.0): New features, enhancements, non-breaking changes
- **Patch version** (x.y.Z): Bug fixes, minor improvements, documentation updates

## Future Roadmap
- v2.1.0: Volume overlay on candlestick chart
- v2.2.0: Moving averages (5, 10, 20 period)
- v2.3.0: Multiple timeframe aggregation (5-min, 15-min)
- v2.4.0: Real-time live data updates
- v3.0.0: Multi-stock comparison and overlay features

---
**Last Updated**: November 24, 2025  
**Current Version**: v2.0.0
