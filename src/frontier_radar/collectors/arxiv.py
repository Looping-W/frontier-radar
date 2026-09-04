from datetime import UTC, datetime
from typing import Protocol
from xml.etree import ElementTree

from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot


class HttpResponse(Protocol):
    """The subset of an HTTP response required by the arXiv collector."""

    status_code: int
    headers: dict[str, str]
    text: str

    def raise_for_status(self) -> None: ...


class HttpClient(Protocol):
    """The subset of an HTTP client required by the arXiv collector."""

    def get(self, url: str, **kwargs: object) -> HttpResponse: ...


class ArxivCollector:
    """Collect recent arXiv entries for one search phrase."""

    endpoint = "https://export.arxiv.org/api/query"
    atom_namespace = "{http://www.w3.org/2005/Atom}"

    def __init__(self, client: HttpClient, max_results: int = 50) -> None:
        self._client = client
        self._max_results = max_results

    def collect(self, query: str) -> CollectionResult:
        response = self._client.get(
            self.endpoint,
            params={
                "search_query": f'all:"{query}"',
                "max_results": self._max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
        )
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        item_count = len(root.findall(f"{self.atom_namespace}entry"))
        snapshot = CollectionSnapshot(
            source="arxiv",
            endpoint="query",
            query=query,
            fetched_at=datetime.now(UTC),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            raw_body=response.text,
        )
        return CollectionResult(
            source="arxiv",
            query=query,
            item_count=item_count,
            snapshots=[snapshot],
        )
