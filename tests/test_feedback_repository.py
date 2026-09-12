import importlib
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.db.base import Base
from frontier_radar.models.collection import (
    ArticleRankingRecord,
    ArticleRecord,
    CollectionSnapshotRecord,
    InterestProfileRecord,
    RawItemRecord,
)
from frontier_radar.schemas.feedback import FeedbackDecision, FeedbackInput


@compiles(LONGTEXT, "sqlite")
def compile_longtext_as_sqlite_text(
    _: LONGTEXT,
    __: object,
    **___: object,
) -> str:
    """Allow the existing MySQL snapshot model in focused SQLite tests."""
    return "TEXT"


@pytest.fixture
def session_factory() -> Callable[[], Session]:
    """Provide positively ranked articles and immutable source lineage."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        session.add_all(
            [
                InterestProfileRecord(id=1, name="Default", slug="default"),
                CollectionSnapshotRecord(
                    id=1,
                    source="hacker_news",
                    endpoint="item/1",
                    fetched_at=datetime(2026, 9, 11, tzinfo=UTC),
                    status_code=200,
                    content_type="application/json",
                    raw_body="{}",
                ),
                ArticleRecord(
                    id=1,
                    title="AI agent guide",
                    title_key="ai agent guide",
                    normalized_url="https://example.com/one",
                    published_at=None,
                ),
                ArticleRecord(
                    id=2,
                    title="Tool calling guide",
                    title_key="tool calling guide",
                    normalized_url="https://example.com/two",
                    published_at=None,
                ),
                ArticleRankingRecord(profile_id=1, article_id=1, score=3),
                ArticleRankingRecord(profile_id=1, article_id=2, score=2),
                RawItemRecord(
                    snapshot_id=1,
                    article_id=1,
                    source="hacker_news",
                    source_item_id="1",
                    title="AI agent guide",
                    url="https://example.com/one",
                    normalized_url="https://example.com/one",
                    published_at=None,
                ),
            ]
        )
        session.commit()
    return factory


def _repository(session_factory: Callable[[], Session]):
    """Load the expected persistence boundary without hiding missing behavior."""
    try:
        module = importlib.import_module("frontier_radar.repositories.feedback")
    except ModuleNotFoundError:
        pytest.fail("Phase 5 feedback repository has not been implemented")
    return module.FeedbackRepository(session_factory)


def test_repository_upserts_current_feedback_without_changing_source_lineage(
    session_factory: Callable[[], Session],
):
    """Catches duplicate learning signals or feedback writes that alter articles."""
    repository = _repository(session_factory)
    first_time = datetime(2026, 9, 11, 8, tzinfo=UTC)
    later_time = datetime(2026, 9, 11, 9, tzinfo=UTC)

    first = repository.upsert_feedback(
        1,
        FeedbackInput(article_id=1, decision="like"),
        first_time,
    )
    repeated = repository.upsert_feedback(
        1,
        FeedbackInput(article_id=1, decision="like"),
        later_time,
    )
    changed = repository.upsert_feedback(
        1,
        FeedbackInput(article_id=1, decision="skip"),
        later_time,
    )

    assert first.decision is FeedbackDecision.LIKE
    assert repeated.recorded_at == first_time
    assert changed.decision is FeedbackDecision.SKIP
    assert changed.recorded_at == later_time
    assert repository.list_feedback(1) == [changed]
    with session_factory() as session:
        article = session.scalar(select(ArticleRecord).where(ArticleRecord.id == 1))
        raw_item = session.scalar(select(RawItemRecord).where(RawItemRecord.id == 1))
        snapshot = session.scalar(
            select(CollectionSnapshotRecord).where(CollectionSnapshotRecord.id == 1)
        )
    assert article.title == "AI agent guide"
    assert raw_item.article_id == 1
    assert snapshot.raw_body == "{}"


def test_repository_lists_feedback_in_article_id_order(
    session_factory: Callable[[], Session],
):
    """Catches non-deterministic feedback ordering across database backends."""
    repository = _repository(session_factory)
    timestamp = datetime(2026, 9, 11, tzinfo=UTC)

    repository.upsert_feedback(
        1, FeedbackInput(article_id=2, decision="skip"), timestamp
    )
    repository.upsert_feedback(
        1, FeedbackInput(article_id=1, decision="like"), timestamp
    )

    feedback_items = repository.list_feedback(1)

    assert [feedback.article_id for feedback in feedback_items] == [1, 2]
    assert [feedback.title for feedback in feedback_items] == [
        "AI agent guide",
        "Tool calling guide",
    ]


def test_repository_removes_current_feedback_without_changing_source_lineage(
    session_factory: Callable[[], Session],
):
    """Catches undo that leaves feedback active or deletes article provenance."""
    repository = _repository(session_factory)
    repository.upsert_feedback(
        1,
        FeedbackInput(article_id=1, decision="like"),
        datetime(2026, 9, 11, tzinfo=UTC),
    )

    removed = repository.delete_feedback(1, 1)

    assert removed is not None
    assert removed.article_id == 1
    assert removed.title == "AI agent guide"
    assert repository.list_feedback(1) == []
    with session_factory() as session:
        raw_item = session.scalar(select(RawItemRecord).where(RawItemRecord.id == 1))
        snapshot = session.scalar(
            select(CollectionSnapshotRecord).where(CollectionSnapshotRecord.id == 1)
        )
    assert raw_item.article_id == 1
    assert snapshot.raw_body == "{}"


def test_repository_removes_all_feedback_without_changing_source_lineage(
    session_factory: Callable[[], Session],
):
    """Catches reset that removes provenance instead of only current feedback."""
    repository = _repository(session_factory)
    timestamp = datetime(2026, 9, 11, tzinfo=UTC)
    repository.upsert_feedback(
        1, FeedbackInput(article_id=1, decision="like"), timestamp
    )
    repository.upsert_feedback(
        1, FeedbackInput(article_id=2, decision="skip"), timestamp
    )

    removed_count = repository.delete_all_feedback(1)

    assert removed_count == 2
    assert repository.list_feedback(1) == []
    with session_factory() as session:
        article = session.scalar(select(ArticleRecord).where(ArticleRecord.id == 1))
        raw_item = session.scalar(select(RawItemRecord).where(RawItemRecord.id == 1))
        snapshot = session.scalar(
            select(CollectionSnapshotRecord).where(CollectionSnapshotRecord.id == 1)
        )
    assert article.title == "AI agent guide"
    assert raw_item.article_id == 1
    assert snapshot.raw_body == "{}"


def test_repository_reset_keeps_feedback_for_other_profiles(
    session_factory: Callable[[], Session],
):
    """Catches reset that clears feedback belonging to another profile."""
    repository = _repository(session_factory)
    timestamp = datetime(2026, 9, 11, tzinfo=UTC)
    with session_factory() as session:
        session.add(InterestProfileRecord(id=2, name="Other", slug="other"))
        session.commit()
    repository.upsert_feedback(
        1, FeedbackInput(article_id=1, decision="like"), timestamp
    )
    repository.upsert_feedback(
        2, FeedbackInput(article_id=2, decision="skip"), timestamp
    )

    removed_count = repository.delete_all_feedback(1)

    assert removed_count == 1
    assert repository.list_feedback(1) == []
    assert [feedback.article_id for feedback in repository.list_feedback(2)] == [2]


def test_repository_recognizes_only_current_positive_profile_rankings(
    session_factory: Callable[[], Session],
):
    """Catches profile-crossing feedback checks or feedback on zero scores."""
    repository = _repository(session_factory)
    with session_factory() as session:
        session.add_all(
            [
                InterestProfileRecord(id=2, name="Other", slug="other"),
                ArticleRecord(
                    id=3,
                    title="Unranked article",
                    title_key="unranked article",
                    normalized_url=None,
                    published_at=None,
                ),
                ArticleRankingRecord(profile_id=2, article_id=1, score=9),
                ArticleRankingRecord(profile_id=1, article_id=3, score=0),
            ]
        )
        session.commit()

    assert repository.has_positive_ranking(1, 1) is True
    assert repository.has_positive_ranking(1, 2) is True
    assert repository.has_positive_ranking(1, 3) is False
    assert repository.has_positive_ranking(1, 99) is False
    assert repository.has_positive_ranking(2, 1) is True
