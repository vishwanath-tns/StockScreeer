"""
Debug Momentum Storage Issues
============================

This script will test the database storage mechanism directly to identify
why momentum calculations aren't persisting to the database.
"""

import sys
import os
from datetime import datetime, date
import pandas as pd

sys.path.append('.')

from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.momentum.database_service import DatabaseService
from services.market_breadth_service import get_engine

def debug_storage_issues():
    """Debug why momentum data isn't being stored"""
    
    print("MOMENTUM DATABASE STORAGE DEBUG")
    print("=" * 40)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Test 1: Check database connectivity
    print("1. TESTING DATABASE CONNECTIVITY")
    print("-" * 30)
    
    try:
        engine = get_engine()
        db_service = DatabaseService()
        
        with engine.connect() as conn:
            # Check if table exists
            check_table_query = """
            SHOW TABLES LIKE 'momentum_analysis'
            """
            result = conn.execute(check_table_query)
            table_exists = result.fetchone() is not None
            print(f"✅ Table 'momentum_analysis' exists: {table_exists}")
            
            if table_exists:
                # Check table structure
                desc_query = "DESCRIBE momentum_analysis"
                desc_result = conn.execute(desc_query)
                columns = desc_result.fetchall()
                print(f"✅ Table has {len(columns)} columns")
                
                # Check current data
                count_query = "SELECT COUNT(*) as count FROM momentum_analysis"
                count_result = conn.execute(count_query)
                current_count = count_result.fetchone()[0]
                print(f"✅ Current records in table: {current_count}")
        
        print("")
        
    except Exception as e:
        print(f"❌ Database connectivity error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Test single stock momentum calculation and storage
    print("2. TESTING SINGLE STOCK CALCULATION")
    print("-" * 35)
    
    test_symbol = "TCS"  # Use a known working symbol
    test_duration = MomentumDuration.ONE_WEEK
    
    try:
        calculator = MomentumCalculator()
        
        # Calculate momentum for single stock
        print(f"Calculating {test_duration.value} momentum for {test_symbol}...")
        results = calculator.calculate_momentum_batch([test_symbol], [test_duration])
        
        if results and len(results) > 0:
            result = results[0]
            print(f"✅ Calculation successful:")
            print(f"   Symbol: {result.symbol}")
            print(f"   Duration: {result.duration_type}")
            print(f"   Percentage Change: {result.percentage_change:.2f}%")
            print(f"   End Date: {result.end_date}")
            
            # Check if it was stored
            engine = get_engine()
            with engine.connect() as conn:
                check_query = """
                SELECT COUNT(*) as count 
                FROM momentum_analysis 
                WHERE symbol = %s AND duration_type = %s 
                AND DATE(end_date) = %s
                """
                
                params = (result.symbol, result.duration_type, result.end_date.strftime('%Y-%m-%d'))
                check_result = conn.execute(check_query, params)
                stored_count = check_result.fetchone()[0]
                print(f"✅ Records found in database: {stored_count}")
                
                if stored_count == 0:
                    print("⚠️  Calculation successful but not found in database!")
                    
                    # Try to manually verify the storage
                    print("\nChecking recent records...")
                    recent_query = """
                    SELECT symbol, duration_type, end_date, calculation_date
                    FROM momentum_analysis
                    WHERE symbol = %s
                    ORDER BY calculation_date DESC
                    LIMIT 5
                    """
                    recent_result = conn.execute(recent_query, (result.symbol,))
                    recent_records = recent_result.fetchall()
                    
                    if recent_records:
                        print("Recent records for this symbol:")
                        for record in recent_records:
                            print(f"  {record[0]} | {record[1]} | {record[2]} | {record[3]}")
                    else:
                        print("No records found for this symbol")
        else:
            print("❌ No calculation results returned")
            
    except Exception as e:
        print(f"❌ Single calculation error: {e}")
        import traceback
        traceback.print_exc()
    
    print("")
    
    # Test 3: Direct database insertion test
    print("3. TESTING DIRECT DATABASE INSERTION")
    print("-" * 35)
    
    try:
        # Create test data
        test_data = {
            'symbol': 'TEST',
            'duration_type': '1W',
            'start_date': date(2025, 11, 10),
            'end_date': date(2025, 11, 17),
            'percentage_change': 5.5,
            'absolute_change': 100.0,
            'start_price': 2000.0,
            'end_price': 2100.0,
            'highest_price': 2150.0,
            'lowest_price': 1950.0,
            'volume_total': 1000000,
            'calculation_date': datetime.now(),
            'market_direction': 'UP',
            'strength_rating': 8,
            'momentum_score': 0.75,
            'volatility': 0.15,
            'relative_strength': 0.8,
            'trend_consistency': 0.9,
            'breakout_potential': 0.7,
            'risk_score': 0.3,
            'volume_surge': 1.2,
            'price_velocity': 0.6,
            'momentum_acceleration': 0.1,
            'support_resistance_ratio': 1.1,
            'high_low_ratio': 1.1,
            'trading_days': 5
        }
        
        test_df = pd.DataFrame([test_data])
        
        db_service = DatabaseService()
        stored_count = db_service.bulk_upsert_dataframe(
            test_df, 
            'momentum_analysis',
            unique_columns=['symbol', 'duration_type', 'end_date']
        )
        
        print(f"✅ Direct insertion result: {stored_count} rows affected")
        
        # Verify the test record was stored
        engine = get_engine()
        with engine.connect() as conn:
            verify_query = """
            SELECT symbol, duration_type, percentage_change 
            FROM momentum_analysis 
            WHERE symbol = 'TEST'
            """
            verify_result = conn.execute(verify_query)
            test_records = verify_result.fetchall()
            
            if test_records:
                print(f"✅ Test record verified in database: {len(test_records)} records")
                # Clean up test data
                cleanup_query = "DELETE FROM momentum_analysis WHERE symbol = 'TEST'"
                conn.execute(cleanup_query)
                conn.commit()
                print("✅ Test data cleaned up")
            else:
                print("❌ Test record not found in database")
        
    except Exception as e:
        print(f"❌ Direct insertion error: {e}")
        import traceback
        traceback.print_exc()
    
    print("")
    
    # Test 4: Check for any recent transaction issues
    print("4. CHECKING RECENT TRANSACTION LOGS")
    print("-" * 35)
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Check for any recent insertions today
            today_query = """
            SELECT symbol, duration_type, COUNT(*) as count,
                   MAX(calculation_date) as latest_calc
            FROM momentum_analysis
            WHERE DATE(calculation_date) = CURDATE()
            GROUP BY symbol, duration_type
            ORDER BY latest_calc DESC
            """
            
            today_result = conn.execute(today_query)
            today_records = today_result.fetchall()
            
            if today_records:
                print(f"✅ Found {len(today_records)} symbol/duration combinations from today:")
                for record in today_records[:10]:  # Show first 10
                    print(f"  {record[0]:12} | {record[1]:2} | Count: {record[2]} | Latest: {record[3]}")
            else:
                print("❌ No records found from today")
                
                # Check latest records regardless of date
                latest_query = """
                SELECT symbol, duration_type, calculation_date
                FROM momentum_analysis
                ORDER BY calculation_date DESC
                LIMIT 10
                """
                
                latest_result = conn.execute(latest_query)
                latest_records = latest_result.fetchall()
                
                if latest_records:
                    print(f"\nLatest 10 records in database:")
                    for record in latest_records:
                        print(f"  {record[0]:12} | {record[1]:2} | {record[2]}")
                else:
                    print("❌ No records found in database at all")
    
    except Exception as e:
        print(f"❌ Transaction log check error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDEBUG COMPLETE")
    print("=" * 20)
    print("Summary:")
    print("- If calculations work but storage fails, there's a database schema issue")
    print("- If direct insertion fails, there's a database permission/connection issue")
    print("- If no recent records exist, transactions may not be committing")


if __name__ == "__main__":
    debug_storage_issues()