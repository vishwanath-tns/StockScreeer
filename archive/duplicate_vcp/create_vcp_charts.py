"""
VCP Pattern Visualization Dashboard
===================================
Create comprehensive charts for the top VCP patterns found
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import date, timedelta
from volatility_patterns.visualization.vcp_visualizer import VCPVisualizer

def create_top_pattern_charts():
    """Create charts for top VCP patterns"""
    
    # Load the scan results
    with open('broader_universe_results/vcp_scan_results_20251116_155922.json', 'r') as f:
        results = json.load(f)

    # Extract unique top patterns
    all_patterns = results['all_patterns']
    unique_patterns = {}

    # Group by symbol and keep the best quality
    for pattern in all_patterns:
        symbol = pattern['symbol']
        if symbol not in unique_patterns or pattern['quality_score'] > unique_patterns[symbol]['quality_score']:
            unique_patterns[symbol] = pattern

    # Get top 5 patterns for visualization
    top_patterns = sorted(unique_patterns.values(), key=lambda x: x['quality_score'], reverse=True)[:5]
    
    print(f"🎨 CREATING CHARTS FOR TOP {len(top_patterns)} VCP PATTERNS")
    print("=" * 60)
    
    visualizer = VCPVisualizer()
    successful_charts = []
    
    # Calculate date range (400 days back from today)
    end_date = date.today()
    start_date = end_date - timedelta(days=400)
    
    for i, pattern in enumerate(top_patterns, 1):
        symbol = pattern['symbol']
        quality = pattern['quality_score']
        sector = pattern['sector']
        
        print(f"[{i}/5] Creating chart for {symbol} (Quality: {quality:.1f}, {sector})")
        
        try:
            # Create individual chart
            chart_path = f"charts/vcp_top_{i}_{symbol}_quality_{quality:.0f}.png"
            
            fig = visualizer.create_vcp_chart(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                save_path=chart_path,
                show_chart=False
            )
            
            successful_charts.append({
                'symbol': symbol,
                'quality': quality,
                'sector': sector,
                'chart_path': chart_path,
                'contractions': pattern['contractions'],
                'stage': pattern['current_stage']
            })
            
            print(f"    ✅ Saved: {chart_path}")
            
        except Exception as e:
            print(f"    ❌ Failed: {str(e)}")
    
    # Create summary
    print(f"\n📊 CHART CREATION SUMMARY")
    print(f"Successful charts: {len(successful_charts)}/5")
    
    if successful_charts:
        print(f"\n📈 SUCCESSFULLY CREATED CHARTS:")
        for chart in successful_charts:
            print(f"   {chart['symbol']:12} Quality: {chart['quality']:5.1f} "
                  f"Stage: {chart['stage']} ({chart['sector']})")
            print(f"                File: {chart['chart_path']}")
    
    return successful_charts

def create_comparison_chart():
    """Create a comparison chart of multiple top patterns"""
    
    print(f"\n🔄 CREATING PATTERN COMPARISON CHART")
    
    try:
        # Load top patterns
        with open('broader_universe_results/vcp_scan_results_20251116_155922.json', 'r') as f:
            results = json.load(f)
        
        # Get unique top 4 patterns for comparison
        all_patterns = results['all_patterns']
        unique_patterns = {}
        for pattern in all_patterns:
            symbol = pattern['symbol']
            if symbol not in unique_patterns or pattern['quality_score'] > unique_patterns[symbol]['quality_score']:
                unique_patterns[symbol] = pattern
        
        top_symbols = [pattern['symbol'] for pattern in 
                      sorted(unique_patterns.values(), key=lambda x: x['quality_score'], reverse=True)[:4]]
        
        visualizer = VCPVisualizer()
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=300)  # Shorter for comparison
        
        comparison_chart = visualizer.create_pattern_comparison_chart(
            symbols=top_symbols,
            start_date=start_date,
            end_date=end_date,
            save_path="charts/vcp_top_patterns_comparison.png"
        )
        
        print(f"✅ Comparison chart saved: charts/vcp_top_patterns_comparison.png")
        return True
        
    except Exception as e:
        print(f"❌ Comparison chart failed: {e}")
        return False

if __name__ == "__main__":
    print("VCP PATTERN VISUALIZATION DASHBOARD")
    print("=" * 50)
    
    # Create individual charts
    successful_charts = create_top_pattern_charts()
    
    # Create comparison chart
    create_comparison_chart()
    
    print(f"\n🎉 VISUALIZATION COMPLETE!")
    print(f"Check the charts/ directory for all generated visualizations.")
    print(f"Total charts created: {len(successful_charts) + 1}")