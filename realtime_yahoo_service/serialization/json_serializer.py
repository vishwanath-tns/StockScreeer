"""
JSON Serializer
===============

Human-readable JSON serialization.
Best for development and debugging.
"""

import json
import logging
from typing import Any
from datetime import datetime, date
from decimal import Decimal

from .base_serializer import IMessageSerializer, SerializationError, DeserializationError

logger = logging.getLogger(__name__)


class JSONSerializer(IMessageSerializer):
    """JSON serialization implementation"""
    
    def __init__(self, pretty: bool = False):
        """
        Initialize JSON serializer
        
        Args:
            pretty: If True, format JSON with indentation
        """
        self.pretty = pretty
    
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize object to JSON bytes
        
        Args:
            obj: Object to serialize (dict, list, or Pydantic model)
            
        Returns:
            JSON bytes (UTF-8 encoded)
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            # Handle Pydantic models
            if hasattr(obj, 'model_dump'):
                obj = obj.model_dump()
            elif hasattr(obj, 'dict'):
                obj = obj.dict()
            
            # Convert to JSON string
            if self.pretty:
                json_str = json.dumps(obj, default=self._json_default, indent=2, sort_keys=True)
            else:
                json_str = json.dumps(obj, default=self._json_default, separators=(',', ':'))
            
            # Encode to bytes
            return json_str.encode('utf-8')
            
        except Exception as e:
            logger.error(f"JSON serialization failed: {e}")
            raise SerializationError(f"Failed to serialize to JSON: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize JSON bytes to object
        
        Args:
            data: JSON bytes (UTF-8 encoded) or already-deserialized dict
            
        Returns:
            Deserialized dict or list
            
        Raises:
            DeserializationError: If deserialization fails
        """
        try:
            # Handle already-deserialized data (in-memory broker optimization)
            if isinstance(data, (dict, list)):
                return data
            
            # Decode bytes to string
            json_str = data.decode('utf-8')
            
            # Parse JSON
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"JSON deserialization failed: {e}")
            raise DeserializationError(f"Failed to deserialize JSON: {e}") from e
    
    def content_type(self) -> str:
        """Get content type"""
        return 'application/json'
    
    def supports_schema_evolution(self) -> bool:
        """JSON supports adding/removing fields"""
        return True
    
    def get_format_name(self) -> str:
        """Get format name"""
        return 'json'
    
    @staticmethod
    def _json_default(obj: Any) -> Any:
        """
        Handle non-serializable types
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON-serializable value
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
