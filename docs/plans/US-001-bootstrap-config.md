# US-001: Bootstrap & Config

## 1. Story Understanding (What, Why, and What For)
- **What:** Initialize the Python environment, configure dependencies, structure the project directories, and implement application settings using `pydantic-settings`. Create a basic FastAPI entrypoint with a health-check endpoint.
- **Why:** Every robust web application needs a structured entry point, verified configuration loading, and isolated virtual environment dependencies.
- **What For:** Provides the workspace foundation and verifies that the FastAPI engine can boot correctly with all necessary configuration options validated before other services start.

---

## 2. Full-Stack Impact Analysis

| Tier | Impact | Description |
|---|---|---|
| **Database** | No | No database configuration or schema changes are needed in this stage. |
| **Backend** | Yes | Define configuration schema via Pydantic, define main application routing, and specify dependency lists. |
| **Frontend** | No | The project is a pure FastAPI backend system; no frontend client is built in this repository. |

---

## 3. Database Changes
No database changes are required for this story.

---

## 4. Ordered Implementation Plan

- [x] ✅ **Task 1: Setup Python virtual environment and dependencies**
  - Create and activate virtual environment `venv`.
  - Install dependencies: `fastapi`, `uvicorn`, `pydantic-settings`, `google-generativeai`, `numpy`.
  - Create `requirements.txt` to freeze dependencies.
- [x] ✅ **Task 2: Configure Environment Settings**
  - Create [config.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/config.py) defining a `Settings` class inheriting from `pydantic_settings.BaseSettings`.
  - Specify fields:
    - `gemini_api_key: str` (required)
    - `similarity_threshold: float = 0.90` (default 0.90)
    - `database_url: str = "sqlite:///./chat_cache.db"` (default local sqlite path)
  - Create [.env.example](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/.env.example) to showcase required variables.
- [x] ✅ **Task 3: Implement FastAPI Application Entrypoint**
  - Create [main.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/main.py).
  - Initialize the FastAPI instance with startup logic that validates the configuration settings.
  - Implement a simple `GET /health` endpoint returning `{"status": "ok"}`.

---

## 5. Use Cases

| Use Case | Acceptance Criteria | Tiers Touched | Verification Method |
|---|---|---|---|
| **UC-1.1: System Boots Successfully** ✅ | AC-1: FastAPI app boots with a basic `/health` check endpoint. | BE | Run `uvicorn main:app --reload` and send a GET request to `/health`. Validate response `{"status": "ok"}`. |
| **UC-1.2: Validate Config Loading** ✅ | AC-2: Environment variables are validated using `pydantic-settings`. | BE | Check that the settings object parses correctly when valid keys are provided in `.env`. |
| **UC-1.3: Prevent Startup on Missing API Key** ✅ | AC-3: Missing `.env` variables throw a validation error on startup. | BE | Run application without setting `GEMINI_API_KEY` and verify it raises a validation error on startup and fails to run. |

---

## 6. Assumptions and Decisions
- **Assumption:** No specific module boundaries are needed for this lightweight project, so files can reside directly in the root directory for simplicity (e.g., `main.py`, `config.py`), keeping code clean and maintainable.
- **Decision:** Use standard Pydantic Settings to allow environment variables to be read from `.env` or system environment context.
