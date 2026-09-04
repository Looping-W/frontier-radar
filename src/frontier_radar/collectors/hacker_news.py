from datetime import UTC, datetime
from typing import Protocol

from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot


class HttpResponse(Protocol):
    """The subset of an HTTP response required by public API collectors."""

    status_code: int
    headers: dict[str, str]
    text: str

    def json(self) -> object: ...

    def raise_for_status(self) -> None: ...


class HttpClient(Protocol):
    """The subset of an HTTP client required by public API collectors."""

    def get(self, url: str, **kwargs: object) -> HttpResponse: ...


class HackerNewsCollector:
    """Collect the highest-ranked Hacker News API entries."""

    base_url = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, client: HttpClient, limit: int = 30) -> None:
        self._client = client
        self._limit = limit

    def collect(self) -> CollectionResult:
        top_stories_response = self._client.get(f"{self.base_url}/topstories.json")
        top_stories_response.raise_for_status()
        story_ids = top_stories_response.json()
        if not isinstance(story_ids, list):
            raise ValueError("Hacker News topstories response must be a list")

        snapshots = [self._snapshot("topstories", top_stories_response)]
        for story_id in story_ids[: self._limit]:
            response = self._client.get(f"{self.base_url}/item/{story_id}.json")
            response.raise_for_status()
            snapshots.append(self._snapshot(f"item/{story_id}", response))

        return CollectionResult(
            source="hacker_news",
            item_count=len(snapshots) - 1,
            snapshots=snapshots,
        )

    @staticmethod
    def _snapshot(endpoint: str, response: HttpResponse) -> CollectionSnapshot:
        return CollectionSnapshot(
            source="hacker_news",
            endpoint=endpoint,
            fetched_at=datetime.now(UTC),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            raw_body=response.text,
        )
