import json
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from frontier_radar.agents.contracts import ToolDefinition
from frontier_radar.schemas.curation import CurationArticleContext, CurationCandidate


class DefaultProfile(Protocol):
    """The persisted default-profile identity needed by read-only tools."""

    id: int


class ProfilePersistence(Protocol):
    """Read-only default-profile boundary used by curation tools."""

    def get_default_profile(self) -> DefaultProfile: ...


class CurationPersistence(Protocol):
    """Read-only article boundary exposed to curation tools."""

    def list_ranked_candidates(
        self, profile_id: int, limit: int
    ) -> list[CurationCandidate]: ...

    def get_article_context(
        self, profile_id: int, article_id: int
    ) -> CurationArticleContext | None: ...


class ListRankedArticlesArguments(BaseModel):
    """Bounded candidate-list request accepted from the model."""

    limit: int = Field(ge=1, le=20)


class ArticleContextArguments(BaseModel):
    """One listed canonical article ID accepted from the model."""

    article_id: int = Field(gt=0)


class CurationToolError(ValueError):
    """A model requested a capability outside the local read-only boundary."""


class ReadOnlyCurationTools:
    """Execute the two local curation reads and reject every other action."""

    def __init__(
        self,
        profile_repository: ProfilePersistence,
        curation_repository: CurationPersistence,
        limit: int,
    ) -> None:
        self._profile_repository = profile_repository
        self._curation_repository = curation_repository
        self._limit = limit
        self._listed_article_ids: set[int] | None = None

    @staticmethod
    def definitions() -> list[ToolDefinition]:
        """Return exactly the two function schemas allowed to the model."""
        return [
            ToolDefinition(
                name="list_ranked_articles",
                description="List locally saved positive-ranked article candidates.",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20}
                    },
                    "required": ["limit"],
                    "additionalProperties": False,
                },
            ),
            ToolDefinition(
                name="get_article_context",
                description="Read saved source lineage for one listed article.",
                parameters={
                    "type": "object",
                    "properties": {"article_id": {"type": "integer", "minimum": 1}},
                    "required": ["article_id"],
                    "additionalProperties": False,
                },
            ),
        ]

    def execute(self, name: str, arguments_json: str) -> str:
        """Run one allowlisted local read and return its JSON-safe result."""
        if name == "list_ranked_articles":
            arguments = self._parse(ListRankedArticlesArguments, arguments_json)
            profile = self._profile_repository.get_default_profile()
            candidates = self._curation_repository.list_ranked_candidates(
                profile.id,
                min(arguments.limit, self._limit),
            )
            self._listed_article_ids = {
                candidate.article_id for candidate in candidates
            }
            return json.dumps([candidate.model_dump() for candidate in candidates])
        if name == "get_article_context":
            arguments = self._parse(ArticleContextArguments, arguments_json)
            if self._listed_article_ids is None:
                raise CurationToolError("List ranked articles first")
            if arguments.article_id not in self._listed_article_ids:
                raise CurationToolError("Article is not a listed candidate")
            profile = self._profile_repository.get_default_profile()
            context = self._curation_repository.get_article_context(
                profile.id,
                arguments.article_id,
            )
            if context is None:
                raise CurationToolError("Article context is unavailable")
            return context.model_dump_json()
        raise CurationToolError(f"Unsupported curation tool: {name}")

    @staticmethod
    def _parse(model: type[BaseModel], arguments_json: str) -> BaseModel:
        try:
            return model.model_validate_json(arguments_json)
        except (ValidationError, ValueError) as error:
            raise CurationToolError(
                f"Invalid curation tool arguments: {error}"
            ) from error
