from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from frontier_radar.schemas.feedback import ArticleFeedback, FeedbackInput


class DefaultProfile(Protocol):
    """The default-profile identity used by feedback orchestration."""

    id: int


class ProfilePersistence(Protocol):
    """Default-profile lookup kept separate from feedback writes."""

    def get_default_profile(self) -> DefaultProfile: ...


class FeedbackPersistence(Protocol):
    """Feedback database boundary used by the service."""

    def has_positive_ranking(self, profile_id: int, article_id: int) -> bool: ...

    def upsert_feedback(
        self,
        profile_id: int,
        feedback: FeedbackInput,
        recorded_at: datetime,
    ) -> ArticleFeedback: ...

    def list_feedback(self, profile_id: int) -> list[ArticleFeedback]: ...

    def delete_feedback(
        self,
        profile_id: int,
        article_id: int,
    ) -> ArticleFeedback | None: ...

    def delete_all_feedback(self, profile_id: int) -> int: ...


class RankingRefresh(Protocol):
    """The deterministic recalculation triggered after an accepted feedback write."""

    def rank_default_profile(self) -> object: ...


class FeedbackService:
    """Record default-profile feedback and immediately rebuild learned rankings."""

    def __init__(
        self,
        profile_repository: ProfilePersistence,
        feedback_repository: FeedbackPersistence,
        ranking_service: RankingRefresh,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profile_repository = profile_repository
        self._feedback_repository = feedback_repository
        self._ranking_service = ranking_service
        self._clock = clock or (lambda: datetime.now(UTC))

    def record(self, feedback: FeedbackInput) -> ArticleFeedback:
        """Save an eligible decision, then rebuild bounded ranking adjustments."""
        profile = self._profile_repository.get_default_profile()
        if not self._feedback_repository.has_positive_ranking(
            profile.id, feedback.article_id
        ):
            raise ValueError("Feedback requires a current positive-ranked article")
        saved = self._feedback_repository.upsert_feedback(
            profile.id,
            feedback,
            self._clock(),
        )
        self._ranking_service.rank_default_profile()
        return saved

    def list(self) -> list[ArticleFeedback]:
        """List the current default-profile feedback in stable repository order."""
        profile = self._profile_repository.get_default_profile()
        return self._feedback_repository.list_feedback(profile.id)

    def undo(self, article_id: int) -> ArticleFeedback:
        """Remove one saved choice and rebuild the learned ranking adjustments."""
        profile = self._profile_repository.get_default_profile()
        removed = self._feedback_repository.delete_feedback(profile.id, article_id)
        if removed is None:
            raise ValueError(f"Feedback not found for article {article_id}")
        self._ranking_service.rank_default_profile()
        return removed

    def reset(self) -> int:
        """Clear all current feedback and rebuild the learned ranking adjustments."""
        profile = self._profile_repository.get_default_profile()
        removed_count = self._feedback_repository.delete_all_feedback(profile.id)
        self._ranking_service.rank_default_profile()
        return removed_count
