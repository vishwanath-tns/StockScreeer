"""
Volatility Analysis & Trading Levels Screener
==============================================

Since pure VCP patterns are rare in current market conditions, this screener 
provides volatility analysis and trading levels for stocks showing any form
of consolidation or contraction tendencies.

Focus: Find stocks that might be setting up for moves, even if they don't 
meet strict VCP criteria.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from volatility_patterns.data.data_service import DataService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VolatilityAnalysis:
    """Volatility and trading level analysis for a stock"""
    symbol: str
    current_price: float
    
    # Volatility metrics
    recent_30d_volatility: float    # % range in last 30 days
    recent_60d_volatility: float    # % range in last 60 days
    volatility_trend: str           # "Contracting", "Expanding", "Stable"
    
    # Trading levels
    resistance_level: float         # Key resistance
    support_level: float           # Key support
    breakout_entry: float          # Entry above resistance
    breakdown_exit: float          # Exit below support
    
    # Position metrics
    distance_to_resistance_pct: float  # % away from breakout
    distance_to_support_pct: float     # % above support
    
    # Volume analysis
    volume_trend: str              # "High", "Normal", "Low"
    avg_volume_20d: float
    
    # Technical indicators
    above_sma20: bool
    above_sma50: bool
    sma20_slope: str               # "Rising", "Falling", "Flat"
    
    # Opportunity score
    setup_score: float             # 0-100, higher = better setup
    recommendation: str            # "Strong Buy Setup", "Watch", "Avoid"
    
    def to_dict(self) -> Dict:
        return {
            'Symbol': self.symbol,
            'Price': f'₹{self.current_price:.2f}',
            'Volatility_30d': f'{self.recent_30d_volatility:.1f}%',
            'Volatility_60d': f'{self.recent_60d_volatility:.1f}%',
            'Vol_Trend': self.volatility_trend,
            'Resistance': f'₹{self.resistance_level:.2f}',
            'Support': f'₹{self.support_level:.2f}',
            'Breakout_Entry': f'₹{self.breakout_entry:.2f}',
            'Distance_to_BO': f'{self.distance_to_resistance_pct:.1f}%',
            'Above_Support': f'{self.distance_to_support_pct:.1f}%',
            'Volume_Trend': self.volume_trend,
            'Above_SMA20': '✅' if self.above_sma20 else '❌',
            'Above_SMA50': '✅' if self.above_sma50 else '❌',
            'SMA20_Trend': self.sma20_slope,
            'Setup_Score': f'{self.setup_score:.1f}',
            'Recommendation': self.recommendation
        }

class VolatilityScreener:
    """Screen for volatility patterns and trading opportunities"""
    
    def __init__(self):
        self.data_service = DataService()
        
        # Screening parameters
        self.min_price = 50.0
        self.max_price = 10000.0
        self.lookback_days = 120  # 4 months of data
        
    def screen_volatility_setups(self, symbols: Optional[List[str]] = None) -> List[VolatilityAnalysis]:
        """Screen stocks for volatility-based trading setups"""
        
        if symbols is None:
            symbols = self._get_screening_universe()
        
        logger.info(f"🔍 Screening {len(symbols)} stocks for volatility setups...")
        
        results = []
        processed = 0
        
        for symbol in symbols:
            try:
                analysis = self._analyze_stock_volatility(symbol)
                if analysis:
                    results.append(analysis)
                    logger.info(f"✅ {symbol}: Setup score {analysis.setup_score:.1f}")
                
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"📊 Processed {processed}/{len(symbols)} stocks")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error analyzing {symbol}: {e}")
                continue
        
        # Sort by setup score
        results.sort(key=lambda x: x.setup_score, reverse=True)
        
        logger.info(f"🎯 Found {len(results)} trading setups")
        return results
    
    def _get_screening_universe(self) -> List[str]:
        """Get stocks to screen"""
        return [
            'HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK',
            'TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM',
            'SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN', 'DIVISLAB', 'BIOCON',
            'HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA', 'DABUR',
            'MARUTI', 'HYUNDAI', 'TATAMOTORS', 'M&M', 'BAJAJ-AUTO',
            'BAJFINANCE', 'BAJAJFINSV', 'SBILIFE', 'HDFCLIFE',
            'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'VEDL',
            'RELIANCE', 'ONGC', 'IOC', 'BPCL', 'NTPC', 'BHARTIARTL',
            'ADANIENT', 'ASIANPAINT', 'LTIM'
        ]
    
    def _analyze_stock_volatility(self, symbol: str) -> Optional[VolatilityAnalysis]:
        """Analyze a single stock's volatility and trading setup"""
        
        # Get data
        end_date = date.today()
        start_date = end_date - timedelta(days=self.lookback_days + 30)
        
        data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
        data = self._filter_trading_days(data)
        
        if len(data) < 60:
            return None
        
        current_price = data.iloc[-1]['close']
        
        # Price filter
        if current_price < self.min_price or current_price > self.max_price:
            return None
        
        # Calculate volatility metrics
        volatility_metrics = self._calculate_volatility_metrics(data)
        
        # Calculate trading levels
        levels = self._calculate_trading_levels(data)
        
        # Calculate technical indicators
        tech_indicators = self._calculate_technical_indicators(data)
        
        # Calculate volume analysis
        volume_analysis = self._analyze_volume(data)
        
        # Calculate setup score
        setup_score = self._calculate_setup_score(
            volatility_metrics, levels, tech_indicators, volume_analysis, current_price
        )
        
        # Determine recommendation
        recommendation = self._get_recommendation(setup_score, levels, current_price)
        
        return VolatilityAnalysis(
            symbol=symbol,
            current_price=current_price,
            recent_30d_volatility=volatility_metrics['vol_30d'],
            recent_60d_volatility=volatility_metrics['vol_60d'],
            volatility_trend=volatility_metrics['trend'],
            resistance_level=levels['resistance'],
            support_level=levels['support'],
            breakout_entry=levels['breakout_entry'],
            breakdown_exit=levels['breakdown_exit'],
            distance_to_resistance_pct=((levels['breakout_entry'] - current_price) / current_price) * 100,
            distance_to_support_pct=((current_price - levels['support']) / levels['support']) * 100,
            volume_trend=volume_analysis['trend'],
            avg_volume_20d=volume_analysis['avg_volume'],
            above_sma20=tech_indicators['above_sma20'],
            above_sma50=tech_indicators['above_sma50'],
            sma20_slope=tech_indicators['sma20_slope'],
            setup_score=setup_score,
            recommendation=recommendation
        )
    
    def _filter_trading_days(self, data):
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _calculate_volatility_metrics(self, data: pd.DataFrame) -> Dict:
        """Calculate volatility metrics"""
        
        # Recent 30 day volatility
        recent_30 = data.tail(30)
        vol_30d = ((recent_30['high'].max() - recent_30['low'].min()) / recent_30['low'].min()) * 100
        
        # Recent 60 day volatility  
        recent_60 = data.tail(60)
        vol_60d = ((recent_60['high'].max() - recent_60['low'].min()) / recent_60['low'].min()) * 100
        
        # Determine trend
        if vol_30d < vol_60d * 0.7:
            trend = "Contracting"  # Good for setups
        elif vol_30d > vol_60d * 1.3:
            trend = "Expanding"    # Volatile
        else:
            trend = "Stable"       # Neutral
        
        return {
            'vol_30d': vol_30d,
            'vol_60d': vol_60d,
            'trend': trend
        }
    
    def _calculate_trading_levels(self, data: pd.DataFrame) -> Dict:
        """Calculate key trading levels"""
        
        # Use recent 60 days for level calculation
        recent_data = data.tail(60)
        
        # Resistance: highest high in period
        resistance = recent_data['high'].max()
        
        # Support: highest low (strongest support)
        support = recent_data['low'].max()
        
        # Alternative support: significant low
        lows_sorted = recent_data['low'].sort_values(ascending=False)
        if len(lows_sorted) >= 3:
            support = lows_sorted.iloc[2]  # 3rd highest low
        
        # Trading levels
        breakout_entry = resistance * 1.02  # 2% above resistance
        breakdown_exit = support * 0.98    # 2% below support
        
        return {
            'resistance': resistance,
            'support': support,
            'breakout_entry': breakout_entry,
            'breakdown_exit': breakdown_exit
        }
    
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        
        # SMAs
        data['sma20'] = data['close'].rolling(20, min_periods=1).mean()
        data['sma50'] = data['close'].rolling(50, min_periods=1).mean()
        
        current_close = data.iloc[-1]['close']
        current_sma20 = data.iloc[-1]['sma20']
        current_sma50 = data.iloc[-1]['sma50']
        
        # SMA20 slope
        recent_sma20 = data['sma20'].tail(5)
        if recent_sma20.iloc[-1] > recent_sma20.iloc[0] * 1.01:
            sma20_slope = "Rising"
        elif recent_sma20.iloc[-1] < recent_sma20.iloc[0] * 0.99:
            sma20_slope = "Falling"
        else:
            sma20_slope = "Flat"
        
        return {
            'above_sma20': current_close > current_sma20,
            'above_sma50': current_close > current_sma50,
            'sma20_slope': sma20_slope
        }
    
    def _analyze_volume(self, data: pd.DataFrame) -> Dict:
        """Analyze volume patterns"""
        
        # Average volume
        avg_volume = data['volume'].tail(20).mean()
        
        # Recent volume vs average
        recent_volume = data['volume'].tail(5).mean()
        
        if recent_volume > avg_volume * 1.2:
            trend = "High"
        elif recent_volume < avg_volume * 0.8:
            trend = "Low"
        else:
            trend = "Normal"
        
        return {
            'avg_volume': avg_volume,
            'trend': trend
        }
    
    def _calculate_setup_score(self, volatility: Dict, levels: Dict, tech: Dict, 
                             volume: Dict, current_price: float) -> float:
        """Calculate overall setup score 0-100"""
        
        score = 0
        
        # Volatility score (0-25 points)
        if volatility['trend'] == "Contracting":
            score += 25  # Best for setups
        elif volatility['trend'] == "Stable":
            score += 15  # Decent
        else:
            score += 5   # Too volatile
        
        # Distance to breakout (0-20 points)
        distance_pct = ((levels['breakout_entry'] - current_price) / current_price) * 100
        if distance_pct <= 2:
            score += 20  # Very close
        elif distance_pct <= 5:
            score += 15  # Close
        elif distance_pct <= 10:
            score += 10  # Reasonable
        else:
            score += 0   # Too far
        
        # Technical position (0-25 points)
        if tech['above_sma20'] and tech['above_sma50']:
            score += 25  # Strong position
        elif tech['above_sma20']:
            score += 15  # Decent
        elif tech['above_sma50']:
            score += 10  # Below recent support
        else:
            score += 0   # Weak
        
        # SMA20 slope (0-15 points)
        if tech['sma20_slope'] == "Rising":
            score += 15
        elif tech['sma20_slope'] == "Flat":
            score += 8
        else:
            score += 0
        
        # Volume (0-15 points)
        if volume['trend'] == "Normal":
            score += 15  # Good for accumulation
        elif volume['trend'] == "Low":
            score += 10  # Quiet accumulation
        else:
            score += 5   # High volume can be distribution
        
        return min(score, 100)
    
    def _get_recommendation(self, score: float, levels: Dict, current_price: float) -> str:
        """Get trading recommendation"""
        
        distance_pct = ((levels['breakout_entry'] - current_price) / current_price) * 100
        
        if score >= 75 and distance_pct <= 3:
            return "Strong Buy Setup"
        elif score >= 60 and distance_pct <= 5:
            return "Buy Setup"
        elif score >= 45:
            return "Watch"
        else:
            return "Avoid"
    
    def display_results(self, results: List[VolatilityAnalysis], top_n: int = 15):
        """Display screening results"""
        
        if not results:
            print("📭 No trading setups found")
            return
        
        print(f"\n🎯 TOP {min(top_n, len(results))} VOLATILITY-BASED TRADING SETUPS")
        print("=" * 140)
        print(f"{'#':<3} {'Symbol':<12} {'Price':<8} {'Vol30d':<7} {'VolTrend':<12} {'Breakout':<9} {'Dist%':<6} {'Score':<5} {'Rec':<15}")
        print("-" * 140)
        
        for i, result in enumerate(results[:top_n], 1):
            status_color = ""
            if result.recommendation == "Strong Buy Setup":
                status_color = "🔥"
            elif result.recommendation == "Buy Setup":
                status_color = "⚡"
            elif result.recommendation == "Watch":
                status_color = "👀"
            else:
                status_color = "💤"
            
            print(f"{i:<3} {result.symbol:<12} ₹{result.current_price:<7.0f} "
                  f"{result.recent_30d_volatility:<6.1f}% {result.volatility_trend:<12} "
                  f"₹{result.breakout_entry:<8.0f} {result.distance_to_resistance_pct:<5.1f}% "
                  f"{result.setup_score:<4.0f} {status_color} {result.recommendation}")
        
        # Summary stats
        strong_setups = sum(1 for r in results if r.recommendation == "Strong Buy Setup")
        buy_setups = sum(1 for r in results if r.recommendation == "Buy Setup")
        watch_setups = sum(1 for r in results if r.recommendation == "Watch")
        
        print(f"\n📊 SETUP BREAKDOWN:")
        print(f"   🔥 Strong Buy Setups: {strong_setups}")
        print(f"   ⚡ Buy Setups: {buy_setups}")
        print(f"   👀 Watch List: {watch_setups}")
        
        # Market insights
        contracting_count = sum(1 for r in results if r.volatility_trend == "Contracting")
        print(f"\n💡 MARKET INSIGHTS:")
        print(f"   📉 Stocks with contracting volatility: {contracting_count}/{len(results)}")
        print(f"   🎯 Best setups typically have: Contracting volatility + Close to breakout")

def main():
    """Run volatility screening"""
    
    print("🔍 VOLATILITY & TRADING LEVELS SCREENER")
    print("=" * 55)
    print("Finding volatility-based trading setups with actionable levels...")
    
    screener = VolatilityScreener()
    results = screener.screen_volatility_setups()
    
    screener.display_results(results, top_n=20)
    
    # Export results
    if results:
        export_data = [r.to_dict() for r in results]
        df = pd.DataFrame(export_data)
        filename = f"volatility_setups_{date.today().strftime('%Y%m%d')}.csv"
        filepath = f"screener_results/{filename}"
        df.to_csv(filepath, index=False)
        print(f"\n💾 Results exported to: {filepath}")

if __name__ == "__main__":
    main()