#!/usr/bin/env python3
"""
Integration Test Script for NSE Indices Management System
=========================================================

This script validates the complete system: database creation, CSV parsing,
import functionality, and API access.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime, timedelta
import logging
import traceback

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from indices_manager.database import db_manager
from indices_manager.parser import NSEIndicesParser
from indices_manager.importer import IndicesImporter
from indices_manager.api import indices_api
from indices_manager.models import *


class TestResults:
    """Track test results"""
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
    
    def add_test(self, test_name: str, passed: bool, error: str = None):
        """Add test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}")
        else:
            self.tests_failed += 1
            self.failures.append((test_name, error))
            print(f"❌ {test_name}: {error}")
    
    def summary(self):
        """Print test summary"""
        print("\\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Tests run: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        
        if self.failures:
            print("\\n❌ FAILURES:")
            for test_name, error in self.failures:
                print(f"  - {test_name}: {error}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\\nSuccess rate: {success_rate:.1f}%")
        
        return self.tests_failed == 0


def setup_logging():
    """Set up logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_csv_file(temp_dir: Path, filename: str) -> str:
    """Create a sample CSV file for testing"""
    file_path = temp_dir / filename
    
    # Sample CSV content based on actual NSE format
    csv_content = '''Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change (%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield,52 week high,52 week low,Change (30 Days),Change (365 Days)
NIFTY 50,15-Nov-2025,24800.50,24950.75,24750.25,24900.30,99.80,0.40,1500000000,85000.50,22.50,3.20,1.25,25000.00,22800.00,5.20,12.50

Symbol,Series,Open Price,High Price,Low Price,LTP,Change,% Change,Volume,Value (Rs. Cr.),52 Week High,52 Week Low,Change (30 Days),Change (365 Days),Weightage
RELIANCE,EQ,2650.00,2680.50,2640.00,2675.25,25.25,0.95,12500000,3342.50,2850.00,2400.00,8.50,15.25,8.50
TCS,EQ,3950.00,3980.00,3930.00,3965.75,15.75,0.40,8750000,3471.03,4200.00,3600.00,4.20,10.15,7.25
HDFCBANK,EQ,1650.00,1670.25,1645.50,1665.80,15.80,0.96,15600000,2599.25,1750.00,1500.00,6.75,11.20,6.75
INFY,EQ,1850.00,1865.50,1840.00,1860.25,10.25,0.55,9850000,1832.35,1950.00,1700.00,3.80,9.50,5.25
ITC,EQ,455.00,460.25,452.50,458.75,3.75,0.82,22500000,1032.19,480.00,420.00,2.15,8.90,4.50
'''
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    return str(file_path)


def test_database_connection(results: TestResults):
    """Test database connection"""
    try:
        # Test connection
        with db_manager.get_connection() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                results.add_test("Database Connection", True)
            else:
                results.add_test("Database Connection", False, "Invalid query result")
    except Exception as e:
        results.add_test("Database Connection", False, str(e))


def test_table_creation(results: TestResults):
    """Test database table creation"""
    try:
        # Create tables
        db_manager.create_tables_if_not_exist()
        
        # Verify tables exist
        tables = ['nse_indices', 'nse_index_data', 'nse_index_constituents', 'index_import_log']
        
        for table in tables:
            if db_manager.table_exists(table):
                results.add_test(f"Table Creation - {table}", True)
            else:
                results.add_test(f"Table Creation - {table}", False, "Table does not exist")
                
    except Exception as e:
        results.add_test("Table Creation", False, str(e))


def test_csv_parser(results: TestResults, sample_file: str):
    """Test CSV parsing functionality"""
    try:
        parser = NSEIndicesParser()
        
        # Test filename parsing
        try:
            index_code, data_date = parser.extract_index_info_from_filename("MW-NIFTY-50-15-Nov-2025.csv")
            if index_code == "NIFTY-50" and data_date == date(2025, 11, 15):
                results.add_test("CSV Parser - Filename Parsing", True)
            else:
                results.add_test("CSV Parser - Filename Parsing", False, f"Unexpected result: {index_code}, {data_date}")
        except Exception as e:
            results.add_test("CSV Parser - Filename Parsing", False, str(e))
        
        # Test CSV validation
        try:
            is_valid = parser.validate_csv_structure(sample_file)
            results.add_test("CSV Parser - Structure Validation", is_valid, "Invalid CSV structure" if not is_valid else None)
        except Exception as e:
            results.add_test("CSV Parser - Structure Validation", False, str(e))
        
        # Test CSV parsing
        try:
            index_data, constituents = parser.parse_csv_file(sample_file)
            
            if index_data:
                results.add_test("CSV Parser - Index Data Parsing", True)
            else:
                results.add_test("CSV Parser - Index Data Parsing", False, "No index data parsed")
            
            if constituents and len(constituents) >= 5:
                results.add_test("CSV Parser - Constituents Parsing", True)
            else:
                results.add_test("CSV Parser - Constituents Parsing", False, f"Expected >= 5 constituents, got {len(constituents) if constituents else 0}")
                
        except Exception as e:
            results.add_test("CSV Parser - Data Parsing", False, str(e))
            
    except Exception as e:
        results.add_test("CSV Parser", False, str(e))


def test_import_functionality(results: TestResults, sample_file: str):
    """Test import functionality"""
    try:
        importer = IndicesImporter()
        
        # Test single file import
        try:
            success = importer.import_csv_file(sample_file)
            results.add_test("Importer - Single File Import", success, "Import failed" if not success else None)
        except Exception as e:
            results.add_test("Importer - Single File Import", False, str(e))
        
        # Test duplicate detection
        try:
            file_hash = importer.parser.get_file_hash(sample_file)
            is_duplicate = importer.check_duplicate_import(file_hash)
            results.add_test("Importer - Duplicate Detection", is_duplicate, "Duplicate not detected" if not is_duplicate else None)
        except Exception as e:
            results.add_test("Importer - Duplicate Detection", False, str(e))
            
    except Exception as e:
        results.add_test("Importer", False, str(e))


def test_api_functionality(results: TestResults):
    """Test API functionality"""
    try:
        # Test get all indices
        try:
            indices = indices_api.get_all_indices()
            if isinstance(indices, list):
                results.add_test("API - Get All Indices", True)
            else:
                results.add_test("API - Get All Indices", False, "Expected list result")
        except Exception as e:
            results.add_test("API - Get All Indices", False, str(e))
        
        # Test get index by code
        try:
            index = indices_api.get_index_by_code("NIFTY-50")
            if index and index.get('index_code') == "NIFTY-50":
                results.add_test("API - Get Index by Code", True)
            else:
                results.add_test("API - Get Index by Code", False, "Index not found or incorrect data")
        except Exception as e:
            results.add_test("API - Get Index by Code", False, str(e))
        
        # Test get index data
        try:
            df = indices_api.get_index_data("NIFTY-50", limit=5)
            if hasattr(df, 'empty') and not df.empty:
                results.add_test("API - Get Index Data", True)
            else:
                results.add_test("API - Get Index Data", False, "No data returned")
        except Exception as e:
            results.add_test("API - Get Index Data", False, str(e))
        
        # Test get constituents
        try:
            df = indices_api.get_index_constituents("NIFTY-50")
            if hasattr(df, 'empty'):
                results.add_test("API - Get Constituents", True)
            else:
                results.add_test("API - Get Constituents", False, "Invalid result type")
        except Exception as e:
            results.add_test("API - Get Constituents", False, str(e))
        
        # Test import status
        try:
            df = indices_api.get_import_status(days=7)
            if hasattr(df, 'empty'):
                results.add_test("API - Get Import Status", True)
            else:
                results.add_test("API - Get Import Status", False, "Invalid result type")
        except Exception as e:
            results.add_test("API - Get Import Status", False, str(e))
        
        # Test data availability
        try:
            df = indices_api.get_data_availability()
            if hasattr(df, 'empty'):
                results.add_test("API - Get Data Availability", True)
            else:
                results.add_test("API - Get Data Availability", False, "Invalid result type")
        except Exception as e:
            results.add_test("API - Get Data Availability", False, str(e))
            
    except Exception as e:
        results.add_test("API", False, str(e))


def test_data_models(results: TestResults):
    """Test data models"""
    try:
        # Test IndexMetadata creation
        try:
            metadata = IndexMetadata(
                id=1,
                index_code="TEST-INDEX",
                index_name="Test Index",
                category=IndexCategory.MAIN,
                sector=None
            )
            results.add_test("Data Models - IndexMetadata", True)
        except Exception as e:
            results.add_test("Data Models - IndexMetadata", False, str(e))
        
        # Test IndexData creation
        try:
            index_data = IndexData(
                data_date=date.today(),
                open_value=25000.0,
                high_value=25100.0,
                low_value=24900.0,
                close_value=25050.0,
                prev_close=25000.0,
                change_points=50.0,
                change_percent=0.2,
                volume=1000000,
                value_crores=5000.0,
                file_source="test.csv"
            )
            results.add_test("Data Models - IndexData", True)
        except Exception as e:
            results.add_test("Data Models - IndexData", False, str(e))
        
        # Test ConstituentData creation
        try:
            constituent = ConstituentData(
                symbol="TESTSTOCK",
                data_date=date.today(),
                open_price=1000.0,
                high_price=1050.0,
                low_price=990.0,
                close_price=1025.0,
                prev_close=1000.0,
                ltp=1025.0,
                change_points=25.0,
                change_percent=2.5,
                volume=500000,
                value_crores=51.25,
                weight_percent=2.5,
                is_active=True,
                file_source="test.csv"
            )
            results.add_test("Data Models - ConstituentData", True)
        except Exception as e:
            results.add_test("Data Models - ConstituentData", False, str(e))
            
    except Exception as e:
        results.add_test("Data Models", False, str(e))


def main():
    """Main test function"""
    print("🧪 NSE Indices Management System - Integration Tests")
    print("="*60)
    
    setup_logging()
    results = TestResults()
    
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Create sample CSV file
            sample_file = create_sample_csv_file(temp_path, "MW-NIFTY-50-15-Nov-2025.csv")
            
            print("\\n📋 Running tests...")
            print("-" * 40)
            
            # Run tests
            test_data_models(results)
            test_database_connection(results)
            test_table_creation(results)
            test_csv_parser(results, sample_file)
            test_import_functionality(results, sample_file)
            test_api_functionality(results)
            
            # Print summary
            success = results.summary()
            
            if success:
                print("\\n🎉 All tests passed! The system is ready for use.")
                print("\\n📝 Next steps:")
                print("  1. Check indices/ folder for CSV files to import")
                print("  2. Run: python indices_cli.py import dir indices/")
                print("  3. List indices: python indices_cli.py list indices")
                print("  4. Show data: python indices_cli.py show NIFTY-50")
            else:
                print("\\n⚠️  Some tests failed. Please check the configuration and try again.")
                
            return 0 if success else 1
            
        except Exception as e:
            print(f"\\n💥 Test execution failed: {e}")
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())