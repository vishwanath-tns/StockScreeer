#!/usr/bin/env python3
"""
Simple Direct Import Test
=========================

Test script to debug the import process step by step.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from indices_manager.parser import NSEIndicesParser
from indices_manager.database import db_manager
import reporting_adv_decl as rad


def test_csv_parsing():
    """Test CSV parsing"""
    print("🧪 Testing CSV parsing...")
    
    parser = NSEIndicesParser()
    test_file = "indices/MW-NIFTY-50-15-Nov-2025.csv"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        # Test filename parsing
        index_code, data_date = parser.extract_index_info_from_filename(os.path.basename(test_file))
        print(f"✅ Filename parsing: {index_code}, {data_date}")
        
        # Test CSV validation
        is_valid = parser.validate_csv_structure(test_file)
        print(f"✅ CSV validation: {is_valid}")
        
        if not is_valid:
            print("❌ CSV validation failed")
            return False
        
        # Test CSV parsing
        index_data, constituents = parser.parse_csv_file(test_file)
        
        print(f"✅ Parsed index data: {index_data is not None}")
        print(f"✅ Parsed {len(constituents)} constituents")
        
        if index_data:
            print(f"   Index close: {index_data.close_value}")
            print(f"   Index change: {index_data.change_percent}%")
        
        if constituents and len(constituents) > 0:
            print(f"   First constituent: {constituents[0].symbol} - {constituents[0].close_price}")
        
        return True
        
    except Exception as e:
        print(f"❌ CSV parsing failed: {e}")
        return False


def test_direct_database_insert():
    """Test direct database operations"""
    print("🗃️  Testing direct database operations...")
    
    try:
        # Test database connection
        with db_manager.get_connection() as conn:
            print("✅ Database connection successful")
        
        # Test getting index ID
        index_id = db_manager.get_index_id("NIFTY-50")
        print(f"✅ NIFTY-50 index ID: {index_id}")
        
        if not index_id:
            print("❌ NIFTY-50 index not found in database")
            return False
        
        # Test simple insert to index_data table
        engine = rad.engine()
        with engine.connect() as conn:
            # Insert a test record
            result = conn.execute(rad.text("""
                INSERT INTO nse_index_data 
                (index_id, data_date, open_value, high_value, low_value, close_value,
                 prev_close, change_points, change_percent, volume, value_crores, file_source)
                VALUES (:index_id, :data_date, :open_value, :high_value, :low_value, :close_value,
                        :prev_close, :change_points, :change_percent, :volume, :value_crores, :file_source)
            """), {
                'index_id': index_id,
                'data_date': '2025-11-15',
                'open_value': 24800.50,
                'high_value': 24950.75,
                'low_value': 24750.25,
                'close_value': 24900.30,
                'prev_close': 24800.50,
                'change_points': 99.80,
                'change_percent': 0.40,
                'volume': 1500000000,
                'value_crores': 85000.50,
                'file_source': 'test_file.csv'
            })
            
            conn.commit()
            print(f"✅ Inserted test index data, rows affected: {result.rowcount}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_api_retrieval():
    """Test API data retrieval"""
    print("📊 Testing API data retrieval...")
    
    try:
        from indices_manager.api import indices_api
        
        # Test getting latest data
        latest_data = indices_api.get_latest_index_data('NIFTY-50')
        if latest_data:
            print(f"✅ Retrieved latest NIFTY-50 data: {latest_data['close_value']}")
            return True
        else:
            print("❌ No latest data found")
            return False
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False


def main():
    """Main test function"""
    print("🧪 NSE Indices Import Debug Test")
    print("=" * 50)
    
    tests = [
        ("CSV Parsing", test_csv_parsing),
        ("Database Operations", test_direct_database_insert),
        ("API Retrieval", test_api_retrieval)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
        
        if result:
            print(f"✅ {test_name} test PASSED")
        else:
            print(f"❌ {test_name} test FAILED")
    
    print("\n" + "=" * 50)
    print("📈 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system should be working.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)