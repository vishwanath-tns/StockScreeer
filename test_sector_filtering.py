"""
Test PDF generation with sector filtering
"""
from services.reports.pdf_report_generator import PDFReportGenerator
import os

def test_with_sectors():
    """Test PDF generation with specific sectors"""
    try:
        generator = PDFReportGenerator()
        
        # Test 1: Generate without sector filter
        print("Test 1: Generating PDF without sector filter...")
        output_path = "test_all_sectors.pdf"
        success = generator.generate_top_performers_report(
            output_path=output_path,
            duration_filter=['1W', '1M', '3M'],
            sector_filter=None,
            include_charts=False
        )
        print(f"  Result: {'SUCCESS' if success else 'FAILED'}")
        if os.path.exists(output_path):
            print(f"  File size: {os.path.getsize(output_path)} bytes")
        
        # Test 2: Generate with specific sector filter
        print("\nTest 2: Generating PDF with Nifty IT sector filter...")
        output_path = "test_nifty_it.pdf"
        success = generator.generate_top_performers_report(
            output_path=output_path,
            duration_filter=['1W', '1M'],
            sector_filter=['Nifty IT'],
            include_charts=False
        )
        print(f"  Result: {'SUCCESS' if success else 'FAILED'}")
        if os.path.exists(output_path):
            print(f"  File size: {os.path.getsize(output_path)} bytes")
        
        # Test 3: Test data retrieval
        print("\nTest 3: Testing sector data retrieval...")
        sectors = generator.get_available_sectors()
        print(f"  Available sectors: {len(sectors)}")
        print(f"  First 5 sectors: {sectors[:5]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_sectors()