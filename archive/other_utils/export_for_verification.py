#!/usr/bin/env python3
"""
Export Sectoral Analysis Data for Manual Verification
Exports detailed data to Excel/CSV for easy manual verification.
"""

import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_breadth_service import get_engine

def export_sectoral_data_for_verification(analysis_date="2025-11-14", export_format="excel"):
    """Export detailed sectoral data for manual verification."""
    print(f"📊 EXPORTING SECTORAL DATA FOR VERIFICATION")
    print(f"📅 Analysis Date: {analysis_date}")
    print("=" * 60)
    
    try:
        engine = get_engine()
        
        # Query to get detailed sector analysis data
        detailed_query = """
        SELECT 
            n.index_name as sector,
            t.symbol,
            t.trend_rating,
            t.daily_trend,
            t.weekly_trend,
            t.close_price,
            t.sma_20,
            t.sma_50,
            CASE 
                WHEN t.trend_rating >= 3 THEN 'Bullish'
                ELSE 'Bearish' 
            END as trend_classification,
            CASE 
                WHEN t.close_price > t.sma_20 THEN 'Above SMA20'
                ELSE 'Below SMA20'
            END as price_vs_sma20,
            CASE 
                WHEN t.close_price > t.sma_50 THEN 'Above SMA50'
                ELSE 'Below SMA50'
            END as price_vs_sma50
        FROM trend_analysis t
        JOIN nse_index_constituents n ON t.symbol = n.symbol
        WHERE t.analysis_date = %s
        AND n.index_name IN (
            'NIFTY-PHARMA', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO',
            'NIFTY-FMCG', 'NIFTY-REALTY', 'NIFTY-METAL', 'NIFTY-ENERGY',
            'NIFTY-HEALTHCARE-INDEX', 'NIFTY-CONSUMER-DURABLES'
        )
        ORDER BY n.index_name, t.trend_rating DESC, t.symbol
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(detailed_query, conn, params=[analysis_date])
            
            if df.empty:
                print("❌ No data found for export")
                return False
            
            # Create summary statistics
            summary_df = df.groupby('sector').agg({
                'symbol': 'count',
                'trend_classification': lambda x: (x == 'Bullish').sum(),
                'trend_rating': 'mean'
            }).reset_index()
            
            summary_df.columns = ['Sector', 'Total_Stocks', 'Bullish_Count', 'Avg_Rating']
            summary_df['Bearish_Count'] = summary_df['Total_Stocks'] - summary_df['Bullish_Count']
            summary_df['Bullish_Percentage'] = (summary_df['Bullish_Count'] / summary_df['Total_Stocks'] * 100).round(1)
            summary_df['Bearish_Percentage'] = (summary_df['Bearish_Count'] / summary_df['Total_Stocks'] * 100).round(1)
            summary_df['Avg_Rating'] = summary_df['Avg_Rating'].round(2)
            
            # Sort by bullish percentage (highest first)
            summary_df = summary_df.sort_values('Bullish_Percentage', ascending=False)
            
            print(f"✅ Processed data for {len(df)} stocks across {len(summary_df)} sectors")
            
            # Export based on format
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format.lower() == "excel":
                filename = f"sectoral_verification_{analysis_date.replace('-', '')}_{timestamp}.xlsx"
                filepath = Path(filename)
                
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    # Summary sheet
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Detailed data by sector
                    for sector in df['sector'].unique():
                        sector_data = df[df['sector'] == sector].copy()
                        sheet_name = sector.replace('NIFTY-', '')[:31]  # Excel sheet name limit
                        sector_data.to_excel(writer, sheet_name=sheet_name, index=False)
                
                print(f"📁 Excel file exported: {filepath}")
                
            else:  # CSV format
                summary_filename = f"sectoral_summary_{analysis_date.replace('-', '')}_{timestamp}.csv"
                detail_filename = f"sectoral_details_{analysis_date.replace('-', '')}_{timestamp}.csv"
                
                summary_df.to_csv(summary_filename, index=False)
                df.to_csv(detail_filename, index=False)
                
                print(f"📁 CSV files exported:")
                print(f"   • Summary: {summary_filename}")
                print(f"   • Details: {detail_filename}")
            
            # Display summary for quick verification
            print(f"\n📊 SUMMARY FOR VERIFICATION:")
            print("=" * 80)
            print(f"{'Sector':<25} {'Stocks':<7} {'Bullish':<7} {'%':<6} {'Bearish':<7} {'%':<6} {'Avg Rating':<10}")
            print("-" * 80)
            
            for _, row in summary_df.iterrows():
                sector_short = row['Sector'].replace('NIFTY-', '')
                print(f"{sector_short:<25} {row['Total_Stocks']:<7} {row['Bullish_Count']:<7} {row['Bullish_Percentage']:<6.1f} {row['Bearish_Count']:<7} {row['Bearish_Percentage']:<6.1f} {row['Avg_Rating']:<10.2f}")
            
            # Quick math verification
            print(f"\n🧮 QUICK MATH VERIFICATION:")
            print("-" * 40)
            
            for _, row in summary_df.head(3).iterrows():  # Check top 3 sectors
                sector = row['Sector'].replace('NIFTY-', '')
                total = row['Total_Stocks']
                bullish = row['Bullish_Count']
                bearish = row['Bearish_Count']
                bullish_pct = row['Bullish_Percentage']
                
                # Manual calculation
                manual_pct = (bullish / total * 100) if total > 0 else 0
                count_check = (bullish + bearish == total)
                pct_check = abs(bullish_pct - manual_pct) < 0.1
                
                status = "✅" if count_check and pct_check else "❌"
                print(f"{status} {sector}: {bullish}/{total} = {manual_pct:.1f}% (reported: {bullish_pct:.1f}%)")
            
            print(f"\n✅ Export completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Export error: {e}")
        return False

def quick_export():
    """Quick export for current date."""
    print("🚀 QUICK SECTORAL DATA EXPORT")
    print("This will export your sectoral analysis data for manual verification")
    print()
    
    # Try both formats
    print("📊 Exporting to Excel format...")
    success_excel = export_sectoral_data_for_verification(analysis_date="2025-11-14", export_format="excel")
    
    if not success_excel:
        print("📊 Excel failed, trying CSV format...")
        success_csv = export_sectoral_data_for_verification(analysis_date="2025-11-14", export_format="csv")
        
        if success_csv:
            print("✅ CSV export successful - you can open these files in Excel")
        else:
            print("❌ Both export formats failed")
    else:
        print("✅ Excel export successful - open the .xlsx file for detailed verification")
    
    print(f"\n💡 HOW TO USE THE EXPORTED DATA:")
    print("1. Open the exported file in Excel")
    print("2. Check the 'Summary' sheet for overview")
    print("3. Verify percentages by dividing Bullish_Count by Total_Stocks")
    print("4. Check individual sector sheets for stock-by-stock details")
    print("5. Look for any inconsistencies or outliers")

if __name__ == "__main__":
    quick_export()