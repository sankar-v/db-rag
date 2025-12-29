-- 1. Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. The Unstructured Store: For PDFs, Wikis, etc.
CREATE TABLE IF NOT EXISTS company_documents (
    id UUID PRIMARY KEY,
    content TEXT,                -- The actual text chunk
    metadata JSONB,              -- Store source, page_no, department
    embedding VECTOR(1536)       -- Vector size for OpenAI 'text-embedding-3-small'
);

-- 3. The Metadata Catalog: For "Table Discovery"
-- This helps the agent find the right table among hundreds
CREATE TABLE IF NOT EXISTS table_metadata_catalog (
    id SERIAL PRIMARY KEY,
    table_name TEXT UNIQUE,
    column_definitions TEXT,     -- Raw DDL or list of columns
    table_description TEXT,      -- LLM-generated summary
    description_embedding VECTOR(1536)
);

-- 4. Create an Index for fast vector retrieval
CREATE INDEX ON company_documents USING ivfflat (embedding vector_cosine_ops);
