# DB-RAG Usage Guide

This guide provides detailed instructions for using the DB-RAG system.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Basic Usage](#basic-usage)
4. [Advanced Usage](#advanced-usage)
5. [CLI Usage](#cli-usage)
6. [API Reference](#api-reference)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

## Installation

### Standard Installation

```bash
# Clone the repository
git clone https://github.com/sankar-v/db-rag.git
cd db-rag

# Install dependencies
pip install -r requirements.txt
```

### Development Installation

```bash
# Install in development mode
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# OpenAI API Key (Required)
OPENAI_API_KEY=sk-...

# Database Configuration
DB_TYPE=sqlite
DB_NAME=my_database.db

# Vector Store Configuration
VECTOR_STORE_TYPE=chroma
VECTOR_STORE_PATH=./chroma_db

# Model Configuration
EMBEDDING_MODEL=text-embedding-ada-002
LLM_MODEL=gpt-3.5-turbo

# RAG Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
```

### Database Connection Strings

#### SQLite
```python
config.db_type = "sqlite"
config.db_name = "database.db"
```

#### PostgreSQL
```python
config.db_type = "postgresql"
config.db_host = "localhost"
config.db_port = 5432
config.db_name = "mydb"
config.db_user = "username"
config.db_password = "password"
```

#### MySQL
```python
config.db_type = "mysql"
config.db_host = "localhost"
config.db_port = 3306
config.db_name = "mydb"
config.db_user = "username"
config.db_password = "password"
```

## Basic Usage

### Simple Query Example

```python
from db_rag import RAGEngine
from db_rag.config import Config

# Initialize
config = Config()
rag = RAGEngine(config)

# Ingest documents
rag.ingest_documents("./documents")

# Query
result = rag.query("What products are available?")
print(result["answer"])

# Clean up
rag.close()
```

### Step-by-Step Workflow

1. **Setup Configuration**
```python
from db_rag.config import Config

config = Config()
config.db_type = "sqlite"
config.db_name = "example.db"
```

2. **Initialize RAG Engine**
```python
from db_rag import RAGEngine

rag = RAGEngine(config)
```

3. **Ingest Documents**
```python
# From a directory
rag.ingest_documents("./docs", source_type="directory")

# From a single file
rag.ingest_documents("./file.pdf", source_type="file")

# Include database schema for semantic search
rag.ingest_database_schema()
```

4. **Query the System**
```python
# Query both database and documents
result = rag.query("What is the return policy?")

# Query only database
result = rag.query("List all products", search_db=True, search_docs=False)

# Query only documents
result = rag.query("Return policy?", search_db=False, search_docs=True)
```

5. **Access Results**
```python
# Get the answer
print(result["answer"])

# Get database results
if result["database_results"]:
    sql = result["database_results"]["sql_query"]
    rows = result["database_results"]["results"]

# Get document results
if result["document_results"]:
    docs = result["document_results"]["documents"]
```

## Advanced Usage

### Using Components Separately

#### Database Connector

```python
from db_rag import DatabaseConnector
from db_rag.config import Config

config = Config()
db = DatabaseConnector(config)

# Get table information
tables = db.get_table_names()
schema = db.get_table_schema("products")

# Execute custom SQL
results = db.execute_query("SELECT * FROM products WHERE price > 100")

# Get sample data
samples = db.get_sample_data("products", limit=10)

db.close()
```

#### Document Loader

```python
from db_rag import DocumentLoader
from db_rag.config import Config

config = Config()
loader = DocumentLoader(config)

# Load different file types
pdf_docs = loader.load_pdf_file("document.pdf")
text_docs = loader.load_text_file("notes.txt")
docx_docs = loader.load_docx_file("report.docx")

# Load from directory
all_docs = loader.load_directory("./documents", glob_pattern="**/*.pdf")

# Load from raw text
docs = loader.load_from_text(
    "This is my content",
    metadata={"source": "manual_entry"}
)
```

#### Vector Store Manager

```python
from db_rag import VectorStoreManager
from db_rag.config import Config

config = Config()
vector_store = VectorStoreManager(config)

# Add documents
vector_store.add_documents(documents)

# Add raw texts
texts = ["Document 1", "Document 2"]
metadatas = [{"source": "src1"}, {"source": "src2"}]
vector_store.add_texts(texts, metadatas)

# Search
results = vector_store.similarity_search("query", k=5)

# Search with scores
results_with_scores = vector_store.similarity_search_with_score("query", k=5)

# Search with metadata filter
results = vector_store.similarity_search(
    "query",
    k=5,
    filter={"source": "src1"}
)
```

### Custom Configuration

```python
from db_rag.config import Config

config = Config()

# Customize chunking
config.chunk_size = 500
config.chunk_overlap = 50

# Customize retrieval
config.top_k_results = 10

# Use different models
config.embedding_model = "text-embedding-ada-002"
config.llm_model = "gpt-4"

# Use custom vector store path
config.vector_store_path = "./my_vectors"
```

## CLI Usage

### Ingest Documents

```bash
# Ingest a directory
python -m db_rag.cli ingest ./documents

# Ingest a single file
python -m db_rag.cli ingest ./file.pdf --type file

# Ingest documents and database schema
python -m db_rag.cli ingest ./documents --include-schema
```

### Query the System

```bash
# Basic query
python -m db_rag.cli query "What products do we have?"

# Query with verbose output
python -m db_rag.cli query "Show all products" --verbose

# Query only database
python -m db_rag.cli query "List products" --db-only

# Query only documents
python -m db_rag.cli query "Return policy?" --docs-only
```

### Database Information

```bash
# Show database schema
python -m db_rag.cli db-info

# Show schema with sample data
python -m db_rag.cli db-info --sample
```

## API Reference

### RAGEngine

Main interface for the RAG system.

**Methods:**

- `__init__(config: Config)`: Initialize the engine
- `ingest_documents(source: str, source_type: str = "auto")`: Ingest documents
- `query(question: str, search_db: bool = True, search_docs: bool = True)`: Query the system
- `query_database(natural_language_query: str)`: Query only database
- `query_documents(query: str, k: Optional[int] = None)`: Query only documents
- `close()`: Clean up resources

### DatabaseConnector

Interface to relational databases.

**Methods:**

- `__init__(config: Config)`: Initialize connector
- `get_table_names()`: Get list of tables
- `get_table_schema(table_name: str)`: Get table schema
- `execute_query(query: str)`: Execute SQL query
- `get_sample_data(table_name: str, limit: int = 5)`: Get sample rows
- `get_database_schema_text()`: Get schema as text
- `close()`: Close connection

### DocumentLoader

Load documents from various sources.

**Methods:**

- `__init__(config: Config)`: Initialize loader
- `load_file(file_path: str)`: Load a file
- `load_directory(directory_path: str, glob_pattern: str = "**/*.*")`: Load directory
- `load_text_file(file_path: str)`: Load text file
- `load_pdf_file(file_path: str)`: Load PDF file
- `load_docx_file(file_path: str)`: Load DOCX file
- `load_from_text(text: str, metadata: Optional[dict] = None)`: Load from string

### VectorStoreManager

Manage vector embeddings.

**Methods:**

- `__init__(config: Config)`: Initialize manager
- `add_documents(documents: List[Document])`: Add documents
- `add_texts(texts: List[str], metadatas: Optional[List[dict]] = None)`: Add texts
- `similarity_search(query: str, k: Optional[int] = None, filter: Optional[dict] = None)`: Search
- `similarity_search_with_score(query: str, k: Optional[int] = None, filter: Optional[dict] = None)`: Search with scores
- `delete_collection()`: Delete vector store

## Examples

### Example 1: E-commerce Query System

```python
from db_rag import RAGEngine
from db_rag.config import Config

# Setup
config = Config()
config.db_name = "ecommerce.db"
rag = RAGEngine(config)

# Ingest product documentation
rag.ingest_documents("./product_docs")
rag.ingest_database_schema()

# Query
result = rag.query("What electronics are in stock under $500?")
print(result["answer"])

rag.close()
```

### Example 2: Customer Support System

```python
from db_rag import RAGEngine
from db_rag.config import Config

config = Config()
rag = RAGEngine(config)

# Ingest support documentation
rag.ingest_documents("./support_docs")

# Handle customer query
customer_query = "How do I return a product?"
result = rag.query(customer_query)

# Access answer and sources
answer = result["answer"]
docs = result["document_results"]["documents"]

print(f"Answer: {answer}")
print(f"Sources: {len(docs)} documents found")

rag.close()
```

### Example 3: Research Database

```python
from db_rag import RAGEngine
from db_rag.config import Config

# Connect to PostgreSQL research database
config = Config()
config.db_type = "postgresql"
config.db_host = "localhost"
config.db_name = "research"
config.db_user = "researcher"
config.db_password = "password"

rag = RAGEngine(config)

# Ingest research papers
rag.ingest_documents("./papers", source_type="directory")

# Query across structured data and papers
result = rag.query("What experiments were conducted in 2023 on topic X?")
print(result["answer"])

rag.close()
```

## Troubleshooting

### Common Issues

**Issue: ModuleNotFoundError**
```
Solution: Install all dependencies
pip install -r requirements.txt
```

**Issue: OpenAI API Key Error**
```
Solution: Set OPENAI_API_KEY in .env file or environment
export OPENAI_API_KEY=sk-...
```

**Issue: Database Connection Error**
```
Solution: Check database credentials and connection string
- For SQLite: Ensure file path is correct
- For PostgreSQL/MySQL: Verify host, port, username, password
```

**Issue: Vector Store Initialization Error**
```
Solution: Ensure vector store directory is writable
mkdir -p ./chroma_db
chmod 755 ./chroma_db
```

**Issue: Document Loading Error**
```
Solution: Ensure file format is supported (PDF, TXT, DOCX)
Check file permissions and encoding
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Tips

1. **Chunk Size**: Larger chunks (1000-2000) for general content, smaller (200-500) for code/technical docs
2. **Overlap**: 10-20% of chunk size is optimal
3. **Top K**: Start with 3-5 results, adjust based on needs
4. **Vector Store**: ChromaDB works well for most use cases

### Getting Help

- Check the [README.md](README.md) for quick start
- Review [examples/](examples/) for working code
- Open an issue on GitHub for bugs or questions
