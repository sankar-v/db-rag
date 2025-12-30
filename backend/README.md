# DB-RAG Backend

FastAPI backend for the DB-RAG system.

## Development

```bash
pip install -r requirements.txt
python -m uvicorn api:app --reload
```

Access API at http://localhost:8000
API docs at http://localhost:8000/docs

## Architecture

- `api.py` - FastAPI REST API and WebSocket endpoints
- `main.py` - Core DB-RAG system
- `orchestrator.py` - Query routing agent
- `sql_agent.py` - SQL generation agent
- `vector_agent.py` - Semantic search agent
- `metadata_catalog.py` - AI-powered table discovery
- `database.py` - Database manager
- `config.py` - Configuration management
