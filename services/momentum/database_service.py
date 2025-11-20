"""
Database Service for Momentum Analysis
=====================================

Provides database operations for momentum analysis including bulk operations
and efficient data retrieval.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from datetime import date
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import text
import uuid

try:
    from services.market_breadth_service import get_engine
except ImportError:
    try:
        from db.connection import ensure_engine
        get_engine = ensure_engine
    except ImportError:
        print("Warning: Could not import database connection. Please ensure database service is available.")
        get_engine = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    """Database service for momentum analysis operations"""
    
    def __init__(self):
        """Initialize database service"""
        self.engine = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection"""
        try:
            if get_engine:
                self.engine = get_engine()
                logger.info("✅ Database connection established for momentum service")
            else:
                logger.error("❌ Database service not available")
                raise Exception("Database connection failed")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database connection: {e}")
            raise
    
    def bulk_upsert_dataframe(
        self, 
        df: pd.DataFrame, 
        table_name: str,
        unique_columns: List[str] = None
    ) -> int:
        """
        Efficiently insert/update DataFrame to database table
        
        Args:
            df: DataFrame to insert
            table_name: Target table name
            unique_columns: Columns that define uniqueness for upsert
            
        Returns:
            Number of rows affected
        """
        if df.empty:
            return 0
        
        if unique_columns is None:
            unique_columns = ['symbol', 'duration_type', 'end_date']
        
        try:
            with self.engine.begin() as conn:
                # Create temporary table
                temp_table = f"temp_{table_name}_{uuid.uuid4().hex[:8]}"
                
                # Create temp table with same structure
                create_temp_sql = f"""
                CREATE TEMPORARY TABLE {temp_table} LIKE {table_name}
                """
                conn.execute(text(create_temp_sql))
                
                # Bulk insert into temp table
                df.to_sql(
                    name=temp_table,
                    con=conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000
                )
                
                # Get all columns for the table
                columns_df = df.columns.tolist()
                columns_str = ', '.join(columns_df)
                
                # Build VALUES clause for ON DUPLICATE KEY UPDATE
                update_clauses = []
                for col in columns_df:
                    if col not in unique_columns:
                        update_clauses.append(f"{col} = VALUES({col})")
                
                update_clause = ', '.join(update_clauses) if update_clauses else f"{columns_df[0]} = VALUES({columns_df[0]})"
                
                # Upsert from temp table to main table
                upsert_sql = f"""
                INSERT INTO {table_name} ({columns_str})
                SELECT {columns_str} FROM {temp_table}
                ON DUPLICATE KEY UPDATE
                {update_clause}
                """
                
                result = conn.execute(text(upsert_sql))
                return result.rowcount
                
        except Exception as e:
            logger.error(f"❌ Error in bulk upsert: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dictionaries
        
        Args:
            query: SQL query string with %s placeholders
            params: Query parameters as tuple
            
        Returns:
            List of result dictionaries
        """
        if params is None:
            params = ()
        
        try:
            with self.engine.begin() as conn:
                # Use raw connection for %s style parameters
                raw_conn = conn.connection
                cursor = raw_conn.cursor()
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                cursor.close()
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return []
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        Execute an UPDATE/INSERT/DELETE query
        
        Args:
            query: SQL query string with %s placeholders
            params: Query parameters as tuple
            
        Returns:
            Number of rows affected
        """
        if params is None:
            params = ()
        
        try:
            with self.engine.begin() as conn:
                # Use raw connection for %s style parameters
                raw_conn = conn.connection
                cursor = raw_conn.cursor()
                cursor.execute(query, params)
                rowcount = cursor.rowcount
                cursor.close()
                
                return rowcount
                
        except Exception as e:
            logger.error(f"❌ Error executing update: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return 0
    
    def create_momentum_schema(self) -> bool:
        """
        Create momentum analysis database schema
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read schema file
            schema_path = os.path.join(os.path.dirname(__file__), 'momentum_schema_simple.sql')
            
            if not os.path.exists(schema_path):
                logger.error(f"❌ Schema file not found: {schema_path}")
                return False
            
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Split into individual statements
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            with self.engine.begin() as conn:
                for statement in statements:
                    if statement.upper().startswith(('CREATE')):
                        try:
                            conn.execute(text(statement))
                            logger.info(f"✅ Executed: {statement[:50]}...")
                        except Exception as e:
                            if 'already exists' in str(e).lower():
                                logger.info(f"ℹ️ Skipped existing: {statement[:50]}...")
                            else:
                                logger.warning(f"⚠️ Error executing: {statement[:50]}... - {e}")
            
            logger.info("✅ Momentum schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating momentum schema: {e}")
            return False
    
    def cleanup_old_data(self, retention_days: int = 90) -> int:
        """
        Clean up old momentum data
        
        Args:
            retention_days: Number of days to retain
            
        Returns:
            Number of rows deleted
        """
        try:
            cutoff_date = date.today() - pd.Timedelta(days=retention_days)
            
            queries = [
                "DELETE FROM momentum_analysis WHERE calculation_date < %s",
                "DELETE FROM momentum_rankings WHERE calculation_date < %s", 
                "DELETE FROM sector_momentum WHERE calculation_date < %s",
                "DELETE FROM momentum_calculation_jobs WHERE calculation_date < %s"
            ]
            
            total_deleted = 0
            
            for query in queries:
                deleted = self.execute_update(query, (cutoff_date,))
                total_deleted += deleted
                logger.info(f"✅ Cleaned up {deleted} rows from {query.split()[2]}")
            
            logger.info(f"✅ Total cleanup: {total_deleted} rows deleted")
            return total_deleted
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old data: {e}")
            return 0
    
    def get_latest_calculation_date(self, duration_type: str = None) -> Optional[date]:
        """
        Get the latest calculation date for momentum data
        
        Args:
            duration_type: Specific duration type (optional)
            
        Returns:
            Latest calculation date or None
        """
        try:
            query = "SELECT MAX(calculation_date) as latest_date FROM momentum_analysis"
            
            if duration_type:
                query += " WHERE duration_type = %s"
                result = self.execute_query(query, (duration_type,))
            else:
                result = self.execute_query(query)
            
            if result and result[0]['latest_date']:
                return result[0]['latest_date']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting latest calculation date: {e}")
            return None
    
    def get_momentum_summary_stats(self, duration_type: str, calculation_date: date = None) -> Dict[str, Any]:
        """
        Get summary statistics for momentum calculations
        
        Args:
            duration_type: Duration type to analyze
            calculation_date: Specific calculation date (default: latest)
            
        Returns:
            Dictionary of summary statistics
        """
        try:
            if calculation_date is None:
                calculation_date = self.get_latest_calculation_date(duration_type)
            
            if calculation_date is None:
                return {}
            
            query = """
            SELECT 
                COUNT(*) as total_stocks,
                AVG(percentage_change) as avg_change,
                STDDEV(percentage_change) as std_change,
                MIN(percentage_change) as min_change,
                MAX(percentage_change) as max_change,
                COUNT(CASE WHEN percentage_change > 0 THEN 1 END) as positive_count,
                COUNT(CASE WHEN percentage_change < 0 THEN 1 END) as negative_count,
                COUNT(CASE WHEN ABS(percentage_change) > 10 THEN 1 END) as high_momentum_count
            FROM momentum_analysis 
            WHERE duration_type = %s AND calculation_date = %s
            """
            
            result = self.execute_query(query, (duration_type, calculation_date))
            
            if result:
                return result[0]
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error getting momentum summary stats: {e}")
            return {}

def main():
    """Test the database service"""
    
    print("🧪 TESTING DATABASE SERVICE")
    print("=" * 40)
    
    db_service = DatabaseService()
    
    # Test schema creation
    print("\n📊 Testing schema creation...")
    success = db_service.create_momentum_schema()
    print(f"Schema creation: {'✅' if success else '❌'}")
    
    # Test basic query
    print("\n🔍 Testing query execution...")
    result = db_service.execute_query("SELECT 1 as test_value")
    print(f"Query test: {'✅' if result and result[0]['test_value'] == 1 else '❌'}")
    
    print(f"\n🏆 DATABASE SERVICE TEST COMPLETE!")

if __name__ == "__main__":
    main()