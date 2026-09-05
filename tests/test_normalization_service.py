import importlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from frontier_radar.models.collection import CollectionSnapshotRecord
from frontier_radar.schemas.normalization import PersistedItemsResult

FIXTURES = Path(__file__).parent / "fixtures"


def load_normalization_module():
    """Return the parser module or clearly report the missing Phase 2 contract."""
    module = importlib.import_module("frontier_radar.services.normalization")
    if getattr(module, "SnapshotParser", None) is None:
        pytest.fail("SnapshotParser has not been implemented")
    return module


def snapshot(
    snapshot_id: int,
    source: str,
    endpoint: str,
    raw_body: str,
) -> CollectionSnapshotRecord:
    return CollectionSnapshotRecord(
        id=snapshot_id,
        source=source,
        endpoint=endpoint,
        fetched_at=datetime(2026, 9, 1, tzinfo=UTC),
        status_code=200,
        content_type="application/json",
        raw_body=raw_body,
    )


def test_parser_returns_one_validated_raw_item_for_hacker_news_story():
    """Catches HN parsing that loses source identity, title, or publication time."""
    module = load_normalization_module()
    hn_snapshot = snapshot(
        17,
        "hacker_news",
        "item/103",
        (FIXTURES / "hn_item_103.json").read_text(),
    )

    items = module.SnapshotParser().parse(hn_snapshot)

    assert len(items) == 1
    assert items[0].snapshot_id == 17
    assert items[0].source_item_id == "103"
    assert items[0].title == "An AI agent project!"
    assert items[0].url == (
        "HTTPS://Example.COM:443/agent/?utm_source=newsletter&b=2&a=1#details"
    )
    assert items[0].published_at == datetime(2024, 8, 31, 14, 0, tzinfo=UTC)


def test_parser_returns_one_raw_item_per_arxiv_atom_entry():
    """Catches Atom parsing that treats a whole feed as one article."""
    module = load_normalization_module()
    arxiv_snapshot = snapshot(
        18,
        "arxiv",
        "query",
        (FIXTURES / "arxiv_normalization.xml").read_text(),
    )

    items = module.SnapshotParser().parse(arxiv_snapshot)

    assert [(item.source_item_id, item.title) for item in items] == [
        ("2609.00001", "Agent systems"),
        ("2609.00002", "Language models"),
    ]
    assert items[0].url == "http://arxiv.org/abs/2609.00001"
    assert items[0].published_at == datetime(2026, 9, 1, 1, 2, 3, tzinfo=UTC)


def test_parser_skips_hacker_news_topstories_list_snapshot():
    """Catches a normalizer that mistakes a HN feed-position list for an article."""
    module = load_normalization_module()
    topstories_snapshot = snapshot(19, "hacker_news", "topstories", "[101, 102]")

    assert module.SnapshotParser().parse(topstories_snapshot) == []


def test_normalize_url_removes_tracking_fragment_and_canonicalizes_components():
    """Catches URL matching that misses duplicates because of display-only variants."""
    module = load_normalization_module()

    normalized = module.normalize_url(
        "HTTPS://Example.COM:443/agent/?utm_source=newsletter&b=2&a=1#details"
    )

    assert normalized == "https://example.com/agent?a=1&b=2"


def test_normalize_title_casefolds_and_removes_punctuation_variants():
    """Catches comparison that treats casing or punctuation as content."""
    module = load_normalization_module()

    assert module.normalize_title("  An AI-Agent Project! ") == "an ai agent project"


def test_normalization_service_parses_saved_snapshots_then_persists_raw_items():
    """Catches service orchestration that skips parsing or saves the wrong batch."""
    module = load_normalization_module()

    class RecordingRepository:
        def __init__(self) -> None:
            self.saved_items = []

        def list_snapshots(self):
            return [
                snapshot(20, "hacker_news", "topstories", "[101]"),
                snapshot(
                    21,
                    "hacker_news",
                    "item/101",
                    (FIXTURES / "hn_item_101.json").read_text(),
                ),
            ]

        def save_items(self, items):
            self.saved_items = items
            return PersistedItemsResult(
                raw_items_created=1,
                articles_created=1,
                merged_items=0,
            )

    repository = RecordingRepository()
    service = module.NormalizationService(repository)

    result = service.normalize()

    assert (
        result.snapshots_processed,
        result.raw_items_parsed,
        result.raw_items_created,
        result.articles_created,
        result.merged_items,
    ) == (2, 1, 1, 1, 0)
    saved_item_ids = [
        (item.snapshot_id, item.source_item_id) for item in repository.saved_items
    ]
    assert saved_item_ids == [(21, "101")]
