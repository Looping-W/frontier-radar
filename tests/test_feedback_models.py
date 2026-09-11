import importlib
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.db.base import Base


@compiles(LONGTEXT, "sqlite")
def compile_longtext_as_sqlite_text(
    _: LONGTEXT,
    __: object,
    **___: object,
) -> str:
    """Allow existing MySQL snapshot columns in focused SQLite tests."""
    return "TEXT"


def _phase_five_types():
    """Load the intended public contracts without hiding a missing feature."""
    try:
        models = importlib.import_module("frontier_radar.models.collection")
        schemas = importlib.import_module("frontier_radar.schemas.feedback")
    except ModuleNotFoundError:
        pytest.fail("Phase 5 feedback models and schemas have not been implemented")
    return (
        models.ArticleFeedbackRecord,
        models.ArticleRecord,
        models.InterestProfileRecord,
        models.InterestTopicRecord,
        schemas.FeedbackDecision,
        schemas.FeedbackInput,
    )


def test_feedback_input_allows_only_positive_article_ids_and_known_decisions():
    """Catches malformed feedback crossing the CLI/service boundary."""
    _, _, _, _, FeedbackDecision, FeedbackInput = _phase_five_types()

    assert (
        FeedbackInput(article_id=4, decision="like").decision
        is FeedbackDecision.LIKE
    )
    with pytest.raises(ValidationError):
        FeedbackInput(article_id=0, decision="like")
    with pytest.raises(ValidationError):
        FeedbackInput(article_id=4, decision="later")


def test_feedback_database_constraints_bound_adjustments_and_unique_feedback():
    """Catches learning drift or duplicate profile/article feedback rows."""
    (
        ArticleFeedbackRecord,
        ArticleRecord,
        InterestProfileRecord,
        InterestTopicRecord,
        _,
        _,
    ) = _phase_five_types()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory: Callable[[], Session] = sessionmaker(engine)
    with factory() as session:
        session.add_all(
            [
                InterestProfileRecord(id=1, name="Default", slug="default"),
                ArticleRecord(
                    id=1,
                    title="AI agent guide",
                    title_key="ai agent guide",
                    normalized_url=None,
                    published_at=None,
                ),
                InterestTopicRecord(
                    profile_id=1,
                    name="AI Agent",
                    name_key="ai agent",
                    weight=3,
                    feedback_adjustment=3,
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add_all(
            [
                ArticleFeedbackRecord(
                    profile_id=1,
                    article_id=1,
                    decision="like",
                    recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                ArticleFeedbackRecord(
                    profile_id=1,
                    article_id=1,
                    decision="skip",
                    recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()
