# DB-RAG: Retrieval-Augmented Generation for Structured and Unstructured Data

A powerful RAG (Retrieval-Augmented Generation) system that seamlessly integrates:
- **Structured data** from relational databases (MySQL, PostgreSQL, SQLite)
- **Unstructured data** from various document sources (PDFs, text files, DOCX)

## Features

✨ **Unified Query Interface**: Ask questions in natural language and get answers from both database records and documents

🗄️ **Multi-Database Support**: Works with SQLite, MySQL, and PostgreSQL

📄 **Multiple Document Formats**: Supports PDF, TXT, and DOCX files

🔍 **Semantic Search**: Uses vector embeddings for intelligent document retrieval

🤖 **AI-Powered**: Leverages OpenAI's GPT models for natural language understanding and SQL generation

⚡ **Easy to Use**: Simple API for both basic and advanced use cases

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sankar-v/db-rag.git
cd db-rag
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Quick Start

```python
from db_rag import RAGEngine
from db_rag.config import Config

# Initialize
config = Config()
rag = RAGEngine(config)

# Ingest documents
rag.ingest_documents("./documents", source_type="directory")

# Ask questions
result = rag.query("What products are in stock?")
print(result["answer"])

# Clean up
rag.close()
```

## Configuration

Configure the system using environment variables in `.env`:

```bash
# OpenAI API Key (Required)
OPENAI_API_KEY=your-key-here

# Database Settings
DB_TYPE=sqlite              # Options: sqlite, mysql, postgresql
DB_NAME=database.db         # Database name or file path
DB_HOST=localhost           # For MySQL/PostgreSQL
DB_PORT=5432               # For MySQL/PostgreSQL
DB_USER=username           # For MySQL/PostgreSQL
DB_PASSWORD=password       # For MySQL/PostgreSQL

# Vector Store Settings
VECTOR_STORE_TYPE=chroma    # Options: chroma
VECTOR_STORE_PATH=./chroma_db

# Model Settings
EMBEDDING_MODEL=text-embedding-ada-002
LLM_MODEL=gpt-3.5-turbo

# RAG Settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
```

## Usage Examples

### Basic Example

See `examples/basic_example.py` for a complete working example:

```bash
python examples/basic_example.py
```

This example demonstrates:
- Setting up a SQLite database with sample data
- Creating and ingesting documents
- Querying both structured and unstructured data
- Getting AI-generated answers

### Advanced Usage

#### Query Database Only

```python
result = rag.query("Show all products", search_db=True, search_docs=False)
```

#### Query Documents Only

```python
result = rag.query("What is the return policy?", search_db=False, search_docs=True)
```

#### Use Components Directly

```python
from db_rag import DatabaseConnector, DocumentLoader, VectorStoreManager

# Database operations
db = DatabaseConnector(config)
tables = db.get_table_names()
results = db.execute_query("SELECT * FROM products")

# Document loading
loader = DocumentLoader(config)
docs = loader.load_file("document.pdf")

# Vector search
vector_store = VectorStoreManager(config)
vector_store.add_documents(docs)
results = vector_store.similarity_search("query", k=5)
```

### Working with Different Databases

#### SQLite
```python
config = Config()
config.db_type = "sqlite"
config.db_name = "my_database.db"
```

#### PostgreSQL
```python
config = Config()
config.db_type = "postgresql"
config.db_host = "localhost"
config.db_port = 5432
config.db_name = "mydb"
config.db_user = "user"
config.db_password = "password"
```

#### MySQL
```python
config = Config()
config.db_type = "mysql"
config.db_host = "localhost"
config.db_port = 3306
config.db_name = "mydb"
config.db_user = "user"
config.db_password = "password"
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   RAGEngine                     │
│  (Unified query interface)                      │
└──────────────┬─────────────────┬────────────────┘
               │                 │
    ┌──────────▼─────────┐  ┌───▼──────────────┐
    │  DatabaseConnector │  │ VectorStoreManager│
    │  (Structured Data) │  │(Unstructured Data)│
    └──────────┬─────────┘  └───┬──────────────┘
               │                 │
        ┌──────▼──────┐   ┌─────▼──────┐
        │  SQL DB     │   │ Documents   │
        │ (MySQL/PG/  │   │ (PDF/TXT/   │
        │  SQLite)    │   │  DOCX)      │
        └─────────────┘   └─────────────┘
```

### Components

- **RAGEngine**: Main interface for querying both data sources
- **DatabaseConnector**: Manages connections to relational databases and executes SQL queries
- **DocumentLoader**: Loads and processes documents from various formats
- **VectorStoreManager**: Handles vector embeddings and semantic search
- **Config**: Configuration management for all components

## API Reference

### RAGEngine

```python
class RAGEngine:
    def __init__(self, config: Config)
    def ingest_documents(self, source: str, source_type: str = "auto") -> None
    def query(self, question: str, search_db: bool = True, search_docs: bool = True) -> Dict
    def query_database(self, natural_language_query: str) -> Dict
    def query_documents(self, query: str, k: Optional[int] = None) -> Dict
    def close(self) -> None
```

### DatabaseConnector

```python
class DatabaseConnector:
    def __init__(self, config: Config)
    def get_table_names(self) -> List[str]
    def get_table_schema(self, table_name: str) -> List[Dict]
    def execute_query(self, query: str) -> List[Dict]
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]
    def close(self) -> None
```

### DocumentLoader

```python
class DocumentLoader:
    def __init__(self, config: Config)
    def load_file(self, file_path: str) -> List[Document]
    def load_directory(self, directory_path: str, glob_pattern: str = "**/*.*") -> List[Document]
    def load_from_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]
```

### VectorStoreManager

```python
class VectorStoreManager:
    def __init__(self, config: Config)
    def add_documents(self, documents: List[Document]) -> None
    def add_texts(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> None
    def similarity_search(self, query: str, k: Optional[int] = None) -> List[Document]
    def similarity_search_with_score(self, query: str, k: Optional[int] = None) -> List[Tuple[Document, float]]
```

## Testing

Run the test suite:

```bash
python tests/test_db_rag.py
```

Note: Some tests require the `OPENAI_API_KEY` environment variable to be set.

## Use Cases

- **Enterprise Knowledge Base**: Query both structured customer data and unstructured documentation
- **E-commerce**: Search product databases while accessing policy documents
- **Research**: Combine structured research data with paper repositories
- **Customer Support**: Access customer records and support documentation simultaneously
- **Data Analytics**: Query databases while referencing analysis reports

## Requirements

- Python 3.8+
- OpenAI API key
- Supported databases: SQLite (built-in), MySQL, PostgreSQL

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.

## Acknowledgments

Built with:
- [LangChain](https://github.com/langchain-ai/langchain) - Framework for LLM applications
- [OpenAI](https://openai.com/) - LLM and embedding models
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit
