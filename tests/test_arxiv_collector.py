import importlib
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    status_code = 200
    headers = {"content-type": "application/atom+xml"}

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeHttpClient:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.requests: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.requests.append((url, kwargs))
        return self._response


def load_collector() -> type:
    """Fail clearly until the arXiv collector production type exists."""
    try:
        module = importlib.import_module("frontier_radar.collectors.arxiv")
    except ModuleNotFoundError:
        pytest.fail("ArxivCollector module has not been implemented")

    collector = getattr(module, "ArxivCollector", None)
    if collector is None:
        pytest.fail("ArxivCollector has not been implemented")
    return collector


def test_arxiv_collector_uses_all_field_search_and_preserves_atom_response():
    """Catches a collector that searches the wrong fields or drops the Atom payload."""
    client = FakeHttpClient(FakeResponse((FIXTURES / "arxiv_ai_agent.xml").read_text()))

    result = load_collector()(client=client, max_results=2).collect("AI agent")

    assert result.source == "arxiv"
    assert result.query == "AI agent"
    assert result.item_count == 2
    assert len(result.snapshots) == 1
    assert "<feed" in result.snapshots[0].raw_body
    assert client.requests == [
        (
            "https://export.arxiv.org/api/query",
            {
                "params": {
                    "search_query": 'all:"AI agent"',
                    "max_results": 2,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
            },
        )
    ]
