import importlib
from datetime import UTC, datetime

import pytest

from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot


def collection_result(source: str, query: str | None = None) -> CollectionResult:
    return CollectionResult(
        source=source,
        query=query,
        item_count=1,
        snapshots=[
            CollectionSnapshot(
                source=source,
                endpoint="test",
                query=query,
                fetched_at=datetime(2026, 9, 1, tzinfo=UTC),
                status_code=200,
                content_type="application/json",
                raw_body="{}",
            )
        ],
    )


class FakeHackerNewsCollector:
    def collect(self) -> CollectionResult:
        return collection_result("hacker_news")


class FakeArxivCollector:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def collect(self, query: str) -> CollectionResult:
        self.queries.append(query)
        return collection_result("arxiv", query)


class InMemorySnapshotRepository:
    def __init__(self) -> None:
        self.saved: list[CollectionSnapshot] = []

    def save_all(self, snapshots: list[CollectionSnapshot]) -> None:
        self.saved.extend(snapshots)


def load_service() -> type:
    """Fail clearly until the collection service production type exists."""
    try:
        module = importlib.import_module("frontier_radar.services.collection")
    except ModuleNotFoundError:
        pytest.fail("CollectionService module has not been implemented")

    service = getattr(module, "CollectionService", None)
    if service is None:
        pytest.fail("CollectionService has not been implemented")
    return service


def test_collection_service_persists_every_hacker_news_snapshot():
    """Catches successful HN collection results that are not retained for debugging."""
    repository = InMemorySnapshotRepository()
    service = load_service()(
        repository,
        FakeHackerNewsCollector(),
        FakeArxivCollector(),
    )

    result = service.collect_hacker_news()

    assert result.source == "hacker_news"
    assert [snapshot.source for snapshot in repository.saved] == ["hacker_news"]


def test_collection_service_collect_all_uses_default_queries_with_respectful_delay():
    """Catches a collect-all run that omits default topics or hammers arXiv requests."""
    repository = InMemorySnapshotRepository()
    arxiv = FakeArxivCollector()
    delays: list[int] = []
    service = load_service()(
        repository,
        FakeHackerNewsCollector(),
        arxiv,
        sleep=delays.append,
    )

    results = service.collect_all()

    assert [result.query for result in results] == [
        None,
        "AI agent",
        "large language model",
        "open source software",
    ]
    assert arxiv.queries == [
        "AI agent",
        "large language model",
        "open source software",
    ]
    assert delays == [3, 3]
    assert len(repository.saved) == 4


def test_collection_service_uses_real_delay_by_default(monkeypatch):
    """Catches the CLI path silently skipping arXiv's required request interval."""
    module = importlib.import_module("frontier_radar.services.collection")
    delays: list[int] = []
    monkeypatch.setattr(module, "default_sleep", delays.append)
    repository = InMemorySnapshotRepository()
    service = module.CollectionService(
        repository,
        FakeHackerNewsCollector(),
        FakeArxivCollector(),
    )

    service.collect_all()

    assert delays == [3, 3]
