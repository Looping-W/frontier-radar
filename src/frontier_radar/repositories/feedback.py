from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from frontier_radar.models.collection import ArticleFeedbackRecord, ArticleRankingRecord
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
            return self._to_schema(stored)

    def list_feedback(self, profile_id: int) -> list[ArticleFeedback]:
        """Return current feedback in the stable canonical article-ID order."""
        with self._session_factory() as session:
            records = session.scalars(
                select(ArticleFeedbackRecord)
                .where(ArticleFeedbackRecord.profile_id == profile_id)
                .order_by(ArticleFeedbackRecord.article_id, ArticleFeedbackRecord.id)
            ).all()
            return [self._to_schema(record) for record in records]

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
    def _to_schema(record: ArticleFeedbackRecord) -> ArticleFeedback:
        """Restore the UTC meaning of database DATETIME values for callers."""
        recorded_at = record.recorded_at
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        else:
            recorded_at = recorded_at.astimezone(UTC)
        return ArticleFeedback(
            article_id=record.article_id,
            decision=record.decision,
            recorded_at=recorded_at,
        )
