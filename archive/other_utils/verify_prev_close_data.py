"""
Quick verification of previous close data for advance-decline calculation
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from services.market_breadth_service import get_engine
from nifty500_stocks_list import NIFTY_500_STOCKS
import pandas as pd

def verify_prev_close_coverage():
    """Check how many stocks have previous close data"""
    engine = get_engine()
    
    print(f"📊 Checking {len(NIFTY_500_STOCKS)} Nifty 500 stocks")
    
    # Get Yahoo symbols for these NSE symbols
    yahoo_query = f"""
    SELECT nse_symbol, yahoo_symbol 
    FROM nse_yahoo_symbol_map 
    WHERE nse_symbol IN ({','.join(["'" + s + "'" for s in NIFTY_500_STOCKS])})
    AND yahoo_symbol IS NOT NULL
    ORDER BY nse_symbol
    """
    
    mapping_df = pd.read_sql(yahoo_query, engine)
    print(f"✅ Symbols with Yahoo mapping: {len(mapping_df)}/{len(NIFTY_500_STOCKS)} ({len(mapping_df)/len(NIFTY_500_STOCKS)*100:.1f}%)")
    
    if len(mapping_df) == 0:
        print("❌ No Yahoo symbols mapped!")
        return 0, len(NIFTY_500_STOCKS)
    
    yahoo_symbols = mapping_df['yahoo_symbol'].tolist()
    
    # Check which symbols have previous close data
    prev_close_query = f"""
    SELECT 
        symbol,
        MAX(trade_date) as last_date,
        (SELECT close FROM yfinance_daily_quotes q2 
         WHERE q2.symbol = q1.symbol 
         AND q2.trade_date = MAX(q1.trade_date)) as last_close
    FROM yfinance_daily_quotes q1
    WHERE symbol IN ({','.join(["'" + s + "'" for s in yahoo_symbols])})
    GROUP BY symbol
    ORDER BY symbol
    """
    
    coverage_df = pd.read_sql(prev_close_query, engine)
    
    print(f"✅ Symbols with data: {len(coverage_df)}/{len(yahoo_symbols)} ({len(coverage_df)/len(yahoo_symbols)*100:.1f}%)")
    print(f"\n📅 Latest dates in database:")
    print(coverage_df['last_date'].value_counts().head(5))
    
    # Check symbols without data
    missing = set(yahoo_symbols) - set(coverage_df['symbol'])
    if missing:
        print(f"\n❌ Missing data for {len(missing)} symbols:")
        for sym in sorted(missing)[:10]:
            print(f"  - {sym}")
        if len(missing) > 10:
            print(f"  ... and {len(missing)-10} more")
    
    # Sample some symbols with data
    print(f"\n✅ Sample symbols with latest data:")
    sample = coverage_df.head(10)
    for _, row in sample.iterrows():
        print(f"  {row['symbol']:20s} | {row['last_date']} | Close: {row['last_close']:.2f}")
    
    engine.dispose()
    
    return len(coverage_df), len(yahoo_symbols)

if __name__ == "__main__":
    print("=" * 80)
    print("VERIFYING PREVIOUS CLOSE DATA FOR ADVANCE-DECLINE")
    print("=" * 80)
    
    try:
        with_data, total = verify_prev_close_coverage()
        
        if with_data == total:
            print(f"\n🎉 SUCCESS! All {total} symbols have previous close data!")
        elif with_data >= total * 0.95:
            print(f"\n✅ GOOD: {with_data}/{total} symbols have data (95%+ coverage)")
        else:
            print(f"\n⚠️  WARNING: Only {with_data}/{total} symbols have data")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
