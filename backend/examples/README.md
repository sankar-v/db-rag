# DB-RAG Examples

This directory contains example scripts demonstrating various use cases for the DB-RAG system.

## Examples

### 1. Command Line Interface (`cli.py`)
Interactive command-line interface for querying your database.

```bash
python examples/cli.py
```

Features:
- Natural language query interface
- Metadata catalog sync command
- Shows SQL queries and data sources used
- Interactive REPL-style interface

### 2. Document Ingestion (`ingest_documents.py`)
Examples of ingesting unstructured documents into the vector store.

```bash
python examples/ingest_documents.py
```

Demonstrates:
- Adding documents programmatically
- Setting document metadata
- Ingesting from text files
- Testing document search

### 3. SQL Generation Testing (`test_sql_generation.py`)
Test suite for SQL query generation capabilities.

```bash
python examples/test_sql_generation.py
```

Tests various query patterns:
- Aggregations (SUM, COUNT, AVG)
- Filtering and WHERE clauses
- Top-N queries
- Date-based queries
- Complex analytical queries

### 4. Hybrid Query Testing (`test_hybrid_queries.py`)
Demonstrates queries that combine structured and unstructured data.

```bash
python examples/test_hybrid_queries.py
```

Shows:
- Automatic routing to multiple agents
- Combining SQL results with document search
- Synthesizing responses from multiple sources

## Running Examples

1. Make sure you've set up your `.env` file with database credentials and API keys
2. Initialize the database schema: `psql -d your_db -f script.sql`
3. Run any example: `python examples/<example_name>.py`

## Customizing Examples

Feel free to modify these examples for your specific use case:
- Add your own test queries
- Customize document metadata
- Adjust output formatting
- Create new examples for your workflows
