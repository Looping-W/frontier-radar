from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot
from frontier_radar.schemas.curation import CurationLanguage
from frontier_radar.schemas.feedback import ArticleFeedback, FeedbackDecision
from frontier_radar.schemas.health import HealthStatus
from frontier_radar.schemas.interests import InterestTerm
from frontier_radar.schemas.llm import LLMConfiguration
from frontier_radar.schemas.normalization import NormalizationResult
from frontier_radar.schemas.ranking import RankedArticle, RankingResult
from frontier_radar.schemas.refresh import RefreshResult
from frontier_radar.schemas.tui import TUIAction, TUIDrawerView, TUILocale
from frontier_radar.services.tui import TUICommandService, TUIInputError


@pytest.mark.parametrize(
    ("raw", "action", "parameters", "requires_confirmation"),
    [
        ("/help", TUIAction.HELP, {}, False),
        ("/health", TUIAction.HEALTH, {}, False),
        ("/model", TUIAction.MODEL, {}, False),
        ("/collect hn", TUIAction.COLLECT_HN, {}, False),
        ("/collect all", TUIAction.COLLECT_ALL, {}, False),
        (
            '/collect arxiv "AI Agent systems"',
            TUIAction.COLLECT_ARXIV,
            {"query": "AI Agent systems"},
            False,
        ),
        ("/normalize", TUIAction.NORMALIZE, {}, False),
        ("/rank", TUIAction.RANK, {}, False),
        ("/refresh", TUIAction.REFRESH, {}, False),
        ("/digest", TUIAction.DIGEST, {"limit": 10}, False),
        ("/digest 5", TUIAction.DIGEST, {"limit": 5}, False),
        ("/topics", TUIAction.LIST_TOPICS, {}, False),
        (
            "/topic add 4 AI Agent",
            TUIAction.ADD_TOPIC,
            {"weight": 4, "name": "AI Agent"},
            False,
        ),
        (
            "/topic update 3 AI Agent",
            TUIAction.UPDATE_TOPIC,
            {"weight": 3, "name": "AI Agent"},
            False,
        ),
        (
            "/topic remove AI Agent",
            TUIAction.REMOVE_TOPIC,
            {"name": "AI Agent"},
            False,
        ),
        ("/keywords", TUIAction.LIST_KEYWORDS, {}, False),
        (
            "/keyword add 5 tool calling",
            TUIAction.ADD_KEYWORD,
            {"weight": 5, "name": "tool calling"},
            False,
        ),
        (
            "/keyword update 2 tool calling",
            TUIAction.UPDATE_KEYWORD,
            {"weight": 2, "name": "tool calling"},
            False,
        ),
        (
            "/keyword remove tool calling",
            TUIAction.REMOVE_KEYWORD,
            {"name": "tool calling"},
            False,
        ),
        ("/feedback", TUIAction.LIST_FEEDBACK, {}, False),
        ("/feedback reset", TUIAction.RESET_FEEDBACK, {}, True),
        ("/like 12", TUIAction.LIKE, {"article_id": 12}, False),
        ("/dislike 12", TUIAction.DISLIKE, {"article_id": 12}, False),
        ("/undo 12", TUIAction.UNDO, {"article_id": 12}, False),
        ("/lang zh", TUIAction.SET_LANGUAGE, {"language": "zh"}, False),
        ("/lang en", TUIAction.SET_LANGUAGE, {"language": "en"}, False),
        ("/quit", TUIAction.QUIT, {}, False),
    ],
)
def test_parse_accepts_only_documented_command_shapes(
    raw: str,
    action: TUIAction,
    parameters: dict[str, str | int],
    requires_confirmation: bool,
):
    """Catches missing allowlist routes or argument corruption."""
    command = TUICommandService.parse(raw)

    assert command.action is action
    assert command.parameters == parameters
    assert command.requires_confirmation is requires_confirmation


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "帮我收集 AI Agent 最新资讯",
        "/unknown",
        '/collect arxiv "unterminated',
        "/collect",
        "/collect arxiv",
        "/collect hn extra",
        "/digest 0",
        "/digest 21",
        "/digest many",
        "/topic add 0 AI Agent",
        "/topic add 6 AI Agent",
        "/topic update two AI Agent",
        "/topic remove",
        "/keyword add 3",
        "/feedback extra",
        "/like 0",
        "/dislike -1",
        "/undo article",
        "/lang",
        "/lang fr",
        "/lang zh extra",
    ],
)
def test_parse_rejects_natural_language_unknown_commands_and_invalid_arguments(
    raw: str,
):
    """Catches input that might otherwise be guessed or executed unsafely."""
    with pytest.raises(TUIInputError):
        TUICommandService.parse(raw)


def _snapshot(source: str) -> CollectionSnapshot:
    return CollectionSnapshot(
        source=source,
        endpoint="fixture",
        fetched_at=datetime(2026, 9, 13, tzinfo=UTC),
        status_code=200,
        content_type="application/json",
        raw_body="{}",
    )


class FakeServices:
    """Complete offline service bundle used to verify command routing."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.health = self.Health(self)
        self.collection = self.Collection(self)
        self.normalization = self.Normalization(self)
        self.ranking = self.Ranking(self)
        self.curation = self.Curation(self)
        self.interests = self.Interests(self)
        self.feedback = self.Feedback(self)
        self.llm = self.LLM(self)

    class Health:
        def __init__(self, owner):
            self.owner = owner

        def check(self):
            self.owner.calls.append(("health",))
            return HealthStatus(database="ok")

    class Collection:
        def __init__(self, owner):
            self.owner = owner

        def collect_hacker_news(self):
            self.owner.calls.append(("collect_hn",))
            return CollectionResult(
                source="hacker_news",
                item_count=1,
                snapshots=[_snapshot("hacker_news")],
            )

        def collect_all(self):
            self.owner.calls.append(("collect_all",))
            return [self.collect_hacker_news()]

        def collect_arxiv(self, query):
            self.owner.calls.append(("collect_arxiv", query))
            return CollectionResult(
                source="arxiv",
                query=query,
                item_count=2,
                snapshots=[_snapshot("arxiv")],
            )

    class Normalization:
        def __init__(self, owner):
            self.owner = owner

        def normalize(self):
            self.owner.calls.append(("normalize",))
            return NormalizationResult(
                snapshots_processed=3,
                raw_items_parsed=2,
                raw_items_created=2,
                articles_created=1,
                merged_items=1,
            )

    class Ranking:
        def __init__(self, owner):
            self.owner = owner

        def rank_default_profile(self):
            self.owner.calls.append(("rank",))
            return RankingResult(
                articles_scored=2,
                rankings=[
                    RankedArticle(article_id=12, title="AI Agent guide", score=5)
                ],
            )

        def list_default_profile(self, limit=20):
            self.owner.calls.append(("list_rankings", limit))
            return [RankedArticle(article_id=12, title="AI Agent guide", score=5)]

    class Curation:
        def __init__(self, owner):
            self.owner = owner

        def create_digest(self, limit, language=CurationLanguage.EN):
            self.owner.calls.append(("digest", limit, language))
            return SimpleNamespace(markdown="# Daily brief\n\nA local digest.\n")

    class Interests:
        def __init__(self, owner):
            self.owner = owner

        def list_topics(self):
            self.owner.calls.append(("list_topics",))
            return [InterestTerm(id=1, name="AI Agent", weight=4)]

        def list_keywords(self):
            self.owner.calls.append(("list_keywords",))
            return [InterestTerm(id=2, name="tool calling", weight=3)]

        def add_topic(self, value):
            self.owner.calls.append(("add_topic", value.name, value.weight))
            return InterestTerm(id=1, name=value.name, weight=value.weight)

        def update_topic(self, value):
            self.owner.calls.append(("update_topic", value.name, value.weight))
            return InterestTerm(id=1, name=value.name, weight=value.weight)

        def remove_topic(self, value):
            self.owner.calls.append(("remove_topic", value.name))
            return InterestTerm(id=1, name=value.name, weight=4)

        def add_keyword(self, value):
            self.owner.calls.append(("add_keyword", value.name, value.weight))
            return InterestTerm(id=2, name=value.name, weight=value.weight)

        def update_keyword(self, value):
            self.owner.calls.append(("update_keyword", value.name, value.weight))
            return InterestTerm(id=2, name=value.name, weight=value.weight)

        def remove_keyword(self, value):
            self.owner.calls.append(("remove_keyword", value.name))
            return InterestTerm(id=2, name=value.name, weight=3)

    class Feedback:
        def __init__(self, owner):
            self.owner = owner

        @staticmethod
        def _item(decision=FeedbackDecision.LIKE):
            return ArticleFeedback(
                article_id=12,
                title="AI Agent guide",
                decision=decision,
                recorded_at=datetime(2026, 9, 13, 8, 30, tzinfo=UTC),
            )

        def list(self):
            self.owner.calls.append(("list_feedback",))
            return [self._item()]

        def record(self, value):
            self.owner.calls.append(
                ("record_feedback", value.article_id, value.decision)
            )
            return self._item(value.decision)

        def undo(self, article_id):
            self.owner.calls.append(("undo_feedback", article_id))
            return self._item()

        def reset(self):
            self.owner.calls.append(("reset_feedback",))
            return 1

    class LLM:
        def __init__(self, owner):
            self.owner = owner

        def show(self):
            self.owner.calls.append(("model",))
            return LLMConfiguration(
                id=1,
                provider_id="custom",
                provider_label="Local model",
                api_protocol="openai_compatible",
                base_url="https://example.com/v1",
                model_name="example-chat",
            )


def _command_service(services: FakeServices) -> TUICommandService:
    return TUICommandService(
        health_service=services.health,
        collection_service=services.collection,
        normalization_service=services.normalization,
        ranking_service=services.ranking,
        curation_service=services.curation,
        interest_service=services.interests,
        feedback_service=services.feedback,
        llm_service=services.llm,
    )


@pytest.mark.parametrize(
    ("raw", "expected_call", "title", "drawer_view"),
    [
        ("/health", ("health",), "System health", None),
        ("/model", ("model",), "Model configuration", None),
        ("/collect hn", ("collect_hn",), "Collection complete", None),
        ("/collect all", ("collect_all",), "Collection complete", None),
        (
            "/collect arxiv AI Agent",
            ("collect_arxiv", "AI Agent"),
            "Collection complete",
            None,
        ),
        ("/normalize", ("normalize",), "Normalization complete", None),
        ("/rank", ("rank",), "Ranking complete", TUIDrawerView.RECOMMENDATIONS),
        (
            "/digest 5",
            ("digest", 5, CurationLanguage.EN),
            "Daily brief",
            TUIDrawerView.DIGEST,
        ),
        ("/topics", ("list_topics",), "Topics", None),
        ("/keywords", ("list_keywords",), "Keywords", None),
        (
            "/topic add 4 AI Agent",
            ("add_topic", "AI Agent", 4),
            "Topic saved",
            None,
        ),
        (
            "/topic update 3 AI Agent",
            ("update_topic", "AI Agent", 3),
            "Topic updated",
            None,
        ),
        (
            "/topic remove AI Agent",
            ("remove_topic", "AI Agent"),
            "Topic removed",
            None,
        ),
        (
            "/keyword add 5 tool calling",
            ("add_keyword", "tool calling", 5),
            "Keyword saved",
            None,
        ),
        (
            "/keyword update 2 tool calling",
            ("update_keyword", "tool calling", 2),
            "Keyword updated",
            None,
        ),
        (
            "/keyword remove tool calling",
            ("remove_keyword", "tool calling"),
            "Keyword removed",
            None,
        ),
        (
            "/feedback",
            ("list_feedback",),
            "Feedback",
            TUIDrawerView.FEEDBACK,
        ),
        (
            "/like 12",
            ("record_feedback", 12, FeedbackDecision.LIKE),
            "Feedback saved",
            TUIDrawerView.FEEDBACK,
        ),
        (
            "/dislike 12",
            ("record_feedback", 12, FeedbackDecision.SKIP),
            "Feedback saved",
            TUIDrawerView.FEEDBACK,
        ),
        (
            "/undo 12",
            ("undo_feedback", 12),
            "Feedback removed",
            TUIDrawerView.FEEDBACK,
        ),
    ],
)
def test_execute_routes_each_command_family_to_existing_services(
    raw: str,
    expected_call: tuple,
    title: str,
    drawer_view: TUIDrawerView | None,
):
    """Catches a command routed to the wrong service or drawer."""
    services = FakeServices()
    result = _command_service(services).execute(TUICommandService.parse(raw))

    assert result.ok is True
    assert result.title == title
    assert result.drawer_view is drawer_view
    assert expected_call in services.calls


def test_execute_reports_refresh_stages_and_help_and_quit_locally():
    """Catches hidden refresh stages or local commands invoking dependencies."""
    services = FakeServices()

    class Refresh:
        def refresh(self):
            services.calls.append(("refresh",))
            return RefreshResult(
                collection_results=[services.collection.collect_hacker_news()],
                normalization=services.normalization.normalize(),
                ranking=services.ranking.rank_default_profile(),
            )

    command_service = TUICommandService(
        health_service=services.health,
        collection_service=services.collection,
        normalization_service=services.normalization,
        ranking_service=services.ranking,
        curation_service=services.curation,
        interest_service=services.interests,
        feedback_service=services.feedback,
        llm_service=services.llm,
        refresh_service=Refresh(),
    )

    help_result = command_service.execute(TUICommandService.parse("/help"))
    refresh_result = command_service.execute(TUICommandService.parse("/refresh"))
    quit_result = command_service.execute(TUICommandService.parse("/quit"))

    assert "/collect arxiv QUERY" in help_result.body
    assert "1 source run" in refresh_result.body
    assert "3 snapshots processed" in refresh_result.body
    assert "1 relevant article" in refresh_result.body
    assert quit_result.should_quit is True
    assert quit_result.title == "Exit Frontier Radar"


def test_execute_localizes_static_copy_without_translating_identifiers():
    """Catches Chinese mode leaving core results English or altering identifiers."""
    services = FakeServices()
    command_service = _command_service(services)

    health = command_service.execute(
        TUICommandService.parse("/health", locale=TUILocale.ZH),
        locale=TUILocale.ZH,
    )
    model = command_service.execute(
        TUICommandService.parse("/model", locale=TUILocale.ZH),
        locale=TUILocale.ZH,
    )
    help_result = command_service.execute(
        TUICommandService.parse("/help", locale=TUILocale.ZH),
        locale=TUILocale.ZH,
    )

    assert health.title == "系统状态"
    assert health.body == "应用：ok\n数据库：ok"
    assert model.title == "模型配置"
    assert "提供方：Local model" in model.body
    assert "协议：openai-compatible" in model.body
    assert "Endpoint：https://example.com/v1" in model.body
    assert "模型：example-chat" in model.body
    assert "采集" in help_result.body
    assert "/collect arxiv QUERY" in help_result.body


def test_digest_uses_the_current_interface_language_for_model_output():
    """Catches a Chinese TUI asking the curation model for an English brief."""
    services = FakeServices()
    command_service = _command_service(services)

    result = command_service.execute(
        TUICommandService.parse("/digest 5", locale=TUILocale.ZH),
        locale=TUILocale.ZH,
    )

    assert result.title == "今日简报"
    assert ("digest", 5, CurationLanguage.ZH) in services.calls


def test_language_command_is_local_and_uses_the_target_language():
    """Catches a session-only language change invoking business dependencies."""
    services = FakeServices()
    command_service = _command_service(services)

    command = TUICommandService.parse("/lang zh")
    result = command_service.execute(command, locale=TUILocale.ZH)

    assert result.title == "界面语言"
    assert result.body == "已切换为中文。"
    assert services.calls == []


def test_parse_reports_usage_errors_in_the_selected_language():
    """Catches localized UI errors falling back to an unrelated language."""
    with pytest.raises(TUIInputError, match="请使用 /lang zh 或 /lang en"):
        TUICommandService.parse("/lang fr", locale=TUILocale.ZH)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("/digest many", "请使用 /digest 或 /digest LIMIT"),
        ("/topic add two AI Agent", "请使用 /topic add、update 或 remove"),
        ("/like article", "请使用 /like ARTICLE_ID"),
    ],
)
def test_parse_localizes_validation_errors(raw: str, message: str):
    """Catches raw English validation traces leaking into Chinese UI copy."""
    with pytest.raises(TUIInputError, match=message):
        TUICommandService.parse(raw, locale=TUILocale.ZH)


@pytest.mark.parametrize(
    ("raw", "title", "body_fragment", "confirmed"),
    [
        ("/collect hn", "采集完成", "Hacker News：已采集 1 条", False),
        ("/normalize", "清洗完成", "已处理 3 个快照", False),
        ("/rank", "排序完成", "2 篇文章已评分", False),
        ("/topics", "主题", "权重 4", False),
        ("/topic add 4 AI Agent", "主题已保存", "AI Agent · 权重 4", False),
        ("/feedback", "反馈记录", "喜欢", False),
        ("/like 12", "反馈已保存", "文章 #12 已标记为喜欢", False),
        ("/undo 12", "反馈已撤销", "文章 #12 已恢复为中性", False),
        ("/feedback reset", "反馈已重置", "已移除 1 条反馈", True),
    ],
)
def test_execute_localizes_each_service_result_family(
    raw: str,
    title: str,
    body_fragment: str,
    confirmed: bool,
):
    """Catches a command family being omitted from the Chinese catalog."""
    services = FakeServices()
    command_service = _command_service(services)

    result = command_service.execute(
        TUICommandService.parse(raw, locale=TUILocale.ZH),
        confirmed=confirmed,
        locale=TUILocale.ZH,
    )

    assert result.title == title
    assert body_fragment in result.body


def test_execute_refuses_feedback_reset_until_explicitly_confirmed():
    """Catches destructive feedback reset bypassing its confirmation gate."""
    services = FakeServices()
    command_service = _command_service(services)
    command = TUICommandService.parse("/feedback reset")

    refused = command_service.execute(command)
    confirmed = command_service.execute(command, confirmed=True)

    assert refused.ok is False
    assert "confirmation" in refused.body.lower()
    assert services.calls.count(("reset_feedback",)) == 1
    assert confirmed.ok is True
    assert confirmed.body == "1 feedback item removed."


def test_execute_converts_dependency_failure_to_recoverable_result():
    """Catches a service failure that would otherwise terminate the TUI."""
    services = FakeServices()

    def fail():
        raise RuntimeError("database unavailable")

    services.health.check = fail

    result = _command_service(services).execute(
        TUICommandService.parse("/health")
    )

    assert result.ok is False
    assert result.title == "Command failed"
    assert result.body == "database unavailable"


def test_dashboard_loads_only_read_only_stored_state_and_current_digest():
    """Catches startup work that collects, ranks, writes, or loses the digest."""
    services = FakeServices()
    command_service = _command_service(services)
    command_service.execute(TUICommandService.parse("/digest 5"))
    services.calls.clear()

    dashboard = command_service.load_dashboard()

    assert dashboard.database_status == "ok"
    assert dashboard.model_label == "Local model · example-chat"
    assert dashboard.recommendations == [
        RankedArticle(article_id=12, title="AI Agent guide", score=5)
    ]
    assert dashboard.feedback[0].article_id == 12
    assert dashboard.digest_markdown == "# Daily brief\n\nA local digest.\n"
    assert services.calls == [
        ("health",),
        ("model",),
        ("list_rankings", 20),
        ("list_feedback",),
    ]
