"""
Check available data for sectors to understand table size limits
"""
from services.reports.pdf_report_generator import PDFReportGenerator

def check_data_availability():
    """Check how much data is available for different sectors"""
    try:
        generator = PDFReportGenerator()
        
        # Check data without sector filter
        print("1. Checking data without sector filter...")
        df_all = generator.get_momentum_data(duration_filter=['1W', '1M'], sector_filter=None)
        print(f"   Total records: {len(df_all)}")
        if not df_all.empty:
            print(f"   Unique symbols: {df_all['symbol'].nunique()}")
            print(f"   Durations: {df_all['duration'].unique()}")
        
        # Check data for Nifty MidSmall Healthcare
        print("\n2. Checking data for Nifty MidSmall Healthcare...")
        df_healthcare = generator.get_momentum_data(
            duration_filter=['1W', '1M'], 
            sector_filter=['Nifty MidSmall Healthcare']
        )
        print(f"   Healthcare records: {len(df_healthcare)}")
        if not df_healthcare.empty:
            print(f"   Unique symbols: {df_healthcare['symbol'].nunique()}")
            print(f"   Durations: {df_healthcare['duration'].unique()}")
            print(f"   Sample symbols: {list(df_healthcare['symbol'].unique()[:10])}")
        
        # Check data for a bigger sector like Nifty 500
        print("\n3. Checking data for all sectors...")
        sectors = generator.get_available_sectors()
        print(f"   Available sectors: {len(sectors)}")
        print(f"   Sectors: {sectors[:10]}{'...' if len(sectors) > 10 else ''}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_data_availability()