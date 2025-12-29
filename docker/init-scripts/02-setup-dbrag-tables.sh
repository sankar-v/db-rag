#!/bin/bash
set -e

echo "========================================"
echo "Setting up pgvector and DB-RAG tables"
echo "========================================"

psql -U postgres -d pagila <<-EOSQL
    -- Enable pgvector extension
    CREATE EXTENSION IF NOT EXISTS vector;

    -- Create metadata catalog table
    CREATE TABLE IF NOT EXISTS table_metadata_catalog (
        id SERIAL PRIMARY KEY,
        table_name TEXT UNIQUE NOT NULL,
        column_definitions TEXT NOT NULL,
        table_description TEXT NOT NULL,
        business_context TEXT,
        sample_queries TEXT[],
        description_embedding VECTOR(1536),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create index for metadata catalog
    CREATE INDEX IF NOT EXISTS idx_metadata_embedding 
    ON table_metadata_catalog 
    USING ivfflat (description_embedding vector_cosine_ops)
    WITH (lists = 100);

    -- Create documents table for unstructured data
    CREATE TABLE IF NOT EXISTS company_documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        content TEXT NOT NULL,
        metadata JSONB,
        embedding VECTOR(1536),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create index for documents
    CREATE INDEX IF NOT EXISTS idx_documents_embedding 
    ON company_documents 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

    -- Grant permissions
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

    EOSQL

echo "DB-RAG tables created successfully!"
