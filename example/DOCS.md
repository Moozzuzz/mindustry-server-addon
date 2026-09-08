# Home Assistant Addon Documentation

## Installation

### Method 1: From Repository

1. In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
2. Add this repository: `https://github.com/Moozzuzz/mindustry-server-addon`
3. Install the "Mindustry Server" addon
4. Configure the addon options
5. Start the addon

### Method 2: Manual Installation

1. SSH into your Home Assistant instance
2. Clone the repository:
   ```bash
   git clone https://github.com/Moozzuzz/mindustry-server-addon /addons/mindustry-server
   ```
3. Restart Home Assistant
4. Install from addon store

## Configuration

Edit the addon options in Home Assistant UI:

### Basic Settings

- **Port**: Server port (default: 6567)
- **Server Name**: Display name for the server
- **Max Players**: Maximum concurrent players (1-256)
- **Log Level**: Logging verbosity (trace, debug, info, warning, error, fatal)

### Game Mode Settings

- **PvP Mode**: Enable player vs player combat
- **Strict Mode**: Enable anti-cheat measures

### Auto-Restart

- **Enable Auto Restart**: Automatically restart server daily
- **Restart Hour**: Hour of day to restart (0-23, UTC)

## API Access

The addon exposes a REST API accessible at `http://homeassistant.local:5000`

### Get API Key

The API key is generated automatically on first start:

```bash
# From Home Assistant host
docker exec addon_mindustry_server cat /data/api_key

# Or from SSH
cat /addons/mindustry-server/.api_key
```

### API Endpoints

All endpoints require authentication:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://homeassistant.local:5000/...
```

#### Server Status
```bash
GET /api/server
```

Response:
```json
{
  "status": "running",
  "uptime_seconds": 3600,
  "players_online": 3,
  "max_players": 10,
  "map_name": "Desolate Pool",
  "wave": 45,
  "difficulty": "hard"
}
```

#### Server Control
```bash
POST /api/server/start
POST /api/server/stop
POST /api/server/restart
```

#### Execute Commands
```bash
POST /api/commands
Content-Type: application/json

{
  "command": "say Server will restart in 5 minutes"
}
```

#### Player Management
```bash
GET /api/players
POST /api/players/{player_id}/kick
POST /api/players/{player_id}/mute
```

#### WebSocket Events
```bash
ws://homeassistant.local/api/mindustry/ws
```

Events include:
- `player_joined` - Player connected
- `player_left` - Player disconnected
- `wave_started` - New wave begun
- `wave_completed` - Wave finished
- `chat_message` - Player sent message
- `map_changed` - Map rotated
- `game_over` - Game ended
- `server_stopped` - Server shut down

## Home Assistant Integration

### REST Sensor

```yaml
sensor:
  - platform: rest
    name: mindustry_status
    resource: http://homeassistant.local:5000/api/server
    headers:
      Authorization: "Bearer YOUR_API_KEY"
    method: GET
    json_attributes:
      - players_online
      - wave
      - map_name
      - difficulty
    value_template: "{{ value_json.status }}"
    scan_interval: 60
```

### REST Command

```yaml
rest_command:
  mindustry_restart:
    url: http://homeassistant.local:5000/api/server/restart
    method: POST
    headers:
      Authorization: "Bearer YOUR_API_KEY"
      Content-Type: application/json

  mindustry_say:
    url: http://homeassistant.local:5000/api/commands
    method: POST
    headers:
      Authorization: "Bearer YOUR_API_KEY"
      Content-Type: application/json
    payload: '{"command": "say {{ message }}"}'
```

### Automation Example

```yaml
automation:
  - alias: "Restart Mindustry Server Daily"
    trigger:
      platform: time
      at: "03:00:00"
    action:
      - service: rest_command.mindustry_restart
      - service: persistent_notification.create
        data:
          title: "Mindustry Server"
          message: "Server is restarting..."
```

### Switch Template

```yaml
switch:
  - platform: template
    switches:
      mindustry_restart:
        friendly_name: "Restart Mindustry Server"
        value_template: "off"
        turn_on:
          - service: rest_command.mindustry_restart
```

## Monitoring & Logging

### View Logs

In Home Assistant:
1. Go to **Settings** → **Add-ons** → **Mindustry Server**
2. Click **Logs** tab

### Enable Debug Logging

Set `log_level` to `debug` in addon options, then restart.

### Log Locations

- `/data/logs/` - Server logs (inside addon)
- Accessible via Home Assistant SSH add-on

## Troubleshooting

### Server Won't Start

1. Check addon logs for errors
2. Verify port 6567 is not in use: `netstat -tuln | grep 6567`
3. Check Java installation: `which java`
4. Try restarting the addon

### Players Can't Connect

1. Verify port forwarding if on remote network
2. Check firewall allows UDP port 6567
3. Confirm server is running: `curl http://homeassistant.local:5000/api/server`
4. Restart server: `curl -X POST http://homeassistant.local:5000/api/server/restart`

### API Connection Issues

1. Verify API key is correct
2. Check API is running: `curl http://homeassistant.local:5000/health`
3. Check authorization header format: `Authorization: Bearer YOUR_KEY`
4. Ensure network connectivity between Home Assistant and addon

### High Memory Usage

1. Reduce `max_players`
2. Lower log level to `warning`
3. Check for player/zombie accumulation
4. Restart server periodically

## Performance Tuning

### CPU Usage

- Reduce max players if CPU is consistently high
- Lower Java heap size if memory-constrained: `-Xmx1G`

### Memory Usage

- Default: `-Xmx2G` (2GB heap)
- For low-memory systems: `-Xmx1G` or `-Xmx512M`
- Monitor with: `docker stats`

### Network Usage

- Monitor player count vs bandwidth
- Consider limiting max players based on available bandwidth

## Support & Contributing

- **Issues**: https://github.com/Moozzuzz/mindustry-server-addon/issues
- **Discussions**: https://github.com/Moozzuzz/mindustry-server-addon/discussions
- **Contributing**: See CONTRIBUTING.md

## License

MIT License - See LICENSE.md
