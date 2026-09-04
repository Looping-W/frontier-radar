import httpx
import typer
from pydantic import ValidationError

from frontier_radar.collectors.arxiv import ArxivCollector
from frontier_radar.collectors.hacker_news import HackerNewsCollector
from frontier_radar.core.settings import Settings
from frontier_radar.db.session import create_engine_and_session_factory
from frontier_radar.repositories.collection import CollectionSnapshotRepository
from frontier_radar.repositories.health import DatabaseHealthRepository
from frontier_radar.services.collection import CollectionService
from frontier_radar.services.health import HealthService
from frontier_radar.services.migrations import MigrationService

app = typer.Typer(help="Frontier Radar technology intelligence CLI.")
collect_app = typer.Typer(help="Collect public technology updates.")
app.add_typer(collect_app, name="collect")


@app.callback()
def main() -> None:
    """Frontier Radar command group."""


def get_health_service() -> HealthService:
    """Assemble the dependencies used by the health command."""
    settings = Settings()
    engine, _ = create_engine_and_session_factory(settings)
    return HealthService(DatabaseHealthRepository(engine))


def get_collection_service() -> CollectionService:
    """Assemble dependencies used by collection commands."""
    settings = Settings()
    _, session_factory = create_engine_and_session_factory(settings)
    client = httpx.Client(timeout=20.0, follow_redirects=True)
    return CollectionService(
        CollectionSnapshotRepository(session_factory),
        HackerNewsCollector(client),
        ArxivCollector(client),
    )


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


def echo_collection_result(result: object) -> None:
    """Print a concise source-level collection result."""
    source_names = {"hacker_news": "Hacker News", "arxiv": "arXiv"}
    collection_result = result
    typer.echo(
        f"{source_names[collection_result.source]}: "
        f"{collection_result.item_count} items collected; "
        f"{len(collection_result.snapshots)} raw responses saved."
    )


@collect_app.command("hn")
def collect_hacker_news() -> None:
    """Collect the current Hacker News top-story feed."""
    try:
        echo_collection_result(get_collection_service().collect_hacker_news())
    except Exception as error:
        typer.echo(f"Collection failed: {error}")
        raise typer.Exit(code=1) from error


@collect_app.command("arxiv")
def collect_arxiv(
    query: str = typer.Option(..., "--query", help="arXiv search phrase."),
) -> None:
    """Collect recent arXiv entries for one search phrase."""
    try:
        echo_collection_result(get_collection_service().collect_arxiv(query))
    except Exception as error:
        typer.echo(f"Collection failed: {error}")
        raise typer.Exit(code=1) from error


@collect_app.command("all")
def collect_all() -> None:
    """Collect Hacker News and all default arXiv topics."""
    try:
        for result in get_collection_service().collect_all():
            echo_collection_result(result)
    except Exception as error:
        typer.echo(f"Collection failed: {error}")
        raise typer.Exit(code=1) from error
