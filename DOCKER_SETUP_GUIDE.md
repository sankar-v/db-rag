# Multi-Tenant Docker Setup

This setup provides a clean separation between control plane and data plane:

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTROL PLANE (Port 5434)                    │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  dbrag-control-plane                                      │ │
│  │  Database: dbrag_metadata                                 │ │
│  │                                                           │ │
│  │  Tables (Common for ALL tenants):                        │ │
│  │  - tenants                                               │ │
│  │  - connections                                           │ │
│  │  - table_metadata_catalog                                │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    DATA PLANE (Port 5435)                       │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  dbrag-data-plane                                         │ │
│  │                                                           │ │
│  │  Databases (Simulating different tenant databases):      │ │
│  │  - pagila         (DVD rental, 31 tables)                │ │
│  │  - adventureworks (Business data, multiple schemas)      │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

1. **Control Plane Isolation**: One PostgreSQL container with `dbrag_metadata` database
   - Stores ALL tenant configurations
   - Manages ALL database connections
   - Maintains searchable table metadata catalog

2. **Data Plane Simulation**: One PostgreSQL container with multiple databases
   - `pagila` - Simulates Tenant A's database
   - `adventureworks` - Simulates Tenant B's database
   - Both accessible on same host:port but different database names

3. **UI-Driven Configuration**: Users add connections via the Connection Wizard
   - Control plane metadata is populated through the UI
   - No hardcoded connection details
   - Each tenant can have multiple database connections

## Services

### Control Plane
- **control-plane-db** (port 5434): PostgreSQL with metadata tables
  - Container: `dbrag-control-plane`
  - Database: `dbrag_metadata`
  - Purpose: Central metadata storage for all tenants
  - Initialized with schema and default tenant automatically

### Data Plane
- **data-plane-db** (port 5435): PostgreSQL with multiple tenant databases
  - Container: `dbrag-data-plane`
  - Databases: `pagila` and `adventureworks`
  - Purpose: Simulates distributed tenant data sources
  - Both databases share same PostgreSQL instance

### Application Services
- **backend** (port 8000): FastAPI backend
  - Connects to control plane for metadata
  - Dynamically connects to tenant databases based on UI configuration
  
- **frontend** (port 3000): React TypeScript UI
  - Connection wizard to add databases
  - Automatic metadata sync

## Usage

### Start All Services
```bash
# Start Docker Desktop first, then:
docker-compose -f docker-compose.multi-tenant.yml up -d
```

### Start Only Databases
```bash
docker-compose -f docker-compose.multi-tenant.yml up -d control-plane-db data-plane-db
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.multi-tenant.yml logs -f

# Control plane only
docker-compose -f docker-compose.multi-tenant.yml logs -f control-plane-db

# Data plane only
docker-compose -f docker-compose.multi-tenant.yml logs -f data-plane-db
```

### Stop Services
```bash
docker-compose -f docker-compose.multi-tenant.yml down

# Remove volumes (clean slate)
docker-compose -f docker-compose.multi-tenant.yml down -v
```

## Connection Details

### From Host Machine (Local Development)

**Control Plane (Metadata):**
- Host: `localhost`
- Port: `5434`
- Database: `dbrag_metadata`
- User: `postgres`
- Password: `postgres`
- Purpose: Application metadata storage

**Data Plane - Pagila:**
- Host: `localhost`
- Port: `5435`
- Database: `pagila`
- User: `postgres`
- Password: `postgres`
- Purpose: Simulated tenant database (DVD rental)

**Data Plane - AdventureWorks:**
- Host: `localhost`
- Port: `5435`
- Database: `adventureworks`
- User: `postgres`
- Password: `postgres`
- Purpose: Simulated tenant database (Business data)

### From Docker Containers (Backend Service)

Use service names as hostnames:
- Control Plane: `control-plane-db:5432/dbrag_metadata`
- Data Plane: `data-plane-db:5432/pagila` or `data-plane-db:5432/adventureworks`

## First-Time Setup

1. **Start Docker Desktop** (ensure it's running)

2. **Build and start services:**
   ```bash
   docker-compose -f docker-compose.multi-tenant.yml up -d --build
   ```

3. **Wait for initialization** (~3-4 minutes first time):
   ```bash
   # Watch logs
   docker-compose -f docker-compose.multi-tenant.yml logs -f
   ```
   
   Look for:
   - Control plane: "✅ Metadata database schema initialized successfully"
   - Data plane: "✅ Pagila database loaded successfully!"
   - Data plane: "✅ AdventureWorks database loaded successfully!"

4. **Verify databases:**
   ```bash
   # Control plane
   docker exec -it dbrag-control-plane psql -U postgres -d dbrag_metadata -c "\dt"
   
   # Data plane - Pagila
   docker exec -it dbrag-data-plane psql -U postgres -d pagila -c "\dt"
   
   # Data plane - AdventureWorks
   docker exec -it dbrag-data-plane psql -U postgres -d adventureworks -c "\dt"
   ```

5. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Using the Connection Wizard (UI Setup)

The system is designed to be configured through the UI, not hardcoded:

1. **Navigate to Database Connections** (http://localhost:3000/connections)

2. **Add Pagila Connection:**
   - Click "New Connection"
   - Name: `Pagila DVD Rental`
   - Host: `localhost` (or `data-plane-db` from Docker)
   - Port: `5435`
   - Database: `pagila`
   - User: `postgres`
   - Password: `postgres`
   - Click "Test Connection" → Should show ~31 tables
   - All tables auto-selected → Click "Next"
   - Save → System syncs metadata to control plane

3. **Add AdventureWorks Connection:**
   - Click "New Connection" again
   - Name: `AdventureWorks Business`
   - Host: `localhost`
   - Port: `5435`
   - Database: `adventureworks`
   - User: `postgres`
   - Password: `postgres`
   - Test → Select tables → Save

4. **Verify Control Plane Storage:**
   ```bash
   docker exec -it dbrag-control-plane psql -U postgres -d dbrag_metadata -c \
     "SELECT connection_name, db_name, is_active FROM connections;"
   ```

## How It Works

### Metadata Flow

1. User adds connection via UI → Frontend calls `/api/connections/test`
2. Backend tests connection to data plane
3. Backend retrieves table list from data plane database
4. User selects tables (all by default) → Frontend calls `/api/connections/save`
5. Backend saves connection to **control plane** `connections` table
6. Backend syncs table metadata to **control plane** `table_metadata_catalog` table
7. All metadata searchable via control plane for query generation

### Query Flow

1. User asks question via chat
2. Backend searches control plane metadata for relevant tables
3. Backend generates SQL using GPT-4o based on metadata
4. Backend connects to appropriate data plane database
5. Backend executes query and returns results

### Tenant Isolation

- Each connection has `tenant_id` foreign key
- All metadata queries filtered by `tenant_id`
- Row-level security enforced in control plane
- Data plane databases completely isolated

## Troubleshooting

### Docker not running
```bash
# macOS - start Docker Desktop application
open -a Docker

# Wait for Docker to start, then retry
docker ps
```

### Port conflicts
```bash
# Check what's using ports
lsof -i :5434  # Control plane
lsof -i :5435  # Data plane

# Stop conflicting processes or change ports in docker-compose
```

### Database initialization failed
```bash
# Check logs
docker-compose -f docker-compose.multi-tenant.yml logs control-plane-db
docker-compose -f docker-compose.multi-tenant.yml logs data-plane-db

# Rebuild with clean slate
docker-compose -f docker-compose.multi-tenant.yml down -v
docker-compose -f docker-compose.multi-tenant.yml up -d --build
```

### Can't connect from UI
```bash
# Verify all containers running
docker ps

# Check backend can reach databases
docker exec -it dbrag-backend psql -h control-plane-db -U postgres -d dbrag_metadata -c "SELECT 1;"
docker exec -it dbrag-backend psql -h data-plane-db -U postgres -d pagila -c "SELECT 1;"
```

### Reset everything
```bash
# Complete cleanup
docker-compose -f docker-compose.multi-tenant.yml down -v
docker volume prune -f
docker network prune -f

# Rebuild from scratch
docker-compose -f docker-compose.multi-tenant.yml up -d --build
```

## Production Considerations

For production deployment:

1. **Separate Control Plane**: Move to AWS RDS, Azure Database, or managed PostgreSQL
2. **Distributed Data Plane**: Keep tenant databases close to data source
3. **Security**:
   - Use secrets manager for passwords
   - Enable SSL/TLS for all connections
   - Implement proper authentication (JWT, API keys)
   - Use connection pooling (PgBouncer)
4. **Scalability**:
   - Connection pooling for control plane
   - Caching for metadata queries
   - Read replicas for heavy query workloads
5. **Monitoring**:
   - Database metrics (connections, query performance)
   - Application metrics (API latency, error rates)
   - Alerting for connection failures

## Development Workflow

1. **Code changes**: Both backend and frontend mounted with hot reload
2. **Database schema changes**: 
   - Control plane: Modify `docker/metadata-init/01-init-metadata-schema.sql`
   - Data plane: Update `docker/init-dataplane.sh` or source SQL files
   - Recreate containers: `docker-compose down -v && docker-compose up -d`
3. **Add new tenant database**: Just use the UI - no code changes needed!
4. **Test multi-tenancy**: Create multiple tenants in control plane, add connections for each

## Architecture Benefits

✅ **Clean Separation**: Control and data planes independent
✅ **UI-Driven**: Zero hardcoded connections, all via UI
✅ **Scalable**: Control plane can manage thousands of connections
✅ **Tenant Isolation**: Complete separation at control plane level
✅ **Realistic Simulation**: Two databases mimics real multi-tenant scenario
✅ **Production-Ready**: Easy migration path to distributed architecture
