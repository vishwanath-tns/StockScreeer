# Real-Time Yahoo Finance Service

Event-driven data distribution system for real-time market data with broker-agnostic architecture, pluggable serialization, and fault tolerance.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- Redis 7.0+ (optional, for production)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### Run the Service

```bash
# Development mode (in-memory broker, JSON serialization)
python realtime_service.py

# Production mode (Redis broker, MessagePack serialization)
export REDIS_URL=redis://localhost:6379/0
export SERIALIZATION_FORMAT=msgpack
python realtime_service.py
```

## 📁 Project Structure

```
realtime_yahoo_service/
├── events/
│   ├── schemas/v1/          # Protocol Buffer definitions
│   ├── event_models.py      # Pydantic event models
│   ├── event_broker.py      # In-memory broker
│   └── broker_factory.py    # Broker selection logic
├── publisher/
│   ├── base_publisher.py    # Abstract publisher interface
│   ├── yahoo_polling_publisher.py  # Yahoo Finance implementation
│   └── streaming_publisher.py      # WebSocket stub for future brokers
├── subscribers/
│   ├── base_subscriber.py           # Abstract subscriber with DLQ
│   ├── db_writer_subscriber.py      # Database persistence
│   ├── state_tracker_subscriber.py  # Download state tracking
│   ├── performance_monitor_subscriber.py  # Prometheus metrics
│   └── market_breadth_subscriber.py       # A/D calculation
├── serialization/
│   ├── base_serializer.py      # IMessageSerializer interface
│   ├── json_serializer.py      # JSON implementation
│   ├── msgpack_serializer.py   # MessagePack implementation
│   ├── protobuf_serializer.py  # Protocol Buffers implementation
│   └── serializer_factory.py   # Auto-selection factory
├── redis_broker/
│   └── redis_event_broker.py   # Redis Pub/Sub implementation
├── dlq/
│   ├── dlq_manager.py          # Dead Letter Queue manager
│   ├── dlq_subscriber.py       # DLQ monitoring
│   └── dlq_replayer.py         # CLI tool for replaying failed events
├── clients/
│   ├── python_client.py        # Async WebSocket client library
│   ├── websocket_server.py     # WebSocket server
│   └── cli_subscriber.py       # Command-line subscriber tool
├── config/
│   └── service_config.yaml     # Service configuration
├── sql/
│   ├── create_realtime_download_state.sql
│   └── create_failed_events.sql
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── performance/            # Performance benchmarks
└── realtime_service.py         # Main orchestrator
```

## 🔧 Configuration

See `.env.example` and `config/service_config.yaml` for all configuration options.

### Key Configuration Options

- **Serialization Format**: `json` (dev), `msgpack` (prod), `protobuf` (high-perf)
- **Event Broker**: Redis (prod) or in-memory (dev)
- **Connection Pools**: Per-subscriber isolated pools to avoid contention
- **Dead Letter Queue**: Automatic retry with exponential backoff

## 📊 Monitoring

Access monitoring endpoints:

- **Health Check**: `http://localhost:8080/health`
- **Prometheus Metrics**: `http://localhost:8080/metrics`

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=realtime_yahoo_service

# Run performance benchmarks
pytest tests/performance/
```

## 📝 Architecture

### Event Flow

```
Yahoo Finance API
       ↓
YahooPollingPublisher (rate-limited, batched)
       ↓
Serializer (JSON/MessagePack/Protobuf)
       ↓
Event Broker (Redis Pub/Sub or In-Memory)
       ↓
    ┌──────┴──────┬─────────┬──────────┬─────────┐
    ↓             ↓         ↓          ↓         ↓
DBWriter   StateTracker  Breadth  Portfolio  Alerts
    ↓             ↓         ↓          ↓         ↓
MySQL DB    Tracking    Publish   P&L Calc   Notify
                          ↓
                    WebSocket Bridge
                          ↓
                  External Clients
```

### Dead Letter Queue Flow

```
Event Processing Failed
       ↓
Retry 3x with exponential backoff
       ↓
Still failing?
       ↓
Send to DLQ (Redis + MySQL)
       ↓
Manual replay via CLI tool
```

## 🔌 WebSocket Client Example

```python
import asyncio
from clients.python_client import RealtimeClient

async def main():
    client = RealtimeClient("ws://localhost:8765")
    
    # Subscribe to topics
    await client.subscribe([
        "candles/RELIANCE.NS",
        "breadth/realtime"
    ])
    
    # Register callback
    def on_event(event):
        print(f"Received: {event}")
    
    client.on_event(on_event)
    
    # Run forever
    await client.run()

asyncio.run(main())
```

## 🐳 Docker Deployment

```bash
# Start Redis + MySQL + Service
docker-compose up -d

# View logs
docker-compose logs -f realtime-service

# Stop all
docker-compose down
```

## 📚 Documentation

- Architecture: `.github/REALTIME_DATA_ARCHITECTURE.md`
- API Documentation: (Coming soon)
- Performance Benchmarks: (Coming soon)

## 🤝 Contributing

1. Create feature branch
2. Implement changes with tests
3. Run `pytest` and `black .`
4. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

## 🙋 Support

For issues and questions, please open a GitHub issue.
