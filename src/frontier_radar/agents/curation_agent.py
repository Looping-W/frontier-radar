import json
from typing import Protocol

from pydantic import ValidationError

from frontier_radar.agents.contracts import CurationModelClient, ModelMessage
from frontier_radar.schemas.curation import CurationDraft


class CurationToolExecutor(Protocol):
    """The strict local tool boundary used by curation orchestration."""

    def definitions(self) -> list: ...

    def execute(self, name: str, arguments_json: str) -> str: ...


class CurationAgentError(ValueError):
    """The model or tool sequence could not produce a valid local curation."""


class CurationAgent:
    """Run a bounded local-tool conversation and validate its final JSON."""

    def __init__(
        self,
        client: CurationModelClient,
        tools: CurationToolExecutor,
    ) -> None:
        self._client = client
        self._tools = tools

    def run(self) -> CurationDraft:
        """Return a validated draft grounded in locally listed candidates."""
        messages = [
            ModelMessage(
                role="system",
                content=(
                    "Curate only saved local articles. Call list_ranked_articles "
                    "before selecting articles. Return final JSON with overview and "
                    "articles; do not return Markdown."
                ),
            ),
            ModelMessage(role="user", content="Create today's technical daily brief."),
        ]
        candidate_ids: set[int] | None = None
        for _ in range(8):
            reply = self._client.complete(messages, self._tools.definitions())
            if reply.tool_calls:
                messages.append(
                    ModelMessage(
                        role="assistant",
                        content=reply.content,
                        tool_calls=reply.tool_calls,
                    )
                )
                for tool_call in reply.tool_calls:
                    try:
                        result = self._tools.execute(
                            tool_call.name,
                            tool_call.arguments_json,
                        )
                    except ValueError as error:
                        raise CurationAgentError(str(error)) from error
                    if tool_call.name == "list_ranked_articles":
                        candidate_ids = {
                            candidate["article_id"] for candidate in json.loads(result)
                        }
                    messages.append(
                        ModelMessage(
                            role="tool",
                            content=result,
                            tool_call_id=tool_call.id,
                        )
                    )
                continue
            if reply.content is None:
                raise CurationAgentError(
                    "Model returned neither text nor curation tools"
                )
            try:
                draft = CurationDraft.model_validate_json(reply.content)
            except ValidationError as error:
                raise CurationAgentError(f"Invalid curation result: {error}") from error
            if candidate_ids is None:
                raise CurationAgentError("List ranked articles before final curation")
            for article in draft.articles:
                if article.article_id not in candidate_ids:
                    raise CurationAgentError(
                        "Selected article is not a listed candidate"
                    )
            return draft
        raise CurationAgentError("Curation Agent exceeded eight model turns")
