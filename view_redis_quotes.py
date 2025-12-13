"""View sample quotes from Redis stream."""
import redis
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

print("=" * 80)
print("Sample Quotes from Redis Stream (dhan:quotes:stream)")
print("=" * 80)
print()

# Get first 5 messages
msgs = r.xrange('dhan:quotes:stream', count=5)
print(f"First 5 messages:")
print("-" * 80)
for msg_id, data in msgs:
    print(f"Stream ID: {msg_id}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print()

# Get last 5 messages
print("-" * 80)
print(f"Last 5 messages:")
print("-" * 80)
msgs_last = r.xrevrange('dhan:quotes:stream', count=5)
for msg_id, data in msgs_last:
    print(f"Stream ID: {msg_id}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print()

# Show unique exchange segments
print("-" * 80)
print("Unique exchange_segment values (sample of 1000 messages):")
sample = r.xrange('dhan:quotes:stream', count=1000)
segments = set()
for msg_id, data in sample:
    seg = data.get('exchange_segment', 'unknown')
    segments.add(seg)
print(f"Segments found: {sorted(segments)}")
print()

# Stream info
print("-" * 80)
print("Stream Info:")
info = r.xinfo_stream('dhan:quotes:stream')
print(f"  Length: {info['length']:,}")
print(f"  First Entry ID: {info.get('first-entry', ['N/A'])[0] if info.get('first-entry') else 'N/A'}")
print(f"  Last Entry ID: {info.get('last-entry', ['N/A'])[0] if info.get('last-entry') else 'N/A'}")
print("=" * 80)
