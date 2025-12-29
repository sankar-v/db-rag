"""
Database connector for structured data retrieval from relational databases.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import logging

from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnector:
    """Connects to relational databases and retrieves structured data."""
    
    def __init__(self, config: Config):
        """
        Initialize database connector.
        
        Args:
            config: Configuration object with database settings
        """
        self.config = config
        self.engine: Optional[Engine] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish database connection."""
        try:
            db_url = self.config.get_db_url()
            self.engine = create_engine(db_url, echo=False)
            logger.info(f"Connected to database: {self.config.db_type}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def get_table_names(self) -> List[str]:
        """
        Get list of all table names in the database.
        
        Returns:
            List of table names
        """
        if not self.engine:
            raise RuntimeError("Database not connected")
        
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        if not self.engine:
            raise RuntimeError("Database not connected")
        
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        return columns
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of result rows as dictionaries
        """
        if not self.engine:
            raise RuntimeError("Database not connected")
        
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                # Convert rows to dictionaries
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return rows
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get sample data from a table.
        
        Args:
            table_name: Name of the table
            limit: Number of rows to retrieve
            
        Returns:
            List of sample rows
        """
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.execute_query(query)
    
    def get_database_schema_text(self) -> str:
        """
        Get a text representation of the entire database schema.
        
        Returns:
            String describing all tables and their columns
        """
        schema_text = "Database Schema:\n\n"
        
        for table_name in self.get_table_names():
            schema_text += f"Table: {table_name}\n"
            columns = self.get_table_schema(table_name)
            
            for col in columns:
                col_name = col['name']
                col_type = str(col['type'])
                nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                schema_text += f"  - {col_name}: {col_type} {nullable}\n"
            
            schema_text += "\n"
        
        return schema_text
    
    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
