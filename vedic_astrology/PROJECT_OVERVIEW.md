# Vedic Astrology Integration for Stock Screener

## Project Overview

This module integrates traditional Vedic astrology principles with modern stock market analysis to provide unique insights based on lunar cycles, planetary positions, and auspicious timings according to ancient Indian astronomical wisdom.

## 🌙 Core Concepts & Integration Areas

### 1. **Moon Cycles & Market Correlation**
```
New Moon (Amavasya)     → Market bottoms, fresh starts, accumulation phase
Waxing Moon (Shukla)    → Growing momentum, bullish trends, expansion
Full Moon (Purnima)     → Market peaks, high volatility, profit booking
Waning Moon (Krishna)   → Consolidation, correction phase, distribution
```

### 2. **Nakshatra-Based Analysis** (27 Lunar Mansions)
```
Each Nakshatra (13°20' of zodiac) has specific characteristics:
- Ashwini: Swift movements, sudden changes
- Bharani: Transformation, volatile periods  
- Kritika: Sharp movements, decisive trends
- Rohini: Stability, growth phases
- Mrigashira: Search for value, research periods
- Ardra: Storms, market disruptions
- Punarvasu: Recovery, return of confidence
- Pushya: Nourishment, steady growth
- Ashlesha: Hidden factors, insider activities
... (continuing for all 27)
```

### 3. **Planetary Influences on Market Sectors**
```
Sun (Surya)      → Banking, Government, Gold, Leadership stocks
Moon (Chandra)   → FMCG, Dairy, Water, Emotional sectors
Mars (Mangal)    → Defense, Steel, Real Estate, Energy
Mercury (Budh)   → IT, Communication, Media, Trading
Jupiter (Guru)   → Finance, Education, Banking, Wisdom sectors
Venus (Shukra)   → Luxury, Entertainment, Beauty, Arts
Saturn (Shani)   → Infrastructure, Oil, Mining, Long-term assets
```

### 4. **Auspicious Timings (Muhurat) for Trading**
```
Brahma Muhurat: 4:00-6:00 AM    → Best for long-term investments
Abhijit Muhurat: 11:45-12:30 PM → Auspicious for all activities
Godhuli Muhurat: Sunset time    → Evening strategy sessions
Rahu Kaal: Inauspicious periods → Avoid major trades
```

## 📊 Technical Integration Strategy

### Phase 1: Foundation (Todos 1-3)
- **Project Structure**: Organized folders for calculations, data, GUI, reports
- **Core Calculations**: Lunar phase engine, astronomical position calculator
- **Moon Cycle Tracking**: Daily lunar phase with market impact scoring

### Phase 2: Advanced Calculations (Todos 4-6)
- **Nakshatra Engine**: 27 lunar mansions with sector correlations
- **Planetary Calculator**: Real-time positions of 9 planets (Navagraha)
- **Muhurat System**: Auspicious timing calculator for trading decisions

### Phase 3: Market Analysis (Todos 7-8)
- **Correlation Analysis**: Historical pattern analysis between lunar cycles and market movements
- **Forecasting Engine**: Predictive models based on upcoming planetary transits
- **Sector Mapping**: Planetary influences on different market sectors

### Phase 4: User Interface (Todos 9-10)
- **Astro Dashboard**: Real-time planetary positions and lunar calendar
- **Trading Calendar**: Auspicious and inauspicious timings highlighted
- **PDF Reports**: Comprehensive astrological market analysis

### Phase 5: Validation & Alerts (Todos 11-12)
- **Backtesting**: Historical validation of astrological patterns
- **Real-time Alerts**: Notifications for significant astrological events

## 🔮 Unique Features to Implement

### 1. **Lunar Phase Stock Scanner**
```python
# Example concept
def scan_by_lunar_phase():
    current_phase = get_moon_phase()
    if current_phase == "New Moon":
        return scan_accumulation_candidates()
    elif current_phase == "Full Moon":
        return scan_profit_booking_candidates()
    elif current_phase == "Waxing":
        return scan_momentum_stocks()
    else:  # Waning
        return scan_correction_plays()
```

### 2. **Nakshatra-Based Sector Rotation**
```python
# Example concept
def get_favored_sectors_by_nakshatra():
    current_nakshatra = get_current_nakshatra()
    nakshatra_sectors = {
        'Ashwini': ['Auto', 'Transportation'],
        'Bharani': ['Healthcare', 'Transformation'],
        'Kritika': ['Defense', 'Sharp Tools'],
        'Rohini': ['FMCG', 'Agriculture'],
        # ... mapping for all 27
    }
    return nakshatra_sectors.get(current_nakshatra, [])
```

### 3. **Planetary Transit Alerts**
```python
# Example concept
def check_major_transits():
    transits = []
    for planet in ['Jupiter', 'Saturn', 'Mars']:
        if is_changing_sign(planet):
            transits.append({
                'planet': planet,
                'from_sign': get_previous_sign(planet),
                'to_sign': get_current_sign(planet),
                'market_impact': get_transit_impact(planet)
            })
    return transits
```

## 🎯 Practical Applications

### 1. **Daily Trading Workflow**
- Morning: Check lunar phase and planetary positions
- Pre-market: Review auspicious timings for the day
- During trading: Avoid Rahu Kaal periods for major decisions
- Evening: Plan next day based on lunar calendar

### 2. **Weekly Analysis**
- Monday: Moon's position and weekly nakshatra influence
- Wednesday: Mercury's impact on IT and communication sectors
- Thursday: Jupiter's influence on financial decisions
- Saturday: Saturn's long-term market implications

### 3. **Monthly Strategy**
- New Moon: Accumulation and fresh position building
- Full Moon: Profit booking and risk management
- Eclipse periods: Major market shifts and volatility
- Planetary retrogrades: Sector rotation strategies

### 4. **Annual Planning**
- Major planetary transits affecting long-term trends
- Auspicious periods for IPO launches and major investments
- Seasonal patterns based on solar calendar
- Festival calendar impact on market sentiment

## 🛠️ Technical Implementation Plan

### Database Schema Extensions
```sql
-- Lunar calendar table
CREATE TABLE lunar_calendar (
    date DATE PRIMARY KEY,
    lunar_phase ENUM('New', 'Waxing_Crescent', 'First_Quarter', 'Waxing_Gibbous', 
                     'Full', 'Waning_Gibbous', 'Last_Quarter', 'Waning_Crescent'),
    nakshatra VARCHAR(20),
    tithi INT,
    moon_sign VARCHAR(20),
    moon_degree DECIMAL(5,2)
);

-- Planetary positions table
CREATE TABLE planetary_positions (
    date DATE,
    planet VARCHAR(20),
    sign VARCHAR(20),
    degree DECIMAL(5,2),
    retrograde BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (date, planet)
);

-- Astrological market correlations
CREATE TABLE astro_market_correlations (
    date DATE,
    lunar_phase VARCHAR(20),
    nakshatra VARCHAR(20),
    market_direction ENUM('Bullish', 'Bearish', 'Neutral'),
    volatility_score DECIMAL(3,2),
    sector_influence JSON
);
```

### Key Python Libraries to Use
```python
# Astronomical calculations
import ephem          # Planetary positions and lunar phases
import pytz           # Timezone handling for accurate calculations
import datetime       # Date and time manipulation

# Mathematical calculations
import numpy as np    # Numerical computations
import pandas as pd   # Data manipulation

# Visualization
import matplotlib.pyplot as plt  # Charts and graphs
import seaborn as sns           # Statistical visualizations

# GUI integration
import tkinter as tk           # GUI development
from tkinter import ttk        # Modern widgets
```

## 🎨 GUI Integration Concepts

### 1. **Astro Dashboard Tab**
- Real-time lunar phase display with visual moon icon
- Current nakshatra with characteristics
- Planetary positions in a circular chart
- Today's auspicious and inauspicious timings

### 2. **Lunar Calendar View**
- Monthly calendar with moon phases
- Highlighting of significant astrological events
- Trading recommendations for each day
- Historical correlation data

### 3. **Planetary Transit Tracker**
- Timeline view of major planetary movements
- Impact analysis on different market sectors
- Alert system for significant transits
- Historical performance during similar transits

## 📈 Success Metrics

### Quantitative Measures
- Correlation coefficient between lunar phases and market movements
- Accuracy of nakshatra-based sector predictions
- Performance of muhurat-timed trades vs random timing
- Volatility patterns during different planetary configurations

### Qualitative Benefits
- Enhanced timing for major investment decisions
- Improved risk management during volatile periods
- Unique competitive advantage in market analysis
- Integration of traditional wisdom with modern analytics

## 🚀 Getting Started

This comprehensive plan provides a roadmap for integrating Vedic astrology into your stock screener. The modular approach allows for incremental development and testing of each component.

**Recommended Starting Point**: Begin with moon cycle analysis and basic nakshatra calculations, then gradually expand to include planetary positions and correlation analysis.

Would you like to prioritize specific aspects of this integration or start with a particular component?