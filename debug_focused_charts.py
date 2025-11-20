"""
Simple VCP Focused Charts - Debug Version
=========================================
Create focused charts for just a few stocks to debug issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector
import seaborn as sns

# Set clean style
plt.style.use('seaborn-v0_8')

class SimpleVCPFocusedChart:
    """
    Simple focused chart creator for debugging
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
    
    def create_simple_focused_chart(self, symbol: str):
        """Create a simple focused chart for one symbol"""
        
        print(f"🔍 Processing {symbol}...")
        
        try:
            # Get extended data (18 months)
            end_date = date.today()
            start_date = end_date - timedelta(days=540)  # ~18 months
            
            print(f"   Fetching data from {start_date} to {end_date}")
            
            # Get data
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            
            if len(data) < 100:
                print(f"   ❌ Insufficient data: only {len(data)} records")
                return None
            
            print(f"   ✅ Got {len(data)} records")
            
            # Detect patterns
            print(f"   🔍 Detecting VCP patterns...")
            patterns = self.detector.detect_vcp_patterns(data, symbol)
            
            if not patterns:
                print(f"   ❌ No patterns found")
                return None
            
            # Get best pattern
            best_pattern = max(patterns, key=lambda p: p.quality_score)
            print(f"   ✅ Found pattern with quality {best_pattern.quality_score:.1f}")
            
            # Create focused chart
            chart_path = f"charts/debug_focused_{symbol}.png"
            self._create_debug_chart(data, best_pattern, symbol, chart_path)
            
            return chart_path
            
        except Exception as e:
            print(f"   ❌ Error processing {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_debug_chart(self, data, pattern, symbol, save_path):
        """Create simple debug chart"""
        
        print(f"   📊 Creating chart...")
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1])
        
        # Plot 1: Price
        ax1.plot(data.index, data['close'], linewidth=2, color='blue', label='Price')
        
        # Add moving averages
        ma20 = data['close'].rolling(20, min_periods=1).mean()
        ax1.plot(data.index, ma20, '--', alpha=0.7, color='orange', label='MA20')
        
        # Highlight pattern base
        if pattern:
            ax1.axvspan(pattern.pattern_start, pattern.pattern_end, 
                       alpha=0.2, color='green', label='VCP Base')
            
            # Mark contractions
            for i, contraction in enumerate(pattern.contractions[:3]):  # Only first 3
                ax1.axvspan(contraction.start_date, contraction.end_date, 
                           alpha=0.3, color='red')
                
                # Add label
                mid_date = contraction.start_date + (contraction.end_date - contraction.start_date) / 2
                ax1.text(mid_date, data['close'].max() * 0.98, f'C{i+1}', 
                        ha='center', fontweight='bold', fontsize=10)
        
        ax1.set_title(f'{symbol} - VCP Pattern (Quality: {pattern.quality_score:.1f})')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Volume
        colors = ['green' if c >= o else 'red' for c, o in zip(data['close'], data['open'])]
        ax2.bar(data.index, data['volume'], color=colors, alpha=0.6, width=1)
        
        ax2.set_title('Volume')
        ax2.set_ylabel('Volume')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        # Save
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"   ✅ Chart saved: {save_path}")
        plt.close(fig)


def test_focused_charts():
    """Test focused charts on a few symbols"""
    
    print("🧪 TESTING FOCUSED VCP CHARTS")
    print("=" * 40)
    
    # Test symbols (from our previous successful analysis)
    test_symbols = ['HDFCBANK', 'CIPLA', 'BAJAJFINSV']
    
    chart_creator = SimpleVCPFocusedChart()
    
    for i, symbol in enumerate(test_symbols, 1):
        print(f"\n[{i}/{len(test_symbols)}] Testing {symbol}")
        print("-" * 20)
        
        try:
            chart_path = chart_creator.create_simple_focused_chart(symbol)
            if chart_path:
                print(f"✅ SUCCESS: {chart_path}")
            else:
                print(f"❌ FAILED: No chart created")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n🎉 TESTING COMPLETE!")
    print("Check charts/ directory for debug_focused_*.png files")


if __name__ == "__main__":
    test_focused_charts()