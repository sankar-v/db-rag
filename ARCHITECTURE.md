# DB-RAG System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                              │
│                     http://localhost:3000                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Components                                                │  │
│  │  • Layout (Navigation)                                    │  │
│  │  • ChatInterface (Conversational UI)                      │  │
│  │  • DocumentManager (Upload/List)                          │  │
│  │  • DatabaseConnections (Config)                           │  │
│  │  • MetadataExplorer (Table Browser)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ API Client (Axios + TanStack Query)                       │  │
│  │  • Query API                                              │  │
│  │  • Document API                                           │  │
│  │  • Table API                                              │  │
│  │  • Connection API                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ REST API / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                FastAPI Backend (Python)                          │
│                 http://localhost:8000                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ REST API Endpoints (api.py)                              │  │
│  │  • POST /api/query          - Main query endpoint        │  │
│  │  • WS /ws/chat              - Real-time chat             │  │
│  │  • POST /api/documents      - Add documents              │  │
│  │  • GET /api/tables          - List tables                │  │
│  │  • POST /api/connection/*   - Connection mgmt            │  │
│  │  • GET /api/status          - System status              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ DBRAG Core (main.py)                                     │  │
│  │  • Initialize system                                      │  │
│  │  • Coordinate agents                                      │  │
│  │  • Manage lifecycle                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Orchestrator Agent (orchestrator.py)                     │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ 1. Analyze query intent                            │  │  │
│  │  │ 2. Route to appropriate agents                     │  │  │
│  │  │ 3. Synthesize results                              │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                                     │                │
│           ▼                                     ▼                │
│  ┌──────────────────────┐          ┌──────────────────────┐    │
│  │ SQL Agent            │          │ Vector Agent         │    │
│  │ (sql_agent.py)       │          │ (vector_agent.py)    │    │
│  │                      │          │                      │    │
│  │ 1. Discover Tables   │          │ 1. Embed Query       │    │
│  │    (semantic search) │          │    (OpenAI)          │    │
│  │ 2. Generate SQL      │          │ 2. Vector Search     │    │
│  │    (LLM)             │          │    (pgvector)        │    │
│  │ 3. Validate Query    │          │ 3. Return Docs       │    │
│  │ 4. Execute           │          │                      │    │
│  └──────────────────────┘          └──────────────────────┘    │
│           │                                     │                │
│           └─────────────┬───────────────────────┘                │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Metadata Catalog Manager (metadata_catalog.py)           │  │
│  │  • Table discovery and descriptions                       │  │
│  │  • AI-generated table summaries                          │  │
│  │  • Vector-based table search                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Database Manager (database.py)                           │  │
│  │  • Connection pooling                                     │  │
│  │  • Query execution                                        │  │
│  │  • Schema introspection                                   │  │
│  │  • Transaction management                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SQL / pgvector
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│         PostgreSQL 16 + pgvector Extension                       │
│               localhost:5433 (mapped from 5432)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Pagila Database (Sample Data)                            │  │
│  │  • customer       - Customer records (599)               │  │
│  │  • film           - Film catalog (1000)                  │  │
│  │  • rental         - Rental transactions (16044)          │  │
│  │  • payment        - Payment records                      │  │
│  │  • actor          - Actor information                    │  │
│  │  • category       - Film categories                      │  │
│  │  • inventory      - Inventory tracking                   │  │
│  │  • staff          - Staff records                        │  │
│  │  ... 14 more tables                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ RAG System Tables                                        │  │
│  │  • metadata_catalog  - AI table descriptions + vectors   │  │
│  │  • company_documents - Document store + vectors          │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ pgvector Extension                                       │  │
│  │  • Vector data type: vector(1536)                        │  │
│  │  • Similarity operators: <-> (cosine distance)           │  │
│  │  • IVFFlat indexing for fast search                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ API Calls
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OpenAI API                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ GPT-4o                                                    │  │
│  │  • Query intent analysis                                  │  │
│  │  • SQL generation                                         │  │
│  │  • Response synthesis                                     │  │
│  │  • Table descriptions                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ text-embedding-3-small                                    │  │
│  │  • Query embeddings (1536 dimensions)                     │  │
│  │  • Document embeddings                                    │  │
│  │  • Table description embeddings                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Query Flow Diagram

```
User Question: "How many customers rented films last week?"
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 1. Frontend (ChatInterface)                                   │
│    • User types question                                      │
│    • Sends POST to /api/query                                 │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 2. Backend API (api.py)                                       │
│    • Receives request                                         │
│    • Calls rag_instance.query(question)                       │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 3. Orchestrator Agent (orchestrator.py)                       │
│    • Calls OpenAI GPT-4 to analyze intent                     │
│    • Determines: "This needs structured data (SQL)"           │
│    • Routes to: [SQL Agent]                                   │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 4. SQL Agent (sql_agent.py)                                   │
│    Step 1: Discover Tables                                    │
│    • Embeds query: "customers rented films last week"         │
│    • Searches metadata_catalog with vector similarity         │
│    • Finds: customer, rental, film tables                     │
│                                                                │
│    Step 2: Generate SQL                                       │
│    • Calls GPT-4 with table schemas                           │
│    • Generates SQL:                                           │
│      SELECT COUNT(DISTINCT customer_id)                       │
│      FROM rental                                              │
│      WHERE rental_date >= CURRENT_DATE - INTERVAL '7 days'    │
│                                                                │
│    Step 3: Validate                                           │
│    • Checks SQL syntax                                        │
│    • Verifies table/column names                              │
│                                                                │
│    Step 4: Execute                                            │
│    • Runs query on PostgreSQL                                 │
│    • Returns: count=127                                       │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 5. Orchestrator Synthesizes Response                          │
│    • Calls GPT-4 to create natural language answer            │
│    • Input: Query + SQL + Results                             │
│    • Output: "127 customers rented films in the last week"    │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 6. Response Returned                                          │
│    {                                                           │
│      "success": true,                                         │
│      "answer": "127 customers rented films last week",        │
│      "query": "How many customers rented films last week?",   │
│      "sql_results": {                                         │
│        "sql": "SELECT COUNT...",                              │
│        "results": [{"count": 127}]                            │
│      },                                                        │
│      "routing": [{"agent": "sql", ...}]                       │
│    }                                                           │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 7. Frontend Displays                                          │
│    • Renders answer with Markdown                             │
│    • Shows SQL query in code block                            │
│    • Displays routing information                             │
└───────────────────────────────────────────────────────────────┘
```

## Docker Container Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Docker Host                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ dbrag-frontend                                           │ │
│  │ Container: Node 20 Alpine                                │ │
│  │ Port: 3000 → 3000                                        │ │
│  │                                                           │ │
│  │ • npm run dev                                            │ │
│  │ • Vite dev server with HMR                               │ │
│  │ • React app with hot reload                              │ │
│  │ • Volume: ./frontend → /app                              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           │ HTTP API Calls                      │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ dbrag-backend                                            │ │
│  │ Container: Python 3.11 Slim                              │ │
│  │ Port: 8000 → 8000                                        │ │
│  │                                                           │ │
│  │ • uvicorn api:app --reload                               │ │
│  │ • FastAPI with auto-reload                               │ │
│  │ • Volume: ./backend → /app                               │ │
│  │ • Env: OPENAI_API_KEY, DB_HOST=postgres                  │ │
│  │ • Depends on: postgres (healthy)                         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           │ PostgreSQL Protocol                 │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ dbrag-postgres                                           │ │
│  │ Container: PostgreSQL 16 + pgvector                      │ │
│  │ Port: 5433 → 5432                                        │ │
│  │                                                           │ │
│  │ • Pagila database loaded                                 │ │
│  │ • pgvector extension enabled                             │ │
│  │ • Init scripts executed                                  │ │
│  │ • Volume: postgres_data (persistent)                     │ │
│  │ • Volume: ./docker/init-scripts                          │ │
│  │ • Health check: pg_isready                               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Network: dbrag-network (bridge)                               │
│  Volumes: postgres_data (named volume for persistence)         │
└────────────────────────────────────────────────────────────────┘

External Access:
• Frontend:  http://localhost:3000 → Container Port 3000
• Backend:   http://localhost:8000 → Container Port 8000  
• Postgres:  localhost:5433       → Container Port 5432
```

## Data Flow: Document Upload

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User uploads document in DocumentManager                 │
│    • File: "vacation_policy.txt"                            │
│    • Content: "Employees get 15 days vacation..."           │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Frontend sends POST /api/documents/upload                │
│    • FormData with file                                     │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend receives file (api.py)                           │
│    • Reads file content                                     │
│    • Calls rag_instance.add_document(content, metadata)     │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Vector Agent (vector_agent.py)                           │
│    • Calls OpenAI text-embedding-3-small                    │
│    • Gets embedding: [0.123, -0.456, ..., 0.789]           │
│    • 1536 dimensions                                        │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Database Manager inserts into company_documents          │
│    INSERT INTO company_documents (                          │
│      id, content, metadata, embedding, created_at           │
│    ) VALUES (                                               │
│      uuid, 'Employees get...', {...}, vector, now()         │
│    )                                                         │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Returns document_id to frontend                          │
│    • Shows success message                                  │
│    • Refreshes document list                                │
│    • Document now searchable via chat                       │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                            │
├─────────────────────────────────────────────────────────────┤
│ React 18           - UI library                             │
│ TypeScript         - Type safety                            │
│ Vite               - Build tool (fast HMR)                  │
│ TailwindCSS        - Styling                                │
│ TanStack Query     - Server state management                │
│ React Router       - Routing                                │
│ Axios              - HTTP client                            │
│ React Markdown     - Markdown rendering                     │
│ Lucide React       - Icons                                  │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend Layer                             │
├─────────────────────────────────────────────────────────────┤
│ FastAPI            - Web framework                          │
│ Uvicorn            - ASGI server                            │
│ Pydantic           - Data validation                        │
│ psycopg2           - PostgreSQL adapter                     │
│ SQLAlchemy         - ORM                                    │
│ python-dotenv      - Environment management                 │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI/ML Layer                               │
├─────────────────────────────────────────────────────────────┤
│ OpenAI GPT-4o                - Query understanding          │
│ text-embedding-3-small       - Vectorization                │
│ Function Calling             - Structured outputs           │
│ Temperature: 0.0             - Deterministic                │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL 16      - Relational database                    │
│ pgvector           - Vector similarity search               │
│ IVFFlat            - Vector indexing                        │
│ Pagila DB          - Sample data (22 tables)                │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                Infrastructure Layer                          │
├─────────────────────────────────────────────────────────────┤
│ Docker             - Containerization                       │
│ Docker Compose     - Multi-container orchestration          │
│ Networks           - Container networking                   │
│ Volumes            - Data persistence                       │
└─────────────────────────────────────────────────────────────┘
```

This architecture provides:
✅ Separation of concerns
✅ Scalability (can run multiple backend instances)
✅ Development isolation
✅ Production-ready containerization
✅ Hot reload for rapid development
✅ Persistent data storage
✅ Intelligent query routing
✅ Real-time capabilities
