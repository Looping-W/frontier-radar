import importlib
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.status_code = 200
        self.headers = {"content-type": "application/json"}
        self.text = json.dumps(payload)
        self._payload = payload

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class FakeHttpClient:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self._responses = responses

    def get(self, url: str, **_: object) -> FakeResponse:
        return self._responses[url]


def load_collector() -> type:
    """Fail clearly until the HN collector production type exists."""
    try:
        module = importlib.import_module("frontier_radar.collectors.hacker_news")
    except ModuleNotFoundError:
        pytest.fail("HackerNewsCollector module has not been implemented")

    collector = getattr(module, "HackerNewsCollector", None)
    if collector is None:
        pytest.fail("HackerNewsCollector has not been implemented")
    return collector


def test_hacker_news_collector_preserves_feed_order_and_raw_responses():
    """Catches a collector that drops feed snapshots or reorders requested stories."""
    top_stories = json.loads((FIXTURES / "hn_topstories.json").read_text())
    item_101 = json.loads((FIXTURES / "hn_item_101.json").read_text())
    item_102 = json.loads((FIXTURES / "hn_item_102.json").read_text())
    base_url = "https://hacker-news.firebaseio.com/v0"
    client = FakeHttpClient(
        {
            f"{base_url}/topstories.json": FakeResponse(top_stories),
            f"{base_url}/item/101.json": FakeResponse(item_101),
            f"{base_url}/item/102.json": FakeResponse(item_102),
        }
    )

    result = load_collector()(client=client, limit=2).collect()

    assert result.source == "hacker_news"
    assert result.item_count == 2
    assert [snapshot.endpoint for snapshot in result.snapshots] == [
        "topstories",
        "item/101",
        "item/102",
    ]
    assert result.snapshots[0].raw_body == "[101, 102, 103]"
    title = json.loads(result.snapshots[2].raw_body)["title"]
    assert title == "Show HN: An open source tool"
