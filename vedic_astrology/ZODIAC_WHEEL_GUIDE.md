# 🎯 Zodiac Wheel Charts - Complete Guide

## Overview

The Zodiac Wheel Chart Generator creates visual representations of the current Moon position in the zodiac, similar to traditional astrological charts. These charts help you visualize where the Moon is positioned and understand its market implications for trading.

## 🚀 Quick Start

### Generating Zodiac Wheel Charts

**From GUI Dashboard:**
1. Open the Trading Dashboard
2. **Quick Actions**: Click "🎯 Zodiac Wheel Chart" button
3. **Analysis Tab**: Click "🎯 Generate Zodiac Wheel" 
4. Charts will be generated and displayed automatically

**From Command Line:**
```bash
cd vedic_astrology/trading_tools
python zodiac_wheel_generator.py
```

## 📊 Chart Types Generated

### 1. **Basic Zodiac Wheel**
- Clean, simple zodiac wheel with current Moon position
- Color-coded elements (Fire/Earth/Air/Water)
- Moon position marked with golden symbol
- Perfect for quick reference

### 2. **Detailed Astrology Chart**
- Enhanced wheel with comprehensive information
- Market analysis panel with trading implications
- Moon phase details and illumination percentage
- Element legend with trading strategies
- Professional presentation suitable for sharing

## 🎨 Chart Elements Explained

### **Zodiac Wheel Structure**

**Outer Ring**: Zodiac signs with symbols
- ♈ Aries (Fire) - ♉ Taurus (Earth) - ♊ Gemini (Air) - ♋ Cancer (Water)
- ♌ Leo (Fire) - ♍ Virgo (Earth) - ♎ Libra (Air) - ♏ Scorpio (Water)
- ♐ Sagittarius (Fire) - ♑ Capricorn (Earth) - ♒ Aquarius (Air) - ♓ Pisces (Water)

**Middle Ring**: Degree markings (0° - 360°)
- Each sign spans exactly 30 degrees
- Major degree marks at sign boundaries
- Minor marks every 5 degrees for precision

**Inner Area**: Planetary positions
- 🌙 Moon symbol shows current lunar position
- Golden circle highlights exact degree location
- Highlighted sign shows current Moon sign

### **Color Coding System**

🔥 **Fire Signs** (Red): Aries, Leo, Sagittarius
- Market Behavior: Momentum-driven, aggressive moves
- Trading Style: Breakout strategies, momentum plays
- Volatility: High (1.2x normal)

🌍 **Earth Signs** (Brown): Taurus, Virgo, Capricorn  
- Market Behavior: Steady, value-oriented moves
- Trading Style: Value investing, accumulation
- Volatility: Low (0.6x - 1.0x normal)

💨 **Air Signs** (Blue): Gemini, Libra, Aquarius
- Market Behavior: Communication-driven, news-sensitive
- Trading Style: Trend following, technical analysis
- Volatility: Medium (1.0x normal)

💧 **Water Signs** (Cyan): Cancer, Scorpio, Pisces
- Market Behavior: Emotional, intuitive moves
- Trading Style: Contrarian plays, sentiment-based
- Volatility: High (1.2x - 1.5x normal)

## 📍 Reading Moon Position

### **Current Example (November 19, 2025)**

**Moon Position**: 15.7° in Scorpio
- **Sign**: Scorpio (Water element)
- **Degree**: 15.7° (middle of the sign)
- **Element**: Water - Emotional, intuitive market behavior
- **Volatility**: Very High (1.5x normal)
- **Trading Approach**: Defensive, small positions, tight stops

### **How Moon Position is Determined**

1. **Astronomical Calculation**: Moon's celestial longitude calculated for Mumbai (19.0760°N, 72.8777°E)
2. **Sign Mapping**: Longitude converted to zodiac sign (each sign = 30°)
3. **Degree Precision**: Exact degree within the sign determined
4. **Visual Mapping**: Position plotted on wheel starting from Aries at top

### **Movement Pattern**
- **Daily Movement**: ~13 degrees per day
- **Sign Duration**: ~2.5 days per sign  
- **Complete Cycle**: 27.3 days for full zodiac
- **Chart Updates**: Daily as Moon position changes

## 💰 Trading Applications

### **Daily Market Preparation**

**Step 1: Check Moon Position**
- Identify current zodiac sign
- Note the element (Fire/Earth/Air/Water)
- Check degree position within sign

**Step 2: Determine Market Approach**
- **Fire Signs**: Focus on momentum, energy stocks
- **Earth Signs**: Look for value, accumulation opportunities  
- **Air Signs**: Follow trends, tech stocks
- **Water Signs**: Watch for emotional extremes, contrarian plays

**Step 3: Adjust Risk Management**
- **High Volatility Signs** (Scorpio, Aries): Max 10-15% positions
- **Medium Volatility Signs**: Max 15-20% positions
- **Low Volatility Signs** (Capricorn, Taurus): Max 20-25% positions

### **Sector Rotation Strategy**

**Fire Element Dominance**:
- Favor: Energy, Infrastructure, Automotive, Metals
- Stocks: RELIANCE, TATAMOTORS, HINDALCO, JSWSTEEL
- Strategy: Momentum breakouts, trending moves

**Earth Element Dominance**:
- Favor: Banking, FMCG, Pharmaceuticals, Agriculture
- Stocks: HDFCBANK, HINDUNILVR, SUNPHARMA, ITC
- Strategy: Value accumulation, dividend plays

**Air Element Dominance**:
- Favor: Technology, Telecom, Media, Airlines
- Stocks: TCS, INFY, BHARTIARTL, INDIGO
- Strategy: Trend following, technical patterns

**Water Element Dominance**:
- Favor: Healthcare, Chemicals, Real Estate, Beverages
- Stocks: DRREDDYS, UPL, GODREJPROP, TATACONS
- Strategy: Contrarian positions, emotional extremes

## 🎯 Chart Interpretation Examples

### **Scorpio Moon (Current Example)**
```
Position: 15.7° Scorpio (Water sign)
Implications:
• Very high volatility expected (1.5x)
• Intense, transformative market movements
• Small position sizes recommended (max 10%)
• Tight stop losses (2-3%)
• Focus on water-element sectors
• Defensive trading approach
```

### **Taurus Moon (Example)**
```
Position: 12.3° Taurus (Earth sign)  
Implications:
• Low volatility expected (0.8x)
• Steady, methodical movements
• Larger positions acceptable (max 25%)
• Normal stop losses (5-7%)
• Focus on banking/FMCG sectors
• Accumulation strategy
```

### **Aries Moon (Example)**
```
Position: 8.5° Aries (Fire sign)
Implications:
• High volatility expected (1.2x)
• Aggressive, momentum-driven moves
• Medium positions (max 20%)
• Momentum stops (3-5%)
• Focus on energy/infrastructure
• Breakout strategy
```

## 📈 Advanced Features

### **Integration with Trading Reports**

The zodiac wheels integrate with your daily trading reports:
- **Daily Strategy**: References current Moon position
- **Weekly Outlook**: Shows Moon transitions during week
- **Market Forecast**: Predicts Moon-based volatility patterns
- **Risk Calendar**: Color-codes days by Moon position risk

### **Historical Analysis**

Use generated charts to:
- Compare Moon positions on significant market days
- Identify patterns in volatility during specific signs
- Validate element-based sector rotation strategies
- Track correlation between Moon cycles and portfolio performance

### **Custom Analysis**

Charts can be customized for:
- Different dates (historical analysis)
- Multiple planetary positions (future enhancement)
- Various time zones and locations
- Specific market events analysis

## 🔧 Technical Information

### **File Locations**
- **Charts Saved**: `vedic_astrology/reports/charts/`
- **Naming**: `zodiac_wheel_YYYYMMDD.png` and `detailed_zodiac_wheel_YYYYMMDD.png`
- **Format**: High-resolution PNG (300 DPI)

### **Dependencies Required**
- `matplotlib` - Chart generation
- `numpy` - Mathematical calculations  
- `pandas` - Data processing
- `ephem` - Astronomical calculations

### **Installation**
```bash
# Install all dependencies
pip install matplotlib numpy pandas pyephem

# Or run the batch file
install_dependencies.bat
```

## 📊 Chart Quality & Specifications

### **Resolution & Format**
- **DPI**: 300 (print quality)
- **Format**: PNG with transparency support
- **Size**: ~12x12 inches for detailed charts
- **Colors**: Professional color scheme suitable for presentations

### **Font Considerations**
- Some Unicode symbols may show warnings (non-critical)
- Charts render correctly despite font warnings
- Standard symbols used for maximum compatibility

## 🎨 Customization Options

### **Color Schemes**
Element colors can be modified in the generator:
- Fire: Red (#FF4444)
- Earth: Brown (#8B4513)  
- Air: Blue (#4169E1)
- Water: Cyan (#00CED1)

### **Additional Elements**
Future enhancements planned:
- Multiple planet positions
- Aspect lines between planets
- House divisions
- Nakshatra (lunar mansion) markings
- Transit predictions

## 🚨 Important Notes

### **Accuracy**
- Calculations based on sidereal (Vedic) astrology
- Mumbai coordinates used for Indian market relevance
- Daily updates reflect actual astronomical positions
- Degree precision suitable for trading analysis

### **Interpretation Guidelines**
- Use charts as one factor in trading decisions
- Combine with technical analysis and risk management
- Historical correlation doesn't guarantee future results
- Market fundamentals remain primary consideration

### **Best Practices**
- Generate fresh charts daily for current analysis
- Archive charts for historical reference
- Share charts with trading team for alignment
- Use detailed charts for comprehensive analysis

---

**Remember**: These zodiac wheel charts provide visual representation of ancient wisdom applied to modern markets. Use them as a valuable tool in your comprehensive trading strategy, always combined with sound risk management and market analysis.