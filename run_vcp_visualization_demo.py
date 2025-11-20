"""
Interactive VCP Visualization Demo
================================

Complete demo script showing how to use the VCP visualization system.
Run this to see the full capabilities in action.

Usage:
    python run_vcp_visualization_demo.py

This will create charts and reports demonstrating all features.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from volatility_patterns.visualization.vcp_visualizer import VCPVisualizer
from volatility_patterns.analysis.vcp_scanner import VCPScanner
from volatility_patterns.analysis.vcp_backtester import VCPBacktester, BacktestConfig


def main():
    """Run comprehensive VCP visualization demo"""
    print("🚀 VCP VISUALIZATION SYSTEM DEMO")
    print("=" * 50)
    
    # Create output directories
    os.makedirs("charts", exist_ok=True)
    os.makedirs("vcp_reports", exist_ok=True)
    
    # Initialize components
    print("\n📊 Initializing VCP System Components...")
    visualizer = VCPVisualizer(figsize=(16, 12))
    scanner = VCPScanner()
    backtester = VCPBacktester()
    
    # Demo symbols (major stocks with good data)
    demo_symbols = [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
        "SBIN", "LT", "ITC", "HINDUNILVR", "BHARTIARTL"
    ]
    
    print(f"✓ System initialized")
    print(f"🔍 Testing with {len(demo_symbols)} major stocks")
    
    # Phase 1: Pattern Scanning
    print(f"\n📈 PHASE 1: VCP Pattern Detection")
    print("-" * 30)
    
    all_results = []
    found_patterns = []
    
    for i, symbol in enumerate(demo_symbols[:5], 1):  # Test first 5
        print(f"[{i}/5] Scanning {symbol}...")
        
        try:
            result = scanner.scan_single_stock(
                symbol=symbol,
                lookback_days=365,
                min_quality=30.0  # Lower threshold for demo
            )
            
            all_results.append(result)
            
            if result.best_pattern:
                found_patterns.append((symbol, result.best_pattern))
                print(f"  ✅ Pattern found! Quality: {result.best_pattern.quality_score:.1f}")
            else:
                print(f"  ⚪ No pattern detected")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}...")
    
    print(f"\n🎯 Pattern Detection Summary:")
    print(f"   • Stocks scanned: {len(all_results)}")
    print(f"   • Patterns found: {len(found_patterns)}")
    
    if found_patterns:
        best_quality = max(p[1].quality_score for p in found_patterns)
        print(f"   • Best quality: {best_quality:.1f}")
        
        # Sort patterns by quality
        found_patterns.sort(key=lambda x: x[1].quality_score, reverse=True)
    
    # Phase 2: Visualization Creation
    print(f"\n🎨 PHASE 2: Creating Visualizations")
    print("-" * 30)
    
    if found_patterns:
        # Visualize best pattern
        best_symbol, best_pattern = found_patterns[0]
        
        print(f"1. Creating detailed chart for {best_symbol}...")
        
        end_date = date.today()
        start_date = best_pattern.pattern_start - timedelta(days=60)
        
        try:
            fig = visualizer.create_vcp_chart(
                symbol=best_symbol,
                start_date=start_date,
                end_date=end_date,
                pattern=best_pattern,
                save_path=f"charts/{best_symbol}_vcp_detailed.png",
                show_chart=False
            )
            
            print(f"  ✅ Detailed chart: charts/{best_symbol}_vcp_detailed.png")
            
            # Export comprehensive report
            report_path, chart_path = visualizer.export_pattern_report(
                symbol=best_symbol,
                pattern=best_pattern,
                output_dir="vcp_reports"
            )
            
            print(f"  ✅ Report exported: {os.path.basename(report_path)}")
            
        except Exception as e:
            print(f"  ❌ Chart error: {str(e)[:50]}...")
        
        # Create comparison chart if multiple patterns
        if len(found_patterns) > 1:
            print(f"2. Creating pattern comparison chart...")
            
            try:
                comp_fig = visualizer.create_pattern_comparison_chart(
                    patterns_data=found_patterns[:3],  # Top 3
                    save_path="charts/vcp_pattern_comparison.png"
                )
                
                print(f"  ✅ Comparison chart: charts/vcp_pattern_comparison.png")
                
            except Exception as e:
                print(f"  ❌ Comparison error: {str(e)[:50]}...")
    
    # Always create sample charts for demonstration
    print(f"3. Creating sample charts...")
    
    sample_symbols = ["RELIANCE", "TCS"] if not found_patterns else [found_patterns[0][0]]
    
    for symbol in sample_symbols:
        try:
            # Dashboard view
            dashboard_fig = visualizer.create_pattern_dashboard(
                symbol=symbol,
                lookback_days=365,
                save_path=f"charts/{symbol}_dashboard.png"
            )
            
            print(f"  ✅ Dashboard: charts/{symbol}_dashboard.png")
            
        except Exception as e:
            print(f"  ❌ Dashboard error for {symbol}: {str(e)[:50]}...")
    
    # Phase 3: Backtesting Integration
    print(f"\n📊 PHASE 3: Backtesting Integration")
    print("-" * 30)
    
    if found_patterns:
        best_symbol, best_pattern = found_patterns[0]
        
        print(f"Running backtest for {best_symbol} pattern...")
        
        try:
            config = BacktestConfig(
                stop_loss_pct=8.0,
                profit_target_pct=25.0,
                position_size_pct=10.0
            )
            
            # Run backtest for pattern period
            end_date = date.today()
            start_date = best_pattern.pattern_start - timedelta(days=30)
            
            results = backtester.backtest_symbol(
                symbol=best_symbol,
                start_date=start_date,
                end_date=end_date,
                config=config
            )
            
            print(f"  ✅ Backtest completed")
            print(f"    • Patterns tested: {results.total_patterns}")
            print(f"    • Trades executed: {results.total_trades}")
            
            if results.total_trades > 0:
                print(f"    • Win rate: {results.win_rate:.1f}%")
                print(f"    • Total return: {results.total_return:.1f}%")
            
        except Exception as e:
            print(f"  ❌ Backtest error: {str(e)[:50]}...")
    
    # Phase 4: Summary and Instructions
    print(f"\n📋 PHASE 4: Summary & Instructions")
    print("-" * 30)
    
    print(f"\n🎯 Demo Results Summary:")
    print(f"   • VCP patterns detected: {len(found_patterns)}")
    print(f"   • Charts created: {len(os.listdir('charts')) if os.path.exists('charts') else 0}")
    print(f"   • Reports generated: {len(os.listdir('vcp_reports')) if os.path.exists('vcp_reports') else 0}")
    
    print(f"\n📁 Output Files:")
    if os.path.exists("charts"):
        chart_files = [f for f in os.listdir("charts") if f.endswith('.png')]
        for file in chart_files[-5:]:  # Show last 5 files
            print(f"   📊 charts/{file}")
    
    if os.path.exists("vcp_reports"):
        report_files = os.listdir("vcp_reports")
        for file in report_files[-3:]:  # Show last 3 files
            print(f"   📄 vcp_reports/{file}")
    
    print(f"\n🚀 Next Steps - How to Use:")
    print(f"""
1. 📊 VIEW CHARTS:
   • Open any PNG file in charts/ folder
   • Charts show price action, patterns, indicators
   
2. 📖 READ REPORTS:
   • Check text files in vcp_reports/ folder
   • Contains detailed pattern analysis
   
3. 🔍 SCAN MORE STOCKS:
   from volatility_patterns.analysis.vcp_scanner import VCPScanner
   scanner = VCPScanner()
   result = scanner.scan_single_stock("SYMBOL", lookback_days=365, min_quality=50)
   
4. 🎨 CREATE CUSTOM CHARTS:
   from volatility_patterns.visualization.vcp_visualizer import VCPVisualizer
   viz = VCPVisualizer()
   fig = viz.create_vcp_chart("SYMBOL", start_date, end_date)
   
5. 📊 RUN BACKTESTS:
   from volatility_patterns.analysis.vcp_backtester import VCPBacktester
   backtester = VCPBacktester()
   results = backtester.backtest_symbol("SYMBOL", start_date, end_date)
""")
    
    print(f"\n🎉 VCP VISUALIZATION SYSTEM DEMO COMPLETE!")
    print(f"System is ready for pattern detection and analysis.")


if __name__ == "__main__":
    main()