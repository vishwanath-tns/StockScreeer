#!/usr/bin/env python3
"""
Sectoral Analysis Integration Examples
====================================

Examples of how to integrate index symbols with your existing scanner functions
for comprehensive sectoral analysis.
"""

from get_index_symbols import get_index_symbols, get_sectoral_symbols

def sectoral_rsi_analysis():
    """
    Example: Run RSI analysis on all banking stocks
    """
    print("=== Banking Sector RSI Analysis ===")
    bank_symbols = get_index_symbols('NIFTY-BANK')
    
    if bank_symbols:
        print(f"Analyzing RSI for {len(bank_symbols)} banking stocks...")
        for symbol in bank_symbols:
            # You can integrate with your existing RSI scanner functions
            print(f"RSI Analysis for {symbol}")
            # Example: Call your rsi_scanner(symbol) function
            # rsi_value = get_rsi(symbol)
            # if rsi_value > 70:
            #     print(f"{symbol}: Overbought (RSI: {rsi_value})")

def sectoral_moving_average_trends():
    """
    Example: Analyze moving average trends across IT sector
    """
    print("\n=== IT Sector Moving Average Trends ===")
    it_symbols = get_index_symbols('NIFTY-IT')
    
    if it_symbols:
        print(f"Analyzing MA trends for {len(it_symbols)} IT stocks...")
        for symbol in it_symbols:
            # You can integrate with your existing MA scanner functions
            print(f"MA Trend Analysis for {symbol}")
            # Example: Call your moving_average_scanner(symbol)
            # ma_trend = get_ma_trend(symbol)
            # print(f"{symbol}: {ma_trend}")

def cross_sectoral_comparison():
    """
    Example: Compare performance across all sectors
    """
    print("\n=== Cross-Sectoral Performance Comparison ===")
    all_sectors = get_sectoral_symbols()
    
    for sector_name, symbols in all_sectors.items():
        print(f"\n{sector_name} Sector ({len(symbols)} stocks):")
        print(f"Symbols: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
        
        # Example sectoral analysis
        # strong_stocks = []
        # weak_stocks = []
        # for symbol in symbols:
        #     trend = analyze_trend(symbol)
        #     if trend == 'STRONG':
        #         strong_stocks.append(symbol)
        #     elif trend == 'WEAK':
        #         weak_stocks.append(symbol)
        # 
        # print(f"Strong stocks: {strong_stocks}")
        # print(f"Weak stocks: {weak_stocks}")

def sectoral_divergence_analysis():
    """
    Example: Look for RSI divergences within pharma sector
    """
    print("\n=== Pharma Sector Divergence Analysis ===")
    pharma_symbols = get_index_symbols('NIFTY-PHARMA')
    
    if pharma_symbols:
        print(f"Scanning for divergences in {len(pharma_symbols)} pharma stocks...")
        divergent_stocks = []
        
        for symbol in pharma_symbols:
            # You can integrate with your existing divergence scanner
            print(f"Checking divergences for {symbol}")
            # Example: 
            # if has_bullish_divergence(symbol):
            #     divergent_stocks.append(symbol)
        
        # print(f"Stocks showing bullish divergence: {divergent_stocks}")

def market_breadth_by_sector():
    """
    Example: Calculate market breadth metrics by sector
    """
    print("\n=== Market Breadth by Sector ===")
    all_sectors = get_sectoral_symbols()
    
    for sector_name, symbols in all_sectors.items():
        # Calculate breadth metrics
        # advancing = 0
        # declining = 0
        # 
        # for symbol in symbols:
        #     price_change = get_price_change(symbol)
        #     if price_change > 0:
        #         advancing += 1
        #     else:
        #         declining += 1
        # 
        # breadth_ratio = advancing / len(symbols) if len(symbols) > 0 else 0
        # print(f"{sector_name}: {advancing}/{len(symbols)} advancing ({breadth_ratio:.1%})")
        
        print(f"{sector_name}: Ready for breadth analysis ({len(symbols)} stocks)")

def integration_with_existing_scanners():
    """
    Show how to integrate with your existing scanner functions
    """
    print("\n=== Integration Examples ===")
    print("""
# 1. Banking Sector RSI Scanner
bank_symbols = get_index_symbols('NIFTY-BANK')
for symbol in bank_symbols:
    # Use your existing RSI functions
    rsi_result = your_rsi_scanner(symbol)
    if rsi_result['oversold']:
        print(f"Banking oversold opportunity: {symbol}")

# 2. IT Sector Trend Analysis  
it_symbols = get_index_symbols('NIFTY-IT')
for symbol in it_symbols:
    # Use your existing trend functions
    trend = your_trend_scanner(symbol) 
    if trend == 'STRONG_UPTREND':
        print(f"IT momentum stock: {symbol}")

# 3. Cross-sector relative strength
all_sectors = get_sectoral_symbols()
for sector, symbols in all_sectors.items():
    sector_strength = calculate_sector_strength(symbols)
    print(f"{sector} relative strength: {sector_strength}")

# 4. Pharma sector divergence hunt
pharma_symbols = get_index_symbols('NIFTY-PHARMA')
for symbol in pharma_symbols:
    if your_divergence_scanner(symbol):
        print(f"Pharma divergence found: {symbol}")
    """)

if __name__ == "__main__":
    # Run example analyses
    sectoral_rsi_analysis()
    sectoral_moving_average_trends()
    cross_sectoral_comparison()
    sectoral_divergence_analysis()
    market_breadth_by_sector()
    integration_with_existing_scanners()