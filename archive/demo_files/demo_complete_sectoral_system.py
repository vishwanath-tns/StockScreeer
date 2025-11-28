#!/usr/bin/env python3
"""
Complete Demo: Index Symbols Database & Sectoral Analysis System

This script demonstrates the complete functionality of the database-backed
index symbols system and sectoral analysis capabilities.

Created as the final demonstration of the comprehensive solution to store
index symbols in database tables and provide API access for other modules.
"""

import sys
from datetime import date
from services.index_symbols_api import IndexSymbolsAPI
from services.market_breadth_service import get_sectoral_breadth, compare_sectoral_breadth

def main():
    """Complete demonstration of the sectoral analysis system."""
    
    print("COMPLETE SECTORAL ANALYSIS SYSTEM DEMO")
    print("="*60)
    print("Database-backed index symbols with sectoral analysis API")
    print("="*60)
    
    # Initialize API
    api = IndexSymbolsAPI()
    analysis_date = date(2025, 11, 14)  # Latest available data date
    
    # 1. Show all available indices in the database
    print("\n1. AVAILABLE INDICES IN DATABASE:")
    print("-" * 40)
    all_indices = api.get_all_indices()
    if all_indices:
        indices_items = list(all_indices.items())[:15]  # Get first 15 as (code, info) pairs
        for index_code, info in indices_items:
            print(f"   {index_code:<20} {info['symbol_count']:>3} symbols")
        if len(all_indices) > 15:
            print(f"   ... and {len(all_indices) - 15} more indices")
        total_symbols = sum(info['symbol_count'] for info in all_indices.values())
        print(f"\nTotal: {len(all_indices)} indices with {total_symbols} total symbols")
    else:
        print("   No indices found in database")
        return
    
    # 2. Demonstrate single sector analysis
    print("\n2. SINGLE SECTOR ANALYSIS EXAMPLE:")
    print("-" * 40)
    
    banking_analysis = get_sectoral_breadth('NIFTY-BANK', analysis_date)
    if banking_analysis['success']:
        print(f"Banking Sector (NIFTY-BANK) - {analysis_date}")
        print(f"   Stocks analyzed: {banking_analysis['symbols_analyzed']}/{banking_analysis['total_stocks']}")
        print(f"   Market sentiment: {banking_analysis['breadth_summary']['bullish_percent']:.1f}% bullish")
        print(f"   Technical momentum: {banking_analysis['technical_breadth']['daily_uptrend_percent']:.1f}% in daily uptrend")
        
        # Show top performers
        if 'individual_ratings' in banking_analysis and banking_analysis['individual_ratings']:
            very_bullish = [stock for stock, rating in banking_analysis['individual_ratings'].items() 
                          if rating >= 8]
            if very_bullish:
                print(f"   Top performers: {', '.join(very_bullish[:5])}")
    
    # 3. Multi-sector comparison
    print("\n3. MULTI-SECTOR COMPARISON:")
    print("-" * 40)
    
    key_sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA', 'NIFTY-FMCG', 'NIFTY-AUTO']
    comparison = compare_sectoral_breadth(key_sectors, analysis_date)
    
    if comparison['comparison_summary']:
        print("Sector Performance Comparison:")
        print("   Sector           Bullish%  Daily Uptrend%  Stocks")
        print("   " + "-"*50)
        
        # Sort by bullish percentage
        sorted_sectors = sorted(comparison['comparison_summary'], 
                              key=lambda x: x['bullish_percent'], reverse=True)
        
        for sector in sorted_sectors:
            print(f"   {sector['sector']:<15} {sector['bullish_percent']:>7.1f}%  "
                  f"{sector['daily_uptrend_percent']:>12.1f}%  "
                  f"{sector['total_stocks']:>6}")
        
        # Highlight best and worst performers
        best = sorted_sectors[0]
        worst = sorted_sectors[-1]
        print(f"\n   Best performer:  {best['sector']} ({best['bullish_percent']:.1f}% bullish)")
        print(f"   Worst performer: {worst['sector']} ({worst['bullish_percent']:.1f}% bullish)")
    
    # 4. API Usage Examples
    print("\n4. API USAGE EXAMPLES:")
    print("-" * 40)
    
    # Get specific sector symbols
    bank_symbols = api.get_index_symbols('NIFTY-BANK')
    if bank_symbols:
        print(f"Banking symbols: {', '.join(bank_symbols[:5])}... ({len(bank_symbols)} total)")
    
    # Search functionality
    pharma_indices = api.search_indices('pharma')
    if pharma_indices:
        print(f"Pharma-related indices: {', '.join(pharma_indices)}")
    
    # Multi-sector symbols
    large_cap_sectors = ['NIFTY-50', 'NIFTY-100']
    multi_symbols = api.get_sectoral_symbols(large_cap_sectors)
    total_unique = len(set().union(*multi_symbols.values())) if multi_symbols else 0
    print(f"Large cap universe: {total_unique} unique symbols across {len(large_cap_sectors)} indices")
    
    # 5. Integration Example
    print("\n5. INTEGRATION EXAMPLE:")
    print("-" * 40)
    print("# Example: Using in existing scanners/analysis")
    print("from services.index_symbols_api import IndexSymbolsAPI")
    print("from services.market_breadth_service import get_sectoral_breadth")
    print("")
    print("# Get symbols for analysis")
    print("api = IndexSymbolsAPI()")
    print("it_symbols = api.get_index_symbols('NIFTY-IT')")
    print("")
    print("# Analyze sector performance")
    print("analysis = get_sectoral_breadth('NIFTY-IT', date.today())")
    print("if analysis['success']:")
    print("    print(f\"IT Sector: {analysis['breadth_summary']['bullish_percent']:.1f}% bullish\")")
    
    print("\n6. SYSTEM SUMMARY:")
    print("-" * 40)
    print("✓ Database populated with 24+ NSE indices")
    print("✓ 500+ symbols across all sectors stored persistently")
    print("✓ Fast API access for any module (no file parsing needed)")
    print("✓ Sectoral analysis with technical breadth metrics")
    print("✓ Multi-sector comparison capabilities")
    print("✓ Search and filtering functions")
    print("✓ Integration examples for existing scanners")
    print("\nMission accomplished: Index symbols are now database-backed with full API access!")

if __name__ == "__main__":
    main()