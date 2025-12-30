"""
Example: Command Line Interface for DB-RAG
"""
from main import DBRAG
from dotenv import load_dotenv
import sys


def main():
    load_dotenv()
    
    print("=" * 60)
    print("DB-RAG: Intelligent Database Query Interface")
    print("=" * 60)
    print()
    
    try:
        with DBRAG() as rag:
            # Initialize system
            print("Initializing DB-RAG system...")
            rag.initialize()
            print("✓ System initialized\n")
            
            print("Commands:")
            print("  - Ask any question about your data")
            print("  - Type 'sync' to update metadata catalog")
            print("  - Type 'quit' or 'exit' to exit")
            print()
            
            while True:
                try:
                    query = input("You: ").strip()
                    
                    if not query:
                        continue
                    
                    if query.lower() in ['quit', 'exit', 'q']:
                        print("\nGoodbye!")
                        break
                    
                    if query.lower() == 'sync':
                        print("Syncing metadata catalog...")
                        rag.sync_metadata()
                        print("✓ Metadata sync complete\n")
                        continue
                    
                    # Process query
                    result = rag.query(query)
                    
                    if result['success']:
                        print(f"\n{result['answer']}\n")
                        
                        # Show SQL if used
                        if result.get('sql_results') and result['sql_results'].get('sql'):
                            print(f"[SQL Query: {result['sql_results']['sql']}]")
                            print(f"[Tables: {', '.join(result['sql_results'].get('tables_used', []))}]")
                        
                        # Show document count if used
                        if result.get('vector_results') and result['vector_results'].get('documents'):
                            doc_count = len(result['vector_results']['documents'])
                            print(f"[Found {doc_count} relevant documents]")
                        
                        print()
                    else:
                        print(f"\n❌ Error: {result.get('error', 'Unknown error')}\n")
                
                except KeyboardInterrupt:
                    print("\n\nGoodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}\n")
    
    except Exception as e:
        print(f"Failed to initialize DB-RAG: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
