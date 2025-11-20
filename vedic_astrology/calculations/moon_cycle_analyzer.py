"""
Moon Cycle Analysis Engine for Stock Market Analysis

This module provides comprehensive moon cycle tracking and analysis for correlation
with stock market movements, including lunar calendar generation, phase impact 
analysis, and market correlation patterns.

Author: Stock Screener with Vedic Astrology Integration
"""

import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from sqlalchemy import create_engine, Column, String, Float, Date, TIMESTAMP, Index
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os

from core_calculator import VedicAstrologyCalculator, LunarPhase


@dataclass
class MoonCycleData:
    """Data class for moon cycle information"""
    date: datetime.date
    phase: str
    illumination: float
    age_days: float
    nakshatra: str
    market_trend_prediction: str
    volatility_score: float
    suggested_strategy: str


class MoonCycleAnalyzer:
    """Comprehensive moon cycle analysis engine for market correlation (MySQL version)"""

    def __init__(self, mysql_url: Optional[str] = None):
        self.calculator = VedicAstrologyCalculator()

        # MySQL connection string (read from env or pass as arg)
        if mysql_url is None:
            # Try to build from environment variables
            mysql_url = self._get_mysql_url_from_env()
        self.engine = create_engine(mysql_url, pool_pre_ping=True, pool_recycle=3600)
        self.Session = sessionmaker(bind=self.engine)

        # SQLAlchemy ORM base
        Base = declarative_base()
        self.Base = Base

        class LunarCycle(Base):
            __tablename__ = 'lunar_cycles'
            date = Column(Date, primary_key=True)
            phase = Column(String(32), nullable=False)
            illumination = Column(Float)
            age_days = Column(Float)
            nakshatra = Column(String(32))
            market_trend_prediction = Column(String(32))
            volatility_score = Column(Float)
            suggested_strategy = Column(String(32))
            created_at = Column(TIMESTAMP)
            __table_args__ = (
                Index('idx_lunar_date', 'date'),
                Index('idx_lunar_phase', 'phase'),
            )
        self.LunarCycle = LunarCycle

        # Create table if not exists
        self.Base.metadata.create_all(self.engine)

        # Moon phase to market correlation mapping
        self.phase_correlations = {
            LunarPhase.NEW_MOON: {
                'volatility_multiplier': 0.7,
                'trend_bias': 'neutral_to_bullish',
                'volume_impact': 'low',
                'strategy': 'accumulation'
            },
            LunarPhase.WAXING_CRESCENT: {
                'volatility_multiplier': 0.8,
                'trend_bias': 'bullish',
                'volume_impact': 'increasing',
                'strategy': 'momentum_building'
            },
            LunarPhase.FIRST_QUARTER: {
                'volatility_multiplier': 1.0,
                'trend_bias': 'bullish',
                'volume_impact': 'normal',
                'strategy': 'trend_following'
            },
            LunarPhase.WAXING_GIBBOUS: {
                'volatility_multiplier': 1.2,
                'trend_bias': 'strong_bullish',
                'volume_impact': 'high',
                'strategy': 'momentum_trading'
            },
            LunarPhase.FULL_MOON: {
                'volatility_multiplier': 1.5,
                'trend_bias': 'volatile',
                'volume_impact': 'very_high',
                'strategy': 'profit_booking'
            },
            LunarPhase.WANING_GIBBOUS: {
                'volatility_multiplier': 1.3,
                'trend_bias': 'bearish_pressure',
                'volume_impact': 'high',
                'strategy': 'defensive'
            },
            LunarPhase.LAST_QUARTER: {
                'volatility_multiplier': 1.1,
                'trend_bias': 'bearish',
                'volume_impact': 'normal',
                'strategy': 'value_hunting'
            },
            LunarPhase.WANING_CRESCENT: {
                'volatility_multiplier': 0.9,
                'trend_bias': 'weak_bearish',
                'volume_impact': 'decreasing',
                'strategy': 'contrarian'
            }
        }
        

    def _get_mysql_url_from_env(self):
        # Reads same env variables as sync_bhav_gui.py
        import os
        from dotenv import load_dotenv
        from sqlalchemy.engine import URL
        
        load_dotenv()
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        host = os.getenv('MYSQL_HOST', '127.0.0.1')
        port = int(os.getenv('MYSQL_PORT', '3306'))
        db = os.getenv('MYSQL_DB', 'marketdata')
        
        # Use SQLAlchemy URL to properly handle special characters
        url = URL.create(
            drivername="mysql+pymysql",
            username=user,
            password=password,
            host=host,
            port=port,
            database=db,
            query={"charset": "utf8mb4"},
        )
        return url
    
    def generate_lunar_calendar(self, start_date: datetime.date, 
                              end_date: datetime.date) -> List[MoonCycleData]:
        """
        Generate lunar calendar for a date range with market analysis
        
        Args:
            start_date: Start date for calendar generation
            end_date: End date for calendar generation
            
        Returns:
            List of MoonCycleData objects with daily lunar information
        """
        lunar_calendar = []
        current_date = start_date
        
        while current_date <= end_date:
            # Get moon phase information for this date
            date_time = datetime.datetime.combine(current_date, datetime.time(12, 0))
            date_time = date_time.replace(tzinfo=datetime.timezone.utc)
            
            moon_info = self.calculator.get_moon_phase(date_time)
            nakshatra_info = self.calculator.get_current_nakshatra(date_time)
            
            # Get phase enum for correlation lookup
            phase_enum = self._get_phase_enum(moon_info['phase_name'])
            correlation = self.phase_correlations.get(phase_enum, {})
            
            # Calculate volatility score
            base_volatility = 1.0
            volatility_score = base_volatility * correlation.get('volatility_multiplier', 1.0)
            
            # Create moon cycle data
            cycle_data = MoonCycleData(
                date=current_date,
                phase=moon_info['phase_name'],
                illumination=moon_info['illumination_percentage'],
                age_days=moon_info['age_days'],
                nakshatra=nakshatra_info['name'],
                market_trend_prediction=correlation.get('trend_bias', 'neutral'),
                volatility_score=round(volatility_score, 3),
                suggested_strategy=correlation.get('strategy', 'normal_trading')
            )
            
            lunar_calendar.append(cycle_data)
            current_date += datetime.timedelta(days=1)
        
        return lunar_calendar
    
    def _get_phase_enum(self, phase_name: str) -> LunarPhase:
        """Convert phase name string to LunarPhase enum"""
        phase_mapping = {
            'New Moon': LunarPhase.NEW_MOON,
            'Waxing Crescent': LunarPhase.WAXING_CRESCENT,
            'First Quarter': LunarPhase.FIRST_QUARTER,
            'Waxing Gibbous': LunarPhase.WAXING_GIBBOUS,
            'Full Moon': LunarPhase.FULL_MOON,
            'Waning Gibbous': LunarPhase.WANING_GIBBOUS,
            'Last Quarter': LunarPhase.LAST_QUARTER,
            'Waning Crescent': LunarPhase.WANING_CRESCENT
        }
        return phase_mapping.get(phase_name, LunarPhase.NEW_MOON)
    
    def save_lunar_calendar(self, lunar_data: List[MoonCycleData]) -> bool:
        """
        Save lunar calendar data to MySQL database
        """
        session = self.Session()
        try:
            for data in lunar_data:
                obj = self.LunarCycle(
                    date=data.date,
                    phase=data.phase,
                    illumination=data.illumination,
                    age_days=data.age_days,
                    nakshatra=data.nakshatra,
                    market_trend_prediction=data.market_trend_prediction,
                    volatility_score=data.volatility_score,
                    suggested_strategy=data.suggested_strategy
                )
                session.merge(obj)  # Upsert
            session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error saving lunar calendar: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_lunar_data(self, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
        """
        Retrieve lunar data from MySQL database as DataFrame
        """
        session = self.Session()
        try:
            q = session.query(self.LunarCycle).filter(
                self.LunarCycle.date >= start_date,
                self.LunarCycle.date <= end_date
            ).order_by(self.LunarCycle.date)
            records = q.all()
            if not records:
                return pd.DataFrame()
            df = pd.DataFrame([
                {
                    'date': r.date,
                    'phase': r.phase,
                    'illumination': r.illumination,
                    'age_days': r.age_days,
                    'nakshatra': r.nakshatra,
                    'market_trend_prediction': r.market_trend_prediction,
                    'volatility_score': r.volatility_score,
                    'suggested_strategy': r.suggested_strategy
                } for r in records
            ])
            df['date'] = pd.to_datetime(df['date'])
            return df
        except SQLAlchemyError as e:
            print(f"Error retrieving lunar data: {e}")
            return pd.DataFrame()
        finally:
            session.close()
    
    def analyze_phase_transitions(self, days_back: int = 90) -> Dict[str, Any]:
        """
        Analyze lunar phase transitions and their potential market impact
        
        Args:
            days_back: Number of days to look back for analysis
            
        Returns:
            Dictionary with phase transition analysis
        """
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days_back)
        
        lunar_df = self.get_lunar_data(start_date, end_date)
        
        if lunar_df.empty:
            # Generate and save lunar data if not available
            lunar_calendar = self.generate_lunar_calendar(start_date, end_date)
            self.save_lunar_calendar(lunar_calendar)
            lunar_df = self.get_lunar_data(start_date, end_date)
        
        # Identify phase transitions
        transitions = []
        previous_phase = None
        
        for _, row in lunar_df.iterrows():
            current_phase = row['phase']
            if previous_phase and previous_phase != current_phase:
                transitions.append({
                    'date': row['date'],
                    'from_phase': previous_phase,
                    'to_phase': current_phase,
                    'volatility_change': self._calculate_volatility_change(previous_phase, current_phase),
                    'market_impact': self._get_transition_impact(previous_phase, current_phase)
                })
            previous_phase = current_phase
        
        # Analyze upcoming transitions
        upcoming_transitions = self._predict_upcoming_transitions()
        
        return {
            'recent_transitions': transitions[-5:],  # Last 5 transitions
            'upcoming_transitions': upcoming_transitions,
            'phase_statistics': self._calculate_phase_statistics(lunar_df),
            'volatility_patterns': self._analyze_volatility_patterns(lunar_df)
        }
    
    def _calculate_volatility_change(self, from_phase: str, to_phase: str) -> float:
        """Calculate volatility change between phases"""
        from_enum = self._get_phase_enum(from_phase)
        to_enum = self._get_phase_enum(to_phase)
        
        from_vol = self.phase_correlations.get(from_enum, {}).get('volatility_multiplier', 1.0)
        to_vol = self.phase_correlations.get(to_enum, {}).get('volatility_multiplier', 1.0)
        
        return round(to_vol - from_vol, 3)
    
    def _get_transition_impact(self, from_phase: str, to_phase: str) -> str:
        """Get market impact description for phase transition"""
        from_enum = self._get_phase_enum(from_phase)
        to_enum = self._get_phase_enum(to_phase)
        
        impact_matrix = {
            (LunarPhase.NEW_MOON, LunarPhase.WAXING_CRESCENT): "Start of bullish momentum",
            (LunarPhase.WAXING_CRESCENT, LunarPhase.FIRST_QUARTER): "Building momentum confirmation",
            (LunarPhase.FIRST_QUARTER, LunarPhase.WAXING_GIBBOUS): "Strong bullish acceleration",
            (LunarPhase.WAXING_GIBBOUS, LunarPhase.FULL_MOON): "Peak volatility approaching",
            (LunarPhase.FULL_MOON, LunarPhase.WANING_GIBBOUS): "Profit booking signals",
            (LunarPhase.WANING_GIBBOUS, LunarPhase.LAST_QUARTER): "Correction phase begins",
            (LunarPhase.LAST_QUARTER, LunarPhase.WANING_CRESCENT): "Final selling pressure",
            (LunarPhase.WANING_CRESCENT, LunarPhase.NEW_MOON): "Bottom formation phase"
        }
        
        return impact_matrix.get((from_enum, to_enum), "Normal transition")
    
    def _predict_upcoming_transitions(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Predict upcoming lunar phase transitions"""
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=days_ahead)
        
        lunar_calendar = self.generate_lunar_calendar(start_date, end_date)
        
        transitions = []
        previous_phase = None
        
        for data in lunar_calendar:
            if previous_phase and previous_phase != data.phase:
                transitions.append({
                    'date': data.date,
                    'from_phase': previous_phase,
                    'to_phase': data.phase,
                    'days_from_now': (data.date - start_date).days,
                    'market_impact': self._get_transition_impact(previous_phase, data.phase),
                    'volatility_change': self._calculate_volatility_change(previous_phase, data.phase),
                    'suggested_strategy': data.suggested_strategy
                })
            previous_phase = data.phase
        
        return transitions
    
    def _calculate_phase_statistics(self, lunar_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate statistics for each lunar phase"""
        if lunar_df.empty:
            return {}
        
        stats = {}
        for phase in lunar_df['phase'].unique():
            phase_data = lunar_df[lunar_df['phase'] == phase]
            stats[phase] = {
                'avg_volatility': round(phase_data['volatility_score'].mean(), 3),
                'days_count': len(phase_data),
                'frequency': round(len(phase_data) / len(lunar_df) * 100, 1)
            }
        
        return stats
    
    def _analyze_volatility_patterns(self, lunar_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volatility patterns across lunar phases"""
        if lunar_df.empty:
            return {}
        
        # Calculate volatility statistics
        volatility_stats = {
            'overall_avg': round(lunar_df['volatility_score'].mean(), 3),
            'min_volatility': round(lunar_df['volatility_score'].min(), 3),
            'max_volatility': round(lunar_df['volatility_score'].max(), 3),
            'volatility_range': round(
                lunar_df['volatility_score'].max() - lunar_df['volatility_score'].min(), 3
            )
        }
        
        # Identify high and low volatility phases
        high_vol_threshold = volatility_stats['overall_avg'] * 1.2
        low_vol_threshold = volatility_stats['overall_avg'] * 0.8
        
        high_vol_phases = lunar_df[lunar_df['volatility_score'] > high_vol_threshold]['phase'].unique()
        low_vol_phases = lunar_df[lunar_df['volatility_score'] < low_vol_threshold]['phase'].unique()
        
        return {
            'statistics': volatility_stats,
            'high_volatility_phases': list(high_vol_phases),
            'low_volatility_phases': list(low_vol_phases),
            'volatility_trend': self._calculate_volatility_trend(lunar_df)
        }
    
    def _calculate_volatility_trend(self, lunar_df: pd.DataFrame) -> str:
        """Calculate overall volatility trend"""
        if len(lunar_df) < 2:
            return "insufficient_data"
        
        recent_volatility = lunar_df['volatility_score'].tail(7).mean()
        earlier_volatility = lunar_df['volatility_score'].head(7).mean()
        
        if recent_volatility > earlier_volatility * 1.1:
            return "increasing"
        elif recent_volatility < earlier_volatility * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def get_current_moon_guidance(self) -> Dict[str, Any]:
        """
        Get current moon phase guidance for trading
        
        Returns:
            Dictionary with current lunar analysis and trading guidance
        """
        current_time = datetime.datetime.now()
        
        # Get current lunar information
        moon_info = self.calculator.get_moon_phase(current_time)
        nakshatra_info = self.calculator.get_current_nakshatra(current_time)
        timing_info = self.calculator.is_auspicious_time(current_time)
        
        # Get phase correlation
        phase_enum = self._get_phase_enum(moon_info['phase_name'])
        correlation = self.phase_correlations.get(phase_enum, {})
        
        # Analyze recent transitions
        transition_analysis = self.analyze_phase_transitions(days_back=30)
        
        return {
            'current_date': current_time.strftime('%Y-%m-%d'),
            'moon_phase': {
                'name': moon_info['phase_name'],
                'illumination': moon_info['illumination_percentage'],
                'age_days': moon_info['age_days']
            },
            'nakshatra': {
                'name': nakshatra_info['name'],
                'characteristics': nakshatra_info['characteristics'],
                'market_influence': nakshatra_info['market_influence']
            },
            'market_guidance': {
                'trend_bias': correlation.get('trend_bias', 'neutral'),
                'volatility_level': correlation.get('volatility_multiplier', 1.0),
                'suggested_strategy': correlation.get('strategy', 'normal_trading'),
                'volume_expectation': correlation.get('volume_impact', 'normal')
            },
            'timing_analysis': timing_info,
            'upcoming_transitions': transition_analysis.get('upcoming_transitions', [])[:3],
            'overall_recommendation': self._generate_overall_recommendation(
                moon_info, nakshatra_info, timing_info, correlation
            )
        }
    
    def _generate_overall_recommendation(self, moon_info: Dict, nakshatra_info: Dict, 
                                       timing_info: Dict, correlation: Dict) -> str:
        """Generate overall trading recommendation"""
        phase = moon_info['phase_name']
        strategy = correlation.get('strategy', 'normal_trading')
        is_auspicious = timing_info['is_auspicious']
        
        if not is_auspicious:
            return f"Current {phase} suggests {strategy}, but timing is not auspicious. Exercise caution."
        else:
            return f"Favorable conditions: {phase} supports {strategy} strategy. Good timing for trading."


def test_moon_cycle_analyzer():
    """Test function for moon cycle analyzer"""
    print("=== Testing Moon Cycle Analyzer ===")
    
    analyzer = MoonCycleAnalyzer()
    
    # Test current guidance
    print("\nCURRENT MOON GUIDANCE:")
    guidance = analyzer.get_current_moon_guidance()
    
    print(f"Date: {guidance['current_date']}")
    print(f"Moon Phase: {guidance['moon_phase']['name']} ({guidance['moon_phase']['illumination']}%)")
    print(f"Nakshatra: {guidance['nakshatra']['name']}")
    print(f"Trend Bias: {guidance['market_guidance']['trend_bias']}")
    print(f"Strategy: {guidance['market_guidance']['suggested_strategy']}")
    print(f"Overall: {guidance['overall_recommendation']}")
    
    # Test lunar calendar generation
    print("\nLUNAR CALENDAR (Next 7 days):")
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=7)
    
    lunar_calendar = analyzer.generate_lunar_calendar(start_date, end_date)
    
    for data in lunar_calendar:
        print(f"{data.date}: {data.phase} | {data.nakshatra} | Strategy: {data.suggested_strategy}")
    
    # Test phase transition analysis
    print("\nPHASE TRANSITION ANALYSIS:")
    transitions = analyzer.analyze_phase_transitions(days_back=30)
    
    if transitions['upcoming_transitions']:
        print("Upcoming Transitions:")
        for trans in transitions['upcoming_transitions'][:3]:
            print(f"  {trans['date']}: {trans['from_phase']} → {trans['to_phase']} ({trans['market_impact']})")
    
    print("\nMoon Cycle Analyzer test completed successfully!")


if __name__ == "__main__":
    test_moon_cycle_analyzer()