# The Vector Search Function
# This function uses the <-> (L2 distance) or <=> (cosine distance) operator provided by pgvector.

import psycopg2
from openai import OpenAI

client = OpenAI()

def vector_search_docs(query_text):
    # 1. Create embedding for the user's search
    xq = client.embeddings.create(input=query_text, model="text-embedding-3-small").data[0].embedding
    
    # 2. Query PostgreSQL using the <=> cosine similarity operator
    conn = psycopg2.connect("postgresql://user:pass@localhost:5432/corp_db")
    cur = conn.cursor()
    cur.execute("""
        SELECT content FROM company_documents 
        ORDER BY embedding <=> %s::vector 
        LIMIT 3
    """, (xq,))
    
    results = cur.fetchall()
    return "\n".join([r[0] for r in results])

# The SQL Execution Function
# This function allows the agent to run analytical queries against your structured tables.

def sql_query_analytics(sql_query):
    conn = psycopg2.connect("postgresql://user:pass@localhost:5432/corp_db")
    cur = conn.cursor()
    try:
        cur.execute(sql_query)
        return str(cur.fetchall())
    except Exception as e:
        return f"Error: {str(e)}"
    
# 3. The Agent (The "Router")
# We define these functions as "Tools" that the OpenAI model can call. This is the Agentic part: the model looks at the user's question and decides which function to trigger.

tools = [
    {
        "type": "function",
        "function": {
            "name": "vector_search_docs",
            "description": "Search for company policies, handbooks, and text-based rules.",
            "parameters": {
                "type": "object",
                "properties": {"query_text": {"type": "string"}},
                "required": ["query_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sql_query_analytics",
            "description": "Run SQL on tables 'sales' (cols: id, amount, date) and 'inventory'.",
            "parameters": {
                "type": "object",
                "properties": {"sql_query": {"type": "string"}},
                "required": ["sql_query"]
            }
        }
    }
]

# User Question
messages = [{"role": "user", "content": "What was our total sales yesterday, and what is the refund policy?"}]

# Agent makes a decision
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
    tool_choice="auto"
)


# 2. Automating the Catalog (Python)
# This script "crawls" your database, asks an LLM to explain what each table does, and saves that into your table_metadata_catalog. This is the "brain" initialization.

import psycopg2
from openai import OpenAI

client = OpenAI()

def sync_metadata_catalog(conn):
    cursor = conn.cursor()
    
    # 1. Get all user-defined tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name != 'table_metadata_catalog';
    """)
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        # 2. Get column names for context
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
        cols = [row[0] for row in cursor.fetchall()]
        
        # 3. LLM generates a searchable description
        prompt = f"Explain the purpose of the table '{table}' with columns {cols}. Focus on what business questions it can answer."
        description = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content

        # 4. Vectorize the description
        embedding = client.embeddings.create(
            input=description, model="text-embedding-3-small"
        ).data[0].embedding

        # 5. Save to Postgres
        cursor.execute("""
            INSERT INTO table_metadata_catalog (table_name, column_definitions, table_description, description_embedding)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (table_name) DO UPDATE 
            SET table_description = EXCLUDED.table_description, description_embedding = EXCLUDED.description_embedding;
        """, (table, str(cols), description, embedding))
    
    conn.commit()