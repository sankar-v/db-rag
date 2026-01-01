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
class MetadataDatabaseConfig:
    """Metadata database configuration (control plane)"""
    host: str
    port: int
    database: str
    user: str
    password: str
    enabled: bool = True  # If False, use in-memory/file-based storage
    
    @classmethod
    def from_env(cls) -> 'MetadataDatabaseConfig':
        """Load metadata database configuration from environment variables"""
        return cls(
            host=os.getenv("METADATA_DB_HOST", os.getenv("DB_HOST", "localhost")),
            port=int(os.getenv("METADATA_DB_PORT", os.getenv("DB_PORT", "5432"))),
            database=os.getenv("METADATA_DB_NAME", "dbrag_metadata"),
            user=os.getenv("METADATA_DB_USER", os.getenv("DB_USER", "postgres")),
            password=os.getenv("METADATA_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
            enabled=os.getenv("USE_METADATA_DB", "true").lower() == "true"
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
class CacheConfig:
    """Cache configuration (Redis)"""
    enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Cache TTLs (seconds)
    embedding_cache_ttl: int = 86400  # 24 hours
    metadata_cache_ttl: int = 3600    # 1 hour
    query_cache_ttl: int = 300        # 5 minutes
    
    # Cache size limits
    max_cache_size_mb: int = 1024     # 1GB
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """Load cache configuration from environment variables"""
        return cls(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            embedding_cache_ttl=int(os.getenv("EMBEDDING_CACHE_TTL", "86400")),
            metadata_cache_ttl=int(os.getenv("METADATA_CACHE_TTL", "3600")),
            query_cache_ttl=int(os.getenv("QUERY_CACHE_TTL", "300")),
            max_cache_size_mb=int(os.getenv("MAX_CACHE_SIZE_MB", "1024"))
        )
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@dataclass
class CeleryConfig:
    """Celery task queue configuration"""
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list = None
    timezone: str = "UTC"
    enable_utc: bool = True
    worker_concurrency: int = 4
    task_acks_late: bool = True
    task_reject_on_worker_lost: bool = True
    
    # Result backend configuration
    result_backend_type: str = "redis"  # redis, postgres, or hybrid
    result_expires: int = 86400  # 24 hours (0 = never expire for postgres)
    
    # PostgreSQL result backend (enterprise)
    database_table_names: dict = None
    
    def __post_init__(self):
        if self.accept_content is None:
            self.accept_content = ['json']
        if self.database_table_names is None:
            self.database_table_names = {
                'task': 'celery_taskmeta',
                'group': 'celery_groupmeta',
            }
    
    @classmethod
    def from_env(cls) -> 'CeleryConfig':
        """Load Celery configuration from environment variables"""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_password = os.getenv("REDIS_PASSWORD")
        
        # Broker URL (always Redis or RabbitMQ)
        broker_type = os.getenv("CELERY_BROKER", "redis")  # redis or rabbitmq
        
        if broker_type == "rabbitmq":
            rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
            rabbitmq_port = os.getenv("RABBITMQ_PORT", "5672")
            rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
            rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
            rabbitmq_vhost = os.getenv("RABBITMQ_VHOST", "/")
            broker_url = f"amqp://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}:{rabbitmq_port}/{rabbitmq_vhost}"
        else:
            if redis_password:
                broker_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
            else:
                broker_url = f"redis://{redis_host}:{redis_port}/0"
        
        # Result backend (Redis, PostgreSQL, or Hybrid)
        result_backend_type = os.getenv("CELERY_RESULT_BACKEND", "redis")  # redis, postgres, hybrid
        
        if result_backend_type == "postgres":
            # Use PostgreSQL for persistent result storage
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "dbrag")
            db_user = os.getenv("DB_USER", "dbrag_user")
            db_password = os.getenv("DB_PASSWORD", "")
            result_backend = f"db+postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            result_expires = 0  # Never expire with PostgreSQL
        elif result_backend_type == "hybrid":
            # Hybrid: Redis for speed, PostgreSQL for persistence
            # Store in both, query from Redis first
            result_backend = f"redis://{redis_host}:{redis_port}/1"
            result_expires = 3600  # 1 hour in Redis, archive to PostgreSQL
        else:
            # Default: Redis only
            if redis_password:
                result_backend = f"redis://:{redis_password}@{redis_host}:{redis_port}/1"
            else:
                result_backend = f"redis://{redis_host}:{redis_port}/1"
            result_expires = int(os.getenv("CELERY_RESULT_EXPIRES", "3600"))  # 1 hour default
        
        return cls(
            broker_url=broker_url,
            result_backend=result_backend,
            result_backend_type=result_backend_type,
            result_expires=result_expires,
            worker_concurrency=int(os.getenv("CELERY_WORKER_CONCURRENCY", "4")),
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
    
    # Async processing
    async_document_processing: bool = True
    async_metadata_updates: bool = True
    
    # Batch processing
    embedding_batch_size: int = 100
    
    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """Load RAG configuration from environment variables"""
        return cls(
            enable_vector_search=os.getenv("ENABLE_VECTOR_SEARCH", "true").lower() == "true",
            enable_sql_search=os.getenv("ENABLE_SQL_SEARCH", "true").lower() == "true",
            max_context_tables=int(os.getenv("MAX_CONTEXT_TABLES", "5")),
            max_vector_results=int(os.getenv("MAX_VECTOR_RESULTS", "3")),
            async_document_processing=os.getenv("ASYNC_DOCUMENT_PROCESSING", "true").lower() == "true",
            async_metadata_updates=os.getenv("ASYNC_METADATA_UPDATES", "true").lower() == "true",
            embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
        )


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.database = DatabaseConfig.from_env()
        self.metadata_db = MetadataDatabaseConfig.from_env()
        self.llm = LLMConfig.from_env()
        self.rag = RAGConfig.from_env()
        self.cache = CacheConfig.from_env()
        self.celery = CeleryConfig.from_env()
    
    @classmethod
    def load(cls) -> 'Config':
        """Load all configurations"""
        return cls()
