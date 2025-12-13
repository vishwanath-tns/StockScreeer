#!/usr/bin/env python3
"""
Backfill quotes from Redis stream to MySQL database.
This script reads all quotes from the Redis stream and inserts them into dhan_quotes table.
"""
import os
import redis
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM_KEY = "dhan:quotes:stream"

def get_db_engine():
    """Create database engine."""
    pw = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    user = os.getenv("MYSQL_USER", "root")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db = os.getenv("MYSQL_DB", "dhan_trading")
    return create_engine(f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}")

def get_redis_client():
    """Create Redis client."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def read_all_stream_messages(r, stream_key, batch_size=1000):
    """Read all messages from Redis stream."""
    messages = []
    last_id = "-"
    
    while True:
        result = r.xrange(stream_key, min=last_id, max="+", count=batch_size)
        if not result:
            break
        
        for msg_id, data in result:
            messages.append((msg_id, data))
        
        if len(result) < batch_size:
            break
        
        # Move past the last ID for next iteration
        # Increment the sequence number to get next batch
        last_msg_id = result[-1][0]
        parts = last_msg_id.split("-")
        last_id = f"{parts[0]}-{int(parts[1]) + 1}"
    
    return messages

def parse_quote(data):
    """Parse a quote from Redis stream data."""
    try:
        # Handle received_at - convert from epoch ms to datetime
        received_at = data.get("received_at")
        if received_at:
            ts = float(received_at)
            if ts > 1e12:  # epoch in milliseconds
                ts = ts / 1000
            received_at = datetime.fromtimestamp(ts)
        else:
            received_at = datetime.now()
        
        return {
            "security_id": int(data.get("security_id", 0)),
            "exchange_segment": int(data.get("exchange_segment", 0)),
            "ltp": float(data.get("ltp", 0)),
            "ltq": int(data.get("ltq", 0)),
            "ltt": data.get("ltt", ""),
            "atp": float(data.get("atp", 0)) if data.get("atp") else None,
            "volume": int(data.get("volume", 0)),
            "total_sell_qty": int(data.get("total_sell_qty", 0)),
            "total_buy_qty": int(data.get("total_buy_qty", 0)),
            "day_open": float(data.get("day_open", 0)) if data.get("day_open") else None,
            "day_close": float(data.get("day_close", 0)) if data.get("day_close") else None,
            "day_high": float(data.get("day_high", 0)) if data.get("day_high") else None,
            "day_low": float(data.get("day_low", 0)) if data.get("day_low") else None,
            "open_interest": int(data.get("open_interest", 0)) if data.get("open_interest") else None,
            "prev_close": float(data.get("prev_close", 0)) if data.get("prev_close") else None,
            "received_at": received_at,
        }
    except Exception as e:
        print(f"Error parsing quote: {e}, data: {data}")
        return None

def insert_quotes_batch(engine, quotes, batch_size=5000):
    """Insert quotes in batches using INSERT IGNORE to skip duplicates."""
    if not quotes:
        return 0
    
    inserted = 0
    
    with engine.begin() as conn:
        for i in tqdm(range(0, len(quotes), batch_size), desc="Inserting batches"):
            batch = quotes[i:i+batch_size]
            
            # Build INSERT IGNORE statement
            sql = text("""
                INSERT IGNORE INTO dhan_quotes 
                (security_id, exchange_segment, ltp, ltq, ltt, atp, volume,
                 total_sell_qty, total_buy_qty, day_open, day_close, day_high, day_low,
                 open_interest, prev_close, received_at)
                VALUES 
                (:security_id, :exchange_segment, :ltp, :ltq, :ltt, :atp, :volume,
                 :total_sell_qty, :total_buy_qty, :day_open, :day_close, :day_high, :day_low,
                 :open_interest, :prev_close, :received_at)
            """)
            
            for quote in batch:
                try:
                    result = conn.execute(sql, quote)
                    inserted += result.rowcount
                except Exception as e:
                    print(f"Error inserting quote: {e}")
    
    return inserted

def insert_quotes_batch_fast(engine, quotes, batch_size=5000):
    """Insert quotes using executemany for better performance."""
    if not quotes:
        return 0
    
    inserted = 0
    
    with engine.begin() as conn:
        for i in tqdm(range(0, len(quotes), batch_size), desc="Inserting batches"):
            batch = quotes[i:i+batch_size]
            
            # Use executemany with INSERT IGNORE
            sql = text("""
                INSERT IGNORE INTO dhan_quotes 
                (security_id, exchange_segment, ltp, ltq, ltt, atp, volume,
                 total_sell_qty, total_buy_qty, day_open, day_close, day_high, day_low,
                 open_interest, prev_close, received_at)
                VALUES 
                (:security_id, :exchange_segment, :ltp, :ltq, :ltt, :atp, :volume,
                 :total_sell_qty, :total_buy_qty, :day_open, :day_close, :day_high, :day_low,
                 :open_interest, :prev_close, :received_at)
            """)
            
            try:
                result = conn.execute(sql, batch)
                inserted += len(batch)  # Approximate since INSERT IGNORE doesn't return exact count
            except Exception as e:
                print(f"Error inserting batch: {e}")
    
    return inserted

def main():
    print("=" * 60)
    print("Redis to Database Backfill Tool")
    print("=" * 60)
    
    # Connect to Redis
    print("\n1. Connecting to Redis...")
    r = get_redis_client()
    stream_len = r.xlen(STREAM_KEY)
    print(f"   Stream '{STREAM_KEY}' has {stream_len:,} messages")
    
    # Connect to Database
    print("\n2. Connecting to Database...")
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM dhan_quotes"))
        db_count = result.scalar()
        print(f"   dhan_quotes table has {db_count:,} rows")
        
        # Get last quote timestamp
        result = conn.execute(text("SELECT MAX(received_at) FROM dhan_quotes"))
        last_ts = result.scalar()
        print(f"   Last quote timestamp: {last_ts}")
    
    # Read all messages from Redis stream
    print(f"\n3. Reading all messages from Redis stream...")
    messages = read_all_stream_messages(r, STREAM_KEY)
    print(f"   Read {len(messages):,} messages")
    
    if not messages:
        print("   No messages to process!")
        return
    
    # Parse quotes
    print("\n4. Parsing quotes...")
    quotes = []
    for msg_id, data in tqdm(messages, desc="Parsing"):
        quote = parse_quote(data)
        if quote:
            quotes.append(quote)
    
    print(f"   Parsed {len(quotes):,} valid quotes")
    
    if not quotes:
        print("   No valid quotes to insert!")
        return
    
    # Show sample
    print("\n5. Sample quote:")
    sample = quotes[0]
    for k, v in sample.items():
        print(f"   {k}: {v}")
    
    # Get date range
    timestamps = [q["received_at"] for q in quotes if q["received_at"]]
    if timestamps:
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        print(f"\n   Date range: {min_ts} to {max_ts}")
    
    # Confirm before insert
    print(f"\n6. Ready to insert {len(quotes):,} quotes into database.")
    confirm = input("   Continue? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("   Aborted.")
        return
    
    # Insert quotes
    print("\n7. Inserting quotes into database...")
    inserted = insert_quotes_batch_fast(engine, quotes)
    print(f"   Inserted approximately {inserted:,} quotes")
    
    # Verify
    print("\n8. Verifying...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM dhan_quotes"))
        new_count = result.scalar()
        print(f"   dhan_quotes now has {new_count:,} rows (was {db_count:,})")
        print(f"   Added {new_count - db_count:,} new rows")
    
    print("\n" + "=" * 60)
    print("Backfill complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
