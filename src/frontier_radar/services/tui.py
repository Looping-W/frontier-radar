import shlex
from typing import Protocol

from pydantic import ValidationError

from frontier_radar.schemas.collection import CollectionResult
from frontier_radar.schemas.feedback import (
    ArticleFeedback,
    FeedbackDecision,
    FeedbackInput,
)
from frontier_radar.schemas.health import HealthStatus
from frontier_radar.schemas.interests import (
    InterestNameInput,
    InterestTerm,
    WeightedInterestInput,
)
from frontier_radar.schemas.llm import LLMConfiguration
from frontier_radar.schemas.normalization import NormalizationResult
from frontier_radar.schemas.ranking import RankedArticle, RankingResult
from frontier_radar.schemas.refresh import RefreshResult
from frontier_radar.schemas.tui import (
    TUIAction,
    TUICommand,
    TUICommandResult,
    TUIDashboard,
    TUIDigestInput,
    TUIDrawerView,
    TUIQueryInput,
)


class TUIInputError(ValueError):
    """Composer text does not match an allowlisted Phase 6 command."""


class HealthCommands(Protocol):
    def check(self) -> HealthStatus: ...


class CollectionCommands(Protocol):
    def collect_hacker_news(self) -> CollectionResult: ...

    def collect_all(self) -> list[CollectionResult]: ...

    def collect_arxiv(self, query: str) -> CollectionResult: ...


class NormalizationCommands(Protocol):
    def normalize(self) -> NormalizationResult: ...


class RankingCommands(Protocol):
    def rank_default_profile(self) -> RankingResult: ...

    def list_default_profile(self, limit: int = 20) -> list[RankedArticle]: ...


class CurationResult(Protocol):
    markdown: str


class CurationCommands(Protocol):
    def create_digest(self, limit: int) -> CurationResult: ...


class InterestCommands(Protocol):
    def list_topics(self) -> list[InterestTerm]: ...

    def list_keywords(self) -> list[InterestTerm]: ...

    def add_topic(self, value: WeightedInterestInput) -> InterestTerm: ...

    def update_topic(self, value: WeightedInterestInput) -> InterestTerm: ...

    def remove_topic(self, value: InterestNameInput) -> InterestTerm: ...

    def add_keyword(self, value: WeightedInterestInput) -> InterestTerm: ...

    def update_keyword(self, value: WeightedInterestInput) -> InterestTerm: ...

    def remove_keyword(self, value: InterestNameInput) -> InterestTerm: ...


class FeedbackCommands(Protocol):
    def list(self) -> list[ArticleFeedback]: ...

    def record(self, value: FeedbackInput) -> ArticleFeedback: ...

    def undo(self, article_id: int) -> ArticleFeedback: ...

    def reset(self) -> int: ...


class LLMCommands(Protocol):
    def show(self) -> LLMConfiguration | None: ...


class RefreshCommands(Protocol):
    def refresh(self) -> RefreshResult: ...


class TUICommandService:
    """Parse and execute the explicit Phase 6 TUI command allowlist."""

    def __init__(
        self,
        *,
        health_service: HealthCommands,
        collection_service: CollectionCommands,
        normalization_service: NormalizationCommands,
        ranking_service: RankingCommands,
        curation_service: CurationCommands,
        interest_service: InterestCommands,
        feedback_service: FeedbackCommands,
        llm_service: LLMCommands,
        refresh_service: RefreshCommands | None = None,
    ) -> None:
        self._health = health_service
        self._collection = collection_service
        self._normalization = normalization_service
        self._ranking = ranking_service
        self._curation = curation_service
        self._interests = interest_service
        self._feedback = feedback_service
        self._llm = llm_service
        self._refresh = refresh_service
        self._current_digest: str | None = None

    @staticmethod
    def parse(raw: str) -> TUICommand:
        """Parse one slash command without guessing user intent."""
        try:
            tokens = shlex.split(raw.strip())
        except ValueError as error:
            raise TUIInputError(f"Invalid quoting: {error}") from error
        if not tokens or not tokens[0].startswith("/"):
            raise TUIInputError(
                "Phase 6 accepts explicit slash commands only; use /help."
            )

        command = tokens[0].lower()
        arguments = tokens[1:]
        try:
            argument_free_commands = {
                "/help",
                "/health",
                "/model",
                "/normalize",
                "/rank",
                "/refresh",
                "/topics",
                "/keywords",
                "/quit",
            }
            if command in argument_free_commands:
                if arguments:
                    raise TUIInputError(f"{command} does not accept arguments")
                action = {
                    "/help": TUIAction.HELP,
                    "/health": TUIAction.HEALTH,
                    "/model": TUIAction.MODEL,
                    "/normalize": TUIAction.NORMALIZE,
                    "/rank": TUIAction.RANK,
                    "/refresh": TUIAction.REFRESH,
                    "/topics": TUIAction.LIST_TOPICS,
                    "/keywords": TUIAction.LIST_KEYWORDS,
                    "/quit": TUIAction.QUIT,
                }[command]
                return TUICommand(raw=raw, action=action)

            if command == "/collect":
                return TUICommandService._parse_collect(raw, arguments)
            if command == "/digest":
                return TUICommandService._parse_digest(raw, arguments)
            if command in {"/topic", "/keyword"}:
                return TUICommandService._parse_interest(raw, command, arguments)
            if command == "/feedback":
                if not arguments:
                    return TUICommand(raw=raw, action=TUIAction.LIST_FEEDBACK)
                if arguments == ["reset"]:
                    return TUICommand(
                        raw=raw,
                        action=TUIAction.RESET_FEEDBACK,
                        requires_confirmation=True,
                    )
                raise TUIInputError("Use /feedback or /feedback reset")
            if command in {"/like", "/dislike", "/undo"}:
                return TUICommandService._parse_article_action(
                    raw, command, arguments
                )
        except (ValidationError, ValueError) as error:
            if isinstance(error, TUIInputError):
                raise
            raise TUIInputError(str(error)) from error

        raise TUIInputError(f"Unknown command: {tokens[0]}; use /help.")

    @staticmethod
    def _parse_collect(raw: str, arguments: list[str]) -> TUICommand:
        if arguments == ["hn"]:
            return TUICommand(raw=raw, action=TUIAction.COLLECT_HN)
        if arguments == ["all"]:
            return TUICommand(raw=raw, action=TUIAction.COLLECT_ALL)
        if len(arguments) >= 2 and arguments[0] == "arxiv":
            query = TUIQueryInput(query=" ".join(arguments[1:])).query
            return TUICommand(
                raw=raw,
                action=TUIAction.COLLECT_ARXIV,
                parameters={"query": query},
            )
        raise TUIInputError("Use /collect hn, /collect all, or /collect arxiv QUERY")

    @staticmethod
    def _parse_digest(raw: str, arguments: list[str]) -> TUICommand:
        if len(arguments) > 1:
            raise TUIInputError("Use /digest or /digest LIMIT")
        limit = TUIDigestInput(limit=int(arguments[0]) if arguments else 10).limit
        return TUICommand(
            raw=raw,
            action=TUIAction.DIGEST,
            parameters={"limit": limit},
        )

    @staticmethod
    def _parse_interest(
        raw: str,
        command: str,
        arguments: list[str],
    ) -> TUICommand:
        if len(arguments) < 2:
            raise TUIInputError(f"Use {command} add, update, or remove with a name")
        operation = arguments[0]
        kind = command.removeprefix("/")
        if operation in {"add", "update"} and len(arguments) >= 3:
            interest = WeightedInterestInput(
                weight=int(arguments[1]),
                name=" ".join(arguments[2:]),
            )
            action = TUIAction(f"{operation}_{kind}")
            return TUICommand(
                raw=raw,
                action=action,
                parameters={"weight": interest.weight, "name": interest.name},
            )
        if operation == "remove":
            interest = InterestNameInput(name=" ".join(arguments[1:]))
            return TUICommand(
                raw=raw,
                action=TUIAction(f"remove_{kind}"),
                parameters={"name": interest.name},
            )
        raise TUIInputError(f"Use {command} add, update, or remove with a name")

    @staticmethod
    def _parse_article_action(
        raw: str,
        command: str,
        arguments: list[str],
    ) -> TUICommand:
        if len(arguments) != 1:
            raise TUIInputError(f"Use {command} ARTICLE_ID")
        article_id = int(arguments[0])
        if command == "/undo":
            FeedbackInput(article_id=article_id, decision=FeedbackDecision.LIKE)
            action = TUIAction.UNDO
        else:
            decision = (
                FeedbackDecision.LIKE
                if command == "/like"
                else FeedbackDecision.SKIP
            )
            FeedbackInput(article_id=article_id, decision=decision)
            action = TUIAction.LIKE if command == "/like" else TUIAction.DISLIKE
        return TUICommand(
            raw=raw,
            action=action,
            parameters={"article_id": article_id},
        )

    def execute(
        self,
        command: TUICommand,
        confirmed: bool = False,
    ) -> TUICommandResult:
        """Run one validated command against explicitly injected services."""
        if command.requires_confirmation and not confirmed:
            return TUICommandResult(
                ok=False,
                title="Confirmation required",
                body="Explicit confirmation is required before feedback reset.",
            )
        try:
            return self._execute(command)
        except Exception as error:
            return TUICommandResult(
                ok=False,
                title="Command failed",
                body=str(error) or error.__class__.__name__,
            )

    def load_dashboard(self) -> TUIDashboard:
        """Read initial drawer data without running collection or ranking writes."""
        notices: list[str] = []
        try:
            health = self._health.check()
        except Exception as error:
            health = HealthStatus(database="unavailable", detail=str(error))
        try:
            configuration = self._llm.show()
        except Exception as error:
            configuration = None
            notices.append(f"Model configuration unavailable: {error}")
        try:
            recommendations = self._ranking.list_default_profile(20)
        except Exception as error:
            recommendations = []
            notices.append(f"Recommendations unavailable: {error}")
        try:
            feedback = self._feedback.list()
        except Exception as error:
            feedback = []
            notices.append(f"Feedback unavailable: {error}")
        return TUIDashboard(
            database_status=health.database,
            database_detail=health.detail,
            model_label=(
                f"{configuration.provider_label} · {configuration.model_name}"
                if configuration is not None
                else None
            ),
            recommendations=recommendations,
            feedback=feedback,
            digest_markdown=self._current_digest,
            notices=notices,
        )

    def _execute(self, command: TUICommand) -> TUICommandResult:
        action = command.action
        parameters = command.parameters
        if action is TUIAction.HELP:
            return TUICommandResult(
                ok=True,
                title="Available commands",
                body=self._help_text(),
            )
        if action is TUIAction.QUIT:
            return TUICommandResult(
                ok=True,
                title="Exit Frontier Radar",
                body="Session data will not be saved.",
                should_quit=True,
            )
        if action is TUIAction.HEALTH:
            status = self._health.check()
            detail = f"\nDetail: {status.detail}" if status.detail else ""
            return TUICommandResult(
                ok=status.database == "ok",
                title="System health",
                body=(
                    f"Application: {status.application}\n"
                    f"Database: {status.database}{detail}"
                ),
            )
        if action is TUIAction.MODEL:
            return self._model_result(self._llm.show())
        if action is TUIAction.COLLECT_HN:
            return self._collection_result(
                [self._collection.collect_hacker_news()]
            )
        if action is TUIAction.COLLECT_ALL:
            return self._collection_result(self._collection.collect_all())
        if action is TUIAction.COLLECT_ARXIV:
            return self._collection_result(
                [self._collection.collect_arxiv(str(parameters["query"]))]
            )
        if action is TUIAction.NORMALIZE:
            return self._normalization_result(self._normalization.normalize())
        if action is TUIAction.RANK:
            return self._ranking_result(self._ranking.rank_default_profile())
        if action is TUIAction.REFRESH:
            if self._refresh is None:
                raise RuntimeError("Refresh service is unavailable")
            return self._refresh_result(self._refresh.refresh())
        if action is TUIAction.DIGEST:
            result = self._curation.create_digest(int(parameters["limit"]))
            self._current_digest = result.markdown
            return TUICommandResult(
                ok=True,
                title="Daily brief",
                body=result.markdown,
                drawer_view=TUIDrawerView.DIGEST,
            )
        if action is TUIAction.LIST_TOPICS:
            return self._interest_list("Topics", self._interests.list_topics())
        if action is TUIAction.LIST_KEYWORDS:
            return self._interest_list("Keywords", self._interests.list_keywords())
        if action in {
            TUIAction.ADD_TOPIC,
            TUIAction.UPDATE_TOPIC,
            TUIAction.ADD_KEYWORD,
            TUIAction.UPDATE_KEYWORD,
        }:
            return self._write_interest(action, parameters)
        if action in {TUIAction.REMOVE_TOPIC, TUIAction.REMOVE_KEYWORD}:
            return self._remove_interest(action, parameters)
        if action is TUIAction.LIST_FEEDBACK:
            return self._feedback_result(self._feedback.list())
        if action in {TUIAction.LIKE, TUIAction.DISLIKE}:
            decision = (
                FeedbackDecision.LIKE
                if action is TUIAction.LIKE
                else FeedbackDecision.SKIP
            )
            saved = self._feedback.record(
                FeedbackInput(
                    article_id=int(parameters["article_id"]),
                    decision=decision,
                )
            )
            return TUICommandResult(
                ok=True,
                title="Feedback saved",
                body=f"Article #{saved.article_id} marked {self._decision(saved)}.",
                drawer_view=TUIDrawerView.FEEDBACK,
            )
        if action is TUIAction.UNDO:
            removed = self._feedback.undo(int(parameters["article_id"]))
            return TUICommandResult(
                ok=True,
                title="Feedback removed",
                body=f"Article #{removed.article_id} is neutral.",
                drawer_view=TUIDrawerView.FEEDBACK,
            )
        if action is TUIAction.RESET_FEEDBACK:
            count = self._feedback.reset()
            return TUICommandResult(
                ok=True,
                title="Feedback reset",
                body=f"{count} feedback {self._plural(count, 'item')} removed.",
                drawer_view=TUIDrawerView.FEEDBACK,
            )
        raise RuntimeError(f"Unsupported action: {action}")

    @staticmethod
    def _help_text() -> str:
        return """Core
/health · /model · /refresh · /rank · /digest [LIMIT]

Collection
/collect hn · /collect all · /collect arxiv QUERY · /normalize

Interests
/topics · /topic add|update WEIGHT NAME · /topic remove NAME
/keywords · /keyword add|update WEIGHT NAME · /keyword remove NAME

Feedback
/feedback · /like ARTICLE_ID · /dislike ARTICLE_ID · /undo ARTICLE_ID
/feedback reset

Session
/help · /quit"""

    @staticmethod
    def _model_result(configuration: LLMConfiguration | None) -> TUICommandResult:
        if configuration is None:
            return TUICommandResult(
                ok=True,
                title="Model configuration",
                body="No local model configuration is saved.",
            )
        return TUICommandResult(
            ok=True,
            title="Model configuration",
            body=(
                f"Provider: {configuration.provider_label}\n"
                f"Protocol: {configuration.api_protocol.replace('_', '-')}\n"
                f"Endpoint: {configuration.base_url}\n"
                f"Model: {configuration.model_name}"
            ),
        )

    @staticmethod
    def _collection_result(results: list[CollectionResult]) -> TUICommandResult:
        labels = {"hacker_news": "Hacker News", "arxiv": "arXiv"}
        lines = [
            f"{labels.get(result.source, result.source)}: "
            f"{result.item_count} items collected; "
            f"{len(result.snapshots)} raw responses saved."
            for result in results
        ]
        return TUICommandResult(
            ok=True,
            title="Collection complete",
            body="\n".join(lines),
        )

    @staticmethod
    def _normalization_result(result: NormalizationResult) -> TUICommandResult:
        return TUICommandResult(
            ok=True,
            title="Normalization complete",
            body=(
                f"{result.snapshots_processed} snapshots processed; "
                f"{result.raw_items_parsed} raw items parsed; "
                f"{result.raw_items_created} raw items saved; "
                f"{result.articles_created} articles created; "
                f"{result.merged_items} items merged."
            ),
        )

    @staticmethod
    def _ranking_result(result: RankingResult) -> TUICommandResult:
        lines = [
            f"{result.articles_scored} articles scored; "
            f"{len(result.rankings)} relevant "
            f"{TUICommandService._plural(len(result.rankings), 'article')}."
        ]
        lines.extend(
            f"{ranking.score} · #{ranking.article_id} · {ranking.title}"
            for ranking in result.rankings
        )
        return TUICommandResult(
            ok=True,
            title="Ranking complete",
            body="\n".join(lines),
            drawer_view=TUIDrawerView.RECOMMENDATIONS,
        )

    @staticmethod
    def _refresh_result(result: RefreshResult) -> TUICommandResult:
        runs = len(result.collection_results)
        relevant = len(result.ranking.rankings)
        return TUICommandResult(
            ok=True,
            title="Refresh complete",
            body=(
                f"{runs} source {TUICommandService._plural(runs, 'run')} collected.\n"
                f"{result.normalization.snapshots_processed} snapshots processed.\n"
                f"{result.ranking.articles_scored} articles scored; "
                f"{relevant} relevant "
                f"{TUICommandService._plural(relevant, 'article')}."
            ),
            drawer_view=TUIDrawerView.RECOMMENDATIONS,
        )

    @staticmethod
    def _interest_list(title: str, terms: list[InterestTerm]) -> TUICommandResult:
        body = (
            "\n".join(f"- {term.name} · weight {term.weight}" for term in terms)
            if terms
            else "None saved."
        )
        return TUICommandResult(ok=True, title=title, body=body)

    def _write_interest(
        self,
        action: TUIAction,
        parameters: dict[str, str | int],
    ) -> TUICommandResult:
        value = WeightedInterestInput(
            name=str(parameters["name"]),
            weight=int(parameters["weight"]),
        )
        routes = {
            TUIAction.ADD_TOPIC: (self._interests.add_topic, "Topic saved"),
            TUIAction.UPDATE_TOPIC: (self._interests.update_topic, "Topic updated"),
            TUIAction.ADD_KEYWORD: (self._interests.add_keyword, "Keyword saved"),
            TUIAction.UPDATE_KEYWORD: (
                self._interests.update_keyword,
                "Keyword updated",
            ),
        }
        operation, title = routes[action]
        term = operation(value)
        return TUICommandResult(
            ok=True,
            title=title,
            body=f"{term.name} · weight {term.weight}",
        )

    def _remove_interest(
        self,
        action: TUIAction,
        parameters: dict[str, str | int],
    ) -> TUICommandResult:
        value = InterestNameInput(name=str(parameters["name"]))
        if action is TUIAction.REMOVE_TOPIC:
            term = self._interests.remove_topic(value)
            title = "Topic removed"
        else:
            term = self._interests.remove_keyword(value)
            title = "Keyword removed"
        return TUICommandResult(ok=True, title=title, body=term.name)

    @staticmethod
    def _feedback_result(items: list[ArticleFeedback]) -> TUICommandResult:
        body = (
            "\n".join(
                f"- #{item.article_id} · {item.title} · "
                f"{TUICommandService._decision(item)} · "
                f"{item.recorded_at.isoformat()}"
                for item in items
            )
            if items
            else "No feedback saved."
        )
        return TUICommandResult(
            ok=True,
            title="Feedback",
            body=body,
            drawer_view=TUIDrawerView.FEEDBACK,
        )

    @staticmethod
    def _decision(item: ArticleFeedback) -> str:
        return "liked" if item.decision is FeedbackDecision.LIKE else "disliked"

    @staticmethod
    def _plural(count: int, noun: str) -> str:
        return noun if count == 1 else f"{noun}s"
