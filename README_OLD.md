# DB-RAG: Agentic RAG for Relational Databases

An intelligent, scalable Agentic RAG (Retrieval-Augmented Generation) system for querying relational databases using natural language. Built with PostgreSQL and pgvector, extensible to other RDBMS and unstructured data sources.

## 🎯 Features

- **🤖 Agentic Architecture**: Intelligent query routing between structured (SQL) and unstructured (vector) data
- **🔍 Automatic Table Discovery**: AI-powered metadata catalog that understands your database schema
- **💬 Natural Language to SQL**: Convert natural language questions to optimized PostgreSQL queries
- **📚 Vector Search**: Semantic search across unstructured documents using pgvector
- **🔄 Hybrid Queries**: Automatically combines SQL and document search when needed
- **🛡️ Query Validation**: Built-in SQL validation before execution
- **📊 Schema Introspection**: Automatic understanding of tables, columns, relationships
- **🚀 Extensible**: Designed to support multiple RDBMS and data sources

## 🏗️ Architecture

```
User Query
    ↓
Orchestrator Agent (Router)
    ↓
    ├─→ SQL Agent ──→ Table Discovery ──→ SQL Generation ──→ Query Execution
    └─→ Vector Agent ──→ Embedding Search ──→ Document Retrieval

Results are synthesized into a coherent natural language response
```

## 📋 Prerequisites

- Python 3.8+
- Docker and Docker Compose (recommended) **OR** PostgreSQL 12+ with pgvector
- OpenAI API key

## 🚀 Quick Start with Docker (Recommended)

The easiest way to get started is using Docker with the **Pagila sample DVD rental database**:

```bash
# 1. Clone the repository and navigate to it
cd db-rag

# 2. Copy and configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Run setup script (includes Pagila database)
chmod +x setup_docker.sh
./setup_docker.sh

# 4. Start querying!
python examples/cli.py
```

This will:
- ✅ Start PostgreSQL 16 with pgvector extension
- ✅ Load Pagila sample database (16 tables with DVD rental data)
- ✅ Create DB-RAG tables and indexes
- ✅ Load sample policy documents
- ✅ Run verification tests

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed Docker documentation.

## 🐳 Manual Installation (Without Docker)

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up PostgreSQL with pgvector**:
```bash
# Install pgvector extension (macOS with Homebrew)
brew install pgvector

# Or on Ubuntu/Debian
sudo apt-get install postgresql-14-pgvector

# Connect to your database and enable the extension
psql -d your_database -c "CREATE EXTENSION vector;"
```

3. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your database credentials and OpenAI API key
```

4. **Initialize the database schema**:
```bash
psql -d your_database -f script.sql
```

## ⚙️ Configuration

Edit `.env` file:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=corp_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_SCHEMA=public

# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small

# RAG Configuration
ENABLE_VECTOR_SEARCH=true
ENABLE_SQL_SEARCH=true
MAX_CONTEXT_TABLES=5
MAX_VECTOR_RESULTS=3
```

## 📖 Usage

### Example Queries for Pagila Database

With the Docker setup, you can immediately query the Pagila DVD rental database:

```python
from main import DBRAG

with DBRAG() as rag:
    rag.initialize()
    
    # Customer analytics
    result = rag.query("How many customers do we have?")
    print(result['answer'])
    
    # Rental analytics
    result = rag.query("What are the most popular film categories?")
    print(result['answer'])
    
    # Policy questions (vector search)
    result = rag.query("What is the DVD rental policy?")
    print(result['answer'])
    
    # Hybrid query (SQL + Vector)
    result = rag.query("How many rentals did we have yesterday and what's our refund policy?")
    print(result['answer'])
```

### Basic Example

```python
from main import DBRAG

# Initialize the system
with DBRAG() as rag:
    # Initialize database structures and metadata
    rag.initialize()
    
    # Ask a question
    result = rag.query("What was our total sales last month?")
    print(result['answer'])
```

### Advanced Usage

```python
from main import DBRAG
from dotenv import load_dotenv

load_dotenv()

with DBRAG() as rag:
    # Initialize system
    rag.initialize()
    
    # Sync metadata catalog (analyzes all tables)
    rag.sync_metadata(force_update=False)
    
    # Add unstructured documents
    doc_id = rag.add_document(
        content="Our refund policy allows returns within 30 days...",
        metadata={"source": "policy_handbook", "department": "customer_service"}
    )
    
    # Query structured data only
    sql_result = rag.query_sql_only("Show top 10 customers by revenue")
    print(f"SQL: {sql_result['sql']}")
    print(f"Results: {sql_result['results']}")
    
    # Search documents only
    doc_result = rag.search_documents_only("What is the refund policy?")
    for doc in doc_result['documents']:
        print(f"Similarity: {doc['similarity']:.3f}")
        print(f"Content: {doc['content']}")
    
    # Hybrid query (automatic routing)
    hybrid_result = rag.query(
        "What were our sales yesterday and what is our refund policy?"
    )
    print(f"Answer: {hybrid_result['answer']}")
```

### Command Line Interface

```python
# examples/cli.py
from main import DBRAG
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    with DBRAG() as rag:
        rag.initialize()
        
        print("DB-RAG Query Interface")
        print("Type 'quit' to exit\n")
        
        while True:
            query = input("Enter your question: ")
            if query.lower() in ['quit', 'exit']:
                break
            
            result = rag.query(query)
            print(f"\nAnswer: {result['answer']}\n")
            
            if result.get('sql_results'):
                print(f"SQL Used: {result['sql_results'].get('sql')}\n")

if __name__ == "__main__":
    main()
```

## 🧪 Testing

### Run End-to-End Tests

The test suite includes comprehensive tests for all query types:

```bash
# Make sure Docker containers are running
docker-compose up -d

# Run the complete test suite
python test_e2e.py
```

Test categories include:
- **Customer Analytics**: Customer counts, top customers, demographics
- **Rental Analytics**: Popular categories, revenue, rental patterns
- **Inventory Management**: Film counts, store inventory, categories
- **Staff Analytics**: Employee counts, store assignments
- **Policy Questions**: Vector search for policies and procedures
- **Hybrid Queries**: Combined SQL and document search

### Individual Example Scripts

```bash
# Interactive CLI
python examples/cli.py

# Document ingestion examples
python examples/ingest_documents.py

# SQL generation tests
python examples/test_sql_generation.py

# Hybrid query tests
python examples/test_hybrid_queries.py
```

## 🔧 API Reference

### DBRAG Class

```python
class DBRAG:
    def __init__(self, config: Optional[Config] = None)
    def initialize() -> None
    def sync_metadata(force_update: bool = False) -> None
    def add_document(content: str, metadata: dict = None) -> str
    def query(question: str) -> dict
    def query_sql_only(question: str) -> dict
    def search_documents_only(query: str) -> dict
    def close() -> None
```

### Response Format

```python
{
    "success": True,
    "query": "What was our total sales last month?",
    "answer": "Your total sales last month were $1,234,567...",
    "routing": [...],  # Which agents were used
    "sql_results": {   # If SQL agent was used
        "sql": "SELECT SUM(amount) FROM sales WHERE...",
        "tables_used": ["sales"],
        "results": [...],
        "row_count": 1
    },
    "vector_results": {  # If vector agent was used
        "documents": [...],
        "count": 3
    }
}
```

## 🗂️ Project Structure

```
db-rag/
├── config.py              # Configuration management
├── database.py            # Database connection and introspection
├── metadata_catalog.py    # Table discovery and metadata management
├── sql_agent.py           # SQL query generation and execution
├── vector_agent.py        # Vector search for unstructured data
├── orchestrator.py        # Main routing and orchestration logic
├── main.py                # Entry point and high-level API
├── test_e2e.py            # End-to-end test suite
├── script.sql             # Database schema initialization (legacy)
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment configuration
├── docker-compose.yml     # Docker orchestration
├── setup_docker.sh        # Automated Docker setup script
├── DOCKER_SETUP.md       # Detailed Docker documentation
├── README.md             # This file
├── docker/
│   ├── Dockerfile         # PostgreSQL + pgvector image
│   └── init-scripts/      # Database initialization scripts
│       ├── 01-load-pagila.sh
│       ├── 02-setup-dbrag-tables.sh
│       └── 03-load-sample-documents.sh
└── examples/
    ├── cli.py             # Interactive CLI
    ├── ingest_documents.py
    ├── test_sql_generation.py
    ├── test_hybrid_queries.py
    └── README.md
```

## 🎬 Pagila Sample Database

The Docker setup includes the **Pagila** database - a PostgreSQL port of the MySQL Sakila sample database representing a DVD rental store. It includes:

### Database Schema (16 Tables)

**Core Business Tables:**
- `customer` - Customer information (599 customers)
- `film` - Movie catalog (1,000 films)
- `rental` - Rental transactions (16,044 rentals)
- `payment` - Payment records
- `inventory` - Film inventory by store
- `store` - Store locations (2 stores)
- `staff` - Employee information

**Supporting Tables:**
- `actor`, `film_actor` - Actor information and film relationships
- `category`, `film_category` - Film categories (Action, Comedy, Drama, etc.)
- `address`, `city`, `country` - Location data
- `language` - Film languages

### Sample Questions You Can Ask

**Customer Analytics:**
- "How many customers do we have?"
- "Show me customers from California"
- "Who are our top 10 customers by rental count?"

**Rental & Revenue:**
- "What was our total rental revenue last month?"
- "Which films have been rented the most?"
- "What's the average rental duration?"

**Inventory & Films:**
- "How many films are in the Action category?"
- "Which store has more inventory?"
- "List all films starring 'PENELOPE GUINESS'"

**Policy Questions (Vector Search):**
- "What is the DVD rental policy?"
- "How do refunds work?"
- "What are the membership benefits?"

**Hybrid Queries:**
- "Show me top customers and explain our refund policy"
- "What's our most popular category and what's the rental policy?"
├── .env.example          # Example environment configuration
└── README.md             # This file
```

## 🎓 How It Works

### 1. Metadata Catalog
The system automatically introspects your database schema and uses an LLM to generate:
- Human-readable descriptions of each table
- Business context and common use cases
- Example questions that can be answered
- Vector embeddings for semantic table discovery

### 2. Query Routing
When you ask a question, the orchestrator:
1. Analyzes the intent (structured vs unstructured data)
2. Routes to appropriate agent(s)
3. May call both agents for hybrid queries

### 3. SQL Generation
The SQL Agent:
1. Discovers relevant tables using vector similarity
2. Retrieves detailed schema information
3. Generates optimized SQL queries
4. Validates queries before execution
5. Returns structured results

### 4. Vector Search
The Vector Agent:
1. Generates embeddings for queries
2. Performs cosine similarity search
3. Returns relevant documents with scores

### 5. Response Synthesis
The orchestrator combines all results into a coherent natural language answer.

## 🔮 Extensibility

### Adding New RDBMS Support

The system is designed for extensibility. To add support for other databases:

1. **Create a new database manager** (e.g., `mysql_database.py`)
2. **Implement the same interface** as `DatabaseManager`
3. **Update configuration** to support new database types

```python
# Example: MySQL support
class MySQLDatabaseManager(DatabaseManager):
    def get_connection_string(self):
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
```

### Adding New Data Sources

To add unstructured data sources (PDFs, APIs, etc.):

1. **Create a data loader** module
2. **Chunk and embed documents**
3. **Use `vector_agent.add_document()`** to store

```python
# Example: PDF ingestion
from PyPDF2 import PdfReader
from main import DBRAG

def ingest_pdf(pdf_path: str, rag: DBRAG):
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages):
        content = page.extract_text()
        rag.add_document(
            content=content,
            metadata={"source": pdf_path, "page": i}
        )
```

## 🐛 Troubleshooting

### pgvector not installed
```bash
# Install pgvector extension
sudo apt-get install postgresql-14-pgvector
# Or brew install pgvector on macOS
```

### Connection errors
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure database exists

### API rate limits
- Adjust `temperature` and `max_tokens` in config
- Consider caching embeddings
- Use smaller embedding models if needed

## 📚 Examples

See the `examples/` directory for:
- CLI interface
- Batch document ingestion
- Custom query workflows
- Integration patterns

## 🤝 Contributing

Contributions are welcome! Areas for enhancement:
- Additional RDBMS support (MySQL, SQL Server, Oracle)
- Query optimization and caching
- Multi-language support
- Enhanced error handling
- Performance benchmarks

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

- Built with OpenAI's GPT-4 and embedding models
- Uses pgvector for efficient vector similarity search
- Inspired by modern RAG architectures


References:

https://wiki.postgresql.org/wiki/Sample_Databases
https://github.com/devrimgunduz/pagila