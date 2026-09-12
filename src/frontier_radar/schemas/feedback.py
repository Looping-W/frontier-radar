from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FeedbackDecision(StrEnum):
    """The two explicit feedback decisions supported by the local profile."""

    LIKE = "like"
    SKIP = "skip"


class FeedbackInput(BaseModel):
    """Validated feedback submitted through the CLI boundary."""

    model_config = ConfigDict(str_strip_whitespace=True)

    article_id: int = Field(gt=0)
    decision: FeedbackDecision


class ArticleFeedback(BaseModel):
    """One saved current feedback decision safe for service and CLI output."""

    article_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=512)
    decision: FeedbackDecision
    recorded_at: datetime
