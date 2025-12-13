#!/usr/bin/env python3
"""
Display FNO instruments being subscribed by the feed launcher
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dhan_trading.market_feed.instrument_selector import InstrumentSelector
from datetime import date, timedelta

def main():
    selector = InstrumentSelector()
    
    print("\n" + "="*120)
    print("FNO FEED LAUNCHER - INSTRUMENTS BEING SUBSCRIBED")
    print("="*120 + "\n")
    
    # Nifty Futures
    print("1. NIFTY FUTURES (Current & Next Expiry)")
    print("-"*120)
    try:
        nifty_futures = selector.get_nifty_futures(expiries=[0, 1])
        for fut in nifty_futures:
            print(f"  {fut.get('symbol', 'N/A'):<40} ID={fut.get('security_id', 'N/A'):<8} "
                  f"Expiry={fut.get('expiry_date', 'N/A'):<15} Lot={fut.get('lot_size', 'N/A')}")
        print(f"  Total: {len(nifty_futures)} futures\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")
    
    # Bank Nifty Futures
    print("2. BANKNIFTY FUTURES (Current & Next Expiry)")
    print("-"*120)
    try:
        banknifty_futures = selector.get_banknifty_futures(expiries=[0, 1])
        for fut in banknifty_futures:
            print(f"  {fut.get('symbol', 'N/A'):<40} ID={fut.get('security_id', 'N/A'):<8} "
                  f"Expiry={fut.get('expiry_date', 'N/A'):<15} Lot={fut.get('lot_size', 'N/A')}")
        print(f"  Total: {len(banknifty_futures)} futures\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")
    
    # NIFTY Weekly Options
    print("3. NIFTY WEEKLY OPTIONS (Next Thursday Expiry - ATM ± 10 Levels)")
    print("-"*120)
    try:
        nifty_weekly = selector.get_nifty_weekly_options(strike_offset_levels=10)
        
        # Group by strike
        from collections import defaultdict
        by_strike = defaultdict(list)
        for opt in nifty_weekly:
            strike = opt.get('strike_price')
            by_strike[strike].append(opt)
        
        for strike in sorted(by_strike.keys()):
            for opt in by_strike[strike]:
                print(f"  {opt.get('symbol', 'N/A'):<40} ID={opt.get('security_id', 'N/A'):<8} "
                      f"Strike={strike:<8} Type={opt.get('option_type', 'N/A'):<4} "
                      f"Expiry={opt.get('expiry_date', 'N/A'):<15}")
        print(f"  Total: {len(nifty_weekly)} options\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")
    
    # BANKNIFTY Weekly Options
    print("4. BANKNIFTY WEEKLY OPTIONS (Next Thursday Expiry - ATM ± 10 Levels)")
    print("-"*120)
    try:
        banknifty_weekly = selector.get_banknifty_weekly_options(strike_offset_levels=10)
        
        # Group by strike
        from collections import defaultdict
        by_strike = defaultdict(list)
        for opt in banknifty_weekly:
            strike = opt.get('strike_price')
            by_strike[strike].append(opt)
        
        for strike in sorted(by_strike.keys()):
            for opt in by_strike[strike]:
                print(f"  {opt.get('symbol', 'N/A'):<40} ID={opt.get('security_id', 'N/A'):<8} "
                      f"Strike={strike:<8} Type={opt.get('option_type', 'N/A'):<4} "
                      f"Expiry={opt.get('expiry_date', 'N/A'):<15}")
        print(f"  Total: {len(banknifty_weekly)} options\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")
    
    # Summary
    print("="*120)
    print("SUMMARY")
    print("="*120)
    
    try:
        nf = selector.get_nifty_futures(expiries=[0, 1])
        bnf = selector.get_banknifty_futures(expiries=[0, 1])
        nw = selector.get_nifty_weekly_options(strike_offset_levels=10)
        bw = selector.get_banknifty_weekly_options(strike_offset_levels=10)
        
        total = len(nf) + len(bnf) + len(nw) + len(bw)
        
        print(f"Nifty Futures:           {len(nf):>4}")
        print(f"BankNifty Futures:       {len(bnf):>4}")
        print(f"Nifty Weekly Options:    {len(nw):>4}")
        print(f"BankNifty Weekly Options:{len(bw):>4}")
        print(f"{'─'*40}")
        print(f"TOTAL INSTRUMENTS:       {total:>4}")
        print("="*120 + "\n")
    except Exception as e:
        print(f"ERROR in summary: {e}\n")

if __name__ == "__main__":
    main()
