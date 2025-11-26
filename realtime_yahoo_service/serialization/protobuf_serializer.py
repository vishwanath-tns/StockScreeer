"""
Protocol Buffers Serializer
============================

Binary serialization with 50-60% size reduction vs JSON.
Best for high-performance requirements with strict schema.
"""

import logging
from typing import Any, Type

from .base_serializer import IMessageSerializer, SerializationError, DeserializationError

logger = logging.getLogger(__name__)


class ProtobufSerializer(IMessageSerializer):
    """
    Protocol Buffers serialization implementation
    
    Note: This is a placeholder implementation. Actual usage requires:
    1. .proto schema definitions
    2. Generated Python classes via protoc
    3. Mapping between Pydantic models and protobuf messages
    """
    
    def __init__(self, schema_registry: dict = None):
        """
        Initialize Protobuf serializer
        
        Args:
            schema_registry: Mapping of event types to protobuf message classes
                            Example: {'CandleDataEvent': CandleDataProto}
        """
        self.schema_registry = schema_registry or {}
    
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize object to Protocol Buffers bytes
        
        Args:
            obj: Object to serialize (must have .to_proto() method or be protobuf message)
            
        Returns:
            Protobuf bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            # Check if object has to_proto method (Pydantic model with protobuf support)
            if hasattr(obj, 'to_proto'):
                proto_msg = obj.to_proto()
                return proto_msg.SerializeToString()
            
            # Check if object is already a protobuf message
            elif hasattr(obj, 'SerializeToString'):
                return obj.SerializeToString()
            
            # Otherwise, need to convert dict to protobuf message
            elif isinstance(obj, dict):
                event_type = obj.get('event_type') or obj.get('__type__')
                if not event_type:
                    raise SerializationError("Object dict must have 'event_type' or '__type__' field")
                
                proto_class = self.schema_registry.get(event_type)
                if not proto_class:
                    raise SerializationError(f"No protobuf schema registered for type: {event_type}")
                
                # Create protobuf message from dict
                proto_msg = proto_class(**obj)
                return proto_msg.SerializeToString()
            
            else:
                raise SerializationError(f"Unsupported object type for protobuf serialization: {type(obj)}")
            
        except Exception as e:
            logger.error(f"Protobuf serialization failed: {e}")
            raise SerializationError(f"Failed to serialize to Protobuf: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize Protocol Buffers bytes to object
        
        Note: Requires knowing the message type. In production, use an envelope
        message with a type discriminator field.
        
        Args:
            data: Protobuf bytes
            
        Returns:
            Deserialized protobuf message or dict
            
        Raises:
            DeserializationError: If deserialization fails
        """
        try:
            # In production, first bytes should indicate message type
            # For now, return raw bytes with warning
            logger.warning("Protobuf deserialization requires message type information. "
                         "Implement envelope pattern with type discriminator.")
            
            # Return as dict for compatibility
            # In production, parse based on envelope type field
            return {'__raw_protobuf__': data}
            
        except Exception as e:
            logger.error(f"Protobuf deserialization failed: {e}")
            raise DeserializationError(f"Failed to deserialize Protobuf: {e}") from e
    
    def content_type(self) -> str:
        """Get content type"""
        return 'application/x-protobuf'
    
    def supports_schema_evolution(self) -> bool:
        """Protobuf supports schema evolution with field numbering rules"""
        return True
    
    def get_format_name(self) -> str:
        """Get format name"""
        return 'protobuf'
    
    def register_schema(self, event_type: str, proto_class: Type) -> None:
        """
        Register a protobuf message class for an event type
        
        Args:
            event_type: Event type identifier
            proto_class: Protobuf message class
        """
        self.schema_registry[event_type] = proto_class
        logger.info(f"Registered protobuf schema for {event_type}")
