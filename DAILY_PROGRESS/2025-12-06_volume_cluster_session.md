# Volume Cluster Analysis Session - December 6, 2025

## Summary
Extended the Volume Cluster Analysis module with:
1. Added "Ultra High" volume quintile (4x+ average volume)
2. Created Trading Rules Engine for generating actionable signals
3. Created Trading Rules GUI for interactive signal analysis

---

## 1. Ultra High Quintile Added

### Changes Made:

| File | Change |
|------|--------|
| `volume_cluster_analysis/core/event_analyzer.py` | Added `ULTRA_HIGH_THRESHOLD = 4.0`, logic to classify 4x+ volume as "Ultra High" |
| `volume_cluster_analysis/alerts.py` | Added `'ultra_high_volume': 4.0` threshold, detection with 💥 emoji and "critical" priority |
| `volume_cluster_analysis/scanner.py` | Added `--ultra` CLI flag, updated alert type comments |
| `volume_cluster_analysis/volume_analysis_suite.py` | Added "Ultra High" to quintile dropdown, default selection |
| `volume_cluster_analysis/populate_events.py` | Added "Ultra High" to default quintiles list, updated ORDER BY |

### Database Updated:
- **341 Ultra High events** across 45 stocks
- Total: 22,858 events (High + Very High + Ultra High)

### Volume Classification:
| Quintile | Threshold | Alert Priority |
|----------|-----------|----------------|
| High | 2x avg | medium 📈 |
| Very High | 3x avg | high 🔥 |
| Ultra High | 4x avg | critical 💥 |

### New Scanner Option:
```bash
python -m volume_cluster_analysis.scanner --ultra --days 30
```

---

## 2. Trading Rules Engine Created

### File: `volume_cluster_analysis/trading_rules.py`

### Trading Rules Implemented:

| Rule | Signal | Criteria | Historical Edge |
|------|--------|----------|-----------------|
| **Ultra Volume Breakout** | 🚀 STRONG BUY | 4x+ volume, +3% return | 65% win rate |
| **Volume Breakout** | 📈 BUY | 2x+ volume, +2% return | 60% win rate |
| **Accumulation Day** | 📈 BUY | 1.5x volume, up day, close in upper range | 58% win rate |
| **Gap Up Continuation** | 📈 BUY | 2x volume, 2%+ gap | 55% win rate |
| **Climax Top Warning** | ⚠️ REDUCE | 3.5x volume near 52w high | 65% pullback probability |
| **Volume Breakdown** | ⛔ AVOID | 2x+ volume, -3% return | 60% continuation |
| **Distribution Warning** | 📉 REDUCE | 1.5x volume, down day, weak close | 55% pullback |
| **Capitulation Buy** | 👀 WATCH | 4x+ volume, -5% extreme selling | 70% bounce probability |

### Usage:
```bash
# Get recent trading signals
python -m volume_cluster_analysis.trading_rules --days 7

# Buy signals only
python -m volume_cluster_analysis.trading_rules --buy-only

# View historical rule performance
python -m volume_cluster_analysis.trading_rules --performance
```

### Rule Performance (Last 90 Days):
| Rule | Win% | Expectancy | Profit Factor |
|------|------|------------|---------------|
| Climax Top Warning | 70.4% | +1.36% | 2.76 |
| Ultra Volume Breakout | 66.7% | +1.29% | 2.52 |
| Volume Breakdown Avoid | 69.2% | +0.95% | 2.12 |
| Accumulation Day Buy | 51.0% | +0.59% | 1.64 |

### Signal Output Includes:
- Entry price, Stop Loss, Target 1 & 2
- Risk/Reward ratio
- Historical win rate and average return
- Sample size
- Reasoning (why signal was generated)
- Warnings (if any)

---

## 3. Trading Rules GUI Created

### File: `volume_cluster_analysis/trading_rules_gui.py`

### Features:

**📈 Tab 1: Trading Signals**
- Scan for signals (3, 5, 7, 14, or 30 days lookback)
- Filter by: All, Buy Signals, Avoid Signals, High Confidence
- Sortable columns (click headers)
- Quick summary panel showing top signals
- Export to clipboard (CSV format)
- Color-coded rows: Green (buy), Red (avoid), Orange (watch)

**📊 Tab 2: Rule Performance**
- Analyze rule performance (30, 60, 90, 180, 365 days)
- Shows: Signals, Winners, Losers, Win%, Avg Win, Avg Loss, Expectancy, Profit Factor
- Color-coded by performance (green = good, red = bad)
- Summary with best rule and weighted averages

**🔍 Tab 3: Signal Details**
- Full signal information when you select a row
- Shows: Entry price, Stop Loss, Targets, Risk/Reward
- Volume analysis: Volume, Relative Volume, Quintile
- Historical edge: Win rate, Avg return, Sample size
- Reasoning: Why this signal was generated + warnings

### How to Launch:
```bash
# From command line
python -m volume_cluster_analysis.trading_rules_gui

# Or from launcher.py
python launcher.py
# → Select "Trading Rules GUI" under Volume Cluster Analysis
```

---

## 4. Launcher Updated

Added new tools to `launcher.py` under "📊 Volume Cluster Analysis":

```python
"📊 Volume Cluster Analysis": [
    ("Volume Analysis Suite", "volume_cluster_analysis/volume_analysis_suite.py", "Full GUI: Scanner, Alerts, Patterns, Stock Events (4 tabs)"),
    ("Trading Rules GUI", "volume_cluster_analysis/trading_rules_gui.py", "Interactive GUI for trading signals with rule performance"),
    ("Trading Rules Engine", "volume_cluster_analysis/trading_rules.py", "Generate trading signals based on volume patterns"),
    ("Volume Events GUI", "volume_cluster_analysis/volume_events_gui.py", "Simple view of high volume events with forward returns"),
    ("Volume Scanner (CLI)", "volume_cluster_analysis/scanner.py", "Find recent high volume events from command line"),
    ("Volume Alerts (CLI)", "volume_cluster_analysis/alerts.py", "Check and manage volume alerts from command line"),
    ("Pattern Analyzer (CLI)", "volume_cluster_analysis/pattern_analyzer.py", "Analyze volume-price patterns from command line"),
    ("Populate Events DB", "volume_cluster_analysis/populate_events.py", "Analyze all Nifty 50 stocks and store events in DB"),
],
```

---

## Files Created/Modified This Session

### New Files:
- `volume_cluster_analysis/trading_rules.py` - Trading rules engine with 8 rules
- `volume_cluster_analysis/trading_rules_gui.py` - Interactive GUI with 3 tabs

### Modified Files:
- `volume_cluster_analysis/core/event_analyzer.py` - Added Ultra High threshold
- `volume_cluster_analysis/alerts.py` - Added Ultra High alert detection
- `volume_cluster_analysis/scanner.py` - Added --ultra flag
- `volume_cluster_analysis/volume_analysis_suite.py` - Added Ultra High to dropdown
- `volume_cluster_analysis/populate_events.py` - Added Ultra High to defaults
- `launcher.py` - Added Trading Rules GUI and Engine

---

## Database Statistics

```
Table: volume_cluster_events (marketdata database)
Total Events: 22,858
Unique Stocks: 47 (Nifty 50)

By Quintile:
- High:       11,454 events
- Very High:  11,156 events  
- Ultra High:    341 events
```

---

## Next Steps (Potential Enhancements)

1. **Backtesting Module** - Test rules with actual P&L simulation
2. **Position Sizing** - Calculate optimal position size based on risk
3. **Multi-timeframe Analysis** - Confirm signals on weekly/monthly
4. **Sector Filter** - Filter signals by sector/industry
5. **Real-time Integration** - Live alerts when signals trigger
6. **Portfolio Tracking** - Track open positions from signals

---

## Commands Reference

```bash
# Scanner
python -m volume_cluster_analysis.scanner --days 7
python -m volume_cluster_analysis.scanner --ultra --days 30
python -m volume_cluster_analysis.scanner --breakouts
python -m volume_cluster_analysis.scanner --patterns

# Alerts
python -m volume_cluster_analysis.alerts --check
python -m volume_cluster_analysis.alerts --recent
python -m volume_cluster_analysis.alerts --summary

# Trading Rules
python -m volume_cluster_analysis.trading_rules --days 7
python -m volume_cluster_analysis.trading_rules --buy-only
python -m volume_cluster_analysis.trading_rules --performance

# GUIs
python -m volume_cluster_analysis.trading_rules_gui
python -m volume_cluster_analysis.volume_analysis_suite

# Database
python -m volume_cluster_analysis.populate_events
```
