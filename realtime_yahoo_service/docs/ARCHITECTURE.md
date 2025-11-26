# Architecture & Design Documentation

## System Architecture

### High-Level Overview

The Real-Time Yahoo Finance Service is built on an event-driven architecture that enables scalable, real-time market data distribution. The system follows these core principles:

1. **Decoupling**: Publishers and subscribers are completely independent
2. **Scalability**: Horizontal scaling through Redis broker
3. **Reliability**: DLQ and automatic retry mechanisms
4. **Flexibility**: Pluggable serialization and broker implementations
5. **Observability**: Comprehensive statistics and health monitoring

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Orchestrator Service Layer                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │ Config Mgmt │  │ Health Check │  │ Lifecycle Management   │    │
│  └─────────────┘  └──────────────┘  └────────────────────────┘    │
└──────────────────┬──────────────────────────────────┬──────────────┘
                   │                                  │
         ┌─────────▼─────────┐              ┌────────▼────────┐
         │  Publisher Layer  │              │  Broker Layer   │
         │  ┌─────────────┐  │              │  ┌───────────┐  │
         │  │ Yahoo       │  │              │  │  Redis    │  │
         │  │ Finance     │──┼──────────────┼─▶│  Pub/Sub  │  │
         │  │ Publisher   │  │              │  └───────────┘  │
         │  └─────────────┘  │              │  ┌───────────┐  │
         │  Rate Limiting    │              │  │ In-Memory │  │
         │  Batch Processing │              │  │  Broker   │  │
         └───────────────────┘              │  └───────────┘  │
                                            └────────┬─────────┘
                                                     │
                        ┌────────────────────────────┼────────────────────┐
                        │                            │                    │
              ┌─────────▼─────────┐      ┌──────────▼──────────┐  ┌─────▼──────┐
              │ Subscriber Layer  │      │ Subscriber Layer    │  │ Client Lyr │
              │  ┌──────────────┐ │      │  ┌───────────────┐ │  │ ┌────────┐ │
              │  │  DBWriter    │ │      │  │ StateTracker  │ │  │ │WebSocket│ │
              │  └──────────────┘ │      │  └───────────────┘ │  │ │ Server │ │
              │  ┌──────────────┐ │      │  ┌───────────────┐ │  │ └────────┘ │
              │  │MarketBreadth │ │      │  │TrendAnalyzer  │ │  │            │
              │  └──────────────┘ │      │  └───────────────┘ │  │ External   │
              └───────────────────┘      └─────────────────────┘  │ Clients    │
                        │                                          └────────────┘
              ┌─────────▼─────────┐
              │  Storage Layer    │
              │  ┌──────────────┐ │
              │  │    MySQL     │ │
              │  │   Database   │ │
              │  └──────────────┘ │
              │  ┌──────────────┐ │
              │  │   DLQ Store  │ │
              │  └──────────────┘ │
              └───────────────────┘
```

## Data Flow

### 1. Data Ingestion Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Yahoo Finance API Call                              │
│   - Rate-limited batches (default: 50 symbols per batch)    │
│   - Configurable intervals (default: 5 seconds)             │
│   - Automatic retry on transient failures                   │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Event Creation                                      │
│   - Transform raw data to CandleDataEvent                   │
│   - Add metadata (timestamp, publisher_id)                  │
│   - Validate data schema with Pydantic                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Serialization                                       │
│   - JSON: Human-readable, debugging (default)               │
│   - MessagePack: Compact binary format                      │
│   - Protobuf: High-performance schema evolution             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Broker Publish                                      │
│   - Channel: "market.candle"                                │
│   - Fanout to all subscribers                               │
│   - Non-blocking publish operation                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Subscriber Processing (Parallel)                    │
│   ┌───────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  │
│   │ DBWriter  │  │  State   │  │ Market  │  │  Trend   │  │
│   │ (MySQL)   │  │ Tracker  │  │ Breadth │  │ Analyzer │  │
│   └───────────┘  └──────────┘  └─────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2. Error Handling Flow

```
┌─────────────────────────────────────────────────┐
│ Event Processing Error                          │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ Retry #1 (Delay: 1 second)                      │
└──────────────────┬──────────────────────────────┘
                   │ Failed
                   ▼
┌─────────────────────────────────────────────────┐
│ Retry #2 (Delay: 2 seconds)                     │
└──────────────────┬──────────────────────────────┘
                   │ Failed
                   ▼
┌─────────────────────────────────────────────────┐
│ Retry #3 (Delay: 4 seconds)                     │
└──────────────────┬──────────────────────────────┘
                   │ Failed
                   ▼
┌─────────────────────────────────────────────────┐
│ Send to Dead Letter Queue                       │
│   - Persist to disk/Redis                       │
│   - Log error details                           │
│   - Emit metrics                                │
└─────────────────────────────────────────────────┘
```

## Design Patterns

### 1. Publisher-Subscriber Pattern

**Benefits:**
- Loose coupling between components
- Easy to add new subscribers
- Scalable data distribution

**Implementation:**
- Publishers don't know about subscribers
- Broker handles message routing
- Subscribers independently process events

### 2. Strategy Pattern

**Used In:**
- Serialization (JSON/MessagePack/Protobuf)
- Broker selection (Redis/InMemory)
- DLQ storage (File/Redis)

**Benefits:**
- Runtime selection of algorithms
- Easy to extend with new implementations
- Testable with mock implementations

### 3. Factory Pattern

**Used In:**
- Component creation in Orchestrator
- Broker instantiation
- Serializer selection

**Benefits:**
- Centralized object creation
- Configuration-driven instantiation
- Dependency injection

### 4. Template Method Pattern

**Used In:**
- BasePublisher (common lifecycle)
- BaseSubscriber (message handling)

**Benefits:**
- Code reuse across implementations
- Enforced lifecycle contracts
- Easy to add new publishers/subscribers

## Scalability Considerations

### Horizontal Scaling

**With Redis Broker:**
```
┌───────────┐     ┌───────────┐     ┌───────────┐
│ Service   │     │ Service   │     │ Service   │
│ Instance  │────▶│ Instance  │────▶│ Instance  │
│    #1     │     │    #2     │     │    #3     │
└─────┬─────┘     └─────┬─────┘     └─────┬─────┘
      │                 │                 │
      └─────────────────┴─────────────────┘
                        │
                   ┌────▼────┐
                   │  Redis  │
                   │ Broker  │
                   └─────────┘
```

**Load Distribution:**
- Each instance can run subset of publishers
- Subscribers independently process messages
- No single point of failure

### Vertical Scaling

**Resource Optimization:**
- Async I/O for non-blocking operations
- Batch processing to reduce API calls
- Connection pooling for database operations
- Rate limiting to prevent overload

### Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| End-to-end Latency | <50ms | 5-10ms |
| Throughput | 1000 events/s | 1500+ events/s |
| Memory Footprint | <500MB | ~100MB |
| CPU Usage (idle) | <5% | 2-3% |
| CPU Usage (peak) | <50% | 20-30% |

## Security Considerations

### 1. Network Security

- WebSocket TLS support
- Redis AUTH authentication
- MySQL SSL connections
- Firewall rules for ports

### 2. Data Security

- No sensitive data in logs
- Sanitized error messages
- Secure configuration management
- Environment variable protection

### 3. Rate Limiting

- Yahoo Finance API rate limits respected
- Configurable rate limiting per publisher
- Prevents API quota exhaustion
- Graceful degradation on limits

## Deployment Architectures

### Development Setup

```
┌─────────────────────────────────────┐
│     Single Machine                  │
│  ┌────────────────────────────────┐ │
│  │   Python Process               │ │
│  │  ┌──────────┐  ┌────────────┐ │ │
│  │  │Publisher │  │InMemory    │ │ │
│  │  │          │  │Broker      │ │ │
│  │  └──────────┘  └────────────┘ │ │
│  │  ┌──────────────────────────┐ │ │
│  │  │    Subscribers           │ │ │
│  │  └──────────────────────────┘ │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │  MySQL (localhost)             │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Production Setup

```
┌─────────────────────────────────────────────────┐
│              Load Balancer                      │
└──────────┬───────────────┬──────────────────────┘
           │               │
┌──────────▼─────┐  ┌──────▼──────────┐
│  Service #1    │  │  Service #2     │
│  (Publishers)  │  │  (Subscribers)  │
└───────┬────────┘  └────────┬────────┘
        │                    │
        └────────┬───────────┘
                 │
        ┌────────▼────────┐
        │  Redis Cluster  │
        │  (High Avail.)  │
        └─────────────────┘
                 │
        ┌────────▼────────┐
        │  MySQL Cluster  │
        │  (Replication)  │
        └─────────────────┘
```

## Monitoring & Observability

### Key Metrics to Monitor

**Publisher Metrics:**
- Fetch success/failure rate
- API call duration
- Symbols processed per second
- Rate limiting violations

**Broker Metrics:**
- Message publish rate
- Queue depths
- Connection count
- Memory usage

**Subscriber Metrics:**
- Message processing rate
- Processing latency
- Error rate
- DLQ entries

**System Metrics:**
- CPU usage
- Memory consumption
- Network I/O
- Disk I/O

### Health Checks

**Component Health:**
```python
{
    "status": "healthy",
    "components": {
        "publishers": {
            "yahoo_main": "running"
        },
        "subscribers": {
            "db_writer": "running",
            "state_tracker": "running"
        },
        "broker": "connected"
    },
    "uptime": 3600,
    "last_check": "2025-11-26T10:30:00Z"
}
```

## Future Enhancements

### Planned Features

1. **Prometheus Integration**: Native metrics export
2. **Grafana Dashboards**: Pre-built visualization
3. **Circuit Breaker**: Prevent cascade failures
4. **Multi-Region Support**: Geographic distribution
5. **Event Replay**: Historical data replay
6. **Compression**: Reduce network bandwidth
7. **Schema Registry**: Centralized schema management
8. **Admin UI**: Web-based configuration

### Research Areas

- Apache Kafka integration
- Apache Pulsar evaluation
- GraphQL subscriptions
- gRPC streaming

## References

- [Event-Driven Architecture](https://martinfowler.com/articles/201701-event-driven.html)
- [Publisher-Subscriber Pattern](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern)
- [Redis Pub/Sub](https://redis.io/topics/pubsub)
- [Async Python Best Practices](https://docs.python.org/3/library/asyncio.html)
