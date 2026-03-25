#!/bin/bash
# Wait for Docker and start Redmine

echo "=========================================="
echo "Waiting for Docker to be available..."
echo "=========================================="

# Check for Docker
MAX_WAIT=300  # 5 minutes
WAIT_INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        echo "✓ Docker is running!"
        echo ""
        break
    fi
    
    if [ $ELAPSED -eq 0 ]; then
        echo "Docker is not running yet..."
        echo "Please:"
        echo "  1. Install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
        echo "  2. Open Docker Desktop from Applications"
        echo "  3. Wait for it to start"
        echo ""
        echo "This script will check every 5 seconds..."
    fi
    
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
    echo -n "."
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "❌ Timeout: Docker did not start within 5 minutes"
    exit 1
fi

echo ""
echo "Starting Redmine..."
cd "$(dirname "$0")"
docker-compose up -d

echo ""
echo "Waiting for Redmine to be ready..."
sleep 10

# Check status
if docker ps | grep -q redmine; then
    echo "✓ Redmine is starting!"
    echo ""
    echo "Redmine will be available at: http://localhost:3000"
    echo ""
    echo "Default login:"
    echo "  Username: admin"
    echo "  Password: admin"
    echo ""
    echo "To view logs: docker-compose logs -f redmine"
    echo "To stop: docker-compose down"
else
    echo "⚠ Checking Redmine status..."
    docker-compose ps
    echo ""
    echo "View logs: docker-compose logs redmine"
fi


