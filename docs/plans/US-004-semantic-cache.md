# US-004: Semantic Cache Engine

## 1. Story Understanding (What, Why, and What For)
- **What:** Create a semantic cache engine that calculates cosine similarity between the incoming query vector and all stored query vectors in the SQLite database.
- **Why:** Pure string matching is too rigid for natural language queries. If a user asks "How do I install FastAPI?" and another asks "FastAPI installation guide", they should hit the same cache item.
- **What For:** Performs vector similarity search locally on SQLite records, identifying cache hits when similarity exceeds `SIMILARITY_THRESHOLD`.

---

## 2. Full-Stack Impact Analysis

| Tier | Impact | Description |
|---|---|---|
| **Database** | Yes | Fetch all stored records (including serialized embeddings) to perform similarity search. |
| **Backend** | Yes | Implement `services/cache_engine.py` which contains vector math (using NumPy or pure python) and the cache lookup workflow. |
| **Frontend** | No | The project is a pure FastAPI backend system; no frontend client is built in this repository. |

---

## 3. Database Changes
No database schema changes are required for this story. The database is queried for matching embeddings.

---

## 4. Ordered Implementation Plan

- [ ] **Task 1: Implement Cosine Similarity Calculation**
  - Create [services/cache_engine.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/services/cache_engine.py).
  - Define `calcular_similitud_coseno(vecA: list[float], vecB: list[float]) -> float` using NumPy:
    $$\text{similarity} = \frac{\vec{A} \cdot \vec{B}}{\|\vec{A}\| \|\vec{B}\|}$$
- [ ] **Task 2: Implement Cache Search Logic**
  - Implement `buscar_en_cache(pregunta_embedding: list[float], db_session) -> tuple[bool, dict | None, float]`:
    - Query all interactions from `cache_interacciones`.
    - Deserialize each embedding JSON string to a list of floats.
    - Calculate similarity with `pregunta_embedding`.
    - Find the item with the maximum similarity.
    - If maximum similarity $\ge$ `settings.similarity_threshold`, return `(True, matching_record, similarity_score)`.
    - Otherwise, return `(False, None, similarity_score)`.

---

## 5. Use Cases

| Use Case | Acceptance Criteria | Tiers Touched | Verification Method |
|---|---|---|---|
| **UC-4.1: Compute Cosine Similarity** | AC-1: Implement cosine similarity calculation. | BE | Run unit tests comparing predefined vectors. Verify identical vectors return `1.0` (or near `1.0`), and orthogonal vectors return `0.0`. |
| **UC-4.2: Retrieve Cache Hit** | AC-2: Search database for highest cosine similarity. AC-3: If similarity $\ge$ threshold, return the cached record. | DB, BE | Save an interaction for "How is FastAPI used?" with its embedding. Run `buscar_en_cache` with a similar query like "What is the usage of FastAPI?" and verify it returns a hit. |
| **UC-4.3: Return Cache Miss** | AC-3: If highest similarity < threshold, return `None`. | DB, BE | Run `buscar_en_cache` with a completely unrelated query like "How to cook pasta?". Verify it returns `False` (cache miss) and a low similarity score. |

---

## 6. Assumptions and Decisions
- **Assumption:** Since SQLite does not have vector indexes, linear scanning (O(N) complexity) is used. Given typical local chat histories (<10,000 queries), this is extremely fast (under 10ms) and avoids complex vector database setup.
- **Decision:** Utilize NumPy for fast vectorized vector math (dot product, norms) to minimize latency during calculations.
