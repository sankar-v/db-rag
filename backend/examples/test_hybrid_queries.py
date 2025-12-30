"""
Example: Hybrid queries combining SQL and document search
"""
from main import DBRAG
from dotenv import load_dotenv


def test_hybrid_queries(rag: DBRAG):
    """Test queries that require both structured and unstructured data"""
    
    hybrid_queries = [
        "What were our sales yesterday, and what is our refund policy?",
        "Show me top customers by revenue and our customer service guidelines",
        "What products are low in stock, and what's our restocking procedure?",
        "How many employees work remotely, and what is the remote work policy?",
        "What was last quarter's revenue, and what are our financial reporting standards?"
    ]
    
    print("=" * 60)
    print("Hybrid Query Tests (SQL + Document Search)")
    print("=" * 60)
    print()
    
    for i, query in enumerate(hybrid_queries, 1):
        print(f"\n{i}. Question: {query}")
        print("=" * 60)
        
        result = rag.query(query)
        
        if result['success']:
            print(f"\n✓ Answer:")
            print(f"{result['answer']}")
            
            print(f"\n📊 Data Sources Used:")
            
            # Show SQL details if used
            if result.get('sql_results') and result['sql_results'].get('success'):
                sql = result['sql_results']
                print(f"\n  SQL Query:")
                print(f"    {sql['sql']}")
                print(f"    Tables: {', '.join(sql.get('tables_used', []))}")
                print(f"    Rows returned: {sql.get('row_count', 0)}")
            
            # Show vector search details if used
            if result.get('vector_results') and result['vector_results'].get('success'):
                vec = result['vector_results']
                print(f"\n  Document Search:")
                print(f"    Documents found: {vec['count']}")
                if vec['documents']:
                    top_doc = vec['documents'][0]
                    print(f"    Top match (similarity: {top_doc['similarity']:.3f}):")
                    print(f"    {top_doc['content'][:200]}...")
            
            print()
        else:
            print(f"❌ Error: {result.get('error')}")
        
        print("\n" + "-" * 60)


def main():
    load_dotenv()
    
    with DBRAG() as rag:
        # Initialize system
        print("Initializing DB-RAG system...")
        rag.initialize()
        print("✓ System initialized\n")
        
        # Make sure we have some documents
        print("Adding sample documents...")
        rag.add_document(
            content="Refund Policy: Customers can return items within 30 days for a full refund.",
            metadata={"type": "policy", "department": "Customer Service"}
        )
        rag.add_document(
            content="Remote Work Policy: Employees may work remotely up to 3 days per week.",
            metadata={"type": "policy", "department": "HR"}
        )
        print("✓ Documents added\n")
        
        # Sync metadata
        print("Syncing metadata catalog...")
        rag.sync_metadata()
        print("✓ Metadata synced\n")
        
        # Run tests
        test_hybrid_queries(rag)


if __name__ == "__main__":
    main()
