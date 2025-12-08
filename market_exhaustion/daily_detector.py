"""
Daily Market Exhaustion Detector
================================
Analyzes daily data for Nifty 500 stocks to detect market exhaustion
and provide portfolio protection signals.

Signals Generated:
- EXTREME_OVERBOUGHT: >85% stocks above 20 SMA (High risk of correction)
- OVERBOUGHT: >75% stocks above 20 SMA (Elevated risk)
- BULLISH_DIVERGENCE: Index falling but breadth improving
- BEARISH_DIVERGENCE: Index rising but breadth declining (DANGER!)
- OVERSOLD: <25% stocks above 20 SMA (Potential bounce)
- EXTREME_OVERSOLD: <15% stocks above 20 SMA (High bounce probability)

Portfolio Protection Rules:
1. EXTREME_OVERBOUGHT + BEARISH_DIVERGENCE = Reduce 30-50% exposure
2. BEARISH_DIVERGENCE sustained 3+ days = Consider hedging
3. EXTREME_OVERSOLD + BULLISH_DIVERGENCE = Opportunity to add
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus
import logging
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class MarketSignal(Enum):
    """Market condition signals."""
    EXTREME_OVERBOUGHT = "🔴 EXTREME OVERBOUGHT"
    OVERBOUGHT = "🟠 OVERBOUGHT"
    NEUTRAL = "🟢 NEUTRAL"
    OVERSOLD = "🟡 OVERSOLD"
    EXTREME_OVERSOLD = "🔵 EXTREME OVERSOLD"


class DivergenceType(Enum):
    """Divergence types."""
    BEARISH = "⚠️ BEARISH DIVERGENCE"
    BULLISH = "✅ BULLISH DIVERGENCE"
    NONE = "➖ NO DIVERGENCE"


@dataclass
class ExhaustionReading:
    """Single reading of market exhaustion indicators."""
    date: date
    index_close: float
    index_change_pct: float
    
    # Breadth indicators
    pct_above_10_sma: float
    pct_above_20_sma: float
    pct_above_50_sma: float
    pct_above_200_sma: float
    
    # Signals
    market_signal: MarketSignal
    divergence: DivergenceType
    
    # Protection recommendation
    risk_score: int  # 0-100, higher = more risk
    action: str


@dataclass
class ProtectionSignal:
    """Portfolio protection recommendation."""
    date: date
    risk_level: str  # LOW, MEDIUM, HIGH, EXTREME
    risk_score: int
    
    # Recommended actions
    reduce_exposure_pct: int
    increase_cash_pct: int
    hedge_recommendation: str
    
    # Supporting data
    reasons: List[str]
    
    def __str__(self):
        return f"""
╔══════════════════════════════════════════════════════════════╗
║  PORTFOLIO PROTECTION SIGNAL - {self.date}
╠══════════════════════════════════════════════════════════════╣
║  Risk Level: {self.risk_level} (Score: {self.risk_score}/100)
╠══════════════════════════════════════════════════════════════╣
║  RECOMMENDED ACTIONS:
║  • Reduce Equity Exposure by: {self.reduce_exposure_pct}%
║  • Target Cash Allocation: {self.increase_cash_pct}%
║  • Hedging: {self.hedge_recommendation}
╠══════════════════════════════════════════════════════════════╣
║  REASONS:
{"".join(f"║  • {r}" + chr(10) for r in self.reasons)}╚══════════════════════════════════════════════════════════════╝
"""


class DailyExhaustionDetector:
    """
    Detects market exhaustion using daily breadth analysis.
    
    Key indicators:
    - % of stocks above various SMAs (10, 20, 50, 200)
    - Divergence between index price and breadth
    - Extreme readings that historically precede corrections
    """
    
    # Nifty 50 symbols for quick analysis
    NIFTY_50_SYMBOLS = [
        'ADANIENT.NS', 'ADANIPORTS.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AXISBANK.NS',
        'BAJAJ-AUTO.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BEL.NS', 'BPCL.NS',
        'BHARTIARTL.NS', 'BRITANNIA.NS', 'CIPLA.NS', 'COALINDIA.NS', 'DRREDDY.NS',
        'EICHERMOT.NS', 'GRASIM.NS', 'HCLTECH.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS',
        'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'INDUSINDBK.NS',
        'INFY.NS', 'ITC.NS', 'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LT.NS',
        'M&M.NS', 'MARUTI.NS', 'NESTLEIND.NS', 'NTPC.NS', 'ONGC.NS',
        'POWERGRID.NS', 'RELIANCE.NS', 'SBILIFE.NS', 'SHRIRAMFIN.NS', 'SBIN.NS',
        'SUNPHARMA.NS', 'TATACONSUM.NS', 'TMPV.NS', 'TATASTEEL.NS', 'TCS.NS',
        'TECHM.NS', 'TITAN.NS', 'TRENT.NS', 'ULTRACEMCO.NS', 'WIPRO.NS'
    ]
    
    # Thresholds for signals
    EXTREME_OVERBOUGHT_THRESHOLD = 85
    OVERBOUGHT_THRESHOLD = 75
    OVERSOLD_THRESHOLD = 25
    EXTREME_OVERSOLD_THRESHOLD = 15
    
    # Divergence lookback periods
    DIVERGENCE_LOOKBACK = 10  # days
    
    def __init__(self, use_db: bool = True):
        """Initialize the detector."""
        self.use_db = use_db
        self.engine = self._create_engine() if use_db else None
        
        # Cache
        self._index_data: Optional[pd.DataFrame] = None
        self._stock_data: Dict[str, pd.DataFrame] = {}
        self._breadth_history: Optional[pd.DataFrame] = None
        
    def _create_engine(self):
        """Create SQLAlchemy engine."""
        try:
            from sqlalchemy.engine import URL
            url = URL.create(
                drivername="mysql+pymysql",
                username=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                database=os.getenv('MYSQL_DB', 'marketdata'),
                query={"charset": "utf8mb4"}
            )
            return create_engine(url, pool_pre_ping=True, pool_recycle=3600)
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            return None
    
    def fetch_daily_data(self, days: int = 250) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Fetch daily data for index and stocks.
        
        Args:
            days: Number of days to fetch (default 250 = ~1 year)
            
        Returns:
            Tuple of (index_df, stock_data_dict)
        """
        logger.info(f"Fetching {days} days of daily data...")
        
        # Fetch Nifty 50 Index
        ticker = yf.Ticker('^NSEI')
        index_df = ticker.history(period=f'{days}d', interval='1d')
        
        if index_df.empty:
            logger.error("Failed to fetch Nifty index data")
            return pd.DataFrame(), {}
        
        # Standardize columns
        index_df = index_df.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low',
            'Close': 'close', 'Volume': 'volume'
        })
        index_df = index_df[['open', 'high', 'low', 'close', 'volume']].copy()
        
        # Remove timezone
        if index_df.index.tz is not None:
            index_df.index = index_df.index.tz_localize(None)
        
        self._index_data = index_df
        logger.info(f"Fetched {len(index_df)} days of index data")
        
        # Fetch all stocks in batch
        logger.info(f"Fetching {len(self.NIFTY_50_SYMBOLS)} stocks...")
        stock_data = {}
        
        try:
            data = yf.download(
                self.NIFTY_50_SYMBOLS,
                period=f'{days}d',
                interval='1d',
                group_by='ticker',
                progress=False,
                threads=True
            )
            
            for symbol in self.NIFTY_50_SYMBOLS:
                try:
                    if symbol in data.columns.get_level_values(0):
                        df = data[symbol].copy()
                        df.columns = df.columns.str.lower()
                        
                        if 'close' in df.columns and not df['close'].dropna().empty:
                            df = df[['open', 'high', 'low', 'close', 'volume']].copy()
                            if df.index.tz is not None:
                                df.index = df.index.tz_localize(None)
                            stock_data[symbol] = df
                except Exception as e:
                    logger.debug(f"Error processing {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error batch downloading: {e}")
        
        self._stock_data = stock_data
        logger.info(f"Fetched {len(stock_data)} stocks")
        
        return index_df, stock_data
    
    def calculate_smas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SMAs for a stock."""
        result = df.copy()
        for period in [10, 20, 50, 200]:
            result[f'sma_{period}'] = result['close'].rolling(window=period).mean()
        return result
    
    def calculate_daily_breadth(self, 
                                 index_df: pd.DataFrame = None,
                                 stock_data: Dict[str, pd.DataFrame] = None) -> pd.DataFrame:
        """
        Calculate daily breadth indicators.
        
        Returns DataFrame with columns:
        - date, index_close, index_change_pct
        - pct_above_sma_10, pct_above_sma_20, pct_above_sma_50, pct_above_sma_200
        - total_stocks
        """
        index_df = index_df if index_df is not None else self._index_data
        stock_data = stock_data if stock_data is not None else self._stock_data
        
        if index_df is None or not stock_data:
            logger.error("No data available for breadth calculation")
            return pd.DataFrame()
        
        # Get common dates
        all_dates = index_df.index.tolist()
        
        # Initialize results
        results = []
        
        # Calculate SMAs for all stocks
        stock_with_smas = {}
        for symbol, df in stock_data.items():
            stock_with_smas[symbol] = self.calculate_smas(df)
        
        # For each date, calculate breadth
        for dt in all_dates:
            dt_date = dt.date() if hasattr(dt, 'date') else dt
            
            # Index data
            if dt not in index_df.index:
                continue
                
            idx_close = index_df.loc[dt, 'close']
            
            # Count stocks above each SMA
            counts = {10: 0, 20: 0, 50: 0, 200: 0}
            totals = {10: 0, 20: 0, 50: 0, 200: 0}
            
            for symbol, df in stock_with_smas.items():
                if dt not in df.index:
                    continue
                    
                close = df.loc[dt, 'close']
                if pd.isna(close):
                    continue
                
                for period in [10, 20, 50, 200]:
                    sma = df.loc[dt, f'sma_{period}']
                    if not pd.isna(sma):
                        totals[period] += 1
                        if close > sma:
                            counts[period] += 1
            
            # Calculate percentages
            pcts = {}
            for period in [10, 20, 50, 200]:
                pcts[period] = (counts[period] / totals[period] * 100) if totals[period] > 0 else 0
            
            results.append({
                'date': dt_date,
                'index_close': idx_close,
                'pct_above_sma_10': pcts[10],
                'pct_above_sma_20': pcts[20],
                'pct_above_sma_50': pcts[50],
                'pct_above_sma_200': pcts[200],
                'total_stocks': max(totals.values())
            })
        
        breadth_df = pd.DataFrame(results)
        
        if not breadth_df.empty:
            breadth_df['date'] = pd.to_datetime(breadth_df['date'])
            breadth_df.set_index('date', inplace=True)
            breadth_df.sort_index(inplace=True)
            
            # Calculate index change
            breadth_df['index_change_pct'] = breadth_df['index_close'].pct_change() * 100
        
        self._breadth_history = breadth_df
        logger.info(f"Calculated breadth for {len(breadth_df)} days")
        
        return breadth_df
    
    def detect_divergence(self, breadth_df: pd.DataFrame = None, 
                          lookback: int = None) -> DivergenceType:
        """
        Detect divergence between index and breadth.
        
        Bearish Divergence: Index making higher highs, breadth making lower highs
        Bullish Divergence: Index making lower lows, breadth making higher lows
        """
        breadth_df = breadth_df if breadth_df is not None else self._breadth_history
        lookback = lookback or self.DIVERGENCE_LOOKBACK
        
        if breadth_df is None or len(breadth_df) < lookback:
            return DivergenceType.NONE
        
        recent = breadth_df.tail(lookback)
        
        # Get first half and second half
        mid = lookback // 2
        first_half = recent.head(mid)
        second_half = recent.tail(mid)
        
        # Index trend
        index_first_avg = first_half['index_close'].mean()
        index_second_avg = second_half['index_close'].mean()
        index_rising = index_second_avg > index_first_avg
        
        # Breadth trend (using 20 SMA breadth)
        breadth_first_avg = first_half['pct_above_sma_20'].mean()
        breadth_second_avg = second_half['pct_above_sma_20'].mean()
        breadth_rising = breadth_second_avg > breadth_first_avg
        
        # Check for significant divergence (>2% difference in trend)
        index_change = (index_second_avg - index_first_avg) / index_first_avg * 100
        breadth_change = breadth_second_avg - breadth_first_avg
        
        # Bearish: Index up, breadth down
        if index_change > 1 and breadth_change < -5:
            return DivergenceType.BEARISH
        
        # Bullish: Index down, breadth up
        if index_change < -1 and breadth_change > 5:
            return DivergenceType.BULLISH
        
        return DivergenceType.NONE
    
    def get_market_signal(self, pct_above_20_sma: float) -> MarketSignal:
        """Get market signal based on breadth reading."""
        if pct_above_20_sma >= self.EXTREME_OVERBOUGHT_THRESHOLD:
            return MarketSignal.EXTREME_OVERBOUGHT
        elif pct_above_20_sma >= self.OVERBOUGHT_THRESHOLD:
            return MarketSignal.OVERBOUGHT
        elif pct_above_20_sma <= self.EXTREME_OVERSOLD_THRESHOLD:
            return MarketSignal.EXTREME_OVERSOLD
        elif pct_above_20_sma <= self.OVERSOLD_THRESHOLD:
            return MarketSignal.OVERSOLD
        else:
            return MarketSignal.NEUTRAL
    
    def calculate_risk_score(self, breadth_df: pd.DataFrame = None) -> int:
        """
        Calculate overall risk score (0-100).
        
        Factors:
        - Current breadth level (overbought = higher risk)
        - Divergence (bearish = higher risk)
        - Rate of change in breadth
        - Historical extremes
        """
        breadth_df = breadth_df if breadth_df is not None else self._breadth_history
        
        if breadth_df is None or breadth_df.empty:
            return 50
        
        latest = breadth_df.iloc[-1]
        pct_20 = latest['pct_above_sma_20']
        
        # Base score from current breadth (inverted - higher breadth = higher risk)
        # 50% breadth = 50 score, 85% = 85 score, 15% = 15 score
        base_score = pct_20
        
        # Divergence adjustment
        divergence = self.detect_divergence(breadth_df)
        if divergence == DivergenceType.BEARISH:
            base_score += 15
        elif divergence == DivergenceType.BULLISH:
            base_score -= 15
        
        # Rate of change adjustment (rapid rises are riskier)
        if len(breadth_df) >= 5:
            recent_change = breadth_df['pct_above_sma_20'].tail(5).diff().mean()
            if recent_change > 3:  # Rapid rise
                base_score += 10
            elif recent_change < -3:  # Rapid fall
                base_score -= 5
        
        # Historical context - check if at extremes
        if len(breadth_df) >= 50:
            percentile = (breadth_df['pct_above_sma_20'] < pct_20).mean() * 100
            if percentile > 90:  # In top 10% historically
                base_score += 10
        
        return max(0, min(100, int(base_score)))
    
    def generate_protection_signal(self, breadth_df: pd.DataFrame = None) -> ProtectionSignal:
        """
        Generate portfolio protection recommendation.
        """
        breadth_df = breadth_df if breadth_df is not None else self._breadth_history
        
        if breadth_df is None or breadth_df.empty:
            return None
        
        latest = breadth_df.iloc[-1]
        risk_score = self.calculate_risk_score(breadth_df)
        divergence = self.detect_divergence(breadth_df)
        market_signal = self.get_market_signal(latest['pct_above_sma_20'])
        
        reasons = []
        reduce_pct = 0
        cash_pct = 10  # Base cash
        hedge = "None required"
        
        # Determine risk level and actions
        if risk_score >= 80:
            risk_level = "EXTREME"
            reduce_pct = 30
            cash_pct = 30
            hedge = "Buy NIFTY PUT options (1-2% of portfolio)"
            reasons.append(f"Risk score at extreme level: {risk_score}/100")
        elif risk_score >= 65:
            risk_level = "HIGH"
            reduce_pct = 20
            cash_pct = 25
            hedge = "Consider protective puts on largest positions"
            reasons.append(f"Risk score elevated: {risk_score}/100")
        elif risk_score >= 50:
            risk_level = "MEDIUM"
            reduce_pct = 10
            cash_pct = 20
            hedge = "Tighten stop-losses"
            reasons.append(f"Risk score moderate: {risk_score}/100")
        else:
            risk_level = "LOW"
            reduce_pct = 0
            cash_pct = 10
            hedge = "None - favorable conditions"
            reasons.append(f"Risk score low: {risk_score}/100")
        
        # Add signal-specific reasons
        if market_signal == MarketSignal.EXTREME_OVERBOUGHT:
            reasons.append(f"Market EXTREME OVERBOUGHT: {latest['pct_above_sma_20']:.1f}% above 20 SMA")
            reduce_pct = max(reduce_pct, 25)
        elif market_signal == MarketSignal.OVERBOUGHT:
            reasons.append(f"Market OVERBOUGHT: {latest['pct_above_sma_20']:.1f}% above 20 SMA")
        elif market_signal == MarketSignal.EXTREME_OVERSOLD:
            reasons.append(f"Market EXTREME OVERSOLD: {latest['pct_above_sma_20']:.1f}% - potential bounce")
            reduce_pct = 0
            hedge = "Consider adding exposure on confirmation"
        
        # Divergence warnings
        if divergence == DivergenceType.BEARISH:
            reasons.append("⚠️ BEARISH DIVERGENCE: Index rising but participation declining!")
            reduce_pct = max(reduce_pct, 20)
            if risk_score >= 60:
                hedge = "STRONGLY recommend protective puts"
        elif divergence == DivergenceType.BULLISH:
            reasons.append("✅ BULLISH DIVERGENCE: Index falling but participation improving")
        
        # Add breadth breakdown
        reasons.append(f"Stocks > 10 SMA: {latest['pct_above_sma_10']:.1f}%")
        reasons.append(f"Stocks > 20 SMA: {latest['pct_above_sma_20']:.1f}%")
        reasons.append(f"Stocks > 50 SMA: {latest['pct_above_sma_50']:.1f}%")
        reasons.append(f"Stocks > 200 SMA: {latest['pct_above_sma_200']:.1f}%")
        
        return ProtectionSignal(
            date=latest.name.date() if hasattr(latest.name, 'date') else latest.name,
            risk_level=risk_level,
            risk_score=risk_score,
            reduce_exposure_pct=reduce_pct,
            increase_cash_pct=cash_pct,
            hedge_recommendation=hedge,
            reasons=reasons
        )
    
    def get_current_reading(self) -> ExhaustionReading:
        """Get current market exhaustion reading."""
        if self._breadth_history is None or self._breadth_history.empty:
            return None
        
        latest = self._breadth_history.iloc[-1]
        divergence = self.detect_divergence()
        market_signal = self.get_market_signal(latest['pct_above_sma_20'])
        risk_score = self.calculate_risk_score()
        
        # Determine action
        if risk_score >= 70:
            action = "REDUCE EXPOSURE - High risk of correction"
        elif risk_score >= 50:
            action = "CAUTION - Tighten stops, avoid new longs"
        elif risk_score <= 30:
            action = "OPPORTUNITY - Consider adding positions"
        else:
            action = "HOLD - Normal conditions"
        
        return ExhaustionReading(
            date=latest.name.date() if hasattr(latest.name, 'date') else latest.name,
            index_close=latest['index_close'],
            index_change_pct=latest['index_change_pct'],
            pct_above_10_sma=latest['pct_above_sma_10'],
            pct_above_20_sma=latest['pct_above_sma_20'],
            pct_above_50_sma=latest['pct_above_sma_50'],
            pct_above_200_sma=latest['pct_above_sma_200'],
            market_signal=market_signal,
            divergence=divergence,
            risk_score=risk_score,
            action=action
        )
    
    def run_analysis(self, days: int = 250) -> Tuple[ExhaustionReading, ProtectionSignal]:
        """
        Run complete exhaustion analysis.
        
        Returns:
            Tuple of (current_reading, protection_signal)
        """
        logger.info("=" * 60)
        logger.info("Running Market Exhaustion Analysis")
        logger.info("=" * 60)
        
        # Fetch data
        index_df, stock_data = self.fetch_daily_data(days)
        
        if index_df.empty or not stock_data:
            logger.error("Failed to fetch data")
            return None, None
        
        # Calculate breadth
        breadth_df = self.calculate_daily_breadth(index_df, stock_data)
        
        if breadth_df.empty:
            logger.error("Failed to calculate breadth")
            return None, None
        
        # Get results
        reading = self.get_current_reading()
        signal = self.generate_protection_signal()
        
        return reading, signal


def main():
    """Main entry point - run analysis and print results."""
    print("=" * 70)
    print("   MARKET EXHAUSTION DETECTOR - Portfolio Protection System")
    print("=" * 70)
    print()
    
    detector = DailyExhaustionDetector(use_db=False)
    reading, signal = detector.run_analysis(days=250)
    
    if reading is None:
        print("❌ Failed to run analysis")
        return
    
    print()
    print("=" * 70)
    print("   CURRENT MARKET READING")
    print("=" * 70)
    print(f"Date: {reading.date}")
    print(f"Nifty 50: {reading.index_close:,.2f} ({reading.index_change_pct:+.2f}%)")
    print()
    print("BREADTH INDICATORS:")
    print(f"  • Stocks > 10 SMA:  {reading.pct_above_10_sma:5.1f}%")
    print(f"  • Stocks > 20 SMA:  {reading.pct_above_20_sma:5.1f}%")
    print(f"  • Stocks > 50 SMA:  {reading.pct_above_50_sma:5.1f}%")
    print(f"  • Stocks > 200 SMA: {reading.pct_above_200_sma:5.1f}%")
    print()
    print(f"MARKET SIGNAL: {reading.market_signal.value}")
    print(f"DIVERGENCE:    {reading.divergence.value}")
    print(f"RISK SCORE:    {reading.risk_score}/100")
    print()
    print(f"ACTION: {reading.action}")
    
    if signal:
        print()
        print(signal)


if __name__ == "__main__":
    main()
