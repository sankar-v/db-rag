"""
Vector Search Agent - Handles unstructured document search using pgvector
"""
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

from database import DatabaseManager
from config import LLMConfig, RAGConfig


logger = logging.getLogger(__name__)


class VectorSearchAgent:
    """Agent for searching unstructured documents using vector similarity"""
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm_config: LLMConfig,
        rag_config: RAGConfig
    ):
        self.db = db_manager
        self.llm_config = llm_config
        self.rag_config = rag_config
        self.client = OpenAI(api_key=llm_config.api_key)
        self.documents_table = rag_config.documents_table
    
    def initialize_documents_table(self):
        """Create the documents table if it doesn't exist"""
        if self.db.table_exists(self.documents_table):
            logger.info(f"Documents table '{self.documents_table}' already exists")
            return
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Ensure pgvector extension is enabled
            self.db.ensure_pgvector_extension()
            
            # Create the documents table
            cursor.execute(f"""
                CREATE TABLE {self.documents_table} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding VECTOR({self.llm_config.embedding_dimensions}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create index for fast vector search
            cursor.execute(f"""
                CREATE INDEX ON {self.documents_table}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
            conn.commit()
            logger.info(f"Created documents table: {self.documents_table}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create documents table: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a document to the vector store
        
        Args:
            content: Document text content
            metadata: Optional metadata (source, page, department, etc.)
            
        Returns:
            Document ID
        """
        import json
        
        # Generate embedding
        embedding = self._generate_embedding(content)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                INSERT INTO {self.documents_table} (content, metadata, embedding)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (content, json.dumps(metadata) if metadata else None, embedding))
            
            doc_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"Added document with ID: {doc_id}")
            return str(doc_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add document: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.llm_config.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using vector similarity
        
        Args:
            query: Search query text
            max_results: Maximum number of results to return
            metadata_filter: Optional JSONB filter conditions
            
        Returns:
            List of relevant documents with similarity scores
        """
        if max_results is None:
            max_results = self.rag_config.max_vector_results
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build query with optional metadata filter
            query_sql = f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM {self.documents_table}
            """
            
            params = [query_embedding]
            
            if metadata_filter:
                # Add metadata filtering
                conditions = []
                for key, value in metadata_filter.items():
                    conditions.append(f"metadata->>'{key}' = %s")
                    params.append(str(value))
                
                query_sql += " WHERE " + " AND ".join(conditions)
            
            query_sql += f"""
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([query_embedding, max_results])
            
            cursor.execute(query_sql, params)
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"Found {len(results)} relevant documents")
            return results
        finally:
            cursor.close()
    
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Complete workflow: search documents and return results
        
        Args:
            user_query: Natural language query
            
        Returns:
            Dictionary with search results
        """
        logger.info(f"Processing vector search query: {user_query}")
        
        try:
            results = self.search(user_query)
            
            # Format results
            documents = []
            for result in results:
                documents.append({
                    "content": result["content"],
                    "metadata": result.get("metadata"),
                    "similarity": float(result["similarity"])
                })
            
            return {
                "success": True,
                "query": user_query,
                "documents": documents,
                "count": len(documents)
            }
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return {
                "success": False,
                "query": user_query,
                "error": str(e),
                "documents": []
            }
