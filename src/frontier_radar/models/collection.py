from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from frontier_radar.db.base import Base


class CollectionSnapshotRecord(Base):
    """Persisted raw response from one external API request."""

    __tablename__ = "collection_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    endpoint: Mapped[str] = mapped_column(String(255))
    query: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status_code: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(255))
    raw_body: Mapped[str] = mapped_column(LONGTEXT)


class ArticleRecord(Base):
    """Canonical article assembled from one or more source raw items."""

    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_normalized_url", "normalized_url", mysql_length=768),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    title_key: Mapped[str] = mapped_column(String(512), index=True)
    normalized_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RawItemRecord(Base):
    """One validated source item, retaining its source-snapshot lineage."""

    __tablename__ = "raw_items"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "source_item_id"),
        Index("ix_raw_items_normalized_url", "normalized_url", mysql_length=768),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("collection_snapshots.id"), index=True
    )
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    source_item_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    normalized_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
