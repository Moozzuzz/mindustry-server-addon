#!/bin/bash
# Health check script for Mindustry Server addon

set -e

# Check API server health
API_PORT=${API_PORT:-5000}
if ! curl -sf http://localhost:${API_PORT}/health > /dev/null 2>&1; then
    echo "API server is not responding to health checks"
    exit 1
fi

# Check Mindustry server status via API
if ! curl -sf http://localhost:${API_PORT}/api/server > /dev/null 2>&1; then
    echo "Mindustry server status check failed"
    exit 1
fi

# Check if processes are running
if ! pgrep -f 'python3 server.py' > /dev/null 2>&1; then
    echo "API server process not found"
    exit 1
fi

if ! pgrep -f 'java.*server.jar' > /dev/null 2>&1; then
    echo "Mindustry server process not found"
    exit 1
fi

echo "Health check passed"
exit 0
