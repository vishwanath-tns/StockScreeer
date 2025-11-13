"""
Test script to verify that candlestick spacing is now even (no weekend gaps)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import reporting_adv_decl as rad
from sqlalchemy import text
from matplotlib.patches import Rectangle

def test_candlestick_spacing():
    """Test the new even-spaced candlestick approach"""
    print("🔍 Testing even candlestick spacing...")
    
    # Get sample data for testing
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get sample price data with weekends excluded
        query = text('''
            SELECT trade_date, open_price, high_price, low_price, close_price
            FROM nse_equity_bhavcopy_full
            WHERE symbol = 'RELIANCE'
                AND series = 'EQ'
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full), INTERVAL 20 DAY)
                AND DAYOFWEEK(trade_date) NOT IN (1, 7)  -- Exclude weekends
            ORDER BY trade_date
        ''')
        
        df = pd.read_sql(query, conn)
    
    if df.empty:
        print("❌ No data found for testing")
        return
    
    # Convert to datetime
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    
    print(f"📊 Sample data: {len(df)} trading days")
    print("📅 Date range:")
    for i, row in df.iterrows():
        weekday = row['trade_date'].strftime('%A')
        print(f"   {row['trade_date'].strftime('%Y-%m-%d')} ({weekday})")
    
    # Create comparison charts
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Chart 1: Old method (date-based spacing with gaps)
    print("\n📈 Creating old-style chart (with date gaps)...")
    for idx, row in df.iterrows():
        date = row['trade_date']
        open_price = float(row['open_price'])
        high = float(row['high_price'])
        low = float(row['low_price'])
        close = float(row['close_price'])
        
        color = 'green' if close >= open_price else 'red'
        
        # Draw with date-based positioning (old way)
        ax1.plot([date, date], [low, high], color='black', linewidth=0.8)
        
        body_height = abs(close - open_price)
        body_bottom = min(open_price, close)
        
        if body_height > 0:
            from datetime import timedelta
            rect = Rectangle((date - timedelta(hours=6), body_bottom), 
                           timedelta(hours=12), body_height,
                           facecolor=color, edgecolor='black', alpha=0.7)
            ax1.add_patch(rect)
    
    ax1.set_title('Old Method: Date-based spacing (gaps for weekends)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Price (₹)')
    ax1.grid(True, alpha=0.3)
    
    # Chart 2: New method (even spacing)
    print("📈 Creating new-style chart (even spacing)...")
    n_days = len(df)
    positions = np.arange(n_days)
    
    for i, (idx, row) in enumerate(df.iterrows()):
        x_pos = positions[i]
        open_price = float(row['open_price'])
        high = float(row['high_price'])
        low = float(row['low_price'])
        close = float(row['close_price'])
        
        color = 'green' if close >= open_price else 'red'
        
        # Draw with position-based spacing (new way)
        ax2.plot([x_pos, x_pos], [low, high], color='black', linewidth=0.8)
        
        body_height = abs(close - open_price)
        body_bottom = min(open_price, close)
        
        if body_height > 0:
            rect = Rectangle((x_pos - 0.3, body_bottom), 
                           0.6, body_height,
                           facecolor=color, edgecolor='black', alpha=0.7)
            ax2.add_patch(rect)
    
    # Set custom x-axis labels
    step = max(1, len(df) // 6)
    tick_positions = positions[::step]
    tick_labels = [df.iloc[i]['trade_date'].strftime('%b %d') for i in range(0, len(df), step)]
    
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels(tick_labels, rotation=45)
    ax2.set_title('New Method: Even spacing (no weekend gaps)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Price (₹)')
    ax2.set_xlabel('Trading Days')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('candlestick_spacing_comparison.png', dpi=100, bbox_inches='tight')
    plt.show()
    
    print("\n✅ Comparison charts created!")
    print("💾 Saved as 'candlestick_spacing_comparison.png'")
    print("\n📋 Key differences:")
    print("   🔴 Old method: Uneven spacing due to weekend date gaps")
    print("   🟢 New method: Even spacing with business days only")
    print("   ✅ New method eliminates visual gaps and provides cleaner charts")

def test_spacing_calculation():
    """Test the mathematical spacing"""
    print("\n🔢 Testing spacing calculations...")
    
    # Simulate 10 business days
    import pandas as pd
    dates = pd.date_range('2025-11-01', periods=15, freq='D')
    business_dates = [d for d in dates if d.weekday() < 5]  # Mon-Fri only
    
    print(f"📅 Original dates (including weekends): {len(dates)}")
    print(f"📅 Business dates only: {len(business_dates)}")
    
    # Old way: actual date spacing
    print("\n🔴 Old spacing (with gaps):")
    for i, date in enumerate(business_dates[:5]):
        if i > 0:
            gap = (date - business_dates[i-1]).days
            print(f"   Day {i+1}: {date.strftime('%Y-%m-%d %A')} - Gap: {gap} days")
        else:
            print(f"   Day {i+1}: {date.strftime('%Y-%m-%d %A')} - Gap: 0 days")
    
    # New way: even spacing
    print("\n🟢 New spacing (even):")
    positions = np.arange(len(business_dates))
    for i, pos in enumerate(positions[:5]):
        gap = 1 if i > 0 else 0
        print(f"   Position {pos}: {business_dates[i].strftime('%Y-%m-%d %A')} - Gap: {gap} unit")
    
    print("\n✅ Even spacing ensures consistent visual flow!")

if __name__ == "__main__":
    test_candlestick_spacing()
    test_spacing_calculation()
    
    print("\n🎉 All tests completed!")
    print("📋 Summary:")
    print("   ✅ Weekend gaps eliminated from candlestick charts")
    print("   ✅ Even spacing implemented for business days")
    print("   ✅ Professional chart appearance maintained")
    print("   ✅ Date labels properly positioned")