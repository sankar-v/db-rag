"""
End-to-end testing script for DB-RAG with Pagila database
"""
import sys
import time
from main import DBRAG
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_db():
    """Wait for database to be ready"""
    import psycopg2
    from config import Config
    
    config = Config.load()
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(config.database.get_connection_string())
            conn.close()
            logger.info("✓ Database is ready!")
            return True
        except psycopg2.OperationalError:
            retry_count += 1
            logger.info(f"Waiting for database... ({retry_count}/{max_retries})")
            time.sleep(2)
    
    logger.error("❌ Database not available after waiting")
    return False


def test_pagila_queries():
    """Test queries specific to Pagila DVD rental database"""
    
    test_cases = [
        {
            "category": "Customer Analytics",
            "queries": [
                "How many customers do we have in total?",
                "Which customers have rented the most films?",
                "Show me customers from the United States",
                "What is the average number of rentals per customer?"
            ]
        },
        {
            "category": "Rental Analytics",
            "queries": [
                "How many rentals were made last month?",
                "What are the most popular film categories?",
                "Which films have been rented the most?",
                "What is our total rental revenue?"
            ]
        },
        {
            "category": "Inventory Management",
            "queries": [
                "How many films do we have in inventory?",
                "Which stores have the most inventory?",
                "List all films in the Action category",
                "What languages are available for our films?"
            ]
        },
        {
            "category": "Staff and Store Analytics",
            "queries": [
                "How many staff members do we have?",
                "Which store has processed the most rentals?",
                "Show me all active stores",
                "List staff members by store"
            ]
        },
        {
            "category": "Policy Questions (Vector Search)",
            "queries": [
                "What is the DVD rental policy?",
                "How do refunds work?",
                "What are the membership benefits?",
                "What is the late fee policy?"
            ]
        },
        {
            "category": "Hybrid Questions",
            "queries": [
                "How many rentals did we have yesterday and what is our rental policy?",
                "Show me top customers and explain our membership benefits",
                "What's our most popular film category and what's our inventory policy?"
            ]
        }
    ]
    
    logger.info("=" * 80)
    logger.info("Starting End-to-End Tests with Pagila Database")
    logger.info("=" * 80)
    
    results = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "by_category": {}
    }
    
    with DBRAG() as rag:
        # Initialize system
        logger.info("\n📋 Initializing DB-RAG system...")
        rag.initialize()
        logger.info("✓ System initialized\n")
        
        # Sync metadata
        logger.info("🔄 Syncing metadata catalog...")
        rag.sync_metadata()
        logger.info("✓ Metadata synced\n")
        
        # Generate embeddings for sample documents
        logger.info("📚 Generating embeddings for sample documents...")
        try:
            # The documents are already in the DB, but need embeddings
            from vector_agent import VectorSearchAgent
            import psycopg2
            
            conn = rag.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check if documents have embeddings
            cursor.execute("SELECT COUNT(*) FROM company_documents WHERE embedding IS NULL")
            null_count = cursor.fetchone()[0]
            
            if null_count > 0:
                logger.info(f"Generating embeddings for {null_count} documents...")
                cursor.execute("SELECT id, content FROM company_documents WHERE embedding IS NULL")
                docs = cursor.fetchall()
                
                for doc_id, content in docs:
                    embedding = rag.orchestrator.vector_agent._generate_embedding(content)
                    cursor.execute(
                        "UPDATE company_documents SET embedding = %s WHERE id = %s",
                        (embedding, doc_id)
                    )
                
                conn.commit()
                logger.info(f"✓ Generated embeddings for {null_count} documents\n")
            else:
                logger.info("✓ All documents already have embeddings\n")
            
            cursor.close()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
        
        # Run tests
        for test_category in test_cases:
            category = test_category["category"]
            queries = test_category["queries"]
            
            logger.info("\n" + "=" * 80)
            logger.info(f"Category: {category}")
            logger.info("=" * 80 + "\n")
            
            category_results = {
                "successful": 0,
                "failed": 0
            }
            
            for i, query in enumerate(queries, 1):
                results["total"] += 1
                logger.info(f"\n{i}. Question: {query}")
                logger.info("-" * 80)
                
                try:
                    result = rag.query(query)
                    
                    if result.get('success'):
                        results["successful"] += 1
                        category_results["successful"] += 1
                        
                        logger.info(f"✓ SUCCESS")
                        logger.info(f"\nAnswer: {result['answer']}\n")
                        
                        # Show which agents were used
                        agents_used = []
                        if result.get('sql_results') and result['sql_results'].get('success'):
                            agents_used.append("SQL")
                            sql = result['sql_results']
                            logger.info(f"📊 SQL Query: {sql.get('sql')}")
                            logger.info(f"   Tables: {', '.join(sql.get('tables_used', []))}")
                            logger.info(f"   Rows: {sql.get('row_count', 0)}")
                        
                        if result.get('vector_results') and result['vector_results'].get('success'):
                            agents_used.append("Vector Search")
                            vec = result['vector_results']
                            logger.info(f"📚 Documents: {vec.get('count', 0)} found")
                            if vec.get('documents'):
                                logger.info(f"   Top match similarity: {vec['documents'][0]['similarity']:.3f}")
                        
                        if agents_used:
                            logger.info(f"\n🤖 Agents used: {', '.join(agents_used)}")
                    else:
                        results["failed"] += 1
                        category_results["failed"] += 1
                        logger.error(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    results["failed"] += 1
                    category_results["failed"] += 1
                    logger.error(f"❌ EXCEPTION: {str(e)}")
                
                logger.info("-" * 80)
            
            results["by_category"][category] = category_results
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"\nTotal Tests: {results['total']}")
    logger.info(f"✓ Successful: {results['successful']} ({results['successful']/results['total']*100:.1f}%)")
    logger.info(f"❌ Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    
    logger.info("\n" + "-" * 80)
    logger.info("Results by Category:")
    logger.info("-" * 80)
    for category, stats in results["by_category"].items():
        total = stats['successful'] + stats['failed']
        success_rate = stats['successful'] / total * 100 if total > 0 else 0
        logger.info(f"{category:30s} {stats['successful']}/{total} ({success_rate:.1f}%)")
    
    logger.info("\n" + "=" * 80)
    
    return results


def main():
    load_dotenv()
    
    # Wait for database
    if not wait_for_db():
        sys.exit(1)
    
    # Run tests
    try:
        results = test_pagila_queries()
        
        # Exit with appropriate code
        if results['failed'] == 0:
            logger.info("✓ All tests passed!")
            sys.exit(0)
        else:
            logger.warning(f"⚠ {results['failed']} tests failed")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
