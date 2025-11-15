"""
CSV Parser for NSE Indices Data
==============================

This module handles parsing of NSE indices CSV files and extracting constituent data.
"""

import os
import re
import hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
from decimal import Decimal, InvalidOperation
import logging

from .models import IndexData, ConstituentData, ValidationError


class NSEIndicesParser:
    """
    Parser for NSE indices CSV files
    """
    
    def __init__(self):
        """Initialize the parser"""
        self.logger = logging.getLogger(__name__)
        
        # Expected CSV columns mapping
        self.column_mapping = {
            'SYMBOL': 'symbol',
            'OPEN': 'open_price',
            'HIGH': 'high_price', 
            'LOW': 'low_price',
            'PREV. CLOSE': 'prev_close',
            'LTP': 'ltp',
            'INDICATIVE CLOSE': 'indicative_close',
            'CHNG': 'change_points',
            '%CHNG': 'change_percent',
            'VOLUME (shares)': 'volume',
            'VALUE  (₹ Crores)': 'value_crores',
            '52W H': 'week52_high',
            '52W L': 'week52_low',
            '30 D   %CHNG': 'change_30d_percent',
            '365 D % CHNG': 'change_365d_percent'
        }
    
    def extract_index_info_from_filename(self, filename: str) -> Tuple[str, date]:
        """
        Extract index code and date from filename
        
        Args:
            filename: CSV filename (e.g., "MW-NIFTY-50-15-Nov-2025.csv")
            
        Returns:
            Tuple of (index_code, data_date)
        """
        try:
            # Remove MW- prefix and .csv suffix
            base_name = filename.replace('MW-', '').replace('.csv', '')
            
            # Extract date part (last part after final dash)
            parts = base_name.split('-')
            if len(parts) < 4:  # Need at least index-name-date-month-year
                raise ValidationError(f"Invalid filename format: {filename}")
            
            # Date is typically in format: DD-Mon-YYYY
            date_parts = parts[-3:]  # Last 3 parts should be date
            date_str = '-'.join(date_parts)
            
            try:
                parsed_date = datetime.strptime(date_str, '%d-%b-%Y').date()
            except ValueError:
                # Try alternative format
                parsed_date = datetime.strptime(date_str, '%d-%B-%Y').date()
            
            # Index code is everything before the date parts
            index_code = '-'.join(parts[:-3])
            
            return index_code, parsed_date
            
        except Exception as e:
            self.logger.error(f"Failed to parse filename {filename}: {e}")
            raise ValidationError(f"Invalid filename format: {filename}")
    
    def clean_csv_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize CSV data
        
        Args:
            df: Raw DataFrame from CSV
            
        Returns:
            Cleaned DataFrame
        """
        try:
            # Clean column names (remove extra spaces and line breaks)
            df.columns = [col.strip().replace('\n', ' ').replace('  ', ' ') for col in df.columns]
            
            # Remove any completely empty rows
            df = df.dropna(how='all')
            
            # Clean string data (remove quotes and extra whitespace)
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip().str.replace('"', '')
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to clean CSV data: {e}")
            raise ValidationError(f"Data cleaning failed: {e}")
    
    def parse_decimal_value(self, value: str, allow_negative: bool = True) -> Optional[Decimal]:
        """
        Parse string value to Decimal, handling various formats
        
        Args:
            value: String value to parse
            allow_negative: Whether negative values are allowed
            
        Returns:
            Decimal value or None if parsing fails
        """
        if pd.isna(value) or str(value).strip() in ['', '-', 'nan', 'NaN', 'None']:
            return None
        
        try:
            # Clean the value
            clean_value = str(value).strip().replace(',', '').replace('₹', '')
            
            # Handle percentage values
            if '%' in clean_value:
                clean_value = clean_value.replace('%', '')
            
            # Convert to Decimal
            decimal_value = Decimal(clean_value)
            
            if not allow_negative and decimal_value < 0:
                return None
                
            return decimal_value
            
        except (InvalidOperation, ValueError):
            return None
    
    def parse_volume(self, value: str) -> Optional[int]:
        """
        Parse volume value to integer
        
        Args:
            value: String value to parse
            
        Returns:
            Integer value or None if parsing fails
        """
        if pd.isna(value) or str(value).strip() in ['', '-', 'nan', 'NaN', 'None']:
            return None
        
        try:
            # Clean the value and remove commas
            clean_value = str(value).strip().replace(',', '')
            return int(float(clean_value))
        except (ValueError, TypeError):
            return None
    
    def parse_csv_file(self, file_path: str) -> Tuple[IndexData, List[ConstituentData]]:
        """
        Parse a single CSV file and extract index and constituent data
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Tuple of (IndexData, List[ConstituentData])
        """
        self.logger.info(f"Parsing CSV file: {file_path}")
        
        try:
            # Extract metadata from filename
            filename = Path(file_path).name
            index_code, data_date = self.extract_index_info_from_filename(filename)
            
            # Read CSV file
            df = pd.read_csv(file_path, encoding='utf-8')
            df = self.clean_csv_data(df)
            
            if df.empty:
                raise ValidationError(f"CSV file is empty: {file_path}")
            
            # Calculate file hash
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            # Parse index data (first row should be index data)
            index_data = None
            constituents = []
            
            for idx, row in df.iterrows():
                symbol = str(row.iloc[0]).strip()
                
                if not symbol or symbol == 'nan':
                    continue
                
                # Create constituent data
                constituent = ConstituentData(
                    index_id=0,  # Will be set during import
                    symbol=symbol,
                    data_date=data_date,
                    open_price=self.parse_decimal_value(row.iloc[1] if len(row) > 1 else None, False),
                    high_price=self.parse_decimal_value(row.iloc[2] if len(row) > 2 else None, False),
                    low_price=self.parse_decimal_value(row.iloc[3] if len(row) > 3 else None, False),
                    prev_close=self.parse_decimal_value(row.iloc[4] if len(row) > 4 else None, False),
                    ltp=self.parse_decimal_value(row.iloc[5] if len(row) > 5 else None, False),
                    change_points=self.parse_decimal_value(row.iloc[7] if len(row) > 7 else None),
                    change_percent=self.parse_decimal_value(row.iloc[8] if len(row) > 8 else None),
                    volume=self.parse_volume(row.iloc[9] if len(row) > 9 else None),
                    value_crores=self.parse_decimal_value(row.iloc[10] if len(row) > 10 else None, False),
                    week52_high=self.parse_decimal_value(row.iloc[11] if len(row) > 11 else None, False),
                    week52_low=self.parse_decimal_value(row.iloc[12] if len(row) > 12 else None, False),
                    change_30d_percent=self.parse_decimal_value(row.iloc[13] if len(row) > 13 else None),
                    change_365d_percent=self.parse_decimal_value(row.iloc[14] if len(row) > 14 else None),
                    file_source=filename
                )
                
                # Set close_price (use LTP or prev_close + change)
                if constituent.ltp:
                    constituent.close_price = constituent.ltp
                elif constituent.prev_close and constituent.change_points:
                    constituent.close_price = constituent.prev_close + constituent.change_points
                
                # If this is the index row (first row with index name), extract index data
                if idx == 0 and symbol.upper().startswith(('NIFTY', index_code.replace('-', ' '))):
                    index_data = IndexData(
                        index_id=0,  # Will be set during import
                        data_date=data_date,
                        open_value=constituent.open_price,
                        high_value=constituent.high_price,
                        low_value=constituent.low_price,
                        close_value=constituent.close_price,
                        prev_close=constituent.prev_close,
                        change_points=constituent.change_points,
                        change_percent=constituent.change_percent,
                        volume=constituent.volume,
                        value_crores=constituent.value_crores,
                        week52_high=constituent.week52_high,
                        week52_low=constituent.week52_low,
                        change_30d_percent=constituent.change_30d_percent,
                        change_365d_percent=constituent.change_365d_percent,
                        file_source=filename
                    )
                else:
                    # Add to constituents list (skip index row)
                    if not symbol.upper().startswith(('NIFTY', index_code.replace('-', ' '))):
                        constituents.append(constituent)
            
            self.logger.info(f"Parsed {len(constituents)} constituents from {filename}")
            
            return index_data, constituents
            
        except Exception as e:
            self.logger.error(f"Failed to parse CSV file {file_path}: {e}")
            raise ValidationError(f"CSV parsing failed: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of file
        
        Args:
            file_path: Path to file
            
        Returns:
            MD5 hash string
        """
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate file hash: {e}")
            return ""
    
    def validate_csv_structure(self, file_path: str) -> bool:
        """
        Validate CSV file structure
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            df = pd.read_csv(file_path, nrows=5)  # Read only first few rows for validation
            
            # Check minimum required columns
            if len(df.columns) < 10:
                self.logger.warning(f"CSV file has insufficient columns: {file_path}")
                return False
            
            # Check if file has data
            if df.empty:
                self.logger.warning(f"CSV file is empty: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"CSV validation failed for {file_path}: {e}")
            return False