#!/usr/bin/env python3
"""
Sectoral Trends Service
=====================

Service for tracking and analyzing sectoral bullish/bearish percentages over time.
Stores daily calculations and provides data for trend analysis and charting.
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import text
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.market_breadth_service import get_sectoral_breadth, get_engine
from services.index_symbols_api import get_api

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SectoralTrendsService:
    """Service for tracking sectoral trends over time."""
    
    def __init__(self):
        self.engine = None
        self._ensure_engine()
        self._ensure_table()
    
    def _ensure_engine(self):
        """Ensure database engine is available."""
        try:
            self.engine = get_engine()
        except Exception as e:
            logger.error(f"Failed to get database engine: {e}")
            raise
    
    def _ensure_table(self):
        """Ensure the sectoral trends table exists."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sectoral_trends_daily (
            id INT AUTO_INCREMENT PRIMARY KEY,
            analysis_date DATE NOT NULL,
            sector_code VARCHAR(50) NOT NULL,
            sector_name VARCHAR(100) NOT NULL,
            total_stocks INT NOT NULL DEFAULT 0,
            bullish_count INT NOT NULL DEFAULT 0,
            bearish_count INT NOT NULL DEFAULT 0,
            bullish_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
            bearish_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
            daily_uptrend_count INT NOT NULL DEFAULT 0,
            weekly_uptrend_count INT NOT NULL DEFAULT 0,
            daily_uptrend_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
            weekly_uptrend_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
            avg_trend_rating DECIMAL(4,2) NOT NULL DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            UNIQUE KEY unique_date_sector (analysis_date, sector_code),
            INDEX idx_analysis_date (analysis_date),
            INDEX idx_sector_code (sector_code),
            INDEX idx_sector_date (sector_code, analysis_date)
        )
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(create_table_sql))
                conn.commit()
                logger.info("✅ Sectoral trends table ensured")
        except Exception as e:
            logger.error(f"Failed to create sectoral trends table: {e}")
            raise
    
    def get_available_sectors(self) -> List[str]:
        """Get list of available sectors for analysis."""
        try:
            api = get_api()
            all_indices = api.get_all_indices()
            sectors = [s for s in all_indices.keys() if 'NIFTY' in s and len(s) < 25]
            sectors = sorted(sectors[:15])  # Get top 15 reasonable sectors
            return sectors
        except Exception as e:
            logger.error(f"Failed to get sectors list: {e}")
            # Fallback list
            return [
                'NIFTY-50', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO', 'NIFTY-PHARMA',
                'NIFTY-FMCG', 'NIFTY-REALTY', 'NIFTY-METAL', 'NIFTY-ENERGY',
                'NIFTY-HEALTHCARE-INDEX', 'NIFTY-CONSUMER-DURABLES', 'NIFTY-CHEMICALS'
            ]
    
    def calculate_and_store_daily_trends(self, start_date: date, end_date: date) -> Dict[str, int]:
        """
        Calculate sectoral trends for a date range and store in database.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Dict with calculation statistics
        """
        stats = {
            'dates_processed': 0,
            'sectors_processed': 0,
            'total_records': 0,
            'errors': 0
        }
        
        sectors = self.get_available_sectors()
        
        # Get available analysis dates from trend_analysis table
        available_dates_query = """
        SELECT DISTINCT trade_date 
        FROM trend_analysis 
        WHERE trade_date BETWEEN :start_date AND :end_date 
        ORDER BY trade_date
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(available_dates_query), {'start_date': start_date, 'end_date': end_date})
                available_dates = [row[0] for row in result.fetchall()]
                
                logger.info(f"📅 Found {len(available_dates)} available dates between {start_date} and {end_date}")
                
                for analysis_date in available_dates:
                    date_stats = self._process_date(analysis_date, sectors)
                    stats['dates_processed'] += 1
                    stats['sectors_processed'] += date_stats['sectors_processed']
                    stats['total_records'] += date_stats['records_created']
                    stats['errors'] += date_stats['errors']
                    
                    if stats['dates_processed'] % 5 == 0:
                        logger.info(f"📊 Processed {stats['dates_processed']} dates...")
                
                logger.info(f"✅ Calculation completed: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"Failed to calculate daily trends: {e}")
            stats['errors'] += 1
            return stats
    
    def _process_date(self, analysis_date: date, sectors: List[str]) -> Dict[str, int]:
        """Process a single date for all sectors."""
        date_stats = {
            'sectors_processed': 0,
            'records_created': 0,
            'errors': 0
        }
        
        for sector_code in sectors:
            try:
                # Get sectoral data
                result = get_sectoral_breadth(sector_code, analysis_date=analysis_date)
                
                if result and result.get('success') == True:
                    # Extract data from result structure
                    breadth_summary = result.get('breadth_summary', {})
                    technical_breadth = result.get('technical_breadth', {})
                    
                    # Calculate average trend rating from sector data if available
                    avg_rating = 0.0
                    sector_data = result.get('sector_data')
                    if sector_data is not None and hasattr(sector_data, 'shape') and sector_data.shape[0] > 0:
                        avg_rating = float(sector_data['trend_rating'].mean())
                    
                    # Prepare record
                    record = {
                        'analysis_date': analysis_date,
                        'sector_code': sector_code,
                        'sector_name': sector_code.replace('NIFTY-', '').replace('-', ' ').title(),
                        'total_stocks': result.get('total_stocks', 0),
                        'bullish_count': breadth_summary.get('bullish_count', 0),
                        'bearish_count': breadth_summary.get('bearish_count', 0),
                        'bullish_percent': breadth_summary.get('bullish_percent', 0.0),
                        'bearish_percent': breadth_summary.get('bearish_percent', 0.0),
                        'daily_uptrend_count': technical_breadth.get('daily_uptrend_count', 0),
                        'weekly_uptrend_count': technical_breadth.get('weekly_uptrend_count', 0),
                        'daily_uptrend_percent': technical_breadth.get('daily_uptrend_percent', 0.0),
                        'weekly_uptrend_percent': technical_breadth.get('weekly_uptrend_percent', 0.0),
                        'avg_trend_rating': avg_rating
                    }
                    
                    # Store in database
                    if self._store_record(record):
                        date_stats['records_created'] += 1
                    
                    date_stats['sectors_processed'] += 1
                    
            except Exception as e:
                logger.warning(f"Failed to process {sector_code} for {analysis_date}: {e}")
                date_stats['errors'] += 1
        
        return date_stats
    
    def _store_record(self, record: Dict) -> bool:
        """Store a single record in database."""
        insert_sql = """
        INSERT INTO sectoral_trends_daily 
        (analysis_date, sector_code, sector_name, total_stocks, bullish_count, bearish_count,
         bullish_percent, bearish_percent, daily_uptrend_count, weekly_uptrend_count,
         daily_uptrend_percent, weekly_uptrend_percent, avg_trend_rating)
        VALUES 
        (:analysis_date, :sector_code, :sector_name, :total_stocks, :bullish_count, :bearish_count,
         :bullish_percent, :bearish_percent, :daily_uptrend_count, :weekly_uptrend_count,
         :daily_uptrend_percent, :weekly_uptrend_percent, :avg_trend_rating)
        ON DUPLICATE KEY UPDATE
        total_stocks = VALUES(total_stocks),
        bullish_count = VALUES(bullish_count),
        bearish_count = VALUES(bearish_count),
        bullish_percent = VALUES(bullish_percent),
        bearish_percent = VALUES(bearish_percent),
        daily_uptrend_count = VALUES(daily_uptrend_count),
        weekly_uptrend_count = VALUES(weekly_uptrend_count),
        daily_uptrend_percent = VALUES(daily_uptrend_percent),
        weekly_uptrend_percent = VALUES(weekly_uptrend_percent),
        avg_trend_rating = VALUES(avg_trend_rating),
        updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(insert_sql), record)
                conn.commit()
                return True
        except Exception as e:
            logger.warning(f"Failed to store record: {e}")
            return False
    
    def get_trends_data(self, 
                       sectors: Optional[List[str]] = None,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None,
                       days_back: int = 30) -> pd.DataFrame:
        """
        Get trends data for charting.
        
        Args:
            sectors: List of sector codes to include (None for all)
            start_date: Start date (None for auto-calculate)
            end_date: End date (None for latest)
            days_back: Days to go back if dates not specified
            
        Returns:
            DataFrame with trends data
        """
        # Set default date range
        if end_date is None:
            end_date = date.today()
        
        if start_date is None:
            start_date = end_date - timedelta(days=days_back)
        
        # Build query
        base_query = """
        SELECT 
            analysis_date,
            sector_code,
            sector_name,
            total_stocks,
            bullish_percent,
            bearish_percent,
            daily_uptrend_percent,
            weekly_uptrend_percent,
            avg_trend_rating
        FROM sectoral_trends_daily 
        WHERE analysis_date BETWEEN :start_date AND :end_date
        """
        
        params = {'start_date': start_date, 'end_date': end_date}
        
        if sectors:
            # Use IN clause with bound parameters for sectors
            sector_params = {f'sector_{i}': sector for i, sector in enumerate(sectors)}
            placeholders = ','.join([f':sector_{i}' for i in range(len(sectors))])
            base_query += f" AND sector_code IN ({placeholders})"
            params.update(sector_params)
        
        base_query += " ORDER BY analysis_date, sector_code"
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(base_query), params)
                columns = [
                    'analysis_date', 'sector_code', 'sector_name', 'total_stocks',
                    'bullish_percent', 'bearish_percent', 'daily_uptrend_percent',
                    'weekly_uptrend_percent', 'avg_trend_rating'
                ]
                data = [dict(zip(columns, row)) for row in result.fetchall()]
                df = pd.DataFrame(data)
                logger.info(f"📊 Retrieved {len(df)} trend records")
                return df
        except Exception as e:
            logger.error(f"Failed to get trends data: {e}")
            return pd.DataFrame()
    
    def get_available_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        """Get the available date range in the trends table."""
        query = """
        SELECT MIN(analysis_date) as min_date, MAX(analysis_date) as max_date
        FROM sectoral_trends_daily
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query)).fetchone()
                if result and result[0] and result[1]:
                    return result[0], result[1]
                else:
                    return None, None
        except Exception as e:
            logger.error(f"Failed to get date range: {e}")
            return None, None
    
    def get_data_summary(self) -> Dict:
        """Get summary of available data."""
        summary_query = """
        SELECT 
            COUNT(DISTINCT analysis_date) as total_dates,
            COUNT(DISTINCT sector_code) as total_sectors,
            COUNT(*) as total_records,
            MIN(analysis_date) as earliest_date,
            MAX(analysis_date) as latest_date
        FROM sectoral_trends_daily
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(summary_query)).fetchone()
                if result:
                    return {
                        'total_dates': result[0] or 0,
                        'total_sectors': result[1] or 0,
                        'total_records': result[2] or 0,
                        'earliest_date': result[3],
                        'latest_date': result[4]
                    }
                else:
                    return {
                        'total_dates': 0,
                        'total_sectors': 0,
                        'total_records': 0,
                        'earliest_date': None,
                        'latest_date': None
                    }
        except Exception as e:
            logger.error(f"Failed to get data summary: {e}")
            return {
                'total_dates': 0,
                'total_sectors': 0,
                'total_records': 0,
                'earliest_date': None,
                'latest_date': None
            }

# Convenience functions
def populate_trends_data(days_back: int = 30) -> Dict[str, int]:
    """
    Populate trends data for the last N days.
    
    Args:
        days_back: Number of days to go back
        
    Returns:
        Calculation statistics
    """
    service = SectoralTrendsService()
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    logger.info(f"📊 Populating trends data from {start_date} to {end_date}")
    return service.calculate_and_store_daily_trends(start_date, end_date)

def get_trends_for_charting(sectors: List[str] = None, days_back: int = 30) -> pd.DataFrame:
    """
    Get trends data formatted for charting.
    
    Args:
        sectors: List of sectors to include (None for all)
        days_back: Number of days to include
        
    Returns:
        DataFrame with trends data
    """
    service = SectoralTrendsService()
    return service.get_trends_data(sectors=sectors, days_back=days_back)

if __name__ == "__main__":
    # Test the service
    service = SectoralTrendsService()
    
    print("🔍 Testing Sectoral Trends Service")
    print("=" * 50)
    
    # Get data summary
    summary = service.get_data_summary()
    print(f"📊 Data Summary: {summary}")
    
    # Get available sectors
    sectors = service.get_available_sectors()
    print(f"🏷️ Available sectors: {len(sectors)}")
    for sector in sectors[:5]:
        print(f"   • {sector}")
    
    if summary['total_records'] == 0:
        print(f"\n📥 No data found, populating last 7 days...")
        stats = populate_trends_data(7)
        print(f"✅ Population completed: {stats}")
    else:
        print(f"\n📈 Getting sample trends data...")
        df = get_trends_for_charting(['NIFTY-PHARMA', 'NIFTY-BANK'], 10)
        print(f"✅ Retrieved {len(df)} records")
        if not df.empty:
            print(df.head())