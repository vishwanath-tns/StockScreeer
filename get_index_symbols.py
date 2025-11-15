#!/usr/bin/env python3
"""
Index Symbol Extractor for Sectoral Analysis
============================================

This script extracts all symbols from NSE index CSV files for sectoral analysis.
Perfect for running technical analysis on specific sectors.
"""

import sys
import os
from pathlib import Path

# Add the indices_manager to path
sys.path.append('.')

from indices_manager.parser import NSEIndicesParser

def get_index_symbols(index_name):
    """
    Get all symbols from a specific index
    
    Args:
        index_name: Index name like 'NIFTY-50', 'NIFTY-BANK', etc.
        
    Returns:
        List of symbols or None if error
    """
    parser = NSEIndicesParser()
    
    # Map index names to file names
    filename = f"MW-{index_name}-15-Nov-2025.csv"
    file_path = f"indices/{filename}"
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {filename}")
        return None
    
    try:
        index_data, constituents = parser.parse_csv_file(file_path)
        symbols = [const.symbol for const in constituents]
        
        print(f"Index: {index_name}")
        print(f"Index Value: {index_data.close_value}")
        print(f"Constituents: {len(symbols)}")
        print(f"Symbols: {symbols}")
        print("-" * 60)
        
        return symbols
        
    except Exception as e:
        print(f"Error parsing {index_name}: {e}")
        return None

def get_sectoral_symbols():
    """
    Get symbols for major sectors for comparative analysis
    """
    sectors = {
        'Banking': 'NIFTY-BANK',
        'IT': 'NIFTY-IT', 
        'Pharma': 'NIFTY-PHARMA',
        'Auto': 'NIFTY-AUTO',
        'FMCG': 'NIFTY-FMCG',
        'Metal': 'NIFTY-METAL',
        'Realty': 'NIFTY-REALTY'
    }
    
    sectoral_data = {}
    
    print("=== Extracting Sectoral Symbols ===")
    for sector, index_code in sectors.items():
        symbols = get_index_symbols(index_code)
        if symbols:
            sectoral_data[sector] = symbols
    
    return sectoral_data

def demo_usage():
    """
    Demonstrate how to use the extracted symbols for analysis
    """
    print("\n=== Usage Examples ===")
    print("# Get banking sector symbols")
    print("bank_symbols = get_index_symbols('NIFTY-BANK')")
    print("# Run RSI analysis on all bank stocks")
    print("for symbol in bank_symbols:")
    print("    # Run your existing scanner functions")
    print("    pass")
    print()
    
    print("# Get IT sector for trend analysis")
    print("it_symbols = get_index_symbols('NIFTY-IT')")
    print("# Compare moving averages across IT sector")
    print()
    
    print("# Get all sectors for market breadth analysis")
    print("all_sectors = get_sectoral_symbols()")
    print("# Compare sector performance")

if __name__ == "__main__":
    # Test with popular indices
    print("=== Testing Index Symbol Extraction ===")
    
    # Test NIFTY-50
    nifty50_symbols = get_index_symbols("NIFTY-50")
    
    # Test Banking sector
    bank_symbols = get_index_symbols("NIFTY-BANK")
    
    # Test IT sector  
    it_symbols = get_index_symbols("NIFTY-IT")
    
    # Get all sectoral data
    sectoral_data = get_sectoral_symbols()
    
    print("\n=== Summary ===")
    print(f"NIFTY-50: {len(nifty50_symbols) if nifty50_symbols else 0} stocks")
    print(f"Banking: {len(bank_symbols) if bank_symbols else 0} stocks")
    print(f"IT: {len(it_symbols) if it_symbols else 0} stocks")
    print(f"Total sectors extracted: {len(sectoral_data)}")
    
    demo_usage()