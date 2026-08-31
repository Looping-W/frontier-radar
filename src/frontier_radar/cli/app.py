import typer
from pydantic import ValidationError

from frontier_radar.core.settings import Settings
from frontier_radar.db.session import create_engine_and_session_factory
from frontier_radar.repositories.health import DatabaseHealthRepository
from frontier_radar.services.health import HealthService
from frontier_radar.services.migrations import MigrationService

app = typer.Typer(help="Frontier Radar technology intelligence CLI.")


@app.callback()
def main() -> None:
    """Frontier Radar command group."""


def get_health_service() -> HealthService:
    """Assemble the dependencies used by the health command."""
    settings = Settings()
    engine, _ = create_engine_and_session_factory(settings)
    return HealthService(DatabaseHealthRepository(engine))


@app.command()
def health() -> None:
    """Report application and MySQL connection health."""
    try:
        status = get_health_service().check()
    except ValidationError as error:
        typer.echo("Application: ok")
        typer.echo("Database: unavailable")
        typer.echo(f"Detail: {error}")
        raise typer.Exit(code=1) from error

    typer.echo(f"Application: {status.application}")
    typer.echo(f"Database: {status.database}")
    if status.detail:
        typer.echo(f"Detail: {status.detail}")
    raise typer.Exit(code=0 if status.database == "ok" else 1)


@app.command("db-upgrade")
def db_upgrade() -> None:
    """Upgrade the configured database to the latest Alembic revision."""
    try:
        MigrationService().upgrade()
    except Exception as error:
        typer.echo(f"Migration failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo("Database migrations upgraded to head.")
