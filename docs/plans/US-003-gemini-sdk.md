# US-003: Gemini SDK Integration

## 1. Story Understanding (What, Why, and What For)
- **What:** Integrate the official Google GenAI SDK (`google-generativeai`) into the FastAPI backend. Construct functions to generate vector embeddings with the `text-embedding-004` model and fetch completions using Gemini text generation.
- **Why:** The semantic cache needs to represent user inputs as dense vector embeddings to calculate cosine similarity. If the cache misses, the backend needs to fall back to the live Gemini LLM to generate responses.
- **What For:** Provides wrapper services for communicating with the Gemini API to handle embeddings generation and text chat completion.

---

## 2. Full-Stack Impact Analysis

| Tier | Impact | Description |
|---|---|---|
| **Database** | No | No database configuration or schema changes are needed. |
| **Backend** | Yes | Implement a Gemini service file `services/gemini.py` that wraps SDK calls and reads API keys from settings. |
| **Frontend** | No | The project is a pure FastAPI backend system; no frontend client is built in this repository. |

---

## 3. Database Changes
No database changes are required for this story.

---

## 4. Ordered Implementation Plan

- [ ] **Task 1: Setup Gemini SDK initialization**
  - Create [services/gemini.py](file:///c:/Users/Usuario/Documents/git_repositories/vector_semantic_cache/services/gemini.py).
  - Import `google.generativeai as genai`.
  - Configure the client using `genai.configure(api_key=settings.gemini_api_key)`.
- [ ] **Task 2: Implement Vector Embedding service**
  - Implement a function `get_embedding(text: str) -> list[float]`.
  - Call the API using `genai.embed_content(model="models/text-embedding-004", content=text)`.
  - Extract and return the embedding float list (768 dimensions).
- [ ] **Task 3: Implement Text Generation service**
  - Implement a function `generate_response(prompt: str) -> str`.
  - Use `genai.GenerativeModel("gemini-1.5-flash")` to initialize the chat/generation client.
  - Call `generate_content(prompt)` and return the text block.

---

## 5. Use Cases

| Use Case | Acceptance Criteria | Tiers Touched | Verification Method |
|---|---|---|---|
| **UC-3.1: Generate Embeddings via SDK** | AC-1: Initialize Gemini client using API key. AC-2: Service returns 768-dimensional float list using `text-embedding-004`. | BE | Call `get_embedding("What is FastAPI?")` in a test script. Assert the returned value is a list of floats, and `len(result) == 768`. |
| **UC-3.2: Generate Text Response via SDK** | AC-3: Service returns a string response from Gemini chat model. | BE | Call `generate_response("Translate hello to Spanish")` in a test script. Assert that the response is a string containing the text "hola" (case-insensitive). |

---

## 6. Assumptions and Decisions
- **Assumption:** The model `text-embedding-004` yields 768-dimensional vectors by default. We do not set custom dimensions unless requested.
- **Decision:** Use `gemini-1.5-flash` as the default model for chat generation to ensure fast response times and low token usage costs, while keeping it configurable.
