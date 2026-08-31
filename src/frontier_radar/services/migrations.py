from pathlib import Path

from alembic.config import Config

from alembic import command


class MigrationService:
    """Execute Alembic migrations without placing infrastructure logic in CLI code."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self._config_path = (
            Path(config_path) if config_path else project_root / "alembic.ini"
        )

    def upgrade(self) -> None:
        command.upgrade(Config(str(self._config_path)), "head")
