#!/usr/bin/env python3
"""
Mindustry Server API
RESTful API with WebSocket support for Home Assistant integration
"""

import asyncio
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from uvicorn import Server, Config
import asyncio

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Models
# ============================================================================

class PlayerInfo(BaseModel):
    """Player information"""
    id: int
    name: str
    admin: bool = False
    team: int = 0
    color: str = "ffffff"
    mobile: bool = False
    muted: bool = False
    time_since_join: int = 0

class ServerStatus(BaseModel):
    """Server status response"""
    status: str  # running, stopped, crashed
    uptime_seconds: int = 0
    version: str = "146"
    players_online: int = 0
    max_players: int = 10
    map_name: str = "Unknown"
    map_width: int = 0
    map_height: int = 0
    wave: int = 0
    difficulty: str = "normal"
    gamemode: str = "survival"
    is_pvp: bool = False
    state: str = "waiting"  # waiting, playing, paused
    port: int = 6567
    host: str = "0.0.0.0"
    last_update: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ControlRequest(BaseModel):
    """Server control request"""
    action: str  # restart, stop, pause, resume

class CommandRequest(BaseModel):
    """Console command request"""
    command: str

class MapChangeRequest(BaseModel):
    """Map change request"""
    map: str
    difficulty: Optional[str] = None
    gamemode: Optional[str] = None

class ConfigUpdateRequest(BaseModel):
    """Configuration update request"""
    server_name: Optional[str] = None
    max_players: Optional[int] = None
    pvp: Optional[bool] = None
    strict: Optional[bool] = None
    auto_restart: Optional[bool] = None

class APIResponse(BaseModel):
    """Standard API response"""
    status: str
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ============================================================================
# Error Classes
# ============================================================================

class MindustryServerError(Exception):
    """Base exception for Mindustry server errors"""
    pass

class ServerNotRunningError(MindustryServerError):
    """Raised when server is not running"""
    pass

class CommandExecutionError(MindustryServerError):
    """Raised when command execution fails"""
    pass

class ConfigurationError(MindustryServerError):
    """Raised when configuration is invalid"""
    pass

class AuthenticationError(MindustryServerError):
    """Raised when authentication fails"""
    pass

# ============================================================================
# Server Manager with Retry Logic
# ============================================================================

class MindustryServerManager:
    """Manages Mindustry server lifecycle and communication"""

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    COMMAND_TIMEOUT = 10  # seconds
    LOG_BUFFER_SIZE = 100
    EVENT_HISTORY_SIZE = 50

    def __init__(self, port: int = 6567, max_retries: int = MAX_RETRIES):
        self.port = port
        self.max_retries = max_retries
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.status = ServerStatus(
            status="stopped",
            port=port,
            max_players=10
        )
        self.players: Dict[int, PlayerInfo] = {}
        self.log_buffer: deque = deque(maxlen=self.LOG_BUFFER_SIZE)
        self.event_history: deque = deque(maxlen=self.EVENT_HISTORY_SIZE)
        self.websocket_clients: List[WebSocket] = []
        self.config: Dict[str, Any] = self._load_config()
        self.lock = asyncio.Lock()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment or defaults"""
        return {
            "port": int(os.getenv("PORT", 6567)),
            "server_name": os.getenv("SERVER_NAME", "Mindustry Server"),
            "max_players": int(os.getenv("MAX_PLAYERS", 10)),
            "log_level": os.getenv("LOG_LEVEL", "info"),
            "pvp": os.getenv("PVP", "false").lower() == "true",
            "strict": os.getenv("STRICT", "false").lower() == "true",
            "auto_restart": os.getenv("AUTO_RESTART", "true").lower() == "true",
            "restart_hour": int(os.getenv("RESTART_HOUR", 3)),
        }

    async def start(self) -> None:
        """Start the Mindustry server with retry logic"""
        async with self.lock:
            if self.process and self.process.poll() is None:
                raise MindustryServerError("Server is already running")

            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(f"Starting server (attempt {attempt}/{self.max_retries})")
                    self.process = subprocess.Popen(
                        self._build_start_command(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )
                    self.start_time = time.time()
                    self.status.status = "running"
                    self.status.uptime_seconds = 0

                    # Verify process started successfully
                    await asyncio.sleep(1)
                    if self.process.poll() is not None:
                        raise MindustryServerError("Server exited immediately")

                    logger.info(f"Server started successfully (PID: {self.process.pid})")
                    await self._broadcast_event({
                        "type": "server_started",
                        "data": {"pid": self.process.pid, "timestamp": datetime.utcnow().isoformat()}
                    })
                    return

                except Exception as e:
                    logger.error(f"Failed to start server (attempt {attempt}): {str(e)}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.RETRY_DELAY * attempt)  # Exponential backoff
                    else:
                        self.status.status = "crashed"
                        raise MindustryServerError(
                            f"Failed to start server after {self.max_retries} attempts: {str(e)}"
                        )

    async def stop(self) -> None:
        """Stop the Mindustry server gracefully"""
        async with self.lock:
            if not self.process or self.process.poll() is not None:
                raise ServerNotRunningError("Server is not running")

            try:
                logger.info("Stopping server gracefully...")
                # Send graceful shutdown command
                if self.process.stdin:
                    self.process.stdin.write("exit\n")
                    self.process.stdin.flush()

                # Wait up to 10 seconds for graceful shutdown
                for _ in range(10):
                    if self.process.poll() is not None:
                        logger.info("Server stopped gracefully")
                        break
                    await asyncio.sleep(1)
                else:
                    # Force kill if still running
                    logger.warning("Server did not stop gracefully, force killing...")
                    self.process.kill()
                    self.process.wait(timeout=5)

                self.status.status = "stopped"
                self.status.uptime_seconds = 0
                self.start_time = None
                await self._broadcast_event({
                    "type": "server_stopped",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                })

            except subprocess.TimeoutExpired:
                logger.error("Failed to kill server process")
                self.status.status = "crashed"
                raise MindustryServerError("Failed to stop server process")
            except Exception as e:
                logger.error(f"Error stopping server: {str(e)}")
                raise

    async def restart(self) -> None:
        """Restart the Mindustry server"""
        logger.info("Restarting server...")
        try:
            if self.process and self.process.poll() is None:
                await self.stop()
            await asyncio.sleep(2)
            await self.start()
            logger.info("Server restarted successfully")
        except Exception as e:
            logger.error(f"Failed to restart server: {str(e)}")
            self.status.status = "crashed"
            raise

    async def execute_command(self, command: str, retry: bool = True) -> List[str]:
        """Execute a console command with retry logic"""
        if not self.process or self.process.poll() is not None:
            raise ServerNotRunningError("Server is not running")

        for attempt in range(1, self.max_retries + 1 if retry else 2):
            try:
                logger.info(f"Executing command (attempt {attempt}): {command}")

                if not self.process.stdin:
                    raise CommandExecutionError("Cannot write to server stdin")

                # Send command
                self.process.stdin.write(f"{command}\n")
                self.process.stdin.flush()

                # Parse response from logs
                output = []
                timeout_time = time.time() + self.COMMAND_TIMEOUT

                while time.time() < timeout_time:
                    # Note: In real implementation, you'd read from stdout
                    # This is simplified - actual implementation would parse server output
                    await asyncio.sleep(0.1)
                    if output:  # Return early if we got output
                        break

                logger.info(f"Command executed successfully: {command}")
                self.log_buffer.append(f"[{datetime.utcnow().isoformat()}] Command: {command}")
                return output or [f"Executed: {command}"]

            except Exception as e:
                logger.error(f"Command execution failed (attempt {attempt}): {str(e)}")
                if attempt < (self.max_retries if retry else 1):
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    raise CommandExecutionError(f"Failed to execute command after {attempt} attempts: {str(e)}")

    def get_status(self) -> ServerStatus:
        """Get current server status"""
        if self.process and self.process.poll() is None:
            self.status.status = "running"
            if self.start_time:
                self.status.uptime_seconds = int(time.time() - self.start_time)
        else:
            self.status.status = "stopped"
            self.status.uptime_seconds = 0

        self.status.players_online = len(self.players)
        self.status.last_update = datetime.utcnow().isoformat()
        return self.status

    def get_players(self) -> Dict[int, PlayerInfo]:
        """Get all connected players"""
        return self.players.copy()

    async def add_player(self, player: PlayerInfo) -> None:
        """Add a player (called when player joins)"""
        async with self.lock:
            self.players[player.id] = player
            await self._broadcast_event({
                "type": "player_joined",
                "data": {
                    "player_id": player.id,
                    "player_name": player.name,
                    "players_online": len(self.players)
                }
            })

    async def remove_player(self, player_id: int) -> None:
        """Remove a player (called when player leaves)"""
        async with self.lock:
            if player_id in self.players:
                player_name = self.players[player_id].name
                del self.players[player_id]
                await self._broadcast_event({
                    "type": "player_left",
                    "data": {
                        "player_id": player_id,
                        "player_name": player_name,
                        "players_online": len(self.players)
                    }
                })

    async def register_websocket(self, websocket: WebSocket) -> None:
        """Register a WebSocket client"""
        async with self.lock:
            self.websocket_clients.append(websocket)
            logger.info(f"WebSocket client connected. Total clients: {len(self.websocket_clients)}")

    async def unregister_websocket(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client"""
        async with self.lock:
            if websocket in self.websocket_clients:
                self.websocket_clients.remove(websocket)
                logger.info(f"WebSocket client disconnected. Total clients: {len(self.websocket_clients)}")

    async def _broadcast_event(self, event: Dict[str, Any]) -> None:
        """Broadcast an event to all connected WebSocket clients"""
        self.event_history.append(event)
        disconnected = []

        for client in self.websocket_clients:
            try:
                await client.send_json(event)
            except Exception as e:
                logger.error(f"Error sending WebSocket event: {str(e)}")
                disconnected.append(client)

        # Clean up disconnected clients
        for client in disconnected:
            await self.unregister_websocket(client)

    def _build_start_command(self) -> List[str]:
        """Build the Java command to start Mindustry server"""
        cmd = [
            "java",
            "-Xmx2G",
            "-server",
            "-jar", "/mindustry/server.jar",
            "-port", str(self.config["port"]),
            "-name", self.config["server_name"],
            "-players", str(self.config["max_players"]),
        ]

        if self.config["pvp"]:
            cmd.append("-pvp")
        if self.config["strict"]:
            cmd.append("-strict")

        return cmd

    def get_log(self, lines: int = 50) -> List[str]:
        """Get recent log entries"""
        return list(self.log_buffer)[-lines:]

    def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events"""
        return list(self.event_history)[-limit:]

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Mindustry Server API",
    description="REST API for Mindustry Server with Home Assistant integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize server manager
server_manager = MindustryServerManager()

# API key validation
API_KEY = os.getenv("API_KEY", "mindustry-addon-key")

def verify_api_key(authorization: Optional[str] = Header(None)) -> None:
    """Verify API key from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    token = authorization.split(" ")[1]
    if token != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health", response_model=APIResponse, tags=["Health"])
async def health_check() -> APIResponse:
    """Health check endpoint"""
    return APIResponse(
        status="ok",
        message="API server is running",
        data={"version": "1.0.0"}
    )

@app.get("/api/server", response_model=ServerStatus, tags=["Server"])
async def get_server_status(authorization: None = Depends(verify_api_key)) -> ServerStatus:
    """Get current server status"""
    return server_manager.get_status()

# ============================================================================
# Server Control Endpoints
# ============================================================================

@app.post("/api/server/start", response_model=APIResponse, tags=["Server Control"])
async def start_server(authorization: None = Depends(verify_api_key)) -> APIResponse:
    """Start the Mindustry server"""
    try:
        await server_manager.start()
        return APIResponse(
            status="success",
            message="Server starting...",
            data={"status": "running"}
        )
    except MindustryServerError as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error starting server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/server/stop", response_model=APIResponse, tags=["Server Control"])
async def stop_server(authorization: None = Depends(verify_api_key)) -> APIResponse:
    """Stop the Mindustry server"""
    try:
        await server_manager.stop()
        return APIResponse(
            status="success",
            message="Server stopped",
            data={"status": "stopped"}
        )
    except ServerNotRunningError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error stopping server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/server/restart", response_model=APIResponse, tags=["Server Control"])
async def restart_server(authorization: None = Depends(verify_api_key)) -> APIResponse:
    """Restart the Mindustry server"""
    try:
        await server_manager.restart()
        return APIResponse(
            status="success",
            message="Server restarted",
            data={"status": "running"}
        )
    except Exception as e:
        logger.error(f"Failed to restart server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/server/control", response_model=APIResponse, tags=["Server Control"])
async def control_server(
    request: ControlRequest,
    authorization: None = Depends(verify_api_key)
) -> APIResponse:
    """Control server with custom actions"""
    try:
        action = request.action.lower()

        if action == "restart":
            await server_manager.restart()
            return APIResponse(
                status="success",
                message="Server restarting...",
                data={"action": "restart", "status": "running"}
            )
        elif action == "stop":
            await server_manager.stop()
            return APIResponse(
                status="success",
                message="Server stopped",
                data={"action": "stop", "status": "stopped"}
            )
        elif action == "pause":
            await server_manager.execute_command("pause")
            return APIResponse(
                status="success",
                message="Server paused",
                data={"action": "pause"}
            )
        elif action == "resume":
            await server_manager.execute_command("resume")
            return APIResponse(
                status="success",
                message="Server resumed",
                data={"action": "resume"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {action}"
            )
    except MindustryServerError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error controlling server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ============================================================================
# Player Management Endpoints
# ============================================================================

@app.get("/api/players", tags=["Players"])
async def get_players(authorization: None = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get all connected players"""
    players = server_manager.get_players()
    return {
        "players": list(players.values()),
        "count": len(players)
    }

@app.post("/api/players/{player_id}/kick", response_model=APIResponse, tags=["Players"])
async def kick_player(
    player_id: int,
    authorization: None = Depends(verify_api_key)
) -> APIResponse:
    """Kick a player from the server"""
    try:
        await server_manager.execute_command(f"kick {player_id}")
        await server_manager.remove_player(player_id)
        return APIResponse(
            status="success",
            message=f"Player {player_id} kicked",
            data={"player_id": player_id}
        )
    except ServerNotRunningError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error kicking player: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/players/{player_id}/mute", response_model=APIResponse, tags=["Players"])
async def mute_player(
    player_id: int,
    muted: bool = True,
    authorization: None = Depends(verify_api_key)
) -> APIResponse:
    """Mute or unmute a player"""
    try:
        command = "mute" if muted else "unmute"
        await server_manager.execute_command(f"{command} {player_id}")
        return APIResponse(
            status="success",
            message=f"Player {player_id} {'muted' if muted else 'unmuted'}",
            data={"player_id": player_id, "muted": muted}
        )
    except ServerNotRunningError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error muting player: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ============================================================================
# Console Command Endpoints
# ============================================================================

@app.post("/api/commands", response_model=APIResponse, tags=["Commands"])
async def execute_command(
    request: CommandRequest,
    authorization: None = Depends(verify_api_key)
) -> APIResponse:
    """Execute a console command"""
    try:
        # Sanitize command input
        command = request.command.strip()
        if not command:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Command cannot be empty"
            )

        if len(command) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Command too long (max 500 characters)"
            )

        output = await server_manager.execute_command(command)
        return APIResponse(
            status="success",
            message="Command executed",
            data={"command": command, "output": output}
        )
    except ServerNotRunningError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except CommandExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/commands/log", tags=["Commands"])
async def get_command_log(
    lines: int = 50,
    authorization: None = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get recent console output"""
    log_lines = server_manager.get_log(min(lines, 200))
    return {
        "log": log_lines,
        "count": len(log_lines),
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time server events"""
    await websocket.accept()
    await server_manager.register_websocket(websocket)

    try:
        # Send event history on connect
        history = server_manager.get_event_history(20)
        for event in history:
            await websocket.send_json(event)

        # Keep connection alive and forward messages
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                logger.info(f"WebSocket message received: {msg}")
                # Echo back or process custom WebSocket commands here
                await websocket.send_json({"type": "ack", "data": msg})
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        await server_manager.unregister_websocket(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await server_manager.unregister_websocket(websocket)

# ============================================================================
# Configuration Endpoints
# ============================================================================

@app.get("/api/config", tags=["Configuration"])
async def get_config(authorization: None = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get current configuration"""
    return server_manager.config.copy()

@app.post("/api/config", response_model=APIResponse, tags=["Configuration"])
async def update_config(
    request: ConfigUpdateRequest,
    authorization: None = Depends(verify_api_key)
) -> APIResponse:
    """Update configuration (requires restart)"""
    try:
        # Validate input
        if request.max_players is not None:
            if not (1 <= request.max_players <= 256):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="max_players must be between 1 and 256"
                )
        if request.server_name is not None:
            if not (1 <= len(request.server_name) <= 50):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="server_name must be between 1 and 50 characters"
                )

        # Update config
        if request.server_name is not None:
            server_manager.config["server_name"] = request.server_name
        if request.max_players is not None:
            server_manager.config["max_players"] = request.max_players
        if request.pvp is not None:
            server_manager.config["pvp"] = request.pvp
        if request.strict is not None:
            server_manager.config["strict"] = request.strict
        if request.auto_restart is not None:
            server_manager.config["auto_restart"] = request.auto_restart

        return APIResponse(
            status="success",
            message="Configuration updated (restart required for changes to take effect)",
            data=server_manager.config.copy()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ============================================================================
# Event History Endpoint
# ============================================================================

@app.get("/api/events", tags=["Events"])
async def get_events(
    limit: int = 50,
    authorization: None = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get event history"""
    events = server_manager.get_event_history(min(limit, 200))
    return {
        "events": events,
        "count": len(events),
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(MindustryServerError)
async def mindustry_error_handler(request, exc):
    """Handle Mindustry-specific errors"""
    return APIResponse(
        status="error",
        message=str(exc),
        data={"error_type": exc.__class__.__name__}
    )

# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """On application startup"""
    logger.info("Mindustry Server API starting...")
    logger.info(f"Configuration: {server_manager.config}")

@app.on_event("shutdown")
async def shutdown_event():
    """On application shutdown"""
    logger.info("Mindustry Server API shutting down...")
    if server_manager.process and server_manager.process.poll() is None:
        try:
            await server_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping server on shutdown: {str(e)}")

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info" if not debug else "debug"
    )
