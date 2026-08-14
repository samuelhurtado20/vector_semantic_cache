from __future__ import annotations

import json
from typing import Generator, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from config import settings
from models import Base, InteractionCache


DEFAULT_DATABASE_URL = settings.database_url
_ENGINE_CACHE: dict[str, Engine] = {}


def get_engine(database_url: Optional[str] = None) -> Engine:
    url = database_url or DEFAULT_DATABASE_URL
    if url not in _ENGINE_CACHE:
        if url.startswith("sqlite"):
            _ENGINE_CACHE[url] = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=NullPool,
                pool_pre_ping=True,
            )
        else:
            _ENGINE_CACHE[url] = create_engine(url)
    return _ENGINE_CACHE[url]


def get_session_factory(database_url: Optional[str] = None, engine: Optional[Engine] = None) -> sessionmaker[Session]:
    bound_engine = engine or get_engine(database_url)
    return sessionmaker(bind=bound_engine, autoflush=False, expire_on_commit=False)


def init_db(database_url: Optional[str] = None) -> Engine:
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_db_session(database_url: Optional[str] = None) -> Session:
    return get_session_factory(database_url)()


def save_interaction(session: Session, question: str, response: str, embedding: List[float]) -> InteractionCache:
    record = InteractionCache(question=question, response=response, embedding=json.dumps(list(embedding)))
    session.add(record)
    return record


def get_all_interactions(session: Session) -> List[InteractionCache]:
    return session.query(InteractionCache).order_by(InteractionCache.created_at.desc()).all()


def get_latest_interaction(session: Session) -> Optional[InteractionCache]:
    return session.query(InteractionCache).order_by(InteractionCache.created_at.desc()).first()


def load_embedding(record: InteractionCache) -> List[float]:
    return json.loads(record.embedding)

