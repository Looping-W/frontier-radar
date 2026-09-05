import importlib
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.db.base import Base
from frontier_radar.models.collection import (
    ArticleRecord,
    CollectionSnapshotRecord,
    RawItemRecord,
)
from frontier_radar.schemas.normalization import ParsedRawItem


@compiles(LONGTEXT, "sqlite")
def compile_longtext_as_sqlite_text(
    _: LONGTEXT,
    __: object,
    **___: object,
) -> str:
    """Allow the existing MySQL snapshot model to participate in local tests."""
    return "TEXT"


def load_repository() -> type:
    """Return the persistence boundary or clearly report the missing contract."""
    module = importlib.import_module("frontier_radar.repositories.normalization")
    repository = getattr(module, "NormalizationRepository", None)
    if repository is None:
        pytest.fail("NormalizationRepository has not been implemented")
    return repository


@pytest.fixture
def session_factory() -> Callable[[], Session]:
    """Provide a real isolated database with persisted source snapshots."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        session.add_all(
            [
                CollectionSnapshotRecord(
                    id=snapshot_id,
                    source="hacker_news",
                    endpoint=f"item/{snapshot_id}",
                    fetched_at=datetime(2026, 9, 1, tzinfo=UTC),
                    status_code=200,
                    content_type="application/json",
                    raw_body="{}",
                )
                for snapshot_id in range(1, 5)
            ]
        )
        session.commit()
    return factory


def raw_item(
    snapshot_id: int,
    source: str,
    source_item_id: str,
    title: str,
    title_key: str,
    normalized_url: str | None,
) -> ParsedRawItem:
    return ParsedRawItem(
        snapshot_id=snapshot_id,
        source=source,
        source_item_id=source_item_id,
        title=title,
        title_key=title_key,
        url=normalized_url,
        normalized_url=normalized_url,
        published_at=datetime(2026, 9, 1, tzinfo=UTC),
    )


def stored_counts(session_factory: Callable[[], Session]) -> tuple[int, int]:
    with session_factory() as session:
        return (
            session.scalar(select(func.count()).select_from(ArticleRecord)) or 0,
            session.scalar(select(func.count()).select_from(RawItemRecord)) or 0,
        )


def test_repository_prefers_same_source_item_id_over_url_and_title(
    session_factory: Callable[[], Session],
):
    """Catches repeat HN records that create a second article after metadata changes."""
    repository = load_repository()(session_factory)

    result = repository.save_items(
        [
            raw_item(
                1,
                "hacker_news",
                "101",
                "First unrelated title",
                "first unrelated title",
                "https://example.com/first",
            ),
            raw_item(
                2,
                "hacker_news",
                "101",
                "Completely different title",
                "completely different title",
                "https://example.com/second",
            ),
        ]
    )

    assert (result.raw_items_created, result.articles_created, result.merged_items) == (
        2,
        1,
        1,
    )
    assert stored_counts(session_factory) == (1, 2)
    with session_factory() as session:
        article_ids = session.scalars(select(RawItemRecord.article_id)).all()
    assert article_ids == [1, 1]


def test_repository_merges_cross_source_items_with_same_normalized_url(
    session_factory: Callable[[], Session],
):
    """Catches cross-source duplicates missed because source IDs differ."""
    repository = load_repository()(session_factory)

    result = repository.save_items(
        [
            raw_item(
                1,
                "hacker_news",
                "101",
                "A linked project",
                "a linked project",
                "https://example.com/project?a=1&b=2",
            ),
            raw_item(
                2,
                "arxiv",
                "2609.00001",
                "A research paper with a different title",
                "a research paper with a different title",
                "https://example.com/project?a=1&b=2",
            ),
        ]
    )

    assert (result.articles_created, result.merged_items) == (1, 1)
    assert stored_counts(session_factory) == (1, 2)


def test_repository_merges_similar_titles_when_source_id_and_url_do_not_match(
    session_factory: Callable[[], Session],
):
    """Catches title-level duplicates that have neither a shared source ID nor URL."""
    repository = load_repository()(session_factory)

    result = repository.save_items(
        [
            raw_item(
                1,
                "hacker_news",
                "101",
                "Agent systems for software engineering",
                "agent systems for software engineering",
                None,
            ),
            raw_item(
                2,
                "arxiv",
                "2609.00001",
                "Agent system for software engineering",
                "agent system for software engineering",
                None,
            ),
        ]
    )

    assert (result.articles_created, result.merged_items) == (1, 1)
    assert stored_counts(session_factory) == (1, 2)


def test_repository_skips_an_item_already_persisted_from_same_snapshot(
    session_factory: Callable[[], Session],
):
    """Catches a repeat normalization command that inserts duplicate raw items."""
    repository = load_repository()(session_factory)
    item = raw_item(
        1,
        "hacker_news",
        "101",
        "An agent project",
        "an agent project",
        "https://example.com/agent",
    )

    repository.save_items([item])
    repeat_result = repository.save_items([item])

    assert (repeat_result.raw_items_created, repeat_result.articles_created) == (0, 0)
    assert stored_counts(session_factory) == (1, 1)


def test_repository_lists_only_successful_supported_snapshots_in_id_order(
    session_factory: Callable[[], Session],
):
    """Catches normalization attempts on failed or unsupported source snapshots."""
    with session_factory() as session:
        session.add_all(
            [
                CollectionSnapshotRecord(
                    id=5,
                    source="arxiv",
                    endpoint="query",
                    fetched_at=datetime(2026, 9, 1, tzinfo=UTC),
                    status_code=500,
                    content_type="application/atom+xml",
                    raw_body="<feed />",
                ),
                CollectionSnapshotRecord(
                    id=6,
                    source="other_source",
                    endpoint="query",
                    fetched_at=datetime(2026, 9, 1, tzinfo=UTC),
                    status_code=200,
                    content_type="application/json",
                    raw_body="{}",
                ),
            ]
        )
        session.commit()

    snapshots = load_repository()(session_factory).list_snapshots()

    assert [snapshot.id for snapshot in snapshots] == [1, 2, 3, 4]
