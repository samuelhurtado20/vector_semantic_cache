"""
Unit tests for services/cache_engine.py (US-004).

These tests are fully isolated: no Gemini API key or live database required.
The DB is created in-memory using SQLite and seeded programmatically.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import numpy as np
import pytest

from services.cache_engine import calculate_cosine_similarity, find_closest_match, search_cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(question: str, response: str, embedding: list[float]):
    """Build a mock InteractionCache record."""
    record = MagicMock()
    record.question = question
    record.response = response
    record.embedding = json.dumps(embedding)
    return record


# ---------------------------------------------------------------------------
# calculate_cosine_similarity
# ---------------------------------------------------------------------------

class TestCalculateCosineSimilarity:

    def test_identical_vectors_return_one(self):
        vec = [1.0, 0.5, 0.3, 0.8]
        result = calculate_cosine_similarity(vec, vec)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_opposite_vectors_return_negative_one(self):
        vec_a = [1.0, 0.0]
        vec_b = [-1.0, 0.0]
        result = calculate_cosine_similarity(vec_a, vec_b)
        assert result == pytest.approx(-1.0, abs=1e-6)

    def test_orthogonal_vectors_return_zero(self):
        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        result = calculate_cosine_similarity(vec_a, vec_b)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_zero_norm_vector_a_returns_zero(self):
        result = calculate_cosine_similarity([0.0, 0.0], [1.0, 2.0])
        assert result == 0.0

    def test_zero_norm_vector_b_returns_zero(self):
        result = calculate_cosine_similarity([1.0, 2.0], [0.0, 0.0])
        assert result == 0.0

    def test_high_dimensional_vectors(self):
        """Simulate real 3072-dimensional embeddings with known similarity."""
        rng = np.random.default_rng(42)
        base = rng.standard_normal(3072).tolist()
        noise = (np.array(base) + rng.standard_normal(3072) * 0.01).tolist()
        result = calculate_cosine_similarity(base, noise)
        assert result > 0.99, f"Expected high similarity, got {result}"

    def test_returns_float(self):
        result = calculate_cosine_similarity([1.0, 2.0], [3.0, 4.0])
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# search_cache
# ---------------------------------------------------------------------------

class TestSearchCache:

    def _make_session(self, records: list) -> MagicMock:
        """Build a mock DB session whose get_all_interactions returns records."""
        session = MagicMock()
        # Patch at module level so search_cache picks it up
        return session

    def test_empty_db_returns_miss_with_zero_similarity(self, monkeypatch):
        monkeypatch.setattr(
            "services.cache_engine.get_all_interactions", lambda _: []
        )
        session = MagicMock()
        is_hit, record, similarity = search_cache([0.1, 0.2], session)

        assert is_hit is False
        assert record is None
        assert similarity == 0.0

    def test_cache_hit_above_threshold(self, monkeypatch):
        vec = [1.0, 0.0, 0.0]
        stored = _make_record("How does Python work?", "Python is a language.", vec)

        monkeypatch.setattr(
            "services.cache_engine.get_all_interactions", lambda _: [stored]
        )
        monkeypatch.setattr(
            "services.cache_engine.settings",
            MagicMock(similarity_threshold=0.90),
        )

        # Identical vector → similarity = 1.0 → hit
        is_hit, matched_record, similarity = search_cache(vec, MagicMock())

        assert is_hit is True
        assert matched_record is stored
        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_cache_miss_below_threshold(self, monkeypatch):
        vec_stored = [1.0, 0.0, 0.0]
        vec_query = [0.0, 1.0, 0.0]  # orthogonal → similarity = 0.0
        stored = _make_record("How does Python work?", "Python is a language.", vec_stored)

        monkeypatch.setattr(
            "services.cache_engine.get_all_interactions", lambda _: [stored]
        )
        monkeypatch.setattr(
            "services.cache_engine.settings",
            MagicMock(similarity_threshold=0.90),
        )

        is_hit, matched_record, similarity = search_cache(vec_query, MagicMock())

        assert is_hit is False
        assert matched_record is None
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_returns_best_match_among_multiple_records(self, monkeypatch):
        base_vec = [1.0, 0.0, 0.0]
        close_vec = [0.99, 0.14, 0.0]   # high similarity
        far_vec = [0.0, 1.0, 0.0]        # low similarity

        close_record = _make_record("Close question", "Close answer.", close_vec)
        far_record = _make_record("Far question", "Far answer.", far_vec)

        monkeypatch.setattr(
            "services.cache_engine.get_all_interactions",
            lambda _: [far_record, close_record],
        )
        monkeypatch.setattr(
            "services.cache_engine.settings",
            MagicMock(similarity_threshold=0.90),
        )

        is_hit, matched_record, similarity = search_cache(base_vec, MagicMock())

        assert is_hit is True
        assert matched_record is close_record
        assert similarity > 0.90


class TestFindClosestMatch:
    def test_empty_db_returns_none_and_zero_similarity(self, monkeypatch):
        monkeypatch.setattr(
            "services.cache_engine.get_all_interactions", lambda _: []
        )
        record, similarity = find_closest_match([0.1, 0.2], MagicMock())

        assert record is None
        assert similarity == 0.0

    def test_returns_closest_match_even_below_threshold(self, monkeypatch):
        vec_stored = [1.0, 0.0, 0.0]
        vec_query = [0.0, 1.0, 0.0]  # orthogonal → similarity = 0.0
        stored = _make_record("How does Python work?", "Python is a language.", vec_stored)

        monkeypatch.setattr(
            "services.cache_engine.get_all_interactions", lambda _: [stored]
        )

        matched_record, similarity = find_closest_match(vec_query, MagicMock())

        assert matched_record is stored
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_returns_best_match_among_multiple_records(self, monkeypatch):
        base_vec = [1.0, 0.0, 0.0]
        close_vec = [0.99, 0.14, 0.0]   # high similarity
        far_vec = [0.0, 1.0, 0.0]        # low similarity

        close_record = _make_record("Close question", "Close answer.", close_vec)
        far_record = _make_record("Far question", "Far answer.", far_vec)

        monkeypatch.setattr(
            "services.cache_engine.get_all_interactions",
            lambda _: [far_record, close_record],
        )

        matched_record, similarity = find_closest_match(base_vec, MagicMock())

        assert matched_record is close_record
        assert similarity > 0.90
