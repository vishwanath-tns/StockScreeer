"""
DLQ Package
===========

Dead Letter Queue for handling failed message processing.
"""

from .dlq_manager import DLQManager, DLQMessage

__all__ = [
    'DLQManager',
    'DLQMessage',
]
