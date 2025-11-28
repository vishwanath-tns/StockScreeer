#!/usr/bin/env python3
"""
Discover all NSE Indices available on Yahoo Finance
Tests comprehensive list of NSE indices including sectoral, thematic, and strategy indices
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# Comprehensive list of NSE indices with their Yahoo Finance symbols
NSE_INDICES = {
    # ========== BROAD MARKET INDICES ==========
    "Nifty 50": "^NSEI",
    "Nifty Next 50": "^NSMIDCP",
    "Nifty 100": "NIFTY_100.NS",
    "Nifty 200": "NIFTY_200.NS",
    "Nifty 500": "NIFTY_500.NS",
    "Nifty Midcap 50": "NIFTY_MIDCAP_50.NS",
    "Nifty Midcap 100": "^CNXMIDCAP",
    "Nifty Midcap 150": "NIFTY_MIDCAP_150.NS",
    "Nifty Smallcap 50": "NIFTY_SMLCAP_50.NS",
    "Nifty Smallcap 100": "^CNXSMALLCAP",
    "Nifty Smallcap 250": "NIFTY_SMLCAP_250.NS",
    "Nifty Microcap 250": "NIFTY_MICROCAP250.NS",
    "Nifty LargeMidcap 250": "NIFTY_LARGEMID250.NS",
    
    # ========== SECTORAL INDICES ==========
    "Nifty Auto": "^CNXAUTO",
    "Nifty Bank": "^NSEBANK",
    "Nifty Financial Services": "NIFTY_FIN_SERVICE.NS",
    "Nifty Financial Services 25/50": "NIFTYFINSERVICE25.NS",
    "Nifty FMCG": "^CNXFMCG",
    "Nifty IT": "^CNXIT",
    "Nifty Media": "NIFTY_MEDIA.NS",
    "Nifty Metal": "^CNXMETAL",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty PSU Bank": "^CNXPSUBANK",
    "Nifty Private Bank": "NIFTY_PVT_BANK.NS",
    "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Infrastructure": "^CNXINFRA",
    "Nifty Commodities": "NIFTY_COMMODITIES.NS",
    "Nifty Consumption": "NIFTY_CONSUMPTION.NS",
    "Nifty CPSE": "NIFTY_CPSE.NS",
    "Nifty MNC": "NIFTY_MNC.NS",
    "Nifty PSE": "NIFTY_PSE.NS",
    "Nifty Services Sector": "NIFTY_SERV_SECTOR.NS",
    
    # ========== OIL & GAS ==========
    "Nifty Oil & Gas": "NIFTY_OIL_AND_GAS.NS",
    
    # ========== HEALTHCARE ==========
    "Nifty Healthcare Index": "NIFTY_HEALTHCARE.NS",
    
    # ========== THEMATIC INDICES ==========
    "Nifty India Consumption": "NIFTY_CONSR_DURBL.NS",
    "Nifty India Defence": "NIFTY_INDIA_DEFENCE.NS",
    "Nifty India Digital": "NIFTYINDIADIGITAL.NS",
    "Nifty India Manufacturing": "NIFTYINDMANUFACTUR.NS",
    "Nifty Mobility": "NIFTY_MOBILITY.NS",
    "Nifty India Tourism": "NIFTY_INDIA_TOURISM.NS",
    "Nifty Housing": "NIFTY_HOUSING.NS",
    "Nifty Transportation & Logistics": "NIFTY_TRANSPORT.NS",
    "Nifty MidSmallcap 400": "NIFTY_MIDSML_400.NS",
    "Nifty Non-Cyclical Consumer": "NIFTY_NON_CYC_CONS.NS",
    
    # ========== DIVIDEND INDICES ==========
    "Nifty Dividend Opportunities 50": "NIFTYDIV_OPPS_50.NS",
    "Nifty High Beta 50": "NIFTYHIGHBETA50.NS",
    "Nifty Low Volatility 50": "NIFTYLOWVOL50.NS",
    "Nifty Quality 30": "NIFTY_QUALITY_30.NS",
    "Nifty Alpha 50": "NIFTY_ALPHA_50.NS",
    
    # ========== STRATEGY INDICES ==========
    "Nifty50 Equal Weight": "NIFTY50_EQL_WGT.NS",
    "Nifty100 Equal Weight": "NIFTY100_EQL_WGT.NS",
    "Nifty50 Value 20": "NIFTY50_VALUE_20.NS",
    "Nifty Midcap150 Quality 50": "NIFTYMID150QUAL50.NS",
    "Nifty Midcap150 Momentum 50": "NIFTYMIDMOM50.NS",
    "Nifty Smallcap250 Quality 50": "NIFTYSMLQUAL50.NS",
    "Nifty200 Quality 30": "NIFTY200QUALIT30.NS",
    "Nifty100 Quality 30": "NIFTY100QUALTY30.NS",
    "Nifty200 Momentum 30": "NIFTY200MOMENTM30.NS",
    "Nifty Midcap Select": "NIFTYMIDCAPSELECT.NS",
    "Nifty Total Market": "NIFTYTOTALMARKET.NS",
    "Nifty Microcap 250": "NIFTYMICROCAP250.NS",
    
    # ========== GLOBAL INDICES ==========
    "Nifty India Corporate Group Index": "NIFTYINDIA_CG.NS",
    
    # ========== NEW/RECENT INDICES ==========
    "Nifty EV & New Age Automotive": "NIFTY_EV_NEW_AGE.NS",
    "Nifty Core Housing": "NIFTY_CORE_HOUSING.NS",
    "Nifty Rural India": "NIFTY_RURAL_INDIA.NS",
    "Nifty 100 ESG": "NIFTY100_ESG.NS",
    "Nifty India Consumption Defence": "NIFTY_CONS_DEFENCE.NS",
}

def test_index(name, symbol):
    """Test if an index is available on Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='5d')
        
        if not data.empty:
            last_close = data['Close'].iloc[-1]
            last_date = data.index[-1].strftime('%Y-%m-%d')
            volume = data['Volume'].iloc[-1] if 'Volume' in data.columns else 0
            
            return {
                'Index Name': name,
                'Symbol': symbol,
                'Status': '✅ Available',
                'Last Price': f'{last_close:,.2f}',
                'Last Date': last_date,
                'Records': len(data)
            }
        else:
            return {
                'Index Name': name,
                'Symbol': symbol,
                'Status': '❌ No Data',
                'Last Price': '-',
                'Last Date': '-',
                'Records': 0
            }
    except Exception as e:
        error_msg = str(e)[:40]
        return {
            'Index Name': name,
            'Symbol': symbol,
            'Status': '⚠️  Error',
            'Last Price': '-',
            'Last Date': '-',
            'Records': error_msg
        }

def main():
    """Test all NSE indices and generate report"""
    print("\n" + "="*100)
    print("DISCOVERING NSE INDICES ON YAHOO FINANCE")
    print("="*100)
    print(f"Testing {len(NSE_INDICES)} indices...")
    print()
    
    results = []
    available_count = 0
    
    for name, symbol in NSE_INDICES.items():
        print(f"Testing: {name:<40} ({symbol})", end="... ")
        result = test_index(name, symbol)
        results.append(result)
        
        if result['Status'] == '✅ Available':
            print(f"✅ {result['Last Price']}")
            available_count += 1
        elif result['Status'] == '❌ No Data':
            print("❌ No Data")
        else:
            print(f"⚠️  {result['Records']}")
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Separate available and unavailable
    available_df = df[df['Status'] == '✅ Available'].copy()
    unavailable_df = df[df['Status'] != '✅ Available'].copy()
    
    # Print summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    print(f"Total Indices Tested: {len(NSE_INDICES)}")
    print(f"Available on Yahoo Finance: {available_count} ({available_count/len(NSE_INDICES)*100:.1f}%)")
    print(f"Not Available: {len(NSE_INDICES) - available_count}")
    print()
    
    # Print available indices grouped by category
    print("="*100)
    print("AVAILABLE INDICES (GROUPED BY CATEGORY)")
    print("="*100)
    
    categories = {
        "BROAD MARKET INDICES": [
            "Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200", "Nifty 500",
            "Nifty Midcap 50", "Nifty Midcap 100", "Nifty Midcap 150",
            "Nifty Smallcap 50", "Nifty Smallcap 100", "Nifty Smallcap 250",
            "Nifty Microcap 250", "Nifty LargeMidcap 250"
        ],
        "SECTORAL INDICES": [
            "Nifty Auto", "Nifty Bank", "Nifty Financial Services", 
            "Nifty FMCG", "Nifty IT", "Nifty Media", "Nifty Metal",
            "Nifty Pharma", "Nifty PSU Bank", "Nifty Private Bank",
            "Nifty Realty", "Nifty Energy", "Nifty Infrastructure",
            "Nifty Commodities", "Nifty Consumption", "Nifty CPSE",
            "Nifty MNC", "Nifty PSE", "Nifty Services Sector",
            "Nifty Oil & Gas", "Nifty Healthcare Index"
        ],
        "THEMATIC INDICES": [
            "Nifty India Consumption", "Nifty India Defence", 
            "Nifty India Digital", "Nifty India Manufacturing",
            "Nifty Mobility", "Nifty India Tourism", "Nifty Housing",
            "Nifty Transportation & Logistics", "Nifty EV & New Age Automotive",
            "Nifty Core Housing", "Nifty Rural India"
        ],
        "STRATEGY INDICES": [
            "Nifty Dividend Opportunities 50", "Nifty High Beta 50",
            "Nifty Low Volatility 50", "Nifty Quality 30", "Nifty Alpha 50",
            "Nifty50 Equal Weight", "Nifty100 Equal Weight", "Nifty50 Value 20",
            "Nifty Midcap150 Quality 50", "Nifty Midcap150 Momentum 50",
            "Nifty Smallcap250 Quality 50", "Nifty200 Quality 30",
            "Nifty100 Quality 30", "Nifty200 Momentum 30",
            "Nifty Midcap Select", "Nifty Total Market", "Nifty 100 ESG"
        ]
    }
    
    for category, index_names in categories.items():
        category_indices = available_df[available_df['Index Name'].isin(index_names)]
        if not category_indices.empty:
            print(f"\n{category} ({len(category_indices)} available):")
            print("-" * 100)
            for _, row in category_indices.iterrows():
                print(f"  {row['Index Name']:<45} {row['Symbol']:<25} ₹{row['Last Price']:>12}")
    
    # Print unavailable indices
    if not unavailable_df.empty:
        print("\n" + "="*100)
        print("UNAVAILABLE/ERROR INDICES")
        print("="*100)
        for _, row in unavailable_df.iterrows():
            print(f"  {row['Index Name']:<45} {row['Symbol']:<25} {row['Status']}")
    
    # Save to CSV
    output_file = "nse_indices_yahoo_finance.csv"
    available_df.to_csv(output_file, index=False)
    print(f"\n✅ Available indices saved to: {output_file}")
    
    # Print SQL insert statements
    print("\n" + "="*100)
    print("SQL INSERT STATEMENTS (for nse_yahoo_symbol_map)")
    print("="*100)
    print("\n-- NSE Indices Symbol Mapping for Yahoo Finance")
    for _, row in available_df.iterrows():
        nse_symbol = row['Symbol']
        yahoo_symbol = row['Symbol']
        name = row['Index Name'].replace("'", "''")
        print(f"INSERT INTO nse_yahoo_symbol_map (nse_symbol, yahoo_symbol, is_verified, is_active, symbol_type, notes)")
        print(f"VALUES ('{nse_symbol}', '{yahoo_symbol}', TRUE, TRUE, 'INDEX', '{name}')")
        print(f"ON DUPLICATE KEY UPDATE yahoo_symbol='{yahoo_symbol}', is_verified=TRUE, notes='{name}';")
    
    print("\n" + "="*100)
    print(f"Discovery Complete! Found {available_count} available NSE indices on Yahoo Finance")
    print("="*100)

if __name__ == "__main__":
    main()
