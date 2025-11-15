"""
NSE Indices Management System
============================

A modular system for managing NSE indices data with database storage,
CSV parsing, and API access.

Components:
- models: Data models and validation
- database: Database connection and utilities
- parser: CSV file parsing and validation
- importer: Data import functionality
- api: API interface for data access

Usage:
    from indices_manager.api import indices_api
    from indices_manager.importer import IndicesImporter
    
    # Get all indices
    indices = indices_api.get_all_indices()
    
    # Import CSV file
    importer = IndicesImporter()
    success = importer.import_csv_file("path/to/file.csv")
"""

__version__ = "1.0.0"
__author__ = "Stock Screener Project"

# Import main classes for convenience
from .api import indices_api, IndicesAPI
from .importer import IndicesImporter
from .database import db_manager, DatabaseManager
from .parser import NSEIndicesParser
from .models import (
    IndexMetadata, IndexData, ConstituentData, ImportLog,
    IndexCategory, ImportStatus, ValidationError, DatabaseError
)

__all__ = [
    'indices_api',
    'IndicesAPI',
    'IndicesImporter', 
    'db_manager',
    'DatabaseManager',
    'NSEIndicesParser',
    'IndexMetadata',
    'IndexData',
    'ConstituentData',
    'ImportLog',
    'IndexCategory',
    'ImportStatus',
    'ValidationError',
    'DatabaseError',
]