"""
Example: Testing SQL query generation
"""
from main import DBRAG
from dotenv import load_dotenv


def test_sql_queries(rag: DBRAG):
    """Test various SQL query patterns"""
    
    test_queries = [
        "Show me the total sales for last month",
        "What are the top 5 customers by revenue?",
        "How many products do we have in inventory?",
        "What was our average order value in Q4?",
        "List all orders placed yesterday",
        "Which product category has the highest sales?",
        "Show me customers who haven't purchased in 6 months",
        "What is our month-over-month growth rate?"
    ]
    
    print("=" * 60)
    print("SQL Query Generation Tests")
    print("=" * 60)
    print()
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Question: {query}")
        print("-" * 60)
        
        result = rag.query_sql_only(query)
        
        if result['success']:
            print(f"✓ SQL Generated:")
            print(f"  {result['sql']}")
            print(f"  Tables used: {', '.join(result.get('tables_used', []))}")
            print(f"  Explanation: {result.get('explanation', 'N/A')}")
            
            if result.get('results'):
                print(f"  Results: {len(result['results'])} rows")
                # Show first result as sample
                if result['results']:
                    print(f"  Sample: {result['results'][0]}")
        else:
            print(f"❌ Error: {result.get('error')}")


def main():
    load_dotenv()
    
    with DBRAG() as rag:
        # Initialize system
        print("Initializing DB-RAG system...")
        rag.initialize()
        print("✓ System initialized\n")
        
        # Sync metadata if needed
        print("Syncing metadata catalog...")
        rag.sync_metadata()
        print("✓ Metadata synced\n")
        
        # Run tests
        test_sql_queries(rag)


if __name__ == "__main__":
    main()
