#!/bin/bash
# Production startup script for self-managed DB-RAG

set -e

echo "🚀 Starting DB-RAG Production Environment"
echo "========================================"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.production.example .env
    echo "📝 Please edit .env file with your configuration:"
    echo "   - OPENAI_API_KEY"
    echo "   - DB_PASSWORD"
    echo "   - REDIS_PASSWORD (optional)"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Check if OPENAI_API_KEY is set
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" == "your_openai_api_key_here" ]; then
    echo "❌ OPENAI_API_KEY not set in .env file"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Build images
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.production.yml build --parallel

echo "✅ Build complete"
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.production.yml up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Health checks
echo ""
echo "🏥 Running health checks..."

# Check postgres
echo -n "  PostgreSQL: "
if docker-compose -f docker-compose.production.yml exec -T postgres pg_isready -U dbrag_user &>/dev/null; then
    echo "✅"
else
    echo "❌"
fi

# Check Redis
echo -n "  Redis: "
if docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping &>/dev/null; then
    echo "✅"
else
    echo "❌"
fi

# Check API
echo -n "  API: "
sleep 5  # Give API more time to start
if curl -sf http://localhost:8000/health &>/dev/null; then
    echo "✅"
else
    echo "❌ (may need more time to start)"
fi

# Check Workers
echo -n "  Workers: "
if curl -sf http://localhost:8000/api/jobs/test &>/dev/null; then
    echo "✅"
else
    echo "❌ (may need more time to start)"
fi

echo ""
echo "========================================"
echo "✅ DB-RAG Production Environment Started!"
echo "========================================"
echo ""
echo "📊 Service URLs:"
echo "  - API:        http://localhost:8000"
echo "  - Frontend:   http://localhost:3000"
echo "  - Flower:     http://localhost:5555 (admin/admin)"
echo "  - Grafana:    http://localhost:3001 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo ""
echo "📝 Next steps:"
echo "  1. Initialize database: docker-compose -f docker-compose.production.yml exec api python upgrade_to_hnsw.py"
echo "  2. Check logs: docker-compose -f docker-compose.production.yml logs -f"
echo "  3. View metrics: http://localhost:3001"
echo ""
echo "🛑 To stop: docker-compose -f docker-compose.production.yml down"
echo ""
