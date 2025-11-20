"""
Nifty 50 Stock Selection Strategy
===============================

This module analyzes momentum data across timeframes to provide specific
stock recommendations for different trading/investment strategies.
"""

import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append('.')

from services.market_breadth_service import get_engine
from sqlalchemy import text

def analyze_stock_selection_strategies():
    """Analyze stocks for different trading strategies based on momentum patterns"""
    
    print("NIFTY 50 STOCK SELECTION STRATEGY ANALYZER")
    print("=" * 55)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Load the complete momentum data
    csv_file = "reports/nifty50_all_durations_complete_20251118_091514.csv"
    
    try:
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded momentum data for {len(df)} stocks")
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    # Convert momentum columns to numeric
    momentum_cols = ['Momentum_1W_Percent', 'Momentum_1M_Percent', 'Momentum_3M_Percent', 
                    'Momentum_6M_Percent', 'Momentum_9M_Percent', 'Momentum_12M_Percent']
    
    for col in momentum_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Also convert volume surge columns
    df['Volume_Surge_1W'] = pd.to_numeric(df['Volume_Surge_1W'], errors='coerce')
    df['Volume_Surge_1M'] = pd.to_numeric(df['Volume_Surge_1M'], errors='coerce')
    
    print("")
    print("🎯 STOCK SELECTION STRATEGIES")
    print("=" * 35)
    print("")
    
    # 1. SHORT-TERM TRADING (1-7 days)
    print("1️⃣  SHORT-TERM TRADING (1-7 Days)")
    print("-" * 40)
    print("Strategy: Momentum + Volume breakouts")
    print("Criteria:")
    print("  • Strong 1W momentum (>2%)")
    print("  • High volume surge (>1.5x)")
    print("  • Positive 1M momentum for confirmation")
    print("")
    
    short_term_criteria = (
        (df['Momentum_1W_Percent'] > 2.0) &
        (df['Volume_Surge_1W'] > 1.5) &
        (df['Momentum_1M_Percent'] > 0)
    )
    
    short_term_stocks = df[short_term_criteria].copy()
    short_term_stocks = short_term_stocks.sort_values('Momentum_1W_Percent', ascending=False)
    
    print(f"📊 SHORT-TERM CANDIDATES ({len(short_term_stocks)} stocks):")
    print("-" * 25)
    
    if len(short_term_stocks) > 0:
        for i, (_, row) in enumerate(short_term_stocks.head(8).iterrows(), 1):
            symbol = row['Symbol']
            sector = row['Sector']
            mom_1w = row['Momentum_1W_Percent']
            mom_1m = row['Momentum_1M_Percent']
            vol_surge = row['Volume_Surge_1W']
            
            print(f"{i:2}. {symbol:12} | 1W: {mom_1w:+6.2f}% | 1M: {mom_1m:+6.2f}% | Vol: {vol_surge:4.1f}x | {sector}")
        
        print(f"\n💡 Short-term strategy notes:")
        print(f"   - Focus on stocks showing immediate momentum")
        print(f"   - Use tight stop-losses (2-3%)")
        print(f"   - Target quick 3-5% gains")
        print(f"   - Monitor volume closely for exit signals")
    else:
        print("No stocks meet short-term criteria today")
    
    print("")
    
    # 2. SWING TRADING (1-4 weeks)
    print("2️⃣  SWING TRADING (1-4 Weeks)")
    print("-" * 35)
    print("Strategy: Multi-timeframe momentum alignment")
    print("Criteria:")
    print("  • Positive 1W and 1M momentum")
    print("  • Strong 3M momentum (>5%)")
    print("  • Reasonable volume activity")
    print("")
    
    swing_criteria = (
        (df['Momentum_1W_Percent'] > 0) &
        (df['Momentum_1M_Percent'] > 0) &
        (df['Momentum_3M_Percent'] > 5.0) &
        (df['Volume_Surge_1M'] > 0.8)
    )
    
    swing_stocks = df[swing_criteria].copy()
    # Create swing score based on momentum alignment
    swing_stocks['Swing_Score'] = (
        swing_stocks['Momentum_1W_Percent'] * 0.2 +
        swing_stocks['Momentum_1M_Percent'] * 0.3 +
        swing_stocks['Momentum_3M_Percent'] * 0.5
    )
    swing_stocks = swing_stocks.sort_values('Swing_Score', ascending=False)
    
    print(f"📊 SWING TRADING CANDIDATES ({len(swing_stocks)} stocks):")
    print("-" * 30)
    
    if len(swing_stocks) > 0:
        for i, (_, row) in enumerate(swing_stocks.head(10).iterrows(), 1):
            symbol = row['Symbol']
            sector = row['Sector']
            mom_1w = row['Momentum_1W_Percent']
            mom_1m = row['Momentum_1M_Percent']
            mom_3m = row['Momentum_3M_Percent']
            swing_score = row['Swing_Score']
            
            print(f"{i:2}. {symbol:12} | Score: {swing_score:5.1f} | 1W: {mom_1w:+5.1f}% | 1M: {mom_1m:+5.1f}% | 3M: {mom_3m:+5.1f}% | {sector}")
        
        print(f"\n💡 Swing trading strategy notes:")
        print(f"   - Hold for 1-4 weeks typically")
        print(f"   - Use 5-8% stop-losses")
        print(f"   - Target 10-20% gains")
        print(f"   - Monitor weekly momentum shifts")
    else:
        print("No stocks meet swing trading criteria today")
    
    print("")
    
    # 3. LONG-TERM INVESTMENT (3+ months)
    print("3️⃣  LONG-TERM INVESTMENT (3+ Months)")
    print("-" * 40)
    print("Strategy: Sustained momentum + Quality sectors")
    print("Criteria:")
    print("  • Strong 6M and 12M momentum")
    print("  • Consistent positive momentum across timeframes")
    print("  • Quality sectors (Banking, IT, FMCG, Pharma)")
    print("")
    
    quality_sectors = ['Banking', 'IT Services', 'FMCG', 'Pharmaceuticals', 'Financial Services']
    
    investment_criteria = (
        (df['Momentum_6M_Percent'] > 3.0) &
        (df['Momentum_12M_Percent'] > 0) &
        (df['Momentum_3M_Percent'] > 0) &
        (df['Sector'].isin(quality_sectors))
    )
    
    investment_stocks = df[investment_criteria].copy()
    
    # Create investment score based on longer-term momentum
    investment_stocks['Investment_Score'] = (
        investment_stocks['Momentum_3M_Percent'] * 0.2 +
        investment_stocks['Momentum_6M_Percent'] * 0.4 +
        investment_stocks['Momentum_12M_Percent'] * 0.4
    )
    investment_stocks = investment_stocks.sort_values('Investment_Score', ascending=False)
    
    print(f"📊 LONG-TERM INVESTMENT CANDIDATES ({len(investment_stocks)} stocks):")
    print("-" * 40)
    
    if len(investment_stocks) > 0:
        for i, (_, row) in enumerate(investment_stocks.head(10).iterrows(), 1):
            symbol = row['Symbol']
            sector = row['Sector']
            mom_3m = row['Momentum_3M_Percent']
            mom_6m = row['Momentum_6M_Percent']
            mom_12m = row['Momentum_12M_Percent']
            inv_score = row['Investment_Score']
            
            print(f"{i:2}. {symbol:12} | Score: {inv_score:5.1f} | 3M: {mom_3m:+5.1f}% | 6M: {mom_6m:+5.1f}% | 12M: {mom_12m:+5.1f}% | {sector}")
        
        print(f"\n💡 Long-term investment strategy notes:")
        print(f"   - Hold for 6+ months")
        print(f"   - Use 15-20% stop-losses")
        print(f"   - Focus on business fundamentals too")
        print(f"   - Dollar-cost averaging on dips")
    else:
        print("No stocks meet long-term investment criteria today")
    
    print("")
    
    # 4. SPECIAL SITUATIONS
    print("4️⃣  SPECIAL SITUATIONS")
    print("-" * 25)
    
    # Momentum Reversal Candidates (for contrarian plays)
    print("📈 MOMENTUM REVERSAL CANDIDATES:")
    print("   (Stocks showing recent weakness but strong long-term momentum)")
    
    reversal_criteria = (
        (df['Momentum_1W_Percent'] < 0) &
        (df['Momentum_1M_Percent'] < 2) &
        (df['Momentum_6M_Percent'] > 10)
    )
    
    reversal_stocks = df[reversal_criteria].sort_values('Momentum_6M_Percent', ascending=False)
    
    if len(reversal_stocks) > 0:
        for i, (_, row) in enumerate(reversal_stocks.head(5).iterrows(), 1):
            symbol = row['Symbol']
            sector = row['Sector']
            mom_1w = row['Momentum_1W_Percent']
            mom_1m = row['Momentum_1M_Percent']
            mom_6m = row['Momentum_6M_Percent']
            
            print(f"   {i}. {symbol:12} | 1W: {mom_1w:+5.1f}% | 1M: {mom_1m:+5.1f}% | 6M: {mom_6m:+5.1f}% | {sector}")
    
    print("")
    
    # Breakout Candidates
    print("🚀 BREAKOUT CANDIDATES:")
    print("   (Stocks showing acceleration across timeframes)")
    
    breakout_criteria = (
        (df['Momentum_1W_Percent'] > df['Momentum_1M_Percent']) &
        (df['Momentum_1M_Percent'] > 0) &
        (df['Volume_Surge_1W'] > 1.2)
    )
    
    breakout_stocks = df[breakout_criteria].sort_values('Momentum_1W_Percent', ascending=False)
    
    if len(breakout_stocks) > 0:
        for i, (_, row) in enumerate(breakout_stocks.head(5).iterrows(), 1):
            symbol = row['Symbol']
            sector = row['Sector']
            mom_1w = row['Momentum_1W_Percent']
            mom_1m = row['Momentum_1M_Percent']
            vol_surge = row['Volume_Surge_1W']
            
            print(f"   {i}. {symbol:12} | 1W: {mom_1w:+5.1f}% | 1M: {mom_1m:+5.1f}% | Vol: {vol_surge:4.1f}x | {sector}")
    
    print("")
    
    # 5. SECTOR ROTATION OPPORTUNITIES
    print("5️⃣  SECTOR ROTATION ANALYSIS")
    print("-" * 30)
    
    # Calculate sector performance
    sector_performance = df.groupby('Sector').agg({
        'Momentum_1M_Percent': 'mean',
        'Momentum_3M_Percent': 'mean',
        'Momentum_6M_Percent': 'mean',
        'Symbol': 'count'
    }).round(2)
    
    sector_performance.columns = ['1M_Avg', '3M_Avg', '6M_Avg', 'Stock_Count']
    sector_performance = sector_performance.sort_values('1M_Avg', ascending=False)
    
    print("📊 SECTOR MOMENTUM RANKING (1M Average):")
    for i, (sector, row) in enumerate(sector_performance.head(8).iterrows(), 1):
        print(f"   {i:2}. {sector:20} | 1M: {row['1M_Avg']:+6.2f}% | 3M: {row['3M_Avg']:+6.2f}% | 6M: {row['6M_Avg']:+6.2f}%")
    
    print("")
    
    # 6. RISK MANAGEMENT GUIDELINES
    print("6️⃣  RISK MANAGEMENT GUIDELINES")
    print("-" * 35)
    print("🛡️  Position Sizing:")
    print("   • Short-term: 2-3% of portfolio per trade")
    print("   • Swing: 5-8% of portfolio per position")
    print("   • Long-term: 10-15% of portfolio per stock")
    print("")
    print("🎯 Stop-Loss Guidelines:")
    print("   • Short-term: 2-3% stop-loss")
    print("   • Swing: 5-8% stop-loss")
    print("   • Long-term: 15-20% stop-loss")
    print("")
    print("⚖️  Diversification:")
    print("   • Max 3-4 positions in same sector")
    print("   • Balance growth vs defensive sectors")
    print("   • Monitor correlation between positions")
    
    # Generate summary report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = f"reports/stock_selection_strategy_{timestamp}.txt"
    
    with open(summary_file, 'w') as f:
        f.write("NIFTY 50 STOCK SELECTION STRATEGY REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("SHORT-TERM TRADING CANDIDATES:\n")
        f.write("-" * 30 + "\n")
        for _, row in short_term_stocks.head(10).iterrows():
            f.write(f"{row['Symbol']:12} | {row['Sector']:20} | 1W: {row['Momentum_1W_Percent']:+6.2f}%\n")
        
        f.write("\nSWING TRADING CANDIDATES:\n")
        f.write("-" * 25 + "\n")
        for _, row in swing_stocks.head(10).iterrows():
            f.write(f"{row['Symbol']:12} | {row['Sector']:20} | Score: {row['Swing_Score']:5.1f}\n")
        
        f.write("\nLONG-TERM INVESTMENT CANDIDATES:\n")
        f.write("-" * 32 + "\n")
        for _, row in investment_stocks.head(10).iterrows():
            f.write(f"{row['Symbol']:12} | {row['Sector']:20} | Score: {row['Investment_Score']:5.1f}\n")
    
    print(f"\n📄 Strategy report saved: {summary_file}")
    print(f"\n🎉 STOCK SELECTION ANALYSIS COMPLETE!")
    print("    Use this analysis as a starting point for your trading decisions.")
    print("    Always combine with technical analysis and fundamental research!")


if __name__ == "__main__":
    analyze_stock_selection_strategies()