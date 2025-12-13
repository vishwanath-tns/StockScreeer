#!/usr/bin/env python
"""Display QuoteData structure from Dhan WebSocket."""

print('=' * 70)
print('Dhan WebSocket QuoteData Structure')
print('=' * 70)
print()
print('Fields received from Dhan FNO Feed WebSocket:')
print('-' * 70)
print(f"  {'Field':<20} {'Type':<15} Description")
print('-' * 70)
print(f"  {'security_id':<20} {'int':<15} Unique instrument ID")
print(f"  {'exchange_segment':<20} {'int':<15} 2=NSE_FNO, 5=MCX_COMM")
print(f"  {'ltp':<20} {'float':<15} Last Traded Price")
print(f"  {'ltq':<20} {'int':<15} Last Traded Quantity")
print(f"  {'ltt':<20} {'int':<15} Last Trade Time (Unix timestamp)")
print(f"  {'atp':<20} {'float':<15} Average Traded Price")
print(f"  {'volume':<20} {'int':<15} Total traded volume")
print(f"  {'total_sell_qty':<20} {'int':<15} Total sell quantity pending")
print(f"  {'total_buy_qty':<20} {'int':<15} Total buy quantity pending")
print(f"  {'day_open':<20} {'float':<15} Day open price")
print(f"  {'day_close':<20} {'float':<15} Previous day close")
print(f"  {'day_high':<20} {'float':<15} Day high price")
print(f"  {'day_low':<20} {'float':<15} Day low price")
print(f"  {'open_interest':<20} {'int (opt)':<15} Open Interest (F&O)")
print(f"  {'prev_close':<20} {'float (opt)':<15} Previous close price")
print(f"  {'received_at':<20} {'float':<15} Timestamp when received")
print('-' * 70)
print()
print('Exchange Segment Codes:')
print('  1 = NSE_EQ (Equity - skipped by FNO writer)')
print('  2 = NSE_FNO (Futures & Options)')
print('  3 = NSE_CURRENCY')
print('  4 = BSE_FNO')
print('  5 = MCX_COMM (Commodities)')
print('  6 = OPTIDX (Index Options)')
print('  7 = OPTSTK (Stock Options)')
print()

# Try to get a live quote from Redis
print('=' * 70)
print('Checking Redis for live quotes...')
print('=' * 70)
try:
    import redis
    import json
    r = redis.Redis(decode_responses=True)
    
    # Check stream length
    stream_len = r.xlen('dhan:quotes:stream')
    print(f"Stream 'dhan:quotes:stream' has {stream_len:,} messages")
    
    # Get latest message from stream
    if stream_len > 0:
        entries = r.xrevrange('dhan:quotes:stream', count=3)
        print(f"\nLatest 3 quotes from Redis stream:")
        print('-' * 70)
        for msg_id, data in entries:
            sec_id = data.get('security_id', '?')
            seg = data.get('exchange_segment', '?')
            ltp = data.get('ltp', '?')
            vol = data.get('volume', '?')
            ltt = data.get('ltt', '?')
            print(f"  ID={sec_id}, Seg={seg}, LTP={ltp}, Vol={vol}, LTT={ltt}")
except Exception as e:
    print(f"Error: {e}")
