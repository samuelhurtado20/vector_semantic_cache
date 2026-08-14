import asyncio

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from config import settings
from database import get_db, init_db, save_interaction
from schemas import ChatRequest, ChatResponse
from services.cache_engine import search_cache
from services.gemini import generate_response, get_embedding

app = FastAPI(
    title="Vector Semantic Cache Chat API",
    description="FastAPI backend utilizing SQLite semantic cache and Google Gemini API.",
    version="1.0.0"
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint to verify that the API is running and configured correctly.
    """
    return {
        "status": "ok",
        "threshold": settings.similarity_threshold,
        "database": settings.database_url,
        "gemini_model": settings.gemini_model,
    }


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
    save_interaction(db_session, question=question, response=llm_response, embedding=question_embedding)
    db_session.commit()

    return ChatResponse(
        source="llm",
        similarity_percentage=best_similarity,
        current_question=question,
        response=llm_response,
    )
