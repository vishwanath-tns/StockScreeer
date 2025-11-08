"""Setup script for the trends analysis database table."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def setup_trends_table():
    """Create the trends analysis table in the database."""
    try:
        # Use the existing engine from reporting_adv_decl which properly loads .env
        import reporting_adv_decl as rad
        from db.trends_repo import create_trend_table
        
        print("Setting up trends analysis table...")
        
        # Get database engine using existing working function
        engine = rad.engine()
        
        # Create the table
        create_trend_table(engine)
        
        print("✅ Trends analysis table created successfully!")
        print("\nThe table 'trend_analysis' is now available with the following structure:")
        print("- symbol: Stock symbol")
        print("- trade_date: Date of analysis")
        print("- daily_trend: UP or DOWN")
        print("- weekly_trend: UP or DOWN") 
        print("- monthly_trend: UP or DOWN")
        print("- trend_rating: -3 to +3")
        print("- created_at/updated_at: Timestamps")
        
        print("\nYou can now use the Trend Analysis tab in the scanner GUI!")
        
    except Exception as e:
        print(f"❌ Error setting up trends table: {e}")
        print("\nPlease ensure:")
        print("1. MySQL server is running")
        print("2. Database credentials in .env file are correct")
        print("3. The 'marketdata' database exists")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    setup_trends_table()