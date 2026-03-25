#!/bin/bash
# Start Redmine using Docker

echo "=========================================="
echo "Starting Redmine with Docker"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo ""
    echo "Please install Docker Desktop:"
    echo "  1. Visit: https://www.docker.com/products/docker-desktop/"
    echo "  2. Download Docker Desktop for Mac (Apple Silicon)"
    echo "  3. Install and start Docker Desktop"
    echo "  4. Then run this script again"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running!"
    echo ""
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "✓ Docker is installed and running"
echo ""

# Start Redmine
echo "Starting Redmine containers..."
docker-compose up -d

echo ""
echo "Waiting for Redmine to be ready..."
sleep 5

# Check if containers are running
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
    echo "⚠ Redmine may still be starting. Check logs with:"
    echo "  docker-compose logs redmine"
fi


