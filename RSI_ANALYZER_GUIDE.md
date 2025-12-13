# RSI Overbought/Oversold Analyzer
## Relative Strength Index Analysis Tool

Analyzes RSI (9-period) values to identify overbought and oversold conditions in NIFTY 50 and NIFTY 500 stocks.

---

## Quick Start

### Option 1: Interactive GUI (Recommended)
```powershell
python rsi_overbought_oversold_gui.py
```

**Features:**
- Real-time RSI status display with color coding
- Filter by NIFTY 50 or NIFTY 500 index
- Interactive tables with sorting and filtering
- Summary statistics and breakdown analysis
- Auto-refresh every 60 seconds (configurable)
- Export to CSV/XLSX

### Option 2: Command-Line CLI
```powershell
python rsi_overbought_oversold_analyzer.py
```

**Output:**
- Console report with formatted tables
- CSV export to `reports_output/` folder
- Overbought, Oversold, and Neutral stock lists

---

## Configuration

### Thresholds
- **Overbought**: RSI >= **80**
- **Oversold**: RSI <= **20**
- **Neutral**: 20 < RSI < 80

### RSI Period
- **9 days** (calculated by Daily Data Wizard)

### Data Source
- **Database**: `marketdata`
- **Table**: `yfinance_daily_rsi`
- **Timeframe**: Daily
- **Source**: Yahoo Finance (synced by Daily Data Wizard)

---

## How It Works

### Data Pipeline
1. **Daily Data Wizard** runs daily to:
   - Download daily OHLCV data from Yahoo Finance
   - Calculate Moving Averages (EMA, SMA)
   - Calculate RSI (9-period)
   - Store in `yfinance_daily_rsi` table

2. **RSI Analyzer** reads latest data:
   - Queries latest RSI values for each stock
   - Classifies as Overbought/Oversold/Neutral
   - Displays summary statistics

### RSI Calculation Formula
```
Gain = Average of gains over last 9 days
Loss = Average of losses over last 9 days
RS = Gain / Loss
RSI = 100 - (100 / (1 + RS))
```

### Logic
```
IF RSI >= 80: Stock considered OVERBOUGHT
  - Potential reversal/pullback risk
  - Sell signal in extreme cases
  
IF RSI <= 20: Stock considered OVERSOLD
  - Potential bounce/recovery opportunity
  - Buy signal in extreme cases
  
IF 20 < RSI < 80: Stock NEUTRAL
  - No extreme condition
```

---

## Prerequisites

### Database Setup
Ensure `marketdata` database has the `yfinance_daily_rsi` table created:
```sql
CREATE TABLE yfinance_daily_rsi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    close DECIMAL(15,4),
    rsi_9 DECIMAL(8,4),
    UNIQUE KEY unique_symbol_date (symbol, date),
    INDEX idx_symbol (symbol),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Environment Variables
Set in `.env` file or system environment:
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=marketdata
```

### Dependencies
- pandas
- sqlalchemy
- mysql-connector-python
- python-dotenv
- tabulate (for CLI)
- PyQt5 (for GUI)

**Install:**
```powershell
pip install pandas sqlalchemy mysql-connector-python python-dotenv tabulate PyQt5
```

---

## Data Workflow

### Before Running Analyzer
1. Run **Daily Data Wizard** to populate `yfinance_daily_rsi` table:
   ```powershell
   python wizards/daily_data_wizard.py
   ```

2. The wizard will:
   - Download latest daily data for NIFTY 500 stocks
   - Calculate RSI 9 for all stocks
   - Update `yfinance_daily_rsi` table

### Then Run Analyzer
Once data is available, use analyzer to identify conditions.

---

## Stocks Analyzed

### NIFTY 50
50 large-cap stocks, including:
- RELIANCE, TCS, HDFCBANK, INFY, WIPRO
- ICICIBANK, SBIN, AXISBANK, BAJAJFINSV, MARUTI
- And 40 more...

### NIFTY 500
Full NIFTY 500 index (500 stocks):
- All large-cap, mid-cap, and small-cap constituents
- Updated periodically with NSE index changes

---

## Output

### GUI Dashboard
1. **Overbought Tab**
   - Stocks with RSI >= 80
   - Sorted by RSI (highest first)
   - Color-coded in red

2. **Oversold Tab**
   - Stocks with RSI <= 20
   - Sorted by RSI (lowest first)
   - Color-coded in green

3. **Neutral Tab**
   - Top 50 neutral stocks
   - Sorted by RSI (highest first)

4. **Summary Tab**
   - Count of overbought/oversold/neutral
   - Percentage breakdown
   - Data source information

### CSV Export
Sample output file: `rsi_analysis_nifty50_20251212_005712.csv`

```
symbol,date,close,rsi_9,status
TCS,2025-12-12,3245.50,82.15,OVERBOUGHT
INFY,2025-12-12,2820.30,78.90,NEUTRAL
RELIANCE,2025-12-12,2950.75,15.30,OVERSOLD
...
```

---

## Usage Examples

### Example 1: GUI Analysis
```powershell
# Launch interactive dashboard
python rsi_overbought_oversold_gui.py

# - Select NIFTY 50 or NIFTY 500
# - View overbought/oversold stocks
# - Click "Export to CSV" to save results
# - Auto-refresh checks every 60 seconds
```

### Example 2: CLI Report
```powershell
# Generate console report
python rsi_overbought_oversold_analyzer.py

# Output:
# - NIFTY 50 analysis with tables
# - NIFTY 500 analysis with tables
# - CSV files saved to reports_output/
```

### Example 3: Programmatic Use
```python
from rsi_overbought_oversold_analyzer import RSIAnalyzerDB, RSIAnalyzer

db = RSIAnalyzerDB()
analyzer = RSIAnalyzer(db)

# Analyze NIFTY 50
result = analyzer.analyze_nifty50()
print(f"Overbought: {len(result['overbought'])}")
print(f"Oversold: {len(result['oversold'])}")

# Get specific stock history
history = db.get_rsi_history('RELIANCE', days=30)
```

---

## Troubleshooting

### "No data available for analysis"
**Cause:** `yfinance_daily_rsi` table is empty
**Solution:**
1. Run Daily Data Wizard first: `python wizards/daily_data_wizard.py`
2. Wait for wizard to complete (5-30 minutes depending on system)
3. Check database: `SELECT COUNT(*) FROM yfinance_daily_rsi;`

### "ModuleNotFoundError: tabulate"
**Solution:**
```powershell
pip install tabulate
```

### "ModuleNotFoundError: PyQt5"
**Solution:**
```powershell
pip install PyQt5 PyQtChart
```

### MySQL Connection Error
**Check:**
1. `.env` file has correct credentials
2. MySQL server is running
3. `marketdata` database exists
4. User has appropriate permissions

---

## Integration with Other Tools

### Daily Data Wizard
- Automatically populates `yfinance_daily_rsi` table daily
- No manual action needed

### Volume Cluster Analysis
- Can combine with volume analysis for trading decisions
- RSI overbought + falling volume = potential reversal

### Golden/Death Cross Scanner
- Combine SMA signals with RSI extremes for confirmation
- RSI >= 80 + price above 200 SMA = caution
- RSI <= 20 + price below 200 SMA = opportunity

### Mean Reversion Scanner
- RSI < 30 = potential mean reversion candidates
- Screen for extreme RSI as part of broader analysis

---

## Performance Notes

- **Query Time**: < 2 seconds for 500 stocks
- **Memory**: < 50 MB for full NIFTY 500 analysis
- **Database Size**: ~5-10 MB per year of daily RSI data
- **GUI Refresh**: 60 seconds (configurable)

---

## Theory Behind RSI

### What is Relative Strength Index?
- Momentum oscillator measuring speed/magnitude of price changes
- Range: 0-100
- Develops on intraday time series: every minute, every 5 minutes, hourly
- Oscillates around 50

### Interpretation
- **Above 70**: Suggests uptrend strength (can also indicate overbought)
- **Above 80**: Strong overbought signal (this analyzer focuses on >= 80)
- **Below 30**: Suggests downtrend strength (can also indicate oversold)
- **Below 20**: Strong oversold signal (this analyzer focuses on <= 20)

### Divergence Patterns
- **Bullish Divergence**: Price makes new low but RSI doesn't (potential reversal)
- **Bearish Divergence**: Price makes new high but RSI doesn't (potential reversal)

See also: [RSI Divergences Scanner](scanners/rsi_divergences.py)

---

## Related Tools

| Tool | Purpose |
|------|---------|
| Daily Data Wizard | Sync daily data & calculate RSI 9 |
| Golden/Death Cross Scanner | 50/200 SMA crossovers |
| Mean Reversion Scanner | RSI + Bollinger Bands extremes |
| Price Cluster Analyzer | Support/resistance levels |
| Volume Cluster Analysis | Volume-price patterns |

---

## Change Log

### v1.0 (December 2025)
- Initial release
- RSI >= 80 / <= 20 analysis
- NIFTY 50 & NIFTY 500 support
- GUI dashboard with auto-refresh
- CLI tool with CSV export
- Database integration with Daily Data Wizard

---

## Questions?

Refer to project documentation:
- `MASTER_INDEX.md` - Complete project reference
- `QUICKSTART.md` - Getting started guide
- `launcher.py` - Launch any project tool

