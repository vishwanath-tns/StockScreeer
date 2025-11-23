#!/usr/bin/env python3
"""
Analyze Nifty 50 Performance by Zodiac Sign
Shows how Nifty performs when Sun is in each zodiac sign, year by year
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sync_bhav_gui import engine
from sqlalchemy import text
import pandas as pd
from datetime import datetime
import numpy as np

def analyze_zodiac_performance():
    """Analyze Nifty performance during each Sun zodiac sign"""
    
    print("=" * 80)
    print("NIFTY 50 PERFORMANCE BY SUN ZODIAC SIGN ANALYSIS")
    print("Vedic Astrology Correlation Study")
    print("=" * 80)
    print()
    
    conn = engine().connect()
    
    # Get Nifty data with Sun positions
    query = text("""
        SELECT 
            n.date,
            n.open,
            n.close,
            n.high,
            n.low,
            YEAR(n.date) as year,
            p.sun_sign,
            p.sun_longitude,
            p.sun_degree
        FROM yfinance_daily_quotes n
        INNER JOIN (
            SELECT DATE(timestamp) as date,
                   sun_sign,
                   AVG(sun_longitude) as sun_longitude,
                   AVG(sun_degree) as sun_degree
            FROM planetary_positions
            WHERE HOUR(timestamp) = 9 
            AND MINUTE(timestamp) = 15
            AND DAYOFWEEK(timestamp) NOT IN (1, 7)
            GROUP BY DATE(timestamp), sun_sign
        ) p ON n.date = p.date
        WHERE n.symbol = 'NIFTY'
        AND n.date >= '2023-01-01'
        ORDER BY n.date
    """)
    
    result = conn.execute(query)
    rows = result.fetchall()
    
    if not rows:
        print("No data found!")
        conn.close()
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=[
        'date', 'open', 'close', 'high', 'low', 'year', 
        'sun_sign', 'sun_longitude', 'sun_degree'
    ])
    
    # Convert Decimal to float
    for col in ['open', 'close', 'high', 'low', 'sun_longitude', 'sun_degree']:
        df[col] = df[col].astype(float)
    
    # Calculate daily returns
    df['daily_return'] = ((df['close'] - df['open']) / df['open']) * 100
    df['intraday_range'] = ((df['high'] - df['low']) / df['open']) * 100
    
    print(f"Analyzed {len(df)} trading days from {df['date'].min()} to {df['date'].max()}")
    print(f"Years covered: {sorted(df['year'].unique())}")
    print()
    
    # Define zodiac order
    zodiac_order = [
        'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ]
    
    print("-" * 80)
    print("OVERALL PERFORMANCE BY ZODIAC SIGN (All Years Combined)")
    print("-" * 80)
    print()
    
    # Overall analysis by zodiac sign
    overall_stats = []
    for sign in zodiac_order:
        sign_data = df[df['sun_sign'] == sign]
        
        if len(sign_data) > 0:
            avg_return = sign_data['daily_return'].mean()
            median_return = sign_data['daily_return'].median()
            total_return = sign_data['daily_return'].sum()
            positive_days = (sign_data['daily_return'] > 0).sum()
            negative_days = (sign_data['daily_return'] < 0).sum()
            win_rate = (positive_days / len(sign_data)) * 100
            avg_volatility = sign_data['intraday_range'].mean()
            num_days = len(sign_data)
            
            overall_stats.append({
                'Sign': sign,
                'Days': num_days,
                'Avg Return %': avg_return,
                'Median Return %': median_return,
                'Total Return %': total_return,
                'Win Rate %': win_rate,
                'Positive Days': positive_days,
                'Negative Days': negative_days,
                'Avg Volatility %': avg_volatility
            })
    
    overall_df = pd.DataFrame(overall_stats)
    
    # Display overall statistics
    print(f"{'Sign':<12} {'Days':>5} {'Avg Ret%':>9} {'Total%':>9} {'Win%':>6} {'+Days':>6} {'-Days':>6} {'Vol%':>6}")
    print("-" * 80)
    for _, row in overall_df.iterrows():
        print(f"{row['Sign']:<12} {row['Days']:>5} "
              f"{row['Avg Return %']:>8.3f}% {row['Total Return %']:>8.2f}% "
              f"{row['Win Rate %']:>5.1f}% {row['Positive Days']:>6} {row['Negative Days']:>6} "
              f"{row['Avg Volatility %']:>5.2f}%")
    
    print()
    print("-" * 80)
    print("YEAR-WISE PERFORMANCE BY ZODIAC SIGN")
    print("-" * 80)
    print()
    
    # Year-wise analysis
    years = sorted(df['year'].unique())
    
    for year in years:
        print(f"\n{'='*80}")
        print(f"YEAR {year}")
        print(f"{'='*80}\n")
        
        year_data = df[df['year'] == year]
        year_stats = []
        
        for sign in zodiac_order:
            sign_data = year_data[year_data['sun_sign'] == sign]
            
            if len(sign_data) > 0:
                avg_return = sign_data['daily_return'].mean()
                total_return = sign_data['daily_return'].sum()
                positive_days = (sign_data['daily_return'] > 0).sum()
                negative_days = (sign_data['daily_return'] < 0).sum()
                win_rate = (positive_days / len(sign_data)) * 100
                num_days = len(sign_data)
                
                # Calculate period return (first to last close)
                period_return = ((sign_data.iloc[-1]['close'] - sign_data.iloc[0]['open']) / 
                               sign_data.iloc[0]['open']) * 100
                
                year_stats.append({
                    'Sign': sign,
                    'Days': num_days,
                    'Avg Daily %': avg_return,
                    'Total %': total_return,
                    'Period %': period_return,
                    'Win Rate %': win_rate,
                    '+/-': f"{positive_days}/{negative_days}"
                })
        
        year_df = pd.DataFrame(year_stats)
        
        print(f"{'Sign':<12} {'Days':>5} {'Avg Daily':>10} {'Total':>9} {'Period':>9} {'Win%':>6} {'+/-':>8}")
        print("-" * 80)
        for _, row in year_df.iterrows():
            print(f"{row['Sign']:<12} {row['Days']:>5} "
                  f"{row['Avg Daily %']:>9.3f}% {row['Total %']:>8.2f}% "
                  f"{row['Period %']:>8.2f}% {row['Win Rate %']:>5.1f}% {row['+/-']:>8}")
    
    print()
    print("=" * 80)
    print("RANKING: BEST TO WORST ZODIAC SIGNS (By Average Daily Return)")
    print("=" * 80)
    print()
    
    # Rank by average return
    ranked = overall_df.sort_values('Avg Return %', ascending=False)
    print(f"{'Rank':>4} {'Sign':<12} {'Avg Daily Return':>16} {'Win Rate':>10} {'Days':>6}")
    print("-" * 80)
    for i, (_, row) in enumerate(ranked.iterrows(), 1):
        emoji = "🟢" if row['Avg Return %'] > 0 else "🔴"
        print(f"{i:>4}. {row['Sign']:<12} {emoji} {row['Avg Return %']:>13.3f}% "
              f"{row['Win Rate %']:>8.1f}% {row['Days']:>6}")
    
    print()
    print("=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print()
    
    # Generate insights
    best_sign = ranked.iloc[0]
    worst_sign = ranked.iloc[-1]
    most_volatile = overall_df.loc[overall_df['Avg Volatility %'].idxmax()]
    least_volatile = overall_df.loc[overall_df['Avg Volatility %'].idxmin()]
    
    print(f"✨ BEST PERFORMING SIGN:")
    print(f"   {best_sign['Sign']} - Average Return: {best_sign['Avg Return %']:.3f}% per day")
    print(f"   Win Rate: {best_sign['Win Rate %']:.1f}% | {best_sign['Days']} trading days")
    print()
    
    print(f"⚠️  WORST PERFORMING SIGN:")
    print(f"   {worst_sign['Sign']} - Average Return: {worst_sign['Avg Return %']:.3f}% per day")
    print(f"   Win Rate: {worst_sign['Win Rate %']:.1f}% | {worst_sign['Days']} trading days")
    print()
    
    print(f"📊 MOST VOLATILE SIGN:")
    print(f"   {most_volatile['Sign']} - Average Intraday Range: {most_volatile['Avg Volatility %']:.2f}%")
    print()
    
    print(f"🔒 LEAST VOLATILE SIGN:")
    print(f"   {least_volatile['Sign']} - Average Intraday Range: {least_volatile['Avg Volatility %']:.2f}%")
    print()
    
    # Element analysis
    print("=" * 80)
    print("ELEMENT-WISE ANALYSIS (Vedic Astrology)")
    print("=" * 80)
    print()
    
    elements = {
        'Fire': ['Aries', 'Leo', 'Sagittarius'],
        'Earth': ['Taurus', 'Virgo', 'Capricorn'],
        'Air': ['Gemini', 'Libra', 'Aquarius'],
        'Water': ['Cancer', 'Scorpio', 'Pisces']
    }
    
    for element, signs in elements.items():
        element_data = df[df['sun_sign'].isin(signs)]
        if len(element_data) > 0:
            avg_return = element_data['daily_return'].mean()
            win_rate = (element_data['daily_return'] > 0).sum() / len(element_data) * 100
            volatility = element_data['intraday_range'].mean()
            
            print(f"{element:>8} Signs ({', '.join(signs)}):")
            print(f"          Avg Return: {avg_return:>7.3f}% | Win Rate: {win_rate:>5.1f}% | Volatility: {volatility:.2f}%")
            print()
    
    # Quality analysis
    print("=" * 80)
    print("QUALITY-WISE ANALYSIS (Cardinal, Fixed, Mutable)")
    print("=" * 80)
    print()
    
    qualities = {
        'Cardinal': ['Aries', 'Cancer', 'Libra', 'Capricorn'],  # Initiating energy
        'Fixed': ['Taurus', 'Leo', 'Scorpio', 'Aquarius'],      # Sustaining energy
        'Mutable': ['Gemini', 'Virgo', 'Sagittarius', 'Pisces'] # Changing energy
    }
    
    for quality, signs in qualities.items():
        quality_data = df[df['sun_sign'].isin(signs)]
        if len(quality_data) > 0:
            avg_return = quality_data['daily_return'].mean()
            win_rate = (quality_data['daily_return'] > 0).sum() / len(quality_data) * 100
            volatility = quality_data['intraday_range'].mean()
            
            print(f"{quality:>8} Signs ({', '.join(signs)}):")
            print(f"          Avg Return: {avg_return:>7.3f}% | Win Rate: {win_rate:>5.1f}% | Volatility: {volatility:.2f}%")
            print()
    
    conn.close()
    
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    analyze_zodiac_performance()
