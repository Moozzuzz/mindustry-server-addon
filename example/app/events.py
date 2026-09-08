#!/usr/bin/env python3
"""
Mindustry Server Event Manager
Manages real-time event broadcasting to WebSocket clients
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Set
from collections import deque

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# ============================================================================
# WebSocket Event Manager
# ============================================================================

class WebSocketManager:
    """Manages WebSocket connections and event broadcasting"""

    def __init__(self, max_history: int = 100):
        self.active_connections: Set[WebSocket] = set()
        self.event_history: deque = deque(maxlen=max_history)
        self.client_id_counter = 0
        self.connection_map: Dict[WebSocket, str] = {}  # websocket -> client_id

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        client_id = f"client_{self.client_id_counter}"
        self.client_id_counter += 1
        self.connection_map[websocket] = client_id

        logger.info(f"WebSocket {client_id} connected. Total: {len(self.active_connections)}")

        # Send connection welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to Mindustry Server API"
        })

        # Send recent event history
        await self._send_history(websocket)

        return client_id

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            client_id = self.connection_map.pop(websocket, "unknown")
            logger.info(f"WebSocket {client_id} disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, event: Dict[str, Any]) -> None:
        """Broadcast an event to all connected clients"""
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat()

        self.event_history.append(event)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(event)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {str(e)}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_to_client(self, websocket: WebSocket, event: Dict[str, Any]) -> None:
        """Send event to a specific client"""
        try:
            if "timestamp" not in event:
                event["timestamp"] = datetime.utcnow().isoformat()
            await websocket.send_json(event)
        except Exception as e:
            logger.error(f"Error sending to specific client: {str(e)}")
            self.disconnect(websocket)

    async def _send_history(self, websocket: WebSocket) -> None:
        """Send event history to a newly connected client"""
        for event in self.event_history:
            try:
                await websocket.send_json({
                    "type": "history",
                    "data": event
                })
            except Exception as e:
                logger.error(f"Error sending history: {str(e)}")
                break

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return {
            "active_connections": len(self.active_connections),
            "event_history_size": len(self.event_history),
            "clients": list(self.connection_map.values())
        }

    def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent event history"""
        return list(self.event_history)[-limit:]

# ============================================================================
# Event Broadcaster Service
# ============================================================================

class EventBroadcaster:
    """High-level service for managing events and broadcasting"""

    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.subscribers: Dict[str, List[Callable]] = {}  # event_type -> [callbacks]

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to a specific event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Broadcast to WebSocket clients
        await self.ws_manager.broadcast(event)

        # Call local subscribers
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error calling subscriber callback: {str(e)}")

    async def publish_server_event(self, event_type: str, **kwargs) -> None:
        """Publish a server-related event with standard format"""
        await self.publish(event_type, {
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })

# ============================================================================
# Health Monitor Service
# ============================================================================

class HealthMonitor:
    """Monitors server health and reports issues"""

    def __init__(
        self,
        event_broadcaster: EventBroadcaster,
        check_interval: float = 30.0
    ):
        self.broadcaster = event_broadcaster
        self.check_interval = check_interval
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.last_check: Optional[float] = None
        self.health_status = "healthy"
        self.alerts: deque = deque(maxlen=50)

    async def start(self, server_manager) -> None:
        """Start health monitoring"""
        self.running = True
        self.monitor_task = asyncio.create_task(self._health_check_loop(server_manager))
        logger.info("Health monitor started")

    async def stop(self) -> None:
        """Stop health monitoring"""
        self.running = False
        if self.monitor_task:
            try:
                await asyncio.wait_for(self.monitor_task, timeout=5)
            except asyncio.TimeoutError:
                self.monitor_task.cancel()
        logger.info("Health monitor stopped")

    async def _health_check_loop(self, server_manager) -> None:
        """Main health check loop"""
        try:
            while self.running:
                try:
                    await self._perform_health_check(server_manager)
                    await asyncio.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Health check error: {str(e)}")
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("Health monitor cancelled")

    async def _perform_health_check(self, server_manager) -> None:
        """Perform a health check on the server"""
        status = server_manager.get_status()

        # Check if server is running
        if status.status != "running":
            if self.health_status == "healthy":
                self.health_status = "unhealthy"
                alert = {
                    "level": "critical",
                    "message": f"Server is {status.status}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.alerts.append(alert)
                await self.broadcaster.publish("health_alert", alert)
        else:
            if self.health_status != "healthy":
                self.health_status = "healthy"
                alert = {
                    "level": "info",
                    "message": "Server recovered",
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.alerts.append(alert)
                await self.broadcaster.publish("health_alert", alert)

        # Publish periodic health status
        await self.broadcaster.publish("health_status", {
            "status": self.health_status,
            "server_status": status.status,
            "uptime_seconds": status.uptime_seconds,
            "players_online": status.players_online
        })

    def get_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent health alerts"""
        return list(self.alerts)[-limit:]

# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """Rate limiter for API endpoints"""

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.request_history: Dict[str, deque] = {}  # client_id -> deque of timestamps

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make a request"""
        now = datetime.utcnow().timestamp()
        minute_ago = now - 60

        if client_id not in self.request_history:
            self.request_history[client_id] = deque()

        # Remove old requests
        while (
            self.request_history[client_id] and
            self.request_history[client_id][0] < minute_ago
        ):
            self.request_history[client_id].popleft()

        # Check rate limit
        if len(self.request_history[client_id]) >= self.requests_per_minute:
            return False

        self.request_history[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client"""
        if client_id not in self.request_history:
            return self.requests_per_minute
        return self.requests_per_minute - len(self.request_history[client_id])
