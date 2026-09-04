from datetime import datetime

from pydantic import BaseModel


class CollectionSnapshot(BaseModel):
    """One unmodified HTTP response saved for collection debugging."""

    source: str
    endpoint: str
    query: str | None = None
    fetched_at: datetime
    status_code: int
    content_type: str
    raw_body: str


class CollectionResult(BaseModel):
    """The source-level outcome returned by a collector."""

    source: str
    query: str | None = None
    item_count: int
    snapshots: list[CollectionSnapshot]
