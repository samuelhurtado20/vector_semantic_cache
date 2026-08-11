from fastapi import FastAPI

from config import settings
from database import init_db

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
        "database": settings.database_url
    }
