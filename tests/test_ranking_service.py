import importlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class DefaultProfile:
    """Minimal default-profile identity used at the ranking service boundary."""

    id: int


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
