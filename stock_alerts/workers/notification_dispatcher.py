"""Notification dispatcher worker - sends notifications when alerts trigger."""

import asyncio
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import platform

from .base_worker import BaseWorker
from ..core.enums import NotificationChannel, EventType
from ..events.events import Event, AlertTriggeredEvent
from ..infrastructure.config import Config, get_config

logger = logging.getLogger(__name__)


class NotificationDispatcherWorker(BaseWorker):
    """
    Dispatches notifications when alerts are triggered.
    
    Supports:
    - Desktop notifications (Windows toast)
    - Sound alerts
    - Webhook calls
    """
    
    def __init__(self, config: Optional[Config] = None, **kwargs):
        super().__init__(name="NotificationDispatcherWorker", config=config, **kwargs)
        
        # Notification queue
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        
        # Stats
        self._notifications_sent = 0
        self._notifications_failed = 0
        
        # Desktop notification support
        self._desktop_available = self._check_desktop_support()
        
        # Sound support
        self._sound_available = self._check_sound_support()
    
    def _check_desktop_support(self) -> bool:
        """Check if desktop notifications are available."""
        if platform.system() == 'Windows':
            try:
                from win10toast import ToastNotifier
                return True
            except ImportError:
                try:
                    from plyer import notification
                    return True
                except ImportError:
                    pass
        return False
    
    def _check_sound_support(self) -> bool:
        """Check if sound alerts are available."""
        if platform.system() == 'Windows':
            try:
                import winsound
                return True
            except ImportError:
                pass
        return False
    
    async def on_start(self):
        """Subscribe to alert triggered events."""
        self.event_bus.subscribe(EventType.ALERT_TRIGGERED, self._on_alert_triggered)
        logger.info(
            f"Notification dispatcher started "
            f"(desktop: {self._desktop_available}, sound: {self._sound_available})"
        )
    
    async def _on_alert_triggered(self, event: Event):
        """Handle alert triggered event."""
        await self._notification_queue.put(event)
    
    async def run(self):
        """Process notifications from queue."""
        try:
            # Get notification from queue with timeout
            event = await asyncio.wait_for(
                self._notification_queue.get(),
                timeout=1.0
            )
            
            await self._dispatch_notification(event)
            
        except asyncio.TimeoutError:
            pass
    
    async def _dispatch_notification(self, event: Event):
        """Dispatch notification through configured channels."""
        payload = event.payload
        channels = payload.get('notification_channels', [])
        message = payload.get('message', 'Alert triggered')
        symbol = payload.get('symbol', 'Unknown')
        priority = payload.get('priority', 'normal')
        
        results = {}
        
        for channel in channels:
            try:
                if channel == 'desktop':
                    success = await self._send_desktop(symbol, message, priority)
                    results['desktop'] = 'sent' if success else 'failed'
                    
                elif channel == 'sound':
                    success = await self._play_sound(priority)
                    results['sound'] = 'sent' if success else 'failed'
                    
                elif channel == 'webhook':
                    webhook_url = payload.get('webhook_url')
                    if webhook_url:
                        success = await self._send_webhook(webhook_url, payload)
                        results['webhook'] = 'sent' if success else 'failed'
                    else:
                        results['webhook'] = 'no_url'
                
                self._notifications_sent += 1
                
            except Exception as e:
                logger.error(f"Notification error ({channel}): {e}")
                results[channel] = f'error: {e}'
                self._notifications_failed += 1
        
        logger.info(f"Notification dispatched for {symbol}: {results}")
    
    async def _send_desktop(self, title: str, message: str, priority: str) -> bool:
        """Send desktop notification."""
        if not self._desktop_available or not self.config.notification.desktop_enabled:
            return False
        
        try:
            if platform.system() == 'Windows':
                return await self._send_windows_toast(title, message, priority)
            else:
                return await self._send_plyer_notification(title, message)
                
        except Exception as e:
            logger.error(f"Desktop notification error: {e}")
            return False
    
    async def _send_windows_toast(self, title: str, message: str, priority: str) -> bool:
        """Send Windows toast notification."""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            
            # Run in executor (it's blocking)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: toaster.show_toast(
                    f"🔔 Stock Alert: {title}",
                    message,
                    duration=self.config.notification.desktop_duration // 1000,
                    threaded=True,
                )
            )
            return True
            
        except ImportError:
            # Fall back to plyer
            return await self._send_plyer_notification(title, message)
    
    async def _send_plyer_notification(self, title: str, message: str) -> bool:
        """Send notification using plyer (cross-platform)."""
        try:
            from plyer import notification
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: notification.notify(
                    title=f"🔔 Stock Alert: {title}",
                    message=message,
                    app_name="Stock Alerts",
                    timeout=self.config.notification.desktop_duration // 1000,
                )
            )
            return True
            
        except Exception as e:
            logger.error(f"Plyer notification error: {e}")
            return False
    
    async def _play_sound(self, priority: str) -> bool:
        """Play alert sound."""
        if not self._sound_available or not self.config.notification.sound_enabled:
            return False
        
        try:
            if platform.system() == 'Windows':
                import winsound
                
                # Choose sound based on priority
                if priority == 'critical':
                    sound = winsound.MB_ICONHAND
                elif priority == 'high':
                    sound = winsound.MB_ICONEXCLAMATION
                else:
                    sound = winsound.MB_ICONASTERISK
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: winsound.MessageBeep(sound)
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Sound alert error: {e}")
            return False
    
    async def _send_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send webhook notification."""
        try:
            import aiohttp
            
            webhook_payload = {
                'event': 'alert_triggered',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'alert_id': payload.get('alert_id'),
                    'symbol': payload.get('symbol'),
                    'condition': payload.get('condition'),
                    'target_value': payload.get('target_value'),
                    'actual_value': payload.get('actual_value'),
                    'message': payload.get('message'),
                    'priority': payload.get('priority'),
                }
            }
            
            timeout = aiohttp.ClientTimeout(total=self.config.notification.webhook_timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    json=webhook_payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status < 300:
                        logger.debug(f"Webhook sent to {url}: {response.status}")
                        return True
                    else:
                        logger.warning(f"Webhook failed: {response.status}")
                        return False
                        
        except ImportError:
            logger.error("aiohttp not installed - webhooks unavailable")
            return False
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False
    
    async def on_stop(self):
        """Cleanup on stop."""
        logger.info(
            f"Notification dispatcher stats: "
            f"{self._notifications_sent} sent, "
            f"{self._notifications_failed} failed"
        )
