"""
WebSocket Feed Service
======================
Connects to Dhan WebSocket and receives live market data.
Parses binary packets and publishes to Redis (Pub/Sub + Streams).

This service is a PURE PUBLISHER - it only fetches data and publishes.
No database writes, no visualization.
"""
import os
import sys
import struct
import asyncio
import logging
import signal
import json
import time
from datetime import datetime, time as dt_time
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass
import threading

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    websockets = None
    print("WARNING: websockets package not installed. Run: pip install websockets")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.market_feed.feed_config import (
    FeedConfig, ExchangeSegment, FeedRequestCode, FeedResponseCode
)
from dhan_trading.market_feed.redis_publisher import (
    RedisPublisher, TickData, QuoteData, DepthData
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BinaryParser:
    """
    Parse binary packets from Dhan WebSocket.
    
    All data is Little Endian.
    """
    
    @staticmethod
    def parse_header(data: bytes) -> Dict:
        """
        Parse 8-byte response header.
        
        Bytes:
            0: Response code (1 byte)
            1-2: Message length (int16)
            3: Exchange segment (1 byte)
            4-7: Security ID (int32)
        """
        if len(data) < 8:
            return {}
        
        response_code = data[0]
        msg_length = struct.unpack('<H', data[1:3])[0]
        exchange_segment = data[3]
        security_id = struct.unpack('<I', data[4:8])[0]
        
        return {
            'response_code': response_code,
            'msg_length': msg_length,
            'exchange_segment': exchange_segment,
            'security_id': security_id
        }
    
    @staticmethod
    def parse_ticker(data: bytes) -> Optional[TickData]:
        """
        Parse ticker packet (LTP + LTT).
        
        Bytes:
            0-7: Header
            8-11: LTP (float32)
            12-15: LTT (int32 EPOCH)
        """
        if len(data) < 16:
            return None
        
        header = BinaryParser.parse_header(data)
        if header.get('response_code') != FeedResponseCode.TICKER_PACKET:
            return None
        
        ltp = struct.unpack('<f', data[8:12])[0]
        ltt = struct.unpack('<I', data[12:16])[0]
        
        return TickData(
            security_id=header['security_id'],
            exchange_segment=header['exchange_segment'],
            ltp=round(ltp, 4),
            ltt=ltt,
            received_at=time.time()
        )
    
    @staticmethod
    def parse_quote(data: bytes) -> Optional[QuoteData]:
        """
        Parse quote packet.
        
        Bytes:
            0-7: Header
            8-11: LTP (float32)
            12-13: LTQ (int16)
            14-17: LTT (int32)
            18-21: ATP (float32)
            22-25: Volume (int32)
            26-29: Total Sell Qty (int32)
            30-33: Total Buy Qty (int32)
            34-37: Day Open (float32)
            38-41: Day Close (float32)
            42-45: Day High (float32)
            46-49: Day Low (float32)
        """
        if len(data) < 50:
            return None
        
        header = BinaryParser.parse_header(data)
        if header.get('response_code') != FeedResponseCode.QUOTE_PACKET:
            return None
        
        ltp = struct.unpack('<f', data[8:12])[0]
        ltq = struct.unpack('<H', data[12:14])[0]
        ltt = struct.unpack('<I', data[14:18])[0]
        atp = struct.unpack('<f', data[18:22])[0]
        volume = struct.unpack('<I', data[22:26])[0]
        total_sell_qty = struct.unpack('<I', data[26:30])[0]
        total_buy_qty = struct.unpack('<I', data[30:34])[0]
        day_open = struct.unpack('<f', data[34:38])[0]
        day_close = struct.unpack('<f', data[38:42])[0]
        day_high = struct.unpack('<f', data[42:46])[0]
        day_low = struct.unpack('<f', data[46:50])[0]
        
        return QuoteData(
            security_id=header['security_id'],
            exchange_segment=header['exchange_segment'],
            ltp=round(ltp, 4),
            ltq=ltq,
            ltt=ltt,
            atp=round(atp, 4),
            volume=volume,
            total_sell_qty=total_sell_qty,
            total_buy_qty=total_buy_qty,
            day_open=round(day_open, 4),
            day_close=round(day_close, 4),
            day_high=round(day_high, 4),
            day_low=round(day_low, 4),
            received_at=time.time()
        )
    
    @staticmethod
    def parse_oi(data: bytes) -> Optional[Dict]:
        """
        Parse OI packet.
        
        Bytes:
            0-7: Header
            8-11: OI (int32)
        """
        if len(data) < 12:
            return None
        
        header = BinaryParser.parse_header(data)
        if header.get('response_code') != FeedResponseCode.OI_PACKET:
            return None
        
        oi = struct.unpack('<I', data[8:12])[0]
        
        return {
            'security_id': header['security_id'],
            'exchange_segment': header['exchange_segment'],
            'open_interest': oi
        }
    
    @staticmethod
    def parse_prev_close(data: bytes) -> Optional[Dict]:
        """
        Parse previous close packet.
        
        Bytes:
            0-7: Header
            8-11: Prev Close (float32)
            12-15: Prev OI (int32)
        """
        if len(data) < 16:
            return None
        
        header = BinaryParser.parse_header(data)
        if header.get('response_code') != FeedResponseCode.PREV_CLOSE_PACKET:
            return None
        
        prev_close = struct.unpack('<f', data[8:12])[0]
        prev_oi = struct.unpack('<I', data[12:16])[0]
        
        return {
            'security_id': header['security_id'],
            'exchange_segment': header['exchange_segment'],
            'prev_close': round(prev_close, 4),
            'prev_oi': prev_oi
        }
    
    @staticmethod
    def parse_full_packet(data: bytes) -> Optional[DepthData]:
        """
        Parse full packet with market depth.
        
        Bytes:
            0-7: Header
            8-11: LTP (float32)
            12-13: LTQ (int16)
            14-17: LTT (int32)
            18-21: ATP (float32)
            22-25: Volume (int32)
            26-29: Total Sell Qty (int32)
            30-33: Total Buy Qty (int32)
            34-37: OI (int32)
            38-41: OI High (int32)
            42-45: OI Low (int32)
            46-49: Day Open (float32)
            50-53: Day Close (float32)
            54-57: Day High (float32)
            58-61: Day Low (float32)
            62-161: Market Depth (5 x 20 bytes)
        """
        if len(data) < 162:
            return None
        
        header = BinaryParser.parse_header(data)
        if header.get('response_code') != FeedResponseCode.FULL_PACKET:
            return None
        
        ltp = struct.unpack('<f', data[8:12])[0]
        ltq = struct.unpack('<H', data[12:14])[0]
        ltt = struct.unpack('<I', data[14:18])[0]
        atp = struct.unpack('<f', data[18:22])[0]
        volume = struct.unpack('<I', data[22:26])[0]
        total_sell_qty = struct.unpack('<I', data[26:30])[0]
        total_buy_qty = struct.unpack('<I', data[30:34])[0]
        oi = struct.unpack('<I', data[34:38])[0]
        oi_high = struct.unpack('<I', data[38:42])[0]
        oi_low = struct.unpack('<I', data[42:46])[0]
        day_open = struct.unpack('<f', data[46:50])[0]
        day_close = struct.unpack('<f', data[50:54])[0]
        day_high = struct.unpack('<f', data[54:58])[0]
        day_low = struct.unpack('<f', data[58:62])[0]
        
        # Parse market depth (5 levels)
        bid_prices = []
        bid_qtys = []
        ask_prices = []
        ask_qtys = []
        
        for i in range(5):
            offset = 62 + (i * 20)
            bid_qty = struct.unpack('<I', data[offset:offset+4])[0]
            ask_qty = struct.unpack('<I', data[offset+4:offset+8])[0]
            bid_price = struct.unpack('<f', data[offset+12:offset+16])[0]
            ask_price = struct.unpack('<f', data[offset+16:offset+20])[0]
            
            bid_prices.append(round(bid_price, 4))
            bid_qtys.append(bid_qty)
            ask_prices.append(round(ask_price, 4))
            ask_qtys.append(ask_qty)
        
        return DepthData(
            security_id=header['security_id'],
            exchange_segment=header['exchange_segment'],
            ltp=round(ltp, 4),
            ltq=ltq,
            ltt=ltt,
            atp=round(atp, 4),
            volume=volume,
            total_sell_qty=total_sell_qty,
            total_buy_qty=total_buy_qty,
            open_interest=oi,
            oi_high=oi_high,
            oi_low=oi_low,
            day_open=round(day_open, 4),
            day_close=round(day_close, 4),
            day_high=round(day_high, 4),
            day_low=round(day_low, 4),
            bid_prices=bid_prices,
            bid_qtys=bid_qtys,
            ask_prices=ask_prices,
            ask_qtys=ask_qtys,
            received_at=time.time()
        )
    
    @staticmethod
    def parse_disconnect(data: bytes) -> Optional[Dict]:
        """Parse disconnect packet."""
        if len(data) < 10:
            return None
        
        header = BinaryParser.parse_header(data)
        if header.get('response_code') != FeedResponseCode.DISCONNECT:
            return None
        
        disconnect_code = struct.unpack('<H', data[8:10])[0]
        
        return {
            'disconnect_code': disconnect_code
        }


class DhanFeedService:
    """
    WebSocket feed service for Dhan market data.
    
    Connects to Dhan WebSocket, subscribes to instruments,
    parses binary data, and PUBLISHES to Redis (Pub/Sub + Streams).
    
    This is a PURE PUBLISHER - no database writes, no visualization.
    """
    
    def __init__(self, config: Optional[FeedConfig] = None):
        if websockets is None:
            raise ImportError("websockets package required. Install with: pip install websockets")
        
        self.config = config or FeedConfig()
        self.config.validate()
        
        # Use RedisPublisher instead of queue
        self.redis = RedisPublisher(self.config)
        self.ws: Optional[WebSocketClientProtocol] = None
        
        self._running = False
        self._reconnecting = False
        self._subscribed_instruments: List[Dict] = []
        
        # Stats
        self._stats = {
            'ticks_received': 0,
            'quotes_received': 0,
            'errors': 0,
            'last_tick_time': None,
            'connected_at': None
        }
        
        # Callbacks
        self._on_tick: Optional[Callable] = None
        self._on_quote: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        
        # OI and prev close cache
        self._oi_cache: Dict[int, int] = {}
        self._prev_close_cache: Dict[int, float] = {}
    
    def set_callbacks(self, 
                     on_tick: Optional[Callable] = None,
                     on_quote: Optional[Callable] = None,
                     on_disconnect: Optional[Callable] = None):
        """Set callback functions for events."""
        self._on_tick = on_tick
        self._on_quote = on_quote
        self._on_disconnect = on_disconnect
    
    async def connect(self) -> bool:
        """Connect to Dhan WebSocket."""
        try:
            logger.info(f"Connecting to Dhan WebSocket...")
            
            self.ws = await websockets.connect(
                self.config.ws_url,
                ping_interval=self.config.PING_INTERVAL_SECONDS,
                ping_timeout=self.config.PING_TIMEOUT_SECONDS
            )
            
            self._stats['connected_at'] = datetime.now()
            logger.info("[OK] Connected to Dhan WebSocket")
            
            # Connect to Redis
            if not self.redis.connect():
                logger.error("Failed to connect to Redis")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        self._running = False
        
        if self.ws:
            # Send disconnect request
            try:
                await self.ws.send(json.dumps({"RequestCode": FeedRequestCode.DISCONNECT}))
            except:
                pass
            
            await self.ws.close()
            self.ws = None
        
        self.redis.disconnect()
        logger.info("Disconnected from Dhan WebSocket")
    
    async def subscribe(self, instruments: List[Dict], 
                       feed_type: str = "QUOTE") -> bool:
        """
        Subscribe to instruments.
        
        Args:
            instruments: List of dicts with 'security_id' and 'exchange_segment'
            feed_type: TICKER, QUOTE, or FULL
        """
        if not self.ws:
            logger.error("Not connected")
            return False
        
        # Map feed type to request code
        request_codes = {
            'TICKER': FeedRequestCode.SUBSCRIBE_TICKER,
            'QUOTE': FeedRequestCode.SUBSCRIBE_QUOTE,
            'FULL': FeedRequestCode.SUBSCRIBE_FULL
        }
        request_code = request_codes.get(feed_type, FeedRequestCode.SUBSCRIBE_QUOTE)
        
        # Split into batches of 100
        batch_size = self.config.MAX_INSTRUMENTS_PER_MESSAGE
        
        for i in range(0, len(instruments), batch_size):
            batch = instruments[i:i + batch_size]
            
            instrument_list = []
            for inst in batch:
                # Get exchange segment string
                segment = inst.get('exchange_segment', '')
                if isinstance(segment, int):
                    segment = ExchangeSegment.CODE_TO_NAME.get(segment, 'NSE_EQ')
                
                instrument_list.append({
                    "ExchangeSegment": segment,
                    "SecurityId": str(inst['security_id'])
                })
            
            request = {
                "RequestCode": request_code,
                "InstrumentCount": len(instrument_list),
                "InstrumentList": instrument_list
            }
            
            logger.info(f"Sending subscription: {json.dumps(request)}")
            await self.ws.send(json.dumps(request))
            logger.info(f"Subscribed batch of {len(batch)} instruments ({feed_type})")
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        self._subscribed_instruments.extend(instruments)
        logger.info(f"Total subscribed: {len(self._subscribed_instruments)} instruments")
        
        return True
    
    async def unsubscribe(self, instruments: List[Dict], 
                         feed_type: str = "QUOTE") -> bool:
        """Unsubscribe from instruments."""
        if not self.ws:
            return False
        
        request_codes = {
            'TICKER': FeedRequestCode.UNSUBSCRIBE_TICKER,
            'QUOTE': FeedRequestCode.UNSUBSCRIBE_QUOTE,
            'FULL': FeedRequestCode.UNSUBSCRIBE_FULL
        }
        request_code = request_codes.get(feed_type, FeedRequestCode.UNSUBSCRIBE_QUOTE)
        
        instrument_list = []
        for inst in instruments:
            segment = inst.get('exchange_segment', 'NSE_EQ')
            instrument_list.append({
                "ExchangeSegment": segment,
                "SecurityId": str(inst['security_id'])
            })
        
        request = {
            "RequestCode": request_code,
            "InstrumentCount": len(instrument_list),
            "InstrumentList": instrument_list
        }
        
        await self.ws.send(json.dumps(request))
        logger.info(f"Unsubscribed {len(instruments)} instruments")
        
        return True
    
    def _handle_message(self, data: bytes):
        """Handle incoming binary message."""
        if len(data) < 8:
            logger.debug(f"Received short message: {len(data)} bytes")
            return
        
        # Parse header to determine packet type
        response_code = data[0]
        
        try:
            if response_code == FeedResponseCode.TICKER_PACKET:
                tick = BinaryParser.parse_ticker(data)
                if tick:
                    self._stats['ticks_received'] += 1
                    self._stats['last_tick_time'] = datetime.now()
                    self.redis.publish_tick(tick)
                    if self._on_tick:
                        self._on_tick(tick)
            
            elif response_code == FeedResponseCode.QUOTE_PACKET:
                quote = BinaryParser.parse_quote(data)
                if quote:
                    # Add OI if cached
                    if quote.security_id in self._oi_cache:
                        quote.open_interest = self._oi_cache[quote.security_id]
                    
                    # Add prev_close if cached
                    if quote.security_id in self._prev_close_cache:
                        quote.prev_close = self._prev_close_cache[quote.security_id]
                    
                    self._stats['quotes_received'] += 1
                    self._stats['last_tick_time'] = datetime.now()
                    self.redis.publish_quote(quote)
                    
                    # Log every 10th quote
                    if self._stats['quotes_received'] % 10 == 1:
                        logger.info(f"Quote #{self._stats['quotes_received']}: ID={quote.security_id} LTP={quote.ltp} Vol={quote.volume}")
                    
                    if self._on_quote:
                        self._on_quote(quote)
            
            elif response_code == FeedResponseCode.OI_PACKET:
                oi_data = BinaryParser.parse_oi(data)
                if oi_data:
                    self._oi_cache[oi_data['security_id']] = oi_data['open_interest']
            
            elif response_code == FeedResponseCode.PREV_CLOSE_PACKET:
                prev_data = BinaryParser.parse_prev_close(data)
                if prev_data:
                    self._prev_close_cache[prev_data['security_id']] = prev_data['prev_close']
            
            elif response_code == FeedResponseCode.FULL_PACKET:
                depth = BinaryParser.parse_full_packet(data)
                if depth:
                    self._stats['quotes_received'] += 1
                    self.redis.publish_depth(depth)
            
            elif response_code == FeedResponseCode.DISCONNECT:
                disc = BinaryParser.parse_disconnect(data)
                logger.warning(f"Disconnect packet received: {disc}")
                if self._on_disconnect:
                    self._on_disconnect(disc)
            
            elif response_code == FeedResponseCode.INDEX_PACKET:
                # Index packet - similar to ticker
                pass
            
            elif response_code == FeedResponseCode.MARKET_STATUS_PACKET:
                # Market status
                pass
            
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"Error handling message: {e}")
    
    async def _receive_loop(self):
        """Main loop to receive WebSocket messages."""
        while self._running and self.ws:
            try:
                # Use timeout to allow checking _running flag periodically
                message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                
                if isinstance(message, bytes):
                    self._handle_message(message)
                else:
                    # Text message (shouldn't happen normally)
                    logger.debug(f"Text message: {message}")
            
            except asyncio.TimeoutError:
                # Timeout is expected, just continue to check _running flag
                continue
            except websockets.ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}")
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")
                self._stats['errors'] += 1
    
    async def run(self, instruments: List[Dict], feed_type: str = "QUOTE"):
        """
        Main run loop.
        
        Args:
            instruments: Instruments to subscribe
            feed_type: TICKER, QUOTE, or FULL
        """
        self._running = True
        
        while self._running:
            # Connect
            if not await self.connect():
                if not self._running:
                    break
                logger.error("Connection failed, retrying...")
                await asyncio.sleep(self.config.RECONNECT_DELAY_SECONDS)
                continue
            
            # Subscribe
            await self.subscribe(instruments, feed_type)
            
            # Receive loop
            await self._receive_loop()
            
            # Disconnected
            if self._running:
                logger.info("Reconnecting...")
                await asyncio.sleep(self.config.RECONNECT_DELAY_SECONDS)
        
        logger.info("Feed service run loop ended")
    
    def get_stats(self) -> Dict:
        """Get service statistics."""
        return {
            **self._stats,
            'queue_lengths': self.redis.get_queue_lengths() if self.redis._connected else {},
            'subscribed_count': len(self._subscribed_instruments)
        }
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        now = datetime.now().time()
        return self.config.PRE_MARKET_OPEN <= now <= self.config.POST_MARKET_CLOSE


def run_feed_service(instruments: List[Dict], feed_type: str = "QUOTE"):
    """Run the feed service (blocking)."""
    service = DhanFeedService()
    
    def on_quote(quote: QuoteData):
        logger.info(f"Quote: {quote.security_id} LTP={quote.ltp} Vol={quote.volume}")
    
    service.set_callbacks(on_quote=on_quote)
    
    try:
        asyncio.run(service.run(instruments, feed_type))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        asyncio.run(service.disconnect())


if __name__ == "__main__":
    # Test with dummy instruments
    test_instruments = [
        {"security_id": 26000, "exchange_segment": "NSE_FNO"},  # NIFTY FUT
    ]
    
    print("\n" + "="*50)
    print("Dhan Feed Service Test")
    print("="*50)
    print("\nNote: This requires valid DHAN_ACCESS_TOKEN and DHAN_CLIENT_ID")
    print("Set them in .env file before running.\n")
    
    try:
        run_feed_service(test_instruments)
    except ValueError as e:
        print(f"Configuration error: {e}")
