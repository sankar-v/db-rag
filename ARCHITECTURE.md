# DB-RAG Architecture

## System Overview

DB-RAG is a Retrieval-Augmented Generation system that combines structured data from relational databases with unstructured data from documents to answer natural language queries.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                    (CLI / Python API / SDK)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         RAGEngine                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Query Processing & Answer Generation                      │ │
│  │  - Natural language understanding                          │ │
│  │  - Context aggregation                                     │ │
│  │  - Answer synthesis with LLM                              │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────┬───────────────────────────────┬───────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────┐   ┌──────────────────────────────┐
│    DatabaseConnector         │   │   VectorStoreManager         │
│  (Structured Data)           │   │  (Unstructured Data)         │
├─────────────────────────────┤   ├──────────────────────────────┤
│ • Natural Language → SQL    │   │ • Document embeddings         │
│ • Schema introspection      │   │ • Semantic similarity search  │
│ • Query execution           │   │ • Metadata filtering          │
│ • Result formatting         │   │ • Score ranking               │
└──────────┬──────────────────┘   └────────┬─────────────────────┘
           │                               │
           ▼                               ▼
    ┌──────────────┐              ┌────────────────┐
    │  SQL Database│              │  Vector Store  │
    │              │              │  (ChromaDB)    │
    │ • SQLite     │              │                │
    │ • PostgreSQL │              │ • Embeddings   │
    │ • MySQL      │              │ • Metadata     │
    └──────────────┘              └────────────────┘
           ▲                               ▲
           │                               │
           │                               │
    ┌──────┴──────┐              ┌────────┴────────┐
    │   Tables    │              │  DocumentLoader │
    │   Rows      │              │                 │
    │   Relations │              │ • PDF           │
    └─────────────┘              │ • Text          │
                                 │ • DOCX          │
                                 │ • Chunking      │
                                 └─────────────────┘
                                         ▲
                                         │
                                 ┌───────┴────────┐
                                 │   Documents    │
                                 │   Files        │
                                 │   Directories  │
                                 └────────────────┘
```

## Component Details

### 1. RAGEngine (Core Orchestrator)

The central component that coordinates all operations.

**Responsibilities:**
- Accept natural language queries
- Route queries to appropriate data sources
- Aggregate results from multiple sources
- Generate coherent answers using LLM

**Key Methods:**
- `query()`: Main query interface
- `query_database()`: Database-specific queries
- `query_documents()`: Document-specific queries
- `ingest_documents()`: Add documents to system

### 2. DatabaseConnector (Structured Data)

Manages interactions with relational databases.

**Responsibilities:**
- Connect to SQL databases (SQLite, PostgreSQL, MySQL)
- Convert natural language to SQL queries
- Execute SQL and return results
- Introspect database schema

**Features:**
- SQLAlchemy-based for multi-database support
- Automatic schema discovery
- Safe query execution
- Result formatting

**Flow:**
```
Natural Language Query
        ↓
  LLM (SQL Generation)
        ↓
   SQL Query String
        ↓
  Database Execution
        ↓
   Structured Results
```

### 3. VectorStoreManager (Unstructured Data)

Manages document embeddings and semantic search.

**Responsibilities:**
- Store document embeddings
- Perform similarity searches
- Manage vector database (ChromaDB)
- Handle metadata and filtering

**Features:**
- OpenAI embeddings for semantic understanding
- ChromaDB for efficient vector storage
- Metadata-based filtering
- Relevance scoring

**Flow:**
```
Documents
    ↓
Chunking (DocumentLoader)
    ↓
Embedding Generation (OpenAI)
    ↓
Vector Storage (ChromaDB)
    ↓
Semantic Search
    ↓
Relevant Documents
```

### 4. DocumentLoader (Data Ingestion)

Handles loading and preprocessing of documents.

**Responsibilities:**
- Load various document formats
- Split documents into chunks
- Preserve metadata
- Handle encoding issues

**Supported Formats:**
- PDF (via PyPDF)
- Text files (TXT)
- Word documents (DOCX)

**Chunking Strategy:**
- Recursive character splitting
- Configurable chunk size
- Overlapping chunks for context preservation

### 5. Config (Configuration Management)

Centralizes all system configuration.

**Configuration Areas:**
- OpenAI API settings
- Database connection details
- Vector store configuration
- RAG parameters (chunk size, top-k, etc.)

## Data Flow

### Query Flow

```
1. User submits natural language query
        ↓
2. RAGEngine receives query
        ↓
3. Parallel execution:
   ├─→ DatabaseConnector
   │   ├─→ Generate SQL via LLM
   │   ├─→ Execute SQL
   │   └─→ Return structured results
   │
   └─→ VectorStoreManager
       ├─→ Generate query embedding
       ├─→ Similarity search
       └─→ Return relevant documents
        ↓
4. RAGEngine aggregates results
        ↓
5. LLM generates coherent answer
        ↓
6. Return answer + sources to user
```

### Ingestion Flow

```
1. User provides document source
        ↓
2. DocumentLoader processes files
   ├─→ Load file content
   ├─→ Split into chunks
   └─→ Add metadata
        ↓
3. VectorStoreManager creates embeddings
   ├─→ Generate embeddings via OpenAI
   ├─→ Store in ChromaDB
   └─→ Index for fast retrieval
        ↓
4. Documents ready for querying
```

## Key Design Decisions

### 1. Unified Query Interface

**Decision:** Single `query()` method for both data sources

**Rationale:**
- Simplified user experience
- Automatic source selection
- Seamless integration of results

### 2. LangChain Framework

**Decision:** Built on LangChain ecosystem

**Rationale:**
- Rich ecosystem of tools
- Standard abstractions for LLMs
- Community support and updates

### 3. SQLAlchemy for Databases

**Decision:** Use SQLAlchemy for database abstraction

**Rationale:**
- Multi-database support
- Safe SQL execution
- Schema introspection
- Connection pooling

### 4. ChromaDB for Vectors

**Decision:** ChromaDB as default vector store

**Rationale:**
- Easy to use and deploy
- Good performance for moderate scale
- Local-first option
- Metadata filtering support

### 5. OpenAI Models

**Decision:** OpenAI for embeddings and LLM

**Rationale:**
- High-quality embeddings
- Powerful language understanding
- Well-documented API
- Consistent results

## Scalability Considerations

### Current Scale
- **Documents:** Thousands of documents
- **Database:** Small to medium databases
- **Queries:** Interactive use cases

### Scaling Up

**For More Documents:**
- Consider Pinecone or Weaviate for vector storage
- Implement batch processing for ingestion
- Use larger embedding models

**For Larger Databases:**
- Optimize SQL query generation
- Add query caching
- Consider read replicas

**For Higher Query Volume:**
- Add response caching
- Implement rate limiting
- Consider async processing

## Security Considerations

### Current Implementation
- Environment-based secrets management
- SQL injection prevention via parameterized queries
- No direct user SQL execution

### Production Recommendations
- Use proper secrets management (Vault, AWS Secrets Manager)
- Implement user authentication
- Add query auditing
- Rate limiting on API calls
- Input sanitization

## Extension Points

### Adding New Document Types
Extend `DocumentLoader` with new loader methods

### Adding New Vector Stores
Implement new backend in `VectorStoreManager`

### Adding New Databases
SQLAlchemy supports additional databases out of the box

### Custom LLM Models
Modify `RAGEngine` to use different LLM providers

## Technology Stack

- **Language:** Python 3.8+
- **LLM Framework:** LangChain
- **Vector Database:** ChromaDB
- **SQL Toolkit:** SQLAlchemy
- **LLM Provider:** OpenAI (GPT-3.5/4, Ada embeddings)
- **Document Processing:** PyPDF, python-docx
- **Configuration:** python-dotenv

## Future Enhancements

1. **Multi-modal Support:** Images, tables, charts
2. **Advanced Filtering:** Time-based, user-based
3. **Query Optimization:** Caching, indexing
4. **Streaming Responses:** Real-time answer generation
5. **Fine-tuning:** Domain-specific model training
6. **Monitoring:** Query analytics, performance metrics
7. **Web Interface:** Browser-based UI
8. **API Server:** REST/GraphQL endpoints
