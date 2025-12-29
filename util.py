import psycopg2
from openai import OpenAI

client = OpenAI()

def execute_hybrid_query(user_prompt):
    # 1. Define the tools for the Agent
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_pgvector_unstructured",
                "description": "Search for semantic concepts like policies, text, or handbooks.",
                "parameters": {
                    "type": "object",
                    "properties": {"search_text": {"type": "string"}},
                    "required": ["search_text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_postgresql_structured",
                "description": "Run analytical SQL queries on tables: sales, users, or products.",
                "parameters": {
                    "type": "object",
                    "properties": {"sql_query": {"type": "string"}},
                    "required": ["sql_query"]
                }
            }
        }
    ]

    # 2. First call: The Agent decides which tool to use
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_prompt}],
        tools=tools
    )

    # 3. Logic to execute the chosen tool
    # (If the Agent chose SQL, it writes the query; if Vector, it writes search text)
    # The final step is taking that data and answering the user.
    return response.choices[0].message


from sqlalchemy import inspect

def get_table_context(engine, table_name):
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    pk = inspector.get_pk_constraint(table_name)
    
    # Build a concise string representation
    col_details = [f"- {c['name']} ({c['type']})" for c in columns]
    pk_details = f"Primary Key: {pk['constrained_columns']}"
    
    context = f"Table: {table_name}\n"
    context += "\n".join(col_details)
    context += f"\n{pk_details}"
    
    return context

# The Dynamic Prompt Builder
# This is where you combine the Table Schema, Few-Shot Examples, and the User Question.

def generate_sql_prompt(user_question, table_name, engine):
    # 1. Get the real-time schema context
    schema_context = get_table_context(engine, table_name)
    
    # 2. Construct the full prompt
    prompt = f"""
    You are a PostgreSQL expert. Given the schema below, write a valid SQL query.
    
    {schema_context}
    
    Rules:
    - Only use columns listed above.
    - Return ONLY the SQL code, no explanation.
    - If the question involves 'revenue', use the 'amount' column.
    
    Examples:
    User: "What's the total for Enterprise?"
    SQL: SELECT SUM(amount) FROM {table_name} WHERE sector = 'Enterprise';
    
    Question: {user_question}
    SQL:
    """
    return prompt
