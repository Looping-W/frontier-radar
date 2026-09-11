import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.db.base import Base
from frontier_radar.models.collection import (
    ArticleFeedbackRecord,
    ArticleRankingRecord,
    ArticleRecord,
    CollectionSnapshotRecord,
    InterestProfileRecord,
    RawItemRecord,
)


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
    """Load fixed traceable data into an isolated local database."""
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "curation_articles.json").read_text(
            encoding="utf-8"
        )
    )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        session.add(InterestProfileRecord(**fixture["profile"]))
        for snapshot in fixture["snapshots"]:
            session.add(
                CollectionSnapshotRecord(
                    **{
                        **snapshot,
                        "fetched_at": datetime.fromisoformat(snapshot["fetched_at"]),
                    }
                )
            )
        for article in fixture["articles"]:
            session.add(ArticleRecord(**article))
        for raw_item in fixture["raw_items"]:
            session.add(RawItemRecord(**raw_item))
        for ranking in fixture["rankings"]:
            session.add(ArticleRankingRecord(**ranking))
        session.commit()
    return factory


def test_repository_lists_positive_rankings_in_stable_order(
    session_factory: Callable[[], Session],
):
    """Catches zero-score or unstable-ranked articles entering curation input."""
    from frontier_radar.repositories.curation import CurationRepository

    candidates = CurationRepository(session_factory).list_ranked_candidates(
        profile_id=7,
        limit=10,
    )

    assert [
        (candidate.article_id, candidate.title, candidate.score)
        for candidate in candidates
    ] == [
        (12, "Agent tools", 5),
        (10, "AI Agent guide", 3),
    ]


def test_repository_returns_raw_item_snapshot_lineage_for_a_candidate(
    session_factory: Callable[[], Session],
):
    """Catches curation detail reads that sever Phase 2 source traceability."""
    from frontier_radar.repositories.curation import CurationRepository

    context = CurationRepository(session_factory).get_article_context(
        profile_id=7,
        article_id=12,
    )

    assert context is not None
    assert context.title == "Agent tools"
    assert [
        (source.raw_item_id, source.snapshot_id, source.url)
        for source in context.sources
    ] == [
        (20, 30, "https://example.test/agent-tools"),
    ]


def test_repository_excludes_feedback_marked_articles_from_candidates_and_context(
    session_factory: Callable[[], Session],
):
    """Catches repeat curation of an article the default profile already rated."""
    from frontier_radar.repositories.curation import CurationRepository

    with session_factory() as session:
        session.add(
            ArticleFeedbackRecord(
                profile_id=7,
                article_id=12,
                decision="skip",
                recorded_at=datetime(2026, 9, 11),
            )
        )
        session.commit()

    repository = CurationRepository(session_factory)

    candidates = repository.list_ranked_candidates(profile_id=7, limit=10)
    context = repository.get_article_context(profile_id=7, article_id=12)

    assert [(candidate.article_id, candidate.score) for candidate in candidates] == [
        (10, 3)
    ]
    assert context is None
