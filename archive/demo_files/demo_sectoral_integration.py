"""
Sectoral Analysis Integration Demo
=================================

Demonstrates how to integrate index symbols API with existing scanners
for sectoral analysis and comparison.
"""

# Import the index symbols API
from services.index_symbols_api import (
    get_index_symbols, 
    get_sectoral_symbols, 
    get_all_bank_symbols,
    get_all_it_symbols,
    get_all_pharma_symbols,
    list_all_indices
)

def demo_sectoral_analysis():
    """
    Demonstrate sectoral analysis using index symbols
    """
    print("🔍 Sectoral Analysis Integration Demo")
    print("=" * 50)
    
    # 1. Basic sector symbol retrieval
    print("\n📈 1. Basic Sector Analysis:")
    
    bank_stocks = get_all_bank_symbols()
    it_stocks = get_all_it_symbols() 
    pharma_stocks = get_all_pharma_symbols()
    
    print(f"  Banking sector: {len(bank_stocks)} stocks")
    print(f"  IT sector: {len(it_stocks)} stocks") 
    print(f"  Pharma sector: {len(pharma_stocks)} stocks")
    
    # 2. Multi-sector comparison
    print("\n🔄 2. Multi-Sector Comparison:")
    
    sectors_to_analyze = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO', 'NIFTY-PHARMA', 'NIFTY-METAL']
    sectoral_data = get_sectoral_symbols(sectors_to_analyze)
    
    for sector, symbols in sectoral_data.items():
        print(f"  {sector:<25}: {len(symbols):>2} stocks")
    
    # 3. Integration examples with existing scanners
    print("\n🛠️  3. Integration Examples:")
    
    print("\n   Example 1: RSI Scanner for Banking Sector")
    print("   " + "-" * 40)
    banking_symbols = get_index_symbols('NIFTY-BANK')
    print(f"   # Run RSI scanner on {len(banking_symbols)} banking stocks")
    print(f"   symbols_to_scan = {banking_symbols[:5]}...  # {len(banking_symbols)} total")
    print("   # Your existing RSI scanner code here")
    print("   # for symbol in banking_symbols:")
    print("   #     rsi_data = calculate_rsi(symbol)")
    
    print("\n   Example 2: Moving Average Scanner for IT Sector")
    print("   " + "-" * 40)
    it_symbols = get_index_symbols('NIFTY-IT')
    print(f"   # Run SMA scanner on {len(it_symbols)} IT stocks")
    print(f"   it_symbols = {it_symbols[:3]}...  # {len(it_symbols)} total")
    print("   # Your existing SMA scanner code here")
    
    print("\n   Example 3: Compare Sectors Performance")
    print("   " + "-" * 40)
    comparison_sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA']
    sector_symbols = get_sectoral_symbols(comparison_sectors)
    
    print("   # Sectoral performance comparison")
    print("   sector_performance = {}")
    print("   for sector, symbols in sector_symbols.items():")
    print("       # Calculate average performance for each sector")
    print("       print(f'   {sector}: {len(symbols)} stocks')")
    
    # 4. Available indices for analysis
    print(f"\n📋 4. Available Indices for Analysis:")
    
    all_indices = list_all_indices()
    sectoral_indices = {k: v for k, v in all_indices.items() if v['category'] == 'SECTORAL'}
    
    print(f"   Total indices available: {len(all_indices)}")
    print(f"   Sectoral indices: {len(sectoral_indices)}")
    print(f"\n   Top sectoral indices by stock count:")
    
    # Sort by symbol count and show top 10
    sorted_sectoral = sorted(sectoral_indices.items(), key=lambda x: x[1]['symbol_count'], reverse=True)
    for i, (code, info) in enumerate(sorted_sectoral[:10]):
        print(f"     {i+1:>2}. {code:<30} {info['symbol_count']:>3} stocks")

def integration_code_examples():
    """
    Show actual code examples for integration
    """
    print("\n" + "=" * 50)
    print("💻 INTEGRATION CODE EXAMPLES")
    print("=" * 50)
    
    print("""
# Example 1: Add sectoral filtering to existing RSI scanner
from services.index_symbols_api import get_index_symbols

def scan_rsi_by_sector(sector_code, rsi_threshold=70):
    \"\"\"
    Run RSI scan on specific sector
    \"\"\"
    symbols = get_index_symbols(sector_code)
    print(f"Scanning {len(symbols)} {sector_code} stocks for RSI > {rsi_threshold}")
    
    # Your existing RSI scanning code
    results = []
    for symbol in symbols:
        # rsi_value = calculate_rsi(symbol)  # Your existing function
        # if rsi_value > rsi_threshold:
        #     results.append((symbol, rsi_value))
        pass
    
    return results

# Usage
banking_rsi_alerts = scan_rsi_by_sector('NIFTY-BANK', 70)
it_rsi_alerts = scan_rsi_by_sector('NIFTY-IT', 70)
    """)
    
    print("""
# Example 2: Sectoral breadth analysis
from services.index_symbols_api import get_sectoral_symbols

def analyze_sectoral_breadth():
    \"\"\"
    Analyze breadth across different sectors
    \"\"\"
    sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO', 'NIFTY-PHARMA']
    sectoral_data = get_sectoral_symbols(sectors)
    
    breadth_data = {}
    for sector, symbols in sectoral_data.items():
        # Count how many stocks are above/below moving averages
        above_sma = 0
        total = len(symbols)
        
        for symbol in symbols:
            # Your existing analysis code
            # if stock_above_sma50(symbol):
            #     above_sma += 1
            pass
        
        breadth_data[sector] = {
            'above_sma_pct': (above_sma / total) * 100,
            'total_stocks': total
        }
    
    return breadth_data
    """)
    
    print("""
# Example 3: Update market_breadth_service.py
# Add this to your existing market breadth service:

from services.index_symbols_api import get_index_symbols

def get_sectoral_breadth(sector_code):
    \"\"\"
    Get market breadth for specific sector
    \"\"\"
    symbols = get_index_symbols(sector_code)
    
    # Use your existing breadth calculation logic
    # but filter to just this sector's symbols
    breadth_data = calculate_breadth_for_symbols(symbols)
    
    return {
        'sector': sector_code,
        'total_stocks': len(symbols),
        'breadth_data': breadth_data
    }
    """)

if __name__ == "__main__":
    demo_sectoral_analysis()
    integration_code_examples()
    
    print(f"\n🎯 READY FOR SECTORAL ANALYSIS!")
    print(f"   ✅ Database populated with {sum(len(get_index_symbols(code)) for code in ['NIFTY-50', 'NIFTY-BANK', 'NIFTY-IT'])} symbols across major indices")
    print(f"   ✅ API ready for import: from services.index_symbols_api import get_index_symbols")
    print(f"   ✅ Integration examples provided above")
    print(f"   ✅ No need to read CSV files anymore - everything is in database!")