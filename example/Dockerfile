ARG BUILD_FROM=ghcr.io/hassio-addons/base:21.0.3
FROM ${BUILD_FROM}

# Install Java and system dependencies
RUN apk add --no-cache \
    openjdk11-jre=11.0.20_p8-r0 \
    curl=8.5.0-r0 \
    wget=1.25.0-r3 \
    netcat-openbsd=1.10-r1 \
    python3=3.11.8-r0 \
    py3-pip=23.3.1-r0 \
    coreutils=9.11-r0 \
    bash=5.2.21-r0

# Create app directory structure
RUN mkdir -p /app /mindustry /data /config
WORKDIR /app

# Copy Python requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/

# Download Mindustry server
RUN mkdir -p /mindustry && \
    cd /mindustry && \
    wget -q https://github.com/Anuken/Mindustry/releases/download/v146/server-release.jar -O server.jar && \
    chmod +x server.jar && \
    # Verify download
    if [ ! -f server.jar ]; then echo "Failed to download server"; exit 1; fi

# Copy root filesystem (S6 overlay, scripts, etc.)
COPY rootfs /

# Make scripts executable
RUN chmod +x /usr/bin/start-server.sh && \
    chmod +x /etc/s6-overlay/s6-rc.d/*/run 2>/dev/null || true

# Create non-root user for running the server
RUN addgroup -g 1000 mindustry && \
    adduser -u 1000 -G mindustry -h /data -s /bin/bash -D mindustry && \
    chown -R mindustry:mindustry /app /mindustry /data

# Set permissions
RUN chmod 755 /app && \
    chmod 755 /mindustry

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="Moozzuzz" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Mindustry Server Addon" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to non-root user
USER mindustry

# Expose ports
EXPOSE 5000 6567

# Volume for persistent data
VOLUME [ "/data" ]

# Entrypoint
ENTRYPOINT [ "/init" ]
