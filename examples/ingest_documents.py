"""
Example: Ingesting documents from various sources
"""
from main import DBRAG
from dotenv import load_dotenv
import os


def ingest_text_files(rag: DBRAG, directory: str):
    """Ingest all text files from a directory"""
    print(f"Ingesting text files from {directory}...")
    
    count = 0
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                doc_id = rag.add_document(
                    content=content,
                    metadata={
                        "source": filename,
                        "type": "text_file",
                        "path": filepath
                    }
                )
                print(f"✓ Added: {filename} (ID: {doc_id})")
                count += 1
    
    print(f"\nTotal documents ingested: {count}")


def ingest_policies(rag: DBRAG):
    """Example: Ingest company policies"""
    policies = [
        {
            "title": "Refund Policy",
            "content": """Our refund policy allows customers to return products within 30 days 
of purchase for a full refund. Products must be in original condition with tags attached. 
Refunds are processed within 5-7 business days after receiving the returned item. 
Shipping costs are non-refundable unless the return is due to our error.""",
            "department": "Customer Service"
        },
        {
            "title": "Remote Work Policy",
            "content": """Employees are allowed to work remotely up to 3 days per week after 
completing 6 months with the company. Remote work must be pre-approved by direct managers. 
Employees must maintain regular working hours and be available for video calls. 
All company equipment must be secured according to IT security guidelines.""",
            "department": "Human Resources"
        },
        {
            "title": "Data Privacy Policy",
            "content": """We collect and process customer data in accordance with GDPR and CCPA 
regulations. Personal data is encrypted at rest and in transit. Customer data is retained 
for a maximum of 7 years unless legally required otherwise. Customers have the right to 
access, modify, or delete their personal data at any time.""",
            "department": "Legal"
        }
    ]
    
    print("Ingesting company policies...")
    for policy in policies:
        doc_id = rag.add_document(
            content=f"{policy['title']}\n\n{policy['content']}",
            metadata={
                "title": policy['title'],
                "department": policy['department'],
                "type": "policy"
            }
        )
        print(f"✓ Added: {policy['title']} (ID: {doc_id})")
    
    print(f"\nTotal policies ingested: {len(policies)}")


def main():
    load_dotenv()
    
    with DBRAG() as rag:
        # Initialize system
        print("Initializing DB-RAG system...")
        rag.initialize()
        print("✓ System initialized\n")
        
        # Ingest sample policies
        ingest_policies(rag)
        
        # Example: Ingest from directory
        # ingest_text_files(rag, "./documents")
        
        print("\n" + "=" * 60)
        print("Document ingestion complete!")
        print("=" * 60)
        
        # Test search
        print("\nTesting search...")
        result = rag.search_documents_only("What is the refund policy?")
        
        if result['success']:
            print(f"\nFound {result['count']} relevant documents:")
            for i, doc in enumerate(result['documents'], 1):
                print(f"\n{i}. Similarity: {doc['similarity']:.3f}")
                print(f"   Content preview: {doc['content'][:200]}...")


if __name__ == "__main__":
    main()
