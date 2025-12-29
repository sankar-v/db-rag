"""
Command-line interface for DB-RAG.
"""

import argparse
import sys
import os
from typing import Optional

from .config import Config
from .rag_engine import RAGEngine


def ingest_command(args):
    """Handle the ingest command."""
    print(f"Ingesting documents from: {args.source}")
    
    config = Config()
    rag = RAGEngine(config)
    
    try:
        rag.ingest_documents(args.source, source_type=args.type)
        
        if args.include_schema:
            print("Ingesting database schema...")
            rag.ingest_database_schema()
        
        print("✅ Documents ingested successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        rag.close()


def query_command(args):
    """Handle the query command."""
    config = Config()
    rag = RAGEngine(config)
    
    try:
        result = rag.query(
            args.question,
            search_db=not args.docs_only,
            search_docs=not args.db_only
        )
        
        # Print results
        print("\n" + "=" * 60)
        print(f"Question: {result['question']}")
        print("=" * 60)
        
        # Database results
        if result.get("database_results"):
            db_res = result["database_results"]
            if not db_res.get("error"):
                print(f"\n📊 Database Results:")
                print(f"SQL Query: {db_res.get('sql_query', 'N/A')}")
                if db_res.get("results"):
                    print(f"Records: {len(db_res['results'])}")
                    if args.verbose:
                        for i, row in enumerate(db_res['results'][:5], 1):
                            print(f"  {i}. {row}")
            else:
                print(f"\n⚠️  Database Error: {db_res['error']}")
        
        # Document results
        if result.get("document_results"):
            doc_res = result["document_results"]
            if not doc_res.get("error"):
                if doc_res.get("documents"):
                    print(f"\n📄 Document Results: {len(doc_res['documents'])} found")
                    if args.verbose:
                        for i, doc in enumerate(doc_res['documents'][:3], 1):
                            print(f"  {i}. Score: {doc['score']:.4f}")
                            print(f"     {doc['content'][:100]}...")
            else:
                print(f"\n⚠️  Document Error: {doc_res['error']}")
        
        # Final answer
        print(f"\n💡 Answer:")
        print(result.get('answer', 'No answer generated'))
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        rag.close()


def db_info_command(args):
    """Handle the db-info command."""
    from .db_connector import DatabaseConnector
    
    config = Config()
    db = DatabaseConnector(config)
    
    try:
        tables = db.get_table_names()
        print(f"\n📊 Database Information")
        print(f"Type: {config.db_type}")
        print(f"Tables: {len(tables)}")
        print()
        
        for table in tables:
            print(f"Table: {table}")
            schema = db.get_table_schema(table)
            for col in schema:
                print(f"  - {col['name']}: {col['type']}")
            
            if args.sample:
                samples = db.get_sample_data(table, limit=3)
                if samples:
                    print(f"  Sample data:")
                    for i, row in enumerate(samples, 1):
                        print(f"    {i}. {row}")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DB-RAG: RAG system for structured and unstructured data",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents into vector store")
    ingest_parser.add_argument("source", help="Path to file or directory")
    ingest_parser.add_argument(
        "--type",
        choices=["auto", "file", "directory"],
        default="auto",
        help="Source type (default: auto)"
    )
    ingest_parser.add_argument(
        "--include-schema",
        action="store_true",
        help="Also ingest database schema"
    )
    ingest_parser.set_defaults(func=ingest_command)
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the RAG system")
    query_parser.add_argument("question", help="Question to ask")
    query_parser.add_argument(
        "--db-only",
        action="store_true",
        help="Query database only"
    )
    query_parser.add_argument(
        "--docs-only",
        action="store_true",
        help="Query documents only"
    )
    query_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed results"
    )
    query_parser.set_defaults(func=query_command)
    
    # DB info command
    db_info_parser = subparsers.add_parser("db-info", help="Show database information")
    db_info_parser.add_argument(
        "--sample",
        action="store_true",
        help="Show sample data from tables"
    )
    db_info_parser.set_defaults(func=db_info_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set!")
        print("Please set your OpenAI API key in .env file or as environment variable.")
        sys.exit(1)
    
    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
