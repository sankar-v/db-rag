-- DB-RAG Metadata Database Schema
-- Control Plane for Multi-Tenant Architecture

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name VARCHAR(255) NOT NULL,
    organization VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Connections table (tenant-scoped)
CREATE TABLE IF NOT EXISTS connections (
    connection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    connection_name VARCHAR(255) NOT NULL,
    db_host VARCHAR(255) NOT NULL,
    db_port INTEGER NOT NULL DEFAULT 5432,
    db_name VARCHAR(255) NOT NULL,
    db_user VARCHAR(255) NOT NULL,
    db_password_encrypted TEXT NOT NULL,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    connection_metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(tenant_id, connection_name)
);

-- Table metadata catalog (tenant-scoped)
CREATE TABLE IF NOT EXISTS table_metadata_catalog (
    metadata_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES connections(connection_id) ON DELETE CASCADE,
    table_schema VARCHAR(255) NOT NULL DEFAULT 'public',
    table_name VARCHAR(255) NOT NULL,
    description TEXT,
    column_info JSONB,
    sample_queries TEXT[],
    tags TEXT[],
    search_vector tsvector,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, connection_id, table_schema, table_name)
);

-- Indexes for performance
CREATE INDEX idx_connections_tenant ON connections(tenant_id);
CREATE INDEX idx_connections_active ON connections(tenant_id, is_active);
CREATE INDEX idx_table_metadata_tenant ON table_metadata_catalog(tenant_id);
CREATE INDEX idx_table_metadata_connection ON table_metadata_catalog(connection_id);
CREATE INDEX idx_table_metadata_search ON table_metadata_catalog USING gin(search_vector);
CREATE INDEX idx_table_metadata_tags ON table_metadata_catalog USING gin(tags);

-- Trigger to update search_vector
CREATE OR REPLACE FUNCTION update_search_vector() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.table_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER table_metadata_search_vector_update 
    BEFORE INSERT OR UPDATE ON table_metadata_catalog
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- Insert default tenant
INSERT INTO tenants (tenant_id, tenant_name, organization, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Development',
    'DB-RAG Development',
    true
) ON CONFLICT (tenant_id) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Metadata database schema initialized successfully';
    RAISE NOTICE '✅ Default tenant created: Development (00000000-0000-0000-0000-000000000001)';
END $$;
