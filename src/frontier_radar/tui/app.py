import re
from collections.abc import Iterable
from functools import partial

from textual import events, on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Markdown, Static

from frontier_radar.schemas.feedback import FeedbackDecision
from frontier_radar.schemas.tui import (
    TUIAction,
    TUICommand,
    TUICommandResult,
    TUIDashboard,
    TUIDrawerView,
)
from frontier_radar.services.tui import TUICommandService, TUIInputError


class ConfirmFeedbackReset(ModalScreen[bool]):
    """Require an explicit in-app decision before clearing all feedback."""

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="confirm-card"):
                yield Static("RESET FEEDBACK", id="confirm-title")
                yield Static(
                    "Clear all feedback for the default profile?\n"
                    "Articles, snapshots, and manual interest weights stay intact.",
                    id="confirm-copy",
                )
                with Horizontal(id="confirm-actions"):
                    yield Button("Cancel", id="cancel-reset")
                    yield Button("Reset feedback", id="confirm-reset", variant="error")

    @on(Button.Pressed)
    def handle_choice(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-reset":
            self.dismiss(True)
        elif event.button.id == "cancel-reset":
            self.dismiss(False)


class FrontierRadarApp(App[None]):
    """Keyboard-first session interface over the existing service layer."""

    CSS_PATH = "frontier_radar.tcss"
    TITLE = "Frontier Radar"
    SUB_TITLE = "local technology intelligence"
    COMMAND_PALETTE_DISPLAY = "Ctrl+P"
    BINDINGS = [
        ("ctrl+b", "toggle_drawer", "Data"),
        ("ctrl+l", "focus_composer", "Command"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, command_service: TUICommandService) -> None:
        super().__init__()
        self._command_service = command_service
        self._dashboard = TUIDashboard(database_status="checking")
        self._drawer_view = TUIDrawerView.EXECUTION
        self._execution_log: list[str] = []

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Horizontal(
                Static("frontierRADAR", id="app-name"),
                Static("● LIVE", id="live-indicator"),
                id="identity",
            ),
            Static("DB CHECKING · MODEL —", id="status-line"),
            id="topbar",
        )
        with Horizontal(id="workspace"):
            with Vertical(id="drawer"):
                yield Static(
                    "CURRENT SESSION",
                    id="drawer-section-current",
                    classes="drawer-section",
                )
                with Vertical(id="drawer-nav"):
                    yield Button(
                        "○  执行记录",
                        id="view-execution",
                        classes="drawer-tab",
                    )
                    yield Button(
                        "◇  推荐文章",
                        id="view-recommendations",
                        classes="drawer-tab",
                    )
                    yield Button("≡  今日简报", id="view-digest", classes="drawer-tab")
                    yield Button(
                        "♡  反馈记录",
                        id="view-feedback",
                        classes="drawer-tab",
                    )
                yield Markdown("No session activity yet.", id="drawer-content")
                yield Static(
                    "SYSTEM",
                    id="drawer-section-system",
                    classes="drawer-section",
                )
                yield Static("DATABASE  CHECKING\nMODEL     —", id="drawer-system")
                yield Static(
                    "MVP · ALLOWLISTED ONLY\nNO AUTONOMOUS ACTIONS",
                    id="drawer-boundary",
                )
            with Vertical(id="main-column"):
                yield Static("frontier\nradar", id="brand")
                yield Static(
                    "Local intelligence, explicit commands.  /help to begin.",
                    id="boundary-copy",
                )
                with Vertical(id="session-head"):
                    yield Static("执行记录", id="view-title")
                    yield Static("CURRENT PROCESS · /health", id="view-subtitle")
                yield VerticalScroll(id="timeline")
                with Vertical(id="composer-shell"):
                    with Horizontal(id="composer-row"):
                        yield Static("›", id="composer-prompt")
                        yield Input(
                            placeholder="Type an allowlisted command…",
                            id="composer",
                        )
                    yield Static(
                        "CTRL+P COMMANDS  ·  CTRL+B DATA  ·  ENTER RUN",
                        id="composer-meta",
                    )

    def on_mount(self) -> None:
        self.query_one("#composer", Input).focus()
        self.set_class(self.size.width <= 84, "narrow")
        self._load_dashboard()

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width <= 84, "narrow")

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        commands = [
            ("Help", "Show the Phase 6 command allowlist", "/help", True),
            ("Health", "Check application and database status", "/health", True),
            (
                "Model configuration",
                "Show saved non-secret model metadata",
                "/model",
                True,
            ),
            ("Refresh radar", "Collect, normalize, and rank", "/refresh", True),
            ("Rank stored articles", "Rebuild deterministic ranking", "/rank", True),
            ("Create daily brief", "Generate a brief from local data", "/digest", True),
            (
                "Collect Hacker News",
                "Collect the current top-story feed",
                "/collect hn",
                True,
            ),
            (
                "Collect all sources",
                "Run the fixed default source collection",
                "/collect all",
                True,
            ),
            ("Show topics", "List weighted profile topics", "/topics", True),
            ("Add topic", "Prefill WEIGHT and NAME", "/topic add ", False),
            ("Update topic", "Prefill WEIGHT and NAME", "/topic update ", False),
            ("Remove topic", "Prefill NAME", "/topic remove ", False),
            ("Show keywords", "List weighted profile keywords", "/keywords", True),
            ("Add keyword", "Prefill WEIGHT and NAME", "/keyword add ", False),
            (
                "Update keyword",
                "Prefill WEIGHT and NAME",
                "/keyword update ",
                False,
            ),
            ("Remove keyword", "Prefill NAME", "/keyword remove ", False),
            ("Show feedback", "List current feedback", "/feedback", True),
            ("Like article", "Prefill ARTICLE_ID", "/like ", False),
            ("Dislike article", "Prefill ARTICLE_ID", "/dislike ", False),
            ("Undo feedback", "Prefill ARTICLE_ID", "/undo ", False),
            (
                "Reset feedback",
                "Clear feedback after explicit confirmation",
                "/feedback reset",
                True,
            ),
            (
                "Collect arXiv",
                "Prefill a temporary arXiv collection query",
                "/collect arxiv ",
                False,
            ),
            (
                "Normalize snapshots",
                "Parse saved snapshots without network calls",
                "/normalize",
                True,
            ),
            ("Exit Frontier Radar", "End this local session", "/quit", True),
        ]
        for title, help_text, raw, execute in commands:
            callback = (
                partial(self._accept_raw, raw)
                if execute
                else partial(self._prefill_composer, raw)
            )
            yield SystemCommand(title, help_text, callback)

    @on(Input.Submitted, "#composer")
    def handle_submission(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.clear()
        self._accept_raw(raw)

    @on(Button.Pressed, ".drawer-tab")
    def handle_drawer_tab(self, event: Button.Pressed) -> None:
        views = {
            "view-execution": TUIDrawerView.EXECUTION,
            "view-recommendations": TUIDrawerView.RECOMMENDATIONS,
            "view-digest": TUIDrawerView.DIGEST,
            "view-feedback": TUIDrawerView.FEEDBACK,
        }
        view = views.get(event.button.id or "")
        if view is not None:
            self._show_drawer_view(view)

    def action_toggle_drawer(self) -> None:
        self.toggle_class("drawer-open")
        if self.has_class("drawer-open"):
            self._render_drawer()

    def action_focus_composer(self) -> None:
        self.query_one("#composer", Input).focus()

    def _prefill_composer(self, raw: str) -> None:
        composer = self.query_one("#composer", Input)
        composer.value = raw
        composer.focus()

    def _accept_raw(self, raw: str) -> None:
        if not raw:
            self.query_one("#composer", Input).focus()
            return
        self.add_class("started")
        self.query_one("#view-subtitle", Static).update(
            f"CURRENT PROCESS · {raw}"
        )
        self._mount_timeline(
            Horizontal(
                Static("YOU", classes="message-role"),
                Static(raw, classes="message-body"),
                classes="message-row command-message user-message",
            )
        )
        try:
            command = self._command_service.parse(raw)
        except TUIInputError as error:
            self._execution_log.append(f"FAILED  {raw}")
            self._mount_timeline(
                Static(
                    "×  INPUT REJECTED",
                    classes="signal signal-rail signal-failed",
                )
            )
            self._mount_timeline(
                Horizontal(
                    Static("RADAR", classes="message-role"),
                    Markdown(
                        f"### Command not accepted\n\n{error}",
                        classes="command-result process-body result-failed",
                    ),
                    classes="message-row radar-message",
                )
            )
            self._render_drawer()
            self.query_one("#composer", Input).focus()
            return
        if command.requires_confirmation:
            self.push_screen(
                ConfirmFeedbackReset(),
                partial(self._finish_confirmation, command),
            )
            return
        self._start_command(command)

    def _finish_confirmation(self, command: TUICommand, confirmed: bool | None) -> None:
        if confirmed:
            self._start_command(command, confirmed=True)
            return
        self._execution_log.append(f"CANCEL  {command.raw}")
        self._mount_timeline(
            Static(
                "—  CANCELLED",
                classes="signal signal-rail signal-cancelled",
            )
        )
        self._render_drawer()
        self.query_one("#composer", Input).focus()

    def _start_command(self, command: TUICommand, confirmed: bool = False) -> None:
        composer = self.query_one("#composer", Input)
        composer.disabled = True
        self._execution_log.append(f"START   {command.raw}")
        self._mount_timeline(
            Static(
                "○  RUNNING",
                classes="signal signal-rail signal-start",
            )
        )
        self._render_drawer()
        self._run_command(command, confirmed)

    @work(thread=True, group="command", exclusive=True)
    def _run_command(self, command: TUICommand, confirmed: bool) -> None:
        result = self._command_service.execute(command, confirmed=confirmed)
        self.call_from_thread(self._finish_command, command, result)

    def _finish_command(
        self,
        command: TUICommand,
        result: TUICommandResult,
    ) -> None:
        result_class = "result-ok" if result.ok else "result-failed"
        body = (
            result.body
            if command.action is TUIAction.DIGEST
            else re.sub(r"(?<!\n)\n(?!\n)", "\n\n", result.body)
        )
        self._mount_timeline(
            Horizontal(
                Static("RADAR", classes="message-role"),
                Markdown(
                    f"### {result.title}\n\n{body}",
                    classes=f"command-result process-body {result_class}",
                ),
                classes="message-row radar-message",
            )
        )
        signal_class = "signal-complete" if result.ok else "signal-failed"
        signal_text = "●  COMPLETED" if result.ok else "×  FAILED"
        self._mount_timeline(
            Static(
                signal_text,
                classes=f"signal signal-rail {signal_class}",
            )
        )
        state = "DONE" if result.ok else "FAILED"
        self._execution_log.append(f"{state:<7} {command.raw}")
        if result.drawer_view is not None:
            self._drawer_view = result.drawer_view
        self._render_drawer()
        composer = self.query_one("#composer", Input)
        composer.disabled = False
        composer.focus()
        if result.drawer_view is not None:
            self._load_dashboard()
        if result.should_quit:
            self.exit()

    @work(thread=True, group="dashboard", exclusive=True)
    def _load_dashboard(self) -> None:
        dashboard = self._command_service.load_dashboard()
        self.call_from_thread(self._apply_dashboard, dashboard)

    def _apply_dashboard(self, dashboard: TUIDashboard) -> None:
        self._dashboard = dashboard
        model = dashboard.model_label or "MODEL —"
        self.query_one("#status-line", Static).update(
            f"DB {dashboard.database_status.upper()} · {model}"
        )
        self._render_drawer()

    def _show_drawer_view(self, view: TUIDrawerView) -> None:
        self._drawer_view = view
        self._render_drawer()

    def _render_drawer(self) -> None:
        content = self.query_one("#drawer-content", Markdown)
        buttons = {
            TUIDrawerView.EXECUTION: self.query_one("#view-execution", Button),
            TUIDrawerView.RECOMMENDATIONS: self.query_one(
                "#view-recommendations", Button
            ),
            TUIDrawerView.DIGEST: self.query_one("#view-digest", Button),
            TUIDrawerView.FEEDBACK: self.query_one("#view-feedback", Button),
        }
        for view, button in buttons.items():
            button.set_class(view is self._drawer_view, "active")
        buttons[TUIDrawerView.RECOMMENDATIONS].label = (
            f"◇  推荐文章  ·  {len(self._dashboard.recommendations)}"
        )
        buttons[TUIDrawerView.FEEDBACK].label = (
            f"♡  反馈记录  ·  {len(self._dashboard.feedback)}"
        )
        model = self._dashboard.model_label or "—"
        self.query_one("#drawer-system", Static).update(
            f"DATABASE  {self._dashboard.database_status.upper()}\nMODEL     {model}"
        )
        if self._drawer_view is TUIDrawerView.EXECUTION:
            body = "**执行记录**\n\n" + (
                "\n\n".join(f"`{entry}`" for entry in self._execution_log)
                if self._execution_log
                else "No commands in this session."
            )
        elif self._drawer_view is TUIDrawerView.RECOMMENDATIONS:
            body = "**推荐文章**\n\n" + (
                "\n\n".join(
                    f"**{item.score}** · `#{item.article_id}` · {item.title}"
                    for item in self._dashboard.recommendations
                )
                if self._dashboard.recommendations
                else "No stored positive rankings. Run `/rank`."
            )
        elif self._drawer_view is TUIDrawerView.DIGEST:
            body = self._dashboard.digest_markdown or (
                "**今日简报**\n\nNo brief in this session. Run `/digest`."
            )
        else:
            body = "**反馈记录**\n\n" + (
                "\n\n".join(
                    f"`#{item.article_id}` · {item.title} · "
                    f"{self._feedback_label(item.decision)}"
                    for item in self._dashboard.feedback
                )
                if self._dashboard.feedback
                else "No feedback saved."
            )
        content.update(body)

    @staticmethod
    def _feedback_label(decision: FeedbackDecision) -> str:
        return "liked" if decision is FeedbackDecision.LIKE else "disliked"

    def _mount_timeline(self, widget: Static | Markdown | Horizontal) -> None:
        timeline = self.query_one("#timeline", VerticalScroll)
        timeline.mount(widget)
        timeline.scroll_end(animate=False)


def run_tui(command_service: TUICommandService) -> None:
    """Run the terminal application with an already assembled service boundary."""
    FrontierRadarApp(command_service).run()
