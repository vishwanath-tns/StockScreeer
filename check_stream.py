import redis

r = redis.Redis(host='localhost', decode_responses=True)
# Get one message from the stream
messages = r.xrange('dhan:quotes:stream', count=1)
if messages:
    msg_id, msg_data = messages[0]
    print(f'Message ID: {msg_id}')
    seg = msg_data.get("exchange_segment")
    sec = msg_data.get("security_id")
    print(f'Exchange Segment: {seg}')
    print(f'Security ID: {sec}')
    print(f'First 5 keys: {list(msg_data.keys())[:5]}')
else:
    print('No messages in stream')
