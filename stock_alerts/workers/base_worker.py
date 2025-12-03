"""Base worker class for async background workers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from ..infrastructure.config import Config, get_config
from ..events.event_bus import EventBus, get_event_bus
from ..events.events import SystemEvent

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Base class for async workers.
    
    Provides common functionality:
    - Start/stop lifecycle
    - Error handling with retry
    - Health monitoring
    - Event bus integration
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[Config] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.name = name
        self.config = config or get_config()
        self.event_bus = event_bus or get_event_bus()
        
        # State
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._error_count = 0
        self._iterations = 0
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 5.0
        self.backoff_multiplier = 2.0
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def uptime_seconds(self) -> float:
        if self._started_at:
            return (datetime.now() - self._started_at).total_seconds()
        return 0
    
    @property
    def health_status(self) -> dict:
        """Get worker health status."""
        return {
            'name': self.name,
            'running': self._running,
            'uptime_seconds': self.uptime_seconds,
            'iterations': self._iterations,
            'error_count': self._error_count,
            'last_error': self._last_error,
        }
    
    async def start(self):
        """Start the worker."""
        if self._running:
            logger.warning(f"{self.name} already running")
            return
        
        self._running = True
        self._started_at = datetime.now()
        self._error_count = 0
        
        # Publish started event
        await self.event_bus.publish_async(
            SystemEvent.worker_started(self.name, self.health_status)
        )
        
        logger.info(f"{self.name} starting...")
        
        # Run initialization
        try:
            await self.on_start()
        except Exception as e:
            logger.error(f"{self.name} initialization failed: {e}")
            self._running = False
            raise
        
        # Start main loop as task
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"{self.name} started")
    
    async def stop(self, reason: str = ""):
        """Stop the worker."""
        if not self._running:
            return
        
        self._running = False
        logger.info(f"{self.name} stopping: {reason}")
        
        # Cancel main task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Run cleanup
        try:
            await self.on_stop()
        except Exception as e:
            logger.error(f"{self.name} cleanup error: {e}")
        
        # Publish stopped event
        await self.event_bus.publish_async(
            SystemEvent.worker_stopped(self.name, reason)
        )
        
        logger.info(f"{self.name} stopped")
    
    async def _run_loop(self):
        """Main worker loop with error handling and retry."""
        retry_count = 0
        delay = self.retry_delay
        
        while self._running:
            try:
                await self.run()
                self._iterations += 1
                retry_count = 0  # Reset on success
                delay = self.retry_delay
                
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                self._error_count += 1
                self._last_error = str(e)
                logger.error(f"{self.name} error: {e}")
                
                # Publish error event
                await self.event_bus.publish_async(
                    SystemEvent.worker_error(self.name, str(e), {
                        'retry_count': retry_count,
                        'error_count': self._error_count,
                    })
                )
                
                retry_count += 1
                if retry_count >= self.max_retries:
                    logger.error(f"{self.name} max retries exceeded, stopping")
                    self._running = False
                    break
                
                # Exponential backoff
                logger.info(f"{self.name} retrying in {delay:.1f}s (attempt {retry_count})")
                await asyncio.sleep(delay)
                delay *= self.backoff_multiplier
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def run(self):
        """
        Main worker logic.
        
        This is called repeatedly in a loop.
        Implement your worker's main functionality here.
        Should handle its own sleep/polling interval.
        """
        pass
    
    async def on_start(self):
        """Called once when worker starts. Override for initialization."""
        pass
    
    async def on_stop(self):
        """Called once when worker stops. Override for cleanup."""
        pass
