# US-002: Database Setup

## 1. Story Understanding (What, Why, and What For)
- **What:** Configure SQLite connection management and define the database schema to persist chat interactions (questions, responses, and embeddings).
- **Why:** The semantic cache strategy requires a local, quick-access storage layer where historical questions can be matched against incoming queries.
- **What For:** Provides a structured SQLite database (`chat_cache.db`) and helper functions/ORM models to query, update, and persist interaction cache data.

---

## 2. Full-Stack Impact Analysis

| Tier | Impact | Description |
|---|---|---|
| **Database** | Yes | Create the local SQLite database file and initialize the `cache_interacciones` table schema. |
| **Backend** | Yes | Implement database initialization functions, session management, and SQLAlchemy models (or raw SQL queries) representing the interactions. |
| **Frontend** | No | The project is a pure FastAPI backend system; no frontend client is built in this repository. |

---

## 3. Database Changes
Create the table `cache_interacciones` in SQLite:

### Table: `cache_interacciones`
- **Columns:**
  - `id`: `INTEGER` (PRIMARY KEY, AUTOINCREMENT)
  - `pregunta`: `TEXT` (NOT NULL)
  - `respuesta`: `TEXT` (NOT NULL)
  - `embedding`: `TEXT` (NOT NULL, stores the 768-dimensional vector as a serialized JSON string of floats, e.g. `[0.012, -0.054, ...]`)
  - `fecha_creacion`: `DATETIME` (NOT NULL, default: `CURRENT_TIMESTAMP`)
- **Indexes:**
  - Index on `pregunta` (optional, for lookup performance)

---

## 4. Ordered Implementation Plan

- [ ] **Task 1: Set up database session engine**
  - Create [database.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/database.py).
  - Configure the SQLAlchemy engine with `DATABASE_URL` from the settings.
  - Set up `sessionmaker` for local session retrieval and a base class for declarative ORM models.
- [ ] **Task 2: Define ORM Schema Models**
  - Create [models.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/models.py).
  - Define the `CacheInteraccion` model with fields representing the `cache_interacciones` table.
- [ ] **Task 3: Implement Database Lifecycle Helpers**
  - Add DB initialization functions (`init_db`) to create tables on startup.
  - Implement a dependency `get_db` to yield session sessions for endpoint routing.

---

## 5. Use Cases

| Use Case | Acceptance Criteria | Tiers Touched | Verification Method |
|---|---|---|---|
| **UC-2.1: Initialize Tables** | AC-1: A SQLite database is initialized using a URL specified in `DATABASE_URL`. AC-2: Table `cache_interacciones` is created. | DB, BE | Boot the application and verify that the file `chat_cache.db` is created in the root directory. Connect via `sqlite3` CLI and run `.schema cache_interacciones` to confirm column types. |
| **UC-2.2: Add and Fetch Interaction** | AC-3: Database helper functions are created to save/retrieve records. | BE | Run a Python unit test script that opens a DB session, inserts a mock record containing an embedding list, retrieves it, and asserts similarity values. |

---

## 6. Assumptions and Decisions
- **Assumption:** SQLite does not natively support vector types like pgvector. Hence, we serialize the 768-dimensional float embedding array as a JSON string (`TEXT`) in the database, and parse it back to a list of floats or NumPy array when retrieved.
- **Decision:** Use SQLAlchemy for connection management and table creation to keep the implementation standard and easily refactorable.
