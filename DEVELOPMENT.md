# DB-RAG Development Guide

## Project Overview

DB-RAG is a full-stack application that combines:
- **Backend**: FastAPI with PostgreSQL and OpenAI integration
- **Frontend**: React + TypeScript with Vite
- **Database**: PostgreSQL 16 with pgvector extension

## Architecture

### Backend (Python/FastAPI)

#### Core Modules
1. **api.py** - REST API endpoints and WebSocket handlers
2. **main.py** - DBRAG class (main entry point)
3. **orchestrator.py** - Query routing logic
4. **sql_agent.py** - Natural language to SQL
5. **vector_agent.py** - Semantic document search
6. **metadata_catalog.py** - Table discovery
7. **database.py** - PostgreSQL operations
8. **config.py** - Configuration management

#### Agent Flow
```
Query → Orchestrator → [SQL Agent | Vector Agent | Both]
                    ↓
              Synthesize Response
```

### Frontend (React/TypeScript)

#### Pages
- **ChatInterface** - Main conversational UI
- **DocumentManager** - Upload and manage documents
- **DatabaseConnections** - Database configuration
- **MetadataExplorer** - Browse tables and metadata

#### API Client
- `src/api/client.ts` - Centralized API calls
- Uses Axios for HTTP, TanStack Query for state

## Development Workflow

### Backend Development

1. **Setup virtual environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. **Run with hot reload**
```bash
python -m uvicorn api:app --reload
```

3. **Run tests**
```bash
python test_e2e.py
```

### Frontend Development

1. **Install dependencies**
```bash
cd frontend
npm install
```

2. **Run dev server**
```bash
npm run dev
```

3. **Build for production**
```bash
npm run build
```

## Adding New Features

### Adding a New API Endpoint

1. Add endpoint to `backend/api.py`:
```python
@app.get("/api/your-endpoint")
async def your_endpoint():
    # Implementation
    pass
```

2. Add API function to `frontend/src/api/client.ts`:
```typescript
export const yourAPI = {
  yourFunction: async (): Promise<YourType> => {
    const response = await api.get('/api/your-endpoint')
    return response.data
  }
}
```

3. Use in component with TanStack Query:
```typescript
const { data } = useQuery({
  queryKey: ['your-key'],
  queryFn: yourAPI.yourFunction
})
```

### Adding a New Page

1. Create component in `frontend/src/pages/`:
```typescript
export default function YourPage() {
  return <div>Your content</div>
}
```

2. Add route to `frontend/src/App.tsx`:
```typescript
<Route path="/your-page" element={<YourPage />} />
```

3. Add to navigation in `frontend/src/components/Layout.tsx`

## Testing

### Backend Tests
- Located in `backend/test_e2e.py`
- Tests SQL generation, vector search, routing
- Uses Pagila sample database

### Frontend Testing (TODO)
- Unit tests with Vitest
- Component tests with React Testing Library
- E2E tests with Playwright

## Database Schema

### Metadata Catalog
```sql
CREATE TABLE metadata_catalog (
    table_name VARCHAR(255) PRIMARY KEY,
    description TEXT,
    columns JSONB,
    sample_data JSONB,
    embedding vector(1536),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Documents Table
```sql
CREATE TABLE company_documents (
    id UUID PRIMARY KEY,
    content TEXT,
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP
);
```

## Deployment

### Docker Production

1. Build images:
```bash
docker-compose build
```

2. Run services:
```bash
docker-compose up -d
```

### Manual Deployment

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm run build
# Serve dist/ with nginx or similar
```

## Environment Variables

See `.env.example` for required and optional variables.

## Troubleshooting

### Common Issues

1. **OpenAI API errors**
   - Verify API key is correct
   - Check rate limits
   - Monitor costs

2. **Database connection issues**
   - Ensure PostgreSQL is running
   - Verify credentials
   - Check network connectivity

3. **Frontend build errors**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Clear Vite cache: `rm -rf .vite`

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Docstrings for public functions
- Line length: 100 characters

### TypeScript
- Use ES6+ features
- Strict type checking
- Functional components with hooks
- Props interfaces for all components

## Git Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "feat: your feature"`
3. Push and create PR: `git push origin feature/your-feature`
4. Request review
5. Merge after approval

## Performance Optimization

### Backend
- Use connection pooling
- Cache metadata catalog queries
- Optimize SQL queries
- Use async/await for I/O operations

### Frontend
- Code splitting with React.lazy()
- Memoize expensive computations
- Optimize re-renders with useMemo/useCallback
- Use TanStack Query caching

## Security Considerations

- Never commit `.env` files
- Sanitize user inputs
- Validate SQL queries before execution
- Use parameterized queries
- Implement rate limiting
- Add authentication/authorization (TODO)
