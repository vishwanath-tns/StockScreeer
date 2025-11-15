"""
Database utilities for NSE Indices Management System
===================================================

This module provides database connection and utility functions for the indices management system.
"""

import os
import sys
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
import logging

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import reporting_adv_decl as rad
from sqlalchemy import create_engine, text, Engine, Connection
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd

from .models import DatabaseError


class DatabaseManager:
    """
    Database manager for NSE indices data
    """
    
    def __init__(self):
        """Initialize database manager"""
        self._engine: Optional[Engine] = None
        self.logger = logging.getLogger(__name__)
    
    @property
    def engine(self) -> Engine:
        """Get database engine, create if needed"""
        if self._engine is None:
            try:
                self._engine = rad.engine()
                self.logger.info("Database connection established successfully")
            except Exception as e:
                self.logger.error(f"Failed to create database engine: {e}")
                raise DatabaseError(f"Failed to connect to database: {e}")
        return self._engine
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            conn = self.engine.connect()
            yield conn
        except SQLAlchemyError as e:
            self.logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: Union[str, text], params: Optional[Dict] = None) -> Any:
        """
        Execute a query and return results
        
        Args:
            query: SQL query string or SQLAlchemy text object
            params: Query parameters
            
        Returns:
            Query results
        """
        try:
            with self.get_connection() as conn:
                if isinstance(query, str):
                    query = text(query)
                result = conn.execute(query, params or {})
                return result.fetchall()
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def execute_query_df(self, query: Union[str, text], params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Execute query and return results as pandas DataFrame
        
        Args:
            query: SQL query string or SQLAlchemy text object
            params: Query parameters
            
        Returns:
            DataFrame with query results
        """
        try:
            with self.get_connection() as conn:
                if isinstance(query, str):
                    query = text(query)
                return pd.read_sql(query, conn, params=params or {})
        except Exception as e:
            self.logger.error(f"DataFrame query failed: {e}")
            raise DatabaseError(f"DataFrame query failed: {e}")
    
    def execute_insert(self, query: Union[str, text], params: Optional[Dict] = None) -> int:
        """
        Execute insert query and return last inserted ID
        
        Args:
            query: SQL insert statement
            params: Query parameters
            
        Returns:
            Last inserted row ID
        """
        try:
            with self.get_connection() as conn:
                if isinstance(query, str):
                    query = text(query)
                result = conn.execute(query, params or {})
                conn.commit()
                return result.lastrowid
        except Exception as e:
            self.logger.error(f"Insert operation failed: {e}")
            raise DatabaseError(f"Insert failed: {e}")
    
    def execute_batch_insert(self, table_name: str, data: List[Dict]) -> int:
        """
        Execute batch insert using pandas to_sql
        
        Args:
            table_name: Target table name
            data: List of dictionaries with data to insert
            
        Returns:
            Number of rows inserted
        """
        if not data:
            return 0
            
        try:
            df = pd.DataFrame(data)
            with self.get_connection() as conn:
                rows_inserted = df.to_sql(
                    name=table_name,
                    con=conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000
                )
                conn.commit()
                return len(data)
        except Exception as e:
            self.logger.error(f"Batch insert failed: {e}")
            raise DatabaseError(f"Batch insert failed: {e}")
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            query = text("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = :table_name
            """)
            result = self.execute_query(query, {"table_name": table_name})
            return result[0][0] > 0
        except Exception as e:
            self.logger.warning(f"Could not check table existence: {e}")
            return False
    
    def create_tables_if_not_exist(self):
        """
        Create the indices tables if they don't exist
        """
        try:
            # Check if main table exists
            if not self.table_exists('nse_indices'):
                self.logger.info("Creating indices tables...")
                
                # Read and execute the SQL schema file
                schema_file = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    'sql', 
                    'create_indices_tables.sql'
                )
                
                if os.path.exists(schema_file):
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # Split and execute each statement
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                    
                    with self.get_connection() as conn:
                        for stmt in statements:
                            if stmt:
                                conn.execute(text(stmt))
                        conn.commit()
                    
                    self.logger.info("Indices tables created successfully")
                else:
                    self.logger.warning(f"Schema file not found: {schema_file}")
            else:
                self.logger.info("Indices tables already exist")
                
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
            raise DatabaseError(f"Table creation failed: {e}")
    
    def get_index_id(self, index_code: str) -> Optional[int]:
        """
        Get index ID by index code
        
        Args:
            index_code: Index code (e.g., 'NIFTY-50')
            
        Returns:
            Index ID if found, None otherwise
        """
        try:
            query = text("SELECT id FROM nse_indices WHERE index_code = :index_code")
            result = self.execute_query(query, {"index_code": index_code})
            return result[0][0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get index ID for {index_code}: {e}")
            return None
    
    def close(self):
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None


# Global database manager instance
db_manager = DatabaseManager()