from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CurationCandidate(BaseModel):
    """One positively ranked canonical article eligible for curation."""

    article_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=512)
    score: int = Field(gt=0)


class CurationSource(BaseModel):
    """One local raw-item and snapshot source retained for a selected article."""

    model_config = ConfigDict(str_strip_whitespace=True)

    raw_item_id: int = Field(gt=0)
    snapshot_id: int = Field(gt=0)
    source: str = Field(min_length=1, max_length=32)
    url: str | None = Field(default=None, max_length=2048)
    published_at: datetime | None = None


class CurationArticleContext(CurationCandidate):
    """Candidate metadata plus its saved Phase 2 source lineage."""

    sources: list[CurationSource]


class CurationSelection(BaseModel):
    """One model-selected article with bounded prose for local rendering."""

    model_config = ConfigDict(str_strip_whitespace=True)

    article_id: int = Field(gt=0)
    summary: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=1000)


class CurationDraft(BaseModel):
    """Structured model output that must be validated before rendering."""

    model_config = ConfigDict(str_strip_whitespace=True)

    overview: str = Field(min_length=20, max_length=1000)
    articles: list[CurationSelection] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def require_unique_article_ids(self) -> "CurationDraft":
        """Reject duplicate recommendations before they reach Markdown output."""
        article_ids = [article.article_id for article in self.articles]
        if len(article_ids) != len(set(article_ids)):
            raise ValueError("Curation article IDs must be unique")
        return self
