from pydantic import BaseModel, ConfigDict, Field


class RankingRule(BaseModel):
    """One weighted profile term used by the deterministic matcher."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=512)
    name_key: str = Field(min_length=1, max_length=512)
    weight: int = Field(gt=0)


class RankableArticle(BaseModel):
    """Canonical article text plus its traceable raw-item display titles."""

    article_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=512)
    source_titles: list[str]


class RankedArticle(BaseModel):
    """One deterministic relevance result safe to return from a service."""

    article_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=512)
    score: int = Field(ge=0)


class RankingResult(BaseModel):
    """Summary and nonzero ranking results from one default-profile run."""

    articles_scored: int = Field(ge=0)
    rankings: list[RankedArticle]
