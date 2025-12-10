"""Check live quotes from Redis."""
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)
pubsub = r.pubsub()
pubsub.subscribe('dhan_quotes')

print('Listening for NIFTY DEC FUT quotes (security_id 49543)...')
count = 0
nifty_prices = []
for msg in pubsub.listen():
    if msg['type'] == 'message':
        data = json.loads(msg['data'])
        sec_id = data.get('security_id')
        ltp = data.get('ltp')
        volume = data.get('volume')
        
        # Only show Nifty Dec Fut
        if sec_id == 49543:
            print(f"  LTP: {ltp}, Volume: {volume:,}")
            nifty_prices.append(ltp)
            count += 1
            
        if count >= 20:
            break

print(f"\nPrice range: {min(nifty_prices):.2f} - {max(nifty_prices):.2f}")
print(f"Range: {max(nifty_prices) - min(nifty_prices):.2f} points")

# Show distribution across 10-point bins
bins = {}
for p in nifty_prices:
    bucket = round(p / 10) * 10
    bins[bucket] = bins.get(bucket, 0) + 1
print(f"\nPrice bins (10 points each):")
for bucket in sorted(bins.keys()):
    print(f"  {bucket}: {bins[bucket]} quotes")
