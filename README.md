# FastAPI Backend - Semantic Cache & Gemini Chat API

A backend developed with **FastAPI**, **Pydantic**, and **SQLite** implementing an intelligent chat system connected to the **Google Gemini** API. It features a semantic cache strategy based on embeddings to optimize costs and response times.

---

## 🚀 Key Features

* **FastAPI & Pydantic:** Fast, validated, and automatically documented endpoints via Swagger/OpenAPI.
* **SQLite:** Lightweight local storage for questions, answers, and their corresponding embeddings.
* **Google Gemini Integration:** Uses official Google models for text generation and embeddings (`gemini-embedding-001`, 3072 dimensions, and chat models).
* **Semantic Cache (Embedding Similarity):**
  * For each incoming question, its vector embedding is generated.
  * It is compared against previously stored embeddings in the database using cosine similarity.
  * If a match greater than or equal to **90%** (configurable) is found, **it returns the cached answer directly without consuming LLM API tokens**.
* **Direct Persistence:** Every new interaction (question, answer, and embedding) is saved entirely (no chunking or segmentation is used).
* **Specific Endpoints:** Allows asking questions, listing history, and performing manual similarity searches with exact metrics.

---

## 🛠️ Technologies Used

* **Python 3.10+**
* **FastAPI**
* **Pydantic / Pydantic Settings**
* **SQLite** (using raw vector manipulation or math computation in Python/NumPy)
* **Google GenAI SDK** (`google-genai`)

---

## 📦 Installation & Configuration

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repository-url>
   cd <project-directory-name>
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:
   ```bash
   pip install fastapi uvicorn pydantic-settings google-genai numpy sqlalchemy pytest
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the root of the project based on the following example:
   ```env
   GEMINI_API_KEY=your_google_gemini_api_key
   SIMILARITY_THRESHOLD=0.90
   DATABASE_URL=sqlite:///./chat_cache.db
   ```

---

## ▶️ Running the Application

Start the development server with Uvicorn:

```bash
uvicorn main:app --reload
```

The API will be available at:

* **Interactive documentation (Swagger UI):** `http://127.0.0.1:8000/docs`
* **Alternative documentation (ReDoc):** `http://127.0.0.1:8000/redoc`

---

## 🧪 Testing the Application

The project uses **pytest** for test discovery and execution. Tests cover the cache engine, database layer, and the live Gemini SDK integration.

### Run all tests

```bash
pytest
```

Or explicitly:

```bash
python -m pytest
```

### Run with verbose output

```bash
python -m pytest -v
```

### Run tests without live API calls

`tests/test_gemini_service.py` requires a valid `GEMINI_API_KEY` because it calls the real Gemini API. To run only the isolated tests:

```bash
python -m pytest tests/test_cache_engine.py tests/test_database.py -v
```

### Run the live Gemini integration tests

Make sure your `.env` file includes a valid key:

```bash
GEMINI_API_KEY=your_google_gemini_api_key
```

Then run:

```bash
python -m pytest tests/test_gemini_service.py -v
```

### Test the `/chat` endpoint manually

Start the server:

```bash
uvicorn main:app --reload
```

Then send a request:

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is FastAPI?"}'
```

*Note: The public API contract uses English paths and field names (`/chat`, `source`, `similarity_percentage`). This aligns the README, agents.md, and implementation.*

---

## 📌 Available Endpoints

### 1. Send a Question (Intelligent Chat)

* **URL:** `POST /chat`
* **Description:** Receives a question, generates its embedding, searches for similarity in the database (>= 90%). If it exceeds the threshold, it responds using the cache; otherwise, it queries Gemini, saves the result, and returns it.
* **Payload (JSON):**
  ```json
  {
    "question": "What is FastAPI?"
  }
  ```

* **Response:**
  ```json
  {
    "source": "semantic_cache",
    "similarity_percentage": 0.95,
    "current_question": "What is FastAPI?",
    "saved_question": "What is FastAPI and what is it used for?",
    "response": "FastAPI is a modern web framework..."
  }
  ```

### 2. List Question History

* **URL:** `GET /questions`
* **Description:** Returns the complete list of all questions and answers stored in the database.
* **Response:**
  ```json
  [
    {
      "id": 1,
      "question": "What is FastAPI?",
      "response": "FastAPI is a modern web framework...",
      "created_at": "2026-08-09T18:44:39"
    }
  ]
  ```

### 3. Manual Similarity Search

* **URL:** `POST /similarity-search`
* **Description:** Allows testing the semantic search engine by sending a query and retrieving the similarity percentage with the closest registered question.
* **Payload (JSON):**
  ```json
  {
    "question": "Explain FastAPI to me"
  }
  ```

* **Response:**
  ```json
  {
    "similarity_percentage": 0.92,
    "current_question": "Explain FastAPI to me",
    "saved_question": "What is FastAPI?",
    "saved_response": "FastAPI is a modern web framework..."
  }
  ```
