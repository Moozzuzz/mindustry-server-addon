# Mindustry Server Addon for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/Moozzuzz/mindustry-server-addon.svg)](https://github.com/Moozzuzz/mindustry-server-addon/releases)
[![License](https://img.shields.io/github/license/Moozzuzz/mindustry-server-addon.svg)](LICENSE)
[![GitHub Activity](https://img.shields.io/github/commit-activity/m/Moozzuzz/mindustry-server-addon.svg)](https://github.com/Moozzuzz/mindustry-server-addon/commits/main)

A complete Home Assistant addon that runs a Mindustry game server with REST API and WebSocket support for full integration with Home Assistant. Monitor and control your Mindustry server directly from Home Assistant automation, dashboards, and automations.

## Features

✅ **Full Server Control**
- Start, stop, and restart the game server
- Execute console commands
- Change maps and game modes
- Manage players (kick, mute)
- Auto-restart scheduling

✅ **Real-time Monitoring**
- WebSocket event streaming
- Player join/leave notifications
- Wave progression tracking
- Map change detection
- Chat message capture
- Server health monitoring with alerts

✅ **REST API**
- Complete REST endpoints for all operations
- Bearer token authentication
- Rate limiting protection
- Comprehensive error handling with retry logic
- Event history on connection

✅ **Robust Architecture**
- Async/await throughout for non-blocking operations
- 3-attempt retry logic with exponential backoff
- Graceful shutdown with timeout fallback to force kill
- Real-time log parsing with regex patterns
- Docker health checks every 30 seconds
- Persistent configuration and data

✅ **Home Assistant Integration**
- REST sensors for server status
- Template switches for control
- Automations and scripts support
- Full webhook/API integration

## Quick Start

### Installation on Home Assistant

1. **Add Repository**
   - Go to Settings → Add-ons → Add-on Store
   - Click the menu (⋮) → Repositories
   - Add: `https://github.com/Moozzuzz/mindustry-server-addon`
   - Close and refresh

2. **Install Addon**
   - Search for "Mindustry Server"
   - Click Install
   - Wait for installation to complete

3. **Configure**
   - Click Configuration tab
   - Adjust settings as needed

4. **Start**
   - Click the Start button
   - Check Logs to verify startup

5. **Get API Key**
   - SSH into Home Assistant
   - Run: `docker exec addon_mindustry_server cat /data/api_key`
   - Save this key securely

**See [QUICKSTART.md](QUICKSTART.md) for detailed step-by-step guide.**

## API Usage

### Health Check
```bash
curl http://localhost:5000/health
```

### Get Server Status
```bash
API_KEY="your-api-key"
curl -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/server
```

### Restart Server
```bash
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/server/restart
```

### Execute Console Command
```bash
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"command": "say Server restarting soon"}' \
  http://localhost:5000/api/commands
```

### List Players
```bash
curl -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/players
```

### Kick Player
```bash
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/players/1/kick
```

### WebSocket Events
```bash
wscat -c ws://localhost:5000/ws
```

## Home Assistant Integration

### REST Sensor

```yaml
sensor:
  - platform: rest
    name: Mindustry Server
    resource: http://homeassistant.local:5000/api/server
    headers:
      Authorization: "Bearer YOUR_API_KEY_HERE"
    method: GET
    json_attributes:
      - players_online
      - wave
      - map_name
    value_template: "{{ value_json.status }}"
    scan_interval: 60
```

### REST Commands

```yaml
rest_command:
  mindustry_restart:
    url: http://homeassistant.local:5000/api/server/restart
    method: POST
    headers:
      Authorization: "Bearer YOUR_API_KEY_HERE"

  mindustry_say:
    url: http://homeassistant.local:5000/api/commands
    method: POST
    headers:
      Authorization: "Bearer YOUR_API_KEY_HERE"
      Content-Type: application/json
    payload: '{"command": "say {{ message }}"}'
```

### Automations

```yaml
automation:
  - alias: "Notify when player joins"
    trigger:
      platform: mqtt
      topic: homeassistant/mindustry/events/player_joined
    action:
      service: persistent_notification.create
      data:
        title: "Player Joined"
        message: "{{ trigger.payload_json.player_name }} joined"

  - alias: "Daily server restart"
    trigger:
      platform: time
      at: "03:00:00"
    action:
      - service: rest_command.mindustry_restart
      - service: notify.mobile_app_phone
        data:
          message: "Mindustry server restarting..."
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `port` | integer | 6567 | Mindustry server port (UDP) |
| `server_name` | string | "Mindustry Server" | Server display name |
| `max_players` | integer | 10 | Maximum concurrent players |
| `log_level` | string | info | Logging verbosity |
| `pvp` | boolean | false | Enable PvP mode |
| `strict` | boolean | false | Enable anti-cheat |
| `auto_restart` | boolean | true | Auto restart daily |
| `restart_hour` | integer | 3 | Restart hour (0-23 UTC) |

## Port Mappings

| Port | Protocol | Purpose |
|------|----------|---------|
| 6567 | UDP | Mindustry game server |
| 5000 | TCP | REST API + WebSocket |

## API Endpoints

### Server Status
- `GET /api/server` - Get server status and stats
- `GET /health` - Health check endpoint

### Server Control
- `POST /api/server/start` - Start server
- `POST /api/server/stop` - Stop server
- `POST /api/server/restart` - Restart server

### Players
- `GET /api/players` - List connected players
- `POST /api/players/{id}/kick` - Kick a player
- `POST /api/players/{id}/mute` - Mute/unmute player

### Commands
- `POST /api/commands` - Execute console command
- `GET /api/commands/log` - Get recent console output

### Events
- `WS /ws` - WebSocket for real-time events
- `GET /api/events` - Get event history

## WebSocket Events

Real-time events include:
- `player_joined` - Player connected
- `player_left` - Player disconnected
- `wave_started` - Wave began
- `wave_completed` - Wave finished
- `map_changed` - Map rotated
- `chat_message` - Player sent message
- `game_over` - Game ended
- `server_stopped` - Server shut down
- `health_status` - Periodic health check
- `health_alert` - Health alerts

## Troubleshooting

### Server Won't Start
1. Check addon logs
2. Verify port 6567 is not in use
3. Check Java is installed
4. Try restarting the addon

### API Connection Issues
1. Verify API is running: `curl http://localhost:5000/health`
2. Check API key format: `Authorization: Bearer YOUR_KEY`
3. Verify network connectivity

### Players Can't Connect
1. Verify port 6567 is open
2. Check firewall allows UDP 6567
3. Verify server is running via API
4. Restart server if needed

## Documentation

- [Quick Start Guide](QUICKSTART.md) - 5-minute setup
- [Docker Development Guide](DOCKER_DEV_GUIDE.md) - Local development
- [Contributing Guide](CONTRIBUTING.md) - How to contribute
- [Changelog](CHANGELOG.md) - Release history

## Project Structure

```
mindustry-server-addon/
├── example/
│   ├── config.yaml          # Addon configuration schema
│   ├── build.yaml           # Docker build config
│   ├── Dockerfile           # Container definition
│   ├── DOCS.md              # Full documentation
│   ├── app/
│   │   ├── server.py        # REST API (1000+ lines)
│   │   ├── monitor.py       # Log monitoring
│   │   ├── events.py        # Event management
│   │   ├── utils.py         # Utilities
│   │   └── integration.py   # Integration service
│   └── rootfs/              # Container filesystem
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Dev environment
├── README.md                # This file
├── QUICKSTART.md            # Quick start guide
├── DOCKER_DEV_GUIDE.md      # Docker guide
├── CONTRIBUTING.md          # Contributing guidelines
├── CHANGELOG.md             # Release notes
└── LICENSE                  # MIT License
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License - See [LICENSE](LICENSE) for details

## Support

- **Issues**: [GitHub Issues](https://github.com/Moozzuzz/mindustry-server-addon/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Moozzuzz/mindustry-server-addon/discussions)

---

**Made with ❤️ for the Mindustry and Home Assistant communities**
