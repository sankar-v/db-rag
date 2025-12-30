"""
FastAPI Backend for DB-RAG
Real-time conversational AI with database querying and document management
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import asyncio
from dotenv import load_dotenv
import json

from main import DBRAG
from config import Config, MetadataDatabaseConfig
from connection_manager import ConnectionManager
from database import DatabaseManager
from metadata_database import MetadataDatabaseManager
import os

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DB-RAG API",
    description="Agentic RAG for Relational Databases with Real-time Querying",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global DB-RAG instance, connection manager, and metadata database
rag_instance: Optional[DBRAG] = None
connection_manager = ConnectionManager()

# Initialize metadata database
metadata_db_config = MetadataDatabaseConfig.from_env()
metadata_db: Optional[MetadataDatabaseManager] = None

if metadata_db_config.enabled:
    try:
        metadata_db = MetadataDatabaseManager(
            host=metadata_db_config.host,
            port=metadata_db_config.port,
            database=metadata_db_config.database,
            user=metadata_db_config.user,
            password=metadata_db_config.password
        )
        metadata_db.connect()
        logger.info("Metadata database connected successfully")
        
        # Create default tenant if it doesn't exist
        default_tenant_id = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        default_tenant_name = os.getenv("DEFAULT_TENANT_NAME", "Development")
        
        if not metadata_db.get_tenant(default_tenant_id):
            metadata_db.create_tenant(
                tenant_name=default_tenant_name,
                organization="Default Organization"
            )
            logger.info(f"Created default tenant: {default_tenant_name}")
    except Exception as e:
        logger.error(f"Failed to initialize metadata database: {e}")
        logger.warning("Falling back to file-based connection storage")
        metadata_db = None

# Helper function to get current tenant ID (from header or default)
def get_tenant_id(request: Any = None) -> str:
    """Get tenant ID from request header or use default"""
    # In production, extract from JWT token or API key
    # For now, use default tenant
    return os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")


# Pydantic models
class QueryRequest(BaseModel):
    question: str
    mode: Optional[str] = "auto"  # auto, sql, vector


class QueryResponse(BaseModel):
    success: bool
    answer: str
    query: str
    sql_results: Optional[Dict[str, Any]] = None
    vector_results: Optional[Dict[str, Any]] = None
    routing: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class DocumentRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    success: bool
    document_id: str
    message: str


class ConnectionRequest(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str = "public"


class SyncTablesRequest(BaseModel):
    tables: List[str]


class SystemStatus(BaseModel):
    status: str
    database_connected: bool
    tables_count: int
    documents_count: int
    metadata_synced: bool


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize DB-RAG on startup"""
    global rag_instance
    try:
        logger.info("Initializing DB-RAG system...")
        rag_instance = DBRAG()
        rag_instance.initialize()
        logger.info("DB-RAG system initialized successfully")
        
        # If using metadata database, ensure default connection is registered and synced
        if metadata_db and rag_instance:
            tenant_id = get_tenant_id()
            db_config = rag_instance.config.database
            
            # Check if connection already exists
            connections = metadata_db.list_connections(tenant_id)
            existing_conn = None
            for conn in connections:
                if (conn['host'] == db_config.host and 
                    conn['port'] == db_config.port and 
                    conn['database_name'] == db_config.database):
                    existing_conn = conn
                    break
            
            if not existing_conn:
                # Create default connection entry
                connection_id = metadata_db.create_connection(
                    tenant_id=tenant_id,
                    connection_name=f"{db_config.database} (Default)",
                    host=db_config.host,
                    port=db_config.port,
                    database_name=db_config.database,
                    username=db_config.user,
                    password=db_config.password,
                    schema_name=db_config.schema,
                    connection_metadata={"auto_synced": True}
                )
                logger.info(f"Created default connection entry for {db_config.database}")
            else:
                connection_id = existing_conn['connection_id']
                logger.info(f"Default connection for {db_config.database} already exists")
            
            # Sync table metadata to control plane if needed
            table_count = metadata_db.get_connection_table_count(tenant_id, connection_id)
            if table_count == 0:
                logger.info(f"Syncing table metadata to control plane for connection {connection_id}")
                # Get tables directly from the database
                tables = rag_instance.orchestrator.db.get_all_tables(
                    exclude_tables=[rag_instance.config.rag.documents_table]
                )
                synced_count = 0
                
                for table_name in tables:
                    try:
                        # Get basic table info from database
                        conn = rag_instance.orchestrator.db.get_connection()
                        cursor = conn.cursor()
                        
                        # Get column information
                        cursor.execute(f"""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_schema = %s AND table_name = %s
                            ORDER BY ordinal_position
                        """, (db_config.schema, table_name))
                        
                        columns = cursor.fetchall()
                        column_descriptions = {col[0]: "" for col in columns}
                        data_types = {col[0]: col[1] for col in columns}
                        
                        # Get row count
                        cursor.execute(f"SELECT COUNT(*) FROM {db_config.schema}.{table_name}")
                        row_count = cursor.fetchone()[0]
                        cursor.close()
                        
                        # Save to control plane
                        metadata_db.save_table_metadata(
                            tenant_id=tenant_id,
                            connection_id=connection_id,
                            table_name=table_name,
                            schema_name=db_config.schema,
                            table_description=f"Table {table_name}",  # Basic description
                            business_context="",
                            column_descriptions=column_descriptions,
                            sample_values={},
                            row_count=row_count,
                            data_types=data_types,
                            relationships={}
                        )
                        synced_count += 1
                        logger.info(f"Synced table: {table_name}")
                    except Exception as e:
                        logger.error(f"Failed to sync table {table_name}: {e}")
                        
                logger.info(f"Synced {synced_count} tables to control plane")
                
    except Exception as e:
        logger.error(f"Failed to initialize DB-RAG: {str(e)}")
        # Don't fail startup, allow connection configuration


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global rag_instance
    if rag_instance:
        rag_instance.close()
        logger.info("DB-RAG system closed")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "db-rag-api"}


# System status endpoint
@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get system status"""
    global rag_instance
    
    if not rag_instance:
        return SystemStatus(
            status="not_initialized",
            database_connected=False,
            tables_count=0,
            documents_count=0,
            metadata_synced=False
        )
    
    try:
        # Get table count from control plane if using metadata DB
        if metadata_db:
            tenant_id = get_tenant_id()
            connections = metadata_db.list_connections(tenant_id)
            active_connection = next((c for c in connections if c.get('is_active')), None)
            
            if active_connection:
                connection_id = active_connection['connection_id']
                table_count = metadata_db.get_connection_table_count(tenant_id, connection_id)
            else:
                table_count = 0
            metadata_count = table_count
        else:
            # Fallback to counting tables directly from database
            tables = rag_instance.db_manager.get_all_tables(
                exclude_tables=[rag_instance.config.rag.documents_table]
            )
            table_count = len(tables)
            metadata_count = table_count
        
        # Get document count
        conn = rag_instance.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {rag_instance.config.rag.documents_table}")
        doc_count = cursor.fetchone()[0]
        cursor.close()
        
        return SystemStatus(
            status="ready",
            database_connected=True,
            tables_count=table_count,
            documents_count=doc_count,
            metadata_synced=metadata_count > 0
        )
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        return SystemStatus(
            status="error",
            database_connected=False,
            tables_count=0,
            documents_count=0,
            metadata_synced=False
        )


# Query endpoint
@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a natural language query"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        logger.info(f"Processing query: {request.question}")
        
        if request.mode == "sql":
            result = rag_instance.query_sql_only(request.question)
        elif request.mode == "vector":
            result = rag_instance.search_documents_only(request.question)
        else:
            result = rag_instance.query(request.question)
        
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for real-time chat
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    global rag_instance
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            question = message.get("question", "")
            
            if not question:
                await websocket.send_json({
                    "type": "error",
                    "message": "No question provided"
                })
                continue
            
            # Send typing indicator
            await websocket.send_json({
                "type": "typing",
                "message": "Processing your question..."
            })
            
            # Process query
            if rag_instance:
                result = rag_instance.query(question)
                await websocket.send_json({
                    "type": "response",
                    "data": result
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "System not initialized"
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


# Document management endpoints
@app.post("/api/documents", response_model=DocumentResponse)
async def add_document(request: DocumentRequest):
    """Add a document to the vector store"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        doc_id = rag_instance.add_document(request.content, request.metadata)
        return DocumentResponse(
            success=True,
            document_id=doc_id,
            message="Document added successfully"
        )
    except Exception as e:
        logger.error(f"Failed to add document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document file"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        filename = file.filename or "unknown"
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if file_ext == 'pdf':
            # Extract text from PDF
            try:
                import PyPDF2
                import io
                
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                if not text_content.strip():
                    raise ValueError("No text could be extracted from PDF")
                    
            except ImportError:
                raise HTTPException(
                    status_code=500, 
                    detail="PDF support not installed. Please install PyPDF2: pip install PyPDF2"
                )
            except Exception as e:
                logger.error(f"Failed to extract text from PDF: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")
        
        elif file_ext in ['txt', 'md', 'csv', 'json', 'xml']:
            # Text-based files
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                # Try other encodings
                try:
                    text_content = content.decode('latin-1')
                except:
                    raise HTTPException(status_code=400, detail="Unable to decode file. Please ensure it's a valid text file.")
        
        elif file_ext in ['doc', 'docx']:
            raise HTTPException(
                status_code=400,
                detail="Word documents not yet supported. Please convert to PDF or text format."
            )
        
        else:
            # Try to decode as text
            try:
                text_content = content.decode('utf-8')
            except:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: .{file_ext}. Supported formats: PDF, TXT, MD, CSV, JSON, XML"
                )
        
        # Chunk large documents to handle token limits
        # OpenAI's text-embedding-ada-002 has 8191 token limit
        # Approximate: 1 token ~= 4 characters, so chunk at ~24,000 chars to be safe
        max_chunk_chars = 20000
        
        if len(text_content) > max_chunk_chars:
            # Generate a unique parent document ID
            import uuid
            parent_doc_id = str(uuid.uuid4())
            
            # Split into chunks
            chunks = []
            for i in range(0, len(text_content), max_chunk_chars):
                chunk = text_content[i:i + max_chunk_chars]
                chunks.append(chunk)
            
            # Add each chunk as a separate document with chunk metadata
            doc_ids = []
            for idx, chunk in enumerate(chunks):
                doc_id = rag_instance.add_document(
                    chunk,
                    metadata={
                        "filename": filename,
                        "content_type": file.content_type,
                        "file_type": file_ext,
                        "source": "upload",
                        "size_bytes": len(content),
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "parent_doc_id": parent_doc_id
                    }
                )
                doc_ids.append(doc_id)
            
            return DocumentResponse(
                success=True,
                document_id=parent_doc_id,  # Return parent ID
                message=f"File '{filename}' uploaded and split into {len(chunks)} chunks for vectorization"
            )
        else:
            # Add to vector store as single document
            doc_id = rag_instance.add_document(
                text_content,
                metadata={
                    "filename": filename,
                    "content_type": file.content_type,
                    "file_type": file_ext,
                    "source": "upload",
                    "size_bytes": len(content)
                }
            )
            
            return DocumentResponse(
                success=True,
                document_id=doc_id,
                message=f"File '{filename}' uploaded and vectorized successfully"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents(limit: int = 10, offset: int = 0):
    """List documents in the vector store, grouping chunks together"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        conn = rag_instance.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT id, content, metadata, created_at 
            FROM {rag_instance.config.rag.documents_table}
            ORDER BY created_at DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        all_docs = [dict(zip(columns, row)) for row in rows]
        
        cursor.close()
        
        # Group chunks by parent_doc_id
        grouped_docs = {}
        standalone_docs = []
        
        for doc in all_docs:
            metadata = doc.get('metadata', {})
            if isinstance(metadata, str):
                import json
                metadata = json.loads(metadata)
            
            parent_doc_id = metadata.get('parent_doc_id')
            chunk_index = metadata.get('chunk_index')
            
            # If this is a chunk (has parent_doc_id), group it
            if parent_doc_id:
                if parent_doc_id not in grouped_docs:
                    # Create parent document entry
                    total_chunks = metadata.get('total_chunks', 1)
                    filename = metadata.get('filename', 'Untitled')
                    
                    grouped_docs[parent_doc_id] = {
                        'id': parent_doc_id,
                        'content': f"[Document with {total_chunks} chunks]\n\nFilename: {filename}\n\nThis document was automatically split into {total_chunks} chunks for efficient vectorization. Each chunk is searchable independently.",
                        'metadata': {
                            **{k: v for k, v in metadata.items() if k not in ['chunk_index', 'parent_doc_id']},
                            'is_chunked': True,
                            'total_chunks': total_chunks,
                            'chunk_ids': []
                        },
                        'created_at': doc['created_at']
                    }
                
                # Add chunk ID to the list
                grouped_docs[parent_doc_id]['metadata']['chunk_ids'].append({
                    'id': doc['id'],
                    'index': chunk_index,
                    'preview': doc['content'][:150] + '...' if len(doc['content']) > 150 else doc['content']
                })
                
                # Sort chunks by index
                grouped_docs[parent_doc_id]['metadata']['chunk_ids'].sort(key=lambda x: x['index'])
            else:
                # Not a chunk, add as-is
                standalone_docs.append(doc)
        
        # Combine grouped and standalone documents
        documents = list(grouped_docs.values()) + standalone_docs
        documents.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply pagination
        paginated_docs = documents[offset:offset + limit]
        
        return {
            "success": True,
            "documents": paginated_docs,
            "count": len(paginated_docs),
            "total": len(documents)
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Table metadata endpoints
@app.get("/api/tables")
async def list_tables():
    """List all tables with metadata from control plane"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        # If using metadata database (multi-tenant), get tables from control plane
        if metadata_db:
            tenant_id = get_tenant_id()
            
            # Get active connection
            connections = metadata_db.list_connections(tenant_id)
            active_connection = next((c for c in connections if c.get('is_active')), None)
            
            if not active_connection:
                # No active connection, return empty list
                return {
                    "success": True,
                    "tables": [],
                    "count": 0
                }
            
            connection_id = active_connection['connection_id']
            
            # Get all table metadata from control plane for active connection
            tables_metadata = metadata_db.list_table_metadata(tenant_id, connection_id)
            
            # Transform to match frontend expectations
            tables = []
            for table_meta in tables_metadata:
                tables.append({
                    "table_name": table_meta.get("table_name"),
                    "schema": table_meta.get("schema_name", "public")  # Frontend expects 'schema'
                })
            
            return {
                "success": True,
                "tables": tables,
                "count": len(tables)
            }
        else:
            # Fallback to old behavior for non-multi-tenant setup
            tables = rag_instance.db_manager.get_all_tables(
                exclude_tables=[rag_instance.config.rag.documents_table]
            )
            
            # Transform simple list to objects
            tables_obj = [{"table_name": t, "schema": "public"} for t in tables]
            
            return {
                "success": True,
                "tables": tables_obj,
                "count": len(tables_obj)
            }
    except Exception as e:
        logger.error(f"Failed to list tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables/{table_name}")
async def get_table_metadata(table_name: str):
    """Get metadata for a specific table from control plane"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        # If using metadata database (multi-tenant), get from control plane
        if metadata_db:
            tenant_id = get_tenant_id()
            
            # Get active connection
            connections = metadata_db.list_connections(tenant_id)
            active_connection = next((c for c in connections if c.get('is_active')), None)
            
            if not active_connection:
                raise HTTPException(status_code=404, detail="No active connection found")
            
            connection_id = active_connection['connection_id']
            
            # Get metadata from control plane
            metadata = metadata_db.get_table_metadata(tenant_id, connection_id, table_name)
            
            if not metadata:
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
            # Transform to match frontend expectations
            transformed_metadata = {
                "table_name": metadata.get("table_name"),
                "description": metadata.get("table_description", ""),
                "columns": [],
                "sample_data": []
            }
            
            # Parse column descriptions and data types
            column_descriptions = metadata.get("column_descriptions", {})
            data_types = metadata.get("data_types", {})
            
            if isinstance(column_descriptions, str):
                import json
                column_descriptions = json.loads(column_descriptions)
            if isinstance(data_types, str):
                import json
                data_types = json.loads(data_types)
            
            # Build columns array
            for col_name, description in column_descriptions.items():
                transformed_metadata["columns"].append({
                    "column_name": col_name,
                    "data_type": data_types.get(col_name, "unknown"),
                    "description": description
                })
            
            return {
                "success": True,
                "metadata": transformed_metadata
            }
        else:
            # Fallback to old behavior
            metadata = rag_instance.orchestrator.metadata_manager.get_table_metadata(table_name)
            
            if not metadata:
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
            return {
                "success": True,
                "metadata": metadata
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get table metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metadata/sync")
async def sync_metadata(force_update: bool = False):
    """Sync metadata catalog for all tables"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        # Run sync in background to avoid timeout
        rag_instance.sync_metadata(force_update=force_update)
        
        return {
            "success": True,
            "message": "Metadata sync completed"
        }
    except Exception as e:
        logger.error(f"Failed to sync metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Database connection management
@app.post("/api/connection/test")
async def test_connection(request: ConnectionRequest):
    """Test database connection with provided credentials"""
    try:
        from database import DatabaseManager
        from config import DatabaseConfig
        
        db_config = DatabaseConfig(
            host=request.host,
            port=request.port,
            database=request.database,
            user=request.user,
            password=request.password,
            schema=request.schema
        )
        
        db_manager = DatabaseManager(db_config)
        tables = db_manager.get_all_tables()
        db_manager.close()
        
        return {
            "success": True,
            "message": "Connection successful",
            "tables_count": len(tables)
        }
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@app.post("/api/connection/configure")
async def configure_connection(request: ConnectionRequest):
    """Configure and reconnect with new database credentials"""
    global rag_instance
    
    try:
        # Close existing connection
        if rag_instance:
            rag_instance.close()
        
        # Create new config
        from config import Config, DatabaseConfig
        
        config = Config()
        config.database = DatabaseConfig(
            host=request.host,
            port=request.port,
            database=request.database,
            user=request.user,
            password=request.password,
            schema=request.schema
        )
        
        # Initialize new instance
        rag_instance = DBRAG(config)
        rag_instance.initialize()
        
        return {
            "success": True,
            "message": "Database connection configured successfully"
        }
    except Exception as e:
        logger.error(f"Failed to configure connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEW CONNECTION MANAGEMENT ENDPOINTS
# ============================================================================

class ConnectionCreateRequest(BaseModel):
    name: str
    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str = "public"
    tables: Optional[List[str]] = None


@app.get("/api/connections")
async def list_connections():
    """List all saved connections for the current tenant"""
    try:
        tenant_id = get_tenant_id()
        
        if metadata_db:
            # Use metadata database
            connections = metadata_db.list_connections(tenant_id)
            # Transform to frontend format and add table counts
            transformed_connections = []
            for conn in connections:
                # Get actual table count from data plane
                try:
                    from config import DatabaseConfig
                    temp_config = DatabaseConfig(
                        host=conn['host'],
                        port=conn['port'],
                        database=conn['database_name'],
                        user=conn['username'],
                        password=conn['password'],
                        schema='public'
                    )
                    temp_db = DatabaseManager(temp_config)
                    tables = temp_db.get_all_tables()
                    table_count = len(tables)
                except Exception as e:
                    logger.warning(f"Could not get table count for connection {conn['connection_id']}: {e}")
                    table_count = 0
                
                transformed_connections.append({
                    'id': conn['connection_id'],
                    'name': conn['connection_name'],
                    'host': conn['host'],
                    'port': conn['port'],
                    'database': conn['database_name'],
                    'user': conn['username'],
                    'schema': 'public',  # Default schema
                    'is_active': conn['is_active'],
                    'status': 'connected' if conn['is_active'] else 'disconnected',
                    'tables_count': table_count,
                    'synced_tables_count': metadata_db.get_connection_table_count(
                        tenant_id, conn['connection_id']
                    ),
                    'created_at': conn['created_at'].isoformat() if conn.get('created_at') else None
                })
            return {"success": True, "connections": transformed_connections}
        else:
            # Fallback to file-based storage
            connections = connection_manager.list_connections()
            return {"success": True, "connections": connections}
            
    except Exception as e:
        logger.error(f"Failed to list connections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connections/test")
async def test_new_connection(request: ConnectionCreateRequest):
    """Test a database connection without saving it"""
    try:
        # Create a temporary database manager
        temp_db = DatabaseManager(
            host=request.host,
            port=request.port,
            database=request.database,
            user=request.user,
            password=request.password
        )
        
        # Try to connect
        conn = temp_db.get_connection()
        
        # Get list of tables
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{request.schema}'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        return {
            "success": True,
            "message": f"Successfully connected to {request.database}",
            "tables": tables
        }
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/connections")
async def create_connection(request: ConnectionCreateRequest):
    """Save a new database connection"""
    try:
        tenant_id = get_tenant_id()
        
        if metadata_db:
            # Use metadata database
            connection_id = metadata_db.create_connection(
                tenant_id=tenant_id,
                connection_name=request.name,
                host=request.host,
                port=request.port,
                database_name=request.database,
                username=request.user,
                password=request.password,
                schema_name=request.schema,
                connection_metadata={"tables": request.tables or []}
            )
        else:
            # Fallback to file-based storage
            connection_id = connection_manager.add_connection(
                name=request.name,
                host=request.host,
                port=request.port,
                database=request.database,
                user=request.user,
                password=request.password,
                schema=request.schema,
                tables=request.tables
            )
        
        return {
            "success": True,
            "connection_id": connection_id,
            "message": f"Connection '{request.name}' saved successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/connections/{connection_id}")
async def update_connection(connection_id: str, request: ConnectionCreateRequest):
    """Update an existing connection"""
    try:
        success = connection_manager.update_connection(
            connection_id,
            name=request.name,
            host=request.host,
            port=request.port,
            database=request.database,
            user=request.user,
            password=request.password,
            schema=request.schema,
            tables=request.tables
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        return {
            "success": True,
            "message": f"Connection updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Delete a connection"""
    try:
        tenant_id = get_tenant_id()
        
        if metadata_db:
            # Use metadata database
            metadata_db.delete_connection(connection_id, tenant_id)
        else:
            # Fallback to file-based storage
            connection_manager.delete_connection(connection_id)
        
        return {"success": True, "message": "Connection deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connections/{connection_id}/activate")
async def activate_connection(connection_id: str):
    """Set a connection as the active connection and reinitialize RAG"""
    global rag_instance
    
    try:
        tenant_id = get_tenant_id()
        
        if metadata_db:
            # Use metadata database
            connection = metadata_db.get_connection_details(connection_id, tenant_id)
            if not connection:
                raise HTTPException(status_code=404, detail="Connection not found")
            
            # Create database config from connection
            db_config = DatabaseConfig(
                host=connection['db_host'],
                port=connection['db_port'],
                database=connection['db_name'],
                user=connection['db_user'],
                password=connection['db_password_encrypted'],
                schema=connection['schema_name']
            )
            
            # Create new config with this database
            config = Config()
            config.database = db_config
            
            # Initialize new RAG instance with this connection
            rag_instance = DBRAG(config)
            rag_instance.initialize()
            
            # Set as active in metadata database
            metadata_db.set_active_connection(connection_id, tenant_id)
            
            return {
                "success": True,
                "message": f"Connection '{connection['connection_name']}' is now active"
            }
        else:
            # Fallback to file-based storage
            connection = connection_manager.get_connection(connection_id)
            if not connection:
                raise HTTPException(status_code=404, detail="Connection not found")
            
            # Create config from connection
            config = Config(
                host=connection['host'],
                port=connection['port'],
                database=connection['database'],
                user=connection['user'],
                password=connection['password'],
                schema=connection.get('schema', 'public')
            )
            
            # Initialize new RAG instance with this connection
            rag_instance = DBRAG(config)
            rag_instance.initialize()
            
            # Set as active in connection manager
            connection_manager.set_active_connection(connection_id)
            
            return {
                "success": True,
                "message": f"Connection '{connection['name']}' is now active"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connections/{connection_id}/sync")
async def sync_connection_tables(connection_id: str, request: SyncTablesRequest):
    """Sync metadata for selected tables in a connection"""
    try:
        tenant_id = get_tenant_id()
        
        if metadata_db:
            # Use metadata database
            connection = metadata_db.get_connection_details(connection_id, tenant_id)
            if not connection:
                raise HTTPException(status_code=404, detail="Connection not found")
        else:
            # Fallback to file-based storage
            connection = connection_manager.get_connection(connection_id)
            if not connection:
                raise HTTPException(status_code=404, detail="Connection not found")
        
        if not rag_instance:
            raise HTTPException(status_code=400, detail="No active RAG instance")
        
        # Sync the specified tables to metadata database
        synced_count = 0
        for table_name in request.tables:
            try:
                # Discover and add table to RAG's metadata catalog
                rag_instance.metadata_catalog.discover_and_add_table(table_name)
                
                # If using metadata database, also save to control plane
                if metadata_db:
                    # Get table info from RAG instance
                    table_info = rag_instance.metadata_catalog.get_table_info(table_name)
                    
                    if table_info:
                        metadata_db.save_table_metadata(
                            tenant_id=tenant_id,
                            connection_id=connection_id,
                            table_name=table_name,
                            schema_name=connection.get('schema_name', 'public'),
                            table_description=table_info.get('description'),
                            column_descriptions=table_info.get('columns'),
                            sample_values=table_info.get('sample_data'),
                            data_types=table_info.get('data_types'),
                            business_context=table_info.get('business_context')
                        )
                
                synced_count += 1
                logger.info(f"Synced table: {table_name} for tenant {tenant_id}")
                
            except Exception as e:
                logger.warning(f"Failed to sync table {table_name}: {e}")
        
        # Update connection with synced tables
        if metadata_db:
            # Update in metadata database (table count is automatically updated)
            pass
        else:
            connection_manager.update_connection(
                connection_id,
                tables=request.tables
            )
            connection_manager.update_tables_count(connection_id, synced_count)
        
        return {
            "success": True,
            "tables_synced": synced_count,
            "message": f"Synced {synced_count} tables to metadata catalog"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
