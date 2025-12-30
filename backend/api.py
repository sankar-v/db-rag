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
from config import Config

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

# Global DB-RAG instance
rag_instance: Optional[DBRAG] = None


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
        # Get table count
        tables = rag_instance.db_manager.get_all_tables(
            exclude_tables=[
                rag_instance.config.rag.metadata_catalog_table,
                rag_instance.config.rag.documents_table
            ]
        )
        
        # Get document count
        conn = rag_instance.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {rag_instance.config.rag.documents_table}")
        doc_count = cursor.fetchone()[0]
        cursor.close()
        
        # Check metadata sync
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {rag_instance.config.rag.metadata_catalog_table}")
        metadata_count = cursor.fetchone()[0]
        cursor.close()
        
        return SystemStatus(
            status="ready",
            database_connected=True,
            tables_count=len(tables),
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
        text_content = content.decode('utf-8')
        
        # Add to vector store
        doc_id = rag_instance.add_document(
            text_content,
            metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "source": "upload"
            }
        )
        
        return DocumentResponse(
            success=True,
            document_id=doc_id,
            message=f"File '{file.filename}' uploaded and vectorized successfully"
        )
    except Exception as e:
        logger.error(f"Failed to upload document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents(limit: int = 10, offset: int = 0):
    """List documents in the vector store"""
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
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        documents = [dict(zip(columns, row)) for row in rows]
        
        cursor.close()
        
        return {
            "success": True,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Table metadata endpoints
@app.get("/api/tables")
async def list_tables():
    """List all tables in the database"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
        tables = rag_instance.db_manager.get_all_tables(
            exclude_tables=[
                rag_instance.config.rag.metadata_catalog_table,
                rag_instance.config.rag.documents_table
            ]
        )
        
        return {
            "success": True,
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        logger.error(f"Failed to list tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables/{table_name}")
async def get_table_metadata(table_name: str):
    """Get metadata for a specific table"""
    global rag_instance
    
    if not rag_instance:
        raise HTTPException(status_code=503, detail="DB-RAG system not initialized")
    
    try:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
