from collections.abc import Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.db.base import Base
from frontier_radar.models.collection import LLMConfigurationRecord
from frontier_radar.schemas.llm import LLMConfigurationInput


@compiles(LONGTEXT, "sqlite")
def compile_longtext_as_sqlite_text(
    _: LONGTEXT,
    __: object,
    **___: object,
) -> str:
    """Allow existing MySQL snapshot models to participate in SQLite tests."""
    return "TEXT"


@pytest.fixture
def session_factory() -> Callable[[], Session]:
    """Provide an isolated persisted configuration boundary."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[LLMConfigurationRecord.__table__])
    return sessionmaker(engine)


def configuration(model_name: str) -> LLMConfigurationInput:
    """Build non-secret user input with a hand-written expected model name."""
    return LLMConfigurationInput(
        provider_id="custom",
        provider_label="Internal compatible service",
        base_url="https://models.example.test/v1",
        model_name=model_name,
    )


def test_repository_replaces_the_single_default_configuration(
    session_factory: Callable[[], Session],
):
    """Catches repeated configuration creating stale default model rows."""
    from frontier_radar.repositories.llm import LLMConfigurationRepository

    repository = LLMConfigurationRepository(session_factory)

    first = repository.upsert_default(configuration("team-curator-1"))
    second = repository.upsert_default(configuration("team-curator-2"))

    assert (first.id, first.model_name) == (1, "team-curator-1")
    assert (second.id, second.model_name) == (1, "team-curator-2")
    assert repository.get_default() == second
