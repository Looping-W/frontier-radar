from datetime import datetime

from sqlalchemy import DateTime, Integer, String
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
