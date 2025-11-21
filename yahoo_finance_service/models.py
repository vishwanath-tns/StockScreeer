"""
Data models for Yahoo Finance service
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

@dataclass
class DailyQuote:
    """Daily quote data model"""
    symbol: str
    date: date
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    volume: Optional[int]
    adj_close: Optional[Decimal]
    timeframe: str = 'Daily'
    source: str = 'Yahoo Finance'
    
    def __post_init__(self):
        """Validate data after initialization"""
        if self.open is not None and self.open < 0:
            raise ValueError(f"Open price cannot be negative: {self.open}")
        if self.high is not None and self.high < 0:
            raise ValueError(f"High price cannot be negative: {self.high}")
        if self.low is not None and self.low < 0:
            raise ValueError(f"Low price cannot be negative: {self.low}")
        if self.close is not None and self.close < 0:
            raise ValueError(f"Close price cannot be negative: {self.close}")
        if self.volume is not None and self.volume < 0:
            raise ValueError(f"Volume cannot be negative: {self.volume}")
            
        # Validate OHLC relationships
        if all(x is not None for x in [self.open, self.high, self.low, self.close]):
            if self.high < max(self.open, self.close):
                raise ValueError("High price should be >= max(open, close)")
            if self.low > min(self.open, self.close):
                raise ValueError("Low price should be <= min(open, close)")
    
    @property
    def day_change(self) -> Optional[Decimal]:
        """Calculate day change"""
        if self.open is not None and self.close is not None and self.open > 0:
            return self.close - self.open
        return None
    
    @property
    def day_change_pct(self) -> Optional[Decimal]:
        """Calculate day change percentage"""
        if self.open is not None and self.close is not None and self.open > 0:
            return ((self.close - self.open) / self.open) * 100
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion"""
        return {
            'symbol': self.symbol,
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'adj_close': self.adj_close,
            'timeframe': self.timeframe,
            'source': self.source
        }

@dataclass
class SymbolInfo:
    """Symbol information model"""
    symbol: str
    yahoo_symbol: str
    name: str
    market: str = 'NSE'
    currency: str = 'INR'
    symbol_type: str = 'INDEX'
    is_active: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion"""
        return {
            'symbol': self.symbol,
            'yahoo_symbol': self.yahoo_symbol,
            'name': self.name,
            'market': self.market,
            'currency': self.currency,
            'symbol_type': self.symbol_type,
            'is_active': self.is_active
        }

@dataclass
class DownloadLog:
    """Download activity log model"""
    symbol: str
    start_date: date
    end_date: date
    timeframe: str
    records_downloaded: int = 0
    records_updated: int = 0
    status: str = 'STARTED'
    error_message: Optional[str] = None
    download_duration_ms: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion"""
        return {
            'symbol': self.symbol,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'timeframe': self.timeframe,
            'records_downloaded': self.records_downloaded,
            'records_updated': self.records_updated,
            'status': self.status,
            'error_message': self.error_message,
            'download_duration_ms': self.download_duration_ms
        }