# Nifty 50 with Sun Planetary Cycles - Visualization Guide

## Overview
This visualization tool combines **Nifty 50 candlestick charts** with **Sun's planetary position indicator** based on Vedic astrology, allowing you to analyze market movements in relation to solar cycles.

## Features

### 1. **Nifty 50 Candlestick Chart** (Top Panel)
- Full OHLC (Open, High, Low, Close) candlesticks
- Green candles: Bullish (close > open)
- Red candles: Bearish (close < open)
- Date range: 2023 to current date
- Price displayed in ₹ (Indian Rupees)

### 2. **Sun Planetary Position Indicator** (Bottom Panel)
- Shows Sun's longitude position (0-360°) through the zodiac
- Orange line tracks Sun's movement through 12 zodiac signs
- Vertical dotted lines mark sign transitions (e.g., Aries → Taurus)
- Horizontal reference lines at key degrees:
  - 0° = Aries start
  - 90° = Cancer start  
  - 180° = Libra start
  - 270° = Capricorn start

## Data Sources

✅ **No new downloads required!** Uses existing data:

- **Nifty prices**: `yfinance_daily_quotes` table (symbol: ^NSEI)
- **Sun positions**: `planetary_positions` table (minute-level data aggregated to daily)

## How to Use

### Step 1: Launch the Application
```powershell
cd D:\MyProjects\StockScreeer\vedic_astrology
python nifty_sun_visualization.py
```

### Step 2: Load Data
1. Set date range (default: 2023-01-01 to today)
2. Click **"Load Data"** button
3. Wait for confirmation message showing records loaded

### Step 3: Generate Chart
1. Click **"Plot Chart"** button
2. Chart will display both panels:
   - Top: Nifty candlesticks
   - Bottom: Sun position line

### Step 4: Analyze
- Look for correlations between Sun sign changes and market movements
- Observe if Nifty shows patterns during specific zodiac signs
- Use zoom/pan tools to focus on specific periods

## Vedic Astrology Interpretation

### Sun's Zodiac Journey
The Sun takes approximately **30 days** to transit through each zodiac sign:

| Sign | Typical Period | Market Characteristics (Traditional) |
|------|---------------|--------------------------------------|
| **Aries** (0-30°) | Mar-Apr | Aggressive, impulsive moves |
| **Taurus** (30-60°) | Apr-May | Stable, value-focused |
| **Gemini** (60-90°) | May-Jun | Volatile, communication-driven |
| **Cancer** (90-120°) | Jun-Jul | Emotional, sentiment-driven |
| **Leo** (120-150°) | Jul-Aug | Confident, leadership themes |
| **Virgo** (150-180°) | Aug-Sep | Analytical, correction phase |
| **Libra** (180-210°) | Sep-Oct | Balanced, indecisive |
| **Scorpio** (210-240°) | Oct-Nov | Intense, transformative |
| **Sagittarius** (240-270°) | Nov-Dec | Optimistic, expansionary |
| **Capricorn** (270-300°) | Dec-Jan | Conservative, structural |
| **Aquarius** (300-330°) | Jan-Feb | Innovative, unpredictable |
| **Pisces** (330-360°) | Feb-Mar | Dreamy, speculative |

### Key Observations to Look For

1. **Sign Transitions**: Do markets show increased volatility when Sun changes signs?

2. **Cardinal Signs** (Aries, Cancer, Libra, Capricorn): Initiating energy - potential trend starts?

3. **Fixed Signs** (Taurus, Leo, Scorpio, Aquarius): Sustained energy - trend continuation?

4. **Mutable Signs** (Gemini, Virgo, Sagittarius, Pisces): Changing energy - reversals?

5. **Fire Signs** (Aries, Leo, Sagittarius): Bullish energy - uptrends more common?

6. **Earth Signs** (Taurus, Virgo, Capricorn): Stable energy - consolidation phases?

7. **Air Signs** (Gemini, Libra, Aquarius): Communication-driven - news-based moves?

8. **Water Signs** (Cancer, Scorpio, Pisces): Emotional energy - sentiment extremes?

## Technical Details

### Date Range Selection
- Format: `YYYY-MM-DD`
- Default from: `2023-01-01`
- Default to: Current date
- Maximum range: Limited by available data (2023-2025)

### Chart Controls
- **Zoom**: Use toolbar or scroll to zoom in/out
- **Pan**: Click and drag to move around
- **Reset**: Home button to reset view
- **Save**: Disk icon to export chart as PNG

### Performance
- Loading 1-2 years of data: ~2-5 seconds
- Rendering chart: ~3-5 seconds
- Smooth interactive navigation

## Analysis Tips

### Correlation Analysis
1. **Visual inspection**: Look for patterns where Sun sign changes align with trend changes
2. **Support/Resistance**: Do certain Sun positions coincide with price levels?
3. **Volatility**: Does market volatility increase during specific signs?
4. **Seasonal patterns**: Compare same Sun positions across different years

### Advanced Research Questions
- Does Nifty perform better in fire signs vs earth signs?
- Are sign transitions (sandhi) associated with reversals?
- Do retrogrades of other planets (shown in other visualizations) matter more?
- How do Sun-Mars conjunctions correlate with energy sector stocks?

## Database Schema Reference

### Nifty Data (yfinance_daily_quotes)
```sql
SELECT date, open, high, low, close, volume
FROM yfinance_daily_quotes
WHERE symbol = '^NSEI'
```

### Sun Position Data (planetary_positions)
```sql
SELECT DATE(timestamp) as date, 
       sun_longitude,    -- 0 to 360 degrees
       sun_sign,         -- Zodiac sign name
       sun_degree        -- Degree within sign (0-30)
FROM planetary_positions
WHERE DATE(timestamp) >= '2023-01-01'
GROUP BY DATE(timestamp)
```

## Troubleshooting

### "No Nifty data found"
- Ensure ^NSEI symbol was downloaded via Yahoo Finance downloader
- Check date range is within 2020-2025 (available data period)
- Verify database connection

### "No Sun position data found"
- Confirm planetary_positions table has data for selected dates
- Check timestamp coverage (should be 2023-2025)
- Try broader date range

### Chart not displaying
- Click "Load Data" before "Plot Chart"
- Ensure both datasets loaded successfully (check info label)
- Try reducing date range if too much data

### Performance issues
- Reduce date range (e.g., 6 months instead of 3 years)
- Close other applications to free memory
- Use zoom to focus on specific periods

## Future Enhancements

Potential additions to this visualization:

1. **Multi-Planet Overlay**: Add Moon, Mars, Jupiter positions
2. **Planetary Aspects**: Mark conjunctions, oppositions, trines
3. **Nakshatra Bands**: Show 27 lunar mansions as background
4. **Volume Correlation**: Color-code volume by Sun sign
5. **Statistical Analysis**: Automatic correlation calculation
6. **Sector Comparison**: Show sector performance by Sun sign
7. **Export Reports**: PDF reports with interpretations
8. **Real-time Updates**: Auto-refresh with latest data

## Related Tools

- **`planetary_position_viewer.py`**: View planetary positions for any date/time
- **`vedic_trading_gui.py`**: Real-time trading dashboard with all planets
- **`market_forecast.py`**: 4-week market predictions
- **`weekly_outlook.py`**: 7-day outlook with sector recommendations

## References

- Swiss Ephemeris: Professional astronomical calculations
- Vedic Astrology: Traditional Sidereal zodiac system
- Market Data: Yahoo Finance via yfinance library
- Database: MySQL MarketData schema

## Support

For issues or enhancements:
1. Check database connectivity
2. Verify data availability in tables
3. Review error messages in status bar
4. Check console output for detailed errors

---

**Remember**: This is a research and analysis tool. Astrological indicators should be used alongside traditional technical and fundamental analysis, not as standalone trading signals.

**Disclaimer**: Past correlations do not guarantee future market movements. Always do your own research and risk management.
