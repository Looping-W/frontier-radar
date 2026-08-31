from pathlib import Path

from frontier_radar.services.migrations import MigrationService


def test_migration_service_upgrades_to_head(monkeypatch):
    """Catches a migration command that targets a revision other than head."""
    revisions: list[str] = []

    monkeypatch.setattr(
        "frontier_radar.services.migrations.command.upgrade",
        lambda config, revision: revisions.append(revision),
    )

    MigrationService(Path("alembic.ini")).upgrade()

    assert revisions == ["head"]
