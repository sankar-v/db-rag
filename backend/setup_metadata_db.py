#!/usr/bin/env python3
"""
Setup script for DB-RAG Metadata Database
Creates the metadata database and initializes the schema
"""
import psycopg2
import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

def create_metadata_database():
    """Create the metadata database if it doesn't exist"""
    
    # Connection parameters
    host = os.getenv("METADATA_DB_HOST", "localhost")
    port = int(os.getenv("METADATA_DB_PORT", "5432"))
    user = os.getenv("METADATA_DB_USER", "postgres")
    password = os.getenv("METADATA_DB_PASSWORD", "postgres")
    metadata_db_name = os.getenv("METADATA_DB_NAME", "dbrag_metadata")
    
    print(f"🔧 Setting up metadata database: {metadata_db_name}")
    print(f"📍 Host: {host}:{port}")
    
    try:
        # Connect to postgres database to create the metadata database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database="postgres",
            user=user,
            password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (metadata_db_name,)
        )
        
        if cursor.fetchone():
            print(f"✅ Metadata database '{metadata_db_name}' already exists")
        else:
            # Create the database
            cursor.execute(f'CREATE DATABASE {metadata_db_name}')
            print(f"✅ Created metadata database '{metadata_db_name}'")
        
        cursor.close()
        conn.close()
        
        # Now connect to the metadata database and initialize schema
        print("📋 Initializing schema...")
        
        from metadata_database import MetadataDatabaseManager
        
        metadata_db = MetadataDatabaseManager(
            host=host,
            port=port,
            database=metadata_db_name,
            user=user,
            password=password
        )
        
        metadata_db.connect()
        print("✅ Schema initialized successfully")
        
        # Create default tenant
        default_tenant_id = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        default_tenant_name = os.getenv("DEFAULT_TENANT_NAME", "Development")
        
        if not metadata_db.get_tenant(default_tenant_id):
            # Create with specific ID
            conn = metadata_db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tenants (tenant_id, tenant_name, organization, status)
                VALUES (%s, %s, %s, %s)
            """, (default_tenant_id, default_tenant_name, "Default Organization", "active"))
            conn.commit()
            cursor.close()
            print(f"✅ Created default tenant: {default_tenant_name} ({default_tenant_id})")
        else:
            print(f"✅ Default tenant already exists: {default_tenant_name}")
        
        print("\n🎉 Metadata database setup complete!")
        print(f"\n📊 Database: {metadata_db_name}")
        print(f"👤 Default Tenant ID: {default_tenant_id}")
        print(f"📝 Default Tenant Name: {default_tenant_name}")
        print("\n💡 You can now start the backend server with: python -m uvicorn api:app --reload")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        print("\n💡 Make sure PostgreSQL is running and credentials are correct")
        print(f"   Check your .env file: METADATA_DB_HOST, METADATA_DB_PORT, METADATA_DB_USER, METADATA_DB_PASSWORD")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("  DB-RAG Metadata Database Setup")
    print("  Multi-Tenant Architecture with Control/Data Plane Separation")
    print("=" * 60)
    print()
    
    success = create_metadata_database()
    
    sys.exit(0 if success else 1)
