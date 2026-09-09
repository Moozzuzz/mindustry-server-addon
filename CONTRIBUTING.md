# Contributing to Mindustry Server Addon

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive. We welcome all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug already exists: [Issues](https://github.com/Moozzuzz/mindustry-server-addon/issues)
2. Create a new issue with:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (Home Assistant version, OS, etc.)
   - Logs (use code blocks)

### Suggesting Features

1. Check [Discussions](https://github.com/Moozzuzz/mindustry-server-addon/discussions)
2. Create a new discussion with:
   - Feature description
   - Use case/motivation
   - Possible implementation approach

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Make your changes:
   - Follow existing code style
   - Add comments for complex logic
   - Keep commits atomic and descriptive

4. Test your changes:
   ```bash
   docker-compose up -d
   docker-compose logs -f
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Open a Pull Request with:
   - Clear title and description
   - Reference any related issues
   - Explain what changed and why

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Git

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/mindustry-server-addon
cd mindustry-server-addon

# Build and run
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f

# Get API key
docker exec mindustry-server cat /data/api_key

# Test API
API_KEY=$(docker exec mindustry-server cat /data/api_key)
curl -H "Authorization: Bearer ${API_KEY}" \
  http://localhost:5000/api/server
```

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Use async/await for I/O
- Add docstrings to functions

### Bash

- Use `#!/bin/bash`
- Follow shellcheck recommendations
- Use bashio functions for logging
- Quote variables: `"${VAR}"`

## Testing

### Manual Testing

1. **API Endpoints**
   ```bash
   curl http://localhost:5000/health
   ```

2. **Player Connection**
   - Launch Mindustry
   - Connect to localhost:6567
   - Verify player appears in API

3. **WebSocket Events**
   ```bash
   wscat -c ws://localhost:5000/ws
   ```

## Documentation

- Update README.md for user-facing changes
- Update DOCS.md for feature documentation
- Add docstrings to all functions
- Keep examples current and tested

## Commit Messages

Use clear, descriptive commit messages:

```
fix: resolve API timeout issue

The API was timing out after 5 seconds. Changed timeout to 10 seconds
and added retry logic with exponential backoff.

Fixes #123
```

## Review Process

1. A maintainer will review your PR
2. Provide feedback or request changes
3. Update your PR with changes
4. Once approved, it will be merged

## Questions?

- Open a [Discussion](https://github.com/Moozzuzz/mindustry-server-addon/discussions)
- Comment on an Issue
- Contact the maintainer

Thank you for contributing! 🎉
