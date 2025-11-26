"""
Event Models
============

Pydantic models for real-time market events with Protocol Buffer conversion.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .schemas.v1 import candle_data_pb2, market_breadth_pb2, fetch_status_pb2


# ============================================================================
# Enums
# ============================================================================

class FetchStatusType(str, Enum):
    """Publisher status types"""
    UNKNOWN = "UNKNOWN"
    STARTED = "STARTED"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    STOPPED = "STOPPED"
    CRASHED = "CRASHED"


# ============================================================================
# Candle Data Event
# ============================================================================

class CandleDataEvent(BaseModel):
    """Real-time OHLCV candle data for a single symbol"""
    
    schema_version: int = Field(default=1, description="Schema version for backward compatibility")
    symbol: str = Field(..., description="Stock symbol (e.g., 'RELIANCE.NS')")
    trade_date: str = Field(..., description="Trade date in ISO 8601 format (YYYY-MM-DD)")
    timestamp: int = Field(..., description="Unix epoch timestamp when data was fetched")
    prev_close: float = Field(..., description="Previous close price")
    open_price: float = Field(..., description="Opening price")
    high_price: float = Field(..., description="High price")
    low_price: float = Field(..., description="Low price")
    close_price: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")
    delivery_qty: Optional[int] = Field(None, description="Delivery quantity (NSE specific)")
    delivery_per: Optional[float] = Field(None, description="Delivery percentage (NSE specific)")
    data_source: str = Field(default="yahoo_finance", description="Data source identifier")
    series: Optional[str] = Field(None, description="Market series (e.g., 'EQ', 'BE')")
    exchange: Optional[str] = Field(None, description="Exchange identifier (e.g., 'NSE', 'BSE')")
    
    @field_validator('trade_date')
    @classmethod
    def validate_trade_date(cls, v: str) -> str:
        """Validate trade_date is ISO 8601 format"""
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"trade_date must be ISO 8601 format (YYYY-MM-DD), got: {v}")
        return v
    
    def to_proto(self) -> candle_data_pb2.CandleData:
        """Convert to Protocol Buffer message"""
        msg = candle_data_pb2.CandleData(
            schema_version=self.schema_version,
            symbol=self.symbol,
            trade_date=self.trade_date,
            timestamp=self.timestamp,
            prev_close=self.prev_close,
            open_price=self.open_price,
            high_price=self.high_price,
            low_price=self.low_price,
            close_price=self.close_price,
            volume=self.volume,
            data_source=self.data_source,
        )
        
        # Optional fields
        if self.delivery_qty is not None:
            msg.delivery_qty = self.delivery_qty
        if self.delivery_per is not None:
            msg.delivery_per = self.delivery_per
        if self.series is not None:
            msg.series = self.series
        if self.exchange is not None:
            msg.exchange = self.exchange
        
        return msg
    
    @classmethod
    def from_proto(cls, msg: candle_data_pb2.CandleData) -> "CandleDataEvent":
        """Create from Protocol Buffer message"""
        return cls(
            schema_version=msg.schema_version,
            symbol=msg.symbol,
            trade_date=msg.trade_date,
            timestamp=msg.timestamp,
            prev_close=msg.prev_close,
            open_price=msg.open_price,
            high_price=msg.high_price,
            low_price=msg.low_price,
            close_price=msg.close_price,
            volume=msg.volume,
            delivery_qty=msg.delivery_qty if msg.HasField("delivery_qty") else None,
            delivery_per=msg.delivery_per if msg.HasField("delivery_per") else None,
            data_source=msg.data_source,
            series=msg.series if msg.HasField("series") else None,
            exchange=msg.exchange if msg.HasField("exchange") else None,
        )


# ============================================================================
# Market Breadth Event
# ============================================================================

class MarketBreadthEvent(BaseModel):
    """Aggregated market-wide statistics"""
    
    schema_version: int = Field(default=1, description="Schema version for backward compatibility")
    index_name: str = Field(..., description="Index identifier (e.g., 'NIFTY50', 'NIFTY500')")
    trade_date: str = Field(..., description="Trade date in ISO 8601 format (YYYY-MM-DD)")
    timestamp: int = Field(..., description="Unix epoch timestamp when data was computed")
    advances: int = Field(..., description="Number of advancing stocks")
    declines: int = Field(..., description="Number of declining stocks")
    unchanged: int = Field(..., description="Number of unchanged stocks")
    total_stocks: int = Field(..., description="Total number of stocks analyzed")
    ad_ratio: float = Field(..., description="Advance/Decline ratio")
    sentiment_score: float = Field(..., description="Market sentiment score (-1.0 to 1.0)")
    avg_pct_change: Optional[float] = Field(None, description="Average percentage change")
    new_highs_52w: Optional[int] = Field(None, description="Stocks hitting 52-week high")
    new_lows_52w: Optional[int] = Field(None, description="Stocks hitting 52-week low")
    data_source: str = Field(default="yahoo_finance", description="Data source identifier")
    
    @field_validator('sentiment_score')
    @classmethod
    def validate_sentiment_score(cls, v: float) -> float:
        """Validate sentiment_score is between -1.0 and 1.0"""
        if not -1.0 <= v <= 1.0:
            raise ValueError(f"sentiment_score must be between -1.0 and 1.0, got: {v}")
        return v
    
    def to_proto(self) -> market_breadth_pb2.MarketBreadth:
        """Convert to Protocol Buffer message"""
        msg = market_breadth_pb2.MarketBreadth(
            schema_version=self.schema_version,
            index_name=self.index_name,
            trade_date=self.trade_date,
            timestamp=self.timestamp,
            advances=self.advances,
            declines=self.declines,
            unchanged=self.unchanged,
            total_stocks=self.total_stocks,
            ad_ratio=self.ad_ratio,
            sentiment_score=self.sentiment_score,
            data_source=self.data_source,
        )
        
        # Optional fields
        if self.avg_pct_change is not None:
            msg.avg_pct_change = self.avg_pct_change
        if self.new_highs_52w is not None:
            msg.new_highs_52w = self.new_highs_52w
        if self.new_lows_52w is not None:
            msg.new_lows_52w = self.new_lows_52w
        
        return msg
    
    @classmethod
    def from_proto(cls, msg: market_breadth_pb2.MarketBreadth) -> "MarketBreadthEvent":
        """Create from Protocol Buffer message"""
        return cls(
            schema_version=msg.schema_version,
            index_name=msg.index_name,
            trade_date=msg.trade_date,
            timestamp=msg.timestamp,
            advances=msg.advances,
            declines=msg.declines,
            unchanged=msg.unchanged,
            total_stocks=msg.total_stocks,
            ad_ratio=msg.ad_ratio,
            sentiment_score=msg.sentiment_score,
            avg_pct_change=msg.avg_pct_change if msg.HasField("avg_pct_change") else None,
            new_highs_52w=msg.new_highs_52w if msg.HasField("new_highs_52w") else None,
            new_lows_52w=msg.new_lows_52w if msg.HasField("new_lows_52w") else None,
            data_source=msg.data_source,
        )


# ============================================================================
# Fetch Status Event
# ============================================================================

class FetchStatusEvent(BaseModel):
    """Publisher health and operational status"""
    
    schema_version: int = Field(default=1, description="Schema version for backward compatibility")
    publisher_id: str = Field(..., description="Publisher identifier (e.g., 'yahoo_publisher_1')")
    timestamp: int = Field(..., description="Unix epoch timestamp when status was emitted")
    status: FetchStatusType = Field(..., description="Publisher status type")
    symbols_succeeded: int = Field(..., description="Symbols successfully fetched in batch")
    symbols_failed: int = Field(..., description="Symbols that failed in batch")
    total_symbols: int = Field(..., description="Total symbols being monitored")
    batch_size: int = Field(..., description="Current fetch batch size")
    rate_limit: int = Field(..., description="Current rate limit (requests per minute)")
    error_message: Optional[str] = Field(None, description="Last error message")
    failed_symbols: list[str] = Field(default_factory=list, description="List of failed symbols")
    fetch_duration_ms: int = Field(..., description="Fetch cycle duration in milliseconds")
    uptime_seconds: int = Field(..., description="Publisher uptime in seconds")
    total_events_published: int = Field(..., description="Total events published since start")
    
    def to_proto(self) -> fetch_status_pb2.FetchStatus:
        """Convert to Protocol Buffer message"""
        # Map FetchStatusType to protobuf enum
        status_map = {
            FetchStatusType.UNKNOWN: fetch_status_pb2.FetchStatus.UNKNOWN,
            FetchStatusType.STARTED: fetch_status_pb2.FetchStatus.STARTED,
            FetchStatusType.HEALTHY: fetch_status_pb2.FetchStatus.HEALTHY,
            FetchStatusType.DEGRADED: fetch_status_pb2.FetchStatus.DEGRADED,
            FetchStatusType.UNHEALTHY: fetch_status_pb2.FetchStatus.UNHEALTHY,
            FetchStatusType.STOPPED: fetch_status_pb2.FetchStatus.STOPPED,
            FetchStatusType.CRASHED: fetch_status_pb2.FetchStatus.CRASHED,
        }
        
        msg = fetch_status_pb2.FetchStatus(
            schema_version=self.schema_version,
            publisher_id=self.publisher_id,
            timestamp=self.timestamp,
            status=status_map[self.status],
            symbols_succeeded=self.symbols_succeeded,
            symbols_failed=self.symbols_failed,
            total_symbols=self.total_symbols,
            batch_size=self.batch_size,
            rate_limit=self.rate_limit,
            fetch_duration_ms=self.fetch_duration_ms,
            uptime_seconds=self.uptime_seconds,
            total_events_published=self.total_events_published,
        )
        
        # Optional fields
        if self.error_message is not None:
            msg.error_message = self.error_message
        if self.failed_symbols:
            msg.failed_symbols.extend(self.failed_symbols)
        
        return msg
    
    @classmethod
    def from_proto(cls, msg: fetch_status_pb2.FetchStatus) -> "FetchStatusEvent":
        """Create from Protocol Buffer message"""
        # Map protobuf enum to FetchStatusType
        status_map = {
            fetch_status_pb2.FetchStatus.UNKNOWN: FetchStatusType.UNKNOWN,
            fetch_status_pb2.FetchStatus.STARTED: FetchStatusType.STARTED,
            fetch_status_pb2.FetchStatus.HEALTHY: FetchStatusType.HEALTHY,
            fetch_status_pb2.FetchStatus.DEGRADED: FetchStatusType.DEGRADED,
            fetch_status_pb2.FetchStatus.UNHEALTHY: FetchStatusType.UNHEALTHY,
            fetch_status_pb2.FetchStatus.STOPPED: FetchStatusType.STOPPED,
            fetch_status_pb2.FetchStatus.CRASHED: FetchStatusType.CRASHED,
        }
        
        return cls(
            schema_version=msg.schema_version,
            publisher_id=msg.publisher_id,
            timestamp=msg.timestamp,
            status=status_map.get(msg.status, FetchStatusType.UNKNOWN),
            symbols_succeeded=msg.symbols_succeeded,
            symbols_failed=msg.symbols_failed,
            total_symbols=msg.total_symbols,
            batch_size=msg.batch_size,
            rate_limit=msg.rate_limit,
            error_message=msg.error_message if msg.HasField("error_message") else None,
            failed_symbols=list(msg.failed_symbols),
            fetch_duration_ms=msg.fetch_duration_ms,
            uptime_seconds=msg.uptime_seconds,
            total_events_published=msg.total_events_published,
        )


# ============================================================================
# Trend Analysis Event
# ============================================================================

class TrendAnalysisEvent(BaseModel):
    """Trend analysis aggregated across multiple symbols"""
    
    timestamp: datetime = Field(..., description="Analysis timestamp")
    analyses: list[dict] = Field(..., description="List of trend analysis dicts per symbol")
    total_symbols: int = Field(..., description="Total symbols analyzed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    'CandleDataEvent',
    'MarketBreadthEvent',
    'FetchStatusEvent',
    'FetchStatusType',
    'TrendAnalysisEvent',
]
