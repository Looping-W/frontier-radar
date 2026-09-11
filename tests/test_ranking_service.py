import importlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class DefaultProfile:
    """Minimal default-profile identity used at the ranking service boundary."""

    id: int


@dataclass
class FeedbackArticle:
    """A rated article returned by the feedback-aware ranking boundary."""

    article_id: int
    title: str
    source_titles: list[str]
    decision: str


def test_service_scores_fixture_articles_with_stable_order_and_once_per_rule():
    """Catches non-deterministic ranking or duplicate weights from raw titles."""
    try:
        schema_module = importlib.import_module("frontier_radar.schemas.ranking")
        service_module = importlib.import_module("frontier_radar.services.ranking")
    except ModuleNotFoundError:
        pytest.fail("Phase 3 ranking service contracts have not been implemented")
    RankableArticle = schema_module.RankableArticle
    RankedArticle = schema_module.RankedArticle
    RankingRule = schema_module.RankingRule
    RankingService = service_module.RankingService

    article_payloads = json.loads(
        (Path(__file__).parent / "fixtures" / "ranking_articles.json").read_text(
            encoding="utf-8"
        )
    )

    class FakeProfileRepository:
        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

    class FakeRankingRepository:
        def __init__(self) -> None:
            self.persisted: tuple[int, list[object]] | None = None
            self.persisted_adjustments: tuple[int, list[object]] | None = None

        def list_rules(self, profile_id: int) -> list[object]:
            assert profile_id == 7
            return [
                RankingRule(name="AI Agent", name_key="ai agent", weight=3),
                RankingRule(name="Tool calling", name_key="tool calling", weight=2),
            ]

        def list_articles(self) -> list[object]:
            return [
                RankableArticle.model_validate(payload) for payload in article_payloads
            ]

        def list_feedback_articles(self, profile_id: int) -> list[object]:
            assert profile_id == 7
            return []

        def replace_feedback_adjustments(
            self, profile_id: int, adjustments: list[object]
        ) -> None:
            self.persisted_adjustments = (profile_id, adjustments)

        def replace_rankings(self, profile_id: int, rankings: list[object]) -> None:
            self.persisted = (profile_id, rankings)

    repository = FakeRankingRepository()
    service = RankingService(FakeProfileRepository(), repository)

    result = service.rank_default_profile()

    assert result.articles_scored == 4
    assert result.rankings == [
        RankedArticle(article_id=12, title="AI agent calls external tools", score=5),
        RankedArticle(article_id=10, title="AI Agent guide", score=3),
        RankedArticle(article_id=11, title="Tool calling patterns", score=2),
    ]
    assert repository.persisted == (
        7,
        [
            RankedArticle(
                article_id=12, title="AI agent calls external tools", score=5
            ),
            RankedArticle(article_id=10, title="AI Agent guide", score=3),
            RankedArticle(article_id=11, title="Tool calling patterns", score=2),
            RankedArticle(article_id=13, title="Database migration notes", score=0),
        ],
    )
    assert repository.persisted_adjustments == (7, [])


def test_service_derives_bounded_feedback_adjustments_and_hides_seen_articles():
    """Catches feedback drift, ignored learning signals, or repeat recommendations."""
    try:
        schema_module = importlib.import_module("frontier_radar.schemas.ranking")
        service_module = importlib.import_module("frontier_radar.services.ranking")
    except ModuleNotFoundError:
        pytest.fail("Phase 5 feedback-aware ranking has not been implemented")
    RankableArticle = schema_module.RankableArticle
    RankedArticle = schema_module.RankedArticle
    RankingRule = schema_module.RankingRule
    RankingService = service_module.RankingService

    class FakeProfileRepository:
        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

    class FakeRankingRepository:
        def __init__(self) -> None:
            self.persisted_rankings: list[object] | None = None
            self.persisted_adjustments: list[object] | None = None

        def list_rules(self, profile_id: int) -> list[object]:
            assert profile_id == 7
            return [
                RankingRule(
                    rule_id=1,
                    kind="topic",
                    name="AI Agent",
                    name_key="ai agent",
                    weight=3,
                    feedback_adjustment=0,
                ),
                RankingRule(
                    rule_id=2,
                    kind="keyword",
                    name="Tool calling",
                    name_key="tool calling",
                    weight=4,
                    feedback_adjustment=0,
                ),
            ]

        def list_articles(self) -> list[object]:
            return [
                RankableArticle(
                    article_id=10,
                    title="AI agent deployment guide",
                    source_titles=[],
                ),
                RankableArticle(
                    article_id=11,
                    title="Tool calling deployment guide",
                    source_titles=[],
                ),
            ]

        def list_feedback_articles(self, profile_id: int) -> list[FeedbackArticle]:
            assert profile_id == 7
            return [
                *[
                    FeedbackArticle(
                        article_id=article_id,
                        title="AI agent article",
                        source_titles=[],
                        decision="like",
                    )
                    for article_id in (1, 2, 3)
                ],
                *[
                    FeedbackArticle(
                        article_id=article_id,
                        title="Tool calling article",
                        source_titles=[],
                        decision="skip",
                    )
                    for article_id in (4, 5, 6)
                ],
            ]

        def replace_feedback_adjustments(
            self, profile_id: int, adjustments: list[object]
        ) -> None:
            assert profile_id == 7
            self.persisted_adjustments = adjustments

        def replace_rankings(self, profile_id: int, rankings: list[object]) -> None:
            assert profile_id == 7
            self.persisted_rankings = rankings

    repository = FakeRankingRepository()
    result = RankingService(FakeProfileRepository(), repository).rank_default_profile()

    assert [
        (adjustment.rule_id, adjustment.kind, adjustment.adjustment)
        for adjustment in repository.persisted_adjustments
    ] == [(1, "topic", 2), (2, "keyword", -2)]
    assert repository.persisted_rankings == [
        RankedArticle(article_id=10, title="AI agent deployment guide", score=5),
        RankedArticle(article_id=11, title="Tool calling deployment guide", score=2),
    ]
    assert result.rankings == repository.persisted_rankings
