"""
Database connection and schema introspection layer
"""
import psycopg2
from psycopg2.extensions import connection as PgConnection
from sqlalchemy import create_engine, inspect, MetaData, Table, Column
from sqlalchemy.engine import Engine
from typing import List, Dict, Any, Optional
import logging

from config import DatabaseConfig


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and schema introspection"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Optional[Engine] = None
        self._connection: Optional[PgConnection] = None
    
    def get_engine(self) -> Engine:
        """Get or create SQLAlchemy engine"""
        if self._engine is None:
            self._engine = create_engine(
                self.config.get_connection_string(),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
            logger.info(f"Created database engine for {self.config.database}")
        return self._engine
    
    def get_connection(self) -> PgConnection:
        """Get or create psycopg2 connection for pgvector operations"""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
            logger.info(f"Created psycopg2 connection to {self.config.database}")
        return self._connection
    
    def close(self):
        """Close all database connections"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Closed psycopg2 connection")
        if self._engine:
            self._engine.dispose()
            logger.info("Disposed SQLAlchemy engine")
    
    def get_all_tables(self, exclude_tables: Optional[List[str]] = None) -> List[str]:
        """
        Get all user-defined tables in the configured schema
        
        Args:
            exclude_tables: List of table names to exclude
            
        Returns:
            List of table names
        """
        if exclude_tables is None:
            exclude_tables = []
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """, (self.config.schema,))
            
            tables = [row[0] for row in cursor.fetchall() if row[0] not in exclude_tables]
            logger.info(f"Found {len(tables)} tables in schema '{self.config.schema}'")
            return tables
        finally:
            cursor.close()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed schema information for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary containing table schema details
        """
        engine = self.get_engine()
        inspector = inspect(engine)
        
        # Get columns
        columns = inspector.get_columns(table_name, schema=self.config.schema)
        
        # Get primary key
        pk_constraint = inspector.get_pk_constraint(table_name, schema=self.config.schema)
        
        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name, schema=self.config.schema)
        
        # Get indexes
        indexes = inspector.get_indexes(table_name, schema=self.config.schema)
        
        return {
            "table_name": table_name,
            "columns": columns,
            "primary_key": pk_constraint.get("constrained_columns", []),
            "foreign_keys": foreign_keys,
            "indexes": indexes
        }
    
    def get_table_context_string(self, table_name: str) -> str:
        """
        Generate a human-readable context string for a table
        Useful for LLM prompts
        
        Args:
            table_name: Name of the table
            
        Returns:
            Formatted string describing the table schema
        """
        schema = self.get_table_schema(table_name)
        
        context = f"Table: {table_name}\n"
        context += "Columns:\n"
        
        for col in schema["columns"]:
            col_type = str(col["type"])
            nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get("default") else ""
            
            context += f"  - {col['name']} ({col_type}) {nullable}{default}\n"
        
        if schema["primary_key"]:
            context += f"Primary Key: {', '.join(schema['primary_key'])}\n"
        
        if schema["foreign_keys"]:
            context += "Foreign Keys:\n"
            for fk in schema["foreign_keys"]:
                context += f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}\n"
        
        return context
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get sample rows from a table
        
        Args:
            table_name: Name of the table
            limit: Maximum number of rows to retrieve
            
        Returns:
            List of dictionaries representing rows
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            
        Returns:
            List of dictionaries representing query results
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            conn.commit()  # Commit after successful query
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            conn.rollback()  # Rollback on error
            logger.error(f"Query execution failed: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """
        Validate a SQL query without executing it
        
        Args:
            query: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Use EXPLAIN to validate without executing
            cursor.execute(f"EXPLAIN {query}")
            conn.commit()  # Commit successful validation
            return True, None
        except Exception as e:
            conn.rollback()  # Rollback on error
            return False, str(e)
        finally:
            cursor.close()
    
    def ensure_pgvector_extension(self):
        """Ensure pgvector extension is enabled"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
            logger.info("Ensured pgvector extension is enabled")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to enable pgvector: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                );
            """, (self.config.schema, table_name))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
