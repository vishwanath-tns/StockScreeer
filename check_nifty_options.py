#!/usr/bin/env python3
"""
Display available NIFTY and BANKNIFTY options with expiry dates
"""
from datetime import datetime, timedelta
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

def display_options():
    selector = InstrumentSelector()
    
    # Get all NIFTY and BANKNIFTY options
    nifty_options = selector.get_nifty_options()
    banknifty_options = selector.get_banknifty_options()
    
    print("\n" + "="*80)
    print("NIFTY OPTIONS - Available Expiries")
    print("="*80)
    print(f"{'Symbol':<30} {'Instrument ID':<15} {'Expiry Date':<15}")
    print("-"*80)
    for opt in nifty_options:
        symbol = opt.get('symbol', 'N/A')
        inst_id = opt.get('instrumentId', 'N/A')
        expiry = opt.get('expiryDate', 'N/A')
        print(f"{symbol:<30} {str(inst_id):<15} {str(expiry):<15}")
    
    print("\n" + "="*80)
    print("BANKNIFTY OPTIONS - Available Expiries")
    print("="*80)
    print(f"{'Symbol':<30} {'Instrument ID':<15} {'Expiry Date':<15}")
    print("-"*80)
    for opt in banknifty_options:
        symbol = opt.get('symbol', 'N/A')
        inst_id = opt.get('instrumentId', 'N/A')
        expiry = opt.get('expiryDate', 'N/A')
        print(f"{symbol:<30} {str(inst_id):<15} {str(expiry):<15}")
    
    # Calculate next week's date range
    today = datetime.now()
    next_week_start = today + timedelta(days=1)
    next_week_end = next_week_start + timedelta(days=6)
    
    print("\n" + "="*80)
    print(f"TODAY: {today.strftime('%Y-%m-%d (%A)')}")
    print(f"NEXT WEEK: {next_week_start.strftime('%Y-%m-%d (%A)')} to {next_week_end.strftime('%Y-%m-%d (%A)')}")
    print("="*80)
    
    # Filter options expiring next week
    print("\n" + "="*80)
    print("NIFTY OPTIONS - EXPIRING NEXT WEEK")
    print("="*80)
    nifty_next_week = [opt for opt in nifty_options 
                       if next_week_start.date() <= datetime.strptime(str(opt.get('expiryDate', '')), '%Y-%m-%d').date() <= next_week_end.date()]
    
    if nifty_next_week:
        print(f"{'Symbol':<30} {'Instrument ID':<15} {'Expiry Date':<15} {'Days Left':<10}")
        print("-"*80)
        for opt in nifty_next_week:
            symbol = opt.get('symbol', 'N/A')
            inst_id = opt.get('instrumentId', 'N/A')
            expiry = opt.get('expiryDate', 'N/A')
            exp_date = datetime.strptime(str(expiry), '%Y-%m-%d')
            days_left = (exp_date.date() - today.date()).days
            print(f"{symbol:<30} {str(inst_id):<15} {str(expiry):<15} {days_left:<10}")
    else:
        print("No NIFTY options expiring next week")
    
    print("\n" + "="*80)
    print("BANKNIFTY OPTIONS - EXPIRING NEXT WEEK")
    print("="*80)
    banknifty_next_week = [opt for opt in banknifty_options 
                           if next_week_start.date() <= datetime.strptime(str(opt.get('expiryDate', '')), '%Y-%m-%d').date() <= next_week_end.date()]
    
    if banknifty_next_week:
        print(f"{'Symbol':<30} {'Instrument ID':<15} {'Expiry Date':<15} {'Days Left':<10}")
        print("-"*80)
        for opt in banknifty_next_week:
            symbol = opt.get('symbol', 'N/A')
            inst_id = opt.get('instrumentId', 'N/A')
            expiry = opt.get('expiryDate', 'N/A')
            exp_date = datetime.strptime(str(expiry), '%Y-%m-%d')
            days_left = (exp_date.date() - today.date()).days
            print(f"{symbol:<30} {str(inst_id):<15} {str(expiry):<15} {days_left:<10}")
    else:
        print("No BANKNIFTY options expiring next week")
    
    print("\n" + "="*80)
    print(f"Summary:")
    print(f"  Total NIFTY options available: {len(nifty_options)}")
    print(f"  NIFTY options expiring next week: {len(nifty_next_week)}")
    print(f"  Total BANKNIFTY options available: {len(banknifty_options)}")
    print(f"  BANKNIFTY options expiring next week: {len(banknifty_next_week)}")
    print("="*80 + "\n")

if __name__ == "__main__":
    display_options()
