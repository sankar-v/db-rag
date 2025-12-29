"""
Vector store manager for storing and retrieving embeddings.
"""

from typing import List, Optional
import logging

from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.vectorstores.base import VectorStore

from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages vector store for document embeddings."""
    
    def __init__(self, config: Config):
        """
        Initialize vector store manager.
        
        Args:
            config: Configuration object with vector store settings
        """
        self.config = config
        self.embeddings = OpenAIEmbeddings(
            model=config.embedding_model,
            openai_api_key=config.openai_api_key
        )
        self.vector_store: Optional[VectorStore] = None
        self._initialize_vector_store()
    
    def _initialize_vector_store(self) -> None:
        """Initialize or load existing vector store."""
        try:
            if self.config.vector_store_type == "chroma":
                # Try to load existing store, or create new one
                self.vector_store = Chroma(
                    persist_directory=self.config.vector_store_path,
                    embedding_function=self.embeddings
                )
                logger.info(f"Initialized Chroma vector store at {self.config.vector_store_path}")
            else:
                raise ValueError(f"Unsupported vector store type: {self.config.vector_store_type}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of Document objects to add
        """
        if not documents:
            logger.warning("No documents to add")
            return
        
        try:
            if self.vector_store is None:
                # Create new vector store with documents
                if self.config.vector_store_type == "chroma":
                    self.vector_store = Chroma.from_documents(
                        documents=documents,
                        embedding=self.embeddings,
                        persist_directory=self.config.vector_store_path
                    )
            else:
                # Add to existing vector store
                self.vector_store.add_documents(documents)
            
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> None:
        """
        Add raw texts to the vector store.
        
        Args:
            texts: List of text strings to add
            metadatas: Optional list of metadata dictionaries
        """
        if not texts:
            logger.warning("No texts to add")
            return
        
        try:
            if self.vector_store is None:
                # Create new vector store with texts
                if self.config.vector_store_type == "chroma":
                    self.vector_store = Chroma.from_texts(
                        texts=texts,
                        embedding=self.embeddings,
                        metadatas=metadatas,
                        persist_directory=self.config.vector_store_path
                    )
            else:
                # Add to existing vector store
                self.vector_store.add_texts(texts, metadatas=metadatas)
            
            logger.info(f"Added {len(texts)} texts to vector store")
        except Exception as e:
            logger.error(f"Failed to add texts: {e}")
            raise
    
    def similarity_search(
        self, 
        query: str, 
        k: Optional[int] = None,
        filter: Optional[dict] = None
    ) -> List[Document]:
        """
        Search for similar documents.
        
        Args:
            query: Query string
            k: Number of results to return (defaults to config.top_k_results)
            filter: Optional metadata filter
            
        Returns:
            List of similar documents
        """
        if self.vector_store is None:
            logger.warning("Vector store is empty")
            return []
        
        k = k or self.config.top_k_results
        
        try:
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            logger.info(f"Found {len(results)} similar documents")
            return results
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise
    
    def similarity_search_with_score(
        self, 
        query: str, 
        k: Optional[int] = None,
        filter: Optional[dict] = None
    ) -> List[tuple[Document, float]]:
        """
        Search for similar documents with relevance scores.
        
        Args:
            query: Query string
            k: Number of results to return (defaults to config.top_k_results)
            filter: Optional metadata filter
            
        Returns:
            List of (document, score) tuples
        """
        if self.vector_store is None:
            logger.warning("Vector store is empty")
            return []
        
        k = k or self.config.top_k_results
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
            logger.info(f"Found {len(results)} similar documents with scores")
            return results
        except Exception as e:
            logger.error(f"Similarity search with score failed: {e}")
            raise
    
    def delete_collection(self) -> None:
        """Delete the vector store collection."""
        try:
            if self.vector_store is not None:
                if hasattr(self.vector_store, 'delete_collection'):
                    self.vector_store.delete_collection()
                    logger.info("Deleted vector store collection")
                self.vector_store = None
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise
    
    def get_vector_store(self) -> Optional[VectorStore]:
        """Get the underlying vector store object."""
        return self.vector_store
