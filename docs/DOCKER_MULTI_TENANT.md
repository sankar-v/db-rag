# Multi-Tenant Docker Setup

This setup provides a complete multi-tenant architecture with separated control and data planes:

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Control Plane                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Metadata DB (Port 5434)                                  │ │
│  │  - Tenants                                                │ │
│  │  - Connections                                            │ │
│  │  - Table Metadata Catalog                                │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         Data Plane                              │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐│
│  │ Pagila DB (5435)     │  │ AdventureWorks DB (5436)         ││
│  │ - DVD Rental         │  │ - Business/Sales Data            ││
│  │ - 31 tables          │  │ - Multiple schemas               ││
│  └──────────────────────┘  └──────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Services

### Control Plane
- **metadata-db** (port 5434): PostgreSQL with metadata tables for multi-tenant management
  - Manages tenants, connections, and table metadata catalog
  - Isolated from data plane databases

### Data Plane
- **pagila-db** (port 5435): DVD rental sample database
  - 31 tables with realistic rental store data
  - Good for testing customer, inventory, payment queries
  
- **adventureworks-db** (port 5436): Business sample database
  - Sales, HR, Production, Purchasing schemas
  - Complex business relationships and hierarchies

### Application Services
- **backend** (port 8000): FastAPI backend with multi-tenant support
- **frontend** (port 3000): React TypeScript frontend with connection wizard

## Usage

### Start All Services
```bash
docker-compose -f docker-compose.multi-tenant.yml up -d
```

### Start Specific Services
```bash
# Just databases
docker-compose -f docker-compose.multi-tenant.yml up -d metadata-db pagila-db adventureworks-db

# With backend
docker-compose -f docker-compose.multi-tenant.yml up -d metadata-db pagila-db adventureworks-db backend

# Full stack
docker-compose -f docker-compose.multi-tenant.yml up -d
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.multi-tenant.yml logs -f

# Specific service
docker-compose -f docker-compose.multi-tenant.yml logs -f metadata-db
docker-compose -f docker-compose.multi-tenant.yml logs -f pagila-db
docker-compose -f docker-compose.multi-tenant.yml logs -f adventureworks-db
```

### Stop Services
```bash
docker-compose -f docker-compose.multi-tenant.yml down

# Remove volumes (clean slate)
docker-compose -f docker-compose.multi-tenant.yml down -v
```

## Connection Details

### From Host Machine (Local Development)

**Metadata Database (Control Plane):**
- Host: `localhost`
- Port: `5434`
- Database: `dbrag_metadata`
- User: `postgres`
- Password: `postgres`

**Pagila Database (Data Plane 1):**
- Host: `localhost`
- Port: `5435`
- Database: `pagila`
- User: `postgres`
- Password: `postgres`

**AdventureWorks Database (Data Plane 2):**
- Host: `localhost`
- Port: `5436`
- Database: `adventureworks`
- User: `postgres`
- Password: `postgres`

### From Docker Containers (Backend Service)

Use service names as hostnames:
- Metadata: `metadata-db:5432`
- Pagila: `pagila-db:5432`
- AdventureWorks: `adventureworks-db:5432`

## First-Time Setup

1. **Start the services:**
   ```bash
   docker-compose -f docker-compose.multi-tenant.yml up -d
   ```

2. **Wait for databases to initialize** (first time takes ~2-3 minutes):
   ```bash
   docker-compose -f docker-compose.multi-tenant.yml logs -f metadata-db pagila-db adventureworks-db
   ```
   Look for: "✅ database initialized successfully" messages

3. **Verify databases are ready:**
   ```bash
   # Check metadata DB
   docker exec -it dbrag-metadata-db psql -U postgres -d dbrag_metadata -c "\dt"
   
   # Check Pagila
   docker exec -it dbrag-pagila-db psql -U postgres -d pagila -c "\dt"
   
   # Check AdventureWorks
   docker exec -it dbrag-adventureworks-db psql -U postgres -d adventureworks -c "\dt"
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Using the Connection Wizard

1. Navigate to **Database Connections** page
2. Click **"New Connection"**
3. Add Pagila connection:
   - Name: `Pagila DVD Rental`
   - Host: `localhost`
   - Port: `5435`
   - Database: `pagila`
   - User: `postgres`
   - Password: `postgres`
4. Test connection → Select tables → Save → Sync metadata
5. Repeat for AdventureWorks (port `5436`)

## Troubleshooting

### Database not starting
```bash
# Check logs
docker-compose -f docker-compose.multi-tenant.yml logs metadata-db

# Restart specific service
docker-compose -f docker-compose.multi-tenant.yml restart metadata-db
```

### Port conflicts
If ports 5434, 5435, or 5436 are in use, stop existing PostgreSQL instances:
```bash
# Check what's using the port
lsof -i :5434
lsof -i :5435
lsof -i :5436

# Stop old docker containers
docker ps
docker stop <container-id>
```

### Reset everything
```bash
# Stop and remove all containers and volumes
docker-compose -f docker-compose.multi-tenant.yml down -v

# Remove images if needed
docker rmi dbrag-backend dbrag-frontend

# Start fresh
docker-compose -f docker-compose.multi-tenant.yml up -d --build
```

## Data Persistence

Data is persisted in named Docker volumes:
- `dbrag_metadata_data`: Metadata database
- `dbrag_pagila_data`: Pagila database
- `dbrag_adventureworks_data`: AdventureWorks database

To backup:
```bash
docker run --rm -v dbrag_metadata_data:/data -v $(pwd):/backup ubuntu tar czf /backup/metadata-backup.tar.gz /data
```

## Development Workflow

1. **Backend changes**: Code in `backend/` is mounted, changes reload automatically
2. **Frontend changes**: Code in `frontend/` is mounted, Vite HMR active
3. **Database schema changes**: Modify init scripts, then recreate containers
4. **Add new database**: Add new service to docker-compose, create init scripts

## Production Considerations

For production deployment:
1. Move metadata-db to AWS RDS or managed PostgreSQL
2. Keep data plane databases distributed (closer to data source)
3. Use secrets manager for passwords
4. Enable SSL/TLS for all connections
5. Set up proper backup/restore procedures
6. Implement connection pooling (PgBouncer)
7. Add monitoring and alerting
