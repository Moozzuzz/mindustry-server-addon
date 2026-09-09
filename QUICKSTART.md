# Quick Start Guide

## 🚀 Installation (5 minutes)

### Step 1: Add Repository to Home Assistant

1. Open Home Assistant
2. Go to **Settings** → **Add-ons** → **Add-on Store** (bottom right)
3. Click menu (⋮) → **Repositories**
4. Paste: `https://github.com/Moozzuzz/mindustry-server-addon`
5. Click **Create**
6. Close the dialog

### Step 2: Install the Addon

1. Click **Refresh** (if needed)
2. Search for **"Mindustry Server"**
3. Click on it
4. Click **Install**
5. Wait for completion (~2 minutes)

### Step 3: Configure Basic Settings

1. Click **Configuration**
2. Adjust if needed (defaults are fine):
   - Server Name: "My Mindustry Server"
   - Max Players: 10
   - Port: 6567
3. Click **Save**

### Step 4: Start the Addon

1. Click **Start**
2. Click **Logs** to watch startup
3. Wait for: `✓ All services started successfully`
4. Takes ~30-60 seconds

### Step 5: Get Your API Key

1. Open SSH add-on (or terminal)
2. Run:
   ```bash
   docker exec addon_mindustry_server cat /data/api_key
   ```
3. **Save this key** - you'll need it!

## 🎮 Playing

### Connect to Your Server

1. Launch Mindustry
2. Go to **Multiplayer**
3. Click **Add Server**
4. Enter:
   - **Name**: Your server name
   - **IP/Host**: Your Home Assistant IP
   - **Port**: 6567 (default)
5. Click **Add**
6. Click to join!

## 📊 Monitor in Home Assistant

### Add a Status Sensor

Add this to your `configuration.yaml`:

```yaml
sensor:
  - platform: rest
    name: Mindustry Status
    resource: http://homeassistant.local:5000/api/server
    headers:
      Authorization: "Bearer YOUR_API_KEY_HERE"
    json_attributes:
      - players_online
      - wave
      - map_name
    value_template: "{{ value_json.status }}"
    scan_interval: 60
```

## 🔧 Common Tasks

### Check Server Status

```bash
API_KEY=$(docker exec addon_mindustry_server cat /data/api_key)
curl -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/server | jq .
```

### Restart Server

```bash
API_KEY=$(docker exec addon_mindustry_server cat /data/api_key)
curl -X POST -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/server/restart
```

### Send Server Message

```bash
API_KEY=$(docker exec addon_mindustry_server cat /data/api_key)
curl -X POST -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"command": "say Server restarting soon!"}' \
  http://localhost:5000/api/commands
```

### List Connected Players

```bash
API_KEY=$(docker exec addon_mindustry_server cat /data/api_key)
curl -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/server | jq '.players_online'
```

## 🆘 Troubleshooting

### Server won't start?

1. Check logs:
   ```bash
   docker logs addon_mindustry_server -f
   ```

2. Common issues:
   - Port 6567 already in use
   - Insufficient memory

3. Try restarting:
   ```bash
   docker restart addon_mindustry_server
   ```

### Can't connect as player?

1. Verify server is running:
   ```bash
   curl -H "Authorization: Bearer $(docker exec addon_mindustry_server cat /data/api_key)" \
     http://localhost:5000/api/server
   ```

2. Check port is open:
   ```bash
   netstat -tuln | grep 6567
   ```

3. Check firewall allows UDP 6567

### API key not working?

1. Get fresh key:
   ```bash
   docker exec addon_mindustry_server cat /data/api_key
   ```

2. Check header format:
   ```
   Authorization: Bearer YOUR_KEY_HERE
   ```

3. Verify API is running:
   ```bash
   curl http://localhost:5000/health
   ```

## 📚 Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Set up automations**: See [README.md](README.md#home-assistant-integration)
3. **Monitor with WebSocket**: [DOCKER_DEV_GUIDE.md](DOCKER_DEV_GUIDE.md)
4. **Join the community**: [GitHub Discussions](https://github.com/Moozzuzz/mindustry-server-addon/discussions)

## 💡 Tips

- **Auto-restart**: Enable in config to restart daily at 3 AM
- **Debug logs**: Set `log_level: debug` for troubleshooting
- **Multiple servers**: Run separate addon instances with different ports
- **Mobile app**: Use Home Assistant app to control from anywhere
- **Notifications**: Add automations to notify when players join

---

**Happy gaming! 🎮**
