"""
Real-Time Yahoo Finance Service - Main Entry Point
===================================================

Starts the orchestrator service with all configured publishers and subscribers.

Usage:
    python main.py [--config CONFIG_FILE]
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from orchestrator import OrchestratorService


def setup_logging(config: dict = None):
    """Setup logging configuration"""
    if config is None:
        config = {}
    
    log_config = config.get('logging', {})
    
    # Create formatter
    formatter = logging.Formatter(
        log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler (if configured)
    handlers = [console_handler]
    log_file = log_config.get('file')
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=log_config.get('max_bytes', 10485760),
            backupCount=log_config.get('backup_count', 5)
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        handlers=handlers
    )


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Real-Time Yahoo Finance Service'
    )
    parser.add_argument(
        '--config',
        default='config/service_config.yaml',
        help='Path to configuration file (default: config/service_config.yaml)'
    )
    
    args = parser.parse_args()
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    
    # Create orchestrator
    orchestrator = OrchestratorService(str(config_path))
    
    # Load config for logging setup
    config = orchestrator.load_config()
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Real-Time Yahoo Finance Service")
    logger.info("="*60)
    logger.info(f"Configuration: {config_path}")
    logger.info("")
    
    try:
        # Run orchestrator (blocks until shutdown)
        await orchestrator.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Service shutdown complete")


if __name__ == '__main__':
    # Import logging.handlers for RotatingFileHandler
    import logging.handlers
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
