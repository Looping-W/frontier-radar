import importlib
from datetime import UTC, datetime

import pytest

from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot
from frontier_radar.schemas.normalization import NormalizationResult
from frontier_radar.schemas.ranking import RankingResult


def collection_result() -> CollectionResult:
    """Build one offline collection result for refresh-service tests."""
    return CollectionResult(
        source="hacker_news",
        item_count=1,
        snapshots=[
            CollectionSnapshot(
                source="hacker_news",
                endpoint="topstories",
                fetched_at=datetime(2026, 9, 10, tzinfo=UTC),
                status_code=200,
                content_type="application/json",
                raw_body="[]",
            )
        ],
    )


def test_refresh_service_runs_existing_stages_in_order():
    """Catches a shortcut command that skips or reorders the fixed pipeline."""
    try:
        schema_module = importlib.import_module("frontier_radar.schemas.refresh")
        service_module = importlib.import_module("frontier_radar.services.refresh")
    except ModuleNotFoundError:
        pytest.fail("Refresh service contracts have not been implemented")
    RefreshResult = schema_module.RefreshResult
    RefreshService = service_module.RefreshService
    calls: list[str] = []

    class FakeCollectionService:
        def collect_all(self) -> list[CollectionResult]:
            calls.append("collect")
            return [collection_result()]

    class FakeNormalizationService:
        def normalize(self) -> NormalizationResult:
            calls.append("normalize")
            return NormalizationResult(
                snapshots_processed=1,
                raw_items_parsed=1,
                raw_items_created=1,
                articles_created=1,
                merged_items=0,
            )

    class FakeRankingService:
        def rank_default_profile(self) -> RankingResult:
            calls.append("rank")
            return RankingResult(articles_scored=1, rankings=[])

    result = RefreshService(
        FakeCollectionService(),
        FakeNormalizationService(),
        FakeRankingService(),
    ).refresh()

    assert calls == ["collect", "normalize", "rank"]
    assert result == RefreshResult(
        collection_results=[collection_result()],
        normalization=NormalizationResult(
            snapshots_processed=1,
            raw_items_parsed=1,
            raw_items_created=1,
            articles_created=1,
            merged_items=0,
        ),
        ranking=RankingResult(articles_scored=1, rankings=[]),
    )


def test_refresh_service_stops_after_collection_failure():
    """Catches refresh runs that hide a collection error by continuing downstream."""
    try:
        service_module = importlib.import_module("frontier_radar.services.refresh")
    except ModuleNotFoundError:
        pytest.fail("Refresh service contracts have not been implemented")
    RefreshService = service_module.RefreshService
    calls: list[str] = []

    class FailingCollectionService:
        def collect_all(self) -> list[CollectionResult]:
            calls.append("collect")
            raise RuntimeError("network unavailable")

    class UnexpectedService:
        def normalize(self) -> NormalizationResult:
            calls.append("normalize")
            raise AssertionError("Normalization must not run")

        def rank_default_profile(self) -> RankingResult:
            calls.append("rank")
            raise AssertionError("Ranking must not run")

    with pytest.raises(RuntimeError, match="network unavailable"):
        RefreshService(
            FailingCollectionService(),
            UnexpectedService(),
            UnexpectedService(),
        ).refresh()

    assert calls == ["collect"]
