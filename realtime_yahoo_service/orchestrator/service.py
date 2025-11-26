"""
Orchestrator Service - Coordinates publishers and subscribers
"""

import asyncio
import logging
import signal
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml

from redis_broker import RedisEventBroker, InMemoryBroker
from serialization import JSONSerializer, MessagePackSerializer, ProtobufSerializer
from dlq import DLQManager
from publisher import YahooFinancePublisher
from subscribers import (
    DBWriterSubscriber,
    StateTrackerSubscriber,
    MarketBreadthSubscriber,
    TrendAnalyzerSubscriber,
)
from clients import WebSocketServer


logger = logging.getLogger(__name__)


class OrchestratorService:
    """
    Orchestrator service that coordinates all publishers and subscribers.
    
    Features:
    - Load configuration from YAML file
    - Initialize broker, serializer, and DLQ
    - Create and manage publishers and subscribers
    - Health monitoring and automatic restarts
    - Graceful shutdown handling
    - Statistics collection
    """
    
    def __init__(self, config_path: str):
        """
        Initialize orchestrator service.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        # Components
        self.broker = None
        self.serializer = None
        self.dlq_manager = None
        
        # Publishers and subscribers
        self.publishers: Dict[str, Any] = {}
        self.subscribers: Dict[str, Any] = {}
        
        # Monitoring
        self._running = False
        self._health_task: Optional[asyncio.Task] = None
        self._restart_counts: Dict[str, int] = {}
        
        logger.info(f"Orchestrator initialized with config: {config_path}")
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return self.config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
    
    def _create_broker(self):
        """Create message broker based on configuration"""
        broker_config = self.config.get('broker', {})
        broker_type = broker_config.get('type', 'inmemory')
        
        if not self.serializer:
            raise RuntimeError("Serializer must be created before broker")
        
        if broker_type == 'redis':
            redis_config = broker_config.get('redis', {})
            self.broker = RedisEventBroker(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                password=redis_config.get('password'),
                pool_size=redis_config.get('pool_size', 10),
            )
            logger.info("Created Redis broker")
        else:
            self.broker = InMemoryBroker(serializer=self.serializer)
            logger.info("Created in-memory broker")
        
        return self.broker
    
    def _create_serializer(self):
        """Create serializer based on configuration"""
        serializer_config = self.config.get('serializer', {})
        serializer_type = serializer_config.get('type', 'json')
        
        if serializer_type == 'msgpack':
            self.serializer = MessagePackSerializer()
            logger.info("Created MessagePack serializer")
        elif serializer_type == 'protobuf':
            self.serializer = ProtobufSerializer()
            logger.info("Created Protobuf serializer")
        else:
            self.serializer = JSONSerializer()
            logger.info("Created JSON serializer")
        
        return self.serializer
    
    def _create_dlq(self):
        """Create Dead Letter Queue based on configuration"""
        dlq_config = self.config.get('dlq', {})
        
        if not dlq_config.get('enabled', True):
            logger.info("DLQ disabled")
            return None
        
        self.dlq_manager = DLQManager(
            storage_path=dlq_config.get('file_path', './dlq'),
            max_retries=dlq_config.get('max_retries', 3),
            retention_days=dlq_config.get('retention_days', 7),
            enable_auto_retry=dlq_config.get('enable_auto_retry', True),
            auto_retry_interval=dlq_config.get('auto_retry_interval', 300.0),
        )
        logger.info(f"Created DLQ at {dlq_config.get('file_path', './dlq')}")
        
        return self.dlq_manager
        
        return self.dlq_manager
    
    def _create_publishers(self):
        """Create publishers based on configuration"""
        publishers_config = self.config.get('publishers', [])
        
        for pub_config in publishers_config:
            if not pub_config.get('enabled', True):
                logger.info(f"Publisher {pub_config['id']} is disabled")
                continue
            
            pub_id = pub_config['id']
            pub_type = pub_config['type']
            
            if pub_type == 'yahoo_finance':
                publisher = YahooFinancePublisher(
                    publisher_id=pub_id,
                    broker=self.broker,
                    serializer=self.serializer,
                    symbols=pub_config.get('symbols', []),
                    batch_size=pub_config.get('batch_size', 50),
                    rate_limit=pub_config.get('rate_limit', 20),
                    rate_limit_period=pub_config.get('rate_limit_period', 60.0),
                    publish_interval=pub_config.get('publish_interval', 5.0),
                    data_interval=pub_config.get('data_interval', '1m'),
                    period=pub_config.get('period', '1d'),
                )
                
                self.publishers[pub_id] = publisher
                logger.info(f"Created Yahoo Finance publisher: {pub_id}")
            else:
                logger.warning(f"Unknown publisher type: {pub_type}")
        
        return self.publishers
    
    def _create_subscribers(self):
        """Create subscribers based on configuration"""
        subscribers_config = self.config.get('subscribers', [])
        
        for sub_config in subscribers_config:
            if not sub_config.get('enabled', True):
                logger.info(f"Subscriber {sub_config['id']} is disabled")
                continue
            
            sub_id = sub_config['id']
            sub_type = sub_config['type']
            channels = sub_config.get('channels', [])
            
            try:
                if sub_type == 'db_writer':
                    subscriber = DBWriterSubscriber(
                        subscriber_id=sub_id,
                        broker=self.broker,
                        serializer=self.serializer,
                        channels=channels,
                        db_url=sub_config.get('db_url'),
                        table_name=sub_config.get('table_name', 'nse_equity_bhavcopy_full'),
                        batch_size=sub_config.get('batch_size', 100),
                        dlq_manager=self.dlq_manager,
                    )
                
                elif sub_type == 'state_tracker':
                    subscriber = StateTrackerSubscriber(
                        subscriber_id=sub_id,
                        broker=self.broker,
                        serializer=self.serializer,
                    )
                
                elif sub_type == 'market_breadth':
                    subscriber = MarketBreadthSubscriber(
                        subscriber_id=sub_id,
                        broker=self.broker,
                        serializer=self.serializer,
                        channels=channels,
                        index_name=sub_config.get('index_name', 'NIFTY50'),
                        publish_interval=sub_config.get('publish_interval', 60),
                        dlq_manager=self.dlq_manager,
                    )
                
                elif sub_type == 'trend_analyzer':
                    subscriber = TrendAnalyzerSubscriber(
                        subscriber_id=sub_id,
                        broker=self.broker,
                        serializer=self.serializer,
                        channels=channels,
                        window_size=sub_config.get('window_size', 50),
                        sma_periods=sub_config.get('sma_periods', [20, 50]),
                        publish_interval=sub_config.get('publish_interval', 300),
                        dlq_manager=self.dlq_manager,
                    )
                
                elif sub_type == 'websocket':
                    subscriber = WebSocketServer(
                        subscriber_id=sub_id,
                        broker=self.broker,
                        serializer=self.serializer,
                        channels=channels,
                        host=sub_config.get('host', '0.0.0.0'),
                        port=sub_config.get('port', 8765),
                        heartbeat_interval=sub_config.get('heartbeat_interval', 30),
                        auth_token=sub_config.get('auth_token'),
                        dlq_manager=self.dlq_manager,
                    )
                
                else:
                    logger.warning(f"Unknown subscriber type: {sub_type}")
                    continue
                
                self.subscribers[sub_id] = subscriber
                logger.info(f"Created subscriber: {sub_id} ({sub_type})")
                
            except Exception as e:
                logger.error(f"Error creating subscriber {sub_id}: {e}")
        
        return self.subscribers
    
    async def start(self):
        """Start all components"""
        if self._running:
            logger.warning("Orchestrator already running")
            return
        
        logger.info("Starting orchestrator service...")
        self._running = True
        
        try:
            # Load configuration
            self.load_config()
            
            # Create components in correct order: serializer first, then broker
            self._create_serializer()
            self._create_broker()
            self._create_dlq()
            
            # Initialize broker
            await self.broker.connect()
            
            # Create publishers and subscribers
            self._create_publishers()
            self._create_subscribers()
            
            # Start publishers
            for pub_id, publisher in self.publishers.items():
                try:
                    await publisher.start()
                    logger.info(f"Started publisher: {pub_id}")
                except Exception as e:
                    logger.error(f"Error starting publisher {pub_id}: {e}")
            
            # Start subscribers
            for sub_id, subscriber in self.subscribers.items():
                try:
                    await subscriber.start()
                    logger.info(f"Started subscriber: {sub_id}")
                except Exception as e:
                    logger.error(f"Error starting subscriber {sub_id}: {e}")
            
            # Start health monitoring
            health_config = self.config.get('health', {})
            if health_config.get('check_interval', 30) > 0:
                self._health_task = asyncio.create_task(self._health_monitor())
            
            logger.info("Orchestrator service started successfully")
            logger.info(f"Publishers: {len(self.publishers)}, Subscribers: {len(self.subscribers)}")
            
        except Exception as e:
            logger.error(f"Error starting orchestrator: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all components"""
        if not self._running:
            return
        
        logger.info("Stopping orchestrator service...")
        self._running = False
        
        # Stop health monitoring
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        # Stop publishers
        for pub_id, publisher in self.publishers.items():
            try:
                await publisher.stop()
                logger.info(f"Stopped publisher: {pub_id}")
            except Exception as e:
                logger.error(f"Error stopping publisher {pub_id}: {e}")
        
        # Stop subscribers
        for sub_id, subscriber in self.subscribers.items():
            try:
                await subscriber.stop()
                logger.info(f"Stopped subscriber: {sub_id}")
            except Exception as e:
                logger.error(f"Error stopping subscriber {sub_id}: {e}")
        
        # Disconnect broker
        if self.broker:
            await self.broker.disconnect()
        
        logger.info("Orchestrator service stopped")
    
    async def _health_monitor(self):
        """Monitor health of publishers and subscribers"""
        health_config = self.config.get('health', {})
        check_interval = health_config.get('check_interval', 30)
        restart_on_failure = health_config.get('restart_on_failure', True)
        max_restart_attempts = health_config.get('max_restart_attempts', 3)
        restart_delay = health_config.get('restart_delay', 10)
        
        logger.info(f"Health monitor started (interval: {check_interval}s)")
        
        while self._running:
            try:
                await asyncio.sleep(check_interval)
                
                # Check publishers
                for pub_id, publisher in self.publishers.items():
                    if not publisher._running:
                        logger.warning(f"Publisher {pub_id} is not running")
                        
                        if restart_on_failure:
                            restart_count = self._restart_counts.get(pub_id, 0)
                            
                            if restart_count < max_restart_attempts:
                                logger.info(f"Attempting to restart publisher {pub_id} (attempt {restart_count + 1})")
                                
                                try:
                                    await asyncio.sleep(restart_delay)
                                    await publisher.start()
                                    self._restart_counts[pub_id] = restart_count + 1
                                    logger.info(f"Successfully restarted publisher {pub_id}")
                                except Exception as e:
                                    logger.error(f"Failed to restart publisher {pub_id}: {e}")
                            else:
                                logger.error(f"Max restart attempts reached for publisher {pub_id}")
                
                # Check subscribers
                for sub_id, subscriber in self.subscribers.items():
                    if not subscriber._running:
                        logger.warning(f"Subscriber {sub_id} is not running")
                        
                        if restart_on_failure:
                            restart_count = self._restart_counts.get(sub_id, 0)
                            
                            if restart_count < max_restart_attempts:
                                logger.info(f"Attempting to restart subscriber {sub_id} (attempt {restart_count + 1})")
                                
                                try:
                                    await asyncio.sleep(restart_delay)
                                    await subscriber.start()
                                    self._restart_counts[sub_id] = restart_count + 1
                                    logger.info(f"Successfully restarted subscriber {sub_id}")
                                except Exception as e:
                                    logger.error(f"Failed to restart subscriber {sub_id}: {e}")
                            else:
                                logger.error(f"Max restart attempts reached for subscriber {sub_id}")
                
                # Log health status
                healthy_pubs = sum(1 for p in self.publishers.values() if p._running)
                healthy_subs = sum(1 for s in self.subscribers.values() if s._running)
                logger.debug(
                    f"Health check: Publishers {healthy_pubs}/{len(self.publishers)}, "
                    f"Subscribers {healthy_subs}/{len(self.subscribers)}"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all components"""
        stats = {
            'orchestrator': {
                'running': self._running,
                'publishers_count': len(self.publishers),
                'subscribers_count': len(self.subscribers),
            },
            'publishers': {},
            'subscribers': {},
        }
        
        # Collect publisher stats
        for pub_id, publisher in self.publishers.items():
            try:
                stats['publishers'][pub_id] = publisher.get_stats()
            except Exception as e:
                logger.error(f"Error getting stats from publisher {pub_id}: {e}")
                stats['publishers'][pub_id] = {'error': str(e)}
        
        # Collect subscriber stats
        for sub_id, subscriber in self.subscribers.items():
            try:
                stats['subscribers'][sub_id] = subscriber.get_stats()
            except Exception as e:
                logger.error(f"Error getting stats from subscriber {sub_id}: {e}")
                stats['subscribers'][sub_id] = {'error': str(e)}
        
        return stats
    
    async def run(self):
        """Run the orchestrator service (blocks until shutdown)"""
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.stop())
            )
        
        try:
            await self.start()
            
            # Wait for shutdown
            while self._running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.stop()
