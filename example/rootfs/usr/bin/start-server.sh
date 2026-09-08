#!/command/with-contenv bashio
# shellcheck shell=bash
# ==============================================================================
# Mindustry Server Addon - Main Startup Script
# ==============================================================================

set -e

# Source bashio helpers
BASHIO_LOG_LEVEL=$(bashio::config 'log_level')
export BASHIO_LOG_LEVEL

bashio::log.info "========================================"
bashio::log.info "Mindustry Server Addon - Starting"
bashio::log.info "========================================"

# ============================================================================
# Configuration
# ============================================================================

PORT=$(bashio::config 'port')
SERVER_NAME=$(bashio::config 'server_name')
MAX_PLAYERS=$(bashio::config 'max_players')
PVP=$(bashio::config 'pvp')
STRICT=$(bashio::config 'strict')
AUTO_RESTART=$(bashio::config 'auto_restart')
RESTART_HOUR=$(bashio::config 'restart_hour')

bashio::log.info "Configuration loaded:"
bashio::log.info "  Port: ${PORT}"
bashio::log.info "  Server Name: ${SERVER_NAME}"
bashio::log.info "  Max Players: ${MAX_PLAYERS}"
bashio::log.info "  PvP Mode: ${PVP}"
bashio::log.info "  Strict Mode: ${STRICT}"
bashio::log.info "  Auto Restart: ${AUTO_RESTART}"
bashio::log.info "  Restart Hour: ${RESTART_HOUR}"

# ============================================================================
# Environment Setup
# ============================================================================

export PORT
export SERVER_NAME
export MAX_PLAYERS
export PVP
export STRICT
export AUTO_RESTART
export RESTART_HOUR
export LOG_LEVEL="${BASHIO_LOG_LEVEL}"

# Set API port (always 5000 internally)
export API_PORT=5000
export API_HOST="0.0.0.0"

# Generate or load API key
API_KEY_FILE="/data/api_key"
if [ ! -f "${API_KEY_FILE}" ]; then
    bashio::log.notice "Generating API key..."
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "${API_KEY}" > "${API_KEY_FILE}"
    chmod 600 "${API_KEY_FILE}"
else
    API_KEY=$(cat "${API_KEY_FILE}")
fi

export API_KEY
bashio::log.notice "API Key: ${API_KEY:0:10}... (stored in /data/api_key)"

# ============================================================================
# Verify Java Installation
# ============================================================================

if ! command -v java &> /dev/null; then
    bashio::log.error "Java is not installed!"
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -n 1)
bashio::log.info "Java available: ${JAVA_VERSION}"

# ============================================================================
# Verify Mindustry Server JAR
# ============================================================================

if [ ! -f /mindustry/server.jar ]; then
    bashio::log.error "Mindustry server JAR not found at /mindustry/server.jar"
    bashio::log.info "Attempting to download..."
    cd /mindustry
    if ! wget -q https://github.com/Anuken/Mindustry/releases/download/v146/server-release.jar -O server.jar; then
        bashio::log.error "Failed to download Mindustry server"
        exit 1
    fi
    chmod +x server.jar
fi

bashio::log.info "Mindustry server JAR verified at /mindustry/server.jar"
ls -lh /mindustry/server.jar

# ============================================================================
# Create Data Directories
# ============================================================================

mkdir -p /data/maps
mkdir -p /data/config
mkdir -p /data/logs

bashio::log.info "Data directories prepared"

# ============================================================================
# Start Python API Server
# ============================================================================

bashio::log.info "Starting API server on ${API_HOST}:${API_PORT}..."

cd /app
export PYTHONUNBUFFERED=1

python3 server.py &
API_PID=$!
bashio::log.info "API server started (PID: ${API_PID})"

# ============================================================================
# Wait for API Server Ready
# ============================================================================

bashio::log.info "Waiting for API server to be ready..."
for i in {1..60}; do
    if curl -sf http://localhost:${API_PORT}/health > /dev/null 2>&1; then
        bashio::log.notice "✓ API server is ready"
        break
    fi

    if ! kill -0 ${API_PID} 2>/dev/null; then
        bashio::log.error "✗ API server process died"
        exit 1
    fi

    if [ $i -eq 60 ]; then
        bashio::log.error "✗ API server failed to start after 60 seconds"
        exit 1
    fi

    bashio::log.debug "Waiting for API server... (${i}/60)"
    sleep 1
done

# ============================================================================
# Start Mindustry Server
# ============================================================================

bashio::log.notice "========================================"
bashio::log.notice "Starting Mindustry game server"
bashio::log.notice "========================================"

cd /mindustry

# Build Java command
JAVA_CMD="java -Xmx2G -server -jar server.jar -port ${PORT} -name '${SERVER_NAME}' -players ${MAX_PLAYERS}"

if [ "${PVP}" = "true" ]; then
    JAVA_CMD="${JAVA_CMD} -pvp"
fi

if [ "${STRICT}" = "true" ]; then
    JAVA_CMD="${JAVA_CMD} -strict"
fi

bashio::log.info "Executing: ${JAVA_CMD}"

# Execute Mindustry server
eval "${JAVA_CMD}" 2>&1 | while IFS= read -r line; do
    bashio::log.info "[Mindustry] ${line}"
done &

SERVER_PID=$!
bashio::log.notice "Mindustry server started (PID: ${SERVER_PID})"

# ============================================================================
# Signal Handlers
# ============================================================================

trap "bashio::log.info 'Received SIGTERM, shutting down...'; kill ${SERVER_PID} 2>/dev/null || true; kill ${API_PID} 2>/dev/null || true; exit 0" SIGTERM SIGINT

# ============================================================================
# Monitor Processes
# ============================================================================

bashio::log.info "========================================"
bashio::log.info "Services running:"
bashio::log.info "  API Server (PID: ${API_PID})"
bashio::log.info "  Mindustry Server (PID: ${SERVER_PID})"
bashio::log.info "========================================"
bashio::log.notice "✓ All services started successfully"

# Keep running and monitor child processes
while true; do
    # Check if processes are still running
    if ! kill -0 ${SERVER_PID} 2>/dev/null; then
        bashio::log.error "✗ Mindustry server process died (PID: ${SERVER_PID})"
        bashio::log.notice "Attempting to restart server..."
        # Could implement restart logic here
        break
    fi

    if ! kill -0 ${API_PID} 2>/dev/null; then
        bashio::log.error "✗ API server process died (PID: ${API_PID})"
        bashio::log.notice "Restarting API server..."
        cd /app
        python3 server.py &
        API_PID=$!
        bashio::log.notice "API server restarted (PID: ${API_PID})"
    fi

    sleep 5
done

# Cleanup on exit
bashio::log.info "Shutting down..."
kill ${SERVER_PID} 2>/dev/null || true
kill ${API_PID} 2>/dev/null || true
wait 2>/dev/null || true
bashio::log.notice "Mindustry Server Addon stopped"
