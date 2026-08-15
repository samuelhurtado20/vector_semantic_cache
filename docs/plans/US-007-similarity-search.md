# US-007: Similarity Search Endpoint (`POST /similarity-search`)

## 1. Story Understanding (What, Why, and What For)
- **What:** Create a manual testing endpoint `POST /similarity-search` that calculates similarity between the input question and all saved queries in the SQLite database, returning the closest match regardless of whether it meets the threshold.
- **Why:** Allows developers and testers to observe similarity scores to evaluate cache tuning, troubleshoot false hits, and calibrate the threshold.
- **What For:** Provides a debug tool to inspect how close user queries are to existing cache definitions.
- **Language Decision:** The public API uses English paths and field names to stay consistent with the existing `/chat` and `/questions` endpoints and the current code.

---

## 2. Full-Stack Impact Analysis

| Tier | Impact | Description |
|---|---|---|
| **Database** | Yes | Read saved embeddings to compute similarity. |
| **Backend** | Yes | Define input/output schemas and implement the similarity search handler in `main.py`. |
| **Frontend** | No | The project is a pure FastAPI backend system; no frontend client is built in this repository. |

---

## 3. Database Changes
No database schema changes are required for this story.

---

## 4. Ordered Implementation Plan

- [x] **Task 1: Define Similarity Search Schemas** ✅
  - In [schemas.py](../../../../schemas.py), define `SimilaritySearchRequest`:
    - `question: str` (non-empty)
  - Define `SimilaritySearchResponse`:
    - `similarity_percentage: float`
    - `current_question: str`
    - `saved_question: Optional[str] = None`
    - `saved_response: Optional[str] = None`
- [x] **Task 2: Implement `/similarity-search` Route Logic** ✅
  - In [main.py](../../../../main.py):
    - Define a `POST /similarity-search` route accepting `SimilaritySearchRequest` and injecting `db_session`.
    - Generate embedding for the input `question` using `services.gemini.get_embedding`.
    - Perform a similarity sweep using `services.cache_engine.find_closest_match`, ignoring the similarity threshold criteria to return the best match.
    - If the DB has no interactions, return a response with `similarity_percentage=0.0`, and `None` placeholders.
    - Return the best match's details in a `SimilaritySearchResponse` object.

---

## 5. Use Cases

| Use Case | Acceptance Criteria | Tiers Touched | Verification Method |
|---|---|---|---|
| **UC-7.1: Validate Search Input** ✅ | AC-1: Expects a payload `{"question": "..."}`. | BE | Send a request with a blank query. Verify validation fails with `422 Unprocessable Entity`. |
| **UC-7.2: Return Closest Match** ✅ | AC-2: Computes similarity against all saved records and returns the closest match even if below threshold. | DB, BE | Seed "How does python work?". Send request for "How to bake a cake?" (expected low similarity, e.g. ~0.35). Confirm it returns the python question as the closest match with the similarity score. |
| **UC-7.3: Check Output Keys** ✅ | AC-3: Returns fields: `similarity_percentage`, `current_question`, `saved_question`, `saved_response`. | BE | Inspect JSON output from `POST /similarity-search` to ensure all fields are correctly populated. |

---

## 6. Assumptions and Decisions
- **Assumption:** If the database contains no entries, the search cannot find a closest match. The endpoint will handle this edge case gracefully by returning a null-match response rather than throwing a server error.
- **Decision:** Do not persist the search query or its generated embedding into the database, as this endpoint is strictly read-only for testing.
