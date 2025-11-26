# API Reference

## Event Models

### CandleDataEvent

Represents market candle/bar data for a symbol.

```python
from events import CandleDataEvent

event = CandleDataEvent(
    symbol="AAPL",
    timestamp=datetime.now(),
    open=150.00,
    high=152.50,
    low=149.00,
    close=151.75,
    volume=1000000,
    publisher_id="yahoo_main"
)
```

**Fields:**
- `symbol` (str): Stock ticker symbol
- `timestamp` (datetime): Event timestamp
- `open` (float): Opening price
- `high` (float): Highest price in period
- `low` (float): Lowest price in period
- `close` (float): Closing price
- `volume` (int): Trading volume
- `publisher_id` (str): Source publisher identifier

### FetchStatusEvent

Publisher status information.

```python
from events import FetchStatusEvent

event = FetchStatusEvent(
    publisher_id="yahoo_main",
    status="completed",
    symbols_count=50,
    fetch_duration=2.5,
    error_message=None
)
```

**Fields:**
- `publisher_id` (str): Publisher identifier
- `status` (str): Status - 'fetching', 'completed', 'failed'
- `symbols_count` (int): Number of symbols processed
- `fetch_duration` (float, optional): Time taken in seconds
- `error_message` (str, optional): Error details if failed

### MarketBreadthEvent

Market breadth and advance/decline metrics.

```python
from events import MarketBreadthEvent

event = MarketBreadthEvent(
    timestamp=datetime.now(),
    advances=120,
    declines=80,
    unchanged=5,
    advance_decline_ratio=1.5,
    total_symbols=205
)
```

**Fields:**
- `timestamp` (datetime): Calculation timestamp
- `advances` (int): Number of advancing stocks
- `declines` (int): Number of declining stocks
- `unchanged` (int): Number of unchanged stocks
- `advance_decline_ratio` (float): Advances/declines ratio
- `total_symbols` (int): Total symbols analyzed

### TrendAnalysisEvent

Technical analysis with moving averages and trends.

```python
from events import TrendAnalysisEvent

event = TrendAnalysisEvent(
    symbol="AAPL",
    timestamp=datetime.now(),
    sma_20=150.5,
    sma_50=148.2,
    sma_200=145.0,
    trend_direction="up",
    price=151.75
)
```

**Fields:**
- `symbol` (str): Stock ticker symbol
- `timestamp` (datetime): Analysis timestamp
- `sma_20` (float, optional): 20-period SMA
- `sma_50` (float, optional): 50-period SMA
- `sma_200` (float, optional): 200-period SMA
- `trend_direction` (str): 'up', 'down', 'neutral'
- `price` (float): Current price

## Publishers

### YahooFinancePublisher

Fetches real-time market data from Yahoo Finance API.

```python
from publisher import YahooFinancePublisher
from redis_broker import InMemoryBroker
from serialization import JSONSerializer

# Create publisher
publisher = YahooFinancePublisher(
    publisher_id='my_publisher',
    broker=broker,
    serializer=serializer,
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    batch_size=50,
    rate_limit=20,
    rate_limit_period=60.0,
    publish_interval=5.0,
    data_interval='1m',
    period='1d'
)

# Start publishing
await publisher.start()

# Get statistics
stats = publisher.get_stats()

# Stop publishing
await publisher.stop()
```

**Constructor Parameters:**
- `publisher_id` (str): Unique identifier
- `broker` (IEventBroker): Message broker instance
- `serializer` (IMessageSerializer): Serializer instance
- `symbols` (List[str]): Stock symbols to fetch
- `batch_size` (int): Symbols per batch (default: 50)
- `rate_limit` (int): Max requests per period (default: 20)
- `rate_limit_period` (float): Rate limit period in seconds (default: 60.0)
- `publish_interval` (float): Fetch interval in seconds (default: 5.0)
- `data_interval` (str): Yahoo interval - '1m', '5m', etc. (default: '1m')
- `period` (str): Yahoo period - '1d', '5d', etc. (default: '1d')

**Methods:**

#### `async start()`
Starts the publisher background task.

#### `async stop()`
Stops the publisher gracefully.

#### `get_stats() -> Dict[str, Any]`
Returns publisher statistics.

**Returns:**
```python
{
    'batch_size': 50,
    'symbols_count': 150,
    'data_interval': '1m',
    'period': '1d',
    'fetch_stats': {
        'symbols_fetched': 150,
        'symbols_failed': 0,
        'last_fetch_time': '2025-11-26T10:30:00',
        'last_fetch_duration': 2.5
    }
}
```

## Subscribers

### StateTrackerSubscriber

Maintains in-memory state of latest candle data.

```python
from subscribers import StateTrackerSubscriber

subscriber = StateTrackerSubscriber(
    subscriber_id='state_tracker',
    broker=broker,
    serializer=serializer
)

await subscriber.start()

# Get state for specific symbol
candle = subscriber.get_symbol_state('AAPL')

# Get all symbols
all_symbols = subscriber.get_all_symbols()

# Get statistics
stats = subscriber.get_stats()

await subscriber.stop()
```

**Methods:**

#### `get_symbol_state(symbol: str) -> Optional[CandleDataEvent]`
Returns latest candle data for symbol.

#### `get_all_symbols() -> Dict[str, CandleDataEvent]`
Returns all tracked symbols with their latest data.

#### `get_publisher_status(publisher_id: str) -> Optional[FetchStatusEvent]`
Returns status for specific publisher.

#### `get_all_publishers() -> Dict[str, FetchStatusEvent]`
Returns status for all publishers.

### DBWriterSubscriber

Persists candle data to MySQL database.

```python
from subscribers import DBWriterSubscriber

subscriber = DBWriterSubscriber(
    subscriber_id='db_writer',
    broker=broker,
    serializer=serializer,
    db_url='mysql+pymysql://user:pass@localhost/db',
    table_name='market_data',
    batch_size=100
)

await subscriber.start()
```

**Constructor Parameters:**
- `subscriber_id` (str): Unique identifier
- `broker` (IEventBroker): Broker instance
- `serializer` (IMessageSerializer): Serializer instance
- `db_url` (str): SQLAlchemy database URL
- `table_name` (str): Target table name (default: 'nse_equity_bhavcopy_full')
- `batch_size` (int): Batch insert size (default: 100)

### MarketBreadthSubscriber

Calculates advance/decline ratios and market breadth metrics.

```python
from subscribers import MarketBreadthSubscriber

subscriber = MarketBreadthSubscriber(
    subscriber_id='market_breadth',
    broker=broker,
    serializer=serializer
)

await subscriber.start()

# Get current metrics
metrics = subscriber.get_metrics()
```

**Methods:**

#### `get_metrics() -> Dict[str, Any]`
Returns current market breadth metrics.

**Returns:**
```python
{
    'advances': 120,
    'declines': 80,
    'unchanged': 5,
    'advance_decline_ratio': 1.5,
    'total_symbols': 205,
    'timestamp': '2025-11-26T10:30:00'
}
```

### TrendAnalyzerSubscriber

Computes moving averages and trend indicators.

```python
from subscribers import TrendAnalyzerSubscriber

subscriber = TrendAnalyzerSubscriber(
    subscriber_id='trend_analyzer',
    broker=broker,
    serializer=serializer
)

await subscriber.start()

# Get analysis for symbol
analysis = subscriber.get_analysis('AAPL')
```

**Methods:**

#### `get_analysis(symbol: str) -> Optional[Dict[str, Any]]`
Returns technical analysis for symbol.

**Returns:**
```python
{
    'symbol': 'AAPL',
    'sma_20': 150.5,
    'sma_50': 148.2,
    'sma_200': 145.0,
    'trend_direction': 'up',
    'price': 151.75
}
```

### WebSocketServer

Broadcasts events to WebSocket clients.

```python
from clients import WebSocketServer

server = WebSocketServer(
    subscriber_id='websocket',
    broker=broker,
    serializer=serializer,
    host='0.0.0.0',
    port=8765
)

await server.start()
```

**Constructor Parameters:**
- `subscriber_id` (str): Unique identifier
- `broker` (IEventBroker): Broker instance
- `serializer` (IMessageSerializer): Serializer instance
- `host` (str): Server host (default: '0.0.0.0')
- `port` (int): Server port (default: 8765)

**WebSocket Protocol:**

Client → Server:
```json
{
    "action": "subscribe",
    "symbol": "AAPL"
}
```

Server → Client:
```json
{
    "type": "candle",
    "data": {
        "symbol": "AAPL",
        "timestamp": "2025-11-26T10:30:00",
        "open": 150.0,
        "high": 152.5,
        "low": 149.0,
        "close": 151.75,
        "volume": 1000000
    }
}
```

## Brokers

### InMemoryBroker

Simple in-memory pub/sub broker for single-node deployments.

```python
from redis_broker import InMemoryBroker
from serialization import JSONSerializer

serializer = JSONSerializer()
broker = InMemoryBroker(serializer=serializer)

await broker.connect()

# Publish message
await broker.publish('channel', {'key': 'value'})

# Subscribe to channel
async def callback(channel, data):
    print(f"Received on {channel}: {data}")

await broker.subscribe('channel', callback)

await broker.disconnect()
```

### RedisEventBroker

Redis-based pub/sub for distributed deployments.

```python
from redis_broker import RedisEventBroker

broker = RedisEventBroker(
    host='localhost',
    port=6379,
    db=0,
    password=None,
    pool_size=10
)

await broker.connect()
# ... use like InMemoryBroker
await broker.disconnect()
```

## Orchestrator

### OrchestratorService

Central coordinator for all components.

```python
from orchestrator.service import OrchestratorService

orchestrator = OrchestratorService('config/service_config.yaml')

# Start service
await orchestrator.start()

# Get statistics
stats = orchestrator.get_stats()

# Stop service
await orchestrator.stop()

# Run with signal handlers
await orchestrator.run()
```

**Methods:**

#### `async start()`
Initializes and starts all configured components.

#### `async stop()`
Gracefully stops all components.

#### `get_stats() -> Dict[str, Any]`
Returns comprehensive statistics.

**Returns:**
```python
{
    'orchestrator': {
        'running': True,
        'publishers_count': 1,
        'subscribers_count': 4
    },
    'publishers': {
        'yahoo_main': {...}
    },
    'subscribers': {
        'state_tracker': {...},
        'db_writer': {...}
    }
}
```

#### `async run()`
Runs the service with signal handlers until shutdown.

## Configuration

### Service Configuration (YAML)

```yaml
# Broker configuration
broker:
  type: inmemory  # or 'redis'
  redis:
    host: localhost
    port: 6379
    db: 0

# Serialization
serializer:
  type: json  # or 'msgpack', 'protobuf'

# Publishers
publishers:
  - id: yahoo_main
    type: yahoo_finance
    enabled: true
    symbols: ['AAPL', 'GOOGL']
    publish_interval: 5.0
    batch_size: 50

# Subscribers
subscribers:
  - id: state_tracker
    type: state_tracker
    enabled: true
    
  - id: db_writer
    type: db_writer
    enabled: true
    db_url: "mysql+pymysql://user:pass@localhost/db"
    
  - id: websocket
    type: websocket
    enabled: true
    host: 0.0.0.0
    port: 8765

# Health monitoring
health:
  check_interval: 10
  restart_on_failure: true
  max_restart_attempts: 3
  restart_delay: 5

# Logging
logging:
  level: INFO
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

## Error Handling

### Custom Exceptions

```python
from subscribers.base_subscriber import SubscriberError
from publisher.base_publisher import PublisherError
from redis_broker.base_broker import BrokerError

try:
    await subscriber.start()
except SubscriberError as e:
    print(f"Subscriber failed: {e}")
```

### Dead Letter Queue

```python
from dlq import DLQManager

dlq = DLQManager(
    storage_path='./dlq',
    max_retries=3,
    retry_delay_base=60.0
)

# Queue failed message
await dlq.add_message(
    channel='market.candle',
    message={'symbol': 'AAPL'},
    error='Database connection failed'
)

# Retrieve failed messages
failed = await dlq.get_failed_messages(limit=10)

# Retry message
await dlq.retry_message(message_id)
```

## Examples

See the following for complete examples:
- `examples/basic_publisher.py` - Simple publisher example
- `examples/basic_subscriber.py` - Simple subscriber example
- `examples/websocket_client.py` - WebSocket client
- `examples/full_service.py` - Complete service setup
