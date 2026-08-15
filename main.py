import asyncio

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from config import settings
from database import get_all_interactions, get_db, init_db, save_interaction
from exceptions import DatabaseError, register_exception_handlers
from models import InteractionCache
from schemas import ChatRequest, ChatResponse, HealthResponse, InteractionHistory
from services.cache_engine import search_cache
from services.gemini import generate_response, get_embedding

app = FastAPI(
    title="Vector Semantic Cache Chat API",
    description="FastAPI backend utilizing SQLite semantic cache and Google Gemini API.",
    version="1.0.0"
)

register_exception_handlers(app)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


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
