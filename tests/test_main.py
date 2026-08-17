"""
FastAPI endpoint integration tests for main.py (US-005, US-006, US-007).

Uses TestClient with an isolated SQLite database per test (via dependency
override) and monkeypatched Gemini service calls so no live API key or
network access is required.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import main
from database import get_db, get_session_factory, init_db


EMBEDDING_DIM = 3072


def _make_embedding(seed: float) -> list[float]:
    """Build a deterministic embedding vector for tests."""
    vector = [0.0] * EMBEDDING_DIM
    vector[0] = seed
    return vector


@pytest.fixture
def database_url() -> Generator[str, None, None]:
    """Provide an isolated SQLite database file per test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    database_url = f"sqlite:///{db_path}"
    yield database_url
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(database_url: str) -> Generator[TestClient, None, None]:
    """Provide a TestClient wired to an isolated database via dependency override."""
    engine = init_db(database_url)
    session_factory = get_session_factory(database_url, engine=engine)

    def override_get_db() -> Generator:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    main.app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


class TestHealthEndpoint:
    def test_returns_ok_status_and_threshold(self, client: TestClient) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert isinstance(body["threshold"], float)


class TestChatEndpoint:
    def test_cache_miss_calls_llm_and_persists(self, client: TestClient, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(main, "get_embedding", lambda text: _make_embedding(1.0))
        monkeypatch.setattr(main, "generate_response", lambda prompt: "Paris is the capital of France.")

        response = client.post("/chat", json={"question": "What is the capital of France?"})

        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "llm"
        assert body["current_question"] == "What is the capital of France?"
        assert body["response"] == "Paris is the capital of France."
        assert body["saved_question"] is None

    def test_cache_hit_returns_saved_answer(self, client: TestClient, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(main, "get_embedding", lambda text: _make_embedding(1.0))
        monkeypatch.setattr(main, "generate_response", lambda prompt: "Paris is the capital of France.")

        first = client.post("/chat", json={"question": "What is the capital of France?"})
        assert first.json()["source"] == "llm"

        second = client.post("/chat", json={"question": "What's the capital city of France?"})

        assert second.status_code == 200
        body = second.json()
        assert body["source"] == "semantic_cache"
        assert body["saved_question"] == "What is the capital of France?"
        assert body["response"] == "Paris is the capital of France."
        assert body["similarity_percentage"] == pytest.approx(1.0)

    def test_missing_question_returns_422(self, client: TestClient) -> None:
        response = client.post("/chat", json={})

        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"

    def test_empty_question_returns_422(self, client: TestClient) -> None:
        response = client.post("/chat", json={"question": ""})

        assert response.status_code == 422


class TestQuestionsEndpoint:
    def test_returns_empty_list_when_no_interactions(self, client: TestClient) -> None:
        response = client.get("/questions")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_saved_interactions_newest_first(self, client: TestClient, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(main, "get_embedding", lambda text: _make_embedding(1.0))
        monkeypatch.setattr(main, "generate_response", lambda prompt: "First answer.")
        client.post("/chat", json={"question": "First question?"})

        monkeypatch.setattr(main, "get_embedding", lambda text: _make_embedding(-1.0))
        monkeypatch.setattr(main, "generate_response", lambda prompt: "Second answer.")
        client.post("/chat", json={"question": "Second question?"})

        response = client.get("/questions")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["question"] == "Second question?"
        assert body[1]["question"] == "First question?"
        assert "embedding" not in body[0]


class TestSimilaritySearchEndpoint:
    def test_returns_null_match_when_cache_empty(self, client: TestClient, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(main, "get_embedding", lambda text: _make_embedding(1.0))

        response = client.post("/similarity-search", json={"question": "Anything?"})

        assert response.status_code == 200
        body = response.json()
        assert body["saved_question"] is None
        assert body["saved_response"] is None
        assert body["similarity_percentage"] == 0.0

    def test_does_not_call_llm_or_persist(self, client: TestClient, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(main, "get_embedding", lambda text: _make_embedding(1.0))

        def fail_if_called(prompt: str) -> str:
            raise AssertionError("generate_response should not be called by similarity-search")

        monkeypatch.setattr(main, "generate_response", fail_if_called)

        client.post("/similarity-search", json={"question": "Anything?"})
        history = client.get("/questions")

        assert history.json() == []

    def test_returns_closest_match_below_threshold(self, client: TestClient, monkeypatch: MonkeyPatch) -> None:
        # Stored vector has component only at index 0; query vector has components
        # at both index 0 and index 1, making cosine similarity strictly between 0 and 1.
        stored_emb = [0.0] * EMBEDDING_DIM
        stored_emb[0] = 1.0
        monkeypatch.setattr(main, "get_embedding", lambda text: list(stored_emb))
        monkeypatch.setattr(main, "generate_response", lambda prompt: "Stored answer.")
        client.post("/chat", json={"question": "Stored question?"})

        partial_emb = [0.0] * EMBEDDING_DIM
        partial_emb[0] = 1.0
        partial_emb[1] = 1.0
        monkeypatch.setattr(main, "get_embedding", lambda text: list(partial_emb))
        response = client.post("/similarity-search", json={"question": "Somewhat related?"})

        assert response.status_code == 200
        body = response.json()
        assert body["saved_question"] == "Stored question?"
        assert body["saved_response"] == "Stored answer."
        assert 0.0 < body["similarity_percentage"] < 1.0
