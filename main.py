import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on application startup."""
    init_db()
    logger.info(
        "startup similarity_threshold=%.2f database_url=%s",
        settings.similarity_threshold,
        settings.database_url,
    )
    yield


app = FastAPI(
    title="Vector Semantic Cache Chat API",
    description="FastAPI backend utilizing SQLite semantic cache and Google Gemini API.",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Simple health check endpoint to verify that the API is running and configured correctly.

    Does not expose connection strings, API keys, or model names.
    """
    return HealthResponse(status="ok", threshold=settings.similarity_threshold)


@app.post("/chat", response_model=ChatResponse, tags=["Chat"], summary="Process a chat question")
@limiter.limit(settings.rate_limit)
async def chat(request: Request, body: ChatRequest = Body(...), db_session: Session = Depends(get_db)) -> ChatResponse:
    """
    Process a user question using the semantic cache.

    - Generates an embedding for the incoming question.
    - Searches the cache for a semantically similar stored question.
    - On cache hit (similarity >= threshold), returns the cached answer.
    - On cache miss, queries Gemini, persists the new interaction, and returns the LLM answer.
    """
    question = body.question
    _t0 = time.perf_counter()

    question_embedding = await asyncio.to_thread(get_embedding, question)
    is_hit, matched_record, best_similarity = await asyncio.to_thread(
        search_cache, question_embedding, db_session
    )

    if is_hit and matched_record is not None:
        logger.info(
            "cache_hit similarity=%.4f elapsed_ms=%.1f question=%r",
            best_similarity,
            (time.perf_counter() - _t0) * 1000,
            question[:80],
        )
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

    logger.info(
        "cache_miss similarity=%.4f elapsed_ms=%.1f question=%r",
        best_similarity,
        (time.perf_counter() - _t0) * 1000,
        question[:80],
    )
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
@limiter.limit(settings.rate_limit)
async def get_questions(request: Request, db_session: Session = Depends(get_db)) -> list[InteractionCache]:
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
@limiter.limit(settings.rate_limit)
async def similarity_search(
    request: Request,
    body: SimilaritySearchRequest = Body(...),
    db_session: Session = Depends(get_db),
) -> SimilaritySearchResponse:
    """
    Find the most similar cached question to the input, ignoring the threshold.

    This endpoint is read-only: it generates an embedding for the input question,
    compares it against all stored embeddings, and returns the closest match along
    with the similarity score. It does not call the LLM or persist anything.
    """
    question = body.question
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
