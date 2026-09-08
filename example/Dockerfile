ARG BUILD_FROM=ghcr.io/hassio-addons/base:21.0.3
FROM ${BUILD_FROM}

# Install Java and dependencies
RUN apk add --no-cache \
    openjdk11-jre=11.0.20_p8-r0 \
    curl=8.5.0-r0 \
    wget=1.25.0-r3 \
    netcat-openbsd=1.10-r1 \
    python3=3.11.8-r0 \
    py3-pip=23.3.1-r0 \
    coreutils=9.11-r0

# Create app directory
RUN mkdir -p /app
WORKDIR /app

# Copy root filesystem
COPY rootfs /

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Download Mindustry server
RUN mkdir -p /mindustry && \
    cd /mindustry && \
    wget -q https://github.com/Anuken/Mindustry/releases/download/v146/server-release.jar -O server.jar && \
    chmod +x server.jar

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
