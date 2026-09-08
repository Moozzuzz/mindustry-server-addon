# Mindustry Server Addon Docker Development Guide

## Quick Start

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f mindustry-server

# Stop the container
docker-compose down
```

## Configuration

Edit the `environment` section in `docker-compose.yml`:

```yaml
environment:
  - PORT=6567                    # Mindustry server port
  - SERVER_NAME=My Server        # Display name
  - MAX_PLAYERS=10               # Max concurrent players
  - LOG_LEVEL=info               # debug, info, warning, error
  - PVP=false                    # Enable PvP mode
  - STRICT=false                 # Strict anti-cheat
  - AUTO_RESTART=true            # Auto restart at specific hour
  - RESTART_HOUR=3               # Hour of day to restart (0-23)
```

## API Access

### Health Check
```bash
curl http://localhost:5000/health
```

### Get Server Status
```bash
API_KEY="your-key-from-/data/api_key"
curl -H "Authorization: Bearer ${API_KEY}" http://localhost:5000/api/server
```

### Start Server
```bash
curl -X POST -H "Authorization: Bearer ${API_KEY}" http://localhost:5000/api/server/start
```

### Restart Server
```bash
curl -X POST -H "Authorization: Bearer ${API_KEY}" http://localhost:5000/api/server/restart
```

### Execute Console Command
```bash
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"command": "say Hello world"}' \
  http://localhost:5000/api/commands
```

## Data Persistence

Data is stored in Docker volumes:
- `mindustry_data`: Configuration, API keys, server data
- `mindustry_maps`: Custom maps
- `mindustry_logs`: Server logs

Retrieve API key:
```bash
docker exec mindustry-server cat /data/api_key
```

## Port Mappings

- **6567 (UDP)**: Mindustry game server
- **5000 (TCP)**: REST API + WebSocket

## Monitoring

### Container Health
```bash
docker ps  # Check STATUS column for health status
```

### Real-time Logs
```bash
docker-compose logs -f
```

### WebSocket Events
```bash
wscat -c ws://localhost:5000/ws
```

## Troubleshooting

### API Server Not Starting
```bash
docker-compose logs mindustry-server | grep "API server"
```

### Mindustry Server Crashes
```bash
docker-compose logs mindustry-server | grep "Mindustry"
```

### Port Already in Use
```bash
# Change ports in docker-compose.yml
ports:
  - "6568:6567/udp"   # Use 6568 instead
  - "5001:5000"       # Use 5001 instead
```

### Check Container Resources
```bash
docker stats mindustry-server
```

## Production Deployment

### 1. Generate Strong API Key
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Update Configuration
- Set `LOG_LEVEL=warning` to reduce log volume
- Adjust `MAX_PLAYERS` based on available resources
- Enable `AUTO_RESTART=true` for stability

### 3. Configure Reverse Proxy
```nginx
upstream mindustry_api {
    server localhost:5000;
}

server {
    listen 443 ssl http2;
    server_name mindustry.example.com;

    location / {
        proxy_pass http://mindustry_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Authorization $http_authorization;
    }
}
```

### 4. Set Up Monitoring
```bash
# Monitor container in Prometheus
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

## Home Assistant Integration

### Add to Home Assistant

1. Install the addon from your Home Assistant UI
2. Configure options in addon settings
3. Start the addon
4. Get the API key:
   ```bash
   docker exec mindustry-server cat /data/api_key
   ```

### Create REST Sensor
```yaml
sensor:
  - platform: rest
    resource: http://homeassistant.local:5000/api/server
    name: Mindustry Server
    headers:
      Authorization: "Bearer YOUR_API_KEY_HERE"
    json_attributes:
      - players_online
      - wave
      - map_name
    value_template: "{{ value_json.status }}"
    scan_interval: 30
```

### Create WebSocket Listener
```yaml
automation:
  - alias: Mindustry Player Join
    trigger:
      platform: mqtt
      topic: mindustry/events/player_joined
    action:
      service: persistent_notification.create
      data:
        title: "Player Joined"
        message: "{{ trigger.payload_json.player_name }} joined the server"
```
