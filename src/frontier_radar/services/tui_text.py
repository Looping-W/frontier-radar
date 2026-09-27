from dataclasses import dataclass
from enum import StrEnum

from frontier_radar.schemas.tui import TUILocale


class TUITextKey(StrEnum):
    """Stable identifiers for static TUI presentation copy."""

    INVALID_QUOTING = "invalid_quoting"
    EXPLICIT_COMMANDS_ONLY = "explicit_commands_only"
    NO_ARGUMENTS = "no_arguments"
    UNKNOWN_COMMAND = "unknown_command"
    USE_COLLECT = "use_collect"
    USE_DIGEST = "use_digest"
    USE_INTEREST = "use_interest"
    USE_FEEDBACK = "use_feedback"
    USE_ARTICLE_ACTION = "use_article_action"
    USE_LANGUAGE = "use_language"
    CONFIRMATION_REQUIRED_TITLE = "confirmation_required_title"
    CONFIRMATION_REQUIRED_BODY = "confirmation_required_body"
    COMMAND_FAILED = "command_failed"
    HELP_TITLE = "help_title"
    HELP_BODY = "help_body"
    EXIT_TITLE = "exit_title"
    EXIT_BODY = "exit_body"
    HEALTH_TITLE = "health_title"
    HEALTH_BODY = "health_body"
    HEALTH_DETAIL = "health_detail"
    MODEL_TITLE = "model_title"
    MODEL_EMPTY = "model_empty"
    MODEL_BODY = "model_body"
    COLLECTION_TITLE = "collection_title"
    COLLECTION_LINE = "collection_line"
    NORMALIZATION_TITLE = "normalization_title"
    NORMALIZATION_BODY = "normalization_body"
    RANKING_TITLE = "ranking_title"
    RANKING_SUMMARY = "ranking_summary"
    REFRESH_TITLE = "refresh_title"
    REFRESH_BODY = "refresh_body"
    DIGEST_TITLE = "digest_title"
    TOPICS_TITLE = "topics_title"
    KEYWORDS_TITLE = "keywords_title"
    NONE_SAVED = "none_saved"
    WEIGHTED_TERM = "weighted_term"
    TOPIC_SAVED = "topic_saved"
    TOPIC_UPDATED = "topic_updated"
    KEYWORD_SAVED = "keyword_saved"
    KEYWORD_UPDATED = "keyword_updated"
    TOPIC_REMOVED = "topic_removed"
    KEYWORD_REMOVED = "keyword_removed"
    FEEDBACK_TITLE = "feedback_title"
    FEEDBACK_EMPTY = "feedback_empty"
    FEEDBACK_LINE = "feedback_line"
    FEEDBACK_SAVED = "feedback_saved"
    FEEDBACK_SAVED_BODY = "feedback_saved_body"
    FEEDBACK_REMOVED = "feedback_removed"
    FEEDBACK_REMOVED_BODY = "feedback_removed_body"
    FEEDBACK_RESET = "feedback_reset"
    FEEDBACK_RESET_BODY = "feedback_reset_body"
    DECISION_LIKED = "decision_liked"
    DECISION_DISLIKED = "decision_disliked"
    LANGUAGE_TITLE = "language_title"
    LANGUAGE_ZH = "language_zh"
    LANGUAGE_EN = "language_en"
    CURRENT_SESSION = "current_session"
    EXECUTION = "execution"
    RECOMMENDATIONS = "recommendations"
    DAILY_BRIEF = "daily_brief"
    FEEDBACK_RECORDS = "feedback_records"
    SYSTEM = "system"
    SAFETY_BOUNDARY = "safety_boundary"
    WELCOME = "welcome"
    CURRENT_PROCESS = "current_process"
    COMPOSER_PLACEHOLDER = "composer_placeholder"
    COMPOSER_META = "composer_meta"
    STATUS_LINE = "status_line"
    DRAWER_SYSTEM = "drawer_system"
    INPUT_REJECTED = "input_rejected"
    COMMAND_NOT_ACCEPTED = "command_not_accepted"
    SIGNAL_CANCELLED = "signal_cancelled"
    SIGNAL_RUNNING = "signal_running"
    SIGNAL_COMPLETED = "signal_completed"
    SIGNAL_FAILED = "signal_failed"
    LOG_FAILED = "log_failed"
    LOG_CANCELLED = "log_cancelled"
    LOG_STARTED = "log_started"
    LOG_DONE = "log_done"
    DRAWER_EXECUTION_EMPTY = "drawer_execution_empty"
    DRAWER_RECOMMENDATIONS_EMPTY = "drawer_recommendations_empty"
    DRAWER_DIGEST_EMPTY = "drawer_digest_empty"
    DRAWER_FEEDBACK_EMPTY = "drawer_feedback_empty"
    RESET_TITLE = "reset_title"
    RESET_COPY = "reset_copy"
    CANCEL = "cancel"
    RESET_ACTION = "reset_action"


_ENGLISH: dict[TUITextKey, str] = {
    TUITextKey.INVALID_QUOTING: "Invalid quoting: {detail}",
    TUITextKey.EXPLICIT_COMMANDS_ONLY: (
        "Phase 6 accepts explicit slash commands only; use /help."
    ),
    TUITextKey.NO_ARGUMENTS: "{command} does not accept arguments",
    TUITextKey.UNKNOWN_COMMAND: "Unknown command: {command}; use /help.",
    TUITextKey.USE_COLLECT: ("Use /collect hn, /collect all, or /collect arxiv QUERY"),
    TUITextKey.USE_DIGEST: "Use /digest or /digest LIMIT",
    TUITextKey.USE_INTEREST: ("Use {command} add, update, or remove with a name"),
    TUITextKey.USE_FEEDBACK: "Use /feedback or /feedback reset",
    TUITextKey.USE_ARTICLE_ACTION: "Use {command} ARTICLE_ID",
    TUITextKey.USE_LANGUAGE: "Use /lang zh or /lang en",
    TUITextKey.CONFIRMATION_REQUIRED_TITLE: "Confirmation required",
    TUITextKey.CONFIRMATION_REQUIRED_BODY: (
        "Explicit confirmation is required before feedback reset."
    ),
    TUITextKey.COMMAND_FAILED: "Command failed",
    TUITextKey.HELP_TITLE: "Available commands",
    TUITextKey.HELP_BODY: """Core
/health · /model · /refresh · /rank · /digest [LIMIT]

Collection
/collect hn · /collect all · /collect arxiv QUERY · /normalize

Interests
/topics · /topic add|update WEIGHT NAME · /topic remove NAME
/keywords · /keyword add|update WEIGHT NAME · /keyword remove NAME

Feedback
/feedback · /like ARTICLE_ID · /dislike ARTICLE_ID · /undo ARTICLE_ID
/feedback reset

Interface
/lang zh · /lang en

Session
/help · /quit""",
    TUITextKey.EXIT_TITLE: "Exit Frontier Radar",
    TUITextKey.EXIT_BODY: "Session data will not be saved.",
    TUITextKey.HEALTH_TITLE: "System health",
    TUITextKey.HEALTH_BODY: "Application: {application}\nDatabase: {database}{detail}",
    TUITextKey.HEALTH_DETAIL: "\nDetail: {detail}",
    TUITextKey.MODEL_TITLE: "Model configuration",
    TUITextKey.MODEL_EMPTY: "No local model configuration is saved.",
    TUITextKey.MODEL_BODY: (
        "Provider: {provider}\nProtocol: {protocol}\n"
        "Endpoint: {endpoint}\nModel: {model}"
    ),
    TUITextKey.COLLECTION_TITLE: "Collection complete",
    TUITextKey.COLLECTION_LINE: (
        "{source}: {items} items collected; {snapshots} raw responses saved."
    ),
    TUITextKey.NORMALIZATION_TITLE: "Normalization complete",
    TUITextKey.NORMALIZATION_BODY: (
        "{snapshots} snapshots processed; {parsed} raw items parsed; "
        "{saved} raw items saved; {articles} articles created; "
        "{merged} items merged."
    ),
    TUITextKey.RANKING_TITLE: "Ranking complete",
    TUITextKey.RANKING_SUMMARY: (
        "{scored} articles scored; {relevant} relevant {article_word}."
    ),
    TUITextKey.REFRESH_TITLE: "Refresh complete",
    TUITextKey.REFRESH_BODY: (
        "{runs} source {run_word} collected.\n"
        "{snapshots} snapshots processed.\n"
        "{scored} articles scored; {relevant} relevant {article_word}."
    ),
    TUITextKey.DIGEST_TITLE: "Daily brief",
    TUITextKey.TOPICS_TITLE: "Topics",
    TUITextKey.KEYWORDS_TITLE: "Keywords",
    TUITextKey.NONE_SAVED: "None saved.",
    TUITextKey.WEIGHTED_TERM: "- {name} · weight {weight}",
    TUITextKey.TOPIC_SAVED: "Topic saved",
    TUITextKey.TOPIC_UPDATED: "Topic updated",
    TUITextKey.KEYWORD_SAVED: "Keyword saved",
    TUITextKey.KEYWORD_UPDATED: "Keyword updated",
    TUITextKey.TOPIC_REMOVED: "Topic removed",
    TUITextKey.KEYWORD_REMOVED: "Keyword removed",
    TUITextKey.FEEDBACK_TITLE: "Feedback",
    TUITextKey.FEEDBACK_EMPTY: "No feedback saved.",
    TUITextKey.FEEDBACK_LINE: "- #{article_id} · {title} · {decision} · {recorded_at}",
    TUITextKey.FEEDBACK_SAVED: "Feedback saved",
    TUITextKey.FEEDBACK_SAVED_BODY: "Article #{article_id} marked {decision}.",
    TUITextKey.FEEDBACK_REMOVED: "Feedback removed",
    TUITextKey.FEEDBACK_REMOVED_BODY: "Article #{article_id} is neutral.",
    TUITextKey.FEEDBACK_RESET: "Feedback reset",
    TUITextKey.FEEDBACK_RESET_BODY: "{count} feedback {item_word} removed.",
    TUITextKey.DECISION_LIKED: "liked",
    TUITextKey.DECISION_DISLIKED: "disliked",
    TUITextKey.LANGUAGE_TITLE: "Interface language",
    TUITextKey.LANGUAGE_ZH: "Switched to Chinese.",
    TUITextKey.LANGUAGE_EN: "Switched to English.",
    TUITextKey.CURRENT_SESSION: "CURRENT SESSION",
    TUITextKey.EXECUTION: "Execution",
    TUITextKey.RECOMMENDATIONS: "Recommendations",
    TUITextKey.DAILY_BRIEF: "Daily brief",
    TUITextKey.FEEDBACK_RECORDS: "Feedback",
    TUITextKey.SYSTEM: "SYSTEM",
    TUITextKey.SAFETY_BOUNDARY: ("MVP · ALLOWLISTED ONLY\nNO AUTONOMOUS ACTIONS"),
    TUITextKey.WELCOME: "Local intelligence, explicit commands.  /help to begin.",
    TUITextKey.CURRENT_PROCESS: "CURRENT PROCESS · {command}",
    TUITextKey.COMPOSER_PLACEHOLDER: "Type an allowlisted command…",
    TUITextKey.COMPOSER_META: "CTRL+P COMMANDS  ·  CTRL+B DATA  ·  ENTER RUN",
    TUITextKey.STATUS_LINE: "DB {database} · {model}",
    TUITextKey.DRAWER_SYSTEM: "DATABASE  {database}\nMODEL     {model}",
    TUITextKey.INPUT_REJECTED: "×  INPUT REJECTED",
    TUITextKey.COMMAND_NOT_ACCEPTED: "Command not accepted",
    TUITextKey.SIGNAL_CANCELLED: "—  CANCELLED",
    TUITextKey.SIGNAL_RUNNING: "○  RUNNING",
    TUITextKey.SIGNAL_COMPLETED: "●  COMPLETED",
    TUITextKey.SIGNAL_FAILED: "×  FAILED",
    TUITextKey.LOG_FAILED: "FAILED",
    TUITextKey.LOG_CANCELLED: "CANCEL",
    TUITextKey.LOG_STARTED: "START",
    TUITextKey.LOG_DONE: "DONE",
    TUITextKey.DRAWER_EXECUTION_EMPTY: "No commands in this session.",
    TUITextKey.DRAWER_RECOMMENDATIONS_EMPTY: (
        "No stored positive rankings. Run `/rank`."
    ),
    TUITextKey.DRAWER_DIGEST_EMPTY: "No brief in this session. Run `/digest`.",
    TUITextKey.DRAWER_FEEDBACK_EMPTY: "No feedback saved.",
    TUITextKey.RESET_TITLE: "RESET FEEDBACK",
    TUITextKey.RESET_COPY: (
        "Clear all feedback for the default profile?\n"
        "Articles, snapshots, and manual interest weights stay intact."
    ),
    TUITextKey.CANCEL: "Cancel",
    TUITextKey.RESET_ACTION: "Reset feedback",
}


_CHINESE: dict[TUITextKey, str] = {
    TUITextKey.INVALID_QUOTING: "引号格式无效：{detail}",
    TUITextKey.EXPLICIT_COMMANDS_ONLY: "Phase 6 只接受明确的斜杠命令；请使用 /help。",
    TUITextKey.NO_ARGUMENTS: "{command} 不接受参数",
    TUITextKey.UNKNOWN_COMMAND: "未知命令：{command}；请使用 /help。",
    TUITextKey.USE_COLLECT: "请使用 /collect hn、/collect all 或 /collect arxiv QUERY",
    TUITextKey.USE_DIGEST: "请使用 /digest 或 /digest LIMIT",
    TUITextKey.USE_INTEREST: "请使用 {command} add、update 或 remove，并提供名称",
    TUITextKey.USE_FEEDBACK: "请使用 /feedback 或 /feedback reset",
    TUITextKey.USE_ARTICLE_ACTION: "请使用 {command} ARTICLE_ID",
    TUITextKey.USE_LANGUAGE: "请使用 /lang zh 或 /lang en",
    TUITextKey.CONFIRMATION_REQUIRED_TITLE: "需要确认",
    TUITextKey.CONFIRMATION_REQUIRED_BODY: "重置反馈前需要明确确认。",
    TUITextKey.COMMAND_FAILED: "命令执行失败",
    TUITextKey.HELP_TITLE: "可用命令",
    TUITextKey.HELP_BODY: """核心
/health · /model · /refresh · /rank · /digest [LIMIT]

采集
/collect hn · /collect all · /collect arxiv QUERY · /normalize

兴趣
/topics · /topic add|update WEIGHT NAME · /topic remove NAME
/keywords · /keyword add|update WEIGHT NAME · /keyword remove NAME

反馈
/feedback · /like ARTICLE_ID · /dislike ARTICLE_ID · /undo ARTICLE_ID
/feedback reset

界面
/lang zh · /lang en

会话
/help · /quit""",
    TUITextKey.EXIT_TITLE: "退出 Frontier Radar",
    TUITextKey.EXIT_BODY: "当前会话数据不会保存。",
    TUITextKey.HEALTH_TITLE: "系统状态",
    TUITextKey.HEALTH_BODY: "应用：{application}\n数据库：{database}{detail}",
    TUITextKey.HEALTH_DETAIL: "\n详情：{detail}",
    TUITextKey.MODEL_TITLE: "模型配置",
    TUITextKey.MODEL_EMPTY: "尚未保存本地模型配置。",
    TUITextKey.MODEL_BODY: (
        "提供方：{provider}\n协议：{protocol}\nEndpoint：{endpoint}\n模型：{model}"
    ),
    TUITextKey.COLLECTION_TITLE: "采集完成",
    TUITextKey.COLLECTION_LINE: (
        "{source}：已采集 {items} 条；已保存 {snapshots} 份原始响应。"
    ),
    TUITextKey.NORMALIZATION_TITLE: "清洗完成",
    TUITextKey.NORMALIZATION_BODY: (
        "已处理 {snapshots} 个快照；解析 {parsed} 条原始数据；"
        "保存 {saved} 条原始数据；新建 {articles} 篇文章；"
        "合并 {merged} 条数据。"
    ),
    TUITextKey.RANKING_TITLE: "排序完成",
    TUITextKey.RANKING_SUMMARY: "{scored} 篇文章已评分；{relevant} 篇符合兴趣。",
    TUITextKey.REFRESH_TITLE: "刷新完成",
    TUITextKey.REFRESH_BODY: (
        "已完成 {runs} 个来源采集。\n"
        "已处理 {snapshots} 个快照。\n"
        "{scored} 篇文章已评分；{relevant} 篇符合兴趣。"
    ),
    TUITextKey.DIGEST_TITLE: "今日简报",
    TUITextKey.TOPICS_TITLE: "主题",
    TUITextKey.KEYWORDS_TITLE: "关键词",
    TUITextKey.NONE_SAVED: "尚未保存任何内容。",
    TUITextKey.WEIGHTED_TERM: "- {name} · 权重 {weight}",
    TUITextKey.TOPIC_SAVED: "主题已保存",
    TUITextKey.TOPIC_UPDATED: "主题已更新",
    TUITextKey.KEYWORD_SAVED: "关键词已保存",
    TUITextKey.KEYWORD_UPDATED: "关键词已更新",
    TUITextKey.TOPIC_REMOVED: "主题已移除",
    TUITextKey.KEYWORD_REMOVED: "关键词已移除",
    TUITextKey.FEEDBACK_TITLE: "反馈记录",
    TUITextKey.FEEDBACK_EMPTY: "尚未保存反馈。",
    TUITextKey.FEEDBACK_LINE: "- #{article_id} · {title} · {decision} · {recorded_at}",
    TUITextKey.FEEDBACK_SAVED: "反馈已保存",
    TUITextKey.FEEDBACK_SAVED_BODY: "文章 #{article_id} 已标记为{decision}。",
    TUITextKey.FEEDBACK_REMOVED: "反馈已撤销",
    TUITextKey.FEEDBACK_REMOVED_BODY: "文章 #{article_id} 已恢复为中性。",
    TUITextKey.FEEDBACK_RESET: "反馈已重置",
    TUITextKey.FEEDBACK_RESET_BODY: "已移除 {count} 条反馈。",
    TUITextKey.DECISION_LIKED: "喜欢",
    TUITextKey.DECISION_DISLIKED: "不感兴趣",
    TUITextKey.LANGUAGE_TITLE: "界面语言",
    TUITextKey.LANGUAGE_ZH: "已切换为中文。",
    TUITextKey.LANGUAGE_EN: "已切换为英文。",
    TUITextKey.CURRENT_SESSION: "当前会话",
    TUITextKey.EXECUTION: "执行记录",
    TUITextKey.RECOMMENDATIONS: "推荐文章",
    TUITextKey.DAILY_BRIEF: "今日简报",
    TUITextKey.FEEDBACK_RECORDS: "反馈记录",
    TUITextKey.SYSTEM: "系统",
    TUITextKey.SAFETY_BOUNDARY: "MVP · 仅限白名单命令\n不执行自主操作",
    TUITextKey.WELCOME: "本地情报，明确命令。输入 /help 开始。",
    TUITextKey.CURRENT_PROCESS: "当前任务 · {command}",
    TUITextKey.COMPOSER_PLACEHOLDER: "输入白名单命令…",
    TUITextKey.COMPOSER_META: "CTRL+P 命令  ·  CTRL+B 资料  ·  ENTER 执行",
    TUITextKey.STATUS_LINE: "数据库 {database} · {model}",
    TUITextKey.DRAWER_SYSTEM: "数据库  {database}\n模型    {model}",
    TUITextKey.INPUT_REJECTED: "×  输入被拒绝",
    TUITextKey.COMMAND_NOT_ACCEPTED: "命令未接受",
    TUITextKey.SIGNAL_CANCELLED: "—  已取消",
    TUITextKey.SIGNAL_RUNNING: "○  执行中",
    TUITextKey.SIGNAL_COMPLETED: "●  已完成",
    TUITextKey.SIGNAL_FAILED: "×  失败",
    TUITextKey.LOG_FAILED: "失败",
    TUITextKey.LOG_CANCELLED: "取消",
    TUITextKey.LOG_STARTED: "开始",
    TUITextKey.LOG_DONE: "完成",
    TUITextKey.DRAWER_EXECUTION_EMPTY: "当前会话还没有执行命令。",
    TUITextKey.DRAWER_RECOMMENDATIONS_EMPTY: "暂无正分推荐。请运行 `/rank`。",
    TUITextKey.DRAWER_DIGEST_EMPTY: "当前会话还没有简报。请运行 `/digest`。",
    TUITextKey.DRAWER_FEEDBACK_EMPTY: "尚未保存反馈。",
    TUITextKey.RESET_TITLE: "重置反馈",
    TUITextKey.RESET_COPY: (
        "清空默认画像的全部反馈？\n文章、快照和手动兴趣权重不会改变。"
    ),
    TUITextKey.CANCEL: "取消",
    TUITextKey.RESET_ACTION: "重置反馈",
}


_CATALOG = {
    TUILocale.EN: _ENGLISH,
    TUILocale.ZH: _CHINESE,
}


def tui_text(locale: TUILocale, key: TUITextKey, **values: object) -> str:
    """Render one complete static message without cross-language fallback."""
    return _CATALOG[locale][key].format(**values)


@dataclass(frozen=True)
class TUICommandOption:
    """One localized command-palette entry with invariant command syntax."""

    title: str
    help_text: str
    raw: str
    execute: bool


_PALETTE_EN = (
    ("/help", "Show the Phase 6 command allowlist", "/help", True),
    ("/health", "Check application and database status", "/health", True),
    ("/model", "Show saved non-secret model metadata", "/model", True),
    ("/refresh", "Collect, normalize, and rank", "/refresh", True),
    ("/rank", "Rebuild deterministic ranking", "/rank", True),
    ("/digest", "Generate a brief from local data", "/digest", True),
    ("/collect hn", "Collect the current top-story feed", "/collect hn", True),
    (
        "/collect all",
        "Run the fixed default source collection",
        "/collect all",
        True,
    ),
    (
        "/collect arxiv QUERY",
        "Collect arXiv articles; enter QUERY after prefilling",
        "/collect arxiv ",
        False,
    ),
    (
        "/normalize",
        "Parse saved snapshots without network calls",
        "/normalize",
        True,
    ),
    ("/topics", "List weighted profile topics", "/topics", True),
    (
        "/topic add WEIGHT NAME",
        "Enter WEIGHT (1–5) and NAME after prefilling",
        "/topic add ",
        False,
    ),
    (
        "/topic update WEIGHT NAME",
        "Enter WEIGHT (1–5) and NAME after prefilling",
        "/topic update ",
        False,
    ),
    ("/topic remove NAME", "Enter NAME after prefilling", "/topic remove ", False),
    ("/keywords", "List weighted profile keywords", "/keywords", True),
    (
        "/keyword add WEIGHT NAME",
        "Enter WEIGHT (1–5) and NAME after prefilling",
        "/keyword add ",
        False,
    ),
    (
        "/keyword update WEIGHT NAME",
        "Enter WEIGHT (1–5) and NAME after prefilling",
        "/keyword update ",
        False,
    ),
    ("/keyword remove NAME", "Enter NAME after prefilling", "/keyword remove ", False),
    ("/feedback", "List current feedback", "/feedback", True),
    ("/like ARTICLE_ID", "Enter ARTICLE_ID after prefilling", "/like ", False),
    ("/dislike ARTICLE_ID", "Enter ARTICLE_ID after prefilling", "/dislike ", False),
    ("/undo ARTICLE_ID", "Enter ARTICLE_ID after prefilling", "/undo ", False),
    (
        "/feedback reset",
        "Clear feedback after explicit confirmation",
        "/feedback reset",
        True,
    ),
    ("/lang zh", "Use Chinese interface copy", "/lang zh", True),
    ("/lang en", "Use English interface copy", "/lang en", True),
    ("/quit", "End this local session", "/quit", True),
)


_PALETTE_ZH = (
    ("/help", "显示 Phase 6 白名单命令", "/help", True),
    ("/health", "检查应用与数据库状态；选择后立即执行", "/health", True),
    ("/model", "显示已保存的非敏感模型信息", "/model", True),
    ("/refresh", "依次采集、清洗并排序", "/refresh", True),
    ("/rank", "重新计算已保存文章的确定性排名", "/rank", True),
    ("/digest", "根据本地数据生成策展简报", "/digest", True),
    ("/collect hn", "采集当前热门文章列表", "/collect hn", True),
    ("/collect all", "执行固定的默认来源采集", "/collect all", True),
    (
        "/collect arxiv QUERY",
        "采集 arXiv 资讯；预填命令后需要填写 QUERY 查询词",
        "/collect arxiv ",
        False,
    ),
    ("/normalize", "离线解析已保存快照", "/normalize", True),
    ("/topics", "列出画像中的加权主题", "/topics", True),
    (
        "/topic add WEIGHT NAME",
        "添加兴趣主题；需要填写 WEIGHT（1–5）和 NAME（名称）",
        "/topic add ",
        False,
    ),
    (
        "/topic update WEIGHT NAME",
        "更新兴趣主题；需要填写 WEIGHT（1–5）和 NAME（名称）",
        "/topic update ",
        False,
    ),
    (
        "/topic remove NAME",
        "移除兴趣主题；需要填写 NAME（名称）",
        "/topic remove ",
        False,
    ),
    ("/keywords", "列出画像中的加权关键词", "/keywords", True),
    (
        "/keyword add WEIGHT NAME",
        "添加兴趣关键词；需要填写 WEIGHT（1–5）和 NAME（名称）",
        "/keyword add ",
        False,
    ),
    (
        "/keyword update WEIGHT NAME",
        "更新兴趣关键词；需要填写 WEIGHT（1–5）和 NAME（名称）",
        "/keyword update ",
        False,
    ),
    (
        "/keyword remove NAME",
        "移除兴趣关键词；需要填写 NAME（名称）",
        "/keyword remove ",
        False,
    ),
    ("/feedback", "列出当前反馈", "/feedback", True),
    (
        "/like ARTICLE_ID",
        "标记为喜欢；需要填写 ARTICLE_ID（文章编号）",
        "/like ",
        False,
    ),
    (
        "/dislike ARTICLE_ID",
        "标记为不感兴趣；需要填写 ARTICLE_ID（文章编号）",
        "/dislike ",
        False,
    ),
    (
        "/undo ARTICLE_ID",
        "撤销该文章反馈；需要填写 ARTICLE_ID（文章编号）",
        "/undo ",
        False,
    ),
    ("/feedback reset", "明确确认后清空反馈", "/feedback reset", True),
    ("/lang zh", "使用中文界面文案", "/lang zh", True),
    ("/lang en", "使用英文界面文案", "/lang en", True),
    ("/quit", "结束当前本地会话", "/quit", True),
)


def tui_command_options(locale: TUILocale) -> tuple[TUICommandOption, ...]:
    """Return localized palette entries with unchanged slash commands."""
    rows = _PALETTE_ZH if locale is TUILocale.ZH else _PALETTE_EN
    return tuple(TUICommandOption(*row) for row in rows)
