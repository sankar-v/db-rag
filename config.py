"""
Configuration management for DB-RAG system
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str = "public"
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Load configuration from environment variables"""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "corp_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            schema=os.getenv("DB_SCHEMA", "public")
        )
    
    def get_connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str = "openai"  # Future: support anthropic, azure, etc.
    model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    temperature: float = 0.0
    max_tokens: int = 4000
    api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Load LLM configuration from environment variables"""
        return cls(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            api_key=os.getenv("OPENAI_API_KEY")
        )


@dataclass
class RAGConfig:
    """RAG-specific configuration"""
    enable_vector_search: bool = True
    enable_sql_search: bool = True
    max_context_tables: int = 5
    max_vector_results: int = 3
    metadata_catalog_table: str = "table_metadata_catalog"
    documents_table: str = "company_documents"
    enable_query_validation: bool = True
    enable_auto_metadata_sync: bool = True
    
    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """Load RAG configuration from environment variables"""
        return cls(
            enable_vector_search=os.getenv("ENABLE_VECTOR_SEARCH", "true").lower() == "true",
            enable_sql_search=os.getenv("ENABLE_SQL_SEARCH", "true").lower() == "true",
            max_context_tables=int(os.getenv("MAX_CONTEXT_TABLES", "5")),
            max_vector_results=int(os.getenv("MAX_VECTOR_RESULTS", "3"))
        )


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.database = DatabaseConfig.from_env()
        self.llm = LLMConfig.from_env()
        self.rag = RAGConfig.from_env()
    
    @classmethod
    def load(cls) -> 'Config':
        """Load all configurations"""
        return cls()
