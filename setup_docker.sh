#!/bin/bash

echo "================================================"
echo "DB-RAG Docker Setup and Testing Script"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your OPENAI_API_KEY"
    echo ""
fi

# Update .env for Docker if needed
if grep -q "DB_HOST=localhost" .env; then
    echo "✓ .env configured for Docker"
else
    echo "Updating .env for Docker setup..."
    sed -i.bak 's/DB_HOST=.*/DB_HOST=localhost/' .env
    sed -i.bak 's/DB_PORT=.*/DB_PORT=5433/' .env
    sed -i.bak 's/DB_NAME=.*/DB_NAME=pagila/' .env
    sed -i.bak 's/DB_USER=.*/DB_USER=postgres/' .env
    sed -i.bak 's/DB_PASSWORD=.*/DB_PASSWORD=postgres/' .env
    rm .env.bak
fi

echo ""
echo "================================================"
echo "Step 1: Starting Docker containers"
echo "================================================"
echo ""

# Stop existing containers
docker-compose down

# Start fresh
echo "Building and starting containers..."
docker-compose up -d --build

echo ""
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for database to be healthy
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec -T postgres pg_isready -U postgres -d pagila > /dev/null 2>&1; then
        echo "✓ PostgreSQL is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "Waiting... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL failed to start"
    docker-compose logs postgres
    exit 1
fi

echo ""
echo "================================================"
echo "Step 2: Verifying Database Setup"
echo "================================================"
echo ""

# Check Pagila tables
echo "Checking Pagila tables..."
table_count=$(docker-compose exec -T postgres psql -U postgres -d pagila -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')

if [ "$table_count" -gt 15 ]; then
    echo "✓ Pagila database loaded successfully ($table_count tables)"
else
    echo "❌ Pagila database not loaded properly (only $table_count tables found)"
    exit 1
fi

# Check pgvector extension
echo "Checking pgvector extension..."
pgvector_check=$(docker-compose exec -T postgres psql -U postgres -d pagila -t -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | tr -d ' ')

if [ "$pgvector_check" == "vector" ]; then
    echo "✓ pgvector extension enabled"
else
    echo "❌ pgvector extension not found"
    exit 1
fi

# Check DB-RAG tables
echo "Checking DB-RAG tables..."
dbrag_tables=$(docker-compose exec -T postgres psql -U postgres -d pagila -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('table_metadata_catalog', 'company_documents');" | tr -d ' ')

if [ "$dbrag_tables" == "2" ]; then
    echo "✓ DB-RAG tables created"
else
    echo "❌ DB-RAG tables not created"
    exit 1
fi

# Check sample documents
echo "Checking sample documents..."
doc_count=$(docker-compose exec -T postgres psql -U postgres -d pagila -t -c "SELECT COUNT(*) FROM company_documents;" | tr -d ' ')

if [ "$doc_count" -gt 0 ]; then
    echo "✓ Sample documents loaded ($doc_count documents)"
else
    echo "⚠️  No sample documents found"
fi

echo ""
echo "================================================"
echo "Step 3: Database Connection Info"
echo "================================================"
echo ""
echo "Host: localhost"
echo "Port: 5433"
echo "Database: pagila"
echo "User: postgres"
echo "Password: postgres"
echo ""
echo "Connect with: psql -h localhost -p 5433 -U postgres -d pagila"
echo ""

echo "================================================"
echo "Step 4: Quick Test"
echo "================================================"
echo ""

# Show some sample data
echo "Sample Pagila data:"
docker-compose exec -T postgres psql -U postgres -d pagila -c "SELECT COUNT(*) as total_customers FROM customer;"
docker-compose exec -T postgres psql -U postgres -d pagila -c "SELECT COUNT(*) as total_films FROM film;"
docker-compose exec -T postgres psql -U postgres -d pagila -c "SELECT COUNT(*) as total_rentals FROM rental;"

echo ""
echo "================================================"
echo "✓ Docker Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Make sure your OPENAI_API_KEY is set in .env"
echo "2. Run the application:"
echo "   python examples/cli.py"
echo ""
echo "3. Or run end-to-end tests:"
echo "   python test_e2e.py"
echo ""
echo "4. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "5. Stop everything:"
echo "   docker-compose down"
echo ""
