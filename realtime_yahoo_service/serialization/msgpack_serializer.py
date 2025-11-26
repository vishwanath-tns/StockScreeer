"""
MessagePack Serializer
======================

Binary serialization with 30-40% size reduction vs JSON.
Recommended for production use - good balance of performance and debugging.
"""

import logging
from typing import Any
from datetime import datetime, date
from decimal import Decimal

try:
    import msgpack
except ImportError:
    msgpack = None

from .base_serializer import IMessageSerializer, SerializationError, DeserializationError

logger = logging.getLogger(__name__)


class MessagePackSerializer(IMessageSerializer):
    """MessagePack serialization implementation"""
    
    def __init__(self, use_bin_type: bool = True):
        """
        Initialize MessagePack serializer
        
        Args:
            use_bin_type: If True, use binary type for bytes (recommended)
        """
        if msgpack is None:
            raise ImportError("msgpack is not installed. Install with: pip install msgpack")
        
        self.use_bin_type = use_bin_type
    
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize object to MessagePack bytes
        
        Args:
            obj: Object to serialize (dict, list, or Pydantic model)
            
        Returns:
            MessagePack bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            # Handle Pydantic models
            if hasattr(obj, 'model_dump'):
                obj = obj.model_dump()
            elif hasattr(obj, 'dict'):
                obj = obj.dict()
            
            # Serialize to MessagePack
            return msgpack.packb(
                obj,
                default=self._msgpack_default,
                use_bin_type=self.use_bin_type
            )
            
        except Exception as e:
            logger.error(f"MessagePack serialization failed: {e}")
            raise SerializationError(f"Failed to serialize to MessagePack: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize MessagePack bytes to object
        
        Args:
            data: MessagePack bytes
            
        Returns:
            Deserialized dict or list
            
        Raises:
            DeserializationError: If deserialization fails
        """
        try:
            # Unpack MessagePack
            return msgpack.unpackb(
                data,
                raw=False,
                strict_map_key=False
            )
            
        except Exception as e:
            logger.error(f"MessagePack deserialization failed: {e}")
            raise DeserializationError(f"Failed to deserialize MessagePack: {e}") from e
    
    def content_type(self) -> str:
        """Get content type"""
        return 'application/msgpack'
    
    def supports_schema_evolution(self) -> bool:
        """MessagePack supports adding/removing fields"""
        return True
    
    def get_format_name(self) -> str:
        """Get format name"""
        return 'msgpack'
    
    @staticmethod
    def _msgpack_default(obj: Any) -> Any:
        """
        Handle non-serializable types
        
        Args:
            obj: Object to convert
            
        Returns:
            MessagePack-serializable value
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
