"""
Demonstrate Full Top 50 Functionality with All Sectors
"""
from services.reports.pdf_report_generator import PDFReportGenerator
import os

def demo_full_top50():
    """Demonstrate Top 50 working with all available data"""
    try:
        generator = PDFReportGenerator()
        
        print("🚀 Demonstrating Full Top 50 Functionality")
        print("=" * 50)
        
        # First, show data availability
        print("\n📊 Data Availability Check:")
        df_all = generator.get_momentum_data(duration_filter=['1W', '1M', '3M'], sector_filter=None)
        print(f"   Total records available: {len(df_all)}")
        print(f"   Unique symbols: {df_all['symbol'].nunique()}")
        print(f"   Durations: {list(df_all['duration'].unique())}")
        
        for duration in df_all['duration'].unique():
            duration_count = len(df_all[df_all['duration'] == duration])
            print(f"   {duration}: {duration_count} stocks available")
        
        print(f"\n✅ With {df_all['symbol'].nunique()} unique stocks, we can easily generate Top 50!")
        
        # Generate PDF with Top 50 - All Sectors
        print(f"\n📄 Generating PDF Report:")
        print(f"   ⚙️  Settings: Top 50 gainers + 50 losers per duration")
        print(f"   📈 Durations: 1W, 1M, 3M (Higher TF first)")
        print(f"   🎯 Sectors: All sectors (no filter)")
        
        output_path = "demo_full_top50_report.pdf"
        success = generator.generate_top_performers_report(
            output_path=output_path,
            top_n=50,
            duration_filter=['1W', '1M', '3M'],  # Multiple durations
            sector_filter=None,  # All sectors - maximum data
            include_charts=True
        )
        
        if success and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"\n🎉 SUCCESS! Report generated: {output_path}")
            print(f"   📄 File size: {file_size:,} bytes")
            print(f"   📊 Expected content:")
            print(f"      • 3M Duration: Top 50 gainers + Top 50 losers = 100 stocks")
            print(f"      • 1M Duration: Top 50 gainers + Top 50 losers = 100 stocks")  
            print(f"      • 1W Duration: Top 50 gainers + Top 50 losers = 100 stocks")
            print(f"      • Cross-duration analysis with up to 20 stocks")
            print(f"      • Total: 300+ stock entries across all tables!")
            
            # Calculate expected vs actual content
            estimated_entries = 50 * 2 * 3  # 50 gainers + 50 losers × 3 durations
            print(f"\n📈 Theoretical maximum entries: {estimated_entries}")
            
        else:
            print(f"\n❌ Failed to generate report")
        
        print(f"\n💡 To test this in the GUI:")
        print(f"   1. Launch scanner_gui.py")
        print(f"   2. Click '📄 Generate PDF Report' button")
        print(f"   3. Leave sectors list EMPTY (or click 'Clear All')")
        print(f"   4. Set 'Top N Gainers/Losers' to 50")
        print(f"   5. Select multiple durations (1W, 1M, 3M)")
        print(f"   6. Click 'Generate Report'")
        print(f"   7. Open PDF - you'll see full 50-entry tables! 🎯")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_full_top50()