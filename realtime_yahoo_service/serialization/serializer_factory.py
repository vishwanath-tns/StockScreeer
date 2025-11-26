"""
Serializer Factory
==================

Factory for creating serializer instances based on configuration.
Auto-selects serializer based on environment variables or config.
"""

import os
import logging
from typing import Optional

from .base_serializer import IMessageSerializer
from .json_serializer import JSONSerializer
from .msgpack_serializer import MessagePackSerializer
from .protobuf_serializer import ProtobufSerializer

logger = logging.getLogger(__name__)


class SerializerFactory:
    """Factory for creating message serializers"""
    
    # Registered serializers
    _serializers = {
        'json': JSONSerializer,
        'msgpack': MessagePackSerializer,
        'protobuf': ProtobufSerializer
    }
    
    @classmethod
    def create(cls, format_name: Optional[str] = None, **kwargs) -> IMessageSerializer:
        """
        Create a serializer instance
        
        Args:
            format_name: Serialization format ('json', 'msgpack', 'protobuf')
                        If None, reads from SERIALIZATION_FORMAT env variable
            **kwargs: Additional arguments for serializer constructor
            
        Returns:
            IMessageSerializer instance
            
        Raises:
            ValueError: If format_name is invalid
        """
        # Get format from environment if not specified
        if format_name is None:
            format_name = os.getenv('SERIALIZATION_FORMAT', 'json').lower()
        
        format_name = format_name.lower()
        
        # Validate format
        if format_name not in cls._serializers:
            available = ', '.join(cls._serializers.keys())
            raise ValueError(
                f"Invalid serialization format: {format_name}. "
                f"Available formats: {available}"
            )
        
        # Create serializer
        serializer_class = cls._serializers[format_name]
        serializer = serializer_class(**kwargs)
        
        logger.info(f"Created {format_name} serializer: {serializer.content_type()}")
        
        return serializer
    
    @classmethod
    def create_for_environment(cls) -> IMessageSerializer:
        """
        Create serializer optimized for current environment
        
        Development: JSON (human-readable)
        Staging/Production: MessagePack (performance + debuggable)
        High-performance: Protobuf (maximum efficiency)
        
        Returns:
            IMessageSerializer instance
        """
        env = os.getenv('ENVIRONMENT', 'development').lower()
        
        if env in ('production', 'staging'):
            # Production: Use MessagePack for balance
            logger.info("Creating MessagePack serializer for production environment")
            return cls.create('msgpack')
        elif env == 'development':
            # Development: Use pretty JSON for debugging
            logger.info("Creating JSON serializer for development environment")
            return cls.create('json', pretty=True)
        else:
            # Default to MessagePack
            logger.info(f"Unknown environment '{env}', defaulting to MessagePack")
            return cls.create('msgpack')
    
    @classmethod
    def register_serializer(cls, format_name: str, serializer_class: type) -> None:
        """
        Register a custom serializer
        
        Args:
            format_name: Format identifier
            serializer_class: Serializer class (must implement IMessageSerializer)
        """
        if not issubclass(serializer_class, IMessageSerializer):
            raise TypeError(f"{serializer_class} must implement IMessageSerializer")
        
        cls._serializers[format_name.lower()] = serializer_class
        logger.info(f"Registered custom serializer: {format_name}")
    
    @classmethod
    def get_available_formats(cls) -> list:
        """
        Get list of available serialization formats
        
        Returns:
            List of format names
        """
        return list(cls._serializers.keys())
    
    @classmethod
    def get_recommended_format(cls, use_case: str = 'general') -> str:
        """
        Get recommended serialization format for a use case
        
        Args:
            use_case: Use case identifier
                     - 'development': Debugging and development
                     - 'general': General production use
                     - 'high_performance': Maximum throughput
                     - 'external_api': API exposed to external clients
        
        Returns:
            Recommended format name
        """
        recommendations = {
            'development': 'json',
            'general': 'msgpack',
            'high_performance': 'protobuf',
            'external_api': 'json'
        }
        
        return recommendations.get(use_case, 'msgpack')


# Convenience function for quick serializer creation
def get_serializer(format_name: Optional[str] = None) -> IMessageSerializer:
    """
    Convenience function to get a serializer
    
    Args:
        format_name: Serialization format or None for auto-detection
        
    Returns:
        IMessageSerializer instance
    """
    return SerializerFactory.create(format_name)
