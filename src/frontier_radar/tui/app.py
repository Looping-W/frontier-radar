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
    TUILocale,
)
from frontier_radar.services.tui import TUICommandService, TUIInputError
from frontier_radar.services.tui_text import (
    TUITextKey,
    tui_command_options,
    tui_text,
)


class ConfirmFeedbackReset(ModalScreen[bool]):
    """Require an explicit in-app decision before clearing all feedback."""

    def __init__(self, locale: TUILocale) -> None:
        super().__init__()
        self._locale = locale

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="confirm-card"):
                yield Static(
                    tui_text(self._locale, TUITextKey.RESET_TITLE),
                    id="confirm-title",
                )
                yield Static(
                    tui_text(self._locale, TUITextKey.RESET_COPY),
                    id="confirm-copy",
                )
                with Horizontal(id="confirm-actions"):
                    yield Button(
                        tui_text(self._locale, TUITextKey.CANCEL),
                        id="cancel-reset",
                    )
                    yield Button(
                        tui_text(self._locale, TUITextKey.RESET_ACTION),
                        id="confirm-reset",
                        variant="error",
                    )

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
        self._locale = TUILocale.ZH
        self._execution_log: list[tuple[TUITextKey, str]] = []
        self._current_command = "/health"

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
                    tui_text(self._locale, TUITextKey.CURRENT_SESSION),
                    id="drawer-section-current",
                    classes="drawer-section",
                )
                with Vertical(id="drawer-nav"):
                    yield Button(
                        tui_text(self._locale, TUITextKey.EXECUTION),
                        id="view-execution",
                        classes="drawer-tab",
                    )
                    yield Button(
                        tui_text(self._locale, TUITextKey.RECOMMENDATIONS),
                        id="view-recommendations",
                        classes="drawer-tab",
                    )
                    yield Button(
                        tui_text(self._locale, TUITextKey.DAILY_BRIEF),
                        id="view-digest",
                        classes="drawer-tab",
                    )
                    yield Button(
                        tui_text(self._locale, TUITextKey.FEEDBACK_RECORDS),
                        id="view-feedback",
                        classes="drawer-tab",
                    )
                with VerticalScroll(id="drawer-scroll"):
                    yield Markdown(
                        tui_text(
                            self._locale,
                            TUITextKey.DRAWER_EXECUTION_EMPTY,
                        ),
                        id="drawer-content",
                    )
                yield Static(
                    tui_text(self._locale, TUITextKey.SYSTEM),
                    id="drawer-section-system",
                    classes="drawer-section",
                )
                yield Static(
                    tui_text(
                        self._locale,
                        TUITextKey.DRAWER_SYSTEM,
                        database="CHECKING",
                        model="—",
                    ),
                    id="drawer-system",
                )
                yield Static(
                    tui_text(self._locale, TUITextKey.SAFETY_BOUNDARY),
                    id="drawer-boundary",
                )
            with Vertical(id="main-column"):
                yield Static("frontier\nradar", id="brand")
                yield Static(
                    tui_text(self._locale, TUITextKey.WELCOME),
                    id="boundary-copy",
                )
                with Vertical(id="session-head"):
                    yield Static(
                        tui_text(self._locale, TUITextKey.EXECUTION),
                        id="view-title",
                    )
                    yield Static(
                        tui_text(
                            self._locale,
                            TUITextKey.CURRENT_PROCESS,
                            command="/health",
                        ),
                        id="view-subtitle",
                    )
                yield VerticalScroll(id="timeline")
                with Vertical(id="composer-shell"):
                    with Horizontal(id="composer-row"):
                        yield Static("›", id="composer-prompt")
                        yield Input(
                            placeholder=tui_text(
                                self._locale,
                                TUITextKey.COMPOSER_PLACEHOLDER,
                            ),
                            id="composer",
                        )
                    yield Static(
                        tui_text(self._locale, TUITextKey.COMPOSER_META),
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
        for option in tui_command_options(self._locale):
            callback = (
                partial(self._accept_raw, option.raw)
                if option.execute
                else partial(self._prefill_composer, option.raw)
            )
            yield SystemCommand(option.title, option.help_text, callback)

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
        self._current_command = raw
        self.query_one("#view-subtitle", Static).update(
            tui_text(
                self._locale,
                TUITextKey.CURRENT_PROCESS,
                command=raw,
            )
        )
        self._mount_timeline(
            Horizontal(
                Static("YOU", classes="message-role"),
                Static(raw, classes="message-body"),
                classes="message-row command-message user-message",
            )
        )
        try:
            command = self._command_service.parse(raw, locale=self._locale)
        except TUIInputError as error:
            self._execution_log.append((TUITextKey.LOG_FAILED, raw))
            self._mount_timeline(
                Static(
                    tui_text(self._locale, TUITextKey.INPUT_REJECTED),
                    classes="signal signal-rail signal-failed",
                )
            )
            self._mount_timeline(
                Horizontal(
                    Static("RADAR", classes="message-role"),
                    Markdown(
                        "### "
                        f"{tui_text(self._locale, TUITextKey.COMMAND_NOT_ACCEPTED)}"
                        f"\n\n{error}",
                        classes="command-result process-body result-failed",
                    ),
                    classes="message-row radar-message",
                )
            )
            self._render_drawer()
            self.query_one("#composer", Input).focus()
            return
        if command.action is TUIAction.SET_LANGUAGE:
            self._locale = TUILocale(str(command.parameters["language"]))
            self._apply_locale()
        if command.requires_confirmation:
            self.push_screen(
                ConfirmFeedbackReset(self._locale),
                partial(self._finish_confirmation, command),
            )
            return
        self._start_command(command)

    def _finish_confirmation(self, command: TUICommand, confirmed: bool | None) -> None:
        if confirmed:
            self._start_command(command, confirmed=True)
            return
        self._execution_log.append((TUITextKey.LOG_CANCELLED, command.raw))
        self._mount_timeline(
            Static(
                tui_text(self._locale, TUITextKey.SIGNAL_CANCELLED),
                classes="signal signal-rail signal-cancelled",
            )
        )
        self._render_drawer()
        self.query_one("#composer", Input).focus()

    def _start_command(self, command: TUICommand, confirmed: bool = False) -> None:
        composer = self.query_one("#composer", Input)
        composer.disabled = True
        self._execution_log.append((TUITextKey.LOG_STARTED, command.raw))
        self._mount_timeline(
            Static(
                tui_text(self._locale, TUITextKey.SIGNAL_RUNNING),
                classes="signal signal-rail signal-start",
            )
        )
        self._render_drawer()
        self._run_command(command, confirmed)

    @work(thread=True, group="command", exclusive=True)
    def _run_command(self, command: TUICommand, confirmed: bool) -> None:
        result = self._command_service.execute(
            command,
            confirmed=confirmed,
            locale=self._locale,
        )
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
        signal_text = tui_text(
            self._locale,
            (
                TUITextKey.SIGNAL_COMPLETED
                if result.ok
                else TUITextKey.SIGNAL_FAILED
            ),
        )
        self._mount_timeline(
            Static(
                signal_text,
                classes=f"signal signal-rail {signal_class}",
            )
        )
        state_key = TUITextKey.LOG_DONE if result.ok else TUITextKey.LOG_FAILED
        self._execution_log.append((state_key, command.raw))
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
        model = dashboard.model_label or "—"
        self.query_one("#status-line", Static).update(
            tui_text(
                self._locale,
                TUITextKey.STATUS_LINE,
                database=dashboard.database_status.upper(),
                model=model,
            )
        )
        self._render_drawer()

    def _apply_locale(self) -> None:
        """Refresh mounted static copy without rewriting prior result cards."""
        self.query_one("#drawer-section-current", Static).update(
            tui_text(self._locale, TUITextKey.CURRENT_SESSION)
        )
        self.query_one("#drawer-section-system", Static).update(
            tui_text(self._locale, TUITextKey.SYSTEM)
        )
        self.query_one("#drawer-boundary", Static).update(
            tui_text(self._locale, TUITextKey.SAFETY_BOUNDARY)
        )
        self.query_one("#boundary-copy", Static).update(
            tui_text(self._locale, TUITextKey.WELCOME)
        )
        self.query_one("#view-title", Static).update(
            tui_text(self._locale, TUITextKey.EXECUTION)
        )
        self.query_one("#view-subtitle", Static).update(
            tui_text(
                self._locale,
                TUITextKey.CURRENT_PROCESS,
                command=self._current_command,
            )
        )
        self.query_one("#composer", Input).placeholder = tui_text(
            self._locale,
            TUITextKey.COMPOSER_PLACEHOLDER,
        )
        self.query_one("#composer-meta", Static).update(
            tui_text(self._locale, TUITextKey.COMPOSER_META)
        )
        self._apply_dashboard(self._dashboard)

    def _show_drawer_view(self, view: TUIDrawerView) -> None:
        self._drawer_view = view
        self._render_drawer()
        drawer_scroll = self.query_one("#drawer-scroll", VerticalScroll)
        drawer_scroll.scroll_home(animate=False)
        drawer_scroll.focus()

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
        buttons[TUIDrawerView.EXECUTION].label = tui_text(
            self._locale,
            TUITextKey.EXECUTION,
        )
        buttons[TUIDrawerView.RECOMMENDATIONS].label = (
            f"{tui_text(self._locale, TUITextKey.RECOMMENDATIONS)}"
            f"  ·  {len(self._dashboard.recommendations)}"
        )
        buttons[TUIDrawerView.DIGEST].label = tui_text(
            self._locale,
            TUITextKey.DAILY_BRIEF,
        )
        buttons[TUIDrawerView.FEEDBACK].label = (
            f"{tui_text(self._locale, TUITextKey.FEEDBACK_RECORDS)}"
            f"  ·  {len(self._dashboard.feedback)}"
        )
        model = self._dashboard.model_label or "—"
        self.query_one("#drawer-system", Static).update(
            tui_text(
                self._locale,
                TUITextKey.DRAWER_SYSTEM,
                database=self._dashboard.database_status.upper(),
                model=model,
            )
        )
        if self._drawer_view is TUIDrawerView.EXECUTION:
            body = f"**{tui_text(self._locale, TUITextKey.EXECUTION)}**\n\n" + (
                "\n\n".join(
                    f"`{tui_text(self._locale, state_key):<7} {raw}`"
                    for state_key, raw in self._execution_log
                )
                if self._execution_log
                else tui_text(
                    self._locale,
                    TUITextKey.DRAWER_EXECUTION_EMPTY,
                )
            )
        elif self._drawer_view is TUIDrawerView.RECOMMENDATIONS:
            body = (
                f"**{tui_text(self._locale, TUITextKey.RECOMMENDATIONS)}**\n\n"
                + (
                "\n\n".join(
                    f"**{item.score}** · `#{item.article_id}` · {item.title}"
                    for item in self._dashboard.recommendations
                )
                if self._dashboard.recommendations
                else tui_text(
                    self._locale,
                    TUITextKey.DRAWER_RECOMMENDATIONS_EMPTY,
                )
                )
            )
        elif self._drawer_view is TUIDrawerView.DIGEST:
            body = self._dashboard.digest_markdown or (
                f"**{tui_text(self._locale, TUITextKey.DAILY_BRIEF)}**\n\n"
                f"{tui_text(self._locale, TUITextKey.DRAWER_DIGEST_EMPTY)}"
            )
        else:
            body = (
                f"**{tui_text(self._locale, TUITextKey.FEEDBACK_RECORDS)}**\n\n"
                + (
                "\n\n".join(
                    f"`#{item.article_id}` · {item.title} · "
                    f"{self._feedback_label(item.decision, self._locale)}"
                    for item in self._dashboard.feedback
                )
                if self._dashboard.feedback
                else tui_text(
                    self._locale,
                    TUITextKey.DRAWER_FEEDBACK_EMPTY,
                )
                )
            )
        content.update(body)

    @staticmethod
    def _feedback_label(
        decision: FeedbackDecision,
        locale: TUILocale,
    ) -> str:
        key = (
            TUITextKey.DECISION_LIKED
            if decision is FeedbackDecision.LIKE
            else TUITextKey.DECISION_DISLIKED
        )
        return tui_text(locale, key)

    def _mount_timeline(self, widget: Static | Markdown | Horizontal) -> None:
        timeline = self.query_one("#timeline", VerticalScroll)
        timeline.mount(widget)
        timeline.scroll_end(animate=False)


def run_tui(command_service: TUICommandService) -> None:
    """Run the terminal application with an already assembled service boundary."""
    FrontierRadarApp(command_service).run()
