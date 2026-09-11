import importlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.db.base import Base
from frontier_radar.models.collection import (
    ArticleFeedbackRecord,
    ArticleRankingRecord,
    ArticleRecord,
    CollectionSnapshotRecord,
    InterestKeywordRecord,
    InterestProfileRecord,
    InterestTopicRecord,
    RawItemRecord,
)
from frontier_radar.schemas.ranking import RankedArticle


@dataclass(frozen=True)
class Adjustment:
    """The repository-facing adjustment value expected from ranking service."""

    rule_id: int
    kind: str
    adjustment: int


@compiles(LONGTEXT, "sqlite")
def compile_longtext_as_sqlite_text(
    _: LONGTEXT,
    __: object,
    **___: object,
) -> str:
    """Allow the existing MySQL snapshot model to participate in SQLite tests."""
    return "TEXT"


@pytest.fixture
def session_factory() -> Callable[[], Session]:
    """Provide articles and immutable raw-item lineage for ranking persistence."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        snapshot = CollectionSnapshotRecord(
            id=1,
            source="hacker_news",
            endpoint="item/101",
            fetched_at=datetime(2026, 9, 10, tzinfo=UTC),
            status_code=200,
            content_type="application/json",
            raw_body="{}",
        )
        profile = InterestProfileRecord(id=1, name="Default", slug="default")
        first_article = ArticleRecord(
            id=1,
            title="Canonical article title",
            title_key="canonical article title",
            normalized_url="https://example.com/one",
            published_at=None,
        )
        second_article = ArticleRecord(
            id=2,
            title="AI Agent overview",
            title_key="ai agent overview",
            normalized_url="https://example.com/two",
            published_at=None,
        )
        session.add_all(
            [
                snapshot,
                profile,
                first_article,
                second_article,
                InterestTopicRecord(
                    profile_id=1,
                    name="AI Agent",
                    name_key="ai agent",
                    weight=3,
                ),
                InterestKeywordRecord(
                    profile_id=1,
                    name="Tool calling",
                    name_key="tool calling",
                    weight=2,
                ),
                RawItemRecord(
                    snapshot_id=1,
                    article_id=1,
                    source="hacker_news",
                    source_item_id="101",
                    title="Tool calling raw source title",
                    url="https://example.com/one",
                    normalized_url="https://example.com/one",
                    published_at=None,
                ),
            ]
        )
        session.commit()
    return factory


def test_repository_reads_traceable_ranking_inputs_and_replaces_profile_scores(
    session_factory: Callable[[], Session],
):
    """Catches scoring writes that duplicate rankings or alter article lineage."""
    try:
        module = importlib.import_module("frontier_radar.repositories.ranking")
    except ModuleNotFoundError:
        pytest.fail("Phase 3 ranking repository has not been implemented")
    RankingRepository = module.RankingRepository
    repository = RankingRepository(session_factory)

    rules = repository.list_rules(1)
    articles = repository.list_articles()
    repository.replace_rankings(
        1,
        [
            RankedArticle(article_id=1, title="Canonical article title", score=2),
            RankedArticle(article_id=2, title="AI Agent overview", score=3),
        ],
    )
    repository.replace_rankings(
        1,
        [
            RankedArticle(article_id=1, title="Canonical article title", score=5),
            RankedArticle(article_id=2, title="AI Agent overview", score=3),
        ],
    )

    assert [(rule.name_key, rule.weight) for rule in rules] == [
        ("ai agent", 3),
        ("tool calling", 2),
    ]
    assert [(article.article_id, article.source_titles) for article in articles] == [
        (1, ["Tool calling raw source title"]),
        (2, []),
    ]
    with session_factory() as session:
        rankings = session.scalars(
            select(ArticleRankingRecord).order_by(ArticleRankingRecord.article_id)
        ).all()
        raw_item = session.scalar(select(RawItemRecord))
        snapshot_count = session.scalar(
            select(func.count()).select_from(CollectionSnapshotRecord)
        )
    assert [(ranking.article_id, ranking.score) for ranking in rankings] == [
        (1, 5),
        (2, 3),
    ]
    assert (raw_item.article_id, raw_item.snapshot_id) == (1, 1)
    assert snapshot_count == 1


def test_repository_reads_feedback_articles_and_replaces_only_adjustments(
    session_factory: Callable[[], Session],
):
    """Catches hidden manual-weight writes or untraceable feedback scoring input."""
    module = importlib.import_module("frontier_radar.repositories.ranking")
    repository = module.RankingRepository(session_factory)
    with session_factory() as session:
        session.add_all(
            [
                ArticleFeedbackRecord(
                    profile_id=1,
                    article_id=1,
                    decision="like",
                    recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                ArticleFeedbackRecord(
                    profile_id=1,
                    article_id=2,
                    decision="skip",
                    recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
            ]
        )
        session.commit()

    feedback_articles = repository.list_feedback_articles(1)
    repository.replace_feedback_adjustments(
        1,
        [
            Adjustment(rule_id=1, kind="topic", adjustment=2),
            Adjustment(rule_id=1, kind="keyword", adjustment=-2),
        ],
    )

    assert [
        (article.article_id, article.decision, article.source_titles)
        for article in feedback_articles
    ] == [
        (1, "like", ["Tool calling raw source title"]),
        (2, "skip", []),
    ]
    with session_factory() as session:
        topic = session.scalar(select(InterestTopicRecord))
        keyword = session.scalar(select(InterestKeywordRecord))
        raw_item = session.scalar(select(RawItemRecord))
    assert (topic.weight, topic.feedback_adjustment) == (3, 2)
    assert (keyword.weight, keyword.feedback_adjustment) == (2, -2)
    assert raw_item.article_id == 1
