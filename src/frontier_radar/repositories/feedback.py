from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from frontier_radar.models.collection import (
    ArticleFeedbackRecord,
    ArticleRankingRecord,
    ArticleRecord,
)
from frontier_radar.schemas.feedback import ArticleFeedback, FeedbackInput


class FeedbackRepository:
    """Persist one current profile-scoped decision for each saved article."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def upsert_feedback(
        self,
        profile_id: int,
        feedback: FeedbackInput,
        recorded_at: datetime,
    ) -> ArticleFeedback:
        """Save a changed decision while making an identical repeat idempotent."""
        with self._session_factory() as session:
            article_title = session.scalar(
                select(ArticleRecord.title).where(
                    ArticleRecord.id == feedback.article_id
                )
            )
            if article_title is None:
                raise ValueError("Feedback requires an existing article")
            stored = session.scalar(
                select(ArticleFeedbackRecord).where(
                    ArticleFeedbackRecord.profile_id == profile_id,
                    ArticleFeedbackRecord.article_id == feedback.article_id,
                )
            )
            if stored is None:
                stored = ArticleFeedbackRecord(
                    profile_id=profile_id,
                    article_id=feedback.article_id,
                    decision=feedback.decision.value,
                    recorded_at=recorded_at,
                )
                session.add(stored)
            elif stored.decision != feedback.decision.value:
                stored.decision = feedback.decision.value
                stored.recorded_at = recorded_at
            session.commit()
            session.refresh(stored)
            return self._to_schema(stored, article_title)

    def list_feedback(self, profile_id: int) -> list[ArticleFeedback]:
        """Return current feedback in the stable canonical article-ID order."""
        with self._session_factory() as session:
            records = session.execute(
                select(ArticleFeedbackRecord, ArticleRecord.title)
                .join(
                    ArticleRecord,
                    ArticleFeedbackRecord.article_id == ArticleRecord.id,
                )
                .where(ArticleFeedbackRecord.profile_id == profile_id)
                .order_by(ArticleFeedbackRecord.article_id, ArticleFeedbackRecord.id)
            ).all()
            return [
                self._to_schema(record, title)
                for record, title in records
            ]

    def delete_feedback(
        self,
        profile_id: int,
        article_id: int,
    ) -> ArticleFeedback | None:
        """Remove one current choice without touching its source lineage."""
        with self._session_factory() as session:
            row = session.execute(
                select(ArticleFeedbackRecord, ArticleRecord.title)
                .join(
                    ArticleRecord,
                    ArticleFeedbackRecord.article_id == ArticleRecord.id,
                )
                .where(
                    ArticleFeedbackRecord.profile_id == profile_id,
                    ArticleFeedbackRecord.article_id == article_id,
                )
            ).one_or_none()
            if row is None:
                return None
            stored, title = row
            removed = self._to_schema(stored, title)
            session.delete(stored)
            session.commit()
            return removed

    def delete_all_feedback(self, profile_id: int) -> int:
        """Remove current feedback for one profile without altering source records."""
        with self._session_factory() as session:
            result = session.execute(
                delete(ArticleFeedbackRecord).where(
                    ArticleFeedbackRecord.profile_id == profile_id
                )
            )
            session.commit()
            return result.rowcount or 0

    def has_positive_ranking(self, profile_id: int, article_id: int) -> bool:
        """Return whether this profile can currently recommend the article."""
        with self._session_factory() as session:
            return (
                session.scalar(
                    select(ArticleRankingRecord.id).where(
                        ArticleRankingRecord.profile_id == profile_id,
                        ArticleRankingRecord.article_id == article_id,
                        ArticleRankingRecord.score > 0,
                    )
                )
                is not None
            )

    @staticmethod
    def _to_schema(record: ArticleFeedbackRecord, title: str) -> ArticleFeedback:
        """Restore the UTC meaning of database DATETIME values for callers."""
        recorded_at = record.recorded_at
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        else:
            recorded_at = recorded_at.astimezone(UTC)
        return ArticleFeedback(
            article_id=record.article_id,
            title=title,
            decision=record.decision,
            recorded_at=recorded_at,
        )
