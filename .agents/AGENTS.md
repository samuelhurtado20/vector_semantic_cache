# Agent Rules and Guidelines for Vector Semantic Cache

This repository contains a **FastAPI** backend that implements an intelligent chat connected to the **Google Gemini** API, optimized using a local **semantic cache** system with **SQLite** and embeddings.

When working on this project, adhere to the following guidelines and design rules:

## 🛠️ Technologies & Technical Stack
- **Language:** Python 3.10+
- **Web Framework:** FastAPI, using Pydantic for validation and Pydantic Settings for configuration.
- **Database:** SQLite (`sqlite:///./chat_cache.db` by default) to store questions, answers, and vector embeddings.
- **Embeddings:** Google GenAI SDK (`google-generativeai`) using the `text-embedding-004` model.
- **Vector Math:** Cosine similarity calculated with NumPy or via direct mathematical computation in Python/SQLite.

## 📌 Semantic Cache Logic
1. **Query Flow (`POST /chat`):**
   - Generate the embedding of the incoming question using `text-embedding-004`.
   - Compare the embedding with the database records using cosine similarity.
   - If the similarity with any saved question is greater than or equal to the threshold (`SIMILARITY_THRESHOLD` - default `0.90` / 90%):
     - Return the saved response directly from the database (marking `"source": "semantic_cache"`).
   - Otherwise:
     - Query the Google Gemini API to get a new response.
     - Persist the question, response, and its corresponding vector embedding in the database.
     - Return the retrieved response (marking `"source": "llm"`).

2. **Direct Persistence:**
   - Interactions are saved in their entirety. Do not use chunking or segmentation unless explicitly requested.

## ⚙️ Configuration & Environment Variables
Any changes or extensions must respect the following environment variables in the `.env` file:
- `GEMINI_API_KEY`: Official API Key for Google Gemini.
- `SIMILARITY_THRESHOLD`: Minimum similarity percentage to consider a cache hit (e.g., `0.90`).
- `DATABASE_URL`: URI for the SQLite database (e.g., `sqlite:///./chat_cache.db`).

## 📁 Standard Endpoints
Maintain and respect the contracts of the following endpoints:
- `POST /chat`: Main interaction with chat and semantic cache.
- `GET /questions`: List the history of saved interactions.
- `POST /similarity-search`: Manual search of semantic similarity for testing and metrics.
