"""Hybrid Pipeline: SQL filtering -> RAG semantic search."""

import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
from langsmith import traceable, get_current_run_tree

from api.agents.sql_agent import get_asins_by_filter
from api.agents.router import route_query, QueryIntent, QueryFilters
from api.agents.retrieval_generation import get_embedding


@traceable(
    name="hybrid_retrieve",
    run_type="retriever"
)
def hybrid_retrieve(
    semantic_query: str,
    filters: QueryFilters,
    qdrant_client: QdrantClient,
    k: int = 10
) -> dict:
    """Retrieve products using SQL filter + Qdrant semantic search.

    1. Apply SQL filters to get candidate ASINs
    2. Use Qdrant to search only within those ASINs
    3. Return enriched results
    """

    # Step 1: Get ASINs matching the filters from PostgreSQL
    filtered_asins = get_asins_by_filter(
        min_price=filters.get("min_price"),
        max_price=filters.get("max_price"),
        min_rating=filters.get("min_rating"),
        category=filters.get("category"),
        limit=100  # Get more candidates for semantic filtering
    )

    if not filtered_asins:
        return {
            "retrieved_context_ids": [],
            "retrieved_context": [],
            "retrieved_context_ratings": [],
            "similarity_scores": [],
            "filter_count": 0
        }

    # Step 2: Embed the semantic query
    query_embedding = get_embedding(semantic_query)

    # Step 3: Search Qdrant with ASIN filter
    qdrant_filter = Filter(
        must=[
            FieldCondition(
                key="parent_asin",
                match=MatchAny(any=filtered_asins)
            )
        ]
    )

    results = qdrant_client.query_points(
        collection_name="Amazon-items-collection-00",
        query=query_embedding,
        query_filter=qdrant_filter,
        limit=k,
    )

    # Step 4: Extract results
    retrieved_context_ids = []
    retrieved_context = []
    similarity_scores = []
    retrieved_context_ratings = []

    for result in results.points:
        retrieved_context_ids.append(result.payload["parent_asin"])
        retrieved_context.append(result.payload["description"])
        retrieved_context_ratings.append(result.payload["average_rating"])
        similarity_scores.append(result.score)

    return {
        "retrieved_context_ids": retrieved_context_ids,
        "retrieved_context": retrieved_context,
        "retrieved_context_ratings": retrieved_context_ratings,
        "similarity_scores": similarity_scores,
        "filter_count": len(filtered_asins)
    }


@traceable(
    name="format_hybrid_context",
    run_type="prompt"
)
def format_hybrid_context(context: dict, filters: QueryFilters) -> str:
    """Format hybrid retrieval context with filter information."""

    formatted = f"(Filtered from {context['filter_count']} products"
    if filters.get("max_price"):
        formatted += f", max price: ${filters['max_price']}"
    if filters.get("min_rating"):
        formatted += f", min rating: {filters['min_rating']}"
    if filters.get("category"):
        formatted += f", category: {filters['category']}"
    formatted += ")\n\n"

    for id, chunk, rating, score in zip(
        context["retrieved_context_ids"],
        context["retrieved_context"],
        context["retrieved_context_ratings"],
        context["similarity_scores"]
    ):
        formatted += f"- ID: {id}, rating: {rating}, relevance: {score:.2f}\n"
        formatted += f"  Description: {chunk}\n\n"

    return formatted


@traceable(
    name="build_hybrid_prompt",
    run_type="prompt"
)
def build_hybrid_prompt(formatted_context: str, question: str, filters: QueryFilters) -> str:
    """Build prompt for hybrid query response."""

    filter_summary = []
    if filters.get("min_price") or filters.get("max_price"):
        price_range = ""
        if filters.get("min_price"):
            price_range += f"from ${filters['min_price']}"
        if filters.get("max_price"):
            price_range += f" up to ${filters['max_price']}"
        filter_summary.append(f"Price: {price_range.strip()}")
    if filters.get("min_rating"):
        filter_summary.append(f"Rating: {filters['min_rating']}+ stars")
    if filters.get("category"):
        filter_summary.append(f"Category: {filters['category']}")

    prompt = f"""You are a shopping assistant helping customers find products.

The user is looking for products with these criteria:
{chr(10).join(filter_summary) if filter_summary else "No specific filters"}

Here are the matching products from our catalog:

{formatted_context}

User question: {question}

Instructions:
- Recommend the best matching products based on both the filters and the user's needs
- Mention specific prices and ratings when available
- If the results are limited, acknowledge the filtering criteria
- Be helpful and conversational"""

    return prompt


@traceable(
    name="hybrid_generate",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-5-nano"}
)
def hybrid_generate(prompt: str) -> str:
    """Generate response for hybrid query."""

    response = openai.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "system", "content": prompt}],
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


@traceable(name="hybrid_pipeline")
def hybrid_pipeline(
    question: str,
    qdrant_client: QdrantClient,
    filters: QueryFilters | None = None,
    semantic_query: str | None = None,
    top_k: int = 5
) -> dict:
    """Execute hybrid pipeline: SQL filter -> Qdrant search -> LLM generation.

    Args:
        question: Original user question
        qdrant_client: Qdrant client instance
        filters: Pre-extracted filters (or will extract from question)
        semantic_query: Pre-extracted semantic part (or will use question)
        top_k: Number of results to retrieve
    """

    # If filters not provided, extract them
    if filters is None:
        route_result = route_query(question)
        filters = route_result.get("filters", {})
        semantic_query = route_result.get("semantic_query", question)

    if semantic_query is None:
        semantic_query = question

    # Retrieve with hybrid approach
    retrieved_context = hybrid_retrieve(
        semantic_query=semantic_query,
        filters=filters,
        qdrant_client=qdrant_client,
        k=top_k
    )

    # Format context
    formatted_context = format_hybrid_context(retrieved_context, filters)

    # Build prompt
    prompt = build_hybrid_prompt(formatted_context, question, filters)

    # Generate answer
    answer = hybrid_generate(prompt)

    return {
        "answer": answer,
        "question": question,
        "intent": "hybrid",
        "filters": filters,
        "semantic_query": semantic_query,
        "retrieved_context_ids": retrieved_context["retrieved_context_ids"],
        "retrieved_context": retrieved_context["retrieved_context"],
        "similarity_scores": retrieved_context["similarity_scores"],
        "filter_count": retrieved_context["filter_count"]
    }
