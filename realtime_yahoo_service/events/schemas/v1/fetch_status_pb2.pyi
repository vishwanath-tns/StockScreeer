from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FetchStatus(_message.Message):
    __slots__ = ("schema_version", "publisher_id", "timestamp", "status", "symbols_succeeded", "symbols_failed", "total_symbols", "batch_size", "rate_limit", "error_message", "failed_symbols", "fetch_duration_ms", "uptime_seconds", "total_events_published")
    class StatusType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[FetchStatus.StatusType]
        STARTED: _ClassVar[FetchStatus.StatusType]
        HEALTHY: _ClassVar[FetchStatus.StatusType]
        DEGRADED: _ClassVar[FetchStatus.StatusType]
        UNHEALTHY: _ClassVar[FetchStatus.StatusType]
        STOPPED: _ClassVar[FetchStatus.StatusType]
        CRASHED: _ClassVar[FetchStatus.StatusType]
    UNKNOWN: FetchStatus.StatusType
    STARTED: FetchStatus.StatusType
    HEALTHY: FetchStatus.StatusType
    DEGRADED: FetchStatus.StatusType
    UNHEALTHY: FetchStatus.StatusType
    STOPPED: FetchStatus.StatusType
    CRASHED: FetchStatus.StatusType
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    PUBLISHER_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SYMBOLS_SUCCEEDED_FIELD_NUMBER: _ClassVar[int]
    SYMBOLS_FAILED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    BATCH_SIZE_FIELD_NUMBER: _ClassVar[int]
    RATE_LIMIT_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    FAILED_SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    FETCH_DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_EVENTS_PUBLISHED_FIELD_NUMBER: _ClassVar[int]
    schema_version: int
    publisher_id: str
    timestamp: int
    status: FetchStatus.StatusType
    symbols_succeeded: int
    symbols_failed: int
    total_symbols: int
    batch_size: int
    rate_limit: int
    error_message: str
    failed_symbols: _containers.RepeatedScalarFieldContainer[str]
    fetch_duration_ms: int
    uptime_seconds: int
    total_events_published: int
    def __init__(self, schema_version: _Optional[int] = ..., publisher_id: _Optional[str] = ..., timestamp: _Optional[int] = ..., status: _Optional[_Union[FetchStatus.StatusType, str]] = ..., symbols_succeeded: _Optional[int] = ..., symbols_failed: _Optional[int] = ..., total_symbols: _Optional[int] = ..., batch_size: _Optional[int] = ..., rate_limit: _Optional[int] = ..., error_message: _Optional[str] = ..., failed_symbols: _Optional[_Iterable[str]] = ..., fetch_duration_ms: _Optional[int] = ..., uptime_seconds: _Optional[int] = ..., total_events_published: _Optional[int] = ...) -> None: ...
