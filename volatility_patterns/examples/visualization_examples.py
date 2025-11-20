"""
VCP Pattern Chart Examples
========================

Example scripts to demonstrate VCP visualization capabilities:
- Single pattern visualization
- Multiple pattern comparison  
- Pattern dashboard creation
- Batch visualization

Usage examples for the VCP visualization system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from volatility_patterns.visualization.vcp_visualizer import VCPVisualizer
from volatility_patterns.analysis.vcp_scanner import VCPScanner


def demo_single_pattern_chart():
    """Demonstrate single VCP pattern visualization"""
    print("=== Single VCP Pattern Visualization Demo ===")
    
    visualizer = VCPVisualizer()
    
    # Example: Create chart for a specific symbol
    symbol = "RELIANCE"  # You can change this
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    try:
        # Create and display chart
        fig = visualizer.create_vcp_chart(
            symbol=symbol,
            start_date=start_date, 
            end_date=end_date,
            save_path=f"charts/{symbol}_vcp_analysis.png",
            show_chart=True
        )
        
        print(f"✓ Chart created for {symbol}")
        
    except Exception as e:
        print(f"✗ Error creating chart for {symbol}: {e}")


def demo_pattern_dashboard():
    """Demonstrate comprehensive pattern dashboard"""
    print("\n=== VCP Pattern Dashboard Demo ===")
    
    visualizer = VCPVisualizer()
    
    # Test symbols (you can modify these)
    test_symbols = ["TCS", "INFY", "HDFCBANK"]
    
    for symbol in test_symbols:
        try:
            fig = visualizer.create_pattern_dashboard(
                symbol=symbol,
                lookback_days=365,
                save_path=f"charts/{symbol}_dashboard.png"
            )
            print(f"✓ Dashboard created for {symbol}")
            
        except Exception as e:
            print(f"✗ Error creating dashboard for {symbol}: {e}")


def demo_scanner_with_visualization():
    """Demonstrate scanning and visualizing best patterns"""
    print("\n=== Scanner + Visualization Demo ===")
    
    scanner = VCPScanner()
    visualizer = VCPVisualizer()
    
    # Scan for patterns
    print("Scanning for VCP patterns...")
    test_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    
    all_patterns = []
    
    for symbol in test_symbols:
        try:
            patterns = scanner.scan_single_symbol(
                symbol=symbol,
                lookback_days=365,
                min_quality_score=50
            )
            
            for pattern in patterns:
                all_patterns.append((symbol, pattern))
                print(f"✓ Found pattern in {symbol} (Quality: {pattern.quality_score:.1f})")
                
        except Exception as e:
            print(f"✗ Error scanning {symbol}: {e}")
    
    # Sort by quality score
    all_patterns.sort(key=lambda x: x[1].quality_score, reverse=True)
    
    if all_patterns:
        print(f"\nFound {len(all_patterns)} patterns total")
        
        # Visualize top 3 patterns
        top_patterns = all_patterns[:3]
        
        for i, (symbol, pattern) in enumerate(top_patterns):
            try:
                # Create individual chart
                end_date = date.today()
                start_date = pattern.pattern_start - timedelta(days=60)
                
                fig = visualizer.create_vcp_chart(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date, 
                    pattern=pattern,
                    save_path=f"charts/top_pattern_{i+1}_{symbol}.png",
                    show_chart=False
                )
                
                # Export detailed report
                visualizer.export_pattern_report(
                    symbol=symbol,
                    pattern=pattern,
                    output_dir="vcp_reports"
                )
                
                print(f"✓ Exported analysis for {symbol} (Rank #{i+1})")
                
            except Exception as e:
                print(f"✗ Error exporting {symbol}: {e}")
        
        # Create comparison chart
        try:
            comp_fig = visualizer.create_pattern_comparison_chart(
                patterns_data=top_patterns,
                save_path="charts/pattern_comparison.png"
            )
            print("✓ Created pattern comparison chart")
            
        except Exception as e:
            print(f"✗ Error creating comparison chart: {e}")
    
    else:
        print("No VCP patterns found in test symbols")


def demo_custom_visualization():
    """Demonstrate custom visualization settings"""
    print("\n=== Custom Visualization Demo ===")
    
    # Create visualizer with custom settings
    visualizer = VCPVisualizer(figsize=(20, 15))
    
    symbol = "RELIANCE"
    end_date = date.today()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    try:
        # Create chart with custom timeframe
        fig = visualizer.create_vcp_chart(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            save_path=f"charts/{symbol}_custom_6months.png",
            show_chart=True
        )
        
        print(f"✓ Custom chart created for {symbol} (6 months)")
        
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("VCP Pattern Visualization Examples")
    print("=" * 50)
    
    # Create output directories
    os.makedirs("charts", exist_ok=True)
    os.makedirs("vcp_reports", exist_ok=True)
    
    # Run demos (comment out any you don't want to run)
    
    # 1. Single pattern visualization
    demo_single_pattern_chart()
    
    # 2. Pattern dashboard
    demo_pattern_dashboard()
    
    # 3. Scanner integration
    demo_scanner_with_visualization()
    
    # 4. Custom visualization
    demo_custom_visualization()
    
    print("\n" + "=" * 50)
    print("Demo completed! Check the 'charts' and 'vcp_reports' folders for output.")
    print("\nVisualization Features Demonstrated:")
    print("✓ Candlestick price charts with moving averages")
    print("✓ VCP pattern highlighting and annotations")
    print("✓ Volume analysis with dry-up detection")
    print("✓ Technical indicators (ATR, Bollinger Bands)")
    print("✓ Pattern quality scoring and stage analysis")
    print("✓ Multiple pattern comparison")
    print("✓ Comprehensive reports and exports")