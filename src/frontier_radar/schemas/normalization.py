from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HackerNewsItemPayload(BaseModel):
    """Validated fields read from one Hacker News item JSON payload."""

    id: int
    type: str
    title: str | None = None
    url: str | None = None
    time: int | None = None


class ArxivEntryPayload(BaseModel):
    """Validated fields read from one arXiv Atom entry."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    published: datetime | None = None


class ParsedRawItem(BaseModel):
    """A source item normalized enough to be persisted and deduplicated."""

    model_config = ConfigDict(str_strip_whitespace=True)

    snapshot_id: int
    source: str
    source_item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    title_key: str = Field(min_length=1)
    url: str | None = None
    normalized_url: str | None = None
    published_at: datetime | None = None


class PersistedItemsResult(BaseModel):
    """Counters produced while storing one parsed-item batch."""

    raw_items_created: int = 0
    articles_created: int = 0
    merged_items: int = 0


class NormalizationResult(BaseModel):
    """Counters reported after one complete saved-snapshot normalization run."""

    snapshots_processed: int
    raw_items_parsed: int
    raw_items_created: int
    articles_created: int
    merged_items: int
