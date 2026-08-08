# FastAPI Backend - Semantic Cache & Gemini Chat API

A backend developed with **FastAPI**, **Pydantic**, and **SQLite** implementing an intelligent chat system connected to the **Google Gemini** API. It features a semantic cache strategy based on embeddings to optimize costs and response times.

---

## 🚀 Key Features

* **FastAPI & Pydantic:** Fast, validated, and automatically documented endpoints via Swagger/OpenAPI.
* **SQLite:** Lightweight local storage for questions, answers, and their corresponding embeddings.
* **Google Gemini Integration:** Uses official Google models for text generation and embeddings (`text-embedding-004` and chat models).
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
* **Google GenAI SDK** (`google-generativeai`)

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
   pip install fastapi uvicorn google-generativeai pydantic-settings numpy
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

## 📌 Available Endpoints

### 1. Send a Question (Intelligent Chat)

* **URL:** `POST /chat`
* **Description:** Receives a question, generates its embedding, searches for similarity in the database (>= 90%). If it exceeds the threshold, it responds using the cache; otherwise, it queries Gemini, saves the result, and returns it.
* **Payload (JSON):**
  ```json
  {
    "pregunta": "What is FastAPI?"
  }
  ```

* **Response:**
  ```json
  {
    "fuente": "cache_semantico",
    "porcentaje_similitud": 0.95,
    "pregunta_actual": "What is FastAPI?",
    "pregunta_guardada": "What is FastAPI and what is it used for?",
    "respuesta": "FastAPI is a modern web framework..."
  }
  ```

### 2. List Question History

* **URL:** `GET /preguntas`
* **Description:** Returns the complete list of all questions and answers stored in the database.

### 3. Manual Similarity Search

* **URL:** `POST /buscar-similitud`
* **Description:** Allows testing the semantic search engine by sending a query and retrieving the similarity percentage with the closest registered question.
* **Payload (JSON):**
  ```json
  {
    "pregunta": "Explain FastAPI to me"
  }
  ```

* **Response:**
  ```json
  {
    "porcentaje_similitud": 0.92,
    "pregunta_actual": "Explain FastAPI to me",
    "pregunta_guardada": "What is FastAPI?",
    "respuesta_guardada": "FastAPI is a modern web framework..."
  }
  ```
