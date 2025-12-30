#!/bin/bash

# DB-RAG Full Stack Setup Script

set -e

echo "======================================"
echo "  DB-RAG Full Stack Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file${NC}"
        echo -e "${YELLOW}Please edit .env and add your OPENAI_API_KEY${NC}"
        echo ""
        read -p "Press Enter to continue once you've added your API key..."
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Verify OpenAI API key is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo -e "${RED}Error: OPENAI_API_KEY not set in .env file${NC}"
    echo "Please edit .env and add your OpenAI API key"
    exit 1
fi

echo -e "${GREEN}✓ Environment configuration verified${NC}"
echo ""

# Stop and remove existing containers
echo "Stopping existing containers (if any)..."
docker-compose down -v 2>/dev/null || true
echo ""

# Build and start services
echo "======================================"
echo "  Building and Starting Services"
echo "======================================"
echo ""

docker-compose up --build -d

echo ""
echo "Waiting for services to be healthy..."
echo ""

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL"
for i in {1..30}; do
    if docker exec dbrag-postgres pg_isready -U postgres -d pagila &>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for backend
echo -n "Waiting for Backend API"
for i in {1..30}; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for frontend
echo -n "Waiting for Frontend"
for i in {1..60}; do
    if curl -s http://localhost:3000 &>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "======================================"
echo "  Setup Complete!"
echo "======================================"
echo ""
echo -e "${GREEN}All services are running!${NC}"
echo ""
echo "Access the application:"
echo -e "  Frontend:  ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo "Database connection:"
echo "  Host: localhost"
echo "  Port: 5433"
echo "  Database: pagila"
echo "  User: postgres"
echo "  Password: postgres"
echo ""
echo "Useful commands:"
echo "  View logs:        docker-compose logs -f"
echo "  Stop services:    docker-compose down"
echo "  Restart services: docker-compose restart"
echo ""
echo -e "${YELLOW}Note: The first startup may take a few minutes to load the Pagila database${NC}"
echo ""
