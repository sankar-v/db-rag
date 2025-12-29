"""
DB-RAG: A RAG system for structured and unstructured data.

This package provides tools for building RAG (Retrieval-Augmented Generation) 
systems that work with both:
- Structured data from relational databases (MySQL, PostgreSQL, SQLite)
- Unstructured data from various sources (PDFs, text files, documents)
"""

__version__ = "0.1.0"

from .db_connector import DatabaseConnector
from .document_loader import DocumentLoader
from .vector_store import VectorStoreManager
from .rag_engine import RAGEngine

__all__ = [
    "DatabaseConnector",
    "DocumentLoader", 
    "VectorStoreManager",
    "RAGEngine",
]
