from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from frontier_radar.schemas.feedback import FeedbackDecision


class RankingRule(BaseModel):
    """One weighted profile term used by the deterministic matcher."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=512)
    name_key: str = Field(min_length=1, max_length=512)
    weight: int = Field(gt=0)
    rule_id: int = Field(default=0, ge=0)
    kind: Literal["topic", "keyword"] = "topic"
    feedback_adjustment: int = Field(default=0, ge=-2, le=2)

    @property
    def effective_weight(self) -> int:
        """Return the non-negative score contribution after bounded learning."""
        return max(0, self.weight + self.feedback_adjustment)


class RankableArticle(BaseModel):
    """Canonical article text plus its traceable raw-item display titles."""

    article_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=512)
    source_titles: list[str]


class FeedbackRankableArticle(RankableArticle):
    """A current feedback decision plus article text used for rule matching."""

    decision: FeedbackDecision


class FeedbackAdjustment(BaseModel):
    """One bounded learned adjustment for a persisted topic or keyword rule."""

    rule_id: int = Field(gt=0)
    kind: Literal["topic", "keyword"]
    adjustment: int = Field(ge=-2, le=2)


class RankedArticle(BaseModel):
    """One deterministic relevance result safe to return from a service."""

    article_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=512)
    score: int = Field(ge=0)


class RankingResult(BaseModel):
    """Summary and nonzero ranking results from one default-profile run."""

    articles_scored: int = Field(ge=0)
    rankings: list[RankedArticle]
