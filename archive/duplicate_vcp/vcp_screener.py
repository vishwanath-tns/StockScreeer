"""
VCP Screener - Find Stocks in Current Volatility Contraction
===========================================================

Scans all NSE stocks to find those currently showing volatility contraction
in the last 2-3 months with actionable trading levels.

Strategy:
- Find stocks with 3+ contractions in last 60-90 days
- Each contraction progressively smaller (volatility contracting)
- Volume declining through contractions
- Calculate precise breakout/breakdown levels
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
from volatility_patterns.core.vcp_detector import VCPDetector
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VCPScreenerResult:
    """Result from VCP screening with trading levels"""
    symbol: str
    current_price: float
    pattern_quality: float
    contractions_count: int
    latest_contraction_size: float  # percentage
    days_since_last_low: int
    
    # Trading levels
    resistance_level: float
    support_level: float
    breakout_level: float  # Entry level
    breakdown_level: float  # Stop watching level
    target_level: float    # Profit target
    stop_loss_level: float # Risk management
    
    # Risk metrics
    risk_reward_ratio: float
    position_score: float  # Overall attractiveness 0-100
    
    # Pattern details
    pattern_start_date: date
    pattern_end_date: date
    total_pattern_days: int
    volume_trend: str  # "Declining", "Mixed", "Increasing"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for easy display/export"""
        return {
            'Symbol': self.symbol,
            'Current_Price': f'₹{self.current_price:.2f}',
            'Quality': f'{self.pattern_quality:.1f}',
            'Contractions': self.contractions_count,
            'Latest_Contraction': f'{self.latest_contraction_size:.1f}%',
            'Days_Since_Low': self.days_since_last_low,
            'Resistance': f'₹{self.resistance_level:.2f}',
            'Support': f'₹{self.support_level:.2f}',
            'Breakout_Entry': f'₹{self.breakout_level:.2f}',
            'Breakdown_Alert': f'₹{self.breakdown_level:.2f}',
            'Target': f'₹{self.target_level:.2f}',
            'Stop_Loss': f'₹{self.stop_loss_level:.2f}',
            'Risk_Reward': f'{self.risk_reward_ratio:.2f}',
            'Position_Score': f'{self.position_score:.1f}',
            'Pattern_Period': f'{self.pattern_start_date} to {self.pattern_end_date}',
            'Pattern_Days': self.total_pattern_days,
            'Volume_Trend': self.volume_trend
        }

class VCPScreener:
    """Screen stocks for current volatility contraction patterns"""
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
        
        # Screening parameters
        self.min_price = 50.0  # Avoid penny stocks
        self.max_price = 10000.0  # Avoid extreme high prices
        self.min_contractions = 2  # Relaxed: Need at least 2 contractions
        self.max_latest_contraction = 12.0  # Relaxed: Latest contraction should be <12%
        self.min_volume_decline_ratio = 0.25  # Relaxed: At least 25% of contractions show volume decline
        
        # Date ranges
        self.end_date = date.today()
        self.lookback_days = 180  # Look back 6 months for pattern detection
        self.pattern_focus_days = 120  # Focus on patterns in last 4 months
        
    def screen_all_stocks(self, symbols: Optional[List[str]] = None) -> List[VCPScreenerResult]:
        """
        Screen all provided stocks for VCP patterns
        
        Args:
            symbols: List of symbols to screen. If None, will use a default watchlist
        
        Returns:
            List of VCPScreenerResult objects, sorted by position score
        """
        if symbols is None:
            symbols = self._get_default_screening_universe()
        
        logger.info(f"🔍 Starting VCP screening for {len(symbols)} stocks")
        logger.info(f"📅 Screening period: {self.end_date - timedelta(days=self.lookback_days)} to {self.end_date}")
        
        results = []
        processed = 0
        
        for symbol in symbols:
            try:
                result = self._screen_single_stock(symbol)
                if result:
                    results.append(result)
                    logger.info(f"✅ {symbol}: Found VCP pattern (Score: {result.position_score:.1f})")
                
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"📊 Processed {processed}/{len(symbols)} stocks, Found {len(results)} VCP patterns")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error screening {symbol}: {e}")
                continue
        
        # Sort by position score (best opportunities first)
        results.sort(key=lambda x: x.position_score, reverse=True)
        
        logger.info(f"🎯 VCP Screening Complete: Found {len(results)} stocks in volatility contraction")
        return results
    
    def _get_default_screening_universe(self) -> List[str]:
        """Get a reasonable set of stocks to screen"""
        # Major liquid stocks for initial screening
        # In production, this would pull from your database
        return [
            # Banking
            'HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK',
            'INDUSINDBK', 'FEDERALBNK', 'BANDHANBNK', 'IDFCFIRSTB',
            
            # IT
            'TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM', 'LTI', 'MINDTREE',
            'MPHASIS', 'COFORGE',
            
            # Pharma
            'SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN', 'DIVISLAB',
            'BIOCON', 'CADILAHC', 'ALKEM', 'AUROPHARMA',
            
            # FMCG
            'HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA', 'DABUR',
            'GODREJCP', 'MARICO', 'COLPAL',
            
            # Auto
            'MARUTI', 'HYUNDAI', 'TATAMOTORS', 'M&M', 'BAJAJ-AUTO',
            'TVSMOTORS', 'EICHERMOT', 'HEROMOTOCO',
            
            # Financials
            'BAJFINANCE', 'BAJAJFINSV', 'SBILIFE', 'HDFCLIFE', 'ICICIPRULI',
            'LICHSGFIN', 'PFC', 'RECLTD',
            
            # Metals
            'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'VEDL', 'NMDC', 'SAIL',
            
            # Others
            'RELIANCE', 'ONGC', 'IOC', 'BPCL', 'NTPC', 'POWERGRID',
            'BHARTIARTL', 'ADANIENT', 'ASIANPAINT', 'LTIM'
        ]
    
    def _screen_single_stock(self, symbol: str) -> Optional[VCPScreenerResult]:
        """Screen a single stock for VCP pattern"""
        
        # Get data
        start_date = self.end_date - timedelta(days=self.lookback_days + 30)  # Extra buffer
        data = self.data_service.get_ohlcv_data(symbol, start_date, self.end_date)
        
        if len(data) < 60:  # Need sufficient data
            return None
        
        # Filter to recent data and trading days only
        data = self._filter_trading_days(data)
        recent_cutoff = self.end_date - timedelta(days=self.pattern_focus_days)
        
        # Basic price filter
        current_price = data.iloc[-1]['close']
        if current_price < self.min_price or current_price > self.max_price:
            return None
        
        # Detect VCP patterns
        patterns = self.detector.detect_vcp_patterns(data, symbol)
        if not patterns:
            return None
        
        # Find the most recent high-quality pattern
        recent_patterns = [
            p for p in patterns 
            if p.end_date >= recent_cutoff and len(p.contractions) >= self.min_contractions
        ]
        
        if not recent_patterns:
            return None
        
        # Get best recent pattern
        best_pattern = max(recent_patterns, key=lambda p: p.quality_score)
        
        # Validate pattern meets our criteria
        if not self._validate_pattern_for_screening(best_pattern, data):
            return None
        
        # Calculate trading levels and metrics
        return self._calculate_trading_levels(symbol, best_pattern, data, current_price)
    
    def _filter_trading_days(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _validate_pattern_for_screening(self, pattern, data: pd.DataFrame) -> bool:
        """Validate that pattern meets our screening criteria"""
        
        contractions = pattern.contractions
        
        # Need minimum contractions
        if len(contractions) < self.min_contractions:
            return False
        
        # Check latest contraction is tight enough
        latest_contraction = contractions[-1]
        if latest_contraction.range_percent > self.max_latest_contraction:
            return False
        
        # Check volume decline trend
        volume_declines = [c.volume_decline for c in contractions[1:]]
        positive_declines = sum(1 for v in volume_declines if v > 0)
        volume_decline_ratio = positive_declines / len(volume_declines) if volume_declines else 0
        
        if volume_decline_ratio < self.min_volume_decline_ratio:
            return False
        
        # Check that contractions are getting smaller (volatility contracting)
        contraction_sizes = [c.range_percent for c in contractions]
        
        # At least 60% of successive contractions should be smaller
        smaller_count = 0
        for i in range(1, len(contraction_sizes)):
            if contraction_sizes[i] < contraction_sizes[i-1]:
                smaller_count += 1
        
        smaller_ratio = smaller_count / (len(contraction_sizes) - 1) if len(contraction_sizes) > 1 else 0
        
        if smaller_ratio < 0.4:  # Relaxed: 40% should show contraction
            return False
        
        return True
    
    def _calculate_trading_levels(self, symbol: str, pattern, data: pd.DataFrame, current_price: float) -> VCPScreenerResult:
        """Calculate all trading levels and metrics for the pattern"""
        
        contractions = pattern.contractions
        
        # Find pattern data range
        pattern_start_mask = data['date'] >= pd.to_datetime(pattern.base_start_date)
        pattern_end_mask = data['date'] <= pd.to_datetime(pattern.end_date)
        pattern_data = data[pattern_start_mask & pattern_end_mask]
        
        if len(pattern_data) == 0:
            pattern_data = data.iloc[-30:]  # Fallback to recent data
        
        # Calculate key levels
        resistance_level = pattern_data['high'].max()
        support_level = pattern_data['low'].max()  # Use highest low as support
        
        # Trading levels
        breakout_level = resistance_level * 1.02  # 2% above resistance
        breakdown_level = support_level * 0.98   # 2% below support  
        target_level = breakout_level * 1.25     # 25% target from entry
        stop_loss_level = support_level * 0.97   # 3% below support
        
        # Risk/reward calculation
        risk = breakout_level - stop_loss_level
        reward = target_level - breakout_level
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Pattern metrics
        latest_contraction = contractions[-1]
        
        # Days since last low
        last_low_date = pd.to_datetime(latest_contraction.end_date)
        days_since_low = (pd.to_datetime(self.end_date) - last_low_date).days
        
        # Volume trend analysis
        volume_trend = self._analyze_volume_trend(contractions)
        
        # Calculate position score (0-100)
        position_score = self._calculate_position_score(
            pattern, current_price, resistance_level, support_level, 
            risk_reward_ratio, days_since_low
        )
        
        return VCPScreenerResult(
            symbol=symbol,
            current_price=current_price,
            pattern_quality=pattern.quality_score,
            contractions_count=len(contractions),
            latest_contraction_size=latest_contraction.range_percent,
            days_since_last_low=days_since_low,
            resistance_level=resistance_level,
            support_level=support_level,
            breakout_level=breakout_level,
            breakdown_level=breakdown_level,
            target_level=target_level,
            stop_loss_level=stop_loss_level,
            risk_reward_ratio=risk_reward_ratio,
            position_score=position_score,
            pattern_start_date=pattern.base_start_date,
            pattern_end_date=pattern.end_date,
            total_pattern_days=(pattern.end_date - pattern.base_start_date).days,
            volume_trend=volume_trend
        )
    
    def _analyze_volume_trend(self, contractions) -> str:
        """Analyze volume trend through contractions"""
        volume_declines = [c.volume_decline for c in contractions[1:]]
        
        if not volume_declines:
            return "Unknown"
        
        positive_declines = sum(1 for v in volume_declines if v > 0)
        decline_ratio = positive_declines / len(volume_declines)
        
        if decline_ratio >= 0.7:
            return "Declining"  # Good for VCP
        elif decline_ratio >= 0.4:
            return "Mixed"
        else:
            return "Increasing"  # Not ideal for VCP
    
    def _calculate_position_score(self, pattern, current_price: float, resistance: float, 
                                support: float, risk_reward: float, days_since_low: int) -> float:
        """Calculate overall position attractiveness score 0-100"""
        
        score = 0
        
        # Pattern quality (0-40 points)
        score += min(pattern.quality_score * 0.4, 40)
        
        # Risk/reward ratio (0-20 points)
        rr_score = min(risk_reward * 5, 20)  # Cap at 4:1 ratio
        score += rr_score
        
        # Distance from resistance (0-15 points)
        distance_to_resistance = (resistance - current_price) / current_price * 100
        if distance_to_resistance <= 2:
            score += 15  # Very close to breakout
        elif distance_to_resistance <= 5:
            score += 10  # Reasonably close
        elif distance_to_resistance <= 10:
            score += 5   # Moderate distance
        
        # Days since last low (0-10 points)
        if days_since_low <= 5:
            score += 10  # Very recent
        elif days_since_low <= 15:
            score += 7   # Recent
        elif days_since_low <= 30:
            score += 4   # Moderate
        
        # Position relative to support (0-15 points)
        distance_to_support = (current_price - support) / support * 100
        if distance_to_support >= 5:
            score += 15  # Good cushion above support
        elif distance_to_support >= 2:
            score += 10  # Reasonable cushion
        elif distance_to_support >= 0:
            score += 5   # Just above support
        
        return min(score, 100)
    
    def export_results(self, results: List[VCPScreenerResult], filename: str = None) -> str:
        """Export results to CSV file"""
        
        if not results:
            print("No results to export")
            return None
        
        if filename is None:
            filename = f"vcp_screener_results_{self.end_date.strftime('%Y%m%d')}.csv"
        
        # Convert results to DataFrame
        results_data = [result.to_dict() for result in results]
        df = pd.DataFrame(results_data)
        
        # Save to CSV
        filepath = f"screener_results/{filename}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)
        
        print(f"✅ Results exported to: {filepath}")
        return filepath
    
    def display_top_results(self, results: List[VCPScreenerResult], top_n: int = 10):
        """Display top screening results in formatted table"""
        
        if not results:
            print("📭 No VCP patterns found matching criteria")
            return
        
        print(f"\n🎯 TOP {min(top_n, len(results))} VCP OPPORTUNITIES")
        print("=" * 120)
        print(f"{'Rank':<4} {'Symbol':<12} {'Price':<8} {'Quality':<7} {'Breakout':<9} {'Target':<8} {'R:R':<5} {'Score':<5} {'Status'}")
        print("-" * 120)
        
        for i, result in enumerate(results[:top_n], 1):
            # Determine current status
            distance_to_breakout = ((result.breakout_level - result.current_price) / result.current_price) * 100
            
            if distance_to_breakout <= 1:
                status = "🔥 Ready"
            elif distance_to_breakout <= 3:
                status = "⚡ Close"
            elif distance_to_breakout <= 8:
                status = "⏳ Watch"
            else:
                status = "💤 Early"
            
            print(f"{i:<4} {result.symbol:<12} ₹{result.current_price:<7.0f} {result.pattern_quality:<6.1f} "
                  f"₹{result.breakout_level:<8.0f} ₹{result.target_level:<7.0f} {result.risk_reward_ratio:<4.1f} "
                  f"{result.position_score:<4.0f} {status}")
        
        print("\n💡 LEGEND:")
        print("   🔥 Ready: <1% from breakout | ⚡ Close: <3% from breakout")  
        print("   ⏳ Watch: <8% from breakout | 💤 Early: >8% from breakout")
        print(f"\n📊 Total patterns found: {len(results)}")

def main():
    """Run VCP screener"""
    
    print("🔍 VCP VOLATILITY CONTRACTION SCREENER")
    print("=" * 55)
    print("Finding stocks in current volatility contraction with trading levels...")
    
    # Initialize screener
    screener = VCPScreener()
    
    # Run screening
    results = screener.screen_all_stocks()
    
    # Display results
    screener.display_top_results(results, top_n=15)
    
    if results:
        # Export results
        export_path = screener.export_results(results)
        
        print(f"\n📈 DETAILED ANALYSIS:")
        print(f"✅ Found {len(results)} stocks in volatility contraction")
        print(f"📅 Screening period: Last {screener.pattern_focus_days} days")
        print(f"🎯 Criteria: Min {screener.min_contractions} contractions, Latest <{screener.max_latest_contraction}%")
        print(f"💾 Results exported: {export_path}")
        
        # Show breakdown by readiness
        ready_count = sum(1 for r in results if ((r.breakout_level - r.current_price) / r.current_price) * 100 <= 1)
        close_count = sum(1 for r in results if 1 < ((r.breakout_level - r.current_price) / r.current_price) * 100 <= 3)
        watch_count = sum(1 for r in results if 3 < ((r.breakout_level - r.current_price) / r.current_price) * 100 <= 8)
        
        print(f"\n📊 BREAKOUT READINESS:")
        print(f"   🔥 Ready for breakout: {ready_count} stocks")
        print(f"   ⚡ Close to breakout: {close_count} stocks")
        print(f"   ⏳ Worth watching: {watch_count} stocks")
    
    print(f"\n🎯 VCP Screening Complete!")

if __name__ == "__main__":
    main()