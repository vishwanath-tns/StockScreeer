"""
Test with a larger sector that has more data
"""
from services.reports.pdf_report_generator import PDFReportGenerator

def test_large_sector():
    """Test with a sector that has more data"""
    try:
        generator = PDFReportGenerator()
        
        # Check Nifty 50 (should have more data)
        print("Checking data for Nifty 50...")
        df_nifty50 = generator.get_momentum_data(
            duration_filter=['1W', '1M'], 
            sector_filter=['Nifty 50']
        )
        print(f"   Nifty 50 records: {len(df_nifty50)}")
        if not df_nifty50.empty:
            print(f"   Unique symbols: {df_nifty50['symbol'].nunique()}")
            print(f"   For 1W: {len(df_nifty50[df_nifty50['duration'] == '1W'])} records")
            print(f"   For 1M: {len(df_nifty50[df_nifty50['duration'] == '1M'])} records")
        
        # Test PDF generation with Nifty 50 and top_n=50
        print(f"\nGenerating PDF with Nifty 50 and top_n=50...")
        success = generator.generate_top_performers_report(
            output_path="test_nifty50_top50.pdf",
            top_n=50,
            duration_filter=['1W', '1M'],
            sector_filter=['Nifty 50'],
            include_charts=False
        )
        print(f"   Result: {'SUCCESS' if success else 'FAILED'}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_large_sector()