"""
Service Manager
===============
Manages lifecycle of market data services (start/stop/monitor).
"""
import os
import sys
import subprocess
import threading
import time
import signal
import logging
from datetime import datetime, time as dt_time
from typing import Dict, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field
import psutil
import redis

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class ServiceInfo:
    """Information about a service."""
    name: str
    command: List[str]
    description: str
    process: Optional[subprocess.Popen] = None
    status: ServiceStatus = ServiceStatus.STOPPED
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    last_error: Optional[str] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    output_lines: List[str] = field(default_factory=list)


class ServiceManager:
    """
    Manages market data services lifecycle.
    
    Services:
    - Feed Publisher: Connects to Dhan WebSocket, publishes to Redis
    - DB Writer: Subscribes to Redis, writes to MySQL
    - Quote Visualizer: Subscribes to Redis, displays in terminal
    """
    
    # Market hours (IST)
    MARKET_OPEN = dt_time(9, 0)    # 9:00 AM
    MARKET_CLOSE = dt_time(15, 35)  # 3:35 PM
    
    MAX_OUTPUT_LINES = 500  # Keep last N lines of output per service
    
    def __init__(self):
        """Initialize service manager."""
        self.services: Dict[str, ServiceInfo] = {}
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._status_callback: Optional[Callable] = None
        self._output_callback: Optional[Callable] = None
        self._redis: Optional[redis.Redis] = None
        
        # Get project root
        self._project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Python executable
        self._python = sys.executable
        
        # Register services
        self._register_services()
    
    def _register_services(self):
        """Register all available services."""
        # Feed Publisher (Core service)
        self.services['feed_publisher'] = ServiceInfo(
            name="Feed Publisher",
            command=[self._python, "-m", "dhan_trading.market_feed.launcher", 
                    "--mode", "quote", "--force"],
            description="Connects to Dhan WebSocket and publishes market data to Redis"
        )
        
        # DB Writer Subscriber
        self.services['db_writer'] = ServiceInfo(
            name="DB Writer",
            command=[self._python, "-m", "dhan_trading.subscribers.db_writer"],
            description="Subscribes to Redis and writes quotes to MySQL database"
        )
        
        # Quote Visualizer (optional, for monitoring)
        # Note: This is a terminal app, might not be needed in dashboard
        # self.services['visualizer'] = ServiceInfo(
        #     name="Quote Visualizer",
        #     command=[self._python, "-m", "dhan_trading.visualizers.quote_visualizer"],
        #     description="Real-time quote display in terminal"
        # )
    
    def set_status_callback(self, callback: Callable[[str, ServiceStatus], None]):
        """Set callback for status updates."""
        self._status_callback = callback
    
    def set_output_callback(self, callback: Callable[[str, str], None]):
        """Set callback for output updates."""
        self._output_callback = callback
    
    def _notify_status(self, service_id: str, status: ServiceStatus):
        """Notify status change."""
        if self._status_callback:
            self._status_callback(service_id, status)
    
    def _notify_output(self, service_id: str, line: str):
        """Notify new output line."""
        if self._output_callback:
            self._output_callback(service_id, line)
    
    def start_service(self, service_id: str) -> bool:
        """
        Start a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if started successfully
        """
        if service_id not in self.services:
            logger.error(f"Unknown service: {service_id}")
            return False
        
        service = self.services[service_id]
        
        if service.status == ServiceStatus.RUNNING:
            logger.warning(f"Service {service.name} is already running")
            return True
        
        try:
            service.status = ServiceStatus.STARTING
            self._notify_status(service_id, ServiceStatus.STARTING)
            
            # Start process with output capture
            service.process = subprocess.Popen(
                service.command,
                cwd=self._project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            service.pid = service.process.pid
            service.start_time = datetime.now()
            service.status = ServiceStatus.RUNNING
            service.last_error = None
            service.output_lines = []
            
            self._notify_status(service_id, ServiceStatus.RUNNING)
            
            # Start output reader thread
            reader_thread = threading.Thread(
                target=self._read_output,
                args=(service_id,),
                daemon=True
            )
            reader_thread.start()
            
            logger.info(f"Started service {service.name} (PID: {service.pid})")
            return True
            
        except Exception as e:
            service.status = ServiceStatus.ERROR
            service.last_error = str(e)
            self._notify_status(service_id, ServiceStatus.ERROR)
            logger.error(f"Failed to start service {service.name}: {e}")
            return False
    
    def stop_service(self, service_id: str) -> bool:
        """
        Stop a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if stopped successfully
        """
        if service_id not in self.services:
            logger.error(f"Unknown service: {service_id}")
            return False
        
        service = self.services[service_id]
        
        if service.status not in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
            logger.warning(f"Service {service.name} is not running")
            return True
        
        try:
            service.status = ServiceStatus.STOPPING
            self._notify_status(service_id, ServiceStatus.STOPPING)
            
            if service.process:
                # Try graceful shutdown first
                if os.name == 'nt':
                    # Windows: send CTRL+BREAK to process group
                    try:
                        service.process.send_signal(signal.CTRL_BREAK_EVENT)
                    except:
                        pass
                else:
                    # Unix: send SIGTERM
                    service.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    service.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill
                    service.process.kill()
                    service.process.wait(timeout=2)
            
            service.status = ServiceStatus.STOPPED
            service.process = None
            service.pid = None
            self._notify_status(service_id, ServiceStatus.STOPPED)
            
            logger.info(f"Stopped service {service.name}")
            return True
            
        except Exception as e:
            service.status = ServiceStatus.ERROR
            service.last_error = str(e)
            self._notify_status(service_id, ServiceStatus.ERROR)
            logger.error(f"Failed to stop service {service.name}: {e}")
            return False
    
    def _read_output(self, service_id: str):
        """Read output from service process."""
        service = self.services[service_id]
        
        try:
            while service.process and service.process.poll() is None:
                line = service.process.stdout.readline()
                if line:
                    line = line.strip()
                    service.output_lines.append(line)
                    
                    # Trim output buffer
                    if len(service.output_lines) > self.MAX_OUTPUT_LINES:
                        service.output_lines = service.output_lines[-self.MAX_OUTPUT_LINES:]
                    
                    self._notify_output(service_id, line)
            
            # Read any remaining output
            if service.process:
                remaining = service.process.stdout.read()
                if remaining:
                    for line in remaining.strip().split('\n'):
                        service.output_lines.append(line)
                        self._notify_output(service_id, line)
                
                # Check exit code
                exit_code = service.process.returncode
                if exit_code != 0 and service.status == ServiceStatus.RUNNING:
                    service.status = ServiceStatus.ERROR
                    service.last_error = f"Process exited with code {exit_code}"
                    self._notify_status(service_id, ServiceStatus.ERROR)
                elif service.status == ServiceStatus.RUNNING:
                    service.status = ServiceStatus.STOPPED
                    self._notify_status(service_id, ServiceStatus.STOPPED)
                    
        except Exception as e:
            logger.error(f"Error reading output from {service_id}: {e}")
    
    def start_all(self) -> Dict[str, bool]:
        """Start all registered services."""
        results = {}
        for service_id in self.services:
            results[service_id] = self.start_service(service_id)
        return results
    
    def stop_all(self) -> Dict[str, bool]:
        """Stop all running services."""
        results = {}
        for service_id in self.services:
            results[service_id] = self.stop_service(service_id)
        return results
    
    def get_service_status(self, service_id: str) -> Optional[ServiceStatus]:
        """Get current status of a service."""
        if service_id in self.services:
            return self.services[service_id].status
        return None
    
    def get_service_info(self, service_id: str) -> Optional[ServiceInfo]:
        """Get full service info."""
        return self.services.get(service_id)
    
    def update_resource_usage(self):
        """Update CPU and memory usage for all running services."""
        for service_id, service in self.services.items():
            if service.status == ServiceStatus.RUNNING and service.pid:
                try:
                    proc = psutil.Process(service.pid)
                    service.cpu_percent = proc.cpu_percent(interval=0.1)
                    service.memory_mb = proc.memory_info().rss / (1024 * 1024)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    
    def check_process_health(self):
        """Check if processes are still running."""
        for service_id, service in self.services.items():
            if service.status == ServiceStatus.RUNNING and service.process:
                if service.process.poll() is not None:
                    # Process has exited
                    exit_code = service.process.returncode
                    if exit_code != 0:
                        service.status = ServiceStatus.ERROR
                        service.last_error = f"Process exited unexpectedly (code {exit_code})"
                    else:
                        service.status = ServiceStatus.STOPPED
                    self._notify_status(service_id, service.status)
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        now = datetime.now()
        
        # Check if weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        current_time = now.time()
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE
    
    def get_redis_stats(self) -> Dict:
        """Get Redis connection stats."""
        try:
            if not self._redis:
                self._redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
            
            # Check connection
            self._redis.ping()
            
            # Get pub/sub stats
            pubsub_channels = self._redis.pubsub_channels()
            
            # Get stream info
            stream_info = {}
            for stream in ['dhan:quotes:stream', 'dhan:ticks:stream', 'dhan:depth:stream']:
                try:
                    info = self._redis.xinfo_stream(stream)
                    stream_info[stream] = {
                        'length': info['length'],
                        'first_entry': info.get('first-entry'),
                        'last_entry': info.get('last-entry')
                    }
                except redis.ResponseError:
                    stream_info[stream] = {'length': 0}
            
            return {
                'connected': True,
                'channels': list(pubsub_channels),
                'streams': stream_info
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def cleanup(self):
        """Cleanup resources."""
        self._running = False
        self.stop_all()
        if self._redis:
            self._redis.close()


# Singleton instance
_manager_instance: Optional[ServiceManager] = None


def get_service_manager() -> ServiceManager:
    """Get singleton service manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ServiceManager()
    return _manager_instance
