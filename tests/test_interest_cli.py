from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.interests import InterestTerm, WeightedInterestInput


def test_interest_topic_add_uses_validated_input_and_reports_the_saved_term(
    monkeypatch,
):
    """Catches CLI wiring that bypasses validation or hides a saved topic."""

    class FakeService:
        def __init__(self) -> None:
            self.received: list[WeightedInterestInput] = []

        def add_topic(self, interest: WeightedInterestInput) -> InterestTerm:
            self.received.append(interest)
            return InterestTerm(id=1, name=interest.name, weight=interest.weight)

    service = FakeService()
    monkeypatch.setattr(cli_module, "get_interest_service", lambda: service)

    runner = CliRunner()
    saved = runner.invoke(
        cli_module.app,
        ["interest", "topic", "add", "AI Agent", "--weight", "3"],
    )
    invalid = runner.invoke(
        cli_module.app,
        ["interest", "topic", "add", "AI Agent", "--weight", "6"],
    )

    assert saved.exit_code == 0
    assert "Topic saved: AI Agent (weight 3)." in saved.output
    assert service.received == [WeightedInterestInput(name="AI Agent", weight=3)]
    assert invalid.exit_code == 2
    assert "Input should be less than or equal to 5" in invalid.output


def test_interest_commands_report_default_profile_topic_and_keyword_operations(
    monkeypatch,
):
    """Catches incomplete command groups or output that obscures changed terms."""

    class FakeService:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def list_topics(self) -> list[InterestTerm]:
            self.calls.append(("list-topics",))
            return [InterestTerm(id=1, name="AI Agent", weight=2)]

        def update_topic(self, interest: WeightedInterestInput) -> InterestTerm:
            self.calls.append(("update-topic", interest))
            return InterestTerm(id=1, name=interest.name, weight=interest.weight)

        def remove_topic(self, interest: object) -> InterestTerm:
            self.calls.append(("remove-topic", interest))
            return InterestTerm(id=1, name=interest.name, weight=2)

        def add_keyword(self, interest: WeightedInterestInput) -> InterestTerm:
            self.calls.append(("add-keyword", interest))
            return InterestTerm(id=2, name=interest.name, weight=interest.weight)

        def list_keywords(self) -> list[InterestTerm]:
            self.calls.append(("list-keywords",))
            return [InterestTerm(id=2, name="Tool calling", weight=3)]

        def update_keyword(self, interest: WeightedInterestInput) -> InterestTerm:
            self.calls.append(("update-keyword", interest))
            return InterestTerm(id=2, name=interest.name, weight=interest.weight)

        def remove_keyword(self, interest: object) -> InterestTerm:
            self.calls.append(("remove-keyword", interest))
            return InterestTerm(id=2, name=interest.name, weight=3)

    service = FakeService()
    monkeypatch.setattr(cli_module, "get_interest_service", lambda: service)
    runner = CliRunner()

    invocations = [
        runner.invoke(cli_module.app, ["interest", "topic", "list"]),
        runner.invoke(
            cli_module.app,
            ["interest", "topic", "update", "AI Agent", "--weight", "5"],
        ),
        runner.invoke(cli_module.app, ["interest", "topic", "remove", "AI Agent"]),
        runner.invoke(
            cli_module.app,
            ["interest", "keyword", "add", "Tool calling", "--weight", "3"],
        ),
        runner.invoke(cli_module.app, ["interest", "keyword", "list"]),
        runner.invoke(
            cli_module.app,
            ["interest", "keyword", "update", "Tool calling", "--weight", "4"],
        ),
        runner.invoke(
            cli_module.app,
            ["interest", "keyword", "remove", "Tool calling"],
        ),
    ]

    assert [invocation.exit_code for invocation in invocations] == [0] * 7
    assert "Topics:\n- AI Agent (weight 2)" in invocations[0].output
    assert "Topic saved: AI Agent (weight 5)." in invocations[1].output
    assert "Topic removed: AI Agent." in invocations[2].output
    assert "Keyword saved: Tool calling (weight 3)." in invocations[3].output
    assert "Keywords:\n- Tool calling (weight 3)" in invocations[4].output
    assert "Keyword saved: Tool calling (weight 4)." in invocations[5].output
    assert "Keyword removed: Tool calling." in invocations[6].output
    assert [call[0] for call in service.calls] == [
        "list-topics",
        "update-topic",
        "remove-topic",
        "add-keyword",
        "list-keywords",
        "update-keyword",
        "remove-keyword",
    ]
