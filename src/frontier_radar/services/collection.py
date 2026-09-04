from collections.abc import Callable
from time import sleep as default_sleep
from typing import Protocol

from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot

DEFAULT_ARXIV_QUERIES = (
    "AI agent",
    "large language model",
    "open source software",
)


class SnapshotRepository(Protocol):
    """Persistence boundary for raw API-response snapshots."""

    def save_all(self, snapshots: list[CollectionSnapshot]) -> None: ...


class HackerNewsCollector(Protocol):
    """Collector boundary used by the collection service."""

    def collect(self) -> CollectionResult: ...


class ArxivCollector(Protocol):
    """Collector boundary used by the collection service."""

    def collect(self, query: str) -> CollectionResult: ...


class CollectionService:
    """Collect public feeds and retain their raw API payloads."""

    def __init__(
        self,
        repository: SnapshotRepository,
        hacker_news_collector: HackerNewsCollector,
        arxiv_collector: ArxivCollector,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._repository = repository
        self._hacker_news_collector = hacker_news_collector
        self._arxiv_collector = arxiv_collector
        self._sleep = sleep if sleep is not None else default_sleep

    def collect_hacker_news(self) -> CollectionResult:
        result = self._hacker_news_collector.collect()
        self._repository.save_all(result.snapshots)
        return result

    def collect_arxiv(self, query: str) -> CollectionResult:
        result = self._arxiv_collector.collect(query)
        self._repository.save_all(result.snapshots)
        return result

    def collect_all(self) -> list[CollectionResult]:
        results = [self.collect_hacker_news()]
        for index, query in enumerate(DEFAULT_ARXIV_QUERIES):
            if index:
                self._sleep(3)
            results.append(self.collect_arxiv(query))
        return results
