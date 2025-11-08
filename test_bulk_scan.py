"""Test the bulk scanning function that was having the SQL parameter errors."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_bulk_scan():
    """Test the bulk scanning functionality."""
    try:
        from services.trends_service import scan_current_day_trends
        import reporting_adv_decl as rad
        
        print("Testing bulk scan_current_day_trends function...")
        
        # Get database engine
        engine = rad.engine()
        
        print("Starting bulk scan (this may take a moment)...")
        
        # Run the scan with just a few symbols to test
        results_df = scan_current_day_trends(engine)
        
        print(f"Scan completed! Processed {len(results_df)} symbols")
        if not results_df.empty:
            print(f"Sample results:")
            print(results_df.head())
        
        print("\n✅ Bulk scan test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_bulk_scan()