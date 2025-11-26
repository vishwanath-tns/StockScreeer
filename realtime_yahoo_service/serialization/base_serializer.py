"""
Base Serializer Interface
==========================

Abstract interface for message serialization formats.
Allows pluggable serialization strategies (JSON, MessagePack, Protobuf).
"""

from abc import ABC, abstractmethod
from typing import Any


class IMessageSerializer(ABC):
    """Abstract interface for message serialization"""
    
    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize an object to bytes
        
        Args:
            obj: Object to serialize (typically dict or Pydantic model)
            
        Returns:
            Serialized bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes to an object
        
        Args:
            data: Serialized bytes
            
        Returns:
            Deserialized object (dict or specific type)
            
        Raises:
            DeserializationError: If deserialization fails
        """
        pass
    
    @abstractmethod
    def content_type(self) -> str:
        """
        Get the content type identifier
        
        Returns:
            Content type string (e.g., 'application/json')
        """
        pass
    
    @abstractmethod
    def supports_schema_evolution(self) -> bool:
        """
        Check if serializer supports schema evolution
        
        Returns:
            True if backward/forward compatible schema changes are supported
        """
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """
        Get the format name
        
        Returns:
            Format name (e.g., 'json', 'msgpack', 'protobuf')
        """
        pass


class SerializationError(Exception):
    """Raised when serialization fails"""
    pass


class DeserializationError(Exception):
    """Raised when deserialization fails"""
    pass
