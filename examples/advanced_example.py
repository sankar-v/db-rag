"""
Advanced example showing more features of DB-RAG.

This example demonstrates:
1. Working with PostgreSQL/MySQL databases
2. Querying only database or only documents
3. Custom configuration
4. Advanced query patterns
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_rag import RAGEngine, DatabaseConnector, DocumentLoader, VectorStoreManager
from db_rag.config import Config


def demo_separate_queries():
    """Demonstrate querying database and documents separately."""
    print("\n" + "=" * 60)
    print("Demo: Separate Queries")
    print("=" * 60)
    
    config = Config()
    rag = RAGEngine(config)
    
    question = "What products are available?"
    
    # Query only database
    print(f"\n1. Database-only query: {question}")
    result = rag.query(question, search_db=True, search_docs=False)
    print(f"Answer: {result.get('answer')}")
    
    # Query only documents
    print(f"\n2. Documents-only query: {question}")
    result = rag.query(question, search_db=False, search_docs=True)
    print(f"Answer: {result.get('answer')}")
    
    # Query both (default)
    print(f"\n3. Combined query: {question}")
    result = rag.query(question, search_db=True, search_docs=True)
    print(f"Answer: {result.get('answer')}")
    
    rag.close()


def demo_direct_components():
    """Demonstrate using components directly."""
    print("\n" + "=" * 60)
    print("Demo: Direct Component Usage")
    print("=" * 60)
    
    config = Config()
    
    # Use DatabaseConnector directly
    print("\n1. Direct Database Access:")
    db = DatabaseConnector(config)
    tables = db.get_table_names()
    print(f"   Tables: {tables}")
    
    if tables:
        schema = db.get_table_schema(tables[0])
        print(f"   Schema of {tables[0]}:")
        for col in schema[:3]:  # Show first 3 columns
            print(f"     - {col['name']}: {col['type']}")
    
    db.close()
    
    # Use DocumentLoader directly
    print("\n2. Direct Document Loading:")
    doc_loader = DocumentLoader(config)
    
    # Load from text
    text = "This is a sample document about machine learning and AI."
    docs = doc_loader.load_from_text(text, metadata={"source": "demo"})
    print(f"   Loaded {len(docs)} document chunks from text")
    
    # Use VectorStoreManager directly
    print("\n3. Direct Vector Store Access:")
    vector_store = VectorStoreManager(config)
    vector_store.add_documents(docs)
    
    # Search
    results = vector_store.similarity_search("What is this about?", k=2)
    print(f"   Found {len(results)} similar documents")
    for i, doc in enumerate(results, 1):
        print(f"   {i}. {doc.page_content[:50]}...")


def demo_custom_config():
    """Demonstrate custom configuration."""
    print("\n" + "=" * 60)
    print("Demo: Custom Configuration")
    print("=" * 60)
    
    # Create custom configuration
    config = Config()
    config.chunk_size = 500  # Smaller chunks
    config.chunk_overlap = 100
    config.top_k_results = 3  # Return fewer results
    
    print(f"\nCustom Configuration:")
    print(f"  - Chunk Size: {config.chunk_size}")
    print(f"  - Chunk Overlap: {config.chunk_overlap}")
    print(f"  - Top K Results: {config.top_k_results}")
    
    # Use custom config
    doc_loader = DocumentLoader(config)
    long_text = " ".join(["This is sentence number {}.".format(i) for i in range(100)])
    docs = doc_loader.load_from_text(long_text)
    
    print(f"\nWith smaller chunks, created {len(docs)} documents from text")


def demo_metadata_filtering():
    """Demonstrate metadata filtering in vector search."""
    print("\n" + "=" * 60)
    print("Demo: Metadata Filtering")
    print("=" * 60)
    
    config = Config()
    vector_store = VectorStoreManager(config)
    
    # Add documents with different metadata
    texts = [
        "Python is a great programming language.",
        "JavaScript is used for web development.",
        "Java is widely used in enterprise applications.",
    ]
    metadatas = [
        {"language": "python", "category": "programming"},
        {"language": "javascript", "category": "programming"},
        {"language": "java", "category": "programming"},
    ]
    
    vector_store.add_texts(texts, metadatas)
    
    # Search with filter
    print("\n1. Search without filter:")
    results = vector_store.similarity_search("programming language", k=3)
    for i, doc in enumerate(results, 1):
        print(f"   {i}. {doc.page_content}")
    
    print("\n2. Search with filter (only Python):")
    results = vector_store.similarity_search(
        "programming language",
        k=3,
        filter={"language": "python"}
    )
    for i, doc in enumerate(results, 1):
        print(f"   {i}. {doc.page_content}")


def main():
    """Run advanced examples."""
    print("=" * 60)
    print("DB-RAG Advanced Examples")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY not set!")
        print("Please set your OpenAI API key in .env file or as environment variable.")
        return
    
    try:
        # Run demos
        demo_direct_components()
        demo_custom_config()
        demo_metadata_filtering()
        
        # Uncomment if you have the basic example database set up
        # demo_separate_queries()
        
        print("\n" + "=" * 60)
        print("✅ All advanced examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
