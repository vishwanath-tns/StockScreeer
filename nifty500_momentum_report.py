#!/usr/bin/env python3
"""
Nifty 500 Momentum Report Generator
===================================

Generates comprehensive momentum analysis reports for Nifty 500 stocks.
Includes sector analysis, top performers, and detailed statistics.
"""

import sys
import os
sys.path.append('.')

# Set UTF-8 encoding for Windows console
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from datetime import datetime, date
from services.market_breadth_service import get_engine
from sqlalchemy import text
from nifty500_stocks_list import NIFTY_500_STOCKS

def generate_nifty500_momentum_report():
    """Generate comprehensive Nifty 500 momentum report"""
    
    print("[*] GENERATING NIFTY 500 MOMENTUM REPORT")
    print("=" * 60)
    print(f"[*] Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] Total Nifty 500 Stocks: {len(NIFTY_500_STOCKS)}")
    print("")
    
    engine = get_engine()
    
    # Get today's momentum data
    query = text("""
        SELECT 
            symbol,
            duration_type,
            percentage_change,
            start_price,
            end_price,
            start_date,
            end_date,
            trading_days
        FROM momentum_analysis 
        WHERE DATE(calculation_date) = CURDATE()
            AND symbol IN :nifty500_symbols
        ORDER BY symbol, 
            CASE duration_type 
                WHEN '1W' THEN 1 WHEN '1M' THEN 2 WHEN '3M' THEN 3
                WHEN '6M' THEN 4 WHEN '9M' THEN 5 WHEN '12M' THEN 6
            END
    """)
    
    with engine.connect() as conn:
        # Convert list to tuple for SQL IN clause
        nifty500_tuple = tuple(NIFTY_500_STOCKS)
        result = conn.execute(query, {"nifty500_symbols": nifty500_tuple})
        momentum_data = result.fetchall()
    
    if not momentum_data:
        print("[ERROR] No momentum data found for today")
        return
    
    print(f"[OK] Found {len(momentum_data)} momentum records")
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(momentum_data, columns=[
        'symbol', 'duration_type', 'percentage_change', 'start_price', 
        'end_price', 'start_date', 'end_date', 'trading_days'
    ])
    
    # Ensure percentage_change is numeric
    df['percentage_change'] = pd.to_numeric(df['percentage_change'], errors='coerce')
    
    # Pivot for easier analysis
    pivot_df = df.pivot(index='symbol', columns='duration_type', values='percentage_change')
    pivot_df = pivot_df.fillna(0)
    
    # Ensure all columns are numeric
    for col in pivot_df.columns:
        pivot_df[col] = pd.to_numeric(pivot_df[col], errors='coerce').fillna(0)
    
    # Generate timestamp for files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save complete CSV
    csv_filename = f"reports/nifty500_momentum_report_{timestamp}.csv"
    pivot_df.to_csv(csv_filename)
    print(f"[SAVE] Saved complete data to: {csv_filename}")
    
    # 2. Generate analysis report
    report_lines = []
    report_lines.append("NIFTY 500 MOMENTUM ANALYSIS REPORT")
    report_lines.append("=" * 50)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Total Stocks Analyzed: {len(pivot_df)}")
    report_lines.append("")
    
    # Summary statistics
    report_lines.append("[*] SUMMARY STATISTICS")
    report_lines.append("-" * 30)
    
    for duration in ['1W', '1M', '3M', '6M', '9M', '12M']:
        if duration in pivot_df.columns:
            col_data = pivot_df[duration].dropna()
            if len(col_data) > 0:
                mean_val = col_data.mean()
                median_val = col_data.median()
                positive_count = (col_data > 0).sum()
                negative_count = (col_data < 0).sum()
                
                report_lines.append(f"{duration} Momentum:")
                report_lines.append(f"  Average: {mean_val:+.2f}%")
                report_lines.append(f"  Median:  {median_val:+.2f}%")
                report_lines.append(f"  Positive: {positive_count} stocks ({positive_count/len(col_data)*100:.1f}%)")
                report_lines.append(f"  Negative: {negative_count} stocks ({negative_count/len(col_data)*100:.1f}%)")
                report_lines.append("")
    
    # Top performers by duration
    for duration in ['1W', '1M', '3M', '6M']:
        if duration in pivot_df.columns:
            col_data = pivot_df[duration].dropna()
            if len(col_data) > 0:
                top_10 = col_data.nlargest(10)
                bottom_10 = col_data.nsmallest(10)
                
                report_lines.append(f"[TOP] TOP 10 PERFORMERS - {duration}")
                report_lines.append("-" * 30)
                for i, (symbol, pct) in enumerate(top_10.items(), 1):
                    report_lines.append(f"{i:2d}. {symbol:<12} {pct:+6.2f}%")
                report_lines.append("")
                
                report_lines.append(f"[BOT] BOTTOM 10 PERFORMERS - {duration}")
                report_lines.append("-" * 30)
                for i, (symbol, pct) in enumerate(bottom_10.items(), 1):
                    report_lines.append(f"{i:2d}. {symbol:<12} {pct:+6.2f}%")
                report_lines.append("")
    
    # Multi-timeframe analysis
    if all(col in pivot_df.columns for col in ['1W', '1M', '3M']):
        report_lines.append("[MULTI] MULTI-TIMEFRAME MOMENTUM LEADERS")
        report_lines.append("-" * 40)
        
        # Stocks positive across multiple timeframes
        multi_positive = pivot_df[(pivot_df['1W'] > 0) & 
                                 (pivot_df['1M'] > 0) & 
                                 (pivot_df['3M'] > 0)]
        
        if len(multi_positive) > 0:
            # Sort by average momentum
            multi_positive['avg_momentum'] = (multi_positive['1W'] + 
                                            multi_positive['1M'] + 
                                            multi_positive['3M']) / 3
            multi_positive = multi_positive.sort_values('avg_momentum', ascending=False)
            
            report_lines.append(f"Stocks positive in 1W, 1M, and 3M ({len(multi_positive)} stocks):")
            for i, (symbol, row) in enumerate(multi_positive.head(15).iterrows(), 1):
                report_lines.append(f"{i:2d}. {symbol:<12} 1W:{row['1W']:+5.1f}% 1M:{row['1M']:+5.1f}% 3M:{row['3M']:+5.1f}%")
            report_lines.append("")
    
    # Momentum distribution
    if '1M' in pivot_df.columns:
        monthly_data = pivot_df['1M'].dropna()
        strong_up = (monthly_data > 10).sum()
        moderate_up = ((monthly_data > 5) & (monthly_data <= 10)).sum()
        weak_up = ((monthly_data > 0) & (monthly_data <= 5)).sum()
        weak_down = ((monthly_data < 0) & (monthly_data >= -5)).sum()
        moderate_down = ((monthly_data < -5) & (monthly_data >= -10)).sum()
        strong_down = (monthly_data < -10).sum()
        
        report_lines.append("[DIST] MONTHLY MOMENTUM DISTRIBUTION")
        report_lines.append("-" * 35)
        report_lines.append(f"Strong Up (>10%):     {strong_up:3d} stocks ({strong_up/len(monthly_data)*100:.1f}%)")
        report_lines.append(f"Moderate Up (5-10%):  {moderate_up:3d} stocks ({moderate_up/len(monthly_data)*100:.1f}%)")
        report_lines.append(f"Weak Up (0-5%):       {weak_up:3d} stocks ({weak_up/len(monthly_data)*100:.1f}%)")
        report_lines.append(f"Weak Down (0 to -5%): {weak_down:3d} stocks ({weak_down/len(monthly_data)*100:.1f}%)")
        report_lines.append(f"Moderate Down (-5 to -10%): {moderate_down:3d} stocks ({moderate_down/len(monthly_data)*100:.1f}%)")
        report_lines.append(f"Strong Down (<-10%):  {strong_down:3d} stocks ({strong_down/len(monthly_data)*100:.1f}%)")
        report_lines.append("")
    
    # Trading recommendations
    report_lines.append("[TIPS] TRADING INSIGHTS")
    report_lines.append("-" * 20)
    
    if all(col in pivot_df.columns for col in ['1W', '1M']):
        # Short-term momentum leaders
        short_term_leaders = pivot_df[(pivot_df['1W'] > 3) & (pivot_df['1M'] > 5)]
        if len(short_term_leaders) > 0:
            report_lines.append("[FAST] Short-term Momentum (1W >3%, 1M >5%):")
            for symbol in short_term_leaders.head(10).index:
                row = short_term_leaders.loc[symbol]
                report_lines.append(f"   {symbol}: 1W {row['1W']:+.1f}%, 1M {row['1M']:+.1f}%")
            report_lines.append("")
    
    if all(col in pivot_df.columns for col in ['3M', '6M']):
        # Long-term trends
        long_term_trends = pivot_df[(pivot_df['3M'] > 8) & (pivot_df['6M'] > 12)]
        if len(long_term_trends) > 0:
            report_lines.append("[LONG] Long-term Trends (3M >8%, 6M >12%):")
            for symbol in long_term_trends.head(10).index:
                row = long_term_trends.loc[symbol]
                report_lines.append(f"   {symbol}: 3M {row['3M']:+.1f}%, 6M {row['6M']:+.1f}%")
            report_lines.append("")
    
    # Save text report
    txt_filename = f"reports/nifty500_momentum_analysis_{timestamp}.txt"
    with open(txt_filename, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"[SAVE] Saved analysis report to: {txt_filename}")
    
    # Print summary to console
    print("\n" + "="*60)
    print("[*] REPORT SUMMARY")
    print("="*60)
    for line in report_lines[:20]:  # Show first 20 lines
        print(line)
    print("...")
    print(f"[*] Full report available in: {txt_filename}")
    
    return {
        'csv_file': csv_filename,
        'txt_file': txt_filename,
        'total_stocks': len(pivot_df),
        'momentum_records': len(momentum_data)
    }

def get_nifty500_quick_stats():
    """Get quick statistics for Nifty 500 momentum data"""
    
    print("[*] NIFTY 500 QUICK STATS")
    print("=" * 30)
    
    engine = get_engine()
    
    with engine.connect() as conn:
        # Count records by duration for Nifty 500
        query = text("""
            SELECT 
                duration_type,
                COUNT(*) as count
            FROM momentum_analysis 
            WHERE DATE(calculation_date) = CURDATE()
                AND symbol IN :nifty500_symbols
            GROUP BY duration_type
            ORDER BY duration_type
        """)
        
        nifty500_tuple = tuple(NIFTY_500_STOCKS)
        result = conn.execute(query, {"nifty500_symbols": nifty500_tuple})
        stats = result.fetchall()
        
        total_records = 0
        print("[*] Today's Nifty 500 Momentum Records:")
        print("-" * 35)
        for duration, count in stats:
            print(f"{duration:3}: {count:3} stocks")
            total_records += count
        
        print(f"{'Total':<3}: {total_records:3} records")
        print()
        
        # Coverage calculation
        expected_records = len(NIFTY_500_STOCKS) * 6  # 6 durations
        coverage = (total_records / expected_records * 100) if expected_records > 0 else 0
        
        print(f"[*] Coverage: {coverage:.1f}% ({total_records}/{expected_records})")
        
        if coverage >= 80:
            print("[OK] Excellent Nifty 500 coverage!")
        elif coverage >= 50:
            print("[OK] Good Nifty 500 coverage")
        else:
            print("[WARN] Need more Nifty 500 data")
        
        return {
            'total_records': total_records,
            'expected_records': expected_records,
            'coverage_percentage': coverage,
            'duration_stats': dict(stats)
        }

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        get_nifty500_quick_stats()
    else:
        generate_nifty500_momentum_report()