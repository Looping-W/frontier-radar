import asyncio

from textual.widgets import Button, Input, Markdown

from frontier_radar.schemas.feedback import ArticleFeedback, FeedbackDecision
from frontier_radar.schemas.ranking import RankedArticle
from frontier_radar.schemas.tui import (
    TUICommandResult,
    TUIDashboard,
    TUIDrawerView,
)
from frontier_radar.services.tui import TUICommandService
from frontier_radar.tui.app import FrontierRadarApp


class FakeCommandService:
    """Offline command boundary that lets tests observe real Textual behavior."""

    parse = staticmethod(TUICommandService.parse)

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, bool]] = []
        self.dashboard_calls = 0

    def load_dashboard(self) -> TUIDashboard:
        self.dashboard_calls += 1
        return TUIDashboard(
            database_status="ok",
            model_label="Local model · example-chat",
            recommendations=[
                RankedArticle(article_id=12, title="AI Agent guide", score=5)
            ],
            feedback=[
                ArticleFeedback(
                    article_id=12,
                    title="AI Agent guide",
                    decision=FeedbackDecision.LIKE,
                    recorded_at="2026-09-13T08:30:00Z",
                )
            ],
            digest_markdown="# Current session digest\n\nA saved result.\n",
        )

    def execute(self, command, confirmed=False) -> TUICommandResult:
        self.executions.append((command.raw, confirmed))
        if self.fail:
            return TUICommandResult(
                ok=False,
                title="Command failed",
                body="database unavailable",
            )
        if command.action.value == "reset_feedback":
            return TUICommandResult(
                ok=True,
                title="Feedback reset",
                body="1 feedback item removed.",
                drawer_view=TUIDrawerView.FEEDBACK,
            )
        return TUICommandResult(
            ok=True,
            title="System health",
            body="Application: ok\nDatabase: ok",
        )


def _run(coroutine):
    return asyncio.run(coroutine)


def test_initial_screen_transitions_to_session_and_renders_worker_signals():
    """Catches a blocking or visually silent first command execution."""

    async def exercise():
        service = FakeCommandService()
        app = FrontierRadarApp(service)
        async with app.run_test(size=(120, 36)) as pilot:
            await app.workers.wait_for_complete()
            composer = app.query_one("#composer", Input)
            assert app.has_class("started") is False
            assert composer.has_focus is True

            composer.value = "/health"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert app.has_class("started") is True
            assert len(app.query(".signal-start")) == 1
            assert len(app.query(".signal-complete")) == 1
            assert len(app.query(".command-result")) == 1
            result_card = app.query_one(".command-result", Markdown)
            assert "Application: ok\n\nDatabase: ok" in result_card.source
            assert service.executions == [("/health", False)]
            assert composer.disabled is False
            assert composer.has_focus is True

    _run(exercise())


def test_session_shell_exposes_a_compact_header_and_composer_frame():
    """Catches the refined shell collapsing back into an unstructured input."""

    async def exercise():
        app = FrontierRadarApp(FakeCommandService())
        async with app.run_test(size=(120, 36)) as pilot:
            await app.workers.wait_for_complete()

            assert len(app.query("#live-indicator")) == 1
            assert len(app.query("#composer-shell")) == 1
            assert len(app.query("#composer-prompt")) == 1
            assert len(app.query("#composer-meta")) == 1

            composer = app.query_one("#composer", Input)
            composer.value = "/rank"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert len(app.query("#view-title")) == 1
            assert len(app.query("#view-subtitle")) == 1
            assert "/rank" in str(app.query_one("#view-subtitle").render())
            assert app.query_one("#brand").styles.display == "none"

    _run(exercise())


def test_session_messages_use_roles_and_a_connected_process_rail():
    """Catches the conversation reverting to heavy cards and detached signals."""

    async def exercise():
        app = FrontierRadarApp(FakeCommandService())
        async with app.run_test(size=(120, 36)) as pilot:
            await app.workers.wait_for_complete()
            composer = app.query_one("#composer", Input)
            composer.value = "/health"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()

            roles = [str(widget.render()) for widget in app.query(".message-role")]
            assert roles == ["YOU", "RADAR"]
            assert len(app.query(".user-message")) == 1
            assert len(app.query(".radar-message")) == 1
            assert len(app.query(".signal-rail")) == 2
            assert len(app.query(".process-body")) == 1

    _run(exercise())


def test_drawer_toggle_tabs_and_focus_shortcut_show_real_session_data():
    """Catches an inert drawer or a shortcut that strands keyboard focus."""

    async def exercise():
        app = FrontierRadarApp(FakeCommandService())
        async with app.run_test(size=(120, 36)) as pilot:
            await app.workers.wait_for_complete()
            assert app.has_class("drawer-open") is False

            await pilot.press("ctrl+b")
            assert app.has_class("drawer-open") is True
            await pilot.click("#view-recommendations")
            drawer_content = app.query_one("#drawer-content", Markdown)
            assert "AI Agent guide" in drawer_content.source
            await pilot.click("#view-digest")
            assert "Current session digest" in drawer_content.source
            await pilot.click("#view-feedback")
            assert "liked" in drawer_content.source

            await pilot.press("ctrl+l")
            assert app.query_one("#composer", Input).has_focus is True
            await pilot.press("ctrl+b")
            assert app.has_class("drawer-open") is False

    _run(exercise())


def test_drawer_uses_vertical_navigation_with_counts_and_active_state():
    """Catches the information drawer reverting to ambiguous horizontal tabs."""

    async def exercise():
        app = FrontierRadarApp(FakeCommandService())
        async with app.run_test(size=(120, 36)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.press("ctrl+b")

            assert len(app.query("#drawer-section-current")) == 1
            assert len(app.query("#drawer-section-system")) == 1
            assert len(app.query("#drawer-system")) == 1

            execution = app.query_one("#view-execution", Button)
            recommendations = app.query_one("#view-recommendations", Button)
            feedback = app.query_one("#view-feedback", Button)
            assert execution.has_class("active") is True
            assert "1" in str(recommendations.label)
            assert "1" in str(feedback.label)

            await pilot.click("#view-recommendations")
            assert execution.has_class("active") is False
            assert recommendations.has_class("active") is True

    _run(exercise())


def test_feedback_reset_runs_only_after_modal_confirmation():
    """Catches the TUI bypassing the destructive reset confirmation."""

    async def exercise():
        service = FakeCommandService()
        app = FrontierRadarApp(service)
        async with app.run_test(size=(120, 36)) as pilot:
            await app.workers.wait_for_complete()
            composer = app.query_one("#composer", Input)
            composer.value = "/feedback reset"
            await pilot.press("enter")
            await pilot.pause()

            assert service.executions == []
            await pilot.click("#confirm-reset")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert service.executions == [("/feedback reset", True)]
            assert len(app.query(".signal-complete")) == 1

    _run(exercise())


def test_failed_command_keeps_app_usable_and_narrow_layout_mounts():
    """Catches worker failures disabling the composer or breaking small terminals."""

    async def exercise():
        app = FrontierRadarApp(FakeCommandService(fail=True))
        async with app.run_test(size=(72, 24)) as pilot:
            await app.workers.wait_for_complete()
            composer = app.query_one("#composer", Input)
            composer.value = "/health"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert len(app.query(".signal-failed")) == 1
            assert composer.disabled is False
            assert composer.has_focus is True
            assert app.query_one("#main-column").region.width > 0
            assert app.has_class("narrow") is True
            await pilot.press("ctrl+b")
            assert app.query_one("#drawer").region.width == 72
            assert app.query_one("#main-column").styles.display == "none"

    _run(exercise())


def test_command_palette_actions_execute_safe_commands_or_prefill_arguments():
    """Catches palette entries that bypass parsing or invent required arguments."""

    async def exercise():
        service = FakeCommandService()
        app = FrontierRadarApp(service)
        async with app.run_test(size=(120, 36)):
            await app.workers.wait_for_complete()
            commands = list(app.get_system_commands(app.screen))
            frontier_titles = {
                "Help",
                "Health",
                "Model configuration",
                "Refresh radar",
                "Rank stored articles",
                "Create daily brief",
                "Collect Hacker News",
                "Collect all sources",
                "Collect arXiv",
                "Normalize snapshots",
                "Show topics",
                "Add topic",
                "Update topic",
                "Remove topic",
                "Show keywords",
                "Add keyword",
                "Update keyword",
                "Remove keyword",
                "Show feedback",
                "Like article",
                "Dislike article",
                "Undo feedback",
                "Reset feedback",
                "Exit Frontier Radar",
            }
            assert frontier_titles <= {command.title for command in commands}
            health = next(command for command in commands if command.title == "Health")
            arxiv = next(
                command for command in commands if command.title == "Collect arXiv"
            )

            health.callback()
            await app.workers.wait_for_complete()
            arxiv.callback()

            assert service.executions == [("/health", False)]
            assert app.query_one("#composer", Input).value == "/collect arxiv "

    _run(exercise())
