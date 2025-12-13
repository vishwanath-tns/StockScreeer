#!/usr/bin/env python3
"""
Check FNO instruments currently configured and their subscription status
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dhan_trading.market_feed.instrument_selector import InstrumentSelector

def main():
    selector = InstrumentSelector()
    
    print("\n" + "="*120)
    print("FNO INSTRUMENTS CURRENTLY CONFIGURED FOR SUBSCRIPTION")
    print("="*120)
    
    # Get all instruments
    nifty_futs = selector.get_nifty_futures(expiries=[0, 1])
    bnifty_futs = selector.get_banknifty_futures(expiries=[0, 1])
    finnifty_futs = selector.get_finnifty_futures(expiries=[0, 1])
    
    nifty_opts = selector.get_nifty_options(expiries=[0, 1], strike_offset_levels=2)
    bnifty_opts = selector.get_banknifty_options(expiries=[0, 1], strike_offset_levels=2)
    
    print("\n" + "NIFTY FUTURES".center(120))
    print("-" * 120)
    print(f"{'Security ID':<12} {'Symbol':<30} {'Underlying':<15} {'Expiry':<12} {'Type':<8}")
    print("-" * 120)
    for inst in nifty_futs:
        print(f"{inst.get('security_id', '-'):<12} {inst.get('symbol', '-'):<30} {inst.get('underlying_symbol', '-'):<15} {str(inst.get('expiry_date', '-')):<12} {inst.get('instrument', '-'):<8}")
    print(f"Total: {len(nifty_futs)} instruments\n")
    
    print("BANKNIFTY FUTURES".center(120))
    print("-" * 120)
    print(f"{'Security ID':<12} {'Symbol':<30} {'Underlying':<15} {'Expiry':<12} {'Type':<8}")
    print("-" * 120)
    for inst in bnifty_futs:
        print(f"{inst.get('security_id', '-'):<12} {inst.get('symbol', '-'):<30} {inst.get('underlying_symbol', '-'):<15} {str(inst.get('expiry_date', '-')):<12} {inst.get('instrument', '-'):<8}")
    print(f"Total: {len(bnifty_futs)} instruments\n")
    
    print("FINNIFTY FUTURES".center(120))
    print("-" * 120)
    print(f"{'Security ID':<12} {'Symbol':<30} {'Underlying':<15} {'Expiry':<12} {'Type':<8}")
    print("-" * 120)
    for inst in finnifty_futs:
        print(f"{inst.get('security_id', '-'):<12} {inst.get('symbol', '-'):<30} {inst.get('underlying_symbol', '-'):<15} {str(inst.get('expiry_date', '-')):<12} {inst.get('instrument', '-'):<8}")
    print(f"Total: {len(finnifty_futs)} instruments\n")
    
    print("NIFTY OPTIONS".center(120))
    print("-" * 120)
    print(f"{'Security ID':<12} {'Symbol':<30} {'Underlying':<15} {'Strike':<8} {'Expiry':<12} {'Type':<8}")
    print("-" * 120)
    for inst in nifty_opts[:10]:  # Show first 10
        print(f"{inst.get('security_id', '-'):<12} {inst.get('symbol', '-'):<30} {inst.get('underlying_symbol', '-'):<15} {str(inst.get('strike_price', '-')):<8} {str(inst.get('expiry_date', '-')):<12} {inst.get('option_type', '-'):<8}")
    print(f"... (showing first 10 of {len(nifty_opts)} total)\n")
    
    print("BANKNIFTY OPTIONS".center(120))
    print("-" * 120)
    print(f"{'Security ID':<12} {'Symbol':<30} {'Underlying':<15} {'Strike':<8} {'Expiry':<12} {'Type':<8}")
    print("-" * 120)
    for inst in bnifty_opts[:10]:  # Show first 10
        print(f"{inst.get('security_id', '-'):<12} {inst.get('symbol', '-'):<30} {inst.get('underlying_symbol', '-'):<15} {str(inst.get('strike_price', '-')):<8} {str(inst.get('expiry_date', '-')):<12} {inst.get('option_type', '-'):<8}")
    print(f"... (showing first 10 of {len(bnifty_opts)} total)\n")
    
    print("="*120)
    total = len(nifty_futs) + len(bnifty_futs) + len(finnifty_futs) + len(nifty_opts) + len(bnifty_opts)
    print(f"TOTAL INSTRUMENTS: {total}")
    print("="*120)
    
    print("\nSUMMARY:")
    print(f"  Nifty Futures:      {len(nifty_futs):>3} instruments")
    print(f"  BankNifty Futures:  {len(bnifty_futs):>3} instruments")
    print(f"  FinNifty Futures:   {len(finnifty_futs):>3} instruments")
    print(f"  Nifty Options:      {len(nifty_opts):>3} instruments")
    print(f"  BankNifty Options:  {len(bnifty_opts):>3} instruments")
    print(f"  {'-'*40}")
    print(f"  TOTAL:              {total:>3} instruments\n")

if __name__ == '__main__':
    main()
