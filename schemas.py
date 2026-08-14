from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for the main chat endpoint."""

    question: str = Field(..., min_length=1, description="User question to process.")


class ChatResponse(BaseModel):
    """Response body returned by the main chat endpoint."""

    source: Literal["semantic_cache", "llm"] = Field(
        ...,
        description="Indicates whether the answer came from the semantic cache or the LLM.",
    )
    similarity_percentage: float = Field(
        ...,
        description="Cosine similarity score between the current and the cached question (0.0 to 1.0).",
    )
    current_question: str = Field(..., description="The question received in the request.")
    saved_question: Optional[str] = Field(
        None,
        description="The closest cached question when a semantic cache hit occurs.",
    )
    response: str = Field(..., description="Answer returned to the user.")
