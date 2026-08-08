# US-005: Chat Endpoint (`POST /chat`)

## 1. Story Understanding (What, Why, and What For)
- **What:** Create the primary endpoint `POST /chat` that processes a user's question, uses the semantic cache, calls the Gemini model on cache miss, and saves the new answer.
- **Why:** This endpoint is the core functionality of the project, routing queries intelligently to either a cheap database cache hit or a rich LLM call.
- **What For:** Provides client applications with a fast, cost-optimized, and context-aware chat interface.

---

## 2. Full-Stack Impact Analysis

| Tier | Impact | Description |
|---|---|---|
| **Database** | Yes | Read existing logs to test similarity, and persist new queries/answers/embeddings when cache misses. |
| **Backend** | Yes | Define input/output Pydantic schemas, write the route logic in `main.py` (or a dedicated router), and orchestrate cache matching and API fallbacks. |
| **Frontend** | No | The project is a pure FastAPI backend system; no frontend client is built in this repository. |

---

## 3. Database Changes
No database schema changes are required for this story. The database is read/written inside the route logic.

---

## 4. Ordered Implementation Plan

- [ ] **Task 1: Define Request and Response Schemas**
  - Create [schemas.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/schemas.py).
  - Define `ChatRequest` containing:
    - `pregunta: str` (non-empty)
  - Define `ChatResponse` containing:
    - `fuente: str` (either `"cache_semantico"` or `"llm"`)
    - `porcentaje_similitud: float` (cosine similarity score)
    - `pregunta_actual: str`
    - `pregunta_guardada: Optional[str] = None` (populated only on cache hit)
    - `respuesta: str`
- [ ] **Task 2: Implement `/chat` Route Logic**
  - In [main.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/main.py):
    - Define `POST /chat` accepting `ChatRequest` and injecting `db_session`.
    - Generate embedding for `pregunta` using `services.gemini.get_embedding`.
    - Check the cache using `services.cache_engine.buscar_en_cache`.
    - **On Hit (similarity $\ge$ threshold):**
      - Return `ChatResponse` with `fuente="cache_semantico"`, matching details, and cached answer.
    - **On Miss (similarity < threshold):**
      - Query Gemini using `services.gemini.generate_response`.
      - Save the query, response, and embedding vector to the DB.
      - Return `ChatResponse` with `fuente="llm"`, similarity score, and Gemini response.

---

## 5. Use Cases

| Use Case | Acceptance Criteria | Tiers Touched | Verification Method |
|---|---|---|---|
| **UC-5.1: Request Format Validation** | AC-1: Expects a payload `{"pregunta": "..."}`. | BE | Send a request with a missing `pregunta` field or invalid type, and verify the server returns a `422 Unprocessable Entity` status code. |
| **UC-5.2: Process Cache Hit** | AC-2: Returns cached response on threshold hit, marking `"fuente": "cache_semantico"`. | DB, BE | Insert a seed row. Send a highly similar request. Confirm the response `fuente` is `"cache_semantico"` and similarity is returned. |
| **UC-5.3: Process Cache Miss** | AC-3: Generate embedding, query Gemini, persist, and return response marking `"fuente": "llm"`. | DB, BE | Send a unique request. Confirm response `fuente` is `"llm"`. Verify that the database now contains the new interaction row. |
| **UC-5.4: Validate Response Structure** | AC-4: Response matches the exact schema contract. | BE | Assert that the response contains all required fields: `fuente`, `porcentaje_similitud`, `pregunta_actual`, and `respuesta`. |

---

## 6. Assumptions and Decisions
- **Assumption:** SQLite handles concurrent writes safely through standard session commits. No high-volume queuing is required.
- **Decision:** Serialize float lists to JSON strings using Python's standard `json.dumps()` before saving them to the `embedding` TEXT column, and deserialize them with `json.loads()` when querying.
