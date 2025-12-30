"""
Main entry point for DB-RAG system
"""
import logging
from typing import Optional

from config import Config
from database import DatabaseManager
from orchestrator import OrchestratorAgent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class DBRAG:
    """
    Main DB-RAG system interface
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize DB-RAG system
        
        Args:
            config: Optional configuration object. If not provided, loads from environment
        """
        self.config = config or Config.load()
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config.database)
        
        # Initialize orchestrator
        self.orchestrator = OrchestratorAgent(
            self.db_manager,
            self.config.llm,
            self.config.rag
        )
        
        logger.info("DB-RAG system created")
    
    def initialize(self):
        """Initialize database structures and metadata catalog"""
        self.orchestrator.initialize()
    
    def sync_metadata(self, force_update: bool = False):
        """
        Sync all database tables to metadata catalog
        
        Args:
            force_update: If True, update existing entries
        """
        self.orchestrator.metadata_manager.sync_all_tables(force_update=force_update)
    
    def add_document(self, content: str, metadata: Optional[dict] = None) -> str:
        """
        Add an unstructured document to the vector store
        
        Args:
            content: Document text content
            metadata: Optional metadata dictionary
            
        Returns:
            Document ID
        """
        return self.orchestrator.vector_agent.add_document(content, metadata)
    
    def query(self, question: str) -> dict:
        """
        Ask a question using natural language
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary with answer and metadata
        """
        return self.orchestrator.query(question)
    
    def query_sql_only(self, question: str) -> dict:
        """
        Query only structured data using SQL
        
        Args:
            question: Natural language question about structured data
            
        Returns:
            Dictionary with SQL query and results
        """
        return self.orchestrator.sql_agent.query(question)
    
    def search_documents_only(self, query: str) -> dict:
        """
        Search only unstructured documents
        
        Args:
            query: Search query text
            
        Returns:
            Dictionary with search results
        """
        return self.orchestrator.vector_agent.query(query)
    
    def close(self):
        """Clean up resources"""
        self.orchestrator.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def main():
    """Example usage"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Create DB-RAG instance
    with DBRAG() as rag:
        # Initialize system
        rag.initialize()
        
        # Example: Ask a question
        result = rag.query("What was our total sales last month?")
        print(f"\nQuestion: {result['query']}")
        print(f"Answer: {result['answer']}")
        
        if result.get('sql_results'):
            print(f"\nSQL Query: {result['sql_results'].get('sql')}")


if __name__ == "__main__":
    main()
