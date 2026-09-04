from collections.abc import Callable

from sqlalchemy.orm import Session

from frontier_radar.models.collection import CollectionSnapshotRecord
from frontier_radar.schemas.collection import CollectionSnapshot


class CollectionSnapshotRepository:
    """Store source responses exactly as returned by public APIs."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def save_all(self, snapshots: list[CollectionSnapshot]) -> None:
        records = [
            CollectionSnapshotRecord(
                source=snapshot.source,
                endpoint=snapshot.endpoint,
                query=snapshot.query,
                fetched_at=snapshot.fetched_at,
                status_code=snapshot.status_code,
                content_type=snapshot.content_type,
                raw_body=snapshot.raw_body,
            )
            for snapshot in snapshots
        ]
        with self._session_factory() as session:
            session.add_all(records)
            session.commit()
