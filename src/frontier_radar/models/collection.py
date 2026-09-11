from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
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


class InterestProfileRecord(Base):
    """One saved set of weighted interests, ready for future multi-profile use."""

    __tablename__ = "interest_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(128), unique=True)


class InterestTopicRecord(Base):
    """A profile-owned topic that contributes a deterministic ranking weight."""

    __tablename__ = "interest_topics"
    __table_args__ = (
        UniqueConstraint("profile_id", "name_key"),
        CheckConstraint(
            "weight >= 1 AND weight <= 5",
            name="ck_interest_topics_weight_range",
        ),
        CheckConstraint(
            "feedback_adjustment >= -2 AND feedback_adjustment <= 2",
            name="ck_interest_topics_feedback_adjustment_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("interest_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(512))
    name_key: Mapped[str] = mapped_column(String(512))
    weight: Mapped[int] = mapped_column(Integer)
    feedback_adjustment: Mapped[int] = mapped_column(Integer, default=0)


class InterestKeywordRecord(Base):
    """A profile-owned keyword that contributes a deterministic ranking weight."""

    __tablename__ = "interest_keywords"
    __table_args__ = (
        UniqueConstraint("profile_id", "name_key"),
        CheckConstraint(
            "weight >= 1 AND weight <= 5",
            name="ck_interest_keywords_weight_range",
        ),
        CheckConstraint(
            "feedback_adjustment >= -2 AND feedback_adjustment <= 2",
            name="ck_interest_keywords_feedback_adjustment_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("interest_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(512))
    name_key: Mapped[str] = mapped_column(String(512))
    weight: Mapped[int] = mapped_column(Integer)
    feedback_adjustment: Mapped[int] = mapped_column(Integer, default=0)


class ArticleRankingRecord(Base):
    """One persisted relevance score for an article in one interest profile."""

    __tablename__ = "article_rankings"
    __table_args__ = (UniqueConstraint("profile_id", "article_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("interest_profiles.id"), index=True
    )
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    score: Mapped[int] = mapped_column(Integer)


class ArticleFeedbackRecord(Base):
    """One current like or skip decision for a profile-owned ranked article."""

    __tablename__ = "article_feedback"
    __table_args__ = (
        UniqueConstraint("profile_id", "article_id"),
        CheckConstraint(
            "decision IN ('like', 'skip')",
            name="ck_article_feedback_decision",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("interest_profiles.id"), index=True
    )
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    decision: Mapped[str] = mapped_column(String(16))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LLMConfigurationRecord(Base):
    """One non-secret model connection configuration for local curation."""

    __tablename__ = "llm_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    provider_id: Mapped[str] = mapped_column(String(128))
    provider_label: Mapped[str] = mapped_column(String(128))
    api_protocol: Mapped[str] = mapped_column(String(64))
    base_url: Mapped[str] = mapped_column(String(2048))
    model_name: Mapped[str] = mapped_column(String(255))
