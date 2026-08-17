# Code Review: Vector Semantic Cache FastAPI Backend

**Date:** 2026-08-17 (updated)  
**Scope:** Full backend review (`main.py`, `config.py`, `database.py`, `models.py`, `schemas.py`, `services/`, `tests/`, `README.md`).  
**Guidelines:** Reviewed against the `python-backend` FastAPI skill (async-first, Pydantic validation, dependency injection, fail fast, security by default).

---

## Executive Summary

The codebase is a functional FastAPI prototype with a clear separation between routes, services, and database layers. The semantic-cache flow is correctly implemented at a high level, and Pydantic settings are used well. All high-priority review items have been resolved: global exception handlers, domain-specific error responses, Gemini API error wrapping, database rollback on persistence failures, a sanitized `/health` endpoint, CORS middleware, rate limiting via `slowapi`, and a full suite of 14 FastAPI endpoint integration tests. The remaining improvements are observability, database scalability, and minor configuration refinements.

---

## 1. API Contract & Endpoint Completeness

### Finding 1.1 — `POST /similarity-search` is documented but not implemented ✅ Fixed
- Implemented `POST /similarity-search` in [main.py](main.py#L93-L117).
- Added `SimilaritySearchRequest` and `SimilaritySearchResponse` schemas in [schemas.py](schemas.py).
- Added `find_closest_match` helper in [services/cache_engine.py](services/cache_engine.py) for threshold-agnostic closest-match lookup.
- Endpoint is read-only and does not persist the query or call the LLM.

### Finding 1.2 — Language mismatch between spec sources ✅ Fixed
- Decision: the public API contract uses **English** paths and field names (`/chat`, `/questions`, `/similarity-search`, `source`, `similarity_percentage`, `semantic_cache`).
- [agents.md](agents.md), [README.md](README.md), and [docs/plans/US-007-similarity-search.md](docs/plans/US-007-similarity-search.md) now align with the implementation.
- References to the old `text-embedding-004` model were updated to `gemini-embedding-001` (3072 dimensions) to match [services/gemini.py](services/gemini.py).

### Finding 1.3 — `/health` leaks sensitive configuration ✅ Fixed
- [main.py](main.py#L24-L32) now returns only `status` and `threshold` via `HealthResponse`.
- `database_url` and `gemini_model` are no longer exposed.
- `HealthResponse` schema added in [schemas.py](schemas.py).

---

## 2. Semantic Cache Logic

### Finding 2.1 — Linear full-table scan
- [services/cache_engine.py#L50-L73](services/cache_engine.py#L50-L73) loads every record and deserializes every embedding on every request.

**Recommendation (Medium):** Document the scalability limit. For production, consider:
- An in-memory FAISS/Annoy index rebuilt periodically.
- A dedicated vector store (e.g., Chroma, Qdrant, pgvector).
- At minimum, cache the deserialized embeddings to avoid repeated JSON parsing.

### Finding 2.2 — Source flag inconsistency
- [main.py#L55](main.py#L55) returns `"semantic_cache"`; the `implement` skill requires `"cache_semantico"`.

**Recommendation (High):** Align the source literal with the chosen API contract and use a shared enum/constant.

---

## 3. Error Handling & Resilience

### Finding 3.1 — No global exception handlers ✅ Fixed
- Created [exceptions.py](exceptions.py) with domain-specific errors: `ApplicationError`, `GeminiAPIError`, `DatabaseError`, `ConfigurationError`.
- Added handlers for `RequestValidationError`, domain errors, and a generic catch-all.
- Registered handlers in [main.py](main.py#L14-L16) via `register_exception_handlers(app)`.
- Added `ErrorResponse` schema in [schemas.py](schemas.py).

### Finding 3.2 — Gemini API failures crash the request ✅ Fixed
- [services/gemini.py](services/gemini.py) now catches `google.genai.errors.APIError` and wraps both `get_embedding` and `generate_response` calls.
- Missing `GEMINI_API_KEY` raises `ConfigurationError` at import time with a clear message.

### Finding 3.3 — Database commits lack rollback ✅ Fixed
- [main.py](main.py#L66-L75) now wraps `save_interaction` and `commit()` in try/except, calls `rollback()` on failure, and raises `DatabaseError`.

---

## 4. Async & Concurrency

### Finding 4.1 — Mixed sync/async database access
- Blocking Gemini calls are correctly offloaded via `asyncio.to_thread`.
- `save_interaction` and `commit()` run synchronously inside an async route. This is acceptable for SQLite but is inconsistent.

**Recommendation (Low):** Either offload DB writes to the thread pool or switch to SQLAlchemy async (`create_async_engine`) for consistency.

### Finding 4.2 — Deprecated startup event ✅ Fixed
- [main.py](main.py#L14-L26) now uses an `asynccontextmanager` lifespan and passes it to `FastAPI(..., lifespan=lifespan)`.
- `@app.on_event("startup")` has been removed.

---

## 5. Database & Persistence

### Finding 5.1 — Embeddings stored as JSON text
- [database.py](database.py#L47) serializes embeddings as JSON strings in a `Text` column.

**Recommendation (Medium):** Store as `BLOB` (bytes) for smaller footprint and faster deserialization, or use SQLite JSON1 only if human readability is required.

### Finding 5.2 — No indexes or migrations
- The `interaction_cache` table has no indexes.
- There is no Alembic setup.

**Recommendation (Medium):** Add an index on `created_at` (history ordering) and introduce Alembic before the schema grows.

### Finding 5.3 — History endpoint loads embeddings ✅ Fixed
- `get_all_interactions` in [database.py](database.py) chains `.options(load_only(...))`, selecting only `id`, `question`, `response`, and `created_at`; the `embedding` column is never fetched for the history endpoint.
- A separate `get_all_records` function (no `load_only`) is used by [services/cache_engine.py](services/cache_engine.py) for similarity search so embeddings are loaded in a single query without lazy-load round-trips.

---

## 6. Security

### Finding 6.1 — No CORS configuration ✅ Fixed
- [main.py](main.py) now mounts `CORSMiddleware` with origins controlled by `settings.cors_origins`.
- [config.py](config.py) exposes `cors_origins: list[str] = ["*"]` (override in `.env` for production).
- Preflight and regular cross-origin responses verified in `TestCORSHeaders` integration tests.

### Finding 6.2 — No rate limiting ✅ Fixed
- `slowapi` added to [requirements.txt](requirements.txt) and installed.
- [main.py](main.py) registers a `Limiter` on `app.state.limiter` with a `RateLimitExceeded` exception handler.
- `@limiter.limit(settings.rate_limit)` applied to `/chat`, `/questions`, and `/similarity-search`; `/health` is exempt.
- [config.py](config.py) exposes `rate_limit: str = "60/minute"` (override in `.env`).
- 429 path verified in `TestRateLimiting` integration tests.

### Finding 6.3 — API key validation only at import
- [config.py](config.py) makes `gemini_api_key` required, but there is no runtime check or graceful degradation.

**Recommendation (Low):** Provide a clear startup error if the key is missing, and consider a `/health` sub-check that validates key format without exposing it.

---

## 7. Configuration

### Finding 7.1 — Single monolithic settings object
- All config lives in [config.py](config.py).

**Recommendation (Low):** For larger projects, split into domain-specific configs (e.g., `GeminiConfig`, `DatabaseConfig`) per the `python-backend` skill.

### Finding 7.2 — `pyrefly: ignore` comment
- [config.py](config.py#L1) suppresses a missing-import warning.

**Recommendation (Low):** Ensure `pydantic-settings` is installed in the active environment and remove the suppression, or switch to a standard `# type: ignore`.

---

## 8. Testing

### Finding 8.1 — Mixed test frameworks ✅ Fixed
- [tests/test_database.py](tests/test_database.py) and [tests/test_gemini_service.py](tests/test_gemini_service.py) were rewritten from `unittest` to `pytest`.
- Removed all `if __name__ == "__main__": unittest.main()` blocks.
- All tests now use `pytest` fixtures and assertions.

### Finding 8.2 — No FastAPI endpoint tests ✅ Fixed
- [tests/test_main.py](tests/test_main.py) added with 14 integration tests using `TestClient` and isolated SQLite databases.
- All Gemini SDK calls are monkeypatched; no live API or network access required.
- Coverage: `GET /health`, `POST /chat` (cache hit, miss, 422), `GET /questions` (empty, ordering, embedding exclusion), `POST /similarity-search` (empty cache, no LLM call, partial similarity), CORS headers (regular + preflight), rate limiter registration, and 429 response path.
- `reset_limiter_storage` autouse fixture clears in-memory rate limit counters between tests to prevent interference.

### Finding 8.3 — Live API dependency in tests ✅ Fixed
- [tests/test_gemini_service.py](tests/test_gemini_service.py) now mocks the Gemini SDK by default.
- Live API tests are marked with `@pytest.mark.integration`.
- [pytest.ini](pytest.ini) registers the `integration` marker.

### Finding 8.4 — Weak database test assertion ✅ Fixed
- [tests/test_database.py](tests/test_database.py) now asserts `OperationalError` specifically and uses `sqlalchemy.text()` for raw SQL.

---

## 9. Observability

### Finding 9.1 — No logging ✅ Fixed
- Python's standard `logging` module configured in [main.py](main.py) with `INFO` level and a timestamped format (`%(asctime)s [%(levelname)-8s] %(name)s — %(message)s`).
- `main.py` emits `cache_hit` / `cache_miss` events with similarity score and total request elapsed time (ms).
- `main.py` logs `startup` with the configured threshold and database URL.
- [services/gemini.py](services/gemini.py) logs `embedding_generated` and `response_generated` with per-call elapsed time; errors are logged before re-raising.
- [exceptions.py](exceptions.py) logs `WARNING` for domain/validation errors (`application_error`, `validation_error`) and `ERROR` with full stack trace for unexpected exceptions.

### Finding 9.2 — No metrics or tracing
- No request timing, cache hit-rate, or LLM token usage metrics.

**Recommendation (Low):** Consider `logfire`, `prometheus-client`, or OpenTelemetry for production observability.

---

## 10. Documentation & Comments

### Finding 10.1 — Gemini service docstring is incorrect ✅ Fixed
- [services/gemini.py](services/gemini.py) docstrings now correctly reference `gemini-embedding-001` and 3072 dimensions, matching the actual SDK call.

### Finding 10.2 — README references missing endpoint ✅ Fixed
- `/similarity-search` is now implemented; the README documentation is accurate.

---

## Prioritized Improvement Backlog

### High Priority
1. ✅ Implement `POST /similarity-search`.
2. ✅ Add global exception handlers and domain-specific error responses.
3. ✅ Wrap Gemini API calls and database writes in try/except with rollback.
4. ✅ Remove sensitive fields from `/health`.
5. ✅ Align API language (English) across specs, code, and docs.
6. ✅ Fix `services/gemini.py` docstring/model mismatch.
7. ✅ Add FastAPI endpoint integration tests (14 tests in `tests/test_main.py`).
8. ✅ Add CORS middleware (`CORSMiddleware`, configurable via `cors_origins` setting).
9. ✅ Add rate limiting (`slowapi`, `60/minute` default, configurable via `rate_limit` setting).

### Medium Priority (open)
10. Document linear scan scalability limit; evaluate vector index for production (Finding 2.1).
11. Store embeddings as `BLOB` instead of JSON `TEXT` (Finding 5.1).
12. Add `created_at` index and introduce Alembic migrations (Finding 5.2).
13. ✅ Add structured logging for cache hits/misses, API latency, and errors (Finding 9.1).

### Low Priority (open)
14. ✅ Use `load_only` for the history endpoint to avoid fetching embeddings into memory (Finding 5.3).
15. Offload DB writes to thread pool or switch to `create_async_engine` (Finding 4.1).
16. Add metrics/tracing (`logfire`, `prometheus-client`, or OpenTelemetry) (Finding 9.2).

---

## Recently Applied Changes

| Item | Status | Files |
|---|---|---|
| Global exception handlers + domain error responses | ✅ Done | [exceptions.py](exceptions.py), [main.py](main.py), [schemas.py](schemas.py) |
| Wrap Gemini API calls with error handling | ✅ Done | [services/gemini.py](services/gemini.py), [exceptions.py](exceptions.py) |
| Database write rollback on failure | ✅ Done | [main.py](main.py#L66-L75) |
| Sanitize `/health` endpoint | ✅ Done | [main.py](main.py#L24-L32), [schemas.py](schemas.py) |
| Fix Gemini docstring/model mismatch | ✅ Done | [services/gemini.py](services/gemini.py) |
| Align API language to English | ✅ Done | [agents.md](agents.md), [README.md](README.md), [docs/plans/US-007-similarity-search.md](docs/plans/US-007-similarity-search.md) |
| Standardize tests on pytest + mock Gemini | ✅ Done | [tests/test_database.py](tests/test_database.py), [tests/test_gemini_service.py](tests/test_gemini_service.py), [pytest.ini](pytest.ini) |
| Replace deprecated startup event with lifespan | ✅ Done | [main.py](main.py) |
| Implement `GET /questions` history endpoint | ✅ Done | [main.py](main.py), [schemas.py](schemas.py) |
| Implement `POST /similarity-search` endpoint | ✅ Done | [main.py](main.py), [schemas.py](schemas.py), [services/cache_engine.py](services/cache_engine.py) |

---

## Conclusion

The project successfully demonstrates the core semantic-cache concept. The most critical operational risks (error handling, Gemini resilience, DB rollback, and health security) have been addressed. The remaining high-impact work is adding FastAPI endpoint integration tests for `/health`, `/chat`, `/questions`, and `/similarity-search`.
