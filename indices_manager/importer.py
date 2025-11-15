"""
Database Import Module for NSE Indices
=====================================

This module handles importing parsed NSE indices data into the database.
"""

import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
from sqlalchemy import text

from .database import db_manager
from .parser import NSEIndicesParser
from .models import (
    IndexData, ConstituentData, ImportLog, ImportStatus,
    IndexMetadata, IndexCategory, ValidationError, DatabaseError
)


class IndicesImporter:
    """
    Handles importing NSE indices data into database
    """
    
    def __init__(self):
        """Initialize the importer"""
        self.logger = logging.getLogger(__name__)
        self.parser = NSEIndicesParser()
        self.db = db_manager
        
        # Ensure tables exist
        self.db.create_tables_if_not_exist()
    
    def get_or_create_index(self, index_code: str) -> int:
        """
        Get existing index ID or create new index record
        
        Args:
            index_code: Index code (e.g., 'NIFTY-50')
            
        Returns:
            Index ID
        """
        try:
            # Try to get existing index
            existing_id = self.db.get_index_id(index_code)
            if existing_id:
                return existing_id
            
            # Create new index record
            self.logger.info(f"Creating new index record for: {index_code}")
            
            # Map index code to metadata (based on predefined mapping)
            index_name, category, sector = self._get_index_metadata(index_code)
            
            query = text("""
                INSERT INTO nse_indices (index_code, index_name, category, sector)
                VALUES (:index_code, :index_name, :category, :sector)
            """)
            
            index_id = self.db.execute_insert(query, {
                'index_code': index_code,
                'index_name': index_name,
                'category': category,
                'sector': sector
            })
            
            self.logger.info(f"Created index {index_code} with ID: {index_id}")
            return index_id
            
        except Exception as e:
            self.logger.error(f"Failed to get/create index {index_code}: {e}")
            raise DatabaseError(f"Index creation failed: {e}")
    
    def _get_index_metadata(self, index_code: str) -> Tuple[str, str, Optional[str]]:
        """
        Get index metadata based on index code
        
        Args:
            index_code: Index code
            
        Returns:
            Tuple of (name, category, sector)
        """
        # Define metadata mapping
        metadata_map = {
            'NIFTY-50': ('Nifty 50', 'MAIN', 'BROAD_MARKET'),
            'NIFTY-NEXT-50': ('Nifty Next 50', 'MAIN', 'BROAD_MARKET'),
            'NIFTY-MIDCAP-SELECT': ('Nifty Midcap Select', 'MAIN', 'BROAD_MARKET'),
            'NIFTY-BANK': ('Nifty Bank', 'SECTORAL', 'BANKING'),
            'NIFTY-FINANCIAL-SERVICES': ('Nifty Financial Services', 'SECTORAL', 'FINANCIAL_SERVICES'),
            'NIFTY-FINANCIAL-SERVICES-25_50': ('Nifty Financial Services 25/50', 'SECTORAL', 'FINANCIAL_SERVICES'),
            'NIFTY-FINANCIAL-SERVICES-EX-BANK': ('Nifty Financial Services Ex-Bank', 'SECTORAL', 'FINANCIAL_SERVICES'),
            'NIFTY-PRIVATE-BANK': ('Nifty Private Bank', 'SECTORAL', 'BANKING'),
            'NIFTY-PSU-BANK': ('Nifty PSU Bank', 'SECTORAL', 'BANKING'),
            'NIFTY-MIDSMALL-FINANCIAL-SERVICES': ('Nifty MidSmall Financial Services', 'SECTORAL', 'FINANCIAL_SERVICES'),
            'NIFTY-AUTO': ('Nifty Auto', 'SECTORAL', 'AUTOMOBILE'),
            'NIFTY-CHEMICALS': ('Nifty Chemicals', 'SECTORAL', 'CHEMICALS'),
            'NIFTY-CONSUMER-DURABLES': ('Nifty Consumer Durables', 'SECTORAL', 'CONSUMER_DURABLES'),
            'NIFTY-FMCG': ('Nifty FMCG', 'SECTORAL', 'FMCG'),
            'NIFTY-IT': ('Nifty IT', 'SECTORAL', 'INFORMATION_TECHNOLOGY'),
            'NIFTY-MEDIA': ('Nifty Media', 'SECTORAL', 'MEDIA'),
            'NIFTY-METAL': ('Nifty Metal', 'SECTORAL', 'METALS'),
            'NIFTY-OIL-&-GAS': ('Nifty Oil & Gas', 'SECTORAL', 'OIL_GAS'),
            'NIFTY-PHARMA': ('Nifty Pharma', 'SECTORAL', 'PHARMACEUTICALS'),
            'NIFTY-REALTY': ('Nifty Realty', 'SECTORAL', 'REAL_ESTATE'),
            'NIFTY-HEALTHCARE-INDEX': ('Nifty Healthcare Index', 'SECTORAL', 'HEALTHCARE'),
            'NIFTY-MIDSMALL-HEALTHCARE': ('Nifty MidSmall Healthcare', 'SECTORAL', 'HEALTHCARE'),
            'NIFTY500-HEALTHCARE': ('Nifty500 Healthcare', 'SECTORAL', 'HEALTHCARE'),
            'NIFTY-MIDSMALL-IT-&-TELECOM': ('Nifty MidSmall IT & Telecom', 'SECTORAL', 'TECHNOLOGY'),
        }
        
        if index_code in metadata_map:
            return metadata_map[index_code]
        else:
            # Default mapping for unknown indices
            return (index_code.replace('-', ' ').title(), 'SECTORAL', None)
    
    def create_import_log(self, filename: str, index_code: str, 
                         data_date: date, file_size: int, file_hash: str) -> int:
        """
        Create import log entry
        
        Args:
            filename: Name of the file being imported
            index_code: Index code
            data_date: Data date from file
            file_size: File size in bytes
            file_hash: MD5 hash of file
            
        Returns:
            Import log ID
        """
        try:
            query = text("""
                INSERT INTO index_import_log 
                (filename, index_code, data_date, file_size, file_hash, status)
                VALUES (:filename, :index_code, :data_date, :file_size, :file_hash, :status)
            """)
            
            log_id = self.db.execute_insert(query, {
                'filename': filename,
                'index_code': index_code,
                'data_date': data_date,
                'file_size': file_size,
                'file_hash': file_hash,
                'status': ImportStatus.PENDING.value
            })
            
            return log_id
            
        except Exception as e:
            self.logger.error(f"Failed to create import log: {e}")
            raise DatabaseError(f"Import log creation failed: {e}")
    
    def update_import_log(self, log_id: int, status: ImportStatus, 
                         records_processed: int = 0, records_imported: int = 0, 
                         error_message: Optional[str] = None):
        """
        Update import log entry
        
        Args:
            log_id: Import log ID
            status: Import status
            records_processed: Number of records processed
            records_imported: Number of records imported
            error_message: Error message if failed
        """
        try:
            query = text("""
                UPDATE index_import_log 
                SET status = :status, 
                    records_processed = :records_processed,
                    records_imported = :records_imported,
                    error_message = :error_message,
                    completed_at = :completed_at
                WHERE id = :log_id
            """)
            
            completed_at = datetime.now() if status in [ImportStatus.COMPLETED, ImportStatus.FAILED] else None
            
            self.db.execute_query(query, {
                'log_id': log_id,
                'status': status.value,
                'records_processed': records_processed,
                'records_imported': records_imported,
                'error_message': error_message,
                'completed_at': completed_at
            })
            
        except Exception as e:
            self.logger.error(f"Failed to update import log {log_id}: {e}")
    
    def check_duplicate_import(self, file_hash: str) -> bool:
        """
        Check if file has already been imported
        
        Args:
            file_hash: MD5 hash of file
            
        Returns:
            True if file was already imported successfully
        """
        try:
            query = text("""
                SELECT COUNT(*) as count 
                FROM index_import_log 
                WHERE file_hash = :file_hash 
                AND status = :status
            """)
            
            result = self.db.execute_query(query, {
                'file_hash': file_hash,
                'status': ImportStatus.COMPLETED.value
            })
            
            return result[0][0] > 0
            
        except Exception as e:
            self.logger.warning(f"Could not check duplicate import: {e}")
            return False
    
    def import_index_data(self, index_id: int, index_data: IndexData) -> bool:
        """
        Import index data into database
        
        Args:
            index_id: Index ID
            index_data: Index data object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not index_data:
                return True  # No index data to import
            
            # Check if data already exists for this date
            query = text("""
                SELECT COUNT(*) as count 
                FROM nse_index_data 
                WHERE index_id = :index_id AND data_date = :data_date
            """)
            
            result = self.db.execute_query(query, {
                'index_id': index_id,
                'data_date': index_data.data_date
            })
            
            if result[0][0] > 0:
                self.logger.info(f"Index data already exists for {index_data.data_date}")
                return True
            
            # Insert new index data
            insert_query = text("""
                INSERT INTO nse_index_data 
                (index_id, data_date, open_value, high_value, low_value, close_value, 
                 prev_close, change_points, change_percent, volume, value_crores,
                 week52_high, week52_low, change_30d_percent, change_365d_percent, file_source)
                VALUES (:index_id, :data_date, :open_value, :high_value, :low_value, :close_value,
                        :prev_close, :change_points, :change_percent, :volume, :value_crores,
                        :week52_high, :week52_low, :change_30d_percent, :change_365d_percent, :file_source)
            """)
            
            self.db.execute_insert(insert_query, {
                'index_id': index_id,
                'data_date': index_data.data_date,
                'open_value': float(index_data.open_value) if index_data.open_value else None,
                'high_value': float(index_data.high_value) if index_data.high_value else None,
                'low_value': float(index_data.low_value) if index_data.low_value else None,
                'close_value': float(index_data.close_value) if index_data.close_value else None,
                'prev_close': float(index_data.prev_close) if index_data.prev_close else None,
                'change_points': float(index_data.change_points) if index_data.change_points else None,
                'change_percent': float(index_data.change_percent) if index_data.change_percent else None,
                'volume': index_data.volume,
                'value_crores': float(index_data.value_crores) if index_data.value_crores else None,
                'week52_high': float(index_data.week52_high) if index_data.week52_high else None,
                'week52_low': float(index_data.week52_low) if index_data.week52_low else None,
                'change_30d_percent': float(index_data.change_30d_percent) if index_data.change_30d_percent else None,
                'change_365d_percent': float(index_data.change_365d_percent) if index_data.change_365d_percent else None,
                'file_source': index_data.file_source
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import index data: {e}")
            return False
    
    def import_constituents_data(self, index_id: int, constituents: List[ConstituentData]) -> int:
        """
        Import constituents data into database
        
        Args:
            index_id: Index ID
            constituents: List of constituent data objects
            
        Returns:
            Number of records imported
        """
        try:
            if not constituents:
                return 0
            
            data_date = constituents[0].data_date
            
            # Delete existing constituents for this date (replace mode)
            delete_query = text("""
                DELETE FROM nse_index_constituents 
                WHERE index_id = :index_id AND data_date = :data_date
            """)
            
            self.db.execute_query(delete_query, {
                'index_id': index_id,
                'data_date': data_date
            })
            
            # Prepare data for batch insert
            records_data = []
            for constituent in constituents:
                record = {
                    'index_id': index_id,
                    'symbol': constituent.symbol,
                    'data_date': constituent.data_date,
                    'open_price': float(constituent.open_price) if constituent.open_price else None,
                    'high_price': float(constituent.high_price) if constituent.high_price else None,
                    'low_price': float(constituent.low_price) if constituent.low_price else None,
                    'close_price': float(constituent.close_price) if constituent.close_price else None,
                    'prev_close': float(constituent.prev_close) if constituent.prev_close else None,
                    'ltp': float(constituent.ltp) if constituent.ltp else None,
                    'change_points': float(constituent.change_points) if constituent.change_points else None,
                    'change_percent': float(constituent.change_percent) if constituent.change_percent else None,
                    'volume': constituent.volume,
                    'value_crores': float(constituent.value_crores) if constituent.value_crores else None,
                    'week52_high': float(constituent.week52_high) if constituent.week52_high else None,
                    'week52_low': float(constituent.week52_low) if constituent.week52_low else None,
                    'change_30d_percent': float(constituent.change_30d_percent) if constituent.change_30d_percent else None,
                    'change_365d_percent': float(constituent.change_365d_percent) if constituent.change_365d_percent else None,
                    'weight_percent': float(constituent.weight_percent) if constituent.weight_percent else None,
                    'is_active': constituent.is_active,
                    'file_source': constituent.file_source
                }
                records_data.append(record)
            
            # Batch insert
            self.db.execute_batch_insert('nse_index_constituents', records_data)
            
            self.logger.info(f"Imported {len(records_data)} constituents for index {index_id}")
            return len(records_data)
            
        except Exception as e:
            self.logger.error(f"Failed to import constituents data: {e}")
            return 0
    
    def import_csv_file(self, file_path: str, skip_duplicates: bool = True) -> bool:
        """
        Import a single CSV file
        
        Args:
            file_path: Path to CSV file
            skip_duplicates: Whether to skip files already imported
            
        Returns:
            True if successful, False otherwise
        """
        filename = Path(file_path).name
        self.logger.info(f"Starting import of: {filename}")
        
        log_id = None
        
        try:
            # Validate file
            if not self.parser.validate_csv_structure(file_path):
                raise ValidationError(f"Invalid CSV structure: {filename}")
            
            # Calculate file hash and check for duplicates
            file_hash = self.parser.get_file_hash(file_path)
            if skip_duplicates and self.check_duplicate_import(file_hash):
                self.logger.info(f"File already imported, skipping: {filename}")
                return True
            
            # Parse CSV file
            index_data, constituents = self.parser.parse_csv_file(file_path)
            
            # Extract metadata
            index_code, data_date = self.parser.extract_index_info_from_filename(filename)
            file_size = os.path.getsize(file_path)
            
            # Create import log
            log_id = self.create_import_log(filename, index_code, data_date, file_size, file_hash)
            
            # Update log status to processing
            self.update_import_log(log_id, ImportStatus.PROCESSING)
            
            # Get or create index
            index_id = self.get_or_create_index(index_code)
            
            # Import index data
            index_imported = self.import_index_data(index_id, index_data)
            
            # Import constituents data
            constituents_imported = self.import_constituents_data(index_id, constituents)
            
            # Update log status to completed
            self.update_import_log(
                log_id, 
                ImportStatus.COMPLETED,
                records_processed=len(constituents) + (1 if index_data else 0),
                records_imported=constituents_imported + (1 if index_imported else 0)
            )
            
            self.logger.info(f"Successfully imported {filename}: {constituents_imported} constituents")
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to import {filename}: {error_msg}")
            
            if log_id:
                self.update_import_log(log_id, ImportStatus.FAILED, error_message=error_msg)
            
            return False
    
    def import_directory(self, directory_path: str, file_pattern: str = "*.csv", 
                        skip_duplicates: bool = True) -> Dict[str, any]:
        """
        Import all CSV files from a directory
        
        Args:
            directory_path: Path to directory containing CSV files
            file_pattern: File pattern to match (default: "*.csv")
            skip_duplicates: Whether to skip already imported files
            
        Returns:
            Dictionary with import results
        """
        self.logger.info(f"Starting directory import: {directory_path}")
        
        try:
            directory = Path(directory_path)
            if not directory.exists():
                raise ValidationError(f"Directory does not exist: {directory_path}")
            
            csv_files = list(directory.glob(file_pattern))
            if not csv_files:
                self.logger.warning(f"No CSV files found in: {directory_path}")
                return {'success': True, 'files_processed': 0, 'files_imported': 0, 'errors': []}
            
            results = {
                'success': True,
                'files_processed': 0,
                'files_imported': 0,
                'files_skipped': 0,
                'errors': [],
                'imported_files': [],
                'failed_files': []
            }
            
            for csv_file in csv_files:
                results['files_processed'] += 1
                
                try:
                    if self.import_csv_file(str(csv_file), skip_duplicates):
                        results['files_imported'] += 1
                        results['imported_files'].append(csv_file.name)
                    else:
                        results['failed_files'].append(csv_file.name)
                        
                except Exception as e:
                    error_msg = f"Failed to import {csv_file.name}: {e}"
                    results['errors'].append(error_msg)
                    results['failed_files'].append(csv_file.name)
                    self.logger.error(error_msg)
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(csv_files)
            
            self.logger.info(
                f"Directory import completed: {results['files_imported']}/{results['files_processed']} files imported"
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Directory import failed: {e}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}