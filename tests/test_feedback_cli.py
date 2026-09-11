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
                    decision="like",
                    recorded_at=datetime(2026, 9, 11, tzinfo=UTC),
                ),
                ArticleFeedback(
                    article_id=12,
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
    assert "- 10 | liked | 2026-09-11T00:00:00+00:00" in invocation.output
    assert "- 12 | disliked | 2026-09-11T00:00:00+00:00" in invocation.output
