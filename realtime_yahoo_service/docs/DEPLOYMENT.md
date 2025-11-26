# Deployment Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Monitoring Setup](#monitoring-setup)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 2GB
- Disk: 10GB
- Python 3.11+

**Recommended:**
- CPU: 4+ cores
- RAM: 8GB
- Disk: 50GB SSD
- Python 3.11+

### Software Dependencies

- Python 3.11 or higher
- MySQL 8.0+ (for DBWriter subscriber)
- Redis 7.0+ (for production deployment)
- Git

## Development Deployment

### 1. Clone Repository

```bash
git clone <repository-url>
cd realtime_yahoo_service
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Service

Create `config/dev_config.yaml`:

```yaml
broker:
  type: inmemory

serializer:
  type: json

dlq:
  enabled: true
  file_path: ./dev_dlq

publishers:
  - id: yahoo_dev
    type: yahoo_finance
    enabled: true
    symbols: ['AAPL', 'GOOGL']
    publish_interval: 10.0
    batch_size: 10

subscribers:
  - id: state_tracker
    type: state_tracker
    enabled: true

health:
  check_interval: 30
  restart_on_failure: false

logging:
  level: DEBUG
```

### 5. Run Service

```bash
python main.py --config config/dev_config.yaml
```

### 6. Verify Operation

```bash
# Check logs
tail -f service.log

# Test WebSocket (if enabled)
# Open examples/test_websocket_client.html in browser
```

## Production Deployment

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip redis-server mysql-server

# Start services
sudo systemctl start redis
sudo systemctl enable redis
sudo systemctl start mysql
sudo systemctl enable mysql
```

### 2. Application Setup

```bash
# Create app user
sudo useradd -r -s /bin/bash -d /opt/realtime_service realtime

# Create directories
sudo mkdir -p /opt/realtime_service
sudo mkdir -p /var/log/realtime_service
sudo mkdir -p /var/lib/realtime_service/dlq

# Set permissions
sudo chown -R realtime:realtime /opt/realtime_service
sudo chown -R realtime:realtime /var/log/realtime_service
sudo chown -R realtime:realtime /var/lib/realtime_service

# Switch to app user
sudo su - realtime
```

### 3. Deploy Application

```bash
cd /opt/realtime_service

# Clone repository
git clone <repository-url> app
cd app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Production Settings

Create `/opt/realtime_service/app/config/production.yaml`:

```yaml
broker:
  type: redis
  redis:
    host: localhost
    port: 6379
    db: 0
    password: ${REDIS_PASSWORD}
    pool_size: 20

serializer:
  type: msgpack  # More efficient than JSON

dlq:
  enabled: true
  file_path: /var/lib/realtime_service/dlq
  max_retries: 5
  retention_days: 30

publishers:
  - id: yahoo_main
    type: yahoo_finance
    enabled: true
    symbols: ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    publish_interval: 5.0
    batch_size: 50
    rate_limit: 20
    rate_limit_period: 60.0

subscribers:
  - id: state_tracker
    type: state_tracker
    enabled: true
    
  - id: db_writer
    type: db_writer
    enabled: true
    db_url: ${DATABASE_URL}
    batch_size: 200
    
  - id: market_breadth
    type: market_breadth
    enabled: true
    
  - id: trend_analyzer
    type: trend_analyzer
    enabled: true
    
  - id: websocket
    type: websocket
    enabled: true
    host: 0.0.0.0
    port: 8765

health:
  check_interval: 10
  restart_on_failure: true
  max_restart_attempts: 5
  restart_delay: 10

logging:
  level: INFO
  file: /var/log/realtime_service/service.log
  max_bytes: 10485760  # 10MB
  backup_count: 10
```

### 5. Environment Variables

Create `/opt/realtime_service/app/.env`:

```bash
REDIS_PASSWORD=your_redis_password
DATABASE_URL=mysql+pymysql://user:password@localhost/dbname
```

### 6. Create Systemd Service

Create `/etc/systemd/system/realtime-service.service`:

```ini
[Unit]
Description=Real-Time Yahoo Finance Service
After=network.target redis.service mysql.service
Wants=redis.service mysql.service

[Service]
Type=simple
User=realtime
Group=realtime
WorkingDirectory=/opt/realtime_service/app
Environment="PATH=/opt/realtime_service/app/venv/bin"
EnvironmentFile=/opt/realtime_service/app/.env
ExecStart=/opt/realtime_service/app/venv/bin/python main.py --config config/production.yaml
Restart=always
RestartSec=10
StandardOutput=append:/var/log/realtime_service/stdout.log
StandardError=append:/var/log/realtime_service/stderr.log

# Resource limits
LimitNOFILE=65536
MemoryMax=4G

[Install]
WantedBy=multi-user.target
```

### 7. Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start service
sudo systemctl start realtime-service

# Enable auto-start
sudo systemctl enable realtime-service

# Check status
sudo systemctl status realtime-service

# View logs
sudo journalctl -u realtime-service -f
```

## Docker Deployment

### 1. Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/logs /app/dlq

# Expose WebSocket port
EXPOSE 8765

# Run service
CMD ["python", "main.py", "--config", "config/docker_config.yaml"]
```

### 2. Create Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: marketdata
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./sql:/docker-entrypoint-initdb.d

  realtime-service:
    build: .
    depends_on:
      - redis
      - mysql
    environment:
      REDIS_HOST: redis
      REDIS_PORT: 6379
      DATABASE_URL: mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql/marketdata
    ports:
      - "8765:8765"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./dlq:/app/dlq
    restart: unless-stopped

volumes:
  redis_data:
  mysql_data:
```

### 3. Deploy with Docker

```bash
# Create .env file
cat > .env << EOF
MYSQL_ROOT_PASSWORD=root_password
MYSQL_USER=marketuser
MYSQL_PASSWORD=market_password
EOF

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f realtime-service

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Monitoring Setup

### 1. Log Rotation

Create `/etc/logrotate.d/realtime-service`:

```
/var/log/realtime_service/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 realtime realtime
    sharedscripts
    postrotate
        systemctl reload realtime-service > /dev/null 2>&1 || true
    endscript
}
```

### 2. Health Check Script

Create `/opt/realtime_service/healthcheck.sh`:

```bash
#!/bin/bash

# Check if service is running
if ! systemctl is-active --quiet realtime-service; then
    echo "Service is not running"
    exit 1
fi

# Check WebSocket port
if ! nc -z localhost 8765; then
    echo "WebSocket port not responding"
    exit 1
fi

# Check Redis connection
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Redis not accessible"
    exit 1
fi

echo "Health check passed"
exit 0
```

### 3. Monitoring with Cron

```bash
# Add to crontab
*/5 * * * * /opt/realtime_service/healthcheck.sh || /usr/bin/systemctl restart realtime-service
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u realtime-service -n 50

# Check configuration
python main.py --config config/production.yaml --validate

# Check permissions
ls -la /opt/realtime_service/app
ls -la /var/log/realtime_service
```

### High Memory Usage

```bash
# Check current usage
ps aux | grep python

# Reduce batch sizes in config
# Reduce symbol count
# Enable memory profiling
```

### WebSocket Connection Issues

```bash
# Check if port is open
netstat -tlnp | grep 8765

# Check firewall
sudo ufw status
sudo ufw allow 8765/tcp

# Test locally
wscat -c ws://localhost:8765
```

### Database Connection Errors

```bash
# Test MySQL connection
mysql -h localhost -u user -p

# Check connection string
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()"

# Check max connections
mysql -e "SHOW VARIABLES LIKE 'max_connections';"
```

### Redis Connection Issues

```bash
# Test Redis
redis-cli ping

# Check authentication
redis-cli -a password ping

# Monitor Redis
redis-cli monitor
```

## Performance Tuning

### 1. Publisher Optimization

```yaml
publishers:
  - publish_interval: 5.0  # Lower = more frequent updates
    batch_size: 100  # Higher = fewer API calls
    rate_limit: 30   # Adjust based on API limits
```

### 2. Subscriber Optimization

```yaml
subscribers:
  - id: db_writer
    batch_size: 500  # Larger batches = better throughput
```

### 3. System Tuning

```bash
# Increase file descriptors
echo "realtime soft nofile 65536" >> /etc/security/limits.conf
echo "realtime hard nofile 65536" >> /etc/security/limits.conf

# Increase TCP backlog
echo "net.core.somaxconn = 4096" >> /etc/sysctl.conf
sysctl -p
```

## Backup and Recovery

### Backup DLQ Data

```bash
# Backup DLQ directory
tar -czf dlq_backup_$(date +%Y%m%d).tar.gz /var/lib/realtime_service/dlq

# Upload to backup storage
aws s3 cp dlq_backup_*.tar.gz s3://your-bucket/backups/
```

### Backup Configuration

```bash
# Backup configs
cp -r /opt/realtime_service/app/config ~/config_backup_$(date +%Y%m%d)
```

## Security Checklist

- [ ] Change default Redis password
- [ ] Use strong MySQL passwords
- [ ] Enable firewall rules
- [ ] Use TLS for WebSocket in production
- [ ] Restrict file permissions
- [ ] Enable SELinux/AppArmor
- [ ] Regular security updates
- [ ] Log monitoring and alerting
- [ ] Backup encryption
- [ ] Access control lists

## Scaling Considerations

### Horizontal Scaling

Deploy multiple instances with Redis broker:

```yaml
# Instance 1: Publishers only
publishers:
  - id: yahoo_instance1
    symbols: ['AAPL', 'GOOGL', 'MSFT']

subscribers: []

# Instance 2: Subscribers only
publishers: []

subscribers:
  - id: db_writer
  - id: websocket
```

### Load Balancing

```nginx
upstream websocket_backend {
    least_conn;
    server 10.0.0.1:8765;
    server 10.0.0.2:8765;
    server 10.0.0.3:8765;
}

server {
    listen 80;
    location / {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
