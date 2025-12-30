# DB-RAG - Full Stack Agentic RAG System

An intelligent Agentic Retrieval-Augmented Generation (RAG) system for PostgreSQL databases with a modern React frontend.

## 🎯 Overview

DB-RAG combines the power of Large Language Models (LLMs) with PostgreSQL databases to enable natural language querying of both structured (SQL) and unstructured (document) data. The system uses an orchestrator pattern with specialized agents to intelligently route queries and provide accurate, context-aware responses.

## ✨ Features

### Core Capabilities
- 💬 **Conversational Chat Interface**: Ask questions in natural language with real-time responses
- 🤖 **Intelligent Query Routing**: Automatically determines SQL, vector search, or hybrid approach
- 📊 **SQL Generation**: Converts natural language to optimized SQL queries
- 🔍 **Semantic Search**: Vector-based document search using pgvector
- 📚 **AI-Generated Metadata**: Automatic table descriptions and schema understanding

### Frontend Features
- 📁 **Document Management**: Drag-and-drop upload with real-time vectorization
- 🔌 **Database Connectors**: Visual connection configuration and testing
- 🗂️ **Metadata Explorer**: Browse tables with AI-generated descriptions
- 🎨 **Modern UI**: React + TypeScript with TailwindCSS
- ⚡ **Real-time Updates**: WebSocket support for live responses

### Infrastructure
- 🐳 **Full Docker Stack**: PostgreSQL, Backend API, Frontend
- 📦 **Sample Database**: Pre-loaded Pagila database (22 tables, 16k+ records)
- 🔄 **Hot Reload**: Development mode with live code updates
- 📝 **API Documentation**: Interactive OpenAPI docs

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### One-Command Setup

```bash
# Clone and navigate to the repository
cd db-rag

# Create environment file with your OpenAI API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here

# Run the automated setup script
chmod +x start.sh
./start.sh
```

The script will:
1. Build all Docker containers (PostgreSQL, Backend, Frontend)
2. Load the Pagila sample database
3. Start all services and verify health
4. Display access URLs

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5433 (user: postgres, password: postgres, database: pagila)

## 📁 Project Structure

```
db-rag/
├── backend/                  # FastAPI backend
│   ├── api.py               # REST API & WebSocket endpoints
│   ├── main.py              # DB-RAG core system
│   ├── orchestrator.py      # Query routing agent
│   ├── sql_agent.py         # SQL generation agent
│   ├── vector_agent.py      # Semantic search agent
│   ├── metadata_catalog.py  # AI-powered table discovery
│   ├── database.py          # Database manager
│   ├── config.py            # Configuration
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Backend container
│
├── frontend/                 # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/           # Page components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── DocumentManager.tsx
│   │   │   ├── DatabaseConnections.tsx
│   │   │   └── MetadataExplorer.tsx
│   │   ├── components/      # Shared components
│   │   ├── api/             # API client
│   │   └── App.tsx          # Main app
│   ├── package.json
│   └── Dockerfile           # Frontend container
│
├── docker/                   # PostgreSQL setup
│   ├── Dockerfile           # Custom PostgreSQL image
│   └── init-scripts/        # Database initialization
│
├── docker-compose.yml       # Multi-container orchestration
├── start.sh                 # Automated setup script
└── README.md
```

## 🎮 Usage Examples

### Chat Interface
Navigate to http://localhost:3000/chat and ask questions like:

**Database Queries (SQL)**:
- "How many customers do we have?"
- "What are the top 5 most rented films?"
- "Show me all rentals from last week"
- "Which staff member processed the most payments?"

**Document Queries (Vector Search)**:
- "What is our vacation policy?"
- "Tell me about employee benefits"
- "What are the company holidays?"

### Document Management
1. Navigate to the **Documents** page
2. Drag and drop files or paste text
3. Documents are automatically vectorized
4. Search them via the chat interface

### Database Connections
1. Go to the **Connections** page
2. Default settings work with the Docker setup:
   - Host: localhost
   - Port: 5433
   - Database: pagila
   - User: postgres
   - Password: postgres
3. Test connection before applying

### Metadata Explorer
1. Go to the **Metadata** page
2. Browse all 22 tables
3. View AI-generated descriptions
4. See column details and sample data
5. Click "Sync Metadata" to refresh

## 🔧 API Endpoints

### Query Endpoints
- `POST /api/query` - Main query endpoint with auto-routing
- `WS /ws/chat` - WebSocket for real-time chat
- `POST /api/query/sql` - SQL-only queries
- `POST /api/query/vector` - Vector search only

### Document Endpoints
- `GET /api/documents` - List all documents
- `POST /api/documents` - Add text document
- `POST /api/documents/upload` - Upload file

### Table Endpoints
- `GET /api/tables` - List all tables
- `GET /api/tables/{name}` - Get table metadata
- `POST /api/metadata/sync` - Sync metadata catalog

### Connection Endpoints
- `POST /api/connection/test` - Test database connection
- `POST /api/connection/configure` - Apply new configuration

### System Endpoints
- `GET /health` - Health check
- `GET /api/status` - Detailed system status

## 🛠️ Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt

# Run with hot reload
python -m uvicorn api:app --reload

# Run tests
python test_e2e.py
```

### Frontend Development
```bash
cd frontend
npm install

# Run dev server with hot reload
npm run dev

# Build for production
npm run build
```

### Docker Commands

**Start all services:**
```bash
docker-compose up
```

**Rebuild after code changes:**
```bash
docker-compose up --build
```

**Stop services:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

**Access PostgreSQL:**
```bash
docker exec -it dbrag-postgres psql -U postgres -d pagila
```

## 📊 Sample Database

The system includes the **Pagila** sample database (PostgreSQL version of the Sakila MySQL database):

**Statistics:**
- 22 tables (customers, films, rentals, payments, etc.)
- 599 customers
- 1,000 films across 16 categories
- 16,044 rental transactions
- Complete DVD rental store schema

**Key Tables:**
- `customer` - Customer information
- `film` - Film catalog with descriptions
- `rental` - Rental transactions
- `payment` - Payment records
- `actor`, `category`, `inventory`, etc.

## 🏗️ Architecture

### Query Flow
1. User enters natural language question in frontend
2. Frontend sends to `/api/query` via REST or WebSocket
3. **Orchestrator Agent** analyzes query intent using GPT-4
4. Routes to **SQL Agent** and/or **Vector Agent**
5. **SQL Agent**: Discovers relevant tables → Generates SQL → Validates → Executes
6. **Vector Agent**: Embeds query → Searches vectors → Returns relevant documents
7. Orchestrator synthesizes results into natural language
8. Response displayed in chat interface

### Key Components

**Backend (Python/FastAPI):**
- **Orchestrator Agent**: Query routing and response synthesis
- **SQL Agent**: Table discovery and SQL generation
- **Vector Agent**: Semantic document search with pgvector
- **Metadata Catalog**: AI-generated table descriptions
- **Database Manager**: PostgreSQL operations and connection management

**Frontend (React/TypeScript):**
- **Chat Interface**: Conversational UI with message history
- **Document Manager**: File upload and document listing
- **Connection Manager**: Database configuration UI
- **Metadata Explorer**: Table browsing and visualization
- **Layout**: Responsive navigation and status indicators

## 📝 Tech Stack

### Backend
- **FastAPI** - Modern Python web framework with async support
- **PostgreSQL 16** - Database with pgvector extension
- **OpenAI GPT-4** - Query understanding and routing
- **text-embedding-3-small** - Document vectorization
- **SQLAlchemy** - ORM and query building
- **psycopg2** - PostgreSQL adapter
- **Uvicorn** - ASGI server

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **TanStack Query** - Server state management
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **React Markdown** - Markdown rendering
- **Lucide React** - Icon library

## 🔐 Environment Variables

Create a `.env` file with:

```bash
# Required: OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Database Configuration (defaults shown)
DB_HOST=localhost
DB_PORT=5433
DB_NAME=pagila
DB_USER=postgres
DB_PASSWORD=postgres
DB_SCHEMA=public

# Optional: LLM Configuration
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.0
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

## 🐛 Troubleshooting

### Backend won't start
- Verify OpenAI API key is set in `.env`
- Check PostgreSQL is running: `docker ps | grep postgres`
- View logs: `docker-compose logs backend`

### Frontend shows "Disconnected"
- Ensure backend is running on port 8000
- Check CORS settings in `backend/api.py`
- View network tab in browser DevTools

### Database connection failed
- Verify PostgreSQL port 5433 is not in use
- Check credentials in Connections page
- Test connection: `docker exec dbrag-postgres pg_isready -U postgres`

### Port already in use
- Stop conflicting services
- Or change ports in `docker-compose.yml`

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙋 Support

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions
- **Email**: [Your contact]

## 🔮 Roadmap

- [ ] Multi-database support (MySQL, SQL Server, Oracle)
- [ ] Advanced query optimization
- [ ] Query history and saved queries
- [ ] User authentication and authorization
- [ ] Custom agent creation
- [ ] Export results to CSV/Excel
- [ ] GraphQL support
- [ ] Slack/Teams integration
- [ ] Query performance analytics
- [ ] Natural language chart generation

---

**Built with ❤️ using OpenAI GPT-4, PostgreSQL, FastAPI, and React**
