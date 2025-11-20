"""
Momentum Analysis Report Generator
=================================

Practical script for generating various momentum analysis reports.
Demonstrates different report types and output formats.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from services.momentum.momentum_reporting_service import (
    MomentumReportingService, ReportConfig, ReportType, ReportFormat, MomentumDuration
)

def generate_comprehensive_momentum_reports():
    """Generate a comprehensive set of momentum analysis reports"""
    
    print("📊 COMPREHENSIVE MOMENTUM ANALYSIS")
    print("=" * 60)
    
    # Initialize reporting service
    reporting_service = MomentumReportingService()
    
    # Report configurations
    report_configs = [
        {
            "name": "📈 Top Performers Analysis",
            "config": ReportConfig(
                report_type=ReportType.TOP_PERFORMERS,
                duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
                top_n=10,
                output_format=ReportFormat.CONSOLE,
                include_negative=True
            )
        },
        {
            "name": "📊 Market Sentiment Summary", 
            "config": ReportConfig(
                report_type=ReportType.MOMENTUM_SUMMARY,
                duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH, MomentumDuration.THREE_MONTHS],
                output_format=ReportFormat.CONSOLE
            )
        },
        {
            "name": "🔄 Cross-Duration Momentum Analysis",
            "config": ReportConfig(
                report_type=ReportType.CROSS_DURATION_ANALYSIS,
                duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
                top_n=15,
                output_format=ReportFormat.CONSOLE
            )
        },
        {
            "name": "🔥 Momentum Heatmap",
            "config": ReportConfig(
                report_type=ReportType.MOMENTUM_HEATMAP,
                duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
                top_n=10,
                output_format=ReportFormat.CONSOLE
            )
        },
        {
            "name": "💪 Strength Distribution Analysis",
            "config": ReportConfig(
                report_type=ReportType.STRENGTH_DISTRIBUTION,
                duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
                output_format=ReportFormat.CONSOLE
            )
        },
        {
            "name": "📊 Volume-Momentum Correlation",
            "config": ReportConfig(
                report_type=ReportType.VOLUME_MOMENTUM_CORRELATION,
                duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
                top_n=5,
                output_format=ReportFormat.CONSOLE
            )
        },
        {
            "name": "⚡ Comparative Analysis",
            "config": ReportConfig(
                report_type=ReportType.COMPARATIVE_ANALYSIS,
                duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
                top_n=10,
                output_format=ReportFormat.CONSOLE
            )
        }
    ]
    
    # Generate each report
    for i, report_info in enumerate(report_configs, 1):
        print(f"\n[{i}/{len(report_configs)}] {report_info['name']}")
        print("=" * 80)
        
        try:
            report = reporting_service.generate_report(report_info['config'])
            print(report)
            
        except Exception as e:
            print(f"❌ Error generating {report_info['name']}: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-" * 80)
    
    print(f"\n🏆 COMPREHENSIVE MOMENTUM ANALYSIS COMPLETE!")

def generate_csv_report():
    """Generate a CSV report for export"""
    
    print("\n📄 GENERATING CSV REPORT")
    print("=" * 40)
    
    reporting_service = MomentumReportingService()
    
    config = ReportConfig(
        report_type=ReportType.TOP_PERFORMERS,
        duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
        top_n=20,
        output_format=ReportFormat.CSV,
        output_file="reports/momentum_top_performers.csv",
        include_negative=True
    )
    
    try:
        # Create reports directory if it doesn't exist
        os.makedirs("reports", exist_ok=True)
        
        report = reporting_service.generate_report(config)
        print("✅ CSV report generated successfully!")
        print("📁 File saved to: reports/momentum_top_performers.csv")
        print("\nFirst few lines of CSV:")
        print("-" * 40)
        lines = report.split('\n')
        for line in lines[:10]:
            if line.strip():
                print(line)
        if len(lines) > 10:
            print("...")
            
    except Exception as e:
        print(f"❌ Error generating CSV report: {e}")
        import traceback
        traceback.print_exc()

def generate_json_report():
    """Generate a JSON report for API consumption"""
    
    print("\n📄 GENERATING JSON REPORT")
    print("=" * 40)
    
    reporting_service = MomentumReportingService()
    
    config = ReportConfig(
        report_type=ReportType.MOMENTUM_SUMMARY,
        duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
        output_format=ReportFormat.JSON,
        output_file="reports/momentum_summary.json"
    )
    
    try:
        # Create reports directory if it doesn't exist
        os.makedirs("reports", exist_ok=True)
        
        report = reporting_service.generate_report(config)
        print("✅ JSON report generated successfully!")
        print("📁 File saved to: reports/momentum_summary.json")
        print("\nJSON structure preview:")
        print("-" * 40)
        lines = report.split('\n')
        for line in lines[:15]:
            if line.strip():
                print(line)
        if len(lines) > 15:
            print("...")
            
    except Exception as e:
        print(f"❌ Error generating JSON report: {e}")
        import traceback
        traceback.print_exc()

def generate_markdown_report():
    """Generate a Markdown report for documentation"""
    
    print("\n📄 GENERATING MARKDOWN REPORT")
    print("=" * 40)
    
    reporting_service = MomentumReportingService()
    
    config = ReportConfig(
        report_type=ReportType.TOP_PERFORMERS,
        duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
        top_n=10,
        output_format=ReportFormat.MARKDOWN,
        output_file="reports/momentum_analysis.md",
        include_negative=True
    )
    
    try:
        # Create reports directory if it doesn't exist
        os.makedirs("reports", exist_ok=True)
        
        report = reporting_service.generate_report(config)
        print("✅ Markdown report generated successfully!")
        print("📁 File saved to: reports/momentum_analysis.md")
        print("\nMarkdown preview:")
        print("-" * 40)
        lines = report.split('\n')
        for line in lines[:20]:
            if line.strip():
                print(line)
        if len(lines) > 20:
            print("...")
            
    except Exception as e:
        print(f"❌ Error generating Markdown report: {e}")
        import traceback
        traceback.print_exc()

def show_usage_examples():
    """Show practical usage examples"""
    
    print(f"\n💡 PRACTICAL USAGE EXAMPLES")
    print("=" * 50)
    print(f"""
🎯 MOMENTUM ANALYSIS WORKFLOWS:

1. Daily Market Analysis:
   - Run momentum summary for 1W, 1M durations
   - Check top performers for quick market overview
   - Analyze strength distribution for market breadth

2. Stock Selection:
   - Use cross-duration analysis to find consistent performers
   - Check volume-momentum correlation for quality setups
   - Compare short-term vs long-term trends

3. Portfolio Review:
   - Generate comparative analysis for existing holdings
   - Monitor momentum changes across timeframes
   - Identify position sizing opportunities

4. Reporting & Documentation:
   - Export CSV for spreadsheet analysis
   - Generate JSON for API integration
   - Create Markdown for team sharing

🚀 EXAMPLE CODE:

from services.momentum.momentum_reporting_service import *

# Quick market summary
config = ReportConfig(
    report_type=ReportType.MOMENTUM_SUMMARY,
    duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
)
service = MomentumReportingService()
report = service.generate_report(config)
print(report)

# Top performers with CSV export
config = ReportConfig(
    report_type=ReportType.TOP_PERFORMERS,
    duration_types=[MomentumDuration.ONE_MONTH],
    top_n=20,
    output_format=ReportFormat.CSV,
    output_file="daily_momentum.csv"
)
service.generate_report(config)
""")

def main():
    """Main function to run momentum analysis examples"""
    
    # Run comprehensive analysis
    generate_comprehensive_momentum_reports()
    
    # Generate different format reports
    generate_csv_report()
    generate_json_report()
    generate_markdown_report()
    
    # Show usage examples
    show_usage_examples()

if __name__ == "__main__":
    main()