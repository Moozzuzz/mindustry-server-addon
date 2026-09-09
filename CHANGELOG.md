# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-09

### Added

#### Core Features
- ✨ Full Mindustry game server with Home Assistant addon support
- ✨ REST API with comprehensive endpoint coverage
- ✨ WebSocket support for real-time event streaming
- ✨ Real-time log parsing with regex patterns (13+ event types)
- ✨ Player management (join/leave tracking, kick, mute)
- ✨ Server control (start, stop, restart, pause, resume)
- ✨ Map management and game mode control
- ✨ Console command execution with output capture

#### Reliability & Error Handling
- ✅ Retry logic with exponential backoff (3 attempts max)
- ✅ Graceful shutdown with timeout fallback
- ✅ Comprehensive error handling with custom exceptions
- ✅ Command execution timeout protection (10s)
- ✅ Process health monitoring and automatic recovery
- ✅ Rate limiting per client (100 req/min)
- ✅ Async locks for race condition prevention

#### Monitoring & Events
- 📊 Real-time WebSocket event broadcasting
- 📊 Event history on new connections (20 events)
- 📊 Health monitoring with automatic alerts
- 📊 Event logging with configurable retention
- 📊 Player state tracking
- 📊 Server uptime tracking

#### Docker & Deployment
- 🐳 Multi-architecture support (amd64, aarch64)
- 🐳 Health checks every 30 seconds
- 🐳 S6 overlay process management
- 🐳 Non-root user execution
- 🐳 Persistent data volumes
- 🐳 Docker Compose development environment
- 🐳 Comprehensive startup scripts with error handling

#### Configuration
- ⚙️ YAML-based configuration
- ⚙️ Port configuration (1025-65535)
- ⚙️ Max players configuration (1-256)
- ⚙️ PvP and strict mode toggles
- ⚙️ Auto-restart scheduling
- ⚙️ Log level control (trace to fatal)

#### API Security
- 🔐 Bearer token authentication
- 🔐 Auto-generated API keys on first start
- 🔐 CORS middleware configuration
- 🔐 Input validation and sanitization
- 🔐 Command injection prevention

#### Utilities
- 🛠️ Config management system
- 🛠️ Advanced logging with colors
- 🛠️ String sanitization functions
- 🛠️ Safe JSON serialization
- 🛠️ Command parsing utilities
- 🛠️ File and directory utilities
- 🛠️ Time formatting and scheduling
- 🛠️ Port and value validation

#### Documentation
- 📚 Comprehensive README with features overview
- 📚 Quick Start guide (5-minute setup)
- 📚 API documentation with examples
- 📚 Home Assistant integration guide
- 📚 Docker development guide
- 📚 Contributing guidelines
- 📚 Full addon documentation
- 📚 Troubleshooting section
- 📚 Architecture diagrams

### Technical Details

#### Server Architecture
- **Language**: Python 3.11 with FastAPI
- **Async Framework**: asyncio with async/await
- **Game Server**: Java-based Mindustry v146
- **Container**: Docker with Home Assistant base image
- **Process Management**: S6 overlay

#### Key Components
- `server.py`: Main REST API with ~1000 lines
- `monitor.py`: Real-time log parsing and event extraction
- `events.py`: WebSocket management and event broadcasting
- `utils.py`: Utility functions and helpers
- `integration.py`: High-level service coordination

#### Performance Characteristics
- CPU: 1-2 cores typical
- Memory: 2GB Java + 512MB Python
- Startup: ~30-60 seconds
- Event latency: <100ms
- API response time: <100ms

### File Structure

```
mindustry-server-addon/
├── example/
│   ├── config.yaml          # Addon configuration schema
│   ├── build.yaml           # Docker build config
│   ├── Dockerfile           # Container definition
│   ├── DOCS.md              # Addon documentation
│   ├── app/
│   │   ├── server.py        # REST API server
│   │   ├── monitor.py       # Log monitor
│   │   ├── events.py        # Event management
│   │   ├── utils.py         # Utilities
│   │   └── integration.py   # Integration service
│   └── rootfs/              # Container filesystem
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Dev environment
├── README.md                # Main documentation
├── QUICKSTART.md            # Quick start guide
├── CONTRIBUTING.md          # Contribution guidelines
└── CHANGELOG.md             # This file
```

### Dependencies

**System**:
- Java 11 (openjdk11-jre)
- Python 3.11
- Bash
- curl/wget

**Python Packages**:
- fastapi==0.104.1
- uvicorn==0.24.0
- websockets==12.0
- pydantic==2.5.0
- python-dotenv==1.0.0
- aiofiles==23.2.1
- psutil==5.9.6
- pyyaml==6.0.1
- retrying==1.3.4

### Known Limitations

- Log parsing based on regex patterns (may miss some events)
- Command output not captured in real-time
- WebSocket connections limited by system resources
- Single server instance per addon container

### Future Roadmap

- [ ] Multi-server support per addon
- [ ] Admin panel UI
- [ ] MQTT integration
- [ ] Prometheus metrics export
- [ ] Advanced player stats tracking
- [ ] Map editor integration
- [ ] Automated backups
- [ ] Plugin system

---

**Initial Release**: Full-featured Mindustry server addon with complete Home Assistant integration.
