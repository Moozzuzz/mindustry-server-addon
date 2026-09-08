#!/usr/bin/env python3
"""
Integration module for WebSocket monitoring and event streaming
Provides high-level API for server manager to use
"""

import asyncio
import logging
from typing import Optional, Callable, Any, Dict

from monitor import MindustryLogMonitor, ServerEvent, EventType
from events import WebSocketManager, EventBroadcaster, HealthMonitor, RateLimiter

logger = logging.getLogger(__name__)

# ============================================================================
# Integration Service
# ============================================================================

class MindustryIntegrationService:
    """High-level service integrating all monitoring and event systems"""

    def __init__(self):
        self.log_monitor = MindustryLogMonitor()
        self.websocket_manager = WebSocketManager()
        self.event_broadcaster = EventBroadcaster(self.websocket_manager)
        self.health_monitor = HealthMonitor(self.event_broadcaster)
        self.rate_limiter = RateLimiter()
        self.running = False

    async def initialize(self, server_manager: Any) -> None:
        """Initialize all services"""
        logger.info("Initializing integration service...")

        # Set up log monitor callback
        await self.log_monitor.start(server_manager.process.stdout if server_manager.process else None)

        # Subscribe log monitor events to broadcaster
        self._setup_event_handlers()

        # Start health monitor
        await self.health_monitor.start(server_manager)

        self.running = True
        logger.info("Integration service initialized")

    async def shutdown(self) -> None:
        """Shutdown all services"""
        logger.info("Shutting down integration service...")
        self.running = False

        await self.log_monitor.stop()
        await self.health_monitor.stop()

        logger.info("Integration service shut down")

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for log monitor"""
        # Set log monitor callback to broadcast events
        async def on_event(event: ServerEvent) -> None:
            await self.event_broadcaster.publish(
                event.type.value,
                event.data
            )

        self.log_monitor.callback = on_event

    async def broadcast_custom_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Broadcast a custom event"""
        await self.event_broadcaster.publish(event_type, data)

    def get_websocket_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return self.websocket_manager.get_stats()

    def get_monitor_state(self) -> Dict[str, Any]:
        """Get log monitor state"""
        return self.log_monitor.get_state()

    def get_health_alerts(self, limit: int = 20) -> list:
        """Get recent health alerts"""
        return self.health_monitor.get_alerts(limit)
