"""
Connection Manager - Handles multiple database connections
"""
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages multiple database connections"""
    
    def __init__(self, storage_file: str = ".connections.json"):
        self.storage_file = storage_file
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.active_connection_id: Optional[str] = None
        self.load_connections()
    
    def load_connections(self):
        """Load connections from storage file"""
        if Path(self.storage_file).exists():
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self.connections = data.get('connections', {})
                    self.active_connection_id = data.get('active_connection_id')
                logger.info(f"Loaded {len(self.connections)} connections from storage")
            except Exception as e:
                logger.error(f"Failed to load connections: {e}")
                self.connections = {}
                self.active_connection_id = None
    
    def save_connections(self):
        """Save connections to storage file"""
        try:
            data = {
                'connections': self.connections,
                'active_connection_id': self.active_connection_id
            }
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.connections)} connections to storage")
        except Exception as e:
            logger.error(f"Failed to save connections: {e}")
    
    def add_connection(
        self,
        name: str,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        schema: str = "public",
        tables: Optional[List[str]] = None
    ) -> str:
        """Add a new connection"""
        connection_id = str(uuid.uuid4())
        
        self.connections[connection_id] = {
            'id': connection_id,
            'name': name,
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password,  # In production, encrypt this!
            'schema': schema,
            'tables': tables or [],
            'is_active': False,
            'status': 'disconnected',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        self.save_connections()
        logger.info(f"Added connection: {name} ({connection_id})")
        return connection_id
    
    def update_connection(
        self,
        connection_id: str,
        **kwargs
    ) -> bool:
        """Update an existing connection"""
        if connection_id not in self.connections:
            return False
        
        # Update allowed fields
        allowed_fields = ['name', 'host', 'port', 'database', 'user', 'password', 'schema', 'tables']
        for key, value in kwargs.items():
            if key in allowed_fields:
                self.connections[connection_id][key] = value
        
        self.connections[connection_id]['updated_at'] = datetime.utcnow().isoformat()
        self.save_connections()
        logger.info(f"Updated connection: {connection_id}")
        return True
    
    def delete_connection(self, connection_id: str) -> bool:
        """Delete a connection"""
        if connection_id not in self.connections:
            return False
        
        # Don't allow deleting active connection
        if self.connections[connection_id].get('is_active'):
            logger.warning(f"Cannot delete active connection: {connection_id}")
            return False
        
        del self.connections[connection_id]
        self.save_connections()
        logger.info(f"Deleted connection: {connection_id}")
        return True
    
    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get a connection by ID"""
        return self.connections.get(connection_id)
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """List all connections (without passwords)"""
        connections = []
        for conn in self.connections.values():
            # Create a copy without the password
            conn_copy = conn.copy()
            conn_copy.pop('password', None)
            connections.append(conn_copy)
        return connections
    
    def set_active_connection(self, connection_id: str) -> bool:
        """Set a connection as active"""
        if connection_id not in self.connections:
            return False
        
        # Deactivate all connections
        for conn in self.connections.values():
            conn['is_active'] = False
        
        # Activate the specified connection
        self.connections[connection_id]['is_active'] = True
        self.connections[connection_id]['status'] = 'connected'
        self.active_connection_id = connection_id
        
        self.save_connections()
        logger.info(f"Set active connection: {connection_id}")
        return True
    
    def get_active_connection(self) -> Optional[Dict[str, Any]]:
        """Get the currently active connection"""
        if self.active_connection_id and self.active_connection_id in self.connections:
            return self.connections[self.active_connection_id]
        return None
    
    def update_connection_status(self, connection_id: str, status: str):
        """Update connection status"""
        if connection_id in self.connections:
            self.connections[connection_id]['status'] = status
            self.save_connections()
    
    def update_tables_count(self, connection_id: str, count: int):
        """Update the number of tables for a connection"""
        if connection_id in self.connections:
            self.connections[connection_id]['tables_count'] = count
            self.save_connections()
