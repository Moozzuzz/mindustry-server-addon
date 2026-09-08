#!/usr/bin/env python3
"""
Mindustry Server Log Monitor
Monitors Mindustry server output and parses events for WebSocket broadcasting
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# Event Types
# ============================================================================

class EventType(str, Enum):
    """Mindustry server event types"""
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_KICKED = "player_kicked"
    WAVE_STARTED = "wave_started"
    WAVE_COMPLETED = "wave_completed"
    MAP_CHANGED = "map_changed"
    GAMEMODE_CHANGED = "gamemode_changed"
    SERVER_STARTED = "server_started"
    SERVER_STOPPED = "server_stopped"
    CHAT_MESSAGE = "chat_message"
    GAME_OVER = "game_over"
    CUSTOM_MESSAGE = "custom_message"
    ERROR = "error"

# ============================================================================
# Event Models
# ============================================================================

class ServerEvent:
    """Represents a parsed server event"""

    def __init__(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        timestamp: Optional[str] = None,
        raw_line: Optional[str] = None
    ):
        self.type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.raw_line = raw_line

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "raw_line": self.raw_line
        }

# ============================================================================
# Log Parser Patterns
# ============================================================================

class LogPatterns:
    """Regex patterns for parsing Mindustry server logs"""

    # Player join: "[Player1] connected"
    PLAYER_JOINED = re.compile(
        r"\[(?P<player_name>[^\]]+)\]\s+connected",
        re.IGNORECASE
    )

    # Player left: "[Player1] disconnected"
    PLAYER_LEFT = re.compile(
        r"\[(?P<player_name>[^\]]+)\]\s+disconnected",
        re.IGNORECASE
    )

    # Player kicked: "[Player1] kicked"
    PLAYER_KICKED = re.compile(
        r"\[(?P<player_name>[^\]]+)\]\s+kicked",
        re.IGNORECASE
    )

    # Wave started: "wave 5 started"
    WAVE_STARTED = re.compile(
        r"wave\s+(?P<wave>\d+)\s+started",
        re.IGNORECASE
    )

    # Wave completed: "wave 5 complete"
    WAVE_COMPLETED = re.compile(
        r"wave\s+(?P<wave>\d+)\s+(complete|finished)",
        re.IGNORECASE
    )

    # Map change: "selected map: Core Shard"
    MAP_CHANGED = re.compile(
        r"selected map:\s+(?P<map_name>.+?)(?:\s+by|$)",
        re.IGNORECASE
    )

    # Chat message: "[Player1]: hello world"
    CHAT_MESSAGE = re.compile(
        r"\[(?P<player_name>[^\]]+)\]:\s+(?P<message>.+)$",
        re.IGNORECASE
    )

    # Game over: "game over"
    GAME_OVER = re.compile(
        r"game\s+over",
        re.IGNORECASE
    )

    # Server started: "Server started"
    SERVER_STARTED = re.compile(
        r"server\s+started",
        re.IGNORECASE
    )

    # Error patterns
    ERROR = re.compile(
        r"(?:error|exception|crash|fatal)",
        re.IGNORECASE
    )

# ============================================================================
# Log Monitor
# ============================================================================

class MindustryLogMonitor:
    """Monitors Mindustry server process output and parses events"""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.players: Dict[str, int] = {}  # player_name -> player_id
        self.current_wave = 0
        self.current_map = "Unknown"

    async def start(self, process_stdout) -> None:
        """Start monitoring the server process output"""
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(process_stdout))
        logger.info("Log monitor started")

    async def stop(self) -> None:
        """Stop monitoring"""
        self.running = False
        if self.monitor_task:
            try:
                await asyncio.wait_for(self.monitor_task, timeout=5)
            except asyncio.TimeoutError:
                self.monitor_task.cancel()
        logger.info("Log monitor stopped")

    async def _monitor_loop(self, process_stdout) -> None:
        """Main monitoring loop"""
        try:
            while self.running:
                try:
                    # Read line from process stdout
                    line = await asyncio.wait_for(
                        self._read_line(process_stdout),
                        timeout=1.0
                    )

                    if line:
                        await self._process_line(line)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error reading process output: {str(e)}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Log monitor cancelled")
        except Exception as e:
            logger.error(f"Monitor loop error: {str(e)}")
            self.running = False

    async def _read_line(self, process_stdout) -> Optional[str]:
        """Read a line from process stdout"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: process_stdout.readline() if process_stdout else None
        )

    async def _process_line(self, line: str) -> None:
        """Process a log line and generate events"""
        line = line.strip()
        if not line:
            return

        logger.debug(f"Processing log line: {line}")

        events = self._parse_line(line)
        for event in events:
            await self.event_queue.put(event)
            if self.callback:
                await self.callback(event)

    def _parse_line(self, line: str) -> List[ServerEvent]:
        """Parse a log line and return list of events"""
        events = []

        # Check for player join
        match = LogPatterns.PLAYER_JOINED.search(line)
        if match:
            player_name = match.group("player_name")
            player_id = self._generate_player_id(player_name)
            self.players[player_name] = player_id
            events.append(ServerEvent(
                EventType.PLAYER_JOINED,
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "players_online": len(self.players)
                },
                raw_line=line
            ))

        # Check for player left
        match = LogPatterns.PLAYER_LEFT.search(line)
        if match:
            player_name = match.group("player_name")
            if player_name in self.players:
                player_id = self.players.pop(player_name)
                events.append(ServerEvent(
                    EventType.PLAYER_LEFT,
                    {
                        "player_id": player_id,
                        "player_name": player_name,
                        "players_online": len(self.players)
                    },
                    raw_line=line
                ))

        # Check for player kicked
        match = LogPatterns.PLAYER_KICKED.search(line)
        if match:
            player_name = match.group("player_name")
            if player_name in self.players:
                player_id = self.players.pop(player_name)
                events.append(ServerEvent(
                    EventType.PLAYER_KICKED,
                    {
                        "player_id": player_id,
                        "player_name": player_name,
                        "players_online": len(self.players)
                    },
                    raw_line=line
                ))

        # Check for wave started
        match = LogPatterns.WAVE_STARTED.search(line)
        if match:
            wave = int(match.group("wave"))
            self.current_wave = wave
            events.append(ServerEvent(
                EventType.WAVE_STARTED,
                {
                    "wave": wave,
                    "players_online": len(self.players)
                },
                raw_line=line
            ))

        # Check for wave completed
        match = LogPatterns.WAVE_COMPLETED.search(line)
        if match:
            wave = int(match.group("wave"))
            events.append(ServerEvent(
                EventType.WAVE_COMPLETED,
                {
                    "wave": wave,
                    "players_online": len(self.players)
                },
                raw_line=line
            ))

        # Check for map change
        match = LogPatterns.MAP_CHANGED.search(line)
        if match:
            map_name = match.group("map_name").strip()
            self.current_map = map_name
            self.current_wave = 0
            events.append(ServerEvent(
                EventType.MAP_CHANGED,
                {
                    "map_name": map_name,
                    "players_online": len(self.players)
                },
                raw_line=line
            ))

        # Check for chat message (only if not already handled above)
        if not any(e.type == EventType.PLAYER_JOINED for e in events):
            match = LogPatterns.CHAT_MESSAGE.search(line)
            if match:
                player_name = match.group("player_name")
                message = match.group("message")
                events.append(ServerEvent(
                    EventType.CHAT_MESSAGE,
                    {
                        "player_name": player_name,
                        "message": message,
                        "players_online": len(self.players)
                    },
                    raw_line=line
                ))

        # Check for game over
        match = LogPatterns.GAME_OVER.search(line)
        if match:
            events.append(ServerEvent(
                EventType.GAME_OVER,
                {
                    "players_online": len(self.players),
                    "wave": self.current_wave,
                    "map": self.current_map
                },
                raw_line=line
            ))

        # Check for errors
        if LogPatterns.ERROR.search(line):
            events.append(ServerEvent(
                EventType.ERROR,
                {
                    "message": line,
                    "severity": "high"
                },
                raw_line=line
            ))

        return events

    def _generate_player_id(self, player_name: str) -> int:
        """Generate a unique player ID"""
        return hash(player_name) % 10000

    async def get_event(self, timeout: float = 1.0) -> Optional[ServerEvent]:
        """Get next event from queue"""
        try:
            return await asyncio.wait_for(
                self.event_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    def get_state(self) -> Dict[str, Any]:
        """Get current monitor state"""
        return {
            "running": self.running,
            "players": self.players,
            "current_wave": self.current_wave,
            "current_map": self.current_map,
            "queue_size": self.event_queue.qsize()
        }
