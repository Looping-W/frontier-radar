import importlib
from datetime import UTC, datetime

import pytest
from sqlalchemy.dialects.mysql import LONGTEXT

from frontier_radar.models.collection import CollectionSnapshotRecord
from frontier_radar.schemas.collection import CollectionSnapshot


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def add_all(self, records: list[object]) -> None:
        self.added.extend(records)

    def commit(self) -> None:
        self.committed = True


def load_repository() -> type:
    """Fail clearly until the snapshot repository production type exists."""
    try:
        module = importlib.import_module("frontier_radar.repositories.collection")
    except ModuleNotFoundError:
        pytest.fail("CollectionSnapshotRepository module has not been implemented")

    repository = getattr(module, "CollectionSnapshotRepository", None)
    if repository is None:
        pytest.fail("CollectionSnapshotRepository has not been implemented")
    return repository


def test_snapshot_repository_persists_raw_response_metadata_and_body():
    """Catches raw snapshots that lose query metadata or the API response body."""
    session = FakeSession()
    snapshot = CollectionSnapshot(
        source="arxiv",
        endpoint="query",
        query="AI agent",
        fetched_at=datetime(2026, 9, 1, tzinfo=UTC),
        status_code=200,
        content_type="application/atom+xml",
        raw_body="<feed />",
    )

    load_repository()(lambda: session).save_all([snapshot])

    assert session.committed is True
    assert len(session.added) == 1
    saved = session.added[0]
    assert saved.source == "arxiv"
    assert saved.query == "AI agent"
    assert saved.raw_body == "<feed />"


def test_snapshot_model_reserves_longtext_for_full_arxiv_responses():
    """Catches a raw-response column too small for a full arXiv Atom feed."""
    column = CollectionSnapshotRecord.__table__.c.raw_body

    assert isinstance(column.type, LONGTEXT)
