"""
Unit Tests for Serialization Layer
===================================

Tests for JSON, MessagePack, and Protobuf serializers.
"""

import sys
import os
import pytest
from datetime import datetime, date
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from serialization.json_serializer import JSONSerializer
from serialization.msgpack_serializer import MessagePackSerializer
from serialization.protobuf_serializer import ProtobufSerializer
from serialization.serializer_factory import SerializerFactory, get_serializer
from serialization.base_serializer import SerializationError, DeserializationError


class TestJSONSerializer:
    """Tests for JSON serializer"""
    
    def test_serialize_simple_dict(self):
        """Test serializing a simple dictionary"""
        serializer = JSONSerializer()
        data = {'name': 'test', 'value': 123}
        
        result = serializer.serialize(data)
        
        assert isinstance(result, bytes)
        assert b'test' in result
        assert b'123' in result
    
    def test_deserialize_simple_dict(self):
        """Test deserializing a simple dictionary"""
        serializer = JSONSerializer()
        data = {'name': 'test', 'value': 123}
        
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)
        
        assert deserialized == data
    
    def test_serialize_with_datetime(self):
        """Test serializing datetime objects"""
        serializer = JSONSerializer()
        now = datetime(2025, 11, 26, 12, 30, 45)
        data = {'timestamp': now, 'date': date(2025, 11, 26)}
        
        result = serializer.serialize(data)
        deserialized = serializer.deserialize(result)
        
        assert '2025-11-26' in deserialized['timestamp']
        assert '2025-11-26' in deserialized['date']
    
    def test_serialize_with_decimal(self):
        """Test serializing Decimal objects"""
        serializer = JSONSerializer()
        data = {'price': Decimal('123.45')}
        
        result = serializer.serialize(data)
        deserialized = serializer.deserialize(result)
        
        assert deserialized['price'] == 123.45
    
    def test_pretty_formatting(self):
        """Test pretty JSON formatting"""
        serializer = JSONSerializer(pretty=True)
        data = {'a': 1, 'b': 2}
        
        result = serializer.serialize(data)
        
        # Pretty JSON should have newlines and indentation
        assert b'\n' in result
        assert b'  ' in result
    
    def test_content_type(self):
        """Test content type"""
        serializer = JSONSerializer()
        assert serializer.content_type() == 'application/json'
    
    def test_format_name(self):
        """Test format name"""
        serializer = JSONSerializer()
        assert serializer.get_format_name() == 'json'
    
    def test_schema_evolution_support(self):
        """Test schema evolution support"""
        serializer = JSONSerializer()
        assert serializer.supports_schema_evolution() is True
    
    def test_roundtrip_complex_data(self):
        """Test roundtrip with complex nested data"""
        serializer = JSONSerializer()
        data = {
            'symbol': 'RELIANCE.NS',
            'candles': [
                {'open': 2500.0, 'close': 2510.0, 'volume': 1000000},
                {'open': 2510.0, 'close': 2520.0, 'volume': 1100000}
            ],
            'metadata': {
                'source': 'yahoo',
                'timestamp': datetime(2025, 11, 26, 10, 0, 0)
            }
        }
        
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)
        
        assert deserialized['symbol'] == 'RELIANCE.NS'
        assert len(deserialized['candles']) == 2
        assert deserialized['candles'][0]['volume'] == 1000000


class TestMessagePackSerializer:
    """Tests for MessagePack serializer"""
    
    def test_serialize_simple_dict(self):
        """Test serializing a simple dictionary"""
        serializer = MessagePackSerializer()
        data = {'name': 'test', 'value': 123}
        
        result = serializer.serialize(data)
        
        assert isinstance(result, bytes)
        assert len(result) < 50  # Should be compact
    
    def test_deserialize_simple_dict(self):
        """Test deserializing a simple dictionary"""
        serializer = MessagePackSerializer()
        data = {'name': 'test', 'value': 123}
        
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)
        
        assert deserialized == data
    
    def test_size_comparison_with_json(self):
        """Test that MessagePack is smaller than JSON"""
        json_serializer = JSONSerializer()
        msgpack_serializer = MessagePackSerializer()
        
        # Large data structure
        data = {
            'records': [
                {'id': i, 'value': f'value_{i}', 'amount': i * 1.5}
                for i in range(100)
            ]
        }
        
        json_size = len(json_serializer.serialize(data))
        msgpack_size = len(msgpack_serializer.serialize(data))
        
        # MessagePack should be smaller than JSON (typically 15-40% reduction)
        assert msgpack_size < json_size
        # Verify at least 10% size reduction
        assert msgpack_size < json_size * 0.9
    
    def test_content_type(self):
        """Test content type"""
        serializer = MessagePackSerializer()
        assert serializer.content_type() == 'application/msgpack'
    
    def test_format_name(self):
        """Test format name"""
        serializer = MessagePackSerializer()
        assert serializer.get_format_name() == 'msgpack'
    
    def test_roundtrip_complex_data(self):
        """Test roundtrip with complex nested data"""
        serializer = MessagePackSerializer()
        data = {
            'symbol': 'RELIANCE.NS',
            'candles': [
                {'open': 2500.0, 'close': 2510.0, 'volume': 1000000},
                {'open': 2510.0, 'close': 2520.0, 'volume': 1100000}
            ],
            'metadata': {
                'source': 'yahoo',
                'timestamp': datetime(2025, 11, 26, 10, 0, 0)
            }
        }
        
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)
        
        assert deserialized['symbol'] == 'RELIANCE.NS'
        assert len(deserialized['candles']) == 2


class TestProtobufSerializer:
    """Tests for Protobuf serializer"""
    
    def test_initialization(self):
        """Test serializer initialization"""
        serializer = ProtobufSerializer()
        assert serializer.schema_registry == {}
    
    def test_content_type(self):
        """Test content type"""
        serializer = ProtobufSerializer()
        assert serializer.content_type() == 'application/x-protobuf'
    
    def test_format_name(self):
        """Test format name"""
        serializer = ProtobufSerializer()
        assert serializer.get_format_name() == 'protobuf'
    
    def test_schema_evolution_support(self):
        """Test schema evolution support"""
        serializer = ProtobufSerializer()
        assert serializer.supports_schema_evolution() is True


class TestSerializerFactory:
    """Tests for Serializer Factory"""
    
    def test_create_json_serializer(self):
        """Test creating JSON serializer"""
        serializer = SerializerFactory.create('json')
        assert isinstance(serializer, JSONSerializer)
        assert serializer.get_format_name() == 'json'
    
    def test_create_msgpack_serializer(self):
        """Test creating MessagePack serializer"""
        serializer = SerializerFactory.create('msgpack')
        assert isinstance(serializer, MessagePackSerializer)
        assert serializer.get_format_name() == 'msgpack'
    
    def test_create_protobuf_serializer(self):
        """Test creating Protobuf serializer"""
        serializer = SerializerFactory.create('protobuf')
        assert isinstance(serializer, ProtobufSerializer)
        assert serializer.get_format_name() == 'protobuf'
    
    def test_create_with_invalid_format(self):
        """Test creating with invalid format"""
        with pytest.raises(ValueError, match="Invalid serialization format"):
            SerializerFactory.create('invalid')
    
    def test_create_case_insensitive(self):
        """Test format name is case-insensitive"""
        serializer1 = SerializerFactory.create('JSON')
        serializer2 = SerializerFactory.create('json')
        
        assert type(serializer1) == type(serializer2)
    
    def test_get_available_formats(self):
        """Test getting available formats"""
        formats = SerializerFactory.get_available_formats()
        
        assert 'json' in formats
        assert 'msgpack' in formats
        assert 'protobuf' in formats
    
    def test_get_recommended_format(self):
        """Test getting recommended format for use cases"""
        assert SerializerFactory.get_recommended_format('development') == 'json'
        assert SerializerFactory.get_recommended_format('general') == 'msgpack'
        assert SerializerFactory.get_recommended_format('high_performance') == 'protobuf'
        assert SerializerFactory.get_recommended_format('external_api') == 'json'
    
    def test_convenience_function(self):
        """Test convenience get_serializer function"""
        serializer = get_serializer('json')
        assert isinstance(serializer, JSONSerializer)


class TestSerializerComparison:
    """Compare serializers for performance and size"""
    
    def test_serialization_consistency(self):
        """Test that all serializers can handle the same data"""
        data = {
            'symbol': 'RELIANCE.NS',
            'price': 2500.50,
            'volume': 1000000,
            'timestamp': datetime(2025, 11, 26, 10, 0, 0)
        }
        
        json_ser = JSONSerializer()
        msgpack_ser = MessagePackSerializer()
        
        # Both should serialize without error
        json_bytes = json_ser.serialize(data)
        msgpack_bytes = msgpack_ser.serialize(data)
        
        # Both should deserialize correctly
        json_result = json_ser.deserialize(json_bytes)
        msgpack_result = msgpack_ser.deserialize(msgpack_bytes)
        
        # Results should be equivalent (accounting for datetime serialization)
        assert json_result['symbol'] == msgpack_result['symbol']
        assert json_result['price'] == msgpack_result['price']
        assert json_result['volume'] == msgpack_result['volume']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
