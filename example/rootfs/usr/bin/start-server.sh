#!/command/with-contenv bashio
# shellcheck shell=bash
# ==============================================================================
# Mindustry Server Addon - Start Script
# ==============================================================================

set -e

BASHIO_LOG_LEVEL=$(bashio::config 'log_level')
export BASHIO_LOG_LEVEL

bashio::log.info "Starting Mindustry Server..."

# Source configuration
PORT=$(bashio::config 'port')
SERVER_NAME=$(bashio::config 'server_name')
MAX_PLAYERS=$(bashio::config 'max_players')
PVP=$(bashio::config 'pvp')
STRICT=$(bashio::config 'strict')

bashio::log.info "Configuration:"
bashio::log.info "  Port: ${PORT}"
bashio::log.info "  Server Name: ${SERVER_NAME}"
bashio::log.info "  Max Players: ${MAX_PLAYERS}"
bashio::log.info "  PvP: ${PVP}"
bashio::log.info "  Strict: ${STRICT}"

# Start Python API server in background
bashio::log.info "Starting API server..."
cd /app
python3 /app/server.py &
API_PID=$!
bashio::log.info "API server PID: ${API_PID}"

# Wait for API to be ready
for i in {1..30}; do
    if nc -z localhost 5000 2>/dev/null; then
        bashio::log.info "API server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        bashio::log.error "API server failed to start"
        exit 1
    fi
    sleep 1
done

# Start Mindustry server
bashio::log.info "Starting Mindustry server process..."
cd /mindustry
java -Xmx2G -server -jar server.jar \
    -port "${PORT}" \
    -name "${SERVER_NAME}" \
    -players "${MAX_PLAYERS}" \
    $([ "${PVP}" = "true" ] && echo "-pvp") \
    $([ "${STRICT}" = "true" ] && echo "-strict") \
    2>&1 | tee /dev/stderr |
    while IFS= read -r line; do
        echo "[Mindustry] $line"
    done &

SERVER_PID=$!
bashio::log.info "Mindustry server started with PID: ${SERVER_PID}"

# Wait for signals
wait
