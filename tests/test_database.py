"""
Unit tests for database.py (US-002).

Uses pytest fixtures and an isolated SQLite file per test.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from database import get_all_interactions, get_session_factory, init_db, save_interaction


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
def engine(database_url: str):
    """Create and dispose the SQLAlchemy engine for a test."""
    engine = init_db(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(database_url: str, engine) -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session with automatic cleanup."""
    SessionLocal = get_session_factory(database_url, engine=engine)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


class TestInitDb:
    def test_missing_table_raises_operational_error(self, engine) -> None:
        with pytest.raises(OperationalError):
            with engine.connect() as connection:
                connection.execute(text("SELECT * FROM missing_table"))

    def test_creates_interaction_cache_table(self, engine) -> None:
        with engine.connect() as connection:
            assert engine.dialect.has_table(connection, "interaction_cache")


class TestSaveInteraction:
    def test_persists_record(self, session: Session) -> None:
        saved = save_interaction(
            session,
            question="What is FastAPI?",
            response="A web framework.",
            embedding=[0.1, 0.2, 0.3],
        )
        session.commit()
        session.refresh(saved)

        assert saved.id is not None
        assert saved.question == "What is FastAPI?"
        assert saved.response == "A web framework."
        assert saved.embedding == "[0.1, 0.2, 0.3]"

    def test_get_all_interactions_returns_records_newest_first(
        self, session: Session
    ) -> None:
        save_interaction(session, "Question 1?", "Answer 1.", [0.1])
        save_interaction(session, "Question 2?", "Answer 2.", [0.2])
        session.commit()

        records = get_all_interactions(session)

        assert len(records) == 2
        assert records[0].question == "Question 2?"
        assert records[1].question == "Question 1?"
