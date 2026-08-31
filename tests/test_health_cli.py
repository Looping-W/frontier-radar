from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.health import HealthStatus


def test_health_command_reports_database_ok(monkeypatch):
    """Catches a CLI that does not expose a successful database check."""

    class FakeService:
        def check(self) -> HealthStatus:
            return HealthStatus(database="ok")

    monkeypatch.setattr(cli_module, "get_health_service", lambda: FakeService())

    result = CliRunner().invoke(cli_module.app, ["health"])

    assert result.exit_code == 0
    assert "Application: ok" in result.output
    assert "Database: ok" in result.output


def test_health_command_returns_nonzero_when_database_is_unavailable(monkeypatch):
    """Catches a failed database check that is incorrectly reported as success."""

    class FakeService:
        def check(self) -> HealthStatus:
            return HealthStatus(database="unavailable", detail="connection refused")

    monkeypatch.setattr(cli_module, "get_health_service", lambda: FakeService())

    result = CliRunner().invoke(cli_module.app, ["health"])

    assert result.exit_code == 1
    assert "Database: unavailable" in result.output
    assert "Detail: connection refused" in result.output
