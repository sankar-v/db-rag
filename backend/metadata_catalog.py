"""
Metadata catalog manager for table discovery and context
"""
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

from database import DatabaseManager
from config import LLMConfig, RAGConfig


logger = logging.getLogger(__name__)


class MetadataCatalogManager:
    """Manages the metadata catalog for table discovery"""
    
    def __init__(self, db_manager: DatabaseManager, llm_config: LLMConfig, rag_config: RAGConfig):
        self.db = db_manager
        self.llm_config = llm_config
        self.rag_config = rag_config
        self.client = OpenAI(api_key=llm_config.api_key)
        self.catalog_table = rag_config.metadata_catalog_table
    
    def initialize_catalog_table(self):
        """Create the metadata catalog table if it doesn't exist"""
        if self.db.table_exists(self.catalog_table):
            logger.info(f"Metadata catalog table '{self.catalog_table}' already exists")
            return
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Ensure pgvector extension is enabled
            self.db.ensure_pgvector_extension()
            
            # Create the catalog table
            cursor.execute(f"""
                CREATE TABLE {self.catalog_table} (
                    id SERIAL PRIMARY KEY,
                    table_name TEXT UNIQUE NOT NULL,
                    column_definitions TEXT NOT NULL,
                    table_description TEXT NOT NULL,
                    business_context TEXT,
                    sample_queries TEXT[],
                    description_embedding VECTOR({self.llm_config.embedding_dimensions}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create index for fast vector search
            cursor.execute(f"""
                CREATE INDEX ON {self.catalog_table} 
                USING ivfflat (description_embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
            conn.commit()
            logger.info(f"Created metadata catalog table: {self.catalog_table}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create metadata catalog: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def generate_table_description(self, table_name: str, schema_context: str, sample_data: List[Dict]) -> Dict[str, str]:
        """
        Use LLM to generate a comprehensive description of a table
        
        Args:
            table_name: Name of the table
            schema_context: Schema information string
            sample_data: Sample rows from the table
            
        Returns:
            Dictionary with description and business_context
        """
        sample_str = "\n".join([str(row) for row in sample_data[:3]])
        
        prompt = f"""You are a database documentation expert. Analyze the following table and provide:
1. A concise description (2-3 sentences) explaining what this table stores and its purpose
2. Business context describing what questions or insights this table can help answer
3. Three example natural language questions that could be answered using this table

Table Schema:
{schema_context}

Sample Data (first 3 rows):
{sample_str}

Respond in the following format:
DESCRIPTION: [your description]
BUSINESS_CONTEXT: [business context]
SAMPLE_QUESTIONS: [question 1] | [question 2] | [question 3]
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            
            # Parse the response
            lines = content.strip().split("\n")
            result = {
                "description": "",
                "business_context": "",
                "sample_questions": []
            }
            
            for line in lines:
                if line.startswith("DESCRIPTION:"):
                    result["description"] = line.replace("DESCRIPTION:", "").strip()
                elif line.startswith("BUSINESS_CONTEXT:"):
                    result["business_context"] = line.replace("BUSINESS_CONTEXT:", "").strip()
                elif line.startswith("SAMPLE_QUESTIONS:"):
                    questions = line.replace("SAMPLE_QUESTIONS:", "").strip()
                    result["sample_questions"] = [q.strip() for q in questions.split("|")]
            
            logger.info(f"Generated description for table: {table_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to generate description for {table_name}: {str(e)}")
            # Return a basic description
            return {
                "description": f"Database table: {table_name}",
                "business_context": "Stores structured data for analytical queries",
                "sample_questions": []
            }
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.llm_config.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def add_table_to_catalog(self, table_name: str, force_update: bool = False):
        """
        Add or update a table in the metadata catalog
        
        Args:
            table_name: Name of the table to add
            force_update: If True, update existing entry
        """
        # Check if table already exists in catalog
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT id FROM {self.catalog_table} WHERE table_name = %s", (table_name,))
            exists = cursor.fetchone()
            
            if exists and not force_update:
                logger.info(f"Table '{table_name}' already in catalog, skipping")
                return
            
            # Get schema and sample data
            schema_context = self.db.get_table_context_string(table_name)
            sample_data = self.db.get_sample_data(table_name, limit=3)
            
            # Generate description using LLM
            descriptions = self.generate_table_description(table_name, schema_context, sample_data)
            
            # Create searchable text for embedding
            searchable_text = f"{table_name} {descriptions['description']} {descriptions['business_context']}"
            embedding = self.generate_embedding(searchable_text)
            
            # Insert or update
            if exists:
                cursor.execute(f"""
                    UPDATE {self.catalog_table}
                    SET column_definitions = %s,
                        table_description = %s,
                        business_context = %s,
                        sample_queries = %s,
                        description_embedding = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE table_name = %s
                """, (
                    schema_context,
                    descriptions['description'],
                    descriptions['business_context'],
                    descriptions['sample_questions'],
                    embedding,
                    table_name
                ))
                logger.info(f"Updated table in catalog: {table_name}")
            else:
                cursor.execute(f"""
                    INSERT INTO {self.catalog_table}
                    (table_name, column_definitions, table_description, business_context, 
                     sample_queries, description_embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    table_name,
                    schema_context,
                    descriptions['description'],
                    descriptions['business_context'],
                    descriptions['sample_questions'],
                    embedding
                ))
                logger.info(f"Added table to catalog: {table_name}")
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add/update table {table_name} in catalog: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def sync_all_tables(self, force_update: bool = False):
        """
        Synchronize all tables in the database with the metadata catalog
        
        Args:
            force_update: If True, update all existing entries
        """
        exclude_tables = [self.catalog_table, self.rag_config.documents_table]
        tables = self.db.get_all_tables(exclude_tables=exclude_tables)
        
        logger.info(f"Syncing {len(tables)} tables to metadata catalog")
        
        for i, table in enumerate(tables, 1):
            logger.info(f"Processing table {i}/{len(tables)}: {table}")
            try:
                self.add_table_to_catalog(table, force_update=force_update)
            except Exception as e:
                logger.error(f"Failed to sync table {table}: {str(e)}")
                continue
        
        logger.info("Metadata catalog sync complete")
    
    def discover_relevant_tables(self, user_query: str, max_tables: int = 5) -> List[Dict[str, Any]]:
        """
        Find relevant tables for a user query using vector similarity
        
        Args:
            user_query: Natural language query from user
            max_tables: Maximum number of tables to return
            
        Returns:
            List of dictionaries with table metadata
        """
        # Generate embedding for the query
        query_embedding = self.generate_embedding(user_query)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # First try: Vector similarity search with a reasonable threshold
            cursor.execute(f"""
                SELECT 
                    table_name,
                    table_description,
                    business_context,
                    column_definitions,
                    sample_queries,
                    1 - (description_embedding <=> %s::vector) as similarity
                FROM {self.catalog_table}
                WHERE 1 - (description_embedding <=> %s::vector) > 0.3
                ORDER BY description_embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, query_embedding, max_tables))
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Fallback: If no results from vector search, try keyword matching
            if len(results) == 0:
                logger.info("Vector search returned 0 results, trying keyword matching fallback")
                
                # Extract potential table names from query (simple keyword matching)
                query_lower = user_query.lower()
                cursor.execute(f"""
                    SELECT 
                        table_name,
                        table_description,
                        business_context,
                        column_definitions,
                        sample_queries,
                        0.5 as similarity
                    FROM {self.catalog_table}
                    WHERE 
                        LOWER(table_name) LIKE %s OR
                        LOWER(table_description) LIKE %s OR
                        LOWER(business_context) LIKE %s OR
                        LOWER(column_definitions::text) LIKE %s
                    LIMIT %s
                """, (
                    f'%{query_lower}%',
                    f'%{query_lower}%', 
                    f'%{query_lower}%',
                    f'%{query_lower}%',
                    max_tables
                ))
                
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # If still no results, return all tables (let LLM decide)
                if len(results) == 0:
                    logger.warning("Keyword matching also failed, returning all tables")
                    cursor.execute(f"""
                        SELECT 
                            table_name,
                            table_description,
                            business_context,
                            column_definitions,
                            sample_queries,
                            0.3 as similarity
                        FROM {self.catalog_table}
                        LIMIT %s
                    """, (max_tables,))
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"Found {len(results)} relevant tables for query")
            return results
        finally:
            cursor.close()
    
    def get_table_metadata(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific table"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT table_name, table_description, business_context, 
                       column_definitions, sample_queries
                FROM {self.catalog_table}
                WHERE table_name = %s
            """, (table_name,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
        finally:
            cursor.close()
