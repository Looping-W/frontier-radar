from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.health import HealthStatus


def test_no_argument_invocation_launches_tui_once(monkeypatch):
    """Catches the root command showing help instead of starting the TUI."""
    service = object()
    launched: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "get_tui_command_service",
        lambda: service,
        raising=False,
    )
    monkeypatch.setattr(
        cli_module,
        "run_tui",
        launched.append,
        raising=False,
    )

    invocation = CliRunner().invoke(cli_module.app, [])

    assert invocation.exit_code == 0
    assert launched == [service]


def test_named_cli_command_never_launches_tui(monkeypatch):
    """Catches the no-argument callback intercepting scriptable commands."""
    launched: list[object] = []

    class FakeHealthService:
        def check(self) -> HealthStatus:
            return HealthStatus(database="ok")

    monkeypatch.setattr(cli_module, "get_health_service", FakeHealthService)
    monkeypatch.setattr(
        cli_module,
        "run_tui",
        launched.append,
        raising=False,
    )

    invocation = CliRunner().invoke(cli_module.app, ["health"])

    assert invocation.exit_code == 0
    assert "Database: ok" in invocation.output
    assert launched == []
