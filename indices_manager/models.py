"""
Data Models for NSE Indices Management System
============================================

This module contains data classes and models for managing NSE indices and their constituents.
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class IndexCategory(Enum):
    """Index categories"""
    MAIN = "MAIN"
    SECTORAL = "SECTORAL" 
    THEMATIC = "THEMATIC"


class ImportStatus(Enum):
    """Import status for tracking file processing"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class IndexMetadata:
    """Metadata for an NSE index"""
    index_code: str
    index_name: str
    category: IndexCategory
    sector: Optional[str] = None
    description: Optional[str] = None
    id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class IndexData:
    """Daily data for an index"""
    index_id: int
    data_date: date
    open_value: Optional[Decimal] = None
    high_value: Optional[Decimal] = None
    low_value: Optional[Decimal] = None
    close_value: Optional[Decimal] = None
    prev_close: Optional[Decimal] = None
    change_points: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    value_crores: Optional[Decimal] = None
    week52_high: Optional[Decimal] = None
    week52_low: Optional[Decimal] = None
    change_30d_percent: Optional[Decimal] = None
    change_365d_percent: Optional[Decimal] = None
    file_source: Optional[str] = None
    id: Optional[int] = None
    imported_at: Optional[datetime] = None


@dataclass
class ConstituentData:
    """Data for an index constituent (stock)"""
    index_id: int
    symbol: str
    data_date: date
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    prev_close: Optional[Decimal] = None
    ltp: Optional[Decimal] = None
    change_points: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    value_crores: Optional[Decimal] = None
    week52_high: Optional[Decimal] = None
    week52_low: Optional[Decimal] = None
    change_30d_percent: Optional[Decimal] = None
    change_365d_percent: Optional[Decimal] = None
    weight_percent: Optional[Decimal] = None
    is_active: bool = True
    file_source: Optional[str] = None
    id: Optional[int] = None
    imported_at: Optional[datetime] = None


@dataclass
class ImportLog:
    """Log entry for file imports"""
    filename: str
    index_code: Optional[str] = None
    data_date: Optional[date] = None
    file_size: Optional[int] = None
    records_processed: int = 0
    records_imported: int = 0
    status: ImportStatus = ImportStatus.PENDING
    error_message: Optional[str] = None
    file_hash: Optional[str] = None
    id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class IndexSummary:
    """Summary information for an index"""
    index_code: str
    index_name: str
    category: str
    sector: Optional[str]
    latest_date: Optional[date]
    latest_close: Optional[Decimal]
    change_percent: Optional[Decimal]
    constituent_count: int
    is_active: bool


@dataclass
class ConstituentSummary:
    """Summary information for a stock across indices"""
    symbol: str
    latest_date: Optional[date]
    latest_price: Optional[Decimal]
    change_percent: Optional[Decimal]
    volume: Optional[int]
    indices: List[str]  # List of index codes this stock belongs to


class ValidationError(Exception):
    """Custom exception for data validation errors"""
    pass


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass