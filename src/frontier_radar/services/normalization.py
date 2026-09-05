import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

from pydantic import ValidationError

from frontier_radar.schemas.normalization import (
    ArxivEntryPayload,
    HackerNewsItemPayload,
    NormalizationResult,
    ParsedRawItem,
    PersistedItemsResult,
)

TRACKING_QUERY_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
ATOM_NAMESPACE = "{http://www.w3.org/2005/Atom}"


class StoredSnapshot(Protocol):
    """The persisted snapshot fields needed by the source parsers."""

    id: int
    source: str
    endpoint: str
    raw_body: str


class NormalizationPersistence(Protocol):
    """Database boundary used by the saved-snapshot normalization service."""

    def list_snapshots(self) -> list[StoredSnapshot]: ...

    def save_items(self, items: list[ParsedRawItem]) -> PersistedItemsResult: ...


def normalize_title(title: str) -> str:
    """Produce a stable title key for deterministic similarity comparisons."""
    normalized = unicodedata.normalize("NFKC", title).casefold()
    without_punctuation = re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE)
    return " ".join(without_punctuation.split())


def normalize_url(url: str | None) -> str | None:
    """Remove presentation and common tracking variance from a web URL."""
    if url is None:
        return None

    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError("URL must include a scheme and hostname")

    scheme = parsed.scheme.casefold()
    host = parsed.hostname.casefold()
    if ":" in host:
        host = f"[{host}]"
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("URL has an invalid port") from error
    if port is not None and (scheme, port) not in {("http", 80), ("https", 443)}:
        host = f"{host}:{port}"

    path = parsed.path.rstrip("/") or "/"
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in TRACKING_QUERY_PARAMETERS
    ]
    query = urlencode(sorted(query_pairs))
    return urlunsplit((scheme, host, path, query, ""))


class SnapshotParser:
    """Parse item-bearing Phase 1 snapshots without issuing HTTP requests."""

    def parse(self, snapshot: StoredSnapshot) -> list[ParsedRawItem]:
        if snapshot.source == "hacker_news":
            return self._parse_hacker_news(snapshot)
        if snapshot.source == "arxiv":
            return self._parse_arxiv(snapshot)
        raise ValueError(f"Unsupported snapshot source: {snapshot.source}")

    def _parse_hacker_news(self, snapshot: StoredSnapshot) -> list[ParsedRawItem]:
        if snapshot.endpoint == "topstories":
            return []
        if not snapshot.endpoint.startswith("item/"):
            raise ValueError(f"Unsupported Hacker News endpoint: {snapshot.endpoint}")
        try:
            payload = HackerNewsItemPayload.model_validate(
                json.loads(snapshot.raw_body)
            )
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError("Invalid Hacker News item snapshot") from error
        if payload.type != "story":
            return []
        if payload.title is None:
            raise ValueError("Hacker News story snapshot has no title")
        return [
            ParsedRawItem(
                snapshot_id=snapshot.id,
                source="hacker_news",
                source_item_id=str(payload.id),
                title=payload.title,
                title_key=normalize_title(payload.title),
                url=payload.url,
                normalized_url=normalize_url(payload.url),
                published_at=(
                    datetime.fromtimestamp(payload.time, UTC)
                    if payload.time is not None
                    else None
                ),
            )
        ]

    def _parse_arxiv(self, snapshot: StoredSnapshot) -> list[ParsedRawItem]:
        if snapshot.endpoint != "query":
            raise ValueError(f"Unsupported arXiv endpoint: {snapshot.endpoint}")
        try:
            root = ElementTree.fromstring(snapshot.raw_body)
        except ElementTree.ParseError as error:
            raise ValueError("Invalid arXiv Atom snapshot") from error

        items = []
        for entry in root.findall(f"{ATOM_NAMESPACE}entry"):
            payload = self._arxiv_payload(entry)
            source_item_id = payload.id.rstrip("/").rsplit("/", maxsplit=1)[-1]
            items.append(
                ParsedRawItem(
                    snapshot_id=snapshot.id,
                    source="arxiv",
                    source_item_id=source_item_id,
                    title=" ".join(payload.title.split()),
                    title_key=normalize_title(payload.title),
                    url=payload.id,
                    normalized_url=normalize_url(payload.id),
                    published_at=payload.published,
                )
            )
        return items

    @staticmethod
    def _arxiv_payload(entry: ElementTree.Element) -> ArxivEntryPayload:
        values = {
            "id": entry.findtext(f"{ATOM_NAMESPACE}id"),
            "title": entry.findtext(f"{ATOM_NAMESPACE}title"),
            "published": entry.findtext(f"{ATOM_NAMESPACE}published"),
        }
        try:
            return ArxivEntryPayload.model_validate(values)
        except ValidationError as error:
            raise ValueError("Invalid arXiv Atom entry") from error


class NormalizationService:
    """Turn persisted Phase 1 snapshots into stored normalized records."""

    def __init__(
        self,
        repository: NormalizationPersistence,
        parser: SnapshotParser | None = None,
    ) -> None:
        self._repository = repository
        self._parser = parser if parser is not None else SnapshotParser()

    def normalize(self) -> NormalizationResult:
        snapshots = self._repository.list_snapshots()
        items = [
            item
            for snapshot in snapshots
            for item in self._parser.parse(snapshot)
        ]
        persisted = self._repository.save_items(items)
        return NormalizationResult(
            snapshots_processed=len(snapshots),
            raw_items_parsed=len(items),
            raw_items_created=persisted.raw_items_created,
            articles_created=persisted.articles_created,
            merged_items=persisted.merged_items,
        )
