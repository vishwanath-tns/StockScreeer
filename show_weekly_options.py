#!/usr/bin/env python3
"""
Display NIFTY and BANKNIFTY weekly options that will be subscribed
"""
from datetime import date, timedelta
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

def main():
    selector = InstrumentSelector()
    
    today = date.today()
    days_until_thursday = (3 - today.weekday()) % 7
    if days_until_thursday == 0:
        days_until_thursday = 7
    next_thursday = today + timedelta(days=days_until_thursday)
    
    print("\n" + "="*100)
    print(f"NIFTY & BANKNIFTY WEEKLY OPTIONS")
    print("="*100)
    print(f"Today: {today.strftime('%A, %Y-%m-%d')}")
    print(f"Weekly Expiry: {next_thursday.strftime('%A, %Y-%m-%d')}")
    print("="*100 + "\n")
    
    # Get NIFTY weekly options
    print("Fetching NIFTY weekly options...")
    nifty_weekly = selector.get_nifty_weekly_options(strike_offset_levels=10)
    
    print(f"\n{'NIFTY WEEKLY OPTIONS':<80}")
    print(f"{'='*80}")
    print(f"Total available: {len(nifty_weekly)} contracts")
    print(f"\n{'Strike':<12} {'Type':<8} {'Symbol':<30} {'Inst ID':<12}")
    print("-"*80)
    
    current_strike = None
    count = 0
    for opt in nifty_weekly[:20]:  # Show first 20
        strike = opt.get('strike_price', 'N/A')
        opt_type = opt.get('option_type', 'N/A')
        symbol = opt.get('symbol', 'N/A')
        inst_id = opt.get('security_id', 'N/A')
        
        if current_strike != strike:
            if current_strike is not None:
                print("-"*40)
            current_strike = strike
        
        print(f"{strike:<12} {opt_type:<8} {symbol:<30} {inst_id:<12}")
        count += 1
    
    if len(nifty_weekly) > 20:
        print(f"... and {len(nifty_weekly) - 20} more contracts")
    
    # Get BANKNIFTY weekly options
    print(f"\n\n{'BANKNIFTY WEEKLY OPTIONS':<80}")
    print(f"{'='*80}")
    
    banknifty_weekly = selector.get_banknifty_weekly_options(strike_offset_levels=10)
    
    print(f"Total available: {len(banknifty_weekly)} contracts")
    print(f"\n{'Strike':<12} {'Type':<8} {'Symbol':<30} {'Inst ID':<12}")
    print("-"*80)
    
    current_strike = None
    count = 0
    for opt in banknifty_weekly[:20]:  # Show first 20
        strike = opt.get('strike_price', 'N/A')
        opt_type = opt.get('option_type', 'N/A')
        symbol = opt.get('symbol', 'N/A')
        inst_id = opt.get('security_id', 'N/A')
        
        if current_strike != strike:
            if current_strike is not None:
                print("-"*40)
            current_strike = strike
        
        print(f"{strike:<12} {opt_type:<8} {symbol:<30} {inst_id:<12}")
        count += 1
    
    if len(banknifty_weekly) > 20:
        print(f"... and {len(banknifty_weekly) - 20} more contracts")
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    print(f"NIFTY weekly options (ATM ± 10 levels):      {len(nifty_weekly)} contracts")
    print(f"BANKNIFTY weekly options (ATM ± 10 levels):  {len(banknifty_weekly)} contracts")
    print(f"Total (with 2 futures each):                 {2 + 2 + len(nifty_weekly) + len(banknifty_weekly)} instruments")
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
