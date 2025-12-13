"""
FNO Database Writer Subscriber
===============================
Subscribes to Redis and writes FNO & Options data to MySQL database.

This is a standalone service - separate from the feed publisher.
Filters quotes by exchange_segment and writes to appropriate tables:
  - NSE_FNO → dhan_fno_quotes
  - MCX_COMM → dhan_fno_quotes
  - OPTIDX/OPTSTK → dhan_options_quotes

Usage:
    python -m dhan_trading.subscribers.fno_db_writer
    python -m dhan_trading.subscribers.fno_db_writer --debug
"""
import os
import sys
import signal
import logging
import time
import threading
import argparse
import redis
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from dhan_trading.market_feed.redis_subscriber import (
    RedisSubscriber, CHANNEL_QUOTES
)
from dhan_trading.market_feed.redis_publisher import QuoteData, STREAM_QUOTES
from dhan_trading.fno_schema import create_fno_quotes_table, create_options_quotes_table

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FNODatabaseWriterSubscriber(RedisSubscriber):
    """
    Subscribes to Redis quotes channel and writes FNO data to MySQL.
    
    Features:
    - Filters quotes by exchange_segment
    - Routes NSE_FNO/MCX_COMM → dhan_fno_quotes table
    - Routes OPTIDX/OPTSTK → dhan_options_quotes table
    - Batch writes for efficiency
    - Keeps only latest quote per instrument
    - Handles reconnection gracefully
    """
    
    def __init__(self, db_url: str, batch_size: int = 100, flush_interval: float = 1.0, debug: bool = False):
        """
        Initialize FNO DB writer.
        
        Args:
            db_url: SQLAlchemy database URL
            batch_size: Max quotes to batch before writing
            flush_interval: Max seconds between flushes
            debug: Enable debug logging
        """
        super().__init__()
        
        self.db_url = db_url
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.debug = debug
        
        # Database
        self._engine = None
        self._session_factory = None
        
        # Separate buffers for futures and options (LIST for time-series storage)
        self._fno_buffer: List[QuoteData] = []  # Futures & Commodities - ALL quotes
        self._options_buffer: List[QuoteData] = []  # Options - ALL quotes
        self._buffer_lock = threading.Lock()
        self._last_flush_time = time.time()
        
        # Stream tracking for catch-up
        self._last_stream_id = "0"  # Start from beginning
        self._stream_catch_up_done = False
        self._stream_read_thread = None
        
        # Stats
        self._db_stats = {
            'fno_quotes_written': 0,
            'options_quotes_written': 0,
            'total_batches_written': 0,
            'errors': 0,
            'quotes_filtered': defaultdict(int),  # Count per segment
            'stream_quotes_read': 0,
            'pubsub_quotes_received': 0,
            'fno_buffer_adds': 0,
            'options_buffer_adds': 0,
            'skipped_quotes': 0,
            'write_time_total_ms': 0,
            'write_count': 0
        }
        
        # Instrument cache: security_id -> {symbol, display_name, ...}
        self._instrument_cache: Dict[int, Dict] = {}
        
        # Redis for status reporting
        self._redis_client = None
        self._start_time = datetime.now()
        
        # Background flush thread
        self._flush_thread: Optional[threading.Thread] = None
        self._flush_running = False
        
        # Thread pool for parallel database writes
        self._write_executor: Optional[ThreadPoolExecutor] = None
        self._num_write_threads = 4  # Parallel write threads
        
        logger.info(f"[INIT] FNODatabaseWriterSubscriber initialized")
        logger.info(f"[INIT] Batch size: {batch_size}, Flush interval: {flush_interval}s, Debug: {debug}")
    
    def connect_db(self) -> bool:
        """Connect to database."""
        logger.info("[DB] Connecting to database...")
        try:
            self._engine = create_engine(
                self.db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,  # Increased pool size for parallel writes
                max_overflow=20,
                echo=self.debug
            )
            self._session_factory = sessionmaker(bind=self._engine)
            
            # Test connection
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("✅ [DB] Connected to database successfully")
            logger.info(f"[DB] Pool size: 10, Max overflow: 20")
            
            # Initialize thread pool for parallel writes
            self._write_executor = ThreadPoolExecutor(max_workers=self._num_write_threads)
            logger.info(f"[DB] Initialized write thread pool with {self._num_write_threads} workers")
            
            # Load instrument cache
            self._load_instrument_cache()
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    def _load_instrument_cache(self):
        """Load instrument mapping from dhan_instruments table."""
        logger.info("Loading instrument cache from dhan_instruments...")
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT security_id, symbol, display_name, instrument_type, 
                           underlying_symbol, expiry_date, strike_price, option_type
                    FROM dhan_instruments
                """))
                
                for row in result:
                    self._instrument_cache[int(row[0])] = {
                        'symbol': row[1] or '',
                        'display_name': row[2] or '',
                        'instrument_type': row[3] or '',
                        'underlying_symbol': row[4] or '',
                        'expiry_date': row[5],
                        'strike_price': float(row[6]) if row[6] else None,
                        'option_type': row[7] or ''
                    }
            
            logger.info(f"✅ Loaded {len(self._instrument_cache):,} instruments into cache")
        except Exception as e:
            logger.error(f"❌ Failed to load instrument cache: {e}")
            # Continue without cache - will use security_id as fallback
    
    def _get_instrument_info(self, security_id: int) -> Dict:
        """Get instrument info from cache, with fallback to security_id."""
        if security_id in self._instrument_cache:
            return self._instrument_cache[security_id]
        else:
            # Fallback: use security_id as symbol
            return {
                'symbol': str(security_id),
                'display_name': f'ID_{security_id}',
                'instrument_type': '',
                'underlying_symbol': '',
                'expiry_date': None,
                'strike_price': None,
                'option_type': ''
            }
    
    def setup_tables(self):
        """Ensure database tables exist."""
        logger.info("Setting up FNO database tables...")
        try:
            create_fno_quotes_table()
            create_options_quotes_table()
            logger.info("✅ FNO database tables ready")
        except Exception as e:
            logger.error(f"❌ Failed to setup tables: {e}")
            raise
    
    def _read_stream_catchup(self):
        """
        Read quotes from Redis stream using Consumer Groups.
        
        Consumer Groups track which messages have been processed:
        - Messages are read but stay in stream
        - After successful DB write, we ACK the messages
        - On restart, only UNACKED messages are re-read (pending)
        - Optionally trim old messages after processing
        """
        logger.info("[STREAM] Starting stream catch-up with Consumer Groups...")
        
        CONSUMER_GROUP = "fno_db_writers"
        CONSUMER_NAME = f"writer_{os.getpid()}"  # Unique per process
        
        # Create consumer group if it doesn't exist
        try:
            self._client.xgroup_create(STREAM_QUOTES, CONSUMER_GROUP, id='0', mkstream=True)
            logger.info(f"[STREAM] Created consumer group '{CONSUMER_GROUP}'")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"[STREAM] Consumer group '{CONSUMER_GROUP}' already exists")
            else:
                raise
        
        # Check stream info
        try:
            stream_info = self._client.xinfo_stream(STREAM_QUOTES)
            stream_length = stream_info.get('length', 0)
            logger.info(f"[STREAM] Stream has {stream_length:,} messages")
        except:
            stream_length = 0
        
        # First: Process any PENDING messages (from previous crashed runs)
        pending_processed = self._process_pending_messages(CONSUMER_GROUP, CONSUMER_NAME)
        logger.info(f"[STREAM] Processed {pending_processed} pending messages from previous runs")
        
        # Then: Read NEW messages (never read before)
        MAX_CATCHUP_MESSAGES = 200000  # Increased limit
        batch_count = 0
        total_quotes_read = 0
        messages_to_ack = []
        
        try:
            while not self._stream_catch_up_done and total_quotes_read < MAX_CATCHUP_MESSAGES:
                try:
                    # XREADGROUP reads only NEW messages (not yet read by this group)
                    # ">" means "messages never delivered to any consumer in this group"
                    entries = self._client.xreadgroup(
                        CONSUMER_GROUP, 
                        CONSUMER_NAME,
                        {STREAM_QUOTES: ">"},  # ">" = new messages only
                        count=1000,
                        block=100  # Wait 100ms for new messages
                    )
                    
                    if not entries:
                        # No more NEW messages - catch-up complete
                        logger.info(f"[STREAM] No more new messages after {total_quotes_read:,} quotes")
                        break
                    
                    for stream, messages in entries:
                        for msg_id, msg_data in messages:
                            if total_quotes_read >= MAX_CATCHUP_MESSAGES:
                                break
                                
                            try:
                                # Parse message
                                quote_dict = {}
                                for key, value in msg_data.items():
                                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                                    val_str = value.decode('utf-8') if isinstance(value, bytes) else value
                                    
                                    if key_str in ['security_id', 'ltq', 'ltt', 'volume', 'total_sell_qty', 'total_buy_qty', 'exchange_segment', 'open_interest']:
                                        quote_dict[key_str] = int(val_str) if val_str else 0
                                    elif key_str in ['ltp', 'atp', 'day_open', 'day_close', 'day_high', 'day_low', 'prev_close', 'received_at']:
                                        quote_dict[key_str] = float(val_str) if val_str else 0.0
                                    else:
                                        quote_dict[key_str] = val_str
                                
                                quote = QuoteData.from_dict(quote_dict)
                                self.on_quote(quote)
                                messages_to_ack.append(msg_id)
                                total_quotes_read += 1
                                
                            except Exception as e:
                                logger.error(f"[STREAM] Error parsing message {msg_id}: {e}")
                                messages_to_ack.append(msg_id)  # ACK even on error to avoid re-processing
                    
                    batch_count += 1
                    
                    # ACK messages in batches of 1000
                    if len(messages_to_ack) >= 1000:
                        self._ack_messages(CONSUMER_GROUP, messages_to_ack)
                        messages_to_ack = []
                    
                    # Log progress every 10 batches
                    if batch_count % 10 == 0:
                        with self._buffer_lock:
                            fno_buf_size = len(self._fno_buffer)
                            opt_buf_size = len(self._options_buffer)
                        logger.info(f"[STREAM] Read {batch_count} batches, {total_quotes_read:,} quotes, Buffer=[FNO:{fno_buf_size}, OPT:{opt_buf_size}]")
                        
                except Exception as e:
                    logger.error(f"[STREAM] Error reading stream: {e}")
                    time.sleep(0.1)
            
            # ACK remaining messages
            if messages_to_ack:
                self._ack_messages(CONSUMER_GROUP, messages_to_ack)
            
            # Catch-up complete
            self._stream_catch_up_done = True
            logger.info(f"[STREAM] ===== CATCH-UP COMPLETE =====")
            logger.info(f"[STREAM] Processed {batch_count} batches, {total_quotes_read:,} quotes")
            
            with self._buffer_lock:
                fno_buf_size = len(self._fno_buffer)
                opt_buf_size = len(self._options_buffer)
            logger.info(f"[STREAM] Final buffer state: FNO={fno_buf_size}, OPT={opt_buf_size}")
            
            # Final flush
            if self._fno_buffer or self._options_buffer:
                logger.info("[STREAM] Flushing remaining quotes before subscribing to real-time...")
                self._flush_buffers()
            
            logger.info(f"[STREAM] ===== READY FOR REAL-TIME =====")
                    
        except Exception as e:
            logger.error(f"[STREAM] Catch-up failed: {e}")
            import traceback
            logger.error(f"[STREAM] Traceback: {traceback.format_exc()}")
            self._stream_catch_up_done = True
    
    def _process_pending_messages(self, group: str, consumer: str) -> int:
        """Process pending messages from previous crashed runs."""
        processed = 0
        try:
            while True:
                # Read pending messages (messages delivered but not ACKed)
                pending = self._client.xreadgroup(
                    group, consumer,
                    {STREAM_QUOTES: "0"},  # "0" = read pending messages
                    count=1000
                )
                
                if not pending:
                    break
                    
                messages_to_ack = []
                for stream, messages in pending:
                    if not messages:
                        break
                    for msg_id, msg_data in messages:
                        try:
                            quote_dict = {}
                            for key, value in msg_data.items():
                                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                                val_str = value.decode('utf-8') if isinstance(value, bytes) else value
                                
                                if key_str in ['security_id', 'ltq', 'ltt', 'volume', 'total_sell_qty', 'total_buy_qty', 'exchange_segment', 'open_interest']:
                                    quote_dict[key_str] = int(val_str) if val_str else 0
                                elif key_str in ['ltp', 'atp', 'day_open', 'day_close', 'day_high', 'day_low', 'prev_close', 'received_at']:
                                    quote_dict[key_str] = float(val_str) if val_str else 0.0
                                else:
                                    quote_dict[key_str] = val_str
                            
                            quote = QuoteData.from_dict(quote_dict)
                            self.on_quote(quote)
                            messages_to_ack.append(msg_id)
                            processed += 1
                        except Exception as e:
                            logger.error(f"[STREAM] Error processing pending {msg_id}: {e}")
                            messages_to_ack.append(msg_id)
                
                if messages_to_ack:
                    self._ack_messages(group, messages_to_ack)
                    
                if not messages:
                    break
                    
        except Exception as e:
            logger.error(f"[STREAM] Error processing pending messages: {e}")
        
        return processed
    
    def _ack_messages(self, group: str, message_ids: list):
        """Acknowledge messages as processed."""
        try:
            if message_ids:
                self._client.xack(STREAM_QUOTES, group, *message_ids)
        except Exception as e:
            logger.error(f"[STREAM] Error ACKing messages: {e}")
    
    def on_quote(self, quote: QuoteData):
        """
        Handle incoming quote - buffer for batch write.
        
        Filters by exchange_segment (integer code):
        - 2 = NSE_FNO → dhan_fno_quotes
        - 3, 4 = MCX, etc. → dhan_fno_quotes
        - 5, 6 = Options → dhan_options_quotes
        """
        with self._buffer_lock:
            # Get segment as integer or string
            segment = getattr(quote, 'exchange_segment', None)
            
            # Convert to int if it's a string
            if isinstance(segment, str):
                try:
                    segment = int(segment)
                except (ValueError, TypeError):
                    if self.debug:
                        logger.debug(f"[SKIP] Could not parse segment={segment}")
                    return
            
            # Map Dhan exchange segment codes to table targets
            # 1=NSE_EQ, 2=NSE_FNO, 3=NSE_CURRENCY, etc., 4=BSE_FNO, 5=MCX, 6+=OPTIONS
            is_fno = segment in [2, 4, 5]  # NSE_FNO, BSE_FNO, MCX
            is_options = segment in [6, 7, 8, 9]  # Various option segments
            
            if is_fno:
                # Futures & Commodities - append ALL quotes (time-series)
                self._fno_buffer.append(quote)
                self._db_stats['quotes_filtered']['FNO'] += 1
                
                if self.debug:
                    logger.debug(f"[FNO] security_id={quote.security_id}, seg={segment}")
                
            elif is_options:
                # Options - append ALL quotes (time-series)
                self._options_buffer.append(quote)
                self._db_stats['quotes_filtered']['OPTIONS'] += 1
                self._db_stats['options_buffer_adds'] += 1
                
                if self.debug:
                    logger.debug(f"[OPT] security_id={quote.security_id}, seg={segment}")
            
            else:
                # Unknown segment - skip (probably equities)
                self._db_stats['skipped_quotes'] += 1
                if not self._stream_catch_up_done:
                    # Log only during catch-up to debug
                    if segment not in [1, 3]:  # Don't spam logs for expected segments
                        logger.info(f"[SKIP-CATCHUP] segment={segment}, sec_id={quote.security_id}")
                return
            
            # Check if we should flush
            total_buffered = len(self._fno_buffer) + len(self._options_buffer)
            if total_buffered >= self.batch_size:
                self._flush_buffers()
    
    def _flush_buffers(self):
        """Flush both FNO and Options buffers to database using parallel writes."""
        flush_start = time.time()
        
        with self._buffer_lock:
            fno_quotes = self._fno_buffer.copy()  # Copy list
            options_quotes = self._options_buffer.copy()  # Copy list
            
            self._fno_buffer.clear()
            self._options_buffer.clear()
        
        if not fno_quotes and not options_quotes:
            logger.debug("[FLUSH] No quotes to flush")
            return
        
        logger.info(f"[FLUSH] Starting parallel flush: FNO={len(fno_quotes)}, OPT={len(options_quotes)}")
        
        # Submit writes to thread pool for parallel execution
        futures = []
        
        if fno_quotes and self._write_executor:
            # Split FNO quotes into chunks for parallel processing
            chunk_size = max(50, len(fno_quotes) // self._num_write_threads)
            fno_chunks = [fno_quotes[i:i+chunk_size] for i in range(0, len(fno_quotes), chunk_size)]
            
            for i, chunk in enumerate(fno_chunks):
                future = self._write_executor.submit(self._write_fno_quotes, chunk)
                futures.append(('FNO', i, len(chunk), future))
                logger.debug(f"[FLUSH] Submitted FNO chunk {i+1}/{len(fno_chunks)} ({len(chunk)} quotes)")
        
        if options_quotes and self._write_executor:
            # Split Options quotes into chunks for parallel processing
            chunk_size = max(50, len(options_quotes) // self._num_write_threads)
            opt_chunks = [options_quotes[i:i+chunk_size] for i in range(0, len(options_quotes), chunk_size)]
            
            for i, chunk in enumerate(opt_chunks):
                future = self._write_executor.submit(self._write_options_quotes, chunk)
                futures.append(('OPT', i, len(chunk), future))
                logger.debug(f"[FLUSH] Submitted OPT chunk {i+1}/{len(opt_chunks)} ({len(chunk)} quotes)")
        
        # Wait for all writes to complete
        success_count = 0
        error_count = 0
        for table_type, chunk_idx, chunk_size, future in futures:
            try:
                future.result(timeout=30)  # 30 second timeout per write
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"[FLUSH] {table_type} chunk {chunk_idx} failed: {e}")
        
        flush_duration = (time.time() - flush_start) * 1000
        self._db_stats['write_time_total_ms'] += flush_duration
        self._db_stats['write_count'] += 1
        
        avg_write_time = self._db_stats['write_time_total_ms'] / self._db_stats['write_count']
        
        logger.info(f"[FLUSH] ✅ Completed in {flush_duration:.1f}ms | "
                   f"Success: {success_count}/{len(futures)} | "
                   f"Avg write time: {avg_write_time:.1f}ms")
        
        if not fno_quotes and not options_quotes:
            logger.debug("[FLUSH] No quotes to flush")
        
        self._last_flush_time = time.time()
    
    def _write_fno_quotes(self, quotes: List[QuoteData]):
        """Write futures and commodity quotes to dhan_fno_quotes table using bulk insert."""
        if not quotes:
            return
        
        write_start = time.time()
        thread_id = threading.current_thread().name
        
        try:
            # Prepare all params first
            all_params = []
            seg_map = {2: 'NSE_FNO', 4: 'BSE_FNO', 5: 'MCX_COMM'}
            
            prep_start = time.time()
            for quote in quotes:
                seg_code = quote.exchange_segment
                if isinstance(seg_code, str):
                    seg_code = int(seg_code)
                exchange_seg = seg_map.get(seg_code, f'SEG_{seg_code}')
                
                # Get instrument info from cache
                inst_info = self._get_instrument_info(quote.security_id)
                
                all_params.append({
                    'security_id': quote.security_id,
                    'exchange_segment': exchange_seg,
                    'symbol': inst_info['symbol'],
                    'ltp': quote.ltp,
                    'ltq': quote.ltq,
                    'ltt': quote.ltt,
                    'atp': quote.atp,
                    'volume': quote.volume,
                    'total_sell_qty': quote.total_sell_qty,
                    'total_buy_qty': quote.total_buy_qty,
                    'day_open': quote.day_open,
                    'day_close': quote.day_close,
                    'day_high': quote.day_high,
                    'day_low': quote.day_low,
                    'open_interest': getattr(quote, 'open_interest', 0) or 0
                })
            
            prep_time = (time.time() - prep_start) * 1000
            
            # Bulk insert with ON DUPLICATE KEY UPDATE (upsert - single round-trip)
            db_start = time.time()
            with self._engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO dhan_fno_quotes (
                            security_id, exchange_segment, symbol,
                            ltp, ltq, ltt, atp, volume, total_sell_qty, total_buy_qty,
                            day_open, day_close, day_high, day_low,
                            open_interest
                        ) VALUES (
                            :security_id, :exchange_segment, :symbol,
                            :ltp, :ltq, :ltt, :atp, :volume, :total_sell_qty, :total_buy_qty,
                            :day_open, :day_close, :day_high, :day_low,
                            :open_interest
                        )
                        ON DUPLICATE KEY UPDATE
                            ltp = VALUES(ltp),
                            ltq = VALUES(ltq),
                            atp = VALUES(atp),
                            volume = VALUES(volume),
                            total_sell_qty = VALUES(total_sell_qty),
                            total_buy_qty = VALUES(total_buy_qty),
                            day_open = VALUES(day_open),
                            day_close = VALUES(day_close),
                            day_high = VALUES(day_high),
                            day_low = VALUES(day_low),
                            open_interest = VALUES(open_interest)
                    """),
                    all_params
                )
                conn.commit()
            
            db_time = (time.time() - db_start) * 1000
            total_time = (time.time() - write_start) * 1000
            
            self._db_stats['fno_quotes_written'] += len(quotes)
            self._db_stats['total_batches_written'] += 1
            
            logger.info(f"[FNO-WRITE] ✅ {len(quotes)} quotes | Thread: {thread_id} | "
                       f"Prep: {prep_time:.1f}ms, DB: {db_time:.1f}ms, Total: {total_time:.1f}ms | "
                       f"Cumulative: {self._db_stats['fno_quotes_written']:,}")
            
        except Exception as e:
            logger.error(f"[FNO-WRITE] ❌ Error in thread {thread_id}: {e}")
            import traceback
            logger.error(f"[FNO-WRITE] Traceback: {traceback.format_exc()}")
            self._db_stats['errors'] += 1
    
    def _write_options_quotes(self, quotes: List[QuoteData]):
        """Write options quotes to dhan_options_quotes table using bulk insert."""
        if not quotes:
            return
        
        write_start = time.time()
        thread_id = threading.current_thread().name
        
        try:
            # Prepare all params first
            all_params = []
            seg_map = {6: 'OPTIDX', 7: 'OPTSTK'}
            
            prep_start = time.time()
            for quote in quotes:
                seg_code = quote.exchange_segment
                if isinstance(seg_code, str):
                    seg_code = int(seg_code)
                exchange_seg = seg_map.get(seg_code, f'OPT_{seg_code}')
                
                # Get instrument info from cache
                inst_info = self._get_instrument_info(quote.security_id)
                
                all_params.append({
                    'security_id': quote.security_id,
                    'exchange_segment': exchange_seg,
                    'symbol': inst_info['symbol'],
                    'ltp': quote.ltp,
                    'ltq': quote.ltq,
                    'ltt': quote.ltt,
                    'atp': quote.atp,
                    'volume': quote.volume,
                    'total_sell_qty': quote.total_sell_qty,
                    'total_buy_qty': quote.total_buy_qty,
                    'day_open': quote.day_open,
                    'day_close': quote.day_close,
                    'day_high': quote.day_high,
                    'day_low': quote.day_low,
                    'open_interest': getattr(quote, 'open_interest', 0) or 0
                })
            
            prep_time = (time.time() - prep_start) * 1000
            
            # Bulk insert with ON DUPLICATE KEY UPDATE (upsert - single round-trip)
            db_start = time.time()
            with self._engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO dhan_options_quotes (
                            security_id, exchange_segment, symbol,
                            ltp, ltq, ltt, atp, volume, total_sell_qty, total_buy_qty,
                            day_open, day_close, day_high, day_low,
                            open_interest
                        ) VALUES (
                            :security_id, :exchange_segment, :symbol,
                            :ltp, :ltq, :ltt, :atp, :volume, :total_sell_qty, :total_buy_qty,
                            :day_open, :day_close, :day_high, :day_low,
                            :open_interest
                        )
                        ON DUPLICATE KEY UPDATE
                            ltp = VALUES(ltp),
                            ltq = VALUES(ltq),
                            atp = VALUES(atp),
                            volume = VALUES(volume),
                            total_sell_qty = VALUES(total_sell_qty),
                            total_buy_qty = VALUES(total_buy_qty),
                            day_open = VALUES(day_open),
                            day_close = VALUES(day_close),
                            day_high = VALUES(day_high),
                            day_low = VALUES(day_low),
                            open_interest = VALUES(open_interest)
                    """),
                    all_params
                )
                conn.commit()
            
            db_time = (time.time() - db_start) * 1000
            total_time = (time.time() - write_start) * 1000
            
            self._db_stats['options_quotes_written'] += len(quotes)
            self._db_stats['total_batches_written'] += 1
            
            logger.info(f"[OPT-WRITE] ✅ {len(quotes)} quotes | Thread: {thread_id} | "
                       f"Prep: {prep_time:.1f}ms, DB: {db_time:.1f}ms, Total: {total_time:.1f}ms | "
                       f"Cumulative: {self._db_stats['options_quotes_written']:,}")
            
        except Exception as e:
            logger.error(f"[OPT-WRITE] ❌ Error in thread {thread_id}: {e}")
            import traceback
            logger.error(f"[OPT-WRITE] Traceback: {traceback.format_exc()}")
            self._db_stats['errors'] += 1
    
    def _flush_loop(self):
        """Background thread to periodically flush buffer."""
        logger.info(f"[FLUSH-LOOP] Started - interval={self.flush_interval}s, batch_size={self.batch_size}")
        loop_count = 0
        last_stats_time = time.time()
        
        while self._flush_running:
            time.sleep(0.5)  # Check every 500ms
            loop_count += 1
            
            now = time.time()
            if now - self._last_flush_time >= self.flush_interval:
                with self._buffer_lock:
                    fno_count = len(self._fno_buffer)
                    opt_count = len(self._options_buffer)
                    buffer_total = fno_count + opt_count
                    
                if buffer_total > 0:
                    logger.info(f"[FLUSH-LOOP] Triggering flush: FNO={fno_count}, OPT={opt_count}, total={buffer_total}")
                    self._flush_buffers()
                elif loop_count % 20 == 0:  # Log every 10 seconds
                    logger.debug(f"[FLUSH-LOOP] No quotes to flush (empty buffers)")
                self._last_flush_time = time.time()
            
            # Log detailed stats every 30 seconds
            if now - last_stats_time >= 30:
                last_stats_time = now
                logger.info("=" * 60)
                logger.info("[STATS] Periodic Statistics Report")
                logger.info(f"  FNO quotes written: {self._db_stats['fno_quotes_written']:,}")
                logger.info(f"  Options quotes written: {self._db_stats['options_quotes_written']:,}")
                logger.info(f"  Total batches: {self._db_stats['total_batches_written']:,}")
                logger.info(f"  Errors: {self._db_stats['errors']}")
                logger.info(f"  Skipped quotes: {self._db_stats['skipped_quotes']:,}")
                if self._db_stats['write_count'] > 0:
                    avg_time = self._db_stats['write_time_total_ms'] / self._db_stats['write_count']
                    logger.info(f"  Avg write time: {avg_time:.1f}ms")
                logger.info("=" * 60)
    
    def _init_redis_status(self):
        """Initialize Redis connection for status reporting."""
        try:
            self._redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self._redis_client.ping()
            logger.info("Redis status reporting initialized")
        except Exception as e:
            logger.warning(f"Redis status reporting not available: {e}")
            self._redis_client = None
    
    def _publish_status(self, connected: bool):
        """Publish writer status to Redis."""
        if not self._redis_client:
            return
        
        try:
            uptime = (datetime.now() - self._start_time).total_seconds()
            self._redis_client.hset(
                'fno:writer:status',
                mapping={
                    'connected': 'true' if connected else 'false',
                    'fno_quotes_written': str(self._db_stats['fno_quotes_written']),
                    'options_quotes_written': str(self._db_stats['options_quotes_written']),
                    'last_update': datetime.now().isoformat(),
                    'uptime_seconds': str(int(uptime)),
                    'status': 'running' if connected else 'stopped'
                }
            )
            self._redis_client.expire('fno:writer:status', 60)  # Expire after 60 seconds
        except Exception as e:
            logger.debug(f"Error publishing status: {e}")
    
    def _status_update_loop(self):
        """Background thread for updating Redis status."""
        while self._flush_running:
            try:
                self._publish_status(True)
                time.sleep(2)
            except Exception as e:
                logger.debug(f"Error in status update: {e}")
                time.sleep(5)
    
    def start(self):
        """Start the FNO DB writer subscriber."""
        # Initialize Redis status reporting
        self._init_redis_status()
        
        # Connect to database first
        if not self.connect_db():
            raise RuntimeError("Failed to connect to database")
        
        # Setup tables
        self.setup_tables()
        
        # Connect to Redis
        if not self.connect():
            raise RuntimeError("Failed to connect to Redis")
        
        # Start stream catch-up thread (read historical quotes)
        # This runs in parallel with Pub/Sub, both feeding into the same buffer
        self._stream_read_thread = threading.Thread(target=self._read_stream_catchup, daemon=True)
        self._stream_read_thread.start()
        
        # Start background flush thread FIRST (before subscribing)
        self._flush_running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        
        # Start status update thread
        status_thread = threading.Thread(target=self._status_update_loop, daemon=True)
        status_thread.start()
        
        # Subscribe to quotes channel (for real-time updates)
        # This will process new messages while stream catch-up happens in parallel
        self.subscribe([CHANNEL_QUOTES])
        
        logger.info("=" * 70)
        logger.info("[RUNNING] FNO Database Writer Subscriber is RUNNING")
        logger.info("=" * 70)
        logger.info(f"  Batch Size: {self.batch_size}")
        logger.info(f"  Flush Interval: {self.flush_interval}s")
        logger.info(f"  Debug Mode: {'ON' if self.debug else 'OFF'}")
        logger.info("")
        logger.info("  Writing to:")
        logger.info("    [X] dhan_fno_quotes (Futures & Commodities)")
        logger.info("    [X] dhan_options_quotes (Index & Stock Options)")
        logger.info("")
        logger.info("  Stream Catch-up: Running in background")
        logger.info("  Real-time Listener: Active")
        logger.info("  Press Ctrl+C to stop")
        logger.info("=" * 70)
        
        # Run the subscriber (blocking)
        self.run(blocking=True)
    
    def stop(self):
        """Stop the FNO DB writer."""
        logger.info("\n[STOP] Stopping FNO DB Writer...")
        
        # Set running flag to false first
        self._running = False
        self._flush_running = False
        self._stream_catch_up_done = True  # Stop stream catch-up
        
        # Stop flush thread first
        if self._flush_thread and self._flush_thread.is_alive():
            logger.info("  Waiting for flush thread to stop...")
            self._flush_thread.join(timeout=2)
        
        # Final flush BEFORE shutting down executor
        fno_quotes = []
        options_quotes = []
        with self._buffer_lock:
            if self._fno_buffer or self._options_buffer:
                logger.info("  Flushing remaining buffered quotes...")
                fno_quotes = list(self._fno_buffer.values())
                options_quotes = list(self._options_buffer.values())
                self._fno_buffer.clear()
                self._options_buffer.clear()
        
        # Write remaining quotes directly (before executor shutdown)
        if fno_quotes:
            try:
                self._write_fno_quotes(fno_quotes)
            except Exception as e:
                logger.error(f"  Error flushing FNO quotes: {e}")
        if options_quotes:
            try:
                self._write_options_quotes(options_quotes)
            except Exception as e:
                logger.error(f"  Error flushing Options quotes: {e}")
        
        # NOW shutdown ThreadPoolExecutor
        if self._write_executor:
            logger.info("  Shutting down write executor...")
            try:
                self._write_executor.shutdown(wait=True, cancel_futures=True)
            except Exception as e:
                logger.warning(f"  Executor shutdown warning: {e}")
        
        # Print stats
        logger.info("=" * 70)
        logger.info("[STATS] Final Statistics:")
        logger.info(f"  FNO Quotes Written: {self._db_stats['fno_quotes_written']:,}")
        logger.info(f"  Options Quotes Written: {self._db_stats['options_quotes_written']:,}")
        logger.info(f"  Total Batches: {self._db_stats['total_batches_written']:,}")
        logger.info(f"  Errors: {self._db_stats['errors']}")
        logger.info("")
        logger.info("  Quotes Received by Segment:")
        for segment, count in self._db_stats['quotes_filtered'].items():
            logger.info(f"    - {segment}: {count:,}")
        logger.info("=" * 70)
        
        # Publish stopped status
        try:
            self._publish_status(False)
        except:
            pass
        
        # Disconnect from Redis
        try:
            super().stop()
        except Exception as e:
            logger.warning(f"  Redis disconnect warning: {e}")
        
        # Dispose database engine
        if self._engine:
            try:
                self._engine.dispose()
            except:
                pass
        
        logger.info("[OK] FNO DB Writer stopped")
    
    def get_db_stats(self) -> Dict:
        """Get database writer statistics."""
        return {
            **self.get_stats(),
            **self._db_stats
        }


def build_db_url() -> str:
    """Build database URL from environment variables."""
    password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
    return (
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
        f"{password}@"
        f"{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"dhan_trading?charset=utf8mb4"
    )


def main():
    """Run the FNO database writer subscriber."""
    parser = argparse.ArgumentParser(
        description="FNO Database Writer - Subscribe to Redis and write to MySQL"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for database writes (default: 100)'
    )
    parser.add_argument(
        '--flush-interval',
        type=float,
        default=1.0,
        help='Flush interval in seconds (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("=" * 70)
    print("FNO Database Writer Subscriber")
    print("=" * 70)
    print()
    
    db_url = build_db_url()
    
    writer = FNODatabaseWriterSubscriber(
        db_url=db_url,
        batch_size=args.batch_size,
        flush_interval=args.flush_interval,
        debug=args.debug
    )
    
    # Handle Ctrl+C - use a flag to track if already stopping
    stopping = False
    
    def signal_handler(sig, frame):
        nonlocal stopping
        if stopping:
            # Second Ctrl+C - force exit
            print("\n[FORCE] Second Ctrl+C - forcing exit...")
            os._exit(1)
        
        stopping = True
        print("\n[STOP] Caught Ctrl+C, stopping gracefully...")
        print("[STOP] Press Ctrl+C again to force exit")
        
        try:
            writer.stop()
        except Exception as e:
            print(f"[STOP] Error during stop: {e}")
        finally:
            sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        writer.start()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        writer.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
