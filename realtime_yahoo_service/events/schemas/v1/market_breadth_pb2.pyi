from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class MarketBreadth(_message.Message):
    __slots__ = ("schema_version", "index_name", "trade_date", "timestamp", "advances", "declines", "unchanged", "total_stocks", "ad_ratio", "sentiment_score", "avg_pct_change", "new_highs_52w", "new_lows_52w", "data_source")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    ADVANCES_FIELD_NUMBER: _ClassVar[int]
    DECLINES_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_STOCKS_FIELD_NUMBER: _ClassVar[int]
    AD_RATIO_FIELD_NUMBER: _ClassVar[int]
    SENTIMENT_SCORE_FIELD_NUMBER: _ClassVar[int]
    AVG_PCT_CHANGE_FIELD_NUMBER: _ClassVar[int]
    NEW_HIGHS_52W_FIELD_NUMBER: _ClassVar[int]
    NEW_LOWS_52W_FIELD_NUMBER: _ClassVar[int]
    DATA_SOURCE_FIELD_NUMBER: _ClassVar[int]
    schema_version: int
    index_name: str
    trade_date: str
    timestamp: int
    advances: int
    declines: int
    unchanged: int
    total_stocks: int
    ad_ratio: float
    sentiment_score: float
    avg_pct_change: float
    new_highs_52w: int
    new_lows_52w: int
    data_source: str
    def __init__(self, schema_version: _Optional[int] = ..., index_name: _Optional[str] = ..., trade_date: _Optional[str] = ..., timestamp: _Optional[int] = ..., advances: _Optional[int] = ..., declines: _Optional[int] = ..., unchanged: _Optional[int] = ..., total_stocks: _Optional[int] = ..., ad_ratio: _Optional[float] = ..., sentiment_score: _Optional[float] = ..., avg_pct_change: _Optional[float] = ..., new_highs_52w: _Optional[int] = ..., new_lows_52w: _Optional[int] = ..., data_source: _Optional[str] = ...) -> None: ...
