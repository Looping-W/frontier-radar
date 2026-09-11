from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from frontier_radar.schemas.curation import CurationArticleContext, CurationDraft
from frontier_radar.schemas.llm import LLMConfiguration


class LLMConfigurationLookup(Protocol):
    def show(self) -> LLMConfiguration | None: ...


class DefaultProfile(Protocol):
    id: int


class ProfileLookup(Protocol):
    def get_default_profile(self) -> DefaultProfile: ...


class CurationLookup(Protocol):
    def get_article_context(
        self, profile_id: int, article_id: int
    ) -> CurationArticleContext | None: ...


class CurationAgentRun(Protocol):
    def run(self) -> CurationDraft: ...


class CurationError(ValueError):
    """A local curation run cannot safely produce a daily brief."""


@dataclass(frozen=True)
class CurationResult:
    """Validated structured output plus its locally rendered Markdown brief."""

    draft: CurationDraft
    markdown: str


class CurationService:
    """Create a local-data-grounded Markdown digest without persisting it."""

    def __init__(
        self,
        configuration_service: LLMConfigurationLookup,
        profile_repository: ProfileLookup,
        curation_repository: CurationLookup,
        api_key: str | None,
        agent_factory: Callable[[LLMConfiguration, str, int], CurationAgentRun],
    ) -> None:
        self._configuration_service = configuration_service
        self._profile_repository = profile_repository
        self._curation_repository = curation_repository
        self._api_key = api_key
        self._agent_factory = agent_factory

    def create_digest(
        self,
        limit: int,
        today: date | None = None,
    ) -> CurationResult:
        """Validate configuration, curate local data, then render safe Markdown."""
        configuration = self._configuration_service.show()
        if configuration is None:
            raise CurationError(
                "LLM configuration not found; run fradar llm configure first"
            )
        if not self._api_key:
            raise CurationError("LLM_API_KEY is not configured")
        draft = self._agent_factory(configuration, self._api_key, limit).run()
        profile = self._profile_repository.get_default_profile()
        contexts = []
        for article in draft.articles:
            context = self._curation_repository.get_article_context(
                profile.id,
                article.article_id,
            )
            if context is None:
                raise CurationError("Selected article context is unavailable")
            contexts.append(context)
        return CurationResult(
            draft=draft,
            markdown=self._render(
                draft,
                contexts,
                today or datetime.now(UTC).date(),
            ),
        )

    @staticmethod
    def _render(
        draft: CurationDraft,
        contexts: list[CurationArticleContext],
        today: date,
    ) -> str:
        sections = [
            f"# Frontier Radar Daily Brief — {today.isoformat()}",
            "## Overview",
            draft.overview,
            "## Selected articles",
        ]
        for index, (selection, context) in enumerate(
            zip(draft.articles, contexts, strict=True),
            start=1,
        ):
            source = context.sources[0] if context.sources else None
            heading = (
                f"### {index}. [{context.title}]({source.url})"
                if source is not None and source.url
                else f"### {index}. {context.title}"
            )
            sections.extend(
                [
                    heading,
                    f"Relevance score: {context.score}",
                    selection.summary,
                    f"Why it matters: {selection.rationale}",
                ]
            )
            if source is not None:
                sections.append(
                    "Traceability: "
                    f"{source.source}; raw item {source.raw_item_id}; "
                    f"snapshot {source.snapshot_id}."
                )
        return "\n\n".join(sections) + "\n"
