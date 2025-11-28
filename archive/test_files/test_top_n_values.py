"""
Test PDF generation with custom top_n values
"""
from services.reports.pdf_report_generator import PDFReportGenerator
import os

def test_top_n_values():
    """Test PDF generation with different top_n values"""
    try:
        generator = PDFReportGenerator()
        
        # Test with top_n = 50
        print("Testing with top_n = 50...")
        output_path = "test_top50.pdf"
        success = generator.generate_top_performers_report(
            output_path=output_path,
            top_n=50,
            duration_filter=['1W', '1M'],
            sector_filter=['Nifty MidSmall Healthcare'],
            include_charts=False
        )
        print(f"  Result: {'SUCCESS' if success else 'FAILED'}")
        if os.path.exists(output_path):
            print(f"  File size: {os.path.getsize(output_path)} bytes")
        
        # Test with top_n = 25
        print("\nTesting with top_n = 25...")
        output_path = "test_top25.pdf"
        success = generator.generate_top_performers_report(
            output_path=output_path,
            top_n=25,
            duration_filter=['1W', '1M'],
            sector_filter=None,
            include_charts=False
        )
        print(f"  Result: {'SUCCESS' if success else 'FAILED'}")
        if os.path.exists(output_path):
            print(f"  File size: {os.path.getsize(output_path)} bytes")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_top_n_values()