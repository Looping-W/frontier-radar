from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot


def result(source: str, item_count: int, snapshot_count: int) -> CollectionResult:
    return CollectionResult(
        source=source,
        item_count=item_count,
        snapshots=[
            CollectionSnapshot(
                source=source,
                endpoint="test",
                fetched_at=datetime(2026, 9, 1, tzinfo=UTC),
                status_code=200,
                content_type="application/json",
                raw_body="{}",
            )
            for _ in range(snapshot_count)
        ],
    )


def test_collect_hn_command_reports_collected_items_and_saved_snapshots(monkeypatch):
    """Catches a CLI command that hides the completed collection outcome."""

    class FakeService:
        def collect_hacker_news(self) -> CollectionResult:
            return result("hacker_news", item_count=30, snapshot_count=31)

    get_service = getattr(cli_module, "get_collection_service", None)
    if get_service is None:
        pytest.fail("get_collection_service has not been implemented")
    monkeypatch.setattr(cli_module, "get_collection_service", lambda: FakeService())

    invocation = CliRunner().invoke(cli_module.app, ["collect", "hn"])

    assert invocation.exit_code == 0
    assert (
        "Hacker News: 30 items collected; 31 raw responses saved."
        in invocation.output
    )
