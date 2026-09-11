import importlib
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from frontier_radar.schemas.feedback import (
    ArticleFeedback,
    FeedbackDecision,
    FeedbackInput,
)
from frontier_radar.schemas.ranking import RankingResult


@dataclass
class DefaultProfile:
    """Minimal profile identity required by the feedback service."""

    id: int


def _feedback_service():
    """Load the intended orchestration boundary without hiding missing behavior."""
    try:
        module = importlib.import_module("frontier_radar.services.feedback")
    except ModuleNotFoundError:
        pytest.fail("Phase 5 feedback service has not been implemented")
    return module.FeedbackService


def test_service_records_eligible_feedback_then_recalculates_rankings():
    """Catches feedback that is saved without applying its learned effect."""
    FeedbackService = _feedback_service()
    timestamp = datetime(2026, 9, 11, 10, tzinfo=UTC)

    class FakeProfileRepository:
        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

    class FakeFeedbackRepository:
        def __init__(self) -> None:
            self.saved: tuple[int, FeedbackInput, datetime] | None = None

        def has_positive_ranking(self, profile_id: int, article_id: int) -> bool:
            return (profile_id, article_id) == (7, 12)

        def upsert_feedback(
            self, profile_id: int, feedback: FeedbackInput, recorded_at: datetime
        ) -> ArticleFeedback:
            self.saved = (profile_id, feedback, recorded_at)
            return ArticleFeedback(
                article_id=feedback.article_id,
                decision=feedback.decision,
                recorded_at=recorded_at,
            )

        def list_feedback(self, profile_id: int) -> list[ArticleFeedback]:
            assert profile_id == 7
            return []

    class FakeRankingService:
        def __init__(self) -> None:
            self.calls = 0

        def rank_default_profile(self) -> RankingResult:
            self.calls += 1
            return RankingResult(articles_scored=1, rankings=[])

    feedback_repository = FakeFeedbackRepository()
    ranking_service = FakeRankingService()
    service = FeedbackService(
        FakeProfileRepository(),
        feedback_repository,
        ranking_service,
        clock=lambda: timestamp,
    )

    saved = service.record(FeedbackInput(article_id=12, decision="like"))

    assert saved.decision is FeedbackDecision.LIKE
    assert feedback_repository.saved == (
        7,
        FeedbackInput(article_id=12, decision="like"),
        timestamp,
    )
    assert ranking_service.calls == 1


def test_service_rejects_an_article_without_a_positive_ranking():
    """Catches feedback records that cannot affect a current recommendation."""
    FeedbackService = _feedback_service()

    class FakeProfileRepository:
        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

    class FakeFeedbackRepository:
        def has_positive_ranking(self, profile_id: int, article_id: int) -> bool:
            return False

        def upsert_feedback(self, *args: object) -> ArticleFeedback:
            raise AssertionError("ineligible feedback must not be saved")

        def list_feedback(self, profile_id: int) -> list[ArticleFeedback]:
            return []

    class FakeRankingService:
        def rank_default_profile(self) -> RankingResult:
            raise AssertionError("ineligible feedback must not rerank")

    service = FeedbackService(
        FakeProfileRepository(),
        FakeFeedbackRepository(),
        FakeRankingService(),
    )

    with pytest.raises(ValueError, match="positive-ranked"):
        service.record(FeedbackInput(article_id=99, decision="skip"))
