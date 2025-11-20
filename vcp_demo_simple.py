"""
VCP Visualization System Demo
============================

Complete demo script showing VCP visualization capabilities.
This demonstrates all the features you requested:
- Pattern detection and visualization
- Backtesting integration  
- Comprehensive charting

Run: python vcp_demo_simple.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from volatility_patterns.visualization.vcp_visualizer import VCPVisualizer
from volatility_patterns.analysis.vcp_scanner import VCPScanner
from volatility_patterns.analysis.vcp_backtester import VCPBacktester, BacktestConfig


def main():
    """Run VCP visualization demo with simple output"""
    print("VCP VISUALIZATION SYSTEM DEMO")
    print("=" * 50)
    
    # Create directories
    os.makedirs("charts", exist_ok=True)
    os.makedirs("vcp_reports", exist_ok=True)
    
    # Initialize
    print("\nInitializing VCP System...")
    visualizer = VCPVisualizer(figsize=(16, 12))
    scanner = VCPScanner()
    backtester = VCPBacktester()
    print("+ System components loaded")
    
    # Test symbols
    demo_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    
    # Phase 1: Pattern Detection
    print(f"\nPHASE 1: VCP Pattern Detection")
    print("-" * 30)
    
    found_patterns = []
    
    for i, symbol in enumerate(demo_symbols[:3], 1):
        print(f"[{i}/3] Scanning {symbol}...")
        
        try:
            result = scanner.scan_single_stock(
                symbol=symbol,
                lookback_days=365,
                min_quality=25.0  # Very low threshold for demo
            )
            
            if result.best_pattern:
                found_patterns.append((symbol, result.best_pattern))
                print(f"  + Pattern found! Quality: {result.best_pattern.quality_score:.1f}")
                print(f"    Duration: {result.best_pattern.base_duration} days")
                print(f"    Contractions: {len(result.best_pattern.contractions)}")
            else:
                print(f"  - No pattern detected")
                
        except Exception as e:
            print(f"  x Error: {str(e)[:50]}...")
    
    print(f"\nPattern Summary: {len(found_patterns)} patterns found")
    
    # Phase 2: Visualization
    print(f"\nPHASE 2: Creating Visualizations")
    print("-" * 30)
    
    charts_created = 0
    
    # Create sample charts regardless of patterns found
    test_symbol = "RELIANCE"
    
    print(f"1. Creating comprehensive chart for {test_symbol}...")
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=180)  # 6 months
        
        fig = visualizer.create_vcp_chart(
            symbol=test_symbol,
            start_date=start_date,
            end_date=end_date,
            save_path=f"charts/{test_symbol}_comprehensive.png",
            show_chart=False
        )
        
        print(f"  + Chart saved: charts/{test_symbol}_comprehensive.png")
        charts_created += 1
        
    except Exception as e:
        print(f"  x Chart error: {str(e)}")
    
    print(f"2. Creating dashboard view for {test_symbol}...")
    try:
        dashboard_fig = visualizer.create_pattern_dashboard(
            symbol=test_symbol,
            lookback_days=365,
            save_path=f"charts/{test_symbol}_dashboard_demo.png"
        )
        
        print(f"  + Dashboard saved: charts/{test_symbol}_dashboard_demo.png")
        charts_created += 1
        
    except Exception as e:
        print(f"  x Dashboard error: {str(e)}")
    
    # If we found patterns, create pattern-specific visualizations
    if found_patterns:
        best_symbol, best_pattern = max(found_patterns, key=lambda x: x[1].quality_score)
        
        print(f"3. Creating pattern visualization for {best_symbol}...")
        try:
            end_date = date.today()
            start_date = best_pattern.pattern_start - timedelta(days=60)
            
            fig = visualizer.create_vcp_chart(
                symbol=best_symbol,
                start_date=start_date,
                end_date=end_date,
                pattern=best_pattern,
                save_path=f"charts/{best_symbol}_pattern_analysis.png",
                show_chart=False
            )
            
            print(f"  + Pattern chart: charts/{best_symbol}_pattern_analysis.png")
            charts_created += 1
            
            # Export report
            report_path, chart_path = visualizer.export_pattern_report(
                symbol=best_symbol,
                pattern=best_pattern,
                output_dir="vcp_reports"
            )
            
            print(f"  + Report exported: {os.path.basename(report_path)}")
            
        except Exception as e:
            print(f"  x Pattern visualization error: {str(e)}")
        
        # Comparison chart if multiple patterns
        if len(found_patterns) > 1:
            print(f"4. Creating pattern comparison...")
            try:
                comp_fig = visualizer.create_pattern_comparison_chart(
                    patterns_data=found_patterns,
                    save_path="charts/vcp_comparison_demo.png"
                )
                
                print(f"  + Comparison chart: charts/vcp_comparison_demo.png")
                charts_created += 1
                
            except Exception as e:
                print(f"  x Comparison error: {str(e)}")
    
    # Phase 3: Backtesting Demo
    print(f"\nPHASE 3: Backtesting Integration")
    print("-" * 30)
    
    print(f"Running sample backtest for {test_symbol}...")
    try:
        config = BacktestConfig(
            stop_loss_pct=8.0,
            profit_target_pct=20.0,
            position_size_pct=10.0
        )
        
        end_date = date.today()
        start_date = end_date - timedelta(days=180)  # 6 months test
        
        results = backtester.backtest_symbol(
            symbol=test_symbol,
            start_date=start_date,
            end_date=end_date,
            config=config
        )
        
        print(f"  + Backtest completed:")
        print(f"    Patterns analyzed: {results.total_patterns}")
        print(f"    Trades executed: {results.total_trades}")
        
        if results.total_trades > 0:
            print(f"    Win rate: {results.win_rate:.1f}%")
            print(f"    Total return: {results.total_return:.1f}%")
        else:
            print(f"    No trades executed (no patterns in test period)")
        
    except Exception as e:
        print(f"  x Backtest error: {str(e)}")
    
    # Final Summary
    print(f"\nSUMMARY")
    print("-" * 30)
    
    print(f"+ VCP patterns detected: {len(found_patterns)}")
    print(f"+ Charts created: {charts_created}")
    
    # List output files
    if os.path.exists("charts"):
        chart_files = [f for f in os.listdir("charts") if f.endswith('.png')]
        print(f"+ Total chart files: {len(chart_files)}")
        
        print(f"\nRecent charts created:")
        for file in chart_files[-3:]:
            print(f"  - {file}")
    
    if os.path.exists("vcp_reports"):
        report_files = os.listdir("vcp_reports")
        if report_files:
            print(f"\nReports generated:")
            for file in report_files[-2:]:
                print(f"  - {file}")
    
    print(f"\nVCP VISUALIZATION FEATURES DEMONSTRATED:")
    features = [
        "Candlestick charts with moving averages",
        "VCP pattern highlighting and annotations",
        "Volume analysis with dry-up detection",
        "Technical indicators (ATR, Bollinger Bands)",
        "Pattern quality scoring",
        "Dashboard views with comprehensive analysis",
        "Multi-pattern comparison charts",
        "Detailed text reports",
        "Backtesting integration",
        "Export capabilities (PNG, reports)"
    ]
    
    for feature in features:
        print(f"+ {feature}")
    
    print(f"\nUSAGE EXAMPLES:")
    print(f"""
# Scan for VCP patterns:
from volatility_patterns.analysis.vcp_scanner import VCPScanner
scanner = VCPScanner()
result = scanner.scan_single_stock("RELIANCE", lookback_days=365, min_quality=50)

# Create visualizations:
from volatility_patterns.visualization.vcp_visualizer import VCPVisualizer
viz = VCPVisualizer()
fig = viz.create_vcp_chart("RELIANCE", start_date, end_date)

# Run backtests:
from volatility_patterns.analysis.vcp_backtester import VCPBacktester
bt = VCPBacktester()
results = bt.backtest_symbol("RELIANCE", start_date, end_date)
""")
    
    print(f"\nDEMO COMPLETE! Check the charts/ and vcp_reports/ folders.")
    print(f"The visualization system is ready for pattern analysis.")


if __name__ == "__main__":
    main()