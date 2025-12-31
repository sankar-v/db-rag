"""
Celery tasks for async processing
Background workers for document ingestion, metadata updates, and maintenance
"""
import logging
import json
from typing import List, Dict, Any, Optional
from celery import Task
from celery.utils.log import get_task_logger

from celeryconfig import celery_app
from config import Config
from database import DatabaseManager
from embedding_service import EmbeddingService
from vector_agent import VectorSearchAgent
from metadata_catalog import MetadataCatalogManager

logger = get_task_logger(__name__)

# Global instances (initialized per worker)
config = None
db_manager = None
embedding_service = None
vector_agent = None
metadata_catalog = None


def init_worker():
    """Initialize worker with database connections and services"""
    global config, db_manager, embedding_service, vector_agent, metadata_catalog
    
    if config is None:
        config = Config.load()
        db_manager = DatabaseManager(config.database)
        embedding_service = EmbeddingService(config.llm, config.cache)
        vector_agent = VectorSearchAgent(db_manager, config.llm, config.rag)
        metadata_catalog = MetadataCatalogManager(db_manager, config.llm, config.rag)
        
        logger.info("Worker initialized successfully")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_document_task(
    self: Task,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict[str, Any]:
    """
    Background task for document ingestion with chunking and embedding
    
    Args:
        content: Document text content
        metadata: Optional metadata (source, page, department, etc.)
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks
        
    Returns:
        Result dictionary with status and statistics
    """
    try:
        init_worker()
        
        logger.info(f"Starting document ingestion, content length: {len(content)}")
        
        # Chunk the document
        chunks = chunk_text(content, chunk_size, chunk_overlap)
        logger.info(f"Document split into {len(chunks)} chunks")
        
        # Generate embeddings in batch
        chunk_texts = [chunk['text'] for chunk in chunks]
        embeddings = embedding_service.generate_embeddings_batch(
            chunk_texts, 
            show_progress=len(chunks) > 50
        )
        
        # Store chunks with embeddings
        doc_ids = []
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Merge chunk metadata with document metadata
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata.update({
                    'chunk_index': i,
                    'chunk_total': len(chunks),
                    'chunk_start': chunk['start'],
                    'chunk_end': chunk['end']
                })
                
                cursor.execute(f"""
                    INSERT INTO {config.rag.documents_table} (content, metadata, embedding)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (chunk['text'], json.dumps(chunk_metadata), embedding))
                
                doc_id = cursor.fetchone()[0]
                doc_ids.append(str(doc_id))
            
            conn.commit()
            logger.info(f"Successfully ingested {len(chunks)} chunks")
            
            return {
                "status": "success",
                "chunks": len(chunks),
                "document_ids": doc_ids,
                "embeddings_from_cache": embedding_service.cache_hits,
                "embeddings_generated": embedding_service.cache_misses
            }
            
        finally:
            cursor.close()
            
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def update_table_metadata_task(
    self: Task,
    table_name: str,
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Background task for updating table metadata in catalog
    
    Args:
        table_name: Name of the table to update
        force_update: If True, update even if entry exists
        
    Returns:
        Result dictionary with status
    """
    try:
        init_worker()
        
        logger.info(f"Updating metadata for table: {table_name}")
        
        # Check if already exists
        if not force_update:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id FROM {config.rag.metadata_catalog_table} WHERE table_name = %s",
                (table_name,)
            )
            exists = cursor.fetchone()
            cursor.close()
            
            if exists:
                logger.info(f"Table '{table_name}' already in catalog, skipping")
                return {"status": "skipped", "table": table_name, "reason": "already_exists"}
        
        # Get table schema and sample data
        schema_context = db_manager.get_table_context_string(table_name)
        sample_data = db_manager.get_sample_data(table_name, limit=5)
        
        # Generate description using LLM
        description_data = metadata_catalog.generate_table_description(
            table_name, schema_context, sample_data
        )
        
        # Generate embedding
        searchable_text = (
            f"{table_name} {description_data['description']} "
            f"{description_data['business_context']}"
        )
        embedding = embedding_service.generate_embedding(searchable_text)
        
        # Update catalog
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                INSERT INTO {config.rag.metadata_catalog_table} 
                (table_name, column_definitions, table_description, business_context, 
                 sample_queries, description_embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (table_name) DO UPDATE SET
                    column_definitions = EXCLUDED.column_definitions,
                    table_description = EXCLUDED.table_description,
                    business_context = EXCLUDED.business_context,
                    sample_queries = EXCLUDED.sample_queries,
                    description_embedding = EXCLUDED.description_embedding,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                table_name,
                schema_context,
                description_data['description'],
                description_data['business_context'],
                description_data['sample_questions'],
                embedding
            ))
            
            conn.commit()
            logger.info(f"Successfully updated metadata for table: {table_name}")
            
            return {
                "status": "success",
                "table": table_name,
                "description": description_data['description']
            }
            
        finally:
            cursor.close()
            
    except Exception as e:
        logger.error(f"Metadata update failed for {table_name}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def batch_update_metadata_task(
    table_names: List[str],
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Batch update metadata for multiple tables
    
    Args:
        table_names: List of table names to update
        force_update: If True, update even if entries exist
        
    Returns:
        Summary of results
    """
    try:
        init_worker()
        
        logger.info(f"Batch metadata update for {len(table_names)} tables")
        
        results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
        
        for table_name in table_names:
            try:
                result = update_table_metadata_task(table_name, force_update)
                if result["status"] == "success":
                    results["success"].append(table_name)
                elif result["status"] == "skipped":
                    results["skipped"].append(table_name)
            except Exception as e:
                logger.error(f"Failed to update {table_name}: {e}")
                results["failed"].append({"table": table_name, "error": str(e)})
        
        logger.info(
            f"Batch update complete: {len(results['success'])} success, "
            f"{len(results['failed'])} failed, {len(results['skipped'])} skipped"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Batch metadata update failed: {e}", exc_info=True)
        raise


@celery_app.task
def rebuild_vector_indexes_task() -> Dict[str, Any]:
    """
    Periodic task to rebuild and optimize vector indexes
    
    Returns:
        Result dictionary with status
    """
    try:
        init_worker()
        
        logger.info("Starting vector index rebuild")
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Reindex documents table
            cursor.execute(f"REINDEX TABLE {config.rag.documents_table}")
            logger.info(f"Reindexed {config.rag.documents_table}")
            
            # Reindex metadata catalog
            cursor.execute(f"REINDEX TABLE {config.rag.metadata_catalog_table}")
            logger.info(f"Reindexed {config.rag.metadata_catalog_table}")
            
            # Run ANALYZE for query planner
            cursor.execute(f"ANALYZE {config.rag.documents_table}")
            cursor.execute(f"ANALYZE {config.rag.metadata_catalog_table}")
            logger.info("Analyzed tables for query planner")
            
            conn.commit()
            
            return {
                "status": "success",
                "tables_reindexed": 2
            }
            
        finally:
            cursor.close()
            
    except Exception as e:
        logger.error(f"Index rebuild failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def chunk_text(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunk dictionaries with text, start, and end positions
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # If not at the end, try to break at a sentence or word boundary
        if end < text_length:
            # Look for sentence boundary
            for delimiter in ['. ', '! ', '? ', '\n\n', '\n', ' ']:
                boundary = text.rfind(delimiter, start, end)
                if boundary != -1:
                    end = boundary + len(delimiter)
                    break
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                'text': chunk_text,
                'start': start,
                'end': end
            })
        
        # Move start position (with overlap)
        start = end - chunk_overlap
        
        # Ensure we're making progress
        if start <= chunks[-1]['start'] if chunks else False:
            start = end
    
    return chunks


# Worker initialization hook
@celery_app.task
def health_check() -> Dict[str, str]:
    """Health check task for worker monitoring"""
    try:
        init_worker()
        
        # Test database connection
        conn = db_manager.get_connection()
        conn.close()
        
        # Test Redis connection
        if embedding_service.cache_enabled:
            embedding_service.redis_client.ping()
        
        return {"status": "healthy", "worker": "ready"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
