"""
Main entry point for Stock Alert System.

Usage:
    python -m stock_alerts.main [command]
    
Commands:
    api         - Run the REST API server
    worker      - Run background workers
    all         - Run API and workers (default)
    init-db     - Initialize database schema
    demo        - Run demo mode (no Redis required)
"""

import asyncio
import logging
import argparse
import signal
import sys
from typing import List

from .infrastructure.config import get_config
from .infrastructure.database import init_database
from .infrastructure.redis_client import get_redis
from .events.event_bus import get_event_bus
from .workers import PriceMonitorWorker, AlertEvaluatorWorker, NotificationDispatcherWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertSystem:
    """Main application coordinator."""
    
    def __init__(self):
        self.config = get_config()
        self.workers: List = []
        self._running = False
    
    async def start_workers(self):
        """Start all background workers."""
        logger.info("Starting background workers...")
        
        # Create workers
        price_monitor = PriceMonitorWorker()
        alert_evaluator = AlertEvaluatorWorker()
        notification_dispatcher = NotificationDispatcherWorker()
        
        self.workers = [price_monitor, alert_evaluator, notification_dispatcher]
        
        # Start event bus listener
        event_bus = get_event_bus()
        await event_bus.start_listening()
        
        # Start all workers
        for worker in self.workers:
            await worker.start()
        
        self._running = True
        logger.info(f"Started {len(self.workers)} workers")
    
    async def stop_workers(self):
        """Stop all background workers."""
        logger.info("Stopping workers...")
        
        for worker in self.workers:
            await worker.stop("shutdown")
        
        # Stop event bus
        event_bus = get_event_bus()
        await event_bus.stop_listening()
        
        self._running = False
        logger.info("All workers stopped")
    
    def run_api(self):
        """Run the FastAPI server."""
        import uvicorn
        from .api.app import app
        
        logger.info(f"Starting API server on {self.config.api_host}:{self.config.api_port}")
        
        uvicorn.run(
            app,
            host=self.config.api_host,
            port=self.config.api_port,
            log_level="info",
        )
    
    async def run_all(self):
        """Run API and workers together."""
        import uvicorn
        from .api.app import app
        
        # Start workers
        await self.start_workers()
        
        # Create uvicorn server
        config = uvicorn.Config(
            app,
            host=self.config.api_host,
            port=self.config.api_port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        
        # Handle shutdown
        loop = asyncio.get_event_loop()
        
        def handle_shutdown():
            logger.info("Shutdown signal received")
            asyncio.create_task(self.stop_workers())
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, handle_shutdown)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass
        
        try:
            await server.serve()
        finally:
            await self.stop_workers()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Stock Alert System")
    parser.add_argument(
        'command',
        nargs='?',
        default='all',
        choices=['api', 'worker', 'all', 'init-db', 'demo'],
        help='Command to run (default: all)'
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    system = AlertSystem()
    
    if args.command == 'init-db':
        logger.info("Initializing database...")
        try:
            init_database()
            logger.info("Database initialized successfully!")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            sys.exit(1)
    
    elif args.command == 'api':
        system.run_api()
    
    elif args.command == 'worker':
        asyncio.run(run_workers_only(system))
    
    elif args.command == 'demo':
        asyncio.run(run_demo())
    
    else:  # 'all'
        asyncio.run(system.run_all())


async def run_workers_only(system: AlertSystem):
    """Run workers without API."""
    await system.start_workers()
    
    # Wait forever
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await system.stop_workers()


async def run_demo():
    """Run a demo without Redis (local events only)."""
    logger.info("Running in DEMO mode (no Redis required)")
    
    from .core.enums import AssetType, AlertType, AlertCondition, NotificationChannel
    from .services.alert_service import AlertService
    
    # Initialize database
    try:
        init_database()
    except Exception as e:
        logger.warning(f"Database init: {e}")
    
    # Create a demo alert
    service = AlertService()
    
    alert = service.create_alert(
        user_id=1,
        symbol="RELIANCE",
        asset_type=AssetType.NSE_EQUITY,
        alert_type=AlertType.PRICE,
        condition=AlertCondition.PRICE_ABOVE,
        target_value=2500.0,
        notification_channels=[NotificationChannel.DESKTOP],
        notes="Demo alert",
    )
    
    logger.info(f"Created demo alert: {alert.id}")
    logger.info(f"  Symbol: {alert.symbol} ({alert.yahoo_symbol})")
    logger.info(f"  Condition: {alert.condition.value} {alert.target_value}")
    
    # List alerts
    alerts = service.get_user_alerts(user_id=1)
    logger.info(f"Total alerts: {len(alerts)}")
    
    logger.info("\nDemo complete! To run the full system:")
    logger.info("  1. Install Redis: docker run -p 6379:6379 redis")
    logger.info("  2. Run: python -m stock_alerts.main")


if __name__ == '__main__':
    main()
