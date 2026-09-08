#!/usr/bin/env python3
"""
Utility functions for Mindustry Server addon
"""

import logging
import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration Utilities
# ============================================================================

class ConfigManager:
    """Manages configuration for the addon"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "/data/options.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
        return self._get_defaults()

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "port": 6567,
            "server_name": "Mindustry Server",
            "log_level": "info",
            "max_players": 10,
            "pvp": False,
            "strict": False,
            "auto_restart": True,
            "restart_hour": 3
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
        self.save()

    def save(self) -> None:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return self.config.copy()

# ============================================================================
# Logging Utilities
# ============================================================================

class LogFormatter(logging.Formatter):
    """Custom log formatter with colors"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color"""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.RESET}"
            )
        return super().format(record)

def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration"""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    formatter = LogFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

# ============================================================================
# Token/Key Utilities
# ============================================================================

def generate_api_key(length: int = 32) -> str:
    """Generate a random API key"""
    import secrets
    return secrets.token_urlsafe(length)

def hash_api_key(key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(key.encode()).hexdigest()

def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Verify an API key against stored hash"""
    return hash_api_key(provided_key) == stored_hash

# ============================================================================
# Time Utilities
# ============================================================================

def get_uptime_string(seconds: int) -> str:
    """Convert seconds to human-readable uptime string"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"

def should_restart(restart_hour: int, last_restart: Optional[datetime] = None) -> bool:
    """Check if server should auto-restart at specified hour"""
    now = datetime.utcnow()
    restart_time = now.replace(hour=restart_hour, minute=0, second=0, microsecond=0)

    # If we're past the restart hour today, check tomorrow
    if now > restart_time:
        restart_time += timedelta(days=1)

    # If last_restart is given, check if enough time has passed
    if last_restart:
        if (now - last_restart).total_seconds() < 3600:  # Less than 1 hour
            return False

    # Return True if we're close to restart time (within 2 minutes)
    time_until_restart = (restart_time - now).total_seconds()
    return 0 <= time_until_restart <= 120

# ============================================================================
# Validation Utilities
# ============================================================================

def validate_port(port: int) -> bool:
    """Validate port number"""
    return 1024 <= port <= 65535

def validate_server_name(name: str) -> bool:
    """Validate server name"""
    return 1 <= len(name) <= 50 and name.isprintable()

def validate_max_players(count: int) -> bool:
    """Validate max players count"""
    return 1 <= count <= 256

def validate_player_name(name: str) -> bool:
    """Validate player name"""
    return 1 <= len(name) <= 32 and name.isprintable()

def validate_command(command: str) -> bool:
    """Validate console command"""
    if not command or len(command) > 500:
        return False
    # Prevent dangerous commands
    dangerous = ["rm ", "system", "exec"]
    return not any(d in command.lower() for d in dangerous)

# ============================================================================
# JSON Utilities
# ============================================================================

def safe_json_serialize(obj: Any) -> str:
    """Safely serialize object to JSON"""
    try:
        return json.dumps(obj, default=str)
    except Exception as e:
        logger.error(f"JSON serialization error: {str(e)}")
        return json.dumps({"error": "Serialization failed"})

def safe_json_deserialize(data: str, default: Any = None) -> Any:
    """Safely deserialize JSON string"""
    try:
        return json.loads(data)
    except Exception as e:
        logger.error(f"JSON deserialization error: {str(e)}")
        return default

# ============================================================================
# String Utilities
# ============================================================================

def truncate_string(s: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate string to specified length"""
    if len(s) <= length:
        return s
    return s[:length - len(suffix)] + suffix

def sanitize_string(s: str, max_length: int = 500) -> str:
    """Sanitize string for safe display"""
    # Remove control characters
    s = ''.join(c for c in s if c.isprintable() or c in '\n\t')
    # Truncate if too long
    return truncate_string(s, max_length)

def parse_command_args(command: str) -> List[str]:
    """Parse command string into arguments"""
    import shlex
    try:
        return shlex.split(command)
    except Exception as e:
        logger.error(f"Error parsing command: {str(e)}")
        return command.split()

# ============================================================================
# File Utilities
# ============================================================================

def get_file_size(path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(path)
    except Exception as e:
        logger.error(f"Error getting file size: {str(e)}")
        return 0

def format_bytes(size: int) -> str:
    """Format bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def ensure_directory(path: str) -> bool:
    """Ensure directory exists"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory: {str(e)}")
        return False
