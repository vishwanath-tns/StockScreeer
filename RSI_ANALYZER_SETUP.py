#!/usr/bin/env python3
"""
RSI Analyzer Setup Guide
========================

Instructions to get RSI Overbought/Oversold Analyzer working.
"""

setup_guide = """
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              RSI OVERBOUGHT/OVERSOLD ANALYZER - SETUP GUIDE                ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

QUICK START (3 STEPS)
════════════════════════════════════════════════════════════════════════════

Step 1: Populate Data
─────────────────────
Run Daily Data Wizard to calculate RSI for all stocks:

  python wizards/daily_data_wizard.py

This will:
  ✓ Download daily data for all NIFTY 500 stocks
  ✓ Calculate RSI (9-period) for each stock
  ✓ Store in marketdata.yfinance_daily_rsi table
  
⏱️  Time: 10-30 minutes (depending on system & network)


Step 2: Launch RSI Analyzer
───────────────────────────
Option A - Interactive GUI Dashboard (RECOMMENDED):

  python rsi_overbought_opensold_gui.py

  Features:
  • Color-coded RSI values (red=overbought, green=oversold)
  • Filter by NIFTY 50 or NIFTY 500
  • Auto-refresh every 60 seconds
  • Export to CSV/XLSX
  • View stock history and trends


Option B - Command-Line Report:

  python rsi_overbought_oversold_analyzer.py

  Features:
  • Console report with formatted tables
  • CSV export to reports_output/
  • Good for scheduled runs/automation


Step 3: Interpret Results
──────────────────────────
The analyzer shows:

  OVERBOUGHT (RSI >= 80):
  • Potential pullback or reversal risk
  • Consider taking profits on long positions
  • Watch for divergence signals

  OVERSOLD (RSI <= 20):
  • Potential bounce or recovery opportunity
  • Consider taking positions on strength
  • Watch for divergence signals

  NEUTRAL (20 < RSI < 80):
  • No extreme condition
  • Normal momentum range


════════════════════════════════════════════════════════════════════════════════

DETAILED SETUP
════════════════════════════════════════════════════════════════════════════════

1. ENVIRONMENT SETUP
─────────────────────

A. Python Environment
   • Python 3.11+ (verify: python --version)
   • Virtual environment (recommended)

B. Required Packages
   Install dependencies:
   
     pip install pandas sqlalchemy mysql-connector-python python-dotenv tabulate PyQt5 PyQtChart

   Or use requirements.txt:
   
     pip install -r requirements.txt

C. Database Configuration
   Edit .env file in project root:
   
     MYSQL_HOST=localhost
     MYSQL_PORT=3306
     MYSQL_USER=root
     MYSQL_PASSWORD=your_password
     MYSQL_DATABASE=marketdata
   
   Verify MySQL is running:
   
     mysql -u root -p
     USE marketdata;
     SHOW TABLES LIKE 'yfinance_daily_rsi';


2. DATA POPULATION
───────────────────

A. First-Time Setup (REQUIRED BEFORE USING ANALYZER)
   
   Run Daily Data Wizard:
   
     python wizards/daily_data_wizard.py
   
   This will:
   1. Sync daily data for all NIFTY 500 stocks
   2. Calculate moving averages (EMA, SMA)
   3. Calculate RSI (9-period)
   4. Store results in marketdata database
   
   Expected Output:
   
     Step 1 of 6: Sync daily data for all Nifty 500 stocks
     Step 2 of 6: Sync intraday data...
     Step 3 of 6: Verify data...
     Step 4 of 6: Calculate moving averages...
     Step 5 of 6: Calculate RSI (9)...
     Step 6 of 6: Update rankings...
     
     [COMPLETE] All steps completed successfully!

B. Regular Updates (DAILY)
   
   Run wizard daily to keep data current:
   
     python wizards/daily_data_wizard.py
   
   Or schedule via Windows Task Scheduler / cron


3. RUNNING THE ANALYZER
────────────────────────

Option A: GUI Dashboard
   
   Command:
     python rsi_overbought_oversold_gui.py
   
   Interface:
   • 4 tabs: Overbought | Oversold | Neutral | Summary
   • Sort/filter by clicking column headers
   • Auto-refresh every 60 seconds
   • Click "Export to CSV" to save results
   
   Keyboard Shortcuts:
   • Ctrl+Q: Quit
   • Alt+F4: Close window

Option B: CLI Tool
   
   Command:
     python rsi_overbought_oversold_analyzer.py
   
   Output:
   • Console report with NIFTY 50 & NIFTY 500 analysis
   • CSV files: reports_output/rsi_analysis_*.csv
   • Overbought/Oversold/Neutral tables
   
   CSV Columns:
   • symbol: Stock ticker
   • date: Data date
   • close: Close price
   • rsi_9: RSI (9-period) value
   • status: OVERBOUGHT | OVERSOLD | NEUTRAL

Option C: Launcher Menu
   
   Command:
     python launcher.py
   
   Then select:
     🔍 Scanners > RSI Overbought/Oversold (GUI)
     🔍 Scanners > RSI Overbought/Oversold (CLI)


════════════════════════════════════════════════════════════════════════════════

UNDERSTANDING THE DATA
════════════════════════════════════════════════════════════════════════════════

RSI Calculation:
───────────────
RSI (Relative Strength Index) measures momentum on a scale of 0-100.

Formula:
  Gain = Average gains over last 9 days
  Loss = Average losses over last 9 days
  RS = Gain / Loss
  RSI = 100 - (100 / (1 + RS))

Interpretation:
  • RSI >= 80: Overbought (potential pullback)
  • RSI <= 20: Oversold (potential bounce)
  • 20 < RSI < 80: Neutral (no extreme)

Example:
  If RELIANCE has RSI = 85:
    Status: OVERBOUGHT
    Interpretation: Strong uptrend, but at risk of pullback
    Action: Consider taking profits or waiting for dip


Database Structure:
──────────────────
Table: yfinance_daily_rsi (in marketdata database)

Columns:
  • id: Auto-increment primary key
  • symbol: Stock symbol (e.g., 'RELIANCE')
  • date: Trading date
  • close: Closing price
  • rsi_9: RSI (9-period) value
  • updated_at: Timestamp of last update

Unique Key: (symbol, date)
Indices: symbol, date (for fast queries)


════════════════════════════════════════════════════════════════════════════════

TROUBLESHOOTING
════════════════════════════════════════════════════════════════════════════════

Problem: "No data available for analysis"
────────────────────────────────────────
Cause: Table yfinance_daily_rsi is empty

Solution:
  1. Run Daily Data Wizard: python wizards/daily_data_wizard.py
  2. Wait for completion (10-30 minutes)
  3. Verify data: SELECT COUNT(*) FROM yfinance_daily_rsi;
  4. Try analyzer again


Problem: "ModuleNotFoundError: tabulate"
────────────────────────────────────────
Cause: Package not installed

Solution:
  pip install tabulate


Problem: "ModuleNotFoundError: PyQt5"
──────────────────────────────────────
Cause: PyQt5 not installed

Solution:
  pip install PyQt5 PyQtChart


Problem: "MySQL connection error"
─────────────────────────────────
Cause: Database configuration issue

Solution:
  1. Verify MySQL is running
  2. Check .env file credentials
  3. Test connection: mysql -u root -p -h localhost
  4. Verify marketdata database exists
  5. Check user permissions


Problem: "SQLAlchemy: Could not create engine"
──────────────────────────────────────────────
Cause: Invalid connection string (usually password with special chars)

Solution:
  • .env password special chars must be URL-encoded
  • Example: password123@! becomes password123%40%21
  • Or: Use single quotes in .env: MYSQL_PASSWORD='your@pass!'


Problem: "PyQt5: No module named 'PyQt5.QtChart'"
──────────────────────────────────────────────────
Cause: PyQtChart not installed

Solution:
  pip install PyQtChart


════════════════════════════════════════════════════════════════════════════════

COMMON WORKFLOWS
════════════════════════════════════════════════════════════════════════════════

Workflow 1: Daily Morning Review
────────────────────────────────
1. Open launcher: python launcher.py
2. Run Daily Data Wizard (if not scheduled)
3. Open RSI Analyzer GUI
4. Review NIFTY 50 overbought/oversold stocks
5. Cross-reference with volume/support-resistance levels
6. Plan day's trades

Workflow 2: Scheduled Analysis
───────────────────────────────
1. Schedule Daily Data Wizard to run daily at market open
2. Schedule RSI Analyzer CLI to export CSV after wizard
3. Load CSV in Excel/Google Sheets for analysis
4. Alert if > 5 stocks in overbought/oversold

Workflow 3: Integration with Other Scanners
────────────────────────────────────────────
1. Run RSI Analyzer to get overbought/oversold lists
2. Cross-check with Golden/Death Cross Scanner
3. Cross-check with Volume Cluster Analysis
4. Combine signals for high-conviction trades

Workflow 4: Programming Integration
───────────────────────────────────
from rsi_overbought_oversold_analyzer import RSIAnalyzerDB, RSIAnalyzer

db = RSIAnalyzerDB()
analyzer = RSIAnalyzer(db)

result = analyzer.analyze_nifty50()
for stock in result['overbought']:
    print(f"{stock['symbol']}: RSI={stock['rsi_9']}")


════════════════════════════════════════════════════════════════════════════════

ADVANCED USAGE
════════════════════════════════════════════════════════════════════════════════

Custom Thresholds:
──────────────────
Edit rsi_overbought_oversold_analyzer.py:

  # Change from:
  RSI_OVERBOUGHT = 80
  RSI_OVERSOLD = 20
  
  # To:
  RSI_OVERBOUGHT = 75      # More aggressive
  RSI_OVERSOLD = 25        # More aggressive


Different Time Periods:
───────────────────────
Extend analyzer to support:
  • RSI 14 (more common in traditional TA)
  • RSI 21 (longer-term)
  
Currently hardcoded to 9-day RSI by Daily Data Wizard.


Auto-Refresh Interval:
──────────────────────
Edit rsi_overbought_oversold_gui.py:

  # Change from:
  REFRESH_INTERVAL = 60000  # 60 seconds
  
  # To:
  REFRESH_INTERVAL = 30000  # 30 seconds


════════════════════════════════════════════════════════════════════════════════

FILE LOCATIONS
════════════════════════════════════════════════════════════════════════════════

Analyzer Files:
  • rsi_overbought_oversold_analyzer.py    [CLI tool]
  • rsi_overbought_oversold_gui.py         [GUI dashboard]
  • RSI_ANALYZER_GUIDE.md                  [Full documentation]

Related Files:
  • wizards/daily_data_wizard.py           [Data sync & RSI calculation]
  • launcher.py                            [Central launcher menu]

Output Files:
  • reports_output/rsi_analysis_*.csv      [Exported analysis]

Configuration:
  • .env                                   [Database credentials]


════════════════════════════════════════════════════════════════════════════════

MORE INFORMATION
════════════════════════════════════════════════════════════════════════════════

Documentation:
  • RSI_ANALYZER_GUIDE.md - Full feature documentation
  • MASTER_INDEX.md - Complete project reference
  • QUICKSTART.md - Getting started guide

Related Tools:
  • Daily Data Wizard - Syncs data & calculates RSI
  • Golden/Death Cross Scanner - SMA crossover signals
  • Mean Reversion Scanner - RSI + Bollinger Bands
  • Volume Cluster Analysis - Volume pattern detection

Project Home:
  • https://github.com/your-repo
  • Launcher: python launcher.py


════════════════════════════════════════════════════════════════════════════════

SUMMARY
════════════════════════════════════════════════════════════════════════════════

✓ RSI Overbought/Oversold Analyzer is now available
✓ Two interfaces: GUI (interactive) & CLI (automated)
✓ Uses existing Daily Data Wizard infrastructure
✓ NIFTY 50 & NIFTY 500 support
✓ CSV export for further analysis
✓ Automatic daily updates via wizard

Ready to use!

Questions? See RSI_ANALYZER_GUIDE.md for detailed documentation.

════════════════════════════════════════════════════════════════════════════════
"""

if __name__ == '__main__':
    print(setup_guide)
