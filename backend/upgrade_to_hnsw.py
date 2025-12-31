"""
Database migration script to upgrade vector indexes from IVFFlat to HNSW
Run this script to improve query performance by 10-100x
"""
import logging
import sys
from config import Config
from database import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def upgrade_to_hnsw(db_manager: DatabaseManager, config: Config):
    """
    Upgrade vector indexes from IVFFlat to HNSW
    
    HNSW (Hierarchical Navigable Small World) provides:
    - 10-100x faster queries
    - Better recall at higher dimensions
    - More suitable for production workloads
    
    Parameters:
    - m: Maximum number of connections per layer (16 is good default)
    - ef_construction: Size of dynamic candidate list (64-128 for quality)
    """
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("Starting vector index upgrade to HNSW...")
        
        # Check if pgvector extension supports HNSW
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        version = cursor.fetchone()
        if version:
            logger.info(f"pgvector version: {version[0]}")
        else:
            raise RuntimeError("pgvector extension not installed")
        
        documents_table = config.rag.documents_table
        metadata_table = config.rag.metadata_catalog_table
        
        # 1. Drop old IVFFlat indexes
        logger.info("Dropping old IVFFlat indexes...")
        
        cursor.execute(f"""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = '{documents_table}' 
              AND indexdef LIKE '%ivfflat%'
        """)
        doc_indexes = cursor.fetchall()
        
        for idx in doc_indexes:
            logger.info(f"Dropping index: {idx[0]}")
            cursor.execute(f"DROP INDEX IF EXISTS {idx[0]}")
        
        cursor.execute(f"""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = '{metadata_table}' 
              AND indexdef LIKE '%ivfflat%'
        """)
        meta_indexes = cursor.fetchall()
        
        for idx in meta_indexes:
            logger.info(f"Dropping index: {idx[0]}")
            cursor.execute(f"DROP INDEX IF EXISTS {idx[0]}")
        
        conn.commit()
        logger.info("Old indexes dropped")
        
        # 2. Create new HNSW indexes
        logger.info("Creating HNSW indexes (this may take a while for large datasets)...")
        
        # Documents table index
        logger.info(f"Creating HNSW index on {documents_table}...")
        cursor.execute(f"""
            CREATE INDEX documents_embedding_hnsw_idx 
            ON {documents_table} 
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        logger.info(f"✓ Created HNSW index on {documents_table}")
        
        # Metadata catalog index
        logger.info(f"Creating HNSW index on {metadata_table}...")
        cursor.execute(f"""
            CREATE INDEX metadata_embedding_hnsw_idx 
            ON {metadata_table} 
            USING hnsw (description_embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        logger.info(f"✓ Created HNSW index on {metadata_table}")
        
        conn.commit()
        
        # 3. Analyze tables for query planner
        logger.info("Running ANALYZE on tables...")
        cursor.execute(f"ANALYZE {documents_table}")
        cursor.execute(f"ANALYZE {metadata_table}")
        conn.commit()
        
        logger.info("=" * 60)
        logger.info("✓ Vector index upgrade complete!")
        logger.info("=" * 60)
        logger.info("Benefits:")
        logger.info("  - 10-100x faster vector similarity queries")
        logger.info("  - Better accuracy at scale")
        logger.info("  - Lower memory usage during queries")
        logger.info("")
        logger.info("Note: Query planning parameters:")
        logger.info("  - hnsw.ef_search controls query accuracy/speed tradeoff")
        logger.info("  - Default is 40, increase to 100-200 for better recall")
        logger.info("  - SET hnsw.ef_search = 100; (session level)")
        logger.info("=" * 60)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to upgrade indexes: {e}")
        logger.error("Rolling back changes...")
        raise
    finally:
        cursor.close()


def verify_indexes(db_manager: DatabaseManager, config: Config):
    """Verify that HNSW indexes are created properly"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        documents_table = config.rag.documents_table
        metadata_table = config.rag.metadata_catalog_table
        
        # Check documents table
        cursor.execute(f"""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = '{documents_table}' 
              AND indexdef LIKE '%hnsw%'
        """)
        doc_indexes = cursor.fetchall()
        
        # Check metadata table
        cursor.execute(f"""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = '{metadata_table}' 
              AND indexdef LIKE '%hnsw%'
        """)
        meta_indexes = cursor.fetchall()
        
        logger.info("\nCurrent HNSW Indexes:")
        logger.info("-" * 60)
        
        if doc_indexes:
            logger.info(f"\n{documents_table}:")
            for idx in doc_indexes:
                logger.info(f"  ✓ {idx[0]}")
        else:
            logger.warning(f"\n{documents_table}: No HNSW indexes found")
        
        if meta_indexes:
            logger.info(f"\n{metadata_table}:")
            for idx in meta_indexes:
                logger.info(f"  ✓ {idx[0]}")
        else:
            logger.warning(f"\n{metadata_table}: No HNSW indexes found")
        
        logger.info("-" * 60)
        
        return len(doc_indexes) > 0 and len(meta_indexes) > 0
        
    finally:
        cursor.close()


if __name__ == "__main__":
    # Load configuration
    config = Config.load()
    db_manager = DatabaseManager(config.database)
    
    try:
        # Check current state
        logger.info("Checking current indexes...")
        has_hnsw = verify_indexes(db_manager, config)
        
        if has_hnsw:
            logger.warning("HNSW indexes already exist!")
            response = input("Do you want to recreate them? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Skipping upgrade")
                sys.exit(0)
        
        # Perform upgrade
        upgrade_to_hnsw(db_manager, config)
        
        # Verify results
        verify_indexes(db_manager, config)
        
    except KeyboardInterrupt:
        logger.info("\nUpgrade cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Upgrade failed: {e}")
        sys.exit(1)
    finally:
        db_manager.close()
