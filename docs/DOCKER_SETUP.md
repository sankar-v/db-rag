# Docker Setup Guide

## Prerequisites

- Docker Desktop installed and running
- Docker Compose v2.0+
- At least 2GB free disk space

## Quick Start

1. **Start the environment**:
```bash
docker-compose up -d
```

This will:
- Build and start PostgreSQL 16 with pgvector extension
- Download and load the Pagila sample database
- Create DB-RAG tables (metadata catalog and documents)
- Load sample policy documents
- Set up the application container

2. **Check status**:
```bash
docker-compose ps
```

3. **View logs**:
```bash
# All services
docker-compose logs -f

# Just database
docker-compose logs -f postgres
```

4. **Connect to database**:
```bash
# Using psql
docker-compose exec postgres psql -U postgres -d pagila

# From host machine (if psql installed)
psql -h localhost -U postgres -d pagila
```

## Environment Setup

Update your `.env` file for Docker:

```bash
# Database Configuration (Docker)
DB_HOST=localhost  # or 'postgres' if running app in Docker
DB_PORT=5432
DB_NAME=pagila
DB_USER=postgres
DB_PASSWORD=postgres
DB_SCHEMA=public

# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
```

## Running the Application

### Option 1: Run locally, connect to Docker DB

```bash
# Make sure Docker containers are running
docker-compose up -d postgres

# Install dependencies
pip install -r requirements.txt

# Run the CLI
python examples/cli.py

# Or run end-to-end tests
python test_e2e.py
```

### Option 2: Run everything in Docker

```bash
# Start all services
docker-compose up -d

# Run CLI in container
docker-compose exec app python examples/cli.py

# Run tests in container
docker-compose exec app python test_e2e.py
```

## Pagila Database Schema

The Pagila database is a sample DVD rental database with the following tables:

### Core Tables
- **actor**: Actor information
- **film**: Film/movie details
- **category**: Film categories (Action, Comedy, etc.)
- **customer**: Customer information
- **rental**: Rental transactions
- **payment**: Payment records
- **inventory**: Film inventory by store
- **store**: Store locations
- **staff**: Staff members

### Relationship Tables
- **film_actor**: Films and their actors
- **film_category**: Films and their categories
- **address**, **city**, **country**: Location data

### Sample Queries

You can ask questions like:
- "How many customers do we have?"
- "What are the most popular film categories?"
- "Show me top customers by rental count"
- "Which films have been rented the most?"
- "What's our total rental revenue?"

## Database Structure

```
pagila database
├── Pagila tables (16 tables)
│   ├── actor, film, category
│   ├── customer, rental, payment
│   └── inventory, store, staff
├── DB-RAG tables
│   ├── table_metadata_catalog (for table discovery)
│   └── company_documents (for vector search)
└── pgvector extension
```

## Useful Commands

### Database Management

```bash
# Stop containers
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Rebuild containers
docker-compose up -d --build

# Access PostgreSQL shell
docker-compose exec postgres psql -U postgres -d pagila
```

### Application Management

```bash
# View app logs
docker-compose logs -f app

# Restart app
docker-compose restart app

# Run a one-off command
docker-compose run --rm app python test_e2e.py
```

### Database Queries

```sql
-- Check Pagila tables
\dt

-- Count customers
SELECT COUNT(*) FROM customer;

-- View sample documents
SELECT content, metadata FROM company_documents;

-- Check metadata catalog
SELECT table_name, table_description FROM table_metadata_catalog;
```

## Troubleshooting

### Port 5432 already in use

If you have PostgreSQL running locally:

```bash
# Stop local PostgreSQL (macOS)
brew services stop postgresql

# Or change the port in docker-compose.yml
ports:
  - "5433:5432"  # Use port 5433 instead

# Then update .env
DB_PORT=5433
```

### Database initialization failed

```bash
# Check logs
docker-compose logs postgres

# Restart with fresh database
docker-compose down -v
docker-compose up -d
```

### Pagila not loading

The init scripts run in alphabetical order:
1. `01-load-pagila.sh` - Downloads and loads Pagila
2. `02-setup-dbrag-tables.sh` - Creates RAG tables
3. `03-load-sample-documents.sh` - Loads sample docs

Check each script's output in logs.

### pgvector extension not found

Make sure the Dockerfile installs `postgresql-16-pgvector`:

```dockerfile
RUN apt-get install -y postgresql-16-pgvector
```

## Data Persistence

Database data is persisted in a Docker volume named `db-rag_postgres_data`.

To backup:
```bash
docker-compose exec postgres pg_dump -U postgres pagila > backup.sql
```

To restore:
```bash
docker-compose exec -T postgres psql -U postgres pagila < backup.sql
```

## Extending to Other Databases

### Adding MySQL Support

1. Update `docker-compose.yml`:
```yaml
mysql:
  image: mysql:8.0
  environment:
    MYSQL_ROOT_PASSWORD: root
    MYSQL_DATABASE: mydb
  ports:
    - "3306:3306"
```

2. Create MySQL database manager in code (implement same interface)

### Adding MongoDB (Unstructured)

1. Add to `docker-compose.yml`:
```yaml
mongodb:
  image: mongo:7
  ports:
    - "27017:27017"
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: password
```

2. Create MongoDB agent for document collections

## Performance Tuning

### PostgreSQL Configuration

Add to `docker-compose.yml`:
```yaml
postgres:
  command: 
    - "postgres"
    - "-c"
    - "shared_buffers=256MB"
    - "-c"
    - "max_connections=200"
```

### Vector Index Tuning

For larger datasets, adjust the IVFFlat lists parameter:
```sql
CREATE INDEX ON table_metadata_catalog 
USING ivfflat (description_embedding vector_cosine_ops)
WITH (lists = 1000);  -- Increase for more data
```

## Next Steps

1. Run end-to-end tests: `python test_e2e.py`
2. Try the CLI: `python examples/cli.py`
3. Explore the Pagila schema: `psql -h localhost -U postgres -d pagila`
4. Add your own documents and policies
5. Extend to other data sources
