import json
from typing import Protocol

from pydantic import ValidationError

from frontier_radar.agents.contracts import CurationModelClient, ModelMessage
from frontier_radar.schemas.curation import CurationDraft, CurationLanguage


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
        language: CurationLanguage = CurationLanguage.EN,
    ) -> None:
        self._client = client
        self._tools = tools
        self._language = language

    def run(self) -> CurationDraft:
        """Return a validated draft grounded in locally listed candidates."""
        messages = [
            ModelMessage(
                role="system",
                content=(
                    "Curate only saved local articles. Call list_ranked_articles "
                    "before selecting articles. Return exactly one final JSON object; "
                    "do not return Markdown or other text. Its exact shape is "
                    '{"overview":"20-1000 characters",'
                    '"articles":[{"article_id":123,"summary":"1-1000 characters",'
                    '"rationale":"1-1000 characters"}]}. '
                    "Select one to five unique article_id values from the listed "
                    "candidates, and include all three fields for every article."
                    f" {self._language_instruction()}"
                ),
            ),
            ModelMessage(role="user", content="Create today's technical daily brief."),
        ]
        candidate_ids: set[int] | None = None
        correction_attempted = False
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
            validation_problem: str | None = None
            try:
                draft = CurationDraft.model_validate_json(reply.content)
            except ValidationError as error:
                validation_problem = str(error)
                draft = None
            else:
                if not self._matches_requested_language(draft):
                    validation_problem = (
                        "The requested Simplified Chinese prose was not provided"
                    )
            if validation_problem is not None:
                if not correction_attempted:
                    correction_attempted = True
                    messages.extend(
                        [
                            ModelMessage(role="assistant", content=reply.content),
                            ModelMessage(
                                role="user",
                                content=(
                                    "Your previous final response failed local JSON "
                                    "validation. Return one JSON object in this exact "
                                    "shape: "
                                    '{"overview":"...","articles":[{"article_id":123,'
                                    '"summary":"...","rationale":"..."}]}. '
                                    "Every selected article must include article_id, "
                                    "summary, and rationale. "
                                    f"{self._language_instruction()}"
                                ),
                            ),
                        ]
                    )
                    continue
                raise CurationAgentError(
                    f"Invalid curation result: {validation_problem}"
                )
            assert draft is not None
            if candidate_ids is None:
                raise CurationAgentError("List ranked articles before final curation")
            for article in draft.articles:
                if article.article_id not in candidate_ids:
                    raise CurationAgentError(
                        "Selected article is not a listed candidate"
                    )
            return draft
        raise CurationAgentError("Curation Agent exceeded eight model turns")

    def _language_instruction(self) -> str:
        if self._language is CurationLanguage.ZH:
            return (
                "Write overview, summary, and rationale in Simplified Chinese. "
                "Keep technical identifiers and article IDs unchanged."
            )
        return "Write overview, summary, and rationale in English."

    def _matches_requested_language(self, draft: CurationDraft) -> bool:
        if self._language is CurationLanguage.EN:
            return True
        prose = [draft.overview]
        for article in draft.articles:
            prose.extend([article.summary, article.rationale])
        return all(
            any("\u4e00" <= character <= "\u9fff" for character in text)
            for text in prose
        )
