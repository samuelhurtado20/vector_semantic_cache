"""
Unit tests for services/gemini.py (US-003).

By default these tests mock the Google GenAI SDK so no API key is required.
Tests that call the live Gemini API are marked with `@pytest.mark.integration`.
"""

from __future__ import annotations

import pytest
from pytest import MonkeyPatch

from exceptions import GeminiAPIError
from services import gemini
from services.gemini import generate_response, get_embedding


# ---------------------------------------------------------------------------
# get_embedding
# ---------------------------------------------------------------------------

class TestGetEmbedding:
    """UC-3.1: Generate Embeddings via SDK."""

    def test_returns_list_of_floats(self, monkeypatch: MonkeyPatch) -> None:
        """AC-1 / AC-2: Service returns a 3072-dimensional float list."""
        expected_embedding = [0.1] * 3072

        class FakeEmbedding:
            values = expected_embedding

        class FakeResponse:
            embeddings = [FakeEmbedding()]

        def fake_embed_content(*, model: str, contents: str):
            assert model == "gemini-embedding-001"
            return FakeResponse()

        monkeypatch.setattr(
            gemini._client.models, "embed_content", fake_embed_content
        )

        result = get_embedding("What is FastAPI?")

        assert isinstance(result, list)
        assert len(result) == 3072
        assert all(isinstance(v, float) for v in result)
        assert result == expected_embedding

    def test_raises_gemini_api_error_on_failure(self, monkeypatch: MonkeyPatch) -> None:
        from google.genai import errors as genai_errors

        def failing_embed_content(*, model: str, contents: str):
            raise genai_errors.APIError(code=500, response_json={})

        monkeypatch.setattr(
            gemini._client.models, "embed_content", failing_embed_content
        )

        with pytest.raises(GeminiAPIError):
            get_embedding("What is FastAPI?")

    @pytest.mark.integration
    def test_live_returns_list_of_floats(self) -> None:
        """Live integration test against the real Gemini API."""
        result = get_embedding("What is FastAPI?")

        assert isinstance(result, list)
        assert len(result) == 3072
        assert all(isinstance(v, float) for v in result)


# ---------------------------------------------------------------------------
# generate_response
# ---------------------------------------------------------------------------

class TestGenerateResponse:
    """UC-3.2: Generate Text Response via SDK."""

    def test_returns_string_response(self, monkeypatch: MonkeyPatch) -> None:
        """AC-3: Service returns a non-empty string response."""

        class FakeMessage:
            text = "Hola"

        class FakeChats:
            def create(self, *, model: str):
                class FakeChat:
                    def send_message(self, prompt: str) -> FakeMessage:
                        return FakeMessage()

                return FakeChat()

        class FakeClient:
            chats = FakeChats()
            models = gemini._client.models

        monkeypatch.setattr(gemini, "_client", FakeClient())

        result = generate_response("Translate hello to Spanish")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "hola" in result.lower()

    def test_raises_gemini_api_error_on_failure(self, monkeypatch: MonkeyPatch) -> None:
        from google.genai import errors as genai_errors

        class FakeChats:
            def create(self, *, model: str):
                class FakeChat:
                    def send_message(self, prompt: str):
                        raise genai_errors.APIError(code=500, response_json={})

                return FakeChat()

        class FakeClient:
            chats = FakeChats()
            models = gemini._client.models

        monkeypatch.setattr(gemini, "_client", FakeClient())

        with pytest.raises(GeminiAPIError):
            generate_response("Translate hello to Spanish")

    @pytest.mark.integration
    def test_live_returns_string_response(self) -> None:
        """Live integration test against the real Gemini API."""
        result = generate_response("Translate hello to Spanish")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "hola" in result.lower()
