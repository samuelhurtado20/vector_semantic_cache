---
name: implement
description: Guidelines and architectural context for implementing and extending the FastAPI backend with Semantic Cache and Gemini API integration.
---

# Instructions

## Project Context
You are working on a FastAPI backend designed to provide an intelligent chat system connected to the Google Gemini API. The core feature of this system is a **Semantic Cache** that minimizes API token usage and latency by serving highly similar past queries directly from a local SQLite database.

## Technology Stack
- **Framework:** FastAPI, Pydantic, Pydantic-Settings
- **Language:** Python 3.10+
- **Database:** SQLite (using local vector serialization and NumPy for similarity math)
- **AI Integration:** `google-generativeai` (Google GenAI SDK)
- **Models:** Gemini chat models for generation, `text-embedding-004` for vector embeddings.

## Core Implementation Rules

### 1. Semantic Cache Logic (CRITICAL)
- **Embedding Generation:** Every incoming question MUST first be converted into a vector embedding using the Gemini `text-embedding-004` model.
- **Similarity Computation:** Compute cosine similarity between the incoming question's embedding and all stored embeddings in the SQLite database. Use `numpy` for efficient array operations.
- **Threshold:** The strict threshold for a semantic match is **>= 0.90 (90%)** (configurable via the `SIMILARITY_THRESHOLD` env variable).
- **Cache Hit:** If similarity >= threshold, return the cached answer immediately. Set the source flag to `cache_semantico`. Do NOT call the Gemini chat model.
- **Cache Miss:** If similarity < threshold, query the Gemini chat model, return the generated response, and immediately persist the original question, its embedding, and the response to the database. Do not use chunking or segmentation.

### 2. Database Operations (SQLite)
- Store data locally (e.g., `chat_cache.db`) as defined by `DATABASE_URL`.
- Embeddings should be efficiently serialized (e.g., JSON strings or BLOB bytes) for storage in SQLite, and deserialized into numpy arrays upon retrieval for computation.
- Maintain simple, direct persistence of interactions.

### 3. API Endpoints Contract
Ensure all current and future endpoints adhere strictly to the defined request/response schemas:
- **`POST /chat`**: 
  - Accepts: `{"pregunta": str}`
  - Returns: JSON containing `fuente` (source), `porcentaje_similitud`, `pregunta_actual`, `pregunta_guardada` (if cache hit), and `respuesta`.
- **`GET /preguntas`**: 
  - Returns: The full history of saved Q&As without embeddings attached in the payload.
- **`POST /buscar-similitud`**: 
  - Accepts: `{"pregunta": str}`
  - Returns: A test lookup containing `porcentaje_similitud`, `pregunta_actual`, `pregunta_guardada`, and `respuesta_guardada` without triggering a new AI generation.

### 4. Configuration and Environment
- Always use `pydantic-settings` to manage environment variables (`GEMINI_API_KEY`, `SIMILARITY_THRESHOLD`, `DATABASE_URL`).
- Ensure fallback mechanisms or graceful errors if environment variables are missing.
- Never hardcode API keys or connection strings.

### 5. Code Style & Quality
- Use strong typing and highly validated Pydantic models for all inputs and outputs.
- Write asynchronous code (`async def`) for FastAPI route handlers, especially for network I/O operations (like Gemini API calls).
- Maintain clean OpenAPI/Swagger documentation by leveraging FastAPI's built-in descriptions, tags, and summary decorators.