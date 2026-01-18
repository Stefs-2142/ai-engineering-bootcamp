"""SQL Agent for querying PostgreSQL product data."""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
from langsmith import traceable, get_current_run_tree


def get_db_connection():
    """Create PostgreSQL connection from environment variables."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "amazon_products"),
        user=os.getenv("POSTGRES_USER", "bootcamp"),
        password=os.getenv("POSTGRES_PASSWORD", "bootcamp"),
    )


SCHEMA_DESCRIPTION = """
Table: products
Columns:
  - asin: VARCHAR(20) PRIMARY KEY - Amazon Standard Identification Number
  - parent_asin: VARCHAR(20) - Parent product ASIN for variations
  - title: TEXT - Product title/name
  - price: DECIMAL(10, 2) - Product price in USD
  - average_rating: DECIMAL(3, 2) - Average customer rating (1.0-5.0)
  - rating_number: INTEGER - Number of customer ratings
  - main_category: VARCHAR(100) - Main product category (e.g., 'Electronics')
  - store: VARCHAR(255) - Store/brand name
  - description: TEXT - Product description
  - features: JSONB - List of product features
  - created_at: TIMESTAMP - Record creation timestamp

Indexes available on: average_rating, price, main_category, rating_number, parent_asin
"""


@traceable(
    name="generate_sql_query",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-5-nano"}
)
def generate_sql_query(question: str) -> str:
    """Generate SQL query from natural language question."""

    prompt = f"""You are a SQL expert. Generate a PostgreSQL query based on the user's question.

{SCHEMA_DESCRIPTION}

Rules:
1. Only generate SELECT queries (no INSERT, UPDATE, DELETE)
2. Always include LIMIT clause (max 50 rows)
3. Return ONLY the SQL query, no explanations
4. Use ILIKE for case-insensitive text matching
5. For product searches, always return parent_asin for linking with vector search

User question: {question}

SQL Query:"""

    response = openai.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        reasoning_effort="minimal"
    )

    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

    sql = response.choices[0].message.content.strip()

    # Clean up markdown code blocks if present
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return sql


@traceable(
    name="execute_sql_query",
    run_type="tool",
    metadata={"tool": "postgresql"}
)
def execute_sql_query(sql: str) -> list[dict]:
    """Execute SQL query and return results as list of dicts."""

    # Security check - only allow SELECT
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
    for word in forbidden:
        if word in sql_upper:
            raise ValueError(f"Forbidden SQL operation: {word}")

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()
            # Convert to regular dicts for JSON serialization
            return [dict(row) for row in results]
    finally:
        conn.close()


@traceable(
    name="format_sql_results",
    run_type="prompt"
)
def format_sql_results(results: list[dict], question: str) -> str:
    """Format SQL results for human-readable response."""

    if not results:
        return "No products found matching your criteria."

    formatted = f"Found {len(results)} product(s):\n\n"

    for i, row in enumerate(results, 1):
        formatted += f"{i}. "
        if "title" in row:
            formatted += f"**{row['title'][:80]}**\n"
        if "price" in row and row["price"]:
            formatted += f"   Price: ${row['price']}\n"
        if "average_rating" in row:
            formatted += f"   Rating: {row['average_rating']}/5"
            if "rating_number" in row:
                formatted += f" ({row['rating_number']} reviews)"
            formatted += "\n"
        if "main_category" in row:
            formatted += f"   Category: {row['main_category']}\n"
        if "parent_asin" in row:
            formatted += f"   ID: {row['parent_asin']}\n"
        formatted += "\n"

    return formatted


@traceable(
    name="generate_sql_answer",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-5-nano"}
)
def generate_sql_answer(question: str, results: list[dict]) -> str:
    """Generate natural language answer from SQL results."""

    prompt = f"""You are a helpful shopping assistant. Based on the database query results,
answer the user's question naturally.

User question: {question}

Query results (JSON):
{json.dumps(results[:10], indent=2, default=str)}

Provide a helpful, conversational answer based on these results. Mention specific products
with their prices and ratings when relevant."""

    response = openai.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="minimal"
    )

    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

    return response.choices[0].message.content


@traceable(name="sql_pipeline")
def sql_pipeline(question: str) -> dict:
    """Execute full SQL pipeline: question -> SQL -> results -> answer."""

    # Generate SQL from natural language
    sql_query = generate_sql_query(question)

    # Execute query
    try:
        results = execute_sql_query(sql_query)
    except Exception as e:
        return {
            "answer": f"Error executing query: {str(e)}",
            "question": question,
            "sql_query": sql_query,
            "results": [],
            "error": str(e)
        }

    # Generate answer
    answer = generate_sql_answer(question, results)

    return {
        "answer": answer,
        "question": question,
        "sql_query": sql_query,
        "results": results,
        "result_count": len(results)
    }


@traceable(name="get_asins_by_filter")
def get_asins_by_filter(
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    category: str | None = None,
    limit: int = 50
) -> list[str]:
    """Get list of parent ASINs matching filter criteria for Qdrant filtering."""

    conditions = []
    params = []

    if min_price is not None:
        conditions.append("price >= %s")
        params.append(min_price)

    if max_price is not None:
        conditions.append("price <= %s")
        params.append(max_price)

    if min_rating is not None:
        conditions.append("average_rating >= %s")
        params.append(min_rating)

    if category is not None:
        conditions.append("main_category ILIKE %s")
        params.append(f"%{category}%")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    sql = f"""
        SELECT DISTINCT parent_asin
        FROM products
        WHERE {where_clause} AND parent_asin IS NOT NULL
        LIMIT %s
    """
    params.append(limit)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
