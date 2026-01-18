"""Router Agent for intent detection and query routing using LangGraph."""

from typing import TypedDict, Literal
from enum import Enum
import openai
from langsmith import traceable, get_current_run_tree
from langgraph.graph import StateGraph, END


class QueryIntent(str, Enum):
    """Types of queries the router can handle."""
    RAG = "rag"           # Semantic search (e.g., "tell me about wireless earbuds")
    SQL = "sql"           # Structured queries (e.g., "how many products are there?")
    HYBRID = "hybrid"     # Combined filter + semantic (e.g., "best headphones under $100")


class QueryFilters(TypedDict, total=False):
    """Extracted filters from user query."""
    min_price: float | None
    max_price: float | None
    min_rating: float | None
    category: str | None
    sort_by: str | None
    limit: int | None


class RouterState(TypedDict):
    """State for the router graph."""
    question: str
    intent: QueryIntent | None
    filters: QueryFilters | None
    semantic_query: str | None
    confidence: float


INTENT_CLASSIFICATION_PROMPT = """You are a query classifier for an Amazon product search system.

Classify the user query into one of these categories:

1. RAG - Pure semantic/conceptual search
   - Looking for products by description or use case
   - Questions about product features or recommendations
   - Examples: "what are good earbuds for running", "tell me about coffee makers"

2. SQL - Pure structured data queries
   - Counting, aggregating, statistics
   - Listing by exact criteria without semantic meaning
   - Examples: "how many products cost over $500", "show all categories"

3. HYBRID - Combination of filters AND semantic search
   - Has both: numeric/categorical filters AND conceptual/descriptive terms
   - Examples: "best headphones under $100", "top rated coffee machines",
              "wireless earbuds with good bass under $50"

User query: {question}

Respond with ONLY one word: RAG, SQL, or HYBRID"""


FILTER_EXTRACTION_PROMPT = """Extract filters from this product search query.

Query: {question}

Return a JSON object with these fields (use null if not mentioned):
{{
    "min_price": number or null,
    "max_price": number or null,
    "min_rating": number or null (e.g., 4.5 for "highly rated"),
    "category": string or null,
    "sort_by": "rating" | "price" | "popularity" | null,
    "limit": number or null,
    "semantic_query": "the conceptual/descriptive part for semantic search"
}}

Examples:
- "best headphones under $100" -> {{"max_price": 100, "semantic_query": "best headphones"}}
- "top rated coffee makers" -> {{"min_rating": 4.0, "sort_by": "rating", "semantic_query": "coffee makers"}}
- "cheap wireless earbuds" -> {{"sort_by": "price", "semantic_query": "cheap wireless earbuds"}}

Only return the JSON, no other text."""


@traceable(
    name="classify_intent",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-5-nano"}
)
def classify_intent(question: str) -> tuple[QueryIntent, float]:
    """Classify user query intent."""

    response = openai.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "user", "content": INTENT_CLASSIFICATION_PROMPT.format(question=question)}
        ],
        reasoning_effort="minimal"
    )

    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

    result = response.choices[0].message.content.strip().upper()

    # Map response to intent
    intent_map = {
        "RAG": QueryIntent.RAG,
        "SQL": QueryIntent.SQL,
        "HYBRID": QueryIntent.HYBRID
    }

    intent = intent_map.get(result, QueryIntent.RAG)
    confidence = 0.9 if result in intent_map else 0.5

    return intent, confidence


@traceable(
    name="extract_filters",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-5-nano"}
)
def extract_filters(question: str) -> tuple[QueryFilters, str]:
    """Extract structured filters and semantic query from user question."""
    import json

    response = openai.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "user", "content": FILTER_EXTRACTION_PROMPT.format(question=question)}
        ],
        reasoning_effort="minimal"
    )

    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

    content = response.choices[0].message.content.strip()

    # Clean up markdown if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        parsed = json.loads(content)
        semantic_query = parsed.pop("semantic_query", question)
        filters: QueryFilters = {
            "min_price": parsed.get("min_price"),
            "max_price": parsed.get("max_price"),
            "min_rating": parsed.get("min_rating"),
            "category": parsed.get("category"),
            "sort_by": parsed.get("sort_by"),
            "limit": parsed.get("limit"),
        }
        return filters, semantic_query
    except json.JSONDecodeError:
        return {}, question


def classify_node(state: RouterState) -> RouterState:
    """Node: Classify the intent of the query."""
    intent, confidence = classify_intent(state["question"])
    return {
        **state,
        "intent": intent,
        "confidence": confidence
    }


def extract_filters_node(state: RouterState) -> RouterState:
    """Node: Extract filters for hybrid queries."""
    filters, semantic_query = extract_filters(state["question"])
    return {
        **state,
        "filters": filters,
        "semantic_query": semantic_query
    }


def should_extract_filters(state: RouterState) -> Literal["extract", "done"]:
    """Edge: Decide if we need to extract filters."""
    if state["intent"] == QueryIntent.HYBRID:
        return "extract"
    return "done"


def build_router_graph() -> StateGraph:
    """Build the LangGraph router workflow."""

    workflow = StateGraph(RouterState)

    # Add nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("extract_filters", extract_filters_node)

    # Set entry point
    workflow.set_entry_point("classify")

    # Add conditional edge
    workflow.add_conditional_edges(
        "classify",
        should_extract_filters,
        {
            "extract": "extract_filters",
            "done": END
        }
    )

    workflow.add_edge("extract_filters", END)

    return workflow.compile()


# Compiled router graph
_router_graph = None


def get_router() -> StateGraph:
    """Get or create the compiled router graph."""
    global _router_graph
    if _router_graph is None:
        _router_graph = build_router_graph()
    return _router_graph


@traceable(name="route_query")
def route_query(question: str) -> RouterState:
    """Route a user query through the intent classification pipeline."""

    router = get_router()

    initial_state: RouterState = {
        "question": question,
        "intent": None,
        "filters": None,
        "semantic_query": None,
        "confidence": 0.0
    }

    result = router.invoke(initial_state)
    return result
