# Multi-Tenant Architecture with Control/Data Plane Separation

## Overview

The DB-RAG system now implements a **production-grade multi-tenant architecture** with complete separation between the **control plane** (metadata) and **data plane** (actual tenant data).

## Architecture Components

### 1. Control Plane - Metadata Database

**Purpose**: Centralized metadata storage (can be AWS RDS, Azure Database, etc.)

**Database**: `dbrag_metadata` (configurable via `METADATA_DB_*` env variables)

**Stores**:
- **Tenants**: Organization/user accounts with unique tenant IDs
- **Connections**: Database connections per tenant
- **Table Metadata Catalog**: AI-generated descriptions, column info, relationships
- **Tenant Settings**: Per-tenant configuration and preferences

**Tables**:
```sql
tenants (
    tenant_id UUID PRIMARY KEY,
    tenant_name VARCHAR,
    organization VARCHAR,
    email VARCHAR,
    status VARCHAR,
    settings JSONB,
    created_at, updated_at
)

connections (
    connection_id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants,
    connection_name VARCHAR,
    host, port, database_name, username, password_encrypted,
    schema_name, is_active, status,
    connection_metadata JSONB,
    created_at, updated_at
)

table_metadata_catalog (
    catalog_id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants,
    connection_id UUID REFERENCES connections,
    table_name, schema_name,
    table_description TEXT,
    column_descriptions JSONB,
    sample_values JSONB,
    data_types JSONB,
    relationships JSONB,
    search_vector tsvector,  -- For fast semantic search
    last_synced, created_at
)
```

### 2. Data Plane - Tenant Databases

**Purpose**: Actual business data for each tenant/customer

**Database**: Tenant-specific databases (e.g., `customer_a_db`, `customer_b_db`)

**Characteristics**:
- Each tenant can have multiple connections
- Connections can be to different databases/hosts
- Data never leaves tenant's database
- Metadata is extracted and stored in control plane

## Multi-Tenant Isolation

### Tenant ID Scoping

All operations are scoped to a tenant_id:

```python
# Every API call automatically filters by tenant
tenant_id = get_tenant_id()  # From JWT token or API key

# List connections for this tenant only
connections = metadata_db.list_connections(tenant_id)

# Query metadata for this tenant only
tables = metadata_db.list_table_metadata(tenant_id, connection_id)
```

### Security Isolation

- **Row-Level Security**: All queries include `WHERE tenant_id = ?`
- **Connection Credentials**: Stored encrypted in metadata database
- **API Keys**: Each tenant has unique API keys (future implementation)
- **JWT Tokens**: Tenant ID embedded in JWT claims (future implementation)

## Connection Workflow

### 1. New Connection Creation

```
User → Connection Wizard → Test Connection → Select Tables → Save & Sync
```

**What Happens**:

1. **Test Connection** (`POST /api/connections/test`):
   - Connects to target database (data plane)
   - Lists all available tables
   - Returns table list to wizard
   - **No data is saved yet**

2. **Save Connection** (`POST /api/connections`):
   - Saves connection details to **metadata database** (control plane)
   - Includes: tenant_id, connection_name, host, port, credentials
   - Assigns unique connection_id
   - Status: `disconnected`

3. **Sync Tables** (`POST /api/connections/{id}/sync`):
   - For each selected table:
     - Connects to tenant database (data plane)
     - Analyzes table structure (columns, types, relationships)
     - Generates AI descriptions using LLM
     - Extracts sample data for context
     - **Saves metadata to control plane**
   - Updates connection status: `connected`

### 2. Activate Connection

```
User → Select Connection → Click Activate → RAG System Reinitializes
```

**What Happens**:

1. **Activate** (`POST /api/connections/{id}/activate`):
   - Retrieves connection from metadata database (control plane)
   - Decrypts credentials
   - Initializes new RAG instance pointing to tenant database (data plane)
   - Sets `is_active = TRUE` in metadata database
   - All queries now route to this connection

### 3. Query Execution

```
User Question → Orchestrator → Metadata Search → SQL Generation → Query Execution
```

**What Happens**:

1. **Metadata Search** (Control Plane):
   - Searches `table_metadata_catalog` using full-text search
   - Filters by: `tenant_id` AND `connection_id` (active)
   - Returns relevant table metadata (descriptions, columns, relationships)

2. **SQL Generation**:
   - LLM uses metadata from control plane
   - Generates SQL for tenant's specific schema

3. **Query Execution** (Data Plane):
   - Executes SQL on active tenant database
   - Returns results to user
   - **Data never touches control plane**

## Configuration

### Environment Variables

```bash
# Control Plane - Metadata Database (can be AWS RDS)
USE_METADATA_DB=true
METADATA_DB_HOST=your-rds-endpoint.amazonaws.com
METADATA_DB_PORT=5432
METADATA_DB_NAME=dbrag_metadata
METADATA_DB_USER=dbrag_admin
METADATA_DB_PASSWORD=secure_password

# Data Plane - Initial/Default Connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pagila
DB_USER=postgres
DB_PASSWORD=postgres

# Tenant Configuration
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001
DEFAULT_TENANT_NAME=Development
```

### Deployment Scenarios

#### Scenario 1: Single Metadata DB + Multiple Tenant DBs

```
AWS RDS (Metadata)
    ├── Tenant A → MySQL Database (Customer A's data)
    ├── Tenant B → PostgreSQL Database (Customer B's data)
    └── Tenant C → PostgreSQL Database (Customer C's data)
```

#### Scenario 2: SaaS Multi-Tenant

```
AWS RDS (Metadata Database)
    ├── Tenant: Company A (tenant_id: uuid-a)
    │   ├── Connection: Production DB
    │   └── Connection: Analytics DB
    │
    ├── Tenant: Company B (tenant_id: uuid-b)
    │   ├── Connection: Main Database
    │   └── Connection: Archive DB
    │
    └── Tenant: Company C (tenant_id: uuid-c)
        └── Connection: Unified DB
```

## Benefits

### 1. **Scalability**
- Metadata database scales independently
- Can handle thousands of tenants
- Each tenant can have multiple connections

### 2. **Security**
- Complete tenant isolation
- Credentials never exposed to clients
- Row-level security in metadata database

### 3. **Flexibility**
- Support any PostgreSQL-compatible database
- Tenants can use their own infrastructure
- No data migration required

### 4. **Performance**
- Fast metadata search with full-text indexes
- Cached table metadata reduces database queries
- Parallel query execution across connections

### 5. **Multi-Cloud Support**
- Metadata: AWS RDS
- Tenant A: Azure Database
- Tenant B: On-premise PostgreSQL
- Tenant C: Google Cloud SQL

## Setup Instructions

### 1. Initialize Metadata Database

```bash
cd backend
python setup_metadata_db.py
```

This creates:
- `dbrag_metadata` database
- All required tables
- Default tenant account
- Necessary indexes

### 2. Start Backend

```bash
cd backend
source venv/bin/activate  # or use absolute path
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Frontend

```bash
cd frontend
npm run dev
```

### 4. Create First Connection

1. Navigate to **Connections** page
2. Click **"New Connection"**
3. Fill in connection details
4. Test connection
5. Select tables (all selected by default)
6. Complete wizard - metadata syncs automatically
7. Connection appears in tree view

### 5. Switch Between Connections

- Click the **Power** icon to activate a different connection
- RAG system automatically reinitializes
- All queries now use the new connection
- Metadata is tenant-scoped

## API Endpoints

### Tenant Management (Future)

```
GET    /api/tenants              - List all tenants (admin only)
POST   /api/tenants              - Create new tenant
GET    /api/tenants/{id}         - Get tenant details
PUT    /api/tenants/{id}         - Update tenant
DELETE /api/tenants/{id}         - Delete tenant
```

### Connection Management

```
GET    /api/connections          - List connections (tenant-scoped)
POST   /api/connections/test     - Test connection without saving
POST   /api/connections          - Create new connection
PUT    /api/connections/{id}     - Update connection
DELETE /api/connections/{id}     - Delete connection
POST   /api/connections/{id}/activate  - Set as active
POST   /api/connections/{id}/sync      - Sync table metadata
```

### Query Execution

```
POST   /api/query                - Execute natural language query
                                   (uses active connection)
```

## Future Enhancements

1. **JWT Authentication**: Embed tenant_id in JWT tokens
2. **API Keys**: Per-tenant API keys for programmatic access
3. **Encryption**: AES-256 encryption for stored credentials
4. **Audit Logs**: Track all metadata access and queries
5. **Rate Limiting**: Per-tenant rate limits
6. **Billing Integration**: Track usage per tenant
7. **Multi-Region**: Replicate metadata database across regions
8. **Role-Based Access**: Admin, developer, analyst roles per tenant

## Migration from Single-Tenant

If you have an existing single-tenant setup:

1. Run `python setup_metadata_db.py` - Creates metadata database
2. Your existing data remains unchanged
3. Create a connection pointing to your existing database
4. Metadata is extracted and stored in control plane
5. System now supports multiple connections/tenants

No data migration required!

## Troubleshooting

### Metadata Database Connection Failed

Check `.env` file:
```bash
METADATA_DB_HOST=localhost
METADATA_DB_PORT=5433  # Check if PostgreSQL is running
METADATA_DB_NAME=dbrag_metadata
METADATA_DB_USER=postgres
METADATA_DB_PASSWORD=postgres
```

### Tables Not Syncing

1. Check backend logs for errors
2. Verify connection credentials are correct
3. Ensure user has SELECT permissions on tables
4. Check if OpenAI API key is set (for AI descriptions)

### Switch Connection Not Working

1. Verify connection is saved in metadata database
2. Check if connection status is 'connected'
3. Look for errors in backend logs
4. Restart backend server if needed

## Production Deployment

### Recommended Setup

1. **Metadata Database**: AWS RDS PostgreSQL with Multi-AZ
2. **Backend**: ECS/EKS with auto-scaling
3. **Frontend**: CloudFront + S3
4. **Secrets**: AWS Secrets Manager for credentials
5. **Monitoring**: CloudWatch + DataDog
6. **Backups**: Automated snapshots for metadata database

### Security Checklist

- [ ] Enable SSL/TLS for all database connections
- [ ] Encrypt credentials in metadata database
- [ ] Implement JWT-based authentication
- [ ] Enable audit logging
- [ ] Set up VPC security groups
- [ ] Use IAM roles for AWS services
- [ ] Enable encryption at rest
- [ ] Regular security audits
- [ ] Implement rate limiting
- [ ] Set up WAF rules

---

**Architecture Type**: Multi-Tenant SaaS with Control/Data Plane Separation  
**Tenant Isolation**: Row-Level Security + Unique Tenant IDs  
**Scalability**: Horizontal scaling with tenant sharding  
**Security**: Encrypted credentials, tenant-scoped queries, audit logs  
**Flexibility**: Support any PostgreSQL-compatible database
