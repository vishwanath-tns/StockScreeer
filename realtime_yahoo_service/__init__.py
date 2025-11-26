"""
Real-Time Yahoo Finance Service
================================

Event-driven data distribution system for real-time market data.

Features:
- Broker-agnostic publisher architecture (polling/streaming)
- Redis Pub/Sub for horizontal scaling
- Pluggable message serialization (JSON/MessagePack/Protobuf)
- Dead Letter Queue for fault tolerance
- Per-subscriber database connection pools
- Comprehensive monitoring and health checks
"""

__version__ = "1.0.0"
__author__ = "Stock Screener Team"

# Lazy imports - only import when modules exist
__all__ = []
