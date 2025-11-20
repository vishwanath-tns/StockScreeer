"""
PDF Report Generation Demo
=========================

Demonstrates the new PDF report functionality for Nifty 500 momentum analysis.
Shows how to generate professional PDF reports with top gainers/losers.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.reports.pdf_report_generator import PDFReportGenerator
from datetime import datetime

def main():
    print("🎯 PDF Report Generation Demo")
    print("=" * 50)
    
    # Initialize the PDF generator
    generator = PDFReportGenerator()
    
    print("📊 Available reporting options:")
    print("1. All durations (12M, 9M, 6M, 3M, 1M, 1W)")
    print("2. Higher timeframes only (12M, 9M, 6M)")
    print("3. Short-term focus (3M, 1M, 1W)")
    print("4. Custom selection")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        durations = None  # All durations
        report_name = "complete"
    elif choice == "2":
        durations = ['12M', '9M', '6M']
        report_name = "higher_tf"
    elif choice == "3":
        durations = ['3M', '1M', '1W']
        report_name = "short_term"
    elif choice == "4":
        print("Available durations: 12M, 9M, 6M, 3M, 1M, 1W")
        duration_input = input("Enter durations (comma-separated): ").strip()
        durations = [d.strip().upper() for d in duration_input.split(',')]
        report_name = "custom"
    else:
        print("Invalid choice. Using all durations.")
        durations = None
        report_name = "complete"
    
    # Get top N
    try:
        top_n = int(input("Number of top gainers/losers per duration (default 10): ").strip() or "10")
    except ValueError:
        top_n = 10
    
    # Generate output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"nifty500_momentum_{report_name}_top{top_n}_{timestamp}.pdf"
    
    print(f"\n🚀 Generating PDF report...")
    print(f"📁 Output: {output_path}")
    print(f"⏰ Durations: {durations if durations else 'All'}")
    print(f"🔢 Top N: {top_n}")
    
    # Generate the report
    success = generator.generate_top_performers_report(
        output_path=output_path,
        top_n=top_n,
        duration_filter=durations,
        sector_filter=None,  # All sectors
        include_charts=True
    )
    
    if success:
        print(f"\n✅ SUCCESS! PDF report generated: {output_path}")
        print(f"📋 Report contains:")
        print(f"   • Executive summary with key statistics")
        print(f"   • Top {top_n} gainers per timeframe")
        print(f"   • Top {top_n} losers per timeframe")
        print(f"   • Cross-timeframe analysis")
        print(f"   • Multi-timeframe winners")
        print(f"   • Professional formatting with charts")
        
        # Ask if user wants to open the file
        open_file = input(f"\n📖 Open the report now? (y/N): ").strip().lower()
        if open_file in ['y', 'yes']:
            try:
                import subprocess
                import platform
                
                if platform.system() == 'Windows':
                    os.startfile(output_path)
                elif platform.system() == 'Darwin':
                    subprocess.call(('open', output_path))
                else:
                    subprocess.call(('xdg-open', output_path))
                    
                print("📖 Report opened!")
            except Exception as e:
                print(f"❌ Could not open file: {e}")
    else:
        print("❌ FAILED to generate PDF report")
        print("Check the console output for error details")

if __name__ == "__main__":
    main()