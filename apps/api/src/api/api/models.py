from pydantic import BaseModel, Field
from typing import Literal


class RAGRequest(BaseModel):
    query: str = Field(..., description="The query to be used in the RAG pipeline")


class RAGResponse(BaseModel):
    request_id: str = Field(..., description="The request ID")
    answer: str = Field(..., description="The answer to the query")


class ChatRequest(BaseModel):
    """Smart chat request - automatically routes to appropriate pipeline."""
    query: str = Field(..., description="The user query")


class ChatResponse(BaseModel):
    """Smart chat response with routing information."""
    request_id: str = Field(..., description="The request ID")
    answer: str = Field(..., description="The answer to the query")
    intent: Literal["rag", "sql", "hybrid"] = Field(..., description="Detected query intent")
    filters: dict | None = Field(None, description="Extracted filters for hybrid queries")


class SQLRequest(BaseModel):
    """SQL query request."""
    query: str = Field(..., description="Natural language query for SQL execution")


class SQLResponse(BaseModel):
    """SQL query response."""
    request_id: str = Field(..., description="The request ID")
    answer: str = Field(..., description="The answer to the query")
    sql_query: str = Field(..., description="The generated SQL query")
    result_count: int = Field(..., description="Number of results returned")