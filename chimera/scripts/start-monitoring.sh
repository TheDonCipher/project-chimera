#!/bin/bash
# Start Chimera bot with monitoring stack

set -e

echo "🚀 Starting Chimera bot with monitoring stack..."
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed"
    echo "Please install docker-compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Copying .env.example to .env..."
    cp ../.env.example ../.env
    echo "Please edit .env with your actual values before running the bot"
    exit 1
fi

# Start services
echo "Starting services..."
cd ..
docker-compose --profile monitoring up -d

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📊 Access the dashboards:"
echo "  - Grafana:    http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo "  - Bot Metrics: http://localhost:8000/metrics"
echo "  - Bot Health:  http://localhost:8000/health"
echo ""
echo "📝 View logs:"
echo "  docker logs -f chimera-bot"
echo ""
echo "🛑 Stop services:"
echo "  docker-compose --profile monitoring down"
echo ""
