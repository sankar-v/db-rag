"""
SQL Agent - Handles table discovery and SQL query generation
"""
import logging
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI

from database import DatabaseManager
from metadata_catalog import MetadataCatalogManager
from config import LLMConfig, RAGConfig


logger = logging.getLogger(__name__)


class SQLAgent:
    """Agent for discovering tables and generating SQL queries"""
    
    def __init__(
        self, 
        db_manager: DatabaseManager,
        metadata_manager: MetadataCatalogManager,
        llm_config: LLMConfig,
        rag_config: RAGConfig
    ):
        self.db = db_manager
        self.metadata = metadata_manager
        self.llm_config = llm_config
        self.rag_config = rag_config
        self.client = OpenAI(api_key=llm_config.api_key)
    
    def discover_tables(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Discover relevant tables for a user query
        
        Args:
            user_query: Natural language query
            
        Returns:
            List of relevant table metadata
        """
        logger.info(f"Discovering tables for query: {user_query}")
        return self.metadata.discover_relevant_tables(
            user_query, 
            max_tables=self.rag_config.max_context_tables
        )
    
    def generate_sql(
        self, 
        user_query: str, 
        relevant_tables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate SQL query from natural language using LLM
        
        Args:
            user_query: Natural language query
            relevant_tables: List of relevant table metadata
            
        Returns:
            Dictionary with generated SQL and explanation
        """
        # Build context from relevant tables
        context = self._build_table_context(relevant_tables)
        
        # Build the prompt
        prompt = self._build_sql_generation_prompt(user_query, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert PostgreSQL query generator. 
Generate precise, efficient SQL queries based on the provided schema and user question.
Always return valid PostgreSQL syntax. Use appropriate JOINs, WHERE clauses, and aggregations.
Return your response in JSON format with keys: 'sql', 'explanation', 'tables_used'."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens
            )
            
            content = response.choices[0].message.content
            
            # Clean up content - remove markdown json code blocks
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]  # Remove ```json
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]  # Remove ```
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]  # Remove trailing ```
            cleaned_content = cleaned_content.strip()
            
            # Try to parse as JSON
            try:
                result = json.loads(cleaned_content)
                if "sql" in result:
                    logger.info("Generated SQL query successfully")
                    return result
            except json.JSONDecodeError:
                pass
            
            # If not JSON, try to extract SQL from markdown code blocks
            sql_query = self._extract_sql_from_response(content)
            
            return {
                "sql": sql_query,
                "explanation": "Generated SQL query based on provided schema",
                "tables_used": [t["table_name"] for t in relevant_tables]
            }
        except Exception as e:
            logger.error(f"Failed to generate SQL: {str(e)}")
            raise
    
    def _build_table_context(self, tables: List[Dict[str, Any]]) -> str:
        """Build context string from table metadata"""
        context = "Available Tables:\n\n"
        
        for table in tables:
            context += f"Table: {table['table_name']}\n"
            context += f"Description: {table['table_description']}\n"
            context += f"Business Context: {table['business_context']}\n"
            context += f"Schema:\n{table['column_definitions']}\n"
            
            if table.get('sample_queries'):
                context += f"Example Questions:\n"
                for q in table['sample_queries']:
                    context += f"  - {q}\n"
            
            context += "\n"
        
        return context
    
    def _build_sql_generation_prompt(self, user_query: str, context: str) -> str:
        """Build the complete prompt for SQL generation"""
        prompt = f"""{context}

USER QUESTION: {user_query}

Generate a PostgreSQL query to answer this question. Follow these rules:
1. Only use tables and columns defined in the schema above
2. Use proper JOINs when querying multiple tables
3. Use appropriate WHERE clauses for filtering
4. Use aggregations (SUM, COUNT, AVG, etc.) when appropriate
5. Return only valid PostgreSQL syntax
6. If the question is ambiguous, make reasonable assumptions
7. Add LIMIT clauses for queries that might return many rows

Return your response as a JSON object with these keys:
- sql: The complete SQL query (string)
- explanation: Brief explanation of what the query does (string)
- tables_used: List of table names used in the query (array)

Example response format:
{{
  "sql": "SELECT column FROM table WHERE condition;",
  "explanation": "This query retrieves...",
  "tables_used": ["table_name"]
}}
"""
        return prompt
    
    def _extract_sql_from_response(self, response: str) -> str:
        """Extract SQL from response if it's in markdown code blocks"""
        # Look for SQL code blocks
        if "```sql" in response:
            start = response.find("```sql") + 6
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()
        
        # Otherwise return as-is
        return response.strip()
    
    def validate_and_execute(
        self, 
        sql_query: str, 
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """
        Validate and optionally execute SQL query
        
        Args:
            sql_query: SQL query to validate/execute
            validate_only: If True, only validate without executing
            
        Returns:
            Dictionary with validation results and query results if executed
        """
        # First validate
        is_valid, error = self.db.validate_query(sql_query)
        
        if not is_valid:
            logger.warning(f"SQL validation failed: {error}")
            return {
                "valid": False,
                "error": error,
                "results": None
            }
        
        if validate_only:
            return {
                "valid": True,
                "error": None,
                "results": None
            }
        
        # Execute the query
        try:
            results = self.db.execute_query(sql_query)
            logger.info(f"Query executed successfully, returned {len(results)} rows")
            
            return {
                "valid": True,
                "error": None,
                "results": results,
                "row_count": len(results)
            }
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
                "results": None
            }
    
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Complete workflow: discover tables, generate SQL, execute
        
        Args:
            user_query: Natural language question
            
        Returns:
            Dictionary with SQL, results, and metadata
        """
        logger.info(f"Processing SQL query: {user_query}")
        
        # Step 1: Discover relevant tables
        relevant_tables = self.discover_tables(user_query)
        
        if not relevant_tables:
            logger.warning("No relevant tables found for query")
            return {
                "success": False,
                "error": "No relevant tables found for this query",
                "query": user_query
            }
        
        logger.info(f"Found {len(relevant_tables)} relevant tables: {[t['table_name'] for t in relevant_tables]}")
        
        # Step 2: Generate SQL
        try:
            sql_result = self.generate_sql(user_query, relevant_tables)
            sql_query = sql_result["sql"]
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate SQL: {str(e)}",
                "query": user_query
            }
        
        # Step 3: Validate and execute
        if self.rag_config.enable_query_validation:
            execution_result = self.validate_and_execute(sql_query)
        else:
            try:
                results = self.db.execute_query(sql_query)
                execution_result = {
                    "valid": True,
                    "error": None,
                    "results": results,
                    "row_count": len(results)
                }
            except Exception as e:
                execution_result = {
                    "valid": False,
                    "error": str(e),
                    "results": None
                }
        
        # Step 4: Return complete result
        return {
            "success": execution_result["valid"],
            "query": user_query,
            "sql": sql_query,
            "explanation": sql_result.get("explanation"),
            "tables_used": sql_result.get("tables_used", []),
            "results": execution_result.get("results"),
            "row_count": execution_result.get("row_count", 0),
            "error": execution_result.get("error")
        }
