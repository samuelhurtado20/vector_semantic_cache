"""
Gemini SDK service module.

Wraps Google GenAI SDK calls for:
- Vector embedding generation using `gemini-embedding-001` (3072 dimensions).
- Text completion (chat) using `gemini-flash-latest` (stable unversioned alias).

Uses the `google-genai` package (google.genai), which supersedes
the deprecated `google-generativeai` package.
"""

from google import genai

from config import settings

# Instantiate a single Client using the API key from settings.
# This replaces the deprecated genai.configure() global call.
_client = genai.Client(api_key=settings.gemini_api_key)


def get_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for the given text using the
    `text-embedding-004` model (768 dimensions).

    Args:
        text: The input text to embed.

    Returns:
        A list of 768 floats representing the dense vector embedding.
    """
    response = _client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    # response.embeddings is a list of ContentEmbedding objects;
    # the first entry holds the values for our single input.
    # gemini-embedding-001 produces 3072-dimensional vectors.
    return response.embeddings[0].values


def generate_response(prompt: str) -> str:
    """
    Generate a text response from the Gemini chat model.

    Uses a stateless chat session via `client.chats.create` and `send_message`,
    which is the recommended way to interact with the model and avoids the
    "automatic function calling" warning associated with `generate_content`.

    Args:
        prompt: The user prompt or question to send to the model.

    Returns:
        The generated text response as a string.
    """
    chat = _client.chats.create(model=settings.gemini_model)
    response = chat.send_message(prompt)
    return response.text
