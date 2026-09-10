from collections.abc import Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.db.base import Base
from frontier_radar.models.collection import InterestKeywordRecord, InterestTopicRecord


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
    """Provide an isolated persistence boundary for profile tests."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(engine)


def test_repository_creates_then_reuses_the_single_default_profile(
    session_factory: Callable[[], Session],
):
    """Catches new local installs without a profile and duplicate defaults on rerun."""
    from frontier_radar.repositories.interests import InterestRepository

    repository = InterestRepository(session_factory)

    first = repository.get_default_profile()
    second = repository.get_default_profile()

    assert (first.id, first.name, first.slug) == (1, "Default", "default")
    assert (second.id, second.name, second.slug) == (1, "Default", "default")


def test_repository_upserts_a_topic_by_its_profile_scoped_normalized_name(
    session_factory: Callable[[], Session],
):
    """Catches duplicate terms caused by display-name spelling differences."""
    from frontier_radar.repositories.interests import InterestRepository

    repository = InterestRepository(session_factory)
    profile = repository.get_default_profile()

    first = repository.upsert_topic(profile.id, "AI Agent", "ai agent", 2)
    second = repository.upsert_topic(profile.id, "AI-Agent", "ai agent", 5)

    assert (first.id, first.name, first.weight) == (1, "AI Agent", 2)
    assert (second.id, second.name, second.weight) == (1, "AI-Agent", 5)
    with session_factory() as session:
        stored = session.query(InterestTopicRecord).one()
    assert (stored.profile_id, stored.name_key, stored.weight) == (
        profile.id,
        "ai agent",
        5,
    )


def test_repository_manages_profile_scoped_topics_and_keywords_in_stable_order(
    session_factory: Callable[[], Session],
):
    """Catches terms that cannot be listed, changed, or removed predictably."""
    from frontier_radar.repositories.interests import InterestRepository

    repository = InterestRepository(session_factory)
    profile = repository.get_default_profile()
    repository.upsert_topic(profile.id, "Zebra", "zebra", 1)
    repository.upsert_topic(profile.id, "AI Agent", "ai agent", 2)
    repository.upsert_keyword(profile.id, "Tool calling", "tool calling", 3)

    assert [
        (term.name, term.weight) for term in repository.list_topics(profile.id)
    ] == [
        ("AI Agent", 2),
        ("Zebra", 1),
    ]
    assert repository.update_topic(profile.id, "ai agent", 5).weight == 5
    assert repository.delete_topic(profile.id, "zebra").name == "Zebra"
    assert repository.update_topic(profile.id, "absent", 4) is None
    assert repository.delete_topic(profile.id, "absent") is None

    assert [
        (term.name, term.weight) for term in repository.list_keywords(profile.id)
    ] == [("Tool calling", 3)]
    assert repository.update_keyword(profile.id, "tool calling", 5).weight == 5
    assert repository.delete_keyword(profile.id, "tool calling").weight == 5
    with session_factory() as session:
        assert session.query(InterestTopicRecord).count() == 1
        assert session.query(InterestKeywordRecord).count() == 0
