"""
Unit Tests for Event Models
============================

Tests for Pydantic event models and Protocol Buffer conversion.
"""

import sys
import os
import unittest
from datetime import datetime
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from events.event_models import (
    CandleDataEvent,
    MarketBreadthEvent,
    FetchStatusEvent,
    FetchStatusType,
)


class TestCandleDataEvent(unittest.TestCase):
    """Tests for CandleDataEvent"""
    
    def test_create_candle_data_event(self):
        """Test creating a CandleDataEvent"""
        event = CandleDataEvent(
            symbol="RELIANCE.NS",
            trade_date="2025-01-15",
            timestamp=1705330800,
            prev_close=2500.50,
            open_price=2505.00,
            high_price=2550.75,
            low_price=2495.25,
            close_price=2545.00,
            volume=1000000,
        )
        
        assert event.symbol == "RELIANCE.NS"
        assert event.trade_date == "2025-01-15"
        assert event.close_price == 2545.00
        assert event.data_source == "yahoo_finance"
    
    def test_candle_data_with_optionals(self):
        """Test CandleDataEvent with optional fields"""
        event = CandleDataEvent(
            symbol="TCS.NS",
            trade_date="2025-01-15",
            timestamp=1705330800,
            prev_close=3500.00,
            open_price=3510.00,
            high_price=3550.00,
            low_price=3495.00,
            close_price=3545.00,
            volume=500000,
            delivery_qty=300000,
            delivery_per=60.0,
            series="EQ",
            exchange="NSE",
        )
        
        assert event.delivery_qty == 300000
        assert event.delivery_per == 60.0
        assert event.series == "EQ"
        assert event.exchange == "NSE"
    
    def test_candle_data_to_proto(self):
        """Test converting CandleDataEvent to protobuf"""
        event = CandleDataEvent(
            symbol="RELIANCE.NS",
            trade_date="2025-01-15",
            timestamp=1705330800,
            prev_close=2500.50,
            open_price=2505.00,
            high_price=2550.75,
            low_price=2495.25,
            close_price=2545.00,
            volume=1000000,
        )
        
        proto = event.to_proto()
        
        assert proto.symbol == "RELIANCE.NS"
        assert proto.trade_date == "2025-01-15"
        assert proto.close_price == 2545.00
    
    def test_candle_data_from_proto(self):
        """Test creating CandleDataEvent from protobuf"""
        event = CandleDataEvent(
            symbol="RELIANCE.NS",
            trade_date="2025-01-15",
            timestamp=1705330800,
            prev_close=2500.50,
            open_price=2505.00,
            high_price=2550.75,
            low_price=2495.25,
            close_price=2545.00,
            volume=1000000,
            delivery_qty=800000,
        )
        
        proto = event.to_proto()
        restored = CandleDataEvent.from_proto(proto)
        
        assert restored.symbol == event.symbol
        assert restored.trade_date == event.trade_date
        assert restored.close_price == event.close_price
        assert restored.delivery_qty == event.delivery_qty
    
    def test_candle_data_roundtrip(self):
        """Test full roundtrip: Event -> Proto -> Event"""
        original = CandleDataEvent(
            symbol="INFY.NS",
            trade_date="2025-01-15",
            timestamp=1705330800,
            prev_close=1500.00,
            open_price=1505.00,
            high_price=1520.00,
            low_price=1495.00,
            close_price=1515.00,
            volume=2000000,
            delivery_qty=1500000,
            delivery_per=75.0,
            series="EQ",
        )
        
        proto = original.to_proto()
        restored = CandleDataEvent.from_proto(proto)
        
        # Compare all fields
        assert restored.model_dump() == original.model_dump()


class TestMarketBreadthEvent(unittest.TestCase):
    """Tests for MarketBreadthEvent"""
    
    def test_create_market_breadth_event(self):
        """Test creating a MarketBreadthEvent"""
        event = MarketBreadthEvent(
            index_name="NIFTY50",
            trade_date="2025-01-15",
            timestamp=1705330800,
            advances=30,
            declines=18,
            unchanged=2,
            total_stocks=50,
            ad_ratio=1.67,
            sentiment_score=0.24,
        )
        
        assert event.index_name == "NIFTY50"
        assert event.advances == 30
        assert event.declines == 18
        assert event.sentiment_score == 0.24
    
    def test_market_breadth_to_proto(self):
        """Test converting MarketBreadthEvent to protobuf"""
        event = MarketBreadthEvent(
            index_name="NIFTY500",
            trade_date="2025-01-15",
            timestamp=1705330800,
            advances=300,
            declines=180,
            unchanged=20,
            total_stocks=500,
            ad_ratio=1.67,
            sentiment_score=0.24,
            avg_pct_change=0.5,
        )
        
        proto = event.to_proto()
        
        assert proto.index_name == "NIFTY500"
        assert proto.advances == 300
        assert proto.avg_pct_change == 0.5
    
    def test_market_breadth_from_proto(self):
        """Test creating MarketBreadthEvent from protobuf"""
        event = MarketBreadthEvent(
            index_name="NIFTY50",
            trade_date="2025-01-15",
            timestamp=1705330800,
            advances=30,
            declines=18,
            unchanged=2,
            total_stocks=50,
            ad_ratio=1.67,
            sentiment_score=0.24,
        )
        
        proto = event.to_proto()
        restored = MarketBreadthEvent.from_proto(proto)
        
        assert restored.index_name == event.index_name
        assert restored.advances == event.advances
        assert restored.sentiment_score == event.sentiment_score
    
    def test_market_breadth_sentiment_validation(self):
        """Test sentiment_score validation"""
        with self.assertRaises(ValueError):
            MarketBreadthEvent(
                index_name="NIFTY50",
                trade_date="2025-01-15",
                timestamp=1705330800,
                advances=30,
                declines=18,
                unchanged=2,
                total_stocks=50,
                ad_ratio=1.67,
                sentiment_score=1.5,  # Invalid: > 1.0
            )


class TestFetchStatusEvent(unittest.TestCase):
    """Tests for FetchStatusEvent"""
    
    def test_create_fetch_status_event(self):
        """Test creating a FetchStatusEvent"""
        event = FetchStatusEvent(
            publisher_id="yahoo_publisher_1",
            timestamp=1705330800,
            status=FetchStatusType.HEALTHY,
            symbols_succeeded=500,
            symbols_failed=12,
            total_symbols=512,
            batch_size=50,
            rate_limit=20,
            fetch_duration_ms=5000,
            uptime_seconds=3600,
            total_events_published=10000,
        )
        
        assert event.publisher_id == "yahoo_publisher_1"
        assert event.status == FetchStatusType.HEALTHY
        assert event.symbols_succeeded == 500
    
    def test_fetch_status_with_error(self):
        """Test FetchStatusEvent with error message"""
        event = FetchStatusEvent(
            publisher_id="yahoo_publisher_1",
            timestamp=1705330800,
            status=FetchStatusType.DEGRADED,
            symbols_succeeded=480,
            symbols_failed=20,
            total_symbols=512,
            batch_size=50,
            rate_limit=20,
            error_message="Rate limit exceeded",
            failed_symbols=["SYMBOL1.NS", "SYMBOL2.NS"],
            fetch_duration_ms=8000,
            uptime_seconds=3600,
            total_events_published=10000,
        )
        
        assert event.status == FetchStatusType.DEGRADED
        assert event.error_message == "Rate limit exceeded"
        assert len(event.failed_symbols) == 2
    
    def test_fetch_status_to_proto(self):
        """Test converting FetchStatusEvent to protobuf"""
        event = FetchStatusEvent(
            publisher_id="yahoo_publisher_1",
            timestamp=1705330800,
            status=FetchStatusType.STARTED,
            symbols_succeeded=0,
            symbols_failed=0,
            total_symbols=512,
            batch_size=50,
            rate_limit=20,
            fetch_duration_ms=100,
            uptime_seconds=10,
            total_events_published=0,
        )
        
        proto = event.to_proto()
        
        assert proto.publisher_id == "yahoo_publisher_1"
        assert proto.status == 1  # STARTED enum value
    
    def test_fetch_status_from_proto(self):
        """Test creating FetchStatusEvent from protobuf"""
        event = FetchStatusEvent(
            publisher_id="yahoo_publisher_1",
            timestamp=1705330800,
            status=FetchStatusType.HEALTHY,
            symbols_succeeded=500,
            symbols_failed=12,
            total_symbols=512,
            batch_size=50,
            rate_limit=20,
            fetch_duration_ms=5000,
            uptime_seconds=3600,
            total_events_published=10000,
        )
        
        proto = event.to_proto()
        restored = FetchStatusEvent.from_proto(proto)
        
        assert restored.publisher_id == event.publisher_id
        assert restored.status == event.status
        assert restored.symbols_succeeded == event.symbols_succeeded
    
    def test_fetch_status_roundtrip(self):
        """Test full roundtrip: Event -> Proto -> Event"""
        original = FetchStatusEvent(
            publisher_id="yahoo_publisher_1",
            timestamp=1705330800,
            status=FetchStatusType.DEGRADED,
            symbols_succeeded=480,
            symbols_failed=20,
            total_symbols=512,
            batch_size=50,
            rate_limit=20,
            error_message="Some symbols timed out",
            failed_symbols=["SYM1.NS", "SYM2.NS", "SYM3.NS"],
            fetch_duration_ms=8000,
            uptime_seconds=3600,
            total_events_published=10000,
        )
        
        proto = original.to_proto()
        restored = FetchStatusEvent.from_proto(proto)
        
        # Compare all fields
        assert restored.model_dump() == original.model_dump()


class TestSerializerIntegration(unittest.TestCase):
    """Test event models work with serializers"""
    
    def test_candle_event_with_json_serializer(self):
        """Test CandleDataEvent with JSONSerializer"""
        from serialization.json_serializer import JSONSerializer
        
        serializer = JSONSerializer()
        event = CandleDataEvent(
            symbol="RELIANCE.NS",
            trade_date="2025-01-15",
            timestamp=1705330800,
            prev_close=2500.50,
            open_price=2505.00,
            high_price=2550.75,
            low_price=2495.25,
            close_price=2545.00,
            volume=1000000,
        )
        
        # Serialize as Pydantic dict
        data = serializer.serialize(event.model_dump())
        deserialized = serializer.deserialize(data)
        
        assert deserialized['symbol'] == event.symbol
        assert deserialized['close_price'] == event.close_price
    
    def test_candle_event_with_protobuf_serializer(self):
        """Test CandleDataEvent with ProtobufSerializer"""
        from serialization.protobuf_serializer import ProtobufSerializer
        from events.schemas.v1 import candle_data_pb2
        
        serializer = ProtobufSerializer()
        
        event = CandleDataEvent(
            symbol="RELIANCE.NS",
            trade_date="2025-01-15",
            timestamp=1705330800,
            prev_close=2500.50,
            open_price=2505.00,
            high_price=2550.75,
            low_price=2495.25,
            close_price=2545.00,
            volume=1000000,
        )
        
        # Convert to proto
        proto = event.to_proto()
        
        # Serialize proto directly
        data = serializer.serialize(proto)
        
        # Manually deserialize using protobuf (serializer.deserialize needs type info)
        deserialized = candle_data_pb2.CandleData()
        deserialized.ParseFromString(data)
        
        assert deserialized.symbol == event.symbol
        assert deserialized.close_price == event.close_price


if __name__ == '__main__':
    unittest.main()
