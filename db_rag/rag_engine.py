"""
RAG Engine for querying both structured (database) and unstructured (documents) data.
"""

from typing import List, Dict, Any, Optional
import logging

from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document

from .config import Config
from .db_connector import DatabaseConnector
from .document_loader import DocumentLoader
from .vector_store import VectorStoreManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Unified RAG engine that queries both structured database data 
    and unstructured document data.
    """
    
    def __init__(self, config: Config):
        """
        Initialize RAG engine.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db_connector = DatabaseConnector(config)
        self.document_loader = DocumentLoader(config)
        self.vector_store = VectorStoreManager(config)
        self.llm = ChatOpenAI(
            model=config.llm_model,
            openai_api_key=config.openai_api_key,
            temperature=0
        )
        
        # Initialize database schema context
        self.db_schema = self.db_connector.get_database_schema_text()
    
    def ingest_documents(self, source: str, source_type: str = "auto") -> None:
        """
        Ingest documents into the vector store.
        
        Args:
            source: Path to file or directory
            source_type: Type of source ('file', 'directory', 'auto')
        """
        import os
        
        if source_type == "auto":
            source_type = "directory" if os.path.isdir(source) else "file"
        
        try:
            if source_type == "file":
                documents = self.document_loader.load_file(source)
            elif source_type == "directory":
                documents = self.document_loader.load_directory(source)
            else:
                raise ValueError(f"Invalid source_type: {source_type}")
            
            self.vector_store.add_documents(documents)
            logger.info(f"Successfully ingested documents from {source}")
        except Exception as e:
            logger.error(f"Failed to ingest documents: {e}")
            raise
    
    def ingest_database_schema(self) -> None:
        """
        Ingest database schema as documents for semantic search.
        This allows queries about database structure.
        """
        try:
            schema_doc = Document(
                page_content=self.db_schema,
                metadata={"source": "database_schema", "type": "schema"}
            )
            self.vector_store.add_documents([schema_doc])
            logger.info("Successfully ingested database schema")
        except Exception as e:
            logger.error(f"Failed to ingest database schema: {e}")
            raise
    
    def query_database(self, natural_language_query: str) -> Dict[str, Any]:
        """
        Query the database using natural language.
        Converts natural language to SQL and executes it.
        
        Args:
            natural_language_query: User's question in natural language
            
        Returns:
            Dictionary with SQL query and results
        """
        # Create prompt for SQL generation
        sql_prompt = PromptTemplate(
            input_variables=["schema", "question"],
            template="""Given the following database schema:

{schema}

Generate a SQL query to answer this question: {question}

Important:
- Only generate the SQL query, nothing else
- Use proper SQL syntax
- Only query existing tables and columns from the schema
- Use appropriate WHERE clauses and JOINs if needed

SQL Query:"""
        )
        
        try:
            # Generate SQL query
            chain = LLMChain(llm=self.llm, prompt=sql_prompt)
            sql_query = chain.run(schema=self.db_schema, question=natural_language_query)
            sql_query = sql_query.strip()
            
            # Remove markdown code blocks if present
            if sql_query.startswith("```"):
                parts = sql_query.split("```")
                if len(parts) >= 2:
                    sql_query = parts[1]
                    if sql_query.startswith("sql"):
                        sql_query = sql_query[3:]
                    sql_query = sql_query.strip()
                else:
                    # If split didn't work as expected, just remove the backticks
                    sql_query = sql_query.replace("```", "").strip()
            
            logger.info(f"Generated SQL: {sql_query}")
            
            # Execute query
            results = self.db_connector.execute_query(sql_query)
            
            return {
                "sql_query": sql_query,
                "results": results,
                "source": "database"
            }
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return {
                "error": str(e),
                "source": "database"
            }
    
    def query_documents(self, query: str, k: Optional[int] = None) -> Dict[str, Any]:
        """
        Query unstructured documents using semantic search.
        
        Args:
            query: User's question
            k: Number of results to return
            
        Returns:
            Dictionary with relevant documents
        """
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            return {
                "documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score
                    }
                    for doc, score in results
                ],
                "source": "documents"
            }
        except Exception as e:
            logger.error(f"Document query failed: {e}")
            return {
                "error": str(e),
                "source": "documents"
            }
    
    def query(self, question: str, search_db: bool = True, search_docs: bool = True) -> Dict[str, Any]:
        """
        Query both structured and unstructured data sources.
        
        Args:
            question: User's question in natural language
            search_db: Whether to search database
            search_docs: Whether to search documents
            
        Returns:
            Dictionary with combined results and generated answer
        """
        results = {
            "question": question,
            "database_results": None,
            "document_results": None,
            "answer": None
        }
        
        # Collect context from both sources
        context_parts = []
        
        # Query database if enabled
        if search_db:
            try:
                db_results = self.query_database(question)
                results["database_results"] = db_results
                
                if "results" in db_results and db_results["results"]:
                    context_parts.append(f"Database Results:\n{self._format_db_results(db_results['results'])}")
            except Exception as e:
                logger.warning(f"Database query failed: {e}")
        
        # Query documents if enabled
        if search_docs:
            try:
                doc_results = self.query_documents(question)
                results["document_results"] = doc_results
                
                if "documents" in doc_results and doc_results["documents"]:
                    doc_context = "\n\n".join([
                        f"Document {i+1}:\n{doc['content']}"
                        for i, doc in enumerate(doc_results["documents"])
                    ])
                    context_parts.append(f"Relevant Documents:\n{doc_context}")
            except Exception as e:
                logger.warning(f"Document query failed: {e}")
        
        # Generate final answer using LLM
        if context_parts:
            answer_prompt = PromptTemplate(
                input_variables=["context", "question"],
                template="""Based on the following context, answer the question.

Context:
{context}

Question: {question}

Answer (be specific and cite sources when possible):"""
            )
            
            try:
                chain = LLMChain(llm=self.llm, prompt=answer_prompt)
                context = "\n\n".join(context_parts)
                answer = chain.run(context=context, question=question)
                results["answer"] = answer.strip()
            except Exception as e:
                logger.error(f"Answer generation failed: {e}")
                results["answer"] = "Failed to generate answer"
        else:
            results["answer"] = "No relevant information found in database or documents."
        
        return results
    
    def _format_db_results(self, results: List[Dict[str, Any]]) -> str:
        """Format database results as text."""
        if not results:
            return "No results found"
        
        formatted = []
        for i, row in enumerate(results, 1):
            row_str = f"Row {i}: " + ", ".join([f"{k}={v}" for k, v in row.items()])
            formatted.append(row_str)
        
        return "\n".join(formatted)
    
    def close(self) -> None:
        """Clean up resources."""
        self.db_connector.close()
        logger.info("RAG Engine closed")
