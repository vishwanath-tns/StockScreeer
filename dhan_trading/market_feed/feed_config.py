"""
Market Feed Configuration
=========================
Configuration for Dhan WebSocket feed and Redis queue.
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import time as dt_time
from enum import Enum, IntEnum
from dotenv import load_dotenv

load_dotenv()


class FeedMode(IntEnum):
    """Feed subscription modes."""
    TICKER = 15   # LTP only (minimal data)
    QUOTE = 17    # Full quote (LTP, volume, OHLC, etc.)
    FULL = 21     # Full with market depth


@dataclass
class FeedConfig:
    """Configuration for market feed service."""
    
    # Dhan WebSocket Configuration
    DHAN_WS_URL: str = "wss://api-feed.dhan.co"
    DHAN_WS_VERSION: int = 2
    DHAN_AUTH_TYPE: int = 2
    DHAN_ACCESS_TOKEN: str = field(default_factory=lambda: os.getenv("DHAN_ACCESS_TOKEN", ""))
    DHAN_CLIENT_ID: str = field(default_factory=lambda: os.getenv("DHAN_CLIENT_ID", ""))
    
    # Redis Configuration
    REDIS_HOST: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    REDIS_DB: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    REDIS_PASSWORD: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    
    # Queue names
    TICK_QUEUE: str = "dhan:ticks"
    QUOTE_QUEUE: str = "dhan:quotes"
    FULL_QUEUE: str = "dhan:full"
    
    # Market hours (IST)
    MARKET_OPEN: dt_time = dt_time(9, 15)
    MARKET_CLOSE: dt_time = dt_time(15, 30)
    PRE_MARKET_OPEN: dt_time = dt_time(9, 0)
    POST_MARKET_CLOSE: dt_time = dt_time(15, 45)
    
    # Connection settings
    MAX_INSTRUMENTS_PER_CONNECTION: int = 5000
    MAX_INSTRUMENTS_PER_MESSAGE: int = 100
    MAX_CONNECTIONS: int = 5
    RECONNECT_DELAY_SECONDS: int = 5
    PING_INTERVAL_SECONDS: int = 10
    PING_TIMEOUT_SECONDS: int = 40
    
    # Database writer settings
    DB_WRITE_BATCH_SIZE: int = 100
    DB_WRITE_INTERVAL_MS: int = 500
    
    @property
    def ws_url(self) -> str:
        """Build complete WebSocket URL with auth params."""
        return (
            f"{self.DHAN_WS_URL}"
            f"?version={self.DHAN_WS_VERSION}"
            f"&token={self.DHAN_ACCESS_TOKEN}"
            f"&clientId={self.DHAN_CLIENT_ID}"
            f"&authType={self.DHAN_AUTH_TYPE}"
        )
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        if not self.DHAN_ACCESS_TOKEN:
            errors.append("DHAN_ACCESS_TOKEN not set")
        if not self.DHAN_CLIENT_ID:
            errors.append("DHAN_CLIENT_ID not set")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True


# Exchange Segment codes (for WebSocket binary parsing)
class ExchangeSegment(IntEnum):
    """Exchange segment codes from Dhan."""
    IDX_I = 0        # Index
    NSE_EQ = 1       # NSE Equity Cash
    NSE_FNO = 2      # NSE Futures & Options
    NSE_CURRENCY = 3 # NSE Currency
    BSE_EQ = 4       # BSE Equity Cash
    MCX_COMM = 5     # MCX Commodity
    BSE_CURRENCY = 7 # BSE Currency
    BSE_FNO = 8      # BSE Futures & Options
    
    @classmethod
    def get_name(cls, code: int) -> str:
        """Get segment name from code."""
        for member in cls:
            if member.value == code:
                return member.name
        return "UNKNOWN"


# For backwards compatibility
ExchangeSegment.CODE_TO_NAME = {
    0: "IDX_I",
    1: "NSE_EQ",
    2: "NSE_FNO",
    3: "NSE_CURRENCY",
    4: "BSE_EQ",
    5: "MCX_COMM",
    7: "BSE_CURRENCY",
    8: "BSE_FNO",
}
ExchangeSegment.NAME_TO_CODE = {v: k for k, v in ExchangeSegment.CODE_TO_NAME.items()}


# Feed Request codes
class FeedRequestCode(IntEnum):
    """Feed request codes for WebSocket subscription."""
    CONNECT = 11
    DISCONNECT = 12
    SUBSCRIBE_TICKER = 15
    UNSUBSCRIBE_TICKER = 16
    SUBSCRIBE_QUOTE = 17
    UNSUBSCRIBE_QUOTE = 18
    SUBSCRIBE_FULL = 21
    UNSUBSCRIBE_FULL = 22
    SUBSCRIBE_DEPTH = 23
    UNSUBSCRIBE_DEPTH = 24


# Feed Response codes
class FeedResponseCode(IntEnum):
    """Feed response codes from WebSocket."""
    INDEX_PACKET = 1
    TICKER_PACKET = 2
    QUOTE_PACKET = 4
    OI_PACKET = 5
    PREV_CLOSE_PACKET = 6
    MARKET_STATUS_PACKET = 7
    FULL_PACKET = 8
    DISCONNECT = 50


# Instrument types
class InstrumentType:
    """Instrument type codes."""
    INDEX = "INDEX"
    FUTIDX = "FUTIDX"      # Futures of Index
    OPTIDX = "OPTIDX"      # Options of Index
    EQUITY = "EQUITY"
    FUTSTK = "FUTSTK"      # Futures of Stock
    OPTSTK = "OPTSTK"      # Options of Stock
    FUTCOM = "FUTCOM"      # Futures of Commodity
    OPTFUT = "OPTFUT"      # Options of Commodity Futures
    FUTCUR = "FUTCUR"      # Futures of Currency
    OPTCUR = "OPTCUR"      # Options of Currency
