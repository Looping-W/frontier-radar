from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.feedback import ArticleFeedback, FeedbackDecision


@pytest.mark.parametrize(
    ("command", "decision", "label"),
    [
        ("like", FeedbackDecision.LIKE, "liked"),
        ("dislike", FeedbackDecision.SKIP, "disliked"),
    ],
)
def test_feedback_commands_delegate_to_service_and_report_saved_choice(
    monkeypatch, command: str, decision: FeedbackDecision, label: str
):
    """Catches CLI feedback commands that bypass service validation or hide results."""

    class FakeService:
        def __init__(self) -> None:
            self.article_id: int | None = None
            self.decision: object | None = None

        def record(self, feedback):
            self.article_id = feedback.article_id
            self.decision = feedback.decision
            return ArticleFeedback(
                article_id=feedback.article_id,
                title="AI Agent guide",
                decision=feedback.decision,
                recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
            )

    service = FakeService()
    monkeypatch.setattr(
        cli_module,
        "get_feedback_service",
        lambda: service,
        raising=False,
    )

    invocation = CliRunner().invoke(cli_module.app, ["feedback", command, "12"])

    assert invocation.exit_code == 0
    assert (service.article_id, service.decision) == (12, decision)
    assert f"Feedback saved: {label} article 12." in invocation.output


def test_feedback_skip_command_is_not_available_after_renaming(monkeypatch):
    """Catches a deprecated skip alias that keeps ambiguous semantics alive."""

    class FakeService:
        def record(self, feedback):
            return ArticleFeedback(
                article_id=feedback.article_id,
                title="AI Agent guide",
                decision=feedback.decision,
                recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
            )

    monkeypatch.setattr(
        cli_module,
        "get_feedback_service",
        lambda: FakeService(),
        raising=False,
    )

    invocation = CliRunner().invoke(cli_module.app, ["feedback", "skip", "12"])

    assert invocation.exit_code != 0
    assert "No such command 'skip'" in invocation.output


def test_feedback_list_command_prints_current_choices_in_stable_order(monkeypatch):
    """Catches a feedback listing that bypasses the service's stable output."""

    class FakeService:
        def list(self) -> list[ArticleFeedback]:
            return [
                ArticleFeedback(
                    article_id=10,
                    title="AI Agent guide",
                    decision="like",
                    recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                ArticleFeedback(
                    article_id=12,
                    title="Tool calling patterns",
                    decision="skip",
                    recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
            ]

    monkeypatch.setattr(
        cli_module,
        "get_feedback_service",
        lambda: FakeService(),
        raising=False,
    )

    invocation = CliRunner().invoke(cli_module.app, ["feedback", "list"])

    assert invocation.exit_code == 0
    assert "Feedback:" in invocation.output
    assert (
        "- 10 | AI Agent guide | liked | 2026-09-11T00:00:00+00:00"
        in invocation.output
    )
    assert (
        "- 12 | Tool calling patterns | disliked | 2026-09-11T00:00:00+00:00"
        in invocation.output
    )


def test_feedback_undo_command_delegates_to_service_and_reports_neutral_state(
    monkeypatch,
):
    """Catches an undo command that leaves learned feedback active."""

    class FakeService:
        def __init__(self) -> None:
            self.article_id: int | None = None

        def undo(self, article_id: int) -> ArticleFeedback:
            self.article_id = article_id
            return ArticleFeedback(
                article_id=article_id,
                title="AI Agent guide",
                decision="like",
                recorded_at=datetime(2026, 9, 12, tzinfo=UTC),
            )

    service = FakeService()
    monkeypatch.setattr(cli_module, "get_feedback_service", lambda: service)

    invocation = CliRunner().invoke(cli_module.app, ["feedback", "undo", "12"])

    assert invocation.exit_code == 0
    assert service.article_id == 12
    assert "Feedback removed: article 12 is neutral." in invocation.output


@pytest.mark.parametrize(
    ("answer", "expected_calls", "expected_output"),
    [
        ("n\n", 0, "Feedback reset cancelled."),
        ("y\n", 1, "Feedback reset: 2 feedback items removed."),
    ],
)
def test_feedback_reset_requires_confirmation_before_delegating(
    monkeypatch,
    answer: str,
    expected_calls: int,
    expected_output: str,
):
    """Catches feedback reset that deletes data without an explicit y/n choice."""

    class FakeService:
        def __init__(self) -> None:
            self.calls = 0

        def reset(self) -> int:
            self.calls += 1
            return 2

    service = FakeService()
    monkeypatch.setattr(cli_module, "get_feedback_service", lambda: service)

    invocation = CliRunner().invoke(
        cli_module.app,
        ["feedback", "reset"],
        input=answer,
    )

    assert invocation.exit_code == 0
    assert "Delete all feedback? This cannot be undone. [y/N]:" in invocation.output
    assert service.calls == expected_calls
    assert expected_output in invocation.output
