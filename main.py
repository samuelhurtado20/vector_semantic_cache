import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from config import settings
from database import get_all_interactions, get_db, init_db, save_interaction
from exceptions import DatabaseError, register_exception_handlers
from models import InteractionCache
from schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    InteractionHistory,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from services.cache_engine import find_closest_match, search_cache
from services.gemini import generate_response, get_embedding


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on application startup."""
    init_db()
    yield


app = FastAPI(
    title="Vector Semantic Cache Chat API",
    description="FastAPI backend utilizing SQLite semantic cache and Google Gemini API.",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Simple health check endpoint to verify that the API is running and configured correctly.

    Does not expose connection strings, API keys, or model names.
    """
    return HealthResponse(status="ok", threshold=settings.similarity_threshold)


@app.post("/chat", response_model=ChatResponse, tags=["Chat"], summary="Process a chat question")
async def chat(request: ChatRequest, db_session: Session = Depends(get_db)) -> ChatResponse:
    """
    Process a user question using the semantic cache.

    - Generates an embedding for the incoming question.
    - Searches the cache for a semantically similar stored question.
    - On cache hit (similarity >= threshold), returns the cached answer.
    - On cache miss, queries Gemini, persists the new interaction, and returns the LLM answer.
    """
    question = request.question

    question_embedding = await asyncio.to_thread(get_embedding, question)
    is_hit, matched_record, best_similarity = await asyncio.to_thread(
        search_cache, question_embedding, db_session
    )

    if is_hit and matched_record is not None:
        return ChatResponse(
            source="semantic_cache",
            similarity_percentage=best_similarity,
            current_question=question,
            saved_question=matched_record.question,
            response=matched_record.response,
        )

    llm_response = await asyncio.to_thread(generate_response, question)
    try:
        save_interaction(db_session, question=question, response=llm_response, embedding=question_embedding)
        db_session.commit()
    except Exception as exc:
        db_session.rollback()
        raise DatabaseError(f"Failed to persist interaction: {exc}") from exc

    return ChatResponse(
        source="llm",
        similarity_percentage=best_similarity,
        current_question=question,
        response=llm_response,
    )


@app.get(
    "/questions",
    response_model=list[InteractionHistory],
    tags=["History"],
    summary="Retrieve interaction history",
)
async def get_questions(db_session: Session = Depends(get_db)) -> list[InteractionCache]:
    """
    Retrieve all stored interactions from the semantic cache.

    Returns a list of question-response records sorted by creation time, newest first.
    The raw embedding vectors are excluded from the response payload.
    """
    return get_all_interactions(db_session)


@app.post(
    "/similarity-search",
    response_model=SimilaritySearchResponse,
    tags=["Search"],
    summary="Manual semantic similarity search",
)
async def similarity_search(
    request: SimilaritySearchRequest,
    db_session: Session = Depends(get_db),
) -> SimilaritySearchResponse:
    """
    Find the most similar cached question to the input, ignoring the threshold.

    This endpoint is read-only: it generates an embedding for the input question,
    compares it against all stored embeddings, and returns the closest match along
    with the similarity score. It does not call the LLM or persist anything.
    """
    question = request.question
    question_embedding = await asyncio.to_thread(get_embedding, question)
    matched_record, best_similarity = await asyncio.to_thread(
        find_closest_match, question_embedding, db_session
    )

    return SimilaritySearchResponse(
        similarity_percentage=best_similarity,
        current_question=question,
        saved_question=matched_record.question if matched_record else None,
        saved_response=matched_record.response if matched_record else None,
    )
