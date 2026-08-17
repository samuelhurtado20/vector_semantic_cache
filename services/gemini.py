"""
Gemini SDK service module.

Wraps Google GenAI SDK calls for:
- Vector embedding generation using `gemini-embedding-001` (3072 dimensions).
- Text completion (chat) using `gemini-flash-latest` (stable unversioned alias).

Uses the `google-genai` package (google.genai), which supersedes
the deprecated `google-generativeai` package.
"""

import logging
import time

from google import genai
from google.genai import errors as genai_errors

from config import settings
from exceptions import ConfigurationError, GeminiAPIError

logger = logging.getLogger(__name__)


# Instantiate a single Client using the API key from settings.
# This replaces the deprecated genai.configure() global call.
if not settings.gemini_api_key:
    raise ConfigurationError("GEMINI_API_KEY is not configured.")

_client = genai.Client(api_key=settings.gemini_api_key)


def get_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for the given text using the
    `gemini-embedding-001` model (3072 dimensions).

    Args:
        text: The input text to embed.

    Returns:
        A list of 3072 floats representing the dense vector embedding.
    """
    _t0 = time.perf_counter()
    try:
        response = _client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        )
        # response.embeddings is a list of ContentEmbedding objects;
        # the first entry holds the values for our single input.
        # gemini-embedding-001 produces 3072-dimensional vectors.
        values = response.embeddings[0].values
        logger.info("embedding_generated elapsed_ms=%.1f", (time.perf_counter() - _t0) * 1000)
        return values
    except genai_errors.APIError as exc:
        logger.error("embedding_failed error=%s", exc)
        raise GeminiAPIError(f"Gemini embedding request failed: {exc}") from exc
    except Exception as exc:
        logger.error("embedding_failed error=%s", exc)
        raise GeminiAPIError(f"Unexpected error calling Gemini embedding API: {exc}") from exc


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
    _t0 = time.perf_counter()
    try:
        chat = _client.chats.create(model=settings.gemini_model)
        response = chat.send_message(prompt)
        logger.info("response_generated elapsed_ms=%.1f", (time.perf_counter() - _t0) * 1000)
        return response.text
    except genai_errors.APIError as exc:
        logger.error("response_failed error=%s", exc)
        raise GeminiAPIError(f"Gemini chat request failed: {exc}") from exc
    except Exception as exc:
        logger.error("response_failed error=%s", exc)
        raise GeminiAPIError(f"Unexpected error calling Gemini chat API: {exc}") from exc
