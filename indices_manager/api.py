"""
API Interface for NSE Indices Management System
===============================================

This module provides a clean API interface for other components to access
indices and constituents data with methods for querying, filtering, and analytics.
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple, Any
from dataclasses import asdict
import pandas as pd
import logging
from sqlalchemy import text

from .database import db_manager
from .models import (
    IndexMetadata, IndexData, ConstituentData, ImportLog,
    IndexCategory, ImportStatus, ValidationError, DatabaseError
)


class IndicesAPI:
    """
    API interface for indices data access and analysis
    """
    
    def __init__(self):
        """Initialize the API"""
        self.logger = logging.getLogger(__name__)
        self.db = db_manager
    
    # Index Metadata Methods
    
    def get_all_indices(self, category: Optional[str] = None, 
                       sector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all available indices
        
        Args:
            category: Filter by category (MAIN, SECTORAL, THEMATIC)
            sector: Filter by sector
            
        Returns:
            List of index metadata dictionaries
        """
        try:
            where_clauses = []
            params = {}
            
            if category:
                where_clauses.append("category = :category")
                params['category'] = category
            
            if sector:
                where_clauses.append("sector = :sector")
                params['sector'] = sector
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            query = text(f"""
                SELECT id, index_code, index_name, category, sector, 
                       created_at, updated_at
                FROM nse_indices 
                {where_clause}
                ORDER BY index_name
            """)
            
            result = self.db.execute_query(query, params)
            
            indices = []
            for row in result:
                indices.append({
                    'id': row[0],
                    'index_code': row[1],
                    'index_name': row[2],
                    'category': row[3],
                    'sector': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            
            return indices
            
        except Exception as e:
            self.logger.error(f"Failed to get indices list: {e}")
            raise DatabaseError(f"Failed to retrieve indices: {e}")
    
    def get_index_by_code(self, index_code: str) -> Optional[Dict[str, Any]]:
        """
        Get index metadata by index code
        
        Args:
            index_code: Index code (e.g., 'NIFTY-50')
            
        Returns:
            Index metadata dictionary or None
        """
        try:
            query = text("""
                SELECT id, index_code, index_name, category, sector, 
                       created_at, updated_at
                FROM nse_indices 
                WHERE index_code = :index_code
            """)
            
            result = self.db.execute_query(query, {'index_code': index_code})
            
            if result:
                row = result[0]
                return {
                    'id': row[0],
                    'index_code': row[1],
                    'index_name': row[2],
                    'category': row[3],
                    'sector': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get index by code {index_code}: {e}")
            raise DatabaseError(f"Failed to retrieve index: {e}")
    
    def get_sectoral_indices(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get indices grouped by sector
        
        Returns:
            Dictionary with sectors as keys and lists of indices as values
        """
        try:
            indices = self.get_all_indices(category='SECTORAL')
            
            sectoral_groups = {}
            for index in indices:
                sector = index.get('sector', 'OTHERS')
                if sector not in sectoral_groups:
                    sectoral_groups[sector] = []
                sectoral_groups[sector].append(index)
            
            return sectoral_groups
            
        except Exception as e:
            self.logger.error(f"Failed to get sectoral indices: {e}")
            raise DatabaseError(f"Failed to retrieve sectoral indices: {e}")
    
    # Index Data Methods
    
    def get_index_data(self, index_code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None, 
                      limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get historical index data
        
        Args:
            index_code: Index code
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum number of records (optional)
            
        Returns:
            DataFrame with index data
        """
        try:
            where_clauses = ["i.index_code = :index_code"]
            params = {'index_code': index_code}
            
            if start_date:
                where_clauses.append("d.data_date >= :start_date")
                params['start_date'] = start_date
            
            if end_date:
                where_clauses.append("d.data_date <= :end_date")
                params['end_date'] = end_date
            
            where_clause = " AND ".join(where_clauses)
            limit_clause = ""
            if limit:
                limit_clause = f"LIMIT {limit}"
            
            query = text(f"""
                SELECT d.data_date, d.open_value, d.high_value, d.low_value, d.close_value,
                       d.prev_close, d.change_points, d.change_percent, d.volume, d.value_crores,
                       d.week52_high, d.week52_low, d.change_30d_percent, d.change_365d_percent,
                       i.index_name, i.category, i.sector
                FROM nse_index_data d
                JOIN nse_indices i ON d.index_id = i.id
                WHERE {where_clause}
                ORDER BY d.data_date DESC
                {limit_clause}
            """)
            
            return self.db.execute_query_df(query, params)
            
        except Exception as e:
            self.logger.error(f"Failed to get index data for {index_code}: {e}")
            raise DatabaseError(f"Failed to retrieve index data: {e}")
    
    def get_latest_index_data(self, index_code: str) -> Optional[Dict[str, Any]]:
        """
        Get latest index data for a specific index
        
        Args:
            index_code: Index code
            
        Returns:
            Dictionary with latest index data or None
        """
        try:
            df = self.get_index_data(index_code, limit=1)
            if not df.empty:
                return df.iloc[0].to_dict()
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get latest data for {index_code}: {e}")
            raise DatabaseError(f"Failed to retrieve latest index data: {e}")
    
    def get_index_performance(self, index_code: str, 
                            periods: List[int] = [1, 5, 30, 90, 365]) -> Dict[str, float]:
        """
        Get index performance over different periods
        
        Args:
            index_code: Index code
            periods: List of periods in days
            
        Returns:
            Dictionary with period performance percentages
        """
        try:
            query = text("""
                SELECT data_date, close_value
                FROM nse_index_data d
                JOIN nse_indices i ON d.index_id = i.id
                WHERE i.index_code = :index_code
                ORDER BY data_date DESC
                LIMIT 400
            """)
            
            df = self.db.execute_query_df(query, {'index_code': index_code})
            
            if df.empty:
                return {}
            
            df['data_date'] = pd.to_datetime(df['data_date'])
            df = df.sort_values('data_date')
            
            performance = {}
            latest_close = df['close_value'].iloc[-1]
            
            for period in periods:
                try:
                    if len(df) > period:
                        period_close = df['close_value'].iloc[-(period + 1)]
                        if period_close and period_close != 0:
                            performance[f'{period}d'] = ((latest_close - period_close) / period_close) * 100
                except (IndexError, ZeroDivisionError):
                    performance[f'{period}d'] = None
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Failed to calculate performance for {index_code}: {e}")
            return {}
    
    # Constituents Methods
    
    def get_index_constituents(self, index_code: str, 
                             data_date: Optional[date] = None,
                             active_only: bool = True) -> pd.DataFrame:
        """
        Get index constituents for a specific date
        
        Args:
            index_code: Index code
            data_date: Data date (latest if not specified)
            active_only: Whether to return only active constituents
            
        Returns:
            DataFrame with constituent data
        """
        try:
            where_clauses = ["i.index_code = :index_code"]
            params = {'index_code': index_code}
            
            if data_date:
                where_clauses.append("c.data_date = :data_date")
                params['data_date'] = data_date
            else:
                # Get latest available date
                where_clauses.append("""
                    c.data_date = (
                        SELECT MAX(c2.data_date) 
                        FROM nse_index_constituents c2
                        JOIN nse_indices i2 ON c2.index_id = i2.id
                        WHERE i2.index_code = :index_code
                    )
                """)
            
            if active_only:
                where_clauses.append("c.is_active = 1")
            
            where_clause = " AND ".join(where_clauses)
            
            query = text(f"""
                SELECT c.symbol, c.data_date, c.open_price, c.high_price, c.low_price,
                       c.close_price, c.prev_close, c.ltp, c.change_points, c.change_percent,
                       c.volume, c.value_crores, c.week52_high, c.week52_low,
                       c.change_30d_percent, c.change_365d_percent, c.weight_percent,
                       c.is_active, i.index_name
                FROM nse_index_constituents c
                JOIN nse_indices i ON c.index_id = i.id
                WHERE {where_clause}
                ORDER BY c.weight_percent DESC, c.symbol
            """)
            
            return self.db.execute_query_df(query, params)
            
        except Exception as e:
            self.logger.error(f"Failed to get constituents for {index_code}: {e}")
            raise DatabaseError(f"Failed to retrieve constituents: {e}")
    
    def get_constituent_history(self, symbol: str, index_code: str,
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> pd.DataFrame:
        """
        Get historical data for a specific constituent
        
        Args:
            symbol: Stock symbol
            index_code: Index code
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            DataFrame with constituent historical data
        """
        try:
            where_clauses = ["i.index_code = :index_code", "c.symbol = :symbol"]
            params = {'index_code': index_code, 'symbol': symbol}
            
            if start_date:
                where_clauses.append("c.data_date >= :start_date")
                params['start_date'] = start_date
            
            if end_date:
                where_clauses.append("c.data_date <= :end_date")
                params['end_date'] = end_date
            
            where_clause = " AND ".join(where_clauses)
            
            query = text(f"""
                SELECT c.data_date, c.open_price, c.high_price, c.low_price,
                       c.close_price, c.prev_close, c.change_points, c.change_percent,
                       c.volume, c.value_crores, c.weight_percent, c.is_active,
                       i.index_name
                FROM nse_index_constituents c
                JOIN nse_indices i ON c.index_id = i.id
                WHERE {where_clause}
                ORDER BY c.data_date DESC
            """)
            
            return self.db.execute_query_df(query, params)
            
        except Exception as e:
            self.logger.error(f"Failed to get history for {symbol} in {index_code}: {e}")
            raise DatabaseError(f"Failed to retrieve constituent history: {e}")
    
    def get_top_performers(self, index_code: str, data_date: Optional[date] = None,
                          by: str = 'change_percent', top_n: int = 10,
                          ascending: bool = False) -> pd.DataFrame:
        """
        Get top performing constituents for an index
        
        Args:
            index_code: Index code
            data_date: Data date (latest if not specified)
            by: Sort column ('change_percent', 'volume', 'value_crores')
            top_n: Number of top performers to return
            ascending: Sort order (False for top gainers, True for top losers)
            
        Returns:
            DataFrame with top performers
        """
        try:
            df = self.get_index_constituents(index_code, data_date, active_only=True)
            
            if df.empty:
                return df
            
            # Sort by the specified column
            if by in df.columns:
                df = df.sort_values(by, ascending=ascending)
                return df.head(top_n)
            else:
                raise ValidationError(f"Invalid sort column: {by}")
            
        except Exception as e:
            self.logger.error(f"Failed to get top performers for {index_code}: {e}")
            raise DatabaseError(f"Failed to retrieve top performers: {e}")
    
    # Analytics Methods
    
    def get_sector_performance(self, data_date: Optional[date] = None) -> pd.DataFrame:
        """
        Get performance summary by sector
        
        Args:
            data_date: Data date (latest if not specified)
            
        Returns:
            DataFrame with sector performance summary
        """
        try:
            date_clause = ""
            params = {}
            
            if data_date:
                date_clause = "AND d.data_date = :data_date"
                params['data_date'] = data_date
            else:
                date_clause = """
                AND d.data_date = (
                    SELECT MAX(data_date) FROM nse_index_data
                )
                """
            
            query = text(f"""
                SELECT i.sector, 
                       COUNT(*) as index_count,
                       AVG(d.change_percent) as avg_change_percent,
                       SUM(d.volume) as total_volume,
                       SUM(d.value_crores) as total_value_crores
                FROM nse_indices i
                JOIN nse_index_data d ON i.id = d.index_id
                WHERE i.category = 'SECTORAL' 
                AND i.sector IS NOT NULL
                {date_clause}
                GROUP BY i.sector
                ORDER BY avg_change_percent DESC
            """)
            
            return self.db.execute_query_df(query, params)
            
        except Exception as e:
            self.logger.error(f"Failed to get sector performance: {e}")
            raise DatabaseError(f"Failed to retrieve sector performance: {e}")
    
    def get_market_breadth(self, index_code: str = 'NIFTY-50', 
                          data_date: Optional[date] = None) -> Dict[str, int]:
        """
        Get market breadth (advancing vs declining stocks)
        
        Args:
            index_code: Index code for breadth calculation
            data_date: Data date (latest if not specified)
            
        Returns:
            Dictionary with advancing, declining, and unchanged counts
        """
        try:
            df = self.get_index_constituents(index_code, data_date, active_only=True)
            
            if df.empty:
                return {'advancing': 0, 'declining': 0, 'unchanged': 0}
            
            advancing = len(df[df['change_percent'] > 0])
            declining = len(df[df['change_percent'] < 0])
            unchanged = len(df[df['change_percent'] == 0])
            
            return {
                'advancing': advancing,
                'declining': declining,
                'unchanged': unchanged,
                'total': len(df),
                'advance_decline_ratio': advancing / declining if declining > 0 else float('inf')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate market breadth: {e}")
            return {'advancing': 0, 'declining': 0, 'unchanged': 0}
    
    # Import Status Methods
    
    def get_import_status(self, days: int = 30) -> pd.DataFrame:
        """
        Get import status for recent imports
        
        Args:
            days: Number of days to look back
            
        Returns:
            DataFrame with import status
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            query = text("""
                SELECT filename, index_code, data_date, status, 
                       records_processed, records_imported, error_message,
                       created_at, completed_at
                FROM index_import_log
                WHERE created_at >= :cutoff_date
                ORDER BY created_at DESC
            """)
            
            return self.db.execute_query_df(query, {'cutoff_date': cutoff_date})
            
        except Exception as e:
            self.logger.error(f"Failed to get import status: {e}")
            raise DatabaseError(f"Failed to retrieve import status: {e}")
    
    def get_data_availability(self) -> pd.DataFrame:
        """
        Get data availability summary by index
        
        Returns:
            DataFrame with data availability statistics
        """
        try:
            query = text("""
                SELECT i.index_code, i.index_name, i.category, i.sector,
                       COUNT(d.data_date) as data_points,
                       MIN(d.data_date) as earliest_date,
                       MAX(d.data_date) as latest_date,
                       DATEDIFF(MAX(d.data_date), MIN(d.data_date)) as date_range_days
                FROM nse_indices i
                LEFT JOIN nse_index_data d ON i.id = d.index_id
                GROUP BY i.id, i.index_code, i.index_name, i.category, i.sector
                ORDER BY data_points DESC, i.index_name
            """)
            
            return self.db.execute_query_df(query)
            
        except Exception as e:
            self.logger.error(f"Failed to get data availability: {e}")
            raise DatabaseError(f"Failed to retrieve data availability: {e}")


# Global API instance
indices_api = IndicesAPI()