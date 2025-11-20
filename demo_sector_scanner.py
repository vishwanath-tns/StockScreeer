"""
Sector Pattern Scanner Demo

This script demonstrates the key features of the sector pattern scanning system.
Run this to see examples of:
1. Scanning multiple sectors
2. Pattern detection across timeframes
3. Breakout analysis
4. PDF report generation

Author: Stock Screener System
Date: November 2025
"""

from datetime import datetime
from services.sector_pattern_scanner import SectorPatternScanner, PatternResult
from services.sector_report_generator import SectorPatternReportGenerator

def demo_sector_scanning():
    """Demonstrate sector pattern scanning"""
    print("🔍 Sector Pattern Scanner Demo")
    print("=" * 50)
    
    # Initialize scanner
    scanner = SectorPatternScanner()
    
    # Get available sectors
    print("\n📊 Available Sectors:")
    sectors = scanner.get_available_sectors()
    for i, (sector_id, sector_name) in enumerate(sectors[:10]):
        print(f"  {sector_id}: {sector_name}")
    
    # Demo 1: Scan Nifty Bank
    print("\n🏦 Demo 1: Scanning Nifty Bank Sector")
    print("-" * 40)
    
    bank_sector_id = 4  # Nifty Bank
    bank_constituents = scanner.get_sector_constituents([bank_sector_id])
    
    if bank_constituents:
        sector_name = list(bank_constituents.keys())[0]
        symbols = bank_constituents[sector_name]
        print(f"Found {len(symbols)} stocks in {sector_name}:")
        print(f"  Symbols: {', '.join(symbols[:8])}{'...' if len(symbols) > 8 else ''}")
        
        # Scan patterns
        patterns, summaries = scanner.scan_sectors_comprehensive([bank_sector_id])
        
        if patterns:
            print(f"\n✅ Found {len(patterns)} patterns:")
            
            # Group by timeframe
            timeframes = {}
            for pattern in patterns:
                tf = pattern.timeframe
                if tf not in timeframes:
                    timeframes[tf] = []
                timeframes[tf].append(pattern)
            
            for timeframe, tf_patterns in timeframes.items():
                print(f"  {timeframe}: {len(tf_patterns)} patterns")
                for pattern in tf_patterns[:3]:  # Show first 3
                    print(f"    {pattern.symbol} - {pattern.pattern_type} (Range: {pattern.current_range:.2f})")
            
            # Check for breakouts
            breakouts = [p for p in patterns if p.breakout_signal]
            if breakouts:
                print(f"\n🚀 Breakout Signals: {len(breakouts)}")
                for breakout in breakouts[:3]:
                    print(f"  {breakout.symbol}: {breakout.breakout_signal[:50]}")
            else:
                print("\n⚠️  No breakout signals detected")
        else:
            print("  No patterns found for latest dates")
    
    # Demo 2: Multi-sector analysis
    print("\n🏭 Demo 2: Multi-Sector Analysis")
    print("-" * 40)
    
    # Select major sectors
    major_sectors = [1, 4, 5]  # Nifty 50, Bank, Financial Services
    sector_names = []
    
    for sector_id in major_sectors:
        sector_name = next((name for id, name in sectors if id == sector_id), f"Sector {sector_id}")
        sector_names.append(sector_name)
    
    print(f"Analyzing sectors: {', '.join(sector_names)}")
    
    patterns, summaries = scanner.scan_sectors_comprehensive(major_sectors, ['DAILY', 'WEEKLY'])
    
    print(f"\n📈 Multi-Sector Results:")
    print(f"  Total patterns found: {len(patterns)}")
    print(f"  Sectors analyzed: {len(summaries)}")
    
    # Show sector breakdown
    if summaries:
        print("\n📊 Sector Breakdown:")
        for summary in summaries:
            total_patterns = sum(summary.pattern_counts.values())
            total_breakouts = summary.breakout_counts.get('BREAKOUT_ABOVE', 0) + \
                            summary.breakout_counts.get('BREAKDOWN_BELOW', 0)
            
            print(f"  {summary.sector_name}:")
            print(f"    Stocks: {summary.total_stocks}, Patterns: {total_patterns}, Breakouts: {total_breakouts}")
            
            if summary.pattern_counts:
                pattern_str = ", ".join([f"{k}:{v}" for k, v in summary.pattern_counts.items() if v > 0])
                print(f"    Pattern types: {pattern_str}")
    
    return patterns, summaries

def demo_pdf_generation():
    """Demonstrate PDF report generation"""
    print("\n📄 Demo 3: PDF Report Generation")
    print("-" * 40)
    
    try:
        report_generator = SectorPatternReportGenerator()
        
        # Generate a quick Nifty Bank report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"reports/demo_nifty_bank_{timestamp}.pdf"
        
        print("Generating Nifty Bank PDF report...")
        
        from services.sector_report_generator import generate_nifty_bank_report
        result_path = generate_nifty_bank_report(report_path)
        
        import os
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✅ PDF report generated successfully!")
            print(f"  Path: {result_path}")
            print(f"  Size: {file_size:,} bytes")
            
            # List reports directory
            reports_dir = "reports"
            if os.path.exists(reports_dir):
                reports = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
                print(f"\n📁 Available reports in {reports_dir}/:")
                for report in reports[-5:]:  # Show last 5
                    report_path = os.path.join(reports_dir, report)
                    size = os.path.getsize(report_path)
                    print(f"  {report} ({size:,} bytes)")
        else:
            print("❌ Report generation failed")
            
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        print("Make sure reportlab and seaborn are installed: pip install reportlab seaborn")

def demo_usage_examples():
    """Show practical usage examples"""
    print("\n💡 Demo 4: Practical Usage Examples")
    print("-" * 40)
    
    print("""
    Here are some practical ways to use the Sector Pattern Scanner:
    
    1. Daily Trading Setup:
       - Scan all major sectors for latest DAILY patterns
       - Look for NR4/NR7 patterns (tight consolidation)
       - Check for breakout signals above previous highs
       - Focus on high-volume breakouts
    
    2. Weekly Analysis:
       - Scan for WEEKLY NR patterns for swing trades
       - Look for sectors with multiple stocks showing patterns
       - Check monthly patterns for long-term positioning
    
    3. Sector Rotation Strategy:
       - Compare pattern counts across sectors
       - Identify sectors with most breakout signals
       - Track sectors with consistent NR patterns
    
    4. Report Generation:
       - Generate weekly sector reports for analysis
       - Share PDF reports with team/clients
       - Archive reports for historical analysis
    
    5. GUI Usage:
       - Use the 'Sector Scanner' tab in scanner_gui.py
       - Select multiple sectors with checkboxes
       - Choose timeframes (Daily/Weekly/Monthly)
       - Enable breakout analysis
       - Export results to CSV or generate PDF
    """)

def main():
    """Run all demos"""
    try:
        # Run pattern scanning demos
        patterns, summaries = demo_sector_scanning()
        
        # Run PDF generation demo
        demo_pdf_generation()
        
        # Show usage examples
        demo_usage_examples()
        
        print("\n" + "=" * 50)
        print("🎉 Demo completed successfully!")
        print("\nNext Steps:")
        print("1. Launch the GUI: python scanner_gui.py")
        print("2. Navigate to 'Sector Scanner' tab")
        print("3. Try the Quick Reports for instant analysis")
        print("4. Experiment with different sector combinations")
        print("5. Generate detailed PDF reports for your analysis")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()