
#!/usr/bin/env bash

set -Eeuo pipefail

echo "===================================="
echo " Task Manager API - Deployment"
echo "===================================="

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed or not in PATH."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker Desktop is not running."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose plugin is unavailable."
    exit 1
fi

if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    echo "ERROR: Run this script from the project directory."
    exit 1
fi

echo "[1/3] Building the API image..."
docker compose build api

echo "[2/3] Starting the containers..."
docker compose up -d

echo "[3/3] Checking container status..."
docker compose ps

echo ""
echo "API address: http://localhost:5000"
echo "Health check: http://localhost:5000/health"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
