from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CandleData(_message.Message):
    __slots__ = ("schema_version", "symbol", "trade_date", "timestamp", "prev_close", "open_price", "high_price", "low_price", "close_price", "volume", "delivery_qty", "delivery_per", "data_source", "series", "exchange")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    PREV_CLOSE_FIELD_NUMBER: _ClassVar[int]
    OPEN_PRICE_FIELD_NUMBER: _ClassVar[int]
    HIGH_PRICE_FIELD_NUMBER: _ClassVar[int]
    LOW_PRICE_FIELD_NUMBER: _ClassVar[int]
    CLOSE_PRICE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    DELIVERY_QTY_FIELD_NUMBER: _ClassVar[int]
    DELIVERY_PER_FIELD_NUMBER: _ClassVar[int]
    DATA_SOURCE_FIELD_NUMBER: _ClassVar[int]
    SERIES_FIELD_NUMBER: _ClassVar[int]
    EXCHANGE_FIELD_NUMBER: _ClassVar[int]
    schema_version: int
    symbol: str
    trade_date: str
    timestamp: int
    prev_close: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    delivery_qty: int
    delivery_per: float
    data_source: str
    series: str
    exchange: str
    def __init__(self, schema_version: _Optional[int] = ..., symbol: _Optional[str] = ..., trade_date: _Optional[str] = ..., timestamp: _Optional[int] = ..., prev_close: _Optional[float] = ..., open_price: _Optional[float] = ..., high_price: _Optional[float] = ..., low_price: _Optional[float] = ..., close_price: _Optional[float] = ..., volume: _Optional[int] = ..., delivery_qty: _Optional[int] = ..., delivery_per: _Optional[float] = ..., data_source: _Optional[str] = ..., series: _Optional[str] = ..., exchange: _Optional[str] = ...) -> None: ...
