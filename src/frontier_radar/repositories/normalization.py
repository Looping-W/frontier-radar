from collections.abc import Callable
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from frontier_radar.models.collection import (
    ArticleRecord,
    CollectionSnapshotRecord,
    RawItemRecord,
)
from frontier_radar.schemas.normalization import ParsedRawItem, PersistedItemsResult

TITLE_SIMILARITY_THRESHOLD = 0.90


class NormalizationRepository:
    """Persist parsed source records and their canonical article links."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def list_snapshots(self) -> list[CollectionSnapshotRecord]:
        """Return persisted successful Phase 1 snapshots in a stable order."""
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(CollectionSnapshotRecord)
                    .where(
                        CollectionSnapshotRecord.source.in_(("hacker_news", "arxiv")),
                        CollectionSnapshotRecord.status_code >= 200,
                        CollectionSnapshotRecord.status_code < 300,
                    )
                    .order_by(CollectionSnapshotRecord.id)
                )
            )

    def save_items(self, items: list[ParsedRawItem]) -> PersistedItemsResult:
        """Save a batch in order, assigning each new item to one article."""
        result = PersistedItemsResult()
        with self._session_factory() as session:
            for item in items:
                if self._raw_item_exists(session, item):
                    continue
                article = self._find_article(session, item)
                if article is None:
                    article = ArticleRecord(
                        title=item.title,
                        title_key=item.title_key,
                        normalized_url=item.normalized_url,
                        published_at=item.published_at,
                    )
                    session.add(article)
                    session.flush()
                    result.articles_created += 1
                else:
                    result.merged_items += 1
                session.add(
                    RawItemRecord(
                        snapshot_id=item.snapshot_id,
                        article_id=article.id,
                        source=item.source,
                        source_item_id=item.source_item_id,
                        title=item.title,
                        url=item.url,
                        normalized_url=item.normalized_url,
                        published_at=item.published_at,
                    )
                )
                result.raw_items_created += 1
            session.commit()
        return result

    @staticmethod
    def _raw_item_exists(session: Session, item: ParsedRawItem) -> bool:
        statement = select(RawItemRecord.id).where(
            RawItemRecord.snapshot_id == item.snapshot_id,
            RawItemRecord.source_item_id == item.source_item_id,
        )
        return session.scalar(statement) is not None

    def _find_article(
        self,
        session: Session,
        item: ParsedRawItem,
    ) -> ArticleRecord | None:
        source_item_article = session.scalars(
            select(ArticleRecord)
            .join(RawItemRecord)
            .where(
                RawItemRecord.source == item.source,
                RawItemRecord.source_item_id == item.source_item_id,
            )
            .order_by(ArticleRecord.id)
        ).first()
        if source_item_article is not None:
            return source_item_article

        if item.normalized_url is not None:
            url_article = session.scalars(
                select(ArticleRecord)
                .where(ArticleRecord.normalized_url == item.normalized_url)
                .order_by(ArticleRecord.id)
            ).first()
            if url_article is not None:
                return url_article

        articles = session.scalars(select(ArticleRecord).order_by(ArticleRecord.id))
        for article in articles:
            similarity = SequenceMatcher(
                None, item.title_key, article.title_key
            ).ratio()
            if similarity >= TITLE_SIMILARITY_THRESHOLD:
                return article
        return None
