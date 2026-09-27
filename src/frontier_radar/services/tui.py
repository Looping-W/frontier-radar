import shlex
from typing import Protocol

from pydantic import ValidationError

from frontier_radar.schemas.collection import CollectionResult
from frontier_radar.schemas.curation import CurationLanguage
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
    TUILanguageInput,
    TUILocale,
    TUIQueryInput,
)
from frontier_radar.services.tui_text import TUITextKey, tui_text


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
    def create_digest(
        self,
        limit: int,
        language: CurationLanguage = CurationLanguage.EN,
    ) -> CurationResult: ...


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
    def parse(
        raw: str,
        locale: TUILocale = TUILocale.EN,
    ) -> TUICommand:
        """Parse one slash command without guessing user intent."""
        try:
            tokens = shlex.split(raw.strip())
        except ValueError as error:
            raise TUIInputError(
                tui_text(locale, TUITextKey.INVALID_QUOTING, detail=error)
            ) from error
        if not tokens or not tokens[0].startswith("/"):
            raise TUIInputError(
                tui_text(locale, TUITextKey.EXPLICIT_COMMANDS_ONLY)
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
                    raise TUIInputError(
                        tui_text(
                            locale,
                            TUITextKey.NO_ARGUMENTS,
                            command=command,
                        )
                    )
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
                return TUICommandService._parse_collect(raw, arguments, locale)
            if command == "/digest":
                return TUICommandService._parse_digest(raw, arguments, locale)
            if command in {"/topic", "/keyword"}:
                return TUICommandService._parse_interest(
                    raw,
                    command,
                    arguments,
                    locale,
                )
            if command == "/feedback":
                if not arguments:
                    return TUICommand(raw=raw, action=TUIAction.LIST_FEEDBACK)
                if arguments == ["reset"]:
                    return TUICommand(
                        raw=raw,
                        action=TUIAction.RESET_FEEDBACK,
                        requires_confirmation=True,
                    )
                raise TUIInputError(tui_text(locale, TUITextKey.USE_FEEDBACK))
            if command in {"/like", "/dislike", "/undo"}:
                return TUICommandService._parse_article_action(
                    raw,
                    command,
                    arguments,
                    locale,
                )
            if command == "/lang":
                return TUICommandService._parse_language(raw, arguments, locale)
        except (ValidationError, ValueError) as error:
            if isinstance(error, TUIInputError):
                raise
            raise TUIInputError(str(error)) from error

        raise TUIInputError(
            tui_text(
                locale,
                TUITextKey.UNKNOWN_COMMAND,
                command=tokens[0],
            )
        )

    @staticmethod
    def _parse_collect(
        raw: str,
        arguments: list[str],
        locale: TUILocale,
    ) -> TUICommand:
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
        raise TUIInputError(tui_text(locale, TUITextKey.USE_COLLECT))

    @staticmethod
    def _parse_digest(
        raw: str,
        arguments: list[str],
        locale: TUILocale,
    ) -> TUICommand:
        if len(arguments) > 1:
            raise TUIInputError(tui_text(locale, TUITextKey.USE_DIGEST))
        try:
            limit = TUIDigestInput(
                limit=int(arguments[0]) if arguments else 10
            ).limit
        except (ValidationError, ValueError) as error:
            raise TUIInputError(
                tui_text(locale, TUITextKey.USE_DIGEST)
            ) from error
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
        locale: TUILocale,
    ) -> TUICommand:
        if len(arguments) < 2:
            raise TUIInputError(
                tui_text(
                    locale,
                    TUITextKey.USE_INTEREST,
                    command=command,
                )
            )
        operation = arguments[0]
        kind = command.removeprefix("/")
        if operation in {"add", "update"} and len(arguments) >= 3:
            try:
                interest = WeightedInterestInput(
                    weight=int(arguments[1]),
                    name=" ".join(arguments[2:]),
                )
            except (ValidationError, ValueError) as error:
                raise TUIInputError(
                    tui_text(
                        locale,
                        TUITextKey.USE_INTEREST,
                        command=command,
                    )
                ) from error
            action = TUIAction(f"{operation}_{kind}")
            return TUICommand(
                raw=raw,
                action=action,
                parameters={"weight": interest.weight, "name": interest.name},
            )
        if operation == "remove":
            try:
                interest = InterestNameInput(name=" ".join(arguments[1:]))
            except ValidationError as error:
                raise TUIInputError(
                    tui_text(
                        locale,
                        TUITextKey.USE_INTEREST,
                        command=command,
                    )
                ) from error
            return TUICommand(
                raw=raw,
                action=TUIAction(f"remove_{kind}"),
                parameters={"name": interest.name},
            )
        raise TUIInputError(
            tui_text(locale, TUITextKey.USE_INTEREST, command=command)
        )

    @staticmethod
    def _parse_article_action(
        raw: str,
        command: str,
        arguments: list[str],
        locale: TUILocale,
    ) -> TUICommand:
        if len(arguments) != 1:
            raise TUIInputError(
                tui_text(
                    locale,
                    TUITextKey.USE_ARTICLE_ACTION,
                    command=command,
                )
            )
        try:
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
        except (ValidationError, ValueError) as error:
            raise TUIInputError(
                tui_text(
                    locale,
                    TUITextKey.USE_ARTICLE_ACTION,
                    command=command,
                )
            ) from error
        return TUICommand(
            raw=raw,
            action=action,
            parameters={"article_id": article_id},
        )

    @staticmethod
    def _parse_language(
        raw: str,
        arguments: list[str],
        locale: TUILocale,
    ) -> TUICommand:
        if len(arguments) != 1:
            raise TUIInputError(tui_text(locale, TUITextKey.USE_LANGUAGE))
        try:
            language = TUILanguageInput(language=arguments[0]).language
        except ValidationError as error:
            raise TUIInputError(
                tui_text(locale, TUITextKey.USE_LANGUAGE)
            ) from error
        return TUICommand(
            raw=raw,
            action=TUIAction.SET_LANGUAGE,
            parameters={"language": language.value},
        )

    def execute(
        self,
        command: TUICommand,
        confirmed: bool = False,
        locale: TUILocale = TUILocale.EN,
    ) -> TUICommandResult:
        """Run one validated command against explicitly injected services."""
        if command.requires_confirmation and not confirmed:
            return TUICommandResult(
                ok=False,
                title=tui_text(
                    locale,
                    TUITextKey.CONFIRMATION_REQUIRED_TITLE,
                ),
                body=tui_text(
                    locale,
                    TUITextKey.CONFIRMATION_REQUIRED_BODY,
                ),
            )
        try:
            return self._execute(command, locale)
        except Exception as error:
            return TUICommandResult(
                ok=False,
                title=tui_text(locale, TUITextKey.COMMAND_FAILED),
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

    def _execute(
        self,
        command: TUICommand,
        locale: TUILocale,
    ) -> TUICommandResult:
        action = command.action
        parameters = command.parameters
        if action is TUIAction.HELP:
            return TUICommandResult(
                ok=True,
                title=tui_text(locale, TUITextKey.HELP_TITLE),
                body=tui_text(locale, TUITextKey.HELP_BODY),
            )
        if action is TUIAction.SET_LANGUAGE:
            target = TUILocale(str(parameters["language"]))
            key = (
                TUITextKey.LANGUAGE_ZH
                if target is TUILocale.ZH
                else TUITextKey.LANGUAGE_EN
            )
            return TUICommandResult(
                ok=True,
                title=tui_text(target, TUITextKey.LANGUAGE_TITLE),
                body=tui_text(target, key),
            )
        if action is TUIAction.QUIT:
            return TUICommandResult(
                ok=True,
                title=tui_text(locale, TUITextKey.EXIT_TITLE),
                body=tui_text(locale, TUITextKey.EXIT_BODY),
                should_quit=True,
            )
        if action is TUIAction.HEALTH:
            status = self._health.check()
            detail = (
                tui_text(
                    locale,
                    TUITextKey.HEALTH_DETAIL,
                    detail=status.detail,
                )
                if status.detail
                else ""
            )
            return TUICommandResult(
                ok=status.database == "ok",
                title=tui_text(locale, TUITextKey.HEALTH_TITLE),
                body=tui_text(
                    locale,
                    TUITextKey.HEALTH_BODY,
                    application=status.application,
                    database=status.database,
                    detail=detail,
                ),
            )
        if action is TUIAction.MODEL:
            return self._model_result(self._llm.show(), locale)
        if action is TUIAction.COLLECT_HN:
            return self._collection_result(
                [self._collection.collect_hacker_news()],
                locale,
            )
        if action is TUIAction.COLLECT_ALL:
            return self._collection_result(
                self._collection.collect_all(),
                locale,
            )
        if action is TUIAction.COLLECT_ARXIV:
            return self._collection_result(
                [self._collection.collect_arxiv(str(parameters["query"]))],
                locale,
            )
        if action is TUIAction.NORMALIZE:
            return self._normalization_result(
                self._normalization.normalize(),
                locale,
            )
        if action is TUIAction.RANK:
            return self._ranking_result(
                self._ranking.rank_default_profile(),
                locale,
            )
        if action is TUIAction.REFRESH:
            if self._refresh is None:
                raise RuntimeError("Refresh service is unavailable")
            return self._refresh_result(self._refresh.refresh(), locale)
        if action is TUIAction.DIGEST:
            language = (
                CurationLanguage.ZH
                if locale is TUILocale.ZH
                else CurationLanguage.EN
            )
            result = self._curation.create_digest(
                int(parameters["limit"]),
                language=language,
            )
            self._current_digest = result.markdown
            return TUICommandResult(
                ok=True,
                title=tui_text(locale, TUITextKey.DIGEST_TITLE),
                body=result.markdown,
                drawer_view=TUIDrawerView.DIGEST,
            )
        if action is TUIAction.LIST_TOPICS:
            return self._interest_list(
                TUITextKey.TOPICS_TITLE,
                self._interests.list_topics(),
                locale,
            )
        if action is TUIAction.LIST_KEYWORDS:
            return self._interest_list(
                TUITextKey.KEYWORDS_TITLE,
                self._interests.list_keywords(),
                locale,
            )
        if action in {
            TUIAction.ADD_TOPIC,
            TUIAction.UPDATE_TOPIC,
            TUIAction.ADD_KEYWORD,
            TUIAction.UPDATE_KEYWORD,
        }:
            return self._write_interest(action, parameters, locale)
        if action in {TUIAction.REMOVE_TOPIC, TUIAction.REMOVE_KEYWORD}:
            return self._remove_interest(action, parameters, locale)
        if action is TUIAction.LIST_FEEDBACK:
            return self._feedback_result(self._feedback.list(), locale)
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
                title=tui_text(locale, TUITextKey.FEEDBACK_SAVED),
                body=tui_text(
                    locale,
                    TUITextKey.FEEDBACK_SAVED_BODY,
                    article_id=saved.article_id,
                    decision=self._decision(saved, locale),
                ),
                drawer_view=TUIDrawerView.FEEDBACK,
            )
        if action is TUIAction.UNDO:
            removed = self._feedback.undo(int(parameters["article_id"]))
            return TUICommandResult(
                ok=True,
                title=tui_text(locale, TUITextKey.FEEDBACK_REMOVED),
                body=tui_text(
                    locale,
                    TUITextKey.FEEDBACK_REMOVED_BODY,
                    article_id=removed.article_id,
                ),
                drawer_view=TUIDrawerView.FEEDBACK,
            )
        if action is TUIAction.RESET_FEEDBACK:
            count = self._feedback.reset()
            return TUICommandResult(
                ok=True,
                title=tui_text(locale, TUITextKey.FEEDBACK_RESET),
                body=tui_text(
                    locale,
                    TUITextKey.FEEDBACK_RESET_BODY,
                    count=count,
                    item_word=self._plural(count, "item"),
                ),
                drawer_view=TUIDrawerView.FEEDBACK,
            )
        raise RuntimeError(f"Unsupported action: {action}")

    @staticmethod
    def _model_result(
        configuration: LLMConfiguration | None,
        locale: TUILocale,
    ) -> TUICommandResult:
        if configuration is None:
            return TUICommandResult(
                ok=True,
                title=tui_text(locale, TUITextKey.MODEL_TITLE),
                body=tui_text(locale, TUITextKey.MODEL_EMPTY),
            )
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, TUITextKey.MODEL_TITLE),
            body=tui_text(
                locale,
                TUITextKey.MODEL_BODY,
                provider=configuration.provider_label,
                protocol=configuration.api_protocol.replace("_", "-"),
                endpoint=configuration.base_url,
                model=configuration.model_name,
            ),
        )

    @staticmethod
    def _collection_result(
        results: list[CollectionResult],
        locale: TUILocale,
    ) -> TUICommandResult:
        labels = {"hacker_news": "Hacker News", "arxiv": "arXiv"}
        lines = [
            tui_text(
                locale,
                TUITextKey.COLLECTION_LINE,
                source=labels.get(result.source, result.source),
                items=result.item_count,
                snapshots=len(result.snapshots),
            )
            for result in results
        ]
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, TUITextKey.COLLECTION_TITLE),
            body="\n".join(lines),
        )

    @staticmethod
    def _normalization_result(
        result: NormalizationResult,
        locale: TUILocale,
    ) -> TUICommandResult:
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, TUITextKey.NORMALIZATION_TITLE),
            body=tui_text(
                locale,
                TUITextKey.NORMALIZATION_BODY,
                snapshots=result.snapshots_processed,
                parsed=result.raw_items_parsed,
                saved=result.raw_items_created,
                articles=result.articles_created,
                merged=result.merged_items,
            ),
        )

    @staticmethod
    def _ranking_result(
        result: RankingResult,
        locale: TUILocale,
    ) -> TUICommandResult:
        lines = [
            tui_text(
                locale,
                TUITextKey.RANKING_SUMMARY,
                scored=result.articles_scored,
                relevant=len(result.rankings),
                article_word=TUICommandService._plural(
                    len(result.rankings),
                    "article",
                ),
            )
        ]
        lines.extend(
            f"{ranking.score} · #{ranking.article_id} · {ranking.title}"
            for ranking in result.rankings
        )
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, TUITextKey.RANKING_TITLE),
            body="\n".join(lines),
            drawer_view=TUIDrawerView.RECOMMENDATIONS,
        )

    @staticmethod
    def _refresh_result(
        result: RefreshResult,
        locale: TUILocale,
    ) -> TUICommandResult:
        runs = len(result.collection_results)
        relevant = len(result.ranking.rankings)
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, TUITextKey.REFRESH_TITLE),
            body=tui_text(
                locale,
                TUITextKey.REFRESH_BODY,
                runs=runs,
                run_word=TUICommandService._plural(runs, "run"),
                snapshots=result.normalization.snapshots_processed,
                scored=result.ranking.articles_scored,
                relevant=relevant,
                article_word=TUICommandService._plural(relevant, "article"),
            ),
            drawer_view=TUIDrawerView.RECOMMENDATIONS,
        )

    @staticmethod
    def _interest_list(
        title_key: TUITextKey,
        terms: list[InterestTerm],
        locale: TUILocale,
    ) -> TUICommandResult:
        body = (
            "\n".join(
                tui_text(
                    locale,
                    TUITextKey.WEIGHTED_TERM,
                    name=term.name,
                    weight=term.weight,
                )
                for term in terms
            )
            if terms
            else tui_text(locale, TUITextKey.NONE_SAVED)
        )
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, title_key),
            body=body,
        )

    def _write_interest(
        self,
        action: TUIAction,
        parameters: dict[str, str | int],
        locale: TUILocale,
    ) -> TUICommandResult:
        value = WeightedInterestInput(
            name=str(parameters["name"]),
            weight=int(parameters["weight"]),
        )
        routes = {
            TUIAction.ADD_TOPIC: (
                self._interests.add_topic,
                TUITextKey.TOPIC_SAVED,
            ),
            TUIAction.UPDATE_TOPIC: (
                self._interests.update_topic,
                TUITextKey.TOPIC_UPDATED,
            ),
            TUIAction.ADD_KEYWORD: (
                self._interests.add_keyword,
                TUITextKey.KEYWORD_SAVED,
            ),
            TUIAction.UPDATE_KEYWORD: (
                self._interests.update_keyword,
                TUITextKey.KEYWORD_UPDATED,
            ),
        }
        operation, title_key = routes[action]
        term = operation(value)
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, title_key),
            body=tui_text(
                locale,
                TUITextKey.WEIGHTED_TERM,
                name=term.name,
                weight=term.weight,
            ).removeprefix("- "),
        )

    def _remove_interest(
        self,
        action: TUIAction,
        parameters: dict[str, str | int],
        locale: TUILocale,
    ) -> TUICommandResult:
        value = InterestNameInput(name=str(parameters["name"]))
        if action is TUIAction.REMOVE_TOPIC:
            term = self._interests.remove_topic(value)
            title_key = TUITextKey.TOPIC_REMOVED
        else:
            term = self._interests.remove_keyword(value)
            title_key = TUITextKey.KEYWORD_REMOVED
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, title_key),
            body=term.name,
        )

    @staticmethod
    def _feedback_result(
        items: list[ArticleFeedback],
        locale: TUILocale,
    ) -> TUICommandResult:
        body = (
            "\n".join(
                tui_text(
                    locale,
                    TUITextKey.FEEDBACK_LINE,
                    article_id=item.article_id,
                    title=item.title,
                    decision=TUICommandService._decision(item, locale),
                    recorded_at=item.recorded_at.isoformat(),
                )
                for item in items
            )
            if items
            else tui_text(locale, TUITextKey.FEEDBACK_EMPTY)
        )
        return TUICommandResult(
            ok=True,
            title=tui_text(locale, TUITextKey.FEEDBACK_TITLE),
            body=body,
            drawer_view=TUIDrawerView.FEEDBACK,
        )

    @staticmethod
    def _decision(item: ArticleFeedback, locale: TUILocale) -> str:
        key = (
            TUITextKey.DECISION_LIKED
            if item.decision is FeedbackDecision.LIKE
            else TUITextKey.DECISION_DISLIKED
        )
        return tui_text(locale, key)

    @staticmethod
    def _plural(count: int, noun: str) -> str:
        return noun if count == 1 else f"{noun}s"
