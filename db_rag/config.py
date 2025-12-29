"""
Configuration management for DB-RAG system.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Configuration for DB-RAG system."""
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    # Database Configuration
    db_type: str = os.getenv("DB_TYPE", "sqlite")  # sqlite, mysql, postgresql
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "database.db")
    db_user: str = os.getenv("DB_USER", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    
    # Vector Store Configuration
    vector_store_type: str = os.getenv("VECTOR_STORE_TYPE", "chroma")  # chroma, faiss
    vector_store_path: str = os.getenv("VECTOR_STORE_PATH", "./chroma_db")
    
    # RAG Configuration
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    top_k_results: int = int(os.getenv("TOP_K_RESULTS", "5"))
    
    def get_db_url(self) -> str:
        """Generate database URL based on configuration."""
        if self.db_type == "sqlite":
            return f"sqlite:///{self.db_name}"
        elif self.db_type == "mysql":
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        elif self.db_type == "postgresql":
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        return True


# Global configuration instance
config = Config()
