# Stock Alert System

A comprehensive, event-driven stock price alert system with support for NSE/BSE equities, commodities, and cryptocurrencies.

## Features

- **Multi-Asset Support**: NSE/BSE stocks, indices, commodities (Gold, Silver, Crude), and cryptocurrencies
- **Flexible Alert Types**: Price (above/below/between), Volume spikes, Technical indicators (RSI, MACD, Bollinger Bands)
- **Multi-User**: Support for multiple users with API key authentication
- **Event-Driven Architecture**: Redis Pub/Sub for real-time event processing
- **Scalable Workers**: Async workers for price monitoring, alert evaluation, and notifications
- **Desktop Notifications**: Windows toast notifications with sound alerts
- **REST API**: Full FastAPI-based REST API for external integrations
- **External Scanner Integration**: Other systems can create alerts via API

## Quick Start

### 1. Initialize Database

First time only - creates the `alerts_db` database and tables:

```bash
python -m stock_alerts.scripts.init_database
```

### 2. Run in Demo Mode (No Redis Required)

Test the system without Redis:

```bash
python stock_alerts_launcher.py demo
```

### 3. Run the Desktop GUI

```bash
python stock_alerts_launcher.py gui
```

### 4. Run Full System (Requires Redis)

```bash
# Start Redis (using Docker)
docker run -d -p 6379:6379 redis

# Run API + Workers
python stock_alerts_launcher.py
```

## Architecture

```
stock_alerts/
├── api/                    # FastAPI REST API
│   ├── app.py             # Main FastAPI application
│   ├── auth.py            # JWT & API Key authentication
│   └── routes/            # API route handlers
├── core/                   # Domain models and business logic
│   ├── enums.py           # Enumerations (AssetType, AlertCondition, etc.)
│   ├── models.py          # Data models (Alert, PriceData, etc.)
│   └── evaluators.py      # Alert condition evaluators
├── events/                 # Event system
│   ├── events.py          # Event classes (PriceUpdateEvent, AlertTriggeredEvent)
│   └── event_bus.py       # Redis Pub/Sub event bus
├── infrastructure/         # Database and Redis clients
│   ├── config.py          # Configuration management
│   ├── database.py        # MySQL connection
│   └── redis_client.py    # Redis client
├── services/               # Business services
│   ├── alert_service.py   # Alert CRUD operations
│   ├── symbol_service.py  # Symbol lookup and validation
│   └── user_service.py    # User management
├── workers/                # Async background workers
│   ├── base_worker.py     # Base worker class
│   ├── price_monitor.py   # Fetches prices from Yahoo Finance
│   ├── alert_evaluator.py # Evaluates alerts against prices
│   └── notification_dispatcher.py  # Sends notifications
├── gui/                    # PyQt6 Desktop GUI
│   └── main_window.py     # Main application window
├── scripts/                # Utility scripts
│   ├── init_db.sql        # SQL schema
│   └── init_database.py   # Database initialization
├── main.py                 # Main entry point
└── requirements.txt        # Dependencies
```

## Configuration

Configuration is loaded from environment variables. Create a `.env` file or set these variables:

### Database
```env
ALERTS_DB_HOST=localhost
ALERTS_DB_PORT=3306
ALERTS_DB_NAME=alerts_db
ALERTS_DB_USER=root
ALERTS_DB_PASSWORD=your_password
```

### Redis
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### API
```env
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET=your-secret-key
```

## Alert Types

### Price Alerts
- `price_above` - Triggers when price goes above target
- `price_below` - Triggers when price goes below target
- `price_between` - Triggers when price is between two values
- `price_crosses_above` - Triggers when price crosses above target
- `price_crosses_below` - Triggers when price crosses below target
- `pct_change_up` - Triggers on % increase from previous close
- `pct_change_down` - Triggers on % decrease from previous close

### Volume Alerts
- `volume_above` - Triggers when volume exceeds threshold
- `volume_spike` - Triggers on unusual volume activity

### Technical Alerts
- `rsi_overbought` - RSI > 70
- `rsi_oversold` - RSI < 30
- `macd_bullish_cross` - MACD crosses above signal
- `macd_bearish_cross` - MACD crosses below signal
- `high_52w` - New 52-week high
- `low_52w` - New 52-week low

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/register` - Register new user

### Alerts
- `GET /api/alerts` - List user's alerts
- `POST /api/alerts` - Create new alert
- `GET /api/alerts/{id}` - Get alert details
- `PUT /api/alerts/{id}` - Update alert
- `DELETE /api/alerts/{id}` - Delete alert

### Symbols
- `GET /api/symbols/search` - Search for symbols
- `GET /api/symbols/price/{symbol}` - Get current price

## Launcher Commands

```bash
python stock_alerts_launcher.py [command]
```

| Command   | Description |
|-----------|-------------|
| `all`     | Run API + Workers (default) |
| `api`     | Run API server only |
| `worker`  | Run workers only |
| `demo`    | Demo mode (no Redis) |
| `gui`     | Desktop GUI |
| `check`   | Check dependencies |
| `init-db` | Initialize database |

## Dependencies

Install with:
```bash
pip install -r stock_alerts/requirements.txt
```

Core dependencies:
- `fastapi` + `uvicorn` - REST API
- `redis` - Event bus and caching
- `aiomysql` - Async MySQL
- `yfinance` - Price data
- `PyQt6` - Desktop GUI
- `win10toast` / `plyer` - Desktop notifications

## Data Sources

All price data is fetched from Yahoo Finance:
- NSE stocks: `SYMBOL.NS` (e.g., `RELIANCE.NS`)
- BSE stocks: `SYMBOL.BO` (e.g., `RELIANCE.BO`)
- Indices: `^NSEI` (NIFTY 50), `^NSEBANK` (Bank NIFTY)
- Commodities: `GC=F` (Gold), `CL=F` (Crude), `SI=F` (Silver)
- Crypto: `BTC-USD`, `ETH-USD`, etc.

## License

MIT License
