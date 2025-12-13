#!/usr/bin/env python
"""Quick script to check MCX commodities available."""
from dhan_trading.market_feed.instrument_selector import InstrumentSelector

selector = InstrumentSelector()

print("=" * 60)
print("MCX Commodity Futures (nearest expiry)")
print("=" * 60)

mcx = selector.get_major_commodity_futures(expiries=[0])
print(f"Total: {len(mcx)} instruments")
print()

for inst in mcx:
    symbol = inst.get('symbol', '')
    display = inst.get('display_name', '')
    sec_id = inst.get('security_id', '')
    expiry = inst.get('expiry_date', '')
    print(f"  {symbol:20} | {display:30} | ID: {sec_id} | Expiry: {expiry}")
