# US-006: History Endpoint (`GET /questions`)

## 1. Story Understanding (What, Why, and What For)
- **What:** Create a `GET /questions` endpoint that retrieves all stored query-response records from SQLite.
- **Why:** Developers and administrators need to see what interactions are saved in the cache database to inspect quality and monitor coverage.
- **What For:** Provides a historical log of cached queries, excluding heavy raw embeddings to keep the payload size optimized.

---

## 2. Full-Stack Impact Analysis

| Tier | Impact | Description |
|---|---|---|
| **Database** | Yes | Read all rows from the `interaction_cache` table. |
| **Backend** | Yes | Define response schemas that omit the vector embedding array, and implement the GET endpoint handler in `main.py`. |
| **Frontend** | No | The project is a pure FastAPI backend system; no frontend client is built in this repository. |

---

## 3. Database Changes
No database schema changes are required for this story.

---

## 4. Ordered Implementation Plan

- [ ] **Task 1: Define History Response Schema**
  - In [schemas.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/schemas.py), define `InteractionHistory`:
    - `id: int`
    - `question: str`
    - `response: str`
    - `created_at: datetime`
- [ ] **Task 2: Implement `/questions` Endpoint**
  - In [main.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/main.py):
    - Define a `GET /questions` endpoint returning a list of `InteractionHistory`.
    - Query the database to retrieve all rows.
    - Validate and serialize the records into the `InteractionHistory` schemas (automatically excluding `embedding`).

---

## 5. Use Cases

| Use Case | Acceptance Criteria | Tiers Touched | Verification Method |
|---|---|---|---|
| **UC-6.1: Retrieve Entire History** | AC-1: Endpoint returns a list of all stored interactions. | DB, BE | Seed the database with 2 mock interactions. Call `GET /questions` and verify the array contains both records. |
| **UC-6.2: Exclude Embedding Array** | AC-2: Exclude the raw embeddings array from the payload. | BE | Query the endpoint and assert that the key `embedding` is not present in the returned JSON object list. |
| **UC-6.3: Check Field Output** | AC-3: Returns fields: `id`, `question`, `response`, `created_at`. | BE | Inspect the return JSON keys of each history item to confirm they contain `id`, `question`, `response`, and `created_at`. |

---

## 6. Assumptions and Decisions
- **Assumption:** The database size will be manageable in a local environment. No pagination is requested, but standard sorting (newest first) will be used.
- **Decision:** Keep the `embedding` database column completely hidden from the REST response schema, protecting bandwidth and API users from parsing huge float arrays.
