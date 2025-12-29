"""
Basic example of using the DB-RAG system.

This example shows how to:
1. Set up a simple SQLite database
2. Ingest some documents
3. Query both structured and unstructured data
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_rag import RAGEngine
from db_rag.config import Config


def setup_example_database():
    """Create a simple example database."""
    import sqlite3
    
    db_path = "example.db"
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create database and tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    
    # Insert sample data
    products = [
        (1, "Laptop", "Electronics", 999.99, 15),
        (2, "Mouse", "Electronics", 29.99, 50),
        (3, "Keyboard", "Electronics", 79.99, 30),
        (4, "Desk Chair", "Furniture", 199.99, 10),
        (5, "Standing Desk", "Furniture", 499.99, 8),
        (6, "Monitor", "Electronics", 299.99, 20),
    ]
    
    cursor.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?, ?)",
        products
    )
    
    conn.commit()
    conn.close()
    
    print(f"Created example database: {db_path}")
    return db_path


def create_example_documents():
    """Create example document files."""
    docs_dir = "example_docs"
    os.makedirs(docs_dir, exist_ok=True)
    
    # Create a product guide document
    product_guide = """
Product Guide

Electronics Category:
- Laptops: Our laptops feature the latest processors and high-resolution displays.
- Mice: Ergonomic design for comfortable extended use.
- Keyboards: Mechanical switches for better typing experience.
- Monitors: 4K resolution with HDR support.

Furniture Category:
- Desk Chairs: Adjustable height with lumbar support for long work sessions.
- Standing Desks: Electric height adjustment with memory settings.

Warranty Information:
- All electronics come with a 2-year warranty.
- Furniture items have a 5-year warranty.
- Extended warranties available for purchase.
"""
    
    with open(f"{docs_dir}/product_guide.txt", "w") as f:
        f.write(product_guide)
    
    # Create a company policy document
    company_policy = """
Company Policies

Return Policy:
- Products can be returned within 30 days of purchase.
- Items must be in original packaging and unused.
- Refunds processed within 5-7 business days.

Shipping:
- Free shipping on orders over $100.
- Standard shipping: 5-7 business days.
- Express shipping: 2-3 business days.

Customer Support:
- Available Monday-Friday 9 AM - 5 PM.
- Email support available 24/7.
- Live chat available during business hours.
"""
    
    with open(f"{docs_dir}/company_policy.txt", "w") as f:
        f.write(company_policy)
    
    print(f"Created example documents in: {docs_dir}")
    return docs_dir


def main():
    """Run the basic example."""
    print("=" * 60)
    print("DB-RAG Basic Example")
    print("=" * 60)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY not set!")
        print("Please set your OpenAI API key in .env file or as environment variable.")
        return
    
    # Setup example data
    print("\n1. Setting up example database...")
    db_path = setup_example_database()
    
    print("\n2. Creating example documents...")
    docs_dir = create_example_documents()
    
    # Configure the system
    config = Config()
    config.db_name = db_path
    config.db_type = "sqlite"
    
    print("\n3. Initializing RAG Engine...")
    rag = RAGEngine(config)
    
    print("\n4. Ingesting documents...")
    rag.ingest_documents(docs_dir, source_type="directory")
    rag.ingest_database_schema()
    
    print("\n5. Running example queries...")
    print("=" * 60)
    
    # Example queries
    queries = [
        "What electronics products do we have in stock?",
        "What is our return policy?",
        "Show me all furniture items and their prices",
        "What warranty do our electronics have?",
    ]
    
    for i, question in enumerate(queries, 1):
        print(f"\nQuery {i}: {question}")
        print("-" * 60)
        
        result = rag.query(question)
        
        # Print database results if available
        if result.get("database_results") and not result["database_results"].get("error"):
            db_res = result["database_results"]
            print(f"\n📊 SQL Query: {db_res.get('sql_query', 'N/A')}")
            if db_res.get("results"):
                print(f"   Results: {len(db_res['results'])} rows")
        
        # Print document results if available
        if result.get("document_results") and not result["document_results"].get("error"):
            doc_res = result["document_results"]
            if doc_res.get("documents"):
                print(f"\n📄 Found {len(doc_res['documents'])} relevant documents")
        
        # Print final answer
        print(f"\n💡 Answer:\n{result.get('answer', 'No answer generated')}")
        print("=" * 60)
    
    # Cleanup
    print("\n6. Cleaning up...")
    rag.close()
    
    print("\n✅ Example completed successfully!")
    print(f"\nNote: Database and documents are saved in:")
    print(f"  - Database: {db_path}")
    print(f"  - Documents: {docs_dir}")
    print(f"  - Vector Store: {config.vector_store_path}")


if __name__ == "__main__":
    main()
