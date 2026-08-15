"""
Semantic Cache Engine.

Provides:
- `calculate_cosine_similarity`: Vector math using NumPy.
- `search_cache`: Linear scan over all stored embeddings to find the
  best semantic match against the incoming query embedding.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from config import settings
from database import get_all_interactions, load_embedding
from models import InteractionCache


def calculate_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute the cosine similarity between two dense vectors.

    Uses the standard formula:
        similarity = (A · B) / (||A|| * ||B||)

    Args:
        vec_a: First embedding vector.
        vec_b: Second embedding vector.

    Returns:
        A float in [0.0, 1.0]. Returns 0.0 if either vector has zero norm
        to avoid division by zero.
    """
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def _find_best_match(
    question_embedding: list[float],
    records: list[InteractionCache],
) -> tuple[InteractionCache | None, float]:
    """
    Find the stored record with the highest cosine similarity to the query.

    Args:
        question_embedding: The embedding vector of the incoming question.
        records: List of stored interaction cache records.

    Returns:
        A 2-tuple of the best matching record (or None if records is empty)
        and the highest similarity score (0.0 if records is empty).
    """
    if not records:
        return None, 0.0

    best_record: InteractionCache | None = None
    best_similarity: float = -1.0

    for record in records:
        stored_embedding = load_embedding(record)
        similarity = calculate_cosine_similarity(question_embedding, stored_embedding)

        if similarity > best_similarity:
            best_similarity = similarity
            best_record = record

    return best_record, best_similarity


def search_cache(
    question_embedding: list[float],
    db_session: Session,
) -> tuple[bool, InteractionCache | None, float]:
    """
    Search the interaction cache for the most semantically similar stored question.

    Performs a linear scan over all records in the `interaction_cache` table,
    computing cosine similarity between `question_embedding` and each stored
    embedding. Returns the record with the highest similarity score.

    Args:
        question_embedding: The embedding vector of the incoming question.
        db_session: An active SQLAlchemy session.

    Returns:
        A 3-tuple:
        - ``is_hit`` (bool): True if the best similarity >= SIMILARITY_THRESHOLD.
        - ``best_record`` (InteractionCache | None): The matching DB record on a hit,
          or None on a miss / empty DB.
        - ``best_similarity`` (float): The highest similarity score found (0.0 if DB
          is empty).
    """
    records = get_all_interactions(db_session)
    best_record, best_similarity = _find_best_match(question_embedding, records)
    is_hit = best_similarity >= settings.similarity_threshold
    return is_hit, (best_record if is_hit else None), best_similarity


def find_closest_match(
    question_embedding: list[float],
    db_session: Session,
) -> tuple[InteractionCache | None, float]:
    """
    Return the closest stored interaction regardless of the similarity threshold.

    This is a read-only helper intended for the `/similarity-search` debug
    endpoint. It never calls the LLM and never persists anything.

    Args:
        question_embedding: The embedding vector of the incoming question.
        db_session: An active SQLAlchemy session.

    Returns:
        A 2-tuple of the closest matching record (or None if the DB is empty)
        and the highest similarity score found (0.0 if the DB is empty).
    """
    records = get_all_interactions(db_session)
    return _find_best_match(question_embedding, records)
