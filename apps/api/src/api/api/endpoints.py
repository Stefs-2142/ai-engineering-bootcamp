from fastapi import Request, APIRouter
from api.api.models import (
    RAGRequest, RAGResponse,
    ChatRequest, ChatResponse,
    SQLRequest, SQLResponse
)

from qdrant_client import QdrantClient
from api.agents.retrieval_generation import rag_pipeline
from api.agents.sql_agent import sql_pipeline
from api.agents.hybrid import hybrid_pipeline
from api.agents.router import route_query, QueryIntent

import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

qdrant_client = QdrantClient(url="http://qdrant:6333")

# RAG Router (original)
rag_router = APIRouter()


@rag_router.post("/")
def rag(
    request: Request,
    payload: RAGRequest
) -> RAGResponse:

    answer = rag_pipeline(payload.query, qdrant_client)

    return RAGResponse(
        request_id=request.state.request_id,
        answer=answer["answer"]
    )


# SQL Router
sql_router = APIRouter()


@sql_router.post("/")
def sql(
    request: Request,
    payload: SQLRequest
) -> SQLResponse:
    """Execute SQL-based product query."""

    result = sql_pipeline(payload.query)

    return SQLResponse(
        request_id=request.state.request_id,
        answer=result["answer"],
        sql_query=result.get("sql_query", ""),
        result_count=result.get("result_count", 0)
    )


# Chat Router (Smart - auto-routes)
chat_router = APIRouter()


@chat_router.post("/")
def chat(
    request: Request,
    payload: ChatRequest
) -> ChatResponse:
    """Smart chat endpoint - automatically routes to RAG, SQL, or Hybrid pipeline."""

    # Route the query
    route_result = route_query(payload.query)
    intent = route_result["intent"]

    logger.info(f"Query '{payload.query[:50]}...' routed to: {intent}")

    # Execute appropriate pipeline
    if intent == QueryIntent.SQL:
        result = sql_pipeline(payload.query)
        return ChatResponse(
            request_id=request.state.request_id,
            answer=result["answer"],
            intent="sql",
            filters=None
        )

    elif intent == QueryIntent.HYBRID:
        result = hybrid_pipeline(
            question=payload.query,
            qdrant_client=qdrant_client,
            filters=route_result.get("filters"),
            semantic_query=route_result.get("semantic_query")
        )
        return ChatResponse(
            request_id=request.state.request_id,
            answer=result["answer"],
            intent="hybrid",
            filters=result.get("filters")
        )

    else:  # RAG (default)
        result = rag_pipeline(payload.query, qdrant_client)
        return ChatResponse(
            request_id=request.state.request_id,
            answer=result["answer"],
            intent="rag",
            filters=None
        )


# Combine all routers
api_router = APIRouter()
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(sql_router, prefix="/sql", tags=["sql"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])