from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from frontier_radar.schemas.feedback import ArticleFeedback
from frontier_radar.schemas.ranking import RankedArticle


class TUIAction(StrEnum):
    """Every operation explicitly allowed through the Phase 6 composer."""

    HELP = "help"
    HEALTH = "health"
    MODEL = "model"
    COLLECT_HN = "collect_hn"
    COLLECT_ALL = "collect_all"
    COLLECT_ARXIV = "collect_arxiv"
    NORMALIZE = "normalize"
    RANK = "rank"
    REFRESH = "refresh"
    DIGEST = "digest"
    LIST_TOPICS = "list_topics"
    ADD_TOPIC = "add_topic"
    UPDATE_TOPIC = "update_topic"
    REMOVE_TOPIC = "remove_topic"
    LIST_KEYWORDS = "list_keywords"
    ADD_KEYWORD = "add_keyword"
    UPDATE_KEYWORD = "update_keyword"
    REMOVE_KEYWORD = "remove_keyword"
    LIST_FEEDBACK = "list_feedback"
    RESET_FEEDBACK = "reset_feedback"
    LIKE = "like"
    DISLIKE = "dislike"
    UNDO = "undo"
    SET_LANGUAGE = "set_language"
    QUIT = "quit"


class TUILocale(StrEnum):
    """Static presentation languages supported by the local TUI."""

    ZH = "zh"
    EN = "en"


class TUICommand(BaseModel):
    """Validated command passed from the composer to the command service."""

    model_config = ConfigDict(str_strip_whitespace=True)

    raw: str = Field(min_length=1)
    action: TUIAction
    parameters: dict[str, str | int] = Field(default_factory=dict)
    requires_confirmation: bool = False


class TUIDrawerView(StrEnum):
    """Named information views available in the collapsible drawer."""

    EXECUTION = "execution"
    RECOMMENDATIONS = "recommendations"
    DIGEST = "digest"
    FEEDBACK = "feedback"


class TUICommandResult(BaseModel):
    """Validated presentation result returned by one command execution."""

    ok: bool
    title: str = Field(min_length=1)
    body: str
    drawer_view: TUIDrawerView | None = None
    should_quit: bool = False


class TUIDashboard(BaseModel):
    """Read-only stored state plus current-process content for the drawer."""

    database_status: str
    database_detail: str | None = None
    model_label: str | None = None
    recommendations: list[RankedArticle] = Field(default_factory=list)
    feedback: list[ArticleFeedback] = Field(default_factory=list)
    digest_markdown: str | None = None
    notices: list[str] = Field(default_factory=list)


class TUIDigestInput(BaseModel):
    """Validated digest size accepted by the Phase 6 command boundary."""

    limit: int = Field(ge=1, le=20)


class TUIQueryInput(BaseModel):
    """Validated free text used only as an arXiv collector query."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=512)


class TUILanguageInput(BaseModel):
    """Validated session-only language selection."""

    language: TUILocale
