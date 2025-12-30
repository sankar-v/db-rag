"""
Orchestrator Agent - Routes queries to appropriate agents and synthesizes responses
"""
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

from database import DatabaseManager
from metadata_catalog import MetadataCatalogManager
from sql_agent import SQLAgent
from vector_agent import VectorSearchAgent
from config import LLMConfig, RAGConfig


logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Main orchestrator that routes queries to SQL or Vector agents
    and synthesizes final responses
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm_config: LLMConfig,
        rag_config: RAGConfig
    ):
        self.db = db_manager
        self.llm_config = llm_config
        self.rag_config = rag_config
        self.client = OpenAI(api_key=llm_config.api_key)
        
        # Initialize metadata manager
        self.metadata_manager = MetadataCatalogManager(db_manager, llm_config, rag_config)
        
        # Initialize specialized agents
        self.sql_agent = SQLAgent(db_manager, self.metadata_manager, llm_config, rag_config)
        self.vector_agent = VectorSearchAgent(db_manager, llm_config, rag_config)
        
        # Agent tool definitions for LLM routing
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "query_structured_data",
                    "description": """Query structured data in database tables using SQL. 
Use this for analytical queries, aggregations, filtering, joining tables, 
or any questions about quantitative data (sales, counts, sums, averages, etc.).
Examples: revenue calculations, user counts, inventory levels, transaction history.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The user's natural language question about structured data"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_unstructured_documents",
                    "description": """Search unstructured text documents using semantic similarity.
Use this for questions about policies, handbooks, procedures, guidelines, 
documentation, or any text-based information.
Examples: company policies, employee handbooks, refund procedures, legal documents.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The user's search query for unstructured documents"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def initialize(self):
        """Initialize all necessary database tables and structures"""
        logger.info("Initializing DB-RAG system...")
        
        # Initialize metadata catalog
        self.metadata_manager.initialize_catalog_table()
        
        # Initialize documents table
        self.vector_agent.initialize_documents_table()
        
        # Sync metadata catalog if auto-sync is enabled
        if self.rag_config.enable_auto_metadata_sync:
            logger.info("Auto-syncing metadata catalog...")
            self.metadata_manager.sync_all_tables()
        
        logger.info("DB-RAG system initialized successfully")
    
    def route_query(self, user_query: str) -> Dict[str, Any]:
        """
        Route user query to appropriate agent(s) using LLM
        
        Args:
            user_query: Natural language question from user
            
        Returns:
            Routing decision with agent and parameters
        """
        logger.info(f"Routing query: {user_query}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a query router. Analyze the user's question and determine 
which tool to use. Choose 'query_structured_data' for analytical/quantitative questions about 
database tables, and 'search_unstructured_documents' for questions about policies, procedures, 
or text documents. You can call both if the question requires both types of information."""
                    },
                    {"role": "user", "content": user_query}
                ],
                tools=self.tools,
                tool_choice="auto",
                temperature=0.0
            )
            
            message = response.choices[0].message
            
            # Check if tools were called
            if message.tool_calls:
                routing_decisions = []
                for tool_call in message.tool_calls:
                    import json
                    routing_decisions.append({
                        "agent": tool_call.function.name,
                        "parameters": json.loads(tool_call.function.arguments),
                        "tool_call_id": tool_call.id
                    })
                
                logger.info(f"Routed to agents: {[d['agent'] for d in routing_decisions]}")
                return {
                    "success": True,
                    "routing_decisions": routing_decisions,
                    "requires_both": len(routing_decisions) > 1
                }
            else:
                # No tool calls, might be a conversational response
                return {
                    "success": False,
                    "error": "Unable to route query to specific agent",
                    "message": message.content
                }
        except Exception as e:
            logger.error(f"Query routing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_agent_calls(self, routing_decisions: list) -> Dict[str, Any]:
        """
        Execute calls to routed agents
        
        Args:
            routing_decisions: List of routing decisions from route_query
            
        Returns:
            Combined results from all agents
        """
        results = {
            "sql_results": None,
            "vector_results": None
        }
        
        for decision in routing_decisions:
            agent_name = decision["agent"]
            params = decision["parameters"]
            query = params.get("query")
            
            if agent_name == "query_structured_data" and self.rag_config.enable_sql_search:
                logger.info("Executing SQL agent")
                results["sql_results"] = self.sql_agent.query(query)
            
            elif agent_name == "search_unstructured_documents" and self.rag_config.enable_vector_search:
                logger.info("Executing vector search agent")
                results["vector_results"] = self.vector_agent.query(query)
        
        return results
    
    def synthesize_response(
        self,
        user_query: str,
        agent_results: Dict[str, Any]
    ) -> str:
        """
        Synthesize final response from agent results
        
        Args:
            user_query: Original user question
            agent_results: Results from executed agents
            
        Returns:
            Natural language response
        """
        # Build context from agent results
        context_parts = []
        
        if agent_results.get("sql_results") and agent_results["sql_results"].get("success"):
            sql_data = agent_results["sql_results"]
            context_parts.append(f"SQL Query Results:")
            context_parts.append(f"Query: {sql_data['sql']}")
            context_parts.append(f"Tables used: {', '.join(sql_data.get('tables_used', []))}")
            context_parts.append(f"Results: {sql_data.get('results', [])}")
        
        if agent_results.get("vector_results") and agent_results["vector_results"].get("success"):
            vector_data = agent_results["vector_results"]
            context_parts.append(f"\nDocument Search Results:")
            for i, doc in enumerate(vector_data.get("documents", []), 1):
                context_parts.append(f"\nDocument {i} (similarity: {doc['similarity']:.3f}):")
                context_parts.append(doc["content"])
        
        context = "\n".join(context_parts)
        
        # Generate final response
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful assistant that answers questions based on 
provided data. Synthesize information from database query results and document searches 
into a clear, accurate response. If data is missing or unclear, say so. 
Be concise but complete."""
                    },
                    {
                        "role": "user",
                        "content": f"""Question: {user_query}

Available Information:
{context}

Please provide a comprehensive answer to the question based on this information."""
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Response synthesis failed: {str(e)}")
            return f"I found the following information but encountered an error synthesizing the response: {context}"
    
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Complete end-to-end query processing
        
        Args:
            user_query: Natural language question from user
            
        Returns:
            Complete response with answer and metadata
        """
        logger.info(f"Processing query: {user_query}")
        
        # Step 1: Route query
        routing_result = self.route_query(user_query)
        
        if not routing_result.get("success"):
            return {
                "success": False,
                "query": user_query,
                "error": routing_result.get("error"),
                "answer": routing_result.get("message", "Unable to process query")
            }
        
        # Step 2: Execute agent calls
        agent_results = self.execute_agent_calls(routing_result["routing_decisions"])
        
        # Step 3: Synthesize response
        final_answer = self.synthesize_response(user_query, agent_results)
        
        # Step 4: Return complete result
        return {
            "success": True,
            "query": user_query,
            "answer": final_answer,
            "routing": routing_result["routing_decisions"],
            "sql_results": agent_results.get("sql_results"),
            "vector_results": agent_results.get("vector_results")
        }
    
    def close(self):
        """Clean up resources"""
        self.db.close()
        logger.info("Orchestrator closed")
