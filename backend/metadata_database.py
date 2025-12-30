"""
Metadata Database Manager - Handles the control plane metadata storage
Stores: connections, table metadata, tenants, catalogs in a separate database
"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid

logger = logging.getLogger(__name__)


class MetadataDatabaseManager:
    """Manages the metadata database (control plane)"""
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        
    def connect(self):
        """Connect to metadata database"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info(f"Connected to metadata database: {self.database}")
            self._initialize_schema()
        except Exception as e:
            logger.error(f"Failed to connect to metadata database: {e}")
            raise
    
    def get_connection(self):
        """Get database connection"""
        if not self.connection or self.connection.closed:
            self.connect()
        return self.connection
    
    def _initialize_schema(self):
        """Create metadata tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Tenants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id UUID PRIMARY KEY,
                    tenant_name VARCHAR(255) NOT NULL,
                    organization VARCHAR(255),
                    email VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'active',
                    settings JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Connections table (per tenant)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    connection_id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    connection_name VARCHAR(255) NOT NULL,
                    host VARCHAR(255) NOT NULL,
                    port INTEGER NOT NULL,
                    database_name VARCHAR(255) NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    password_encrypted TEXT NOT NULL,
                    schema_name VARCHAR(255) DEFAULT 'public',
                    is_active BOOLEAN DEFAULT FALSE,
                    status VARCHAR(50) DEFAULT 'disconnected',
                    connection_metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, connection_name)
                )
            """)
            
            # Table metadata catalog (per connection/tenant)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS table_metadata_catalog (
                    catalog_id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    connection_id UUID NOT NULL REFERENCES connections(connection_id) ON DELETE CASCADE,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255) NOT NULL,
                    table_description TEXT,
                    column_descriptions JSONB,
                    sample_values JSONB,
                    row_count BIGINT,
                    data_types JSONB,
                    relationships JSONB,
                    business_context TEXT,
                    search_vector tsvector,
                    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, connection_id, table_name, schema_name)
                )
            """)
            
            # Create index on search vector for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_table_metadata_search 
                ON table_metadata_catalog USING GIN(search_vector)
            """)
            
            # Create index on tenant_id for fast filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_connections_tenant 
                ON connections(tenant_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_catalog_tenant 
                ON table_metadata_catalog(tenant_id)
            """)
            
            conn.commit()
            logger.info("Metadata database schema initialized")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize metadata schema: {e}")
            raise
        finally:
            cursor.close()
    
    # ============= TENANT MANAGEMENT =============
    
    def create_tenant(
        self,
        tenant_name: str,
        organization: Optional[str] = None,
        email: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> str:
        """Create a new tenant"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            tenant_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tenants (tenant_id, tenant_name, organization, email, settings)
                VALUES (%s, %s, %s, %s, %s)
            """, (tenant_id, tenant_name, organization, email, json.dumps(settings or {})))
            
            conn.commit()
            logger.info(f"Created tenant: {tenant_name} ({tenant_id})")
            return tenant_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create tenant: {e}")
            raise
        finally:
            cursor.close()
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant by ID"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("SELECT * FROM tenants WHERE tenant_id = %s", (tenant_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            cursor.close()
    
    def list_tenants(self) -> List[Dict]:
        """List all tenants"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("SELECT * FROM tenants ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    # ============= CONNECTION MANAGEMENT =============
    
    def create_connection(
        self,
        tenant_id: str,
        connection_name: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        schema_name: str = 'public',
        connection_metadata: Optional[Dict] = None
    ) -> str:
        """Create a new connection for a tenant"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            connection_id = str(uuid.uuid4())
            
            # In production, encrypt the password!
            # For now, we'll store it as-is (TODO: Add encryption)
            password_encrypted = password
            
            cursor.execute("""
                INSERT INTO connections (
                    connection_id, tenant_id, connection_name, db_host, db_port,
                    db_name, db_user, db_password_encrypted,
                    connection_metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                connection_id, tenant_id, connection_name, host, port,
                database_name, username, password_encrypted,
                json.dumps(connection_metadata or {})
            ))
            
            conn.commit()
            logger.info(f"Created connection: {connection_name} ({connection_id}) for tenant {tenant_id}")
            return connection_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create connection: {e}")
            raise
        finally:
            cursor.close()
    
    def get_connection_details(self, connection_id: str, tenant_id: str) -> Optional[Dict]:
        """Get connection details (tenant-scoped)"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT * FROM connections 
                WHERE connection_id = %s AND tenant_id = %s
            """, (connection_id, tenant_id))
            
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            cursor.close()
    
    def list_connections(self, tenant_id: str) -> List[Dict]:
        """List all connections for a tenant"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT 
                    connection_id, tenant_id, connection_name, db_host as host, db_port as port,
                    db_name as database_name, db_user as username, db_password_encrypted as password,
                    is_active, connection_metadata, created_at, updated_at
                FROM connections 
                WHERE tenant_id = %s 
                ORDER BY created_at DESC
            """, (tenant_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def update_connection_status(self, connection_id: str, tenant_id: str, status: str):
        """Update connection status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE connections 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE connection_id = %s AND tenant_id = %s
            """, (status, connection_id, tenant_id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update connection status: {e}")
            raise
        finally:
            cursor.close()
    
    def set_active_connection(self, connection_id: str, tenant_id: str):
        """Set a connection as active (deactivate others)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Deactivate all connections for this tenant
            cursor.execute("""
                UPDATE connections 
                SET is_active = FALSE 
                WHERE tenant_id = %s
            """, (tenant_id,))
            
            # Activate the specified connection
            cursor.execute("""
                UPDATE connections 
                SET is_active = TRUE, status = 'connected', updated_at = CURRENT_TIMESTAMP
                WHERE connection_id = %s AND tenant_id = %s
            """, (connection_id, tenant_id))
            
            conn.commit()
            logger.info(f"Set active connection: {connection_id} for tenant {tenant_id}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to set active connection: {e}")
            raise
        finally:
            cursor.close()
    
    def get_active_connection(self, tenant_id: str) -> Optional[Dict]:
        """Get the active connection for a tenant"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT * FROM connections 
                WHERE tenant_id = %s AND is_active = TRUE
                LIMIT 1
            """, (tenant_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            cursor.close()
    
    def delete_connection(self, connection_id: str, tenant_id: str):
        """Delete a connection (tenant-scoped)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM connections 
                WHERE connection_id = %s AND tenant_id = %s AND is_active = FALSE
            """, (connection_id, tenant_id))
            
            conn.commit()
            logger.info(f"Deleted connection: {connection_id}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete connection: {e}")
            raise
        finally:
            cursor.close()
    
    # ============= TABLE METADATA MANAGEMENT =============
    
    def save_table_metadata(
        self,
        tenant_id: str,
        connection_id: str,
        table_name: str,
        schema_name: str,
        table_description: Optional[str] = None,
        column_descriptions: Optional[Dict] = None,
        sample_values: Optional[Dict] = None,
        row_count: Optional[int] = None,
        data_types: Optional[Dict] = None,
        relationships: Optional[Dict] = None,
        business_context: Optional[str] = None
    ) -> str:
        """Save or update table metadata"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            catalog_id = str(uuid.uuid4())
            
            # Create search vector from description and business context
            search_text = f"{table_name} {table_description or ''} {business_context or ''}"
            
            cursor.execute("""
                INSERT INTO table_metadata_catalog (
                    catalog_id, tenant_id, connection_id, table_name, schema_name,
                    table_description, column_descriptions, sample_values, row_count,
                    data_types, relationships, business_context, search_vector
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector('english', %s))
                ON CONFLICT (tenant_id, connection_id, table_name, schema_name)
                DO UPDATE SET
                    table_description = EXCLUDED.table_description,
                    column_descriptions = EXCLUDED.column_descriptions,
                    sample_values = EXCLUDED.sample_values,
                    row_count = EXCLUDED.row_count,
                    data_types = EXCLUDED.data_types,
                    relationships = EXCLUDED.relationships,
                    business_context = EXCLUDED.business_context,
                    search_vector = to_tsvector('english', %s),
                    last_synced = CURRENT_TIMESTAMP
            """, (
                catalog_id, tenant_id, connection_id, table_name, schema_name,
                table_description, json.dumps(column_descriptions or {}),
                json.dumps(sample_values or {}), row_count,
                json.dumps(data_types or {}), json.dumps(relationships or {}),
                business_context, search_text, search_text
            ))
            
            conn.commit()
            logger.info(f"Saved metadata for table: {table_name} (tenant: {tenant_id})")
            return catalog_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save table metadata: {e}")
            raise
        finally:
            cursor.close()
    
    def get_table_metadata(
        self,
        tenant_id: str,
        connection_id: str,
        table_name: str,
        schema_name: str = 'public'
    ) -> Optional[Dict]:
        """Get metadata for a specific table"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT * FROM table_metadata_catalog
                WHERE tenant_id = %s AND connection_id = %s 
                AND table_name = %s AND schema_name = %s
            """, (tenant_id, connection_id, table_name, schema_name))
            
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            cursor.close()
    
    def list_table_metadata(
        self,
        tenant_id: str,
        connection_id: str
    ) -> List[Dict]:
        """List all table metadata for a connection"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT * FROM table_metadata_catalog
                WHERE tenant_id = %s AND connection_id = %s
                ORDER BY table_name
            """, (tenant_id, connection_id))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def search_relevant_tables(
        self,
        tenant_id: str,
        connection_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """Search for relevant tables using full-text search"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT *, 
                    ts_rank(search_vector, to_tsquery('english', %s)) as rank
                FROM table_metadata_catalog
                WHERE tenant_id = %s AND connection_id = %s
                AND search_vector @@ to_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
            """, (query, tenant_id, connection_id, query, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def get_connection_table_count(self, tenant_id: str, connection_id: str) -> int:
        """Get count of synced tables for a connection"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM table_metadata_catalog
                WHERE tenant_id = %s AND connection_id = %s
            """, (tenant_id, connection_id))
            
            return cursor.fetchone()[0]
        finally:
            cursor.close()
