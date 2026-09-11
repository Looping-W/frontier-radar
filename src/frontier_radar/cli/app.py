import httpx
import typer
from pydantic import ValidationError

from frontier_radar.agents.curation_agent import CurationAgent
from frontier_radar.agents.curation_tools import ReadOnlyCurationTools
from frontier_radar.agents.openai_compatible import OpenAICompatibleCurationModelClient
from frontier_radar.collectors.arxiv import ArxivCollector
from frontier_radar.collectors.hacker_news import HackerNewsCollector
from frontier_radar.core.settings import Settings
from frontier_radar.db.session import create_engine_and_session_factory
from frontier_radar.repositories.collection import CollectionSnapshotRepository
from frontier_radar.repositories.curation import CurationRepository
from frontier_radar.repositories.feedback import FeedbackRepository
from frontier_radar.repositories.health import DatabaseHealthRepository
from frontier_radar.repositories.interests import InterestRepository
from frontier_radar.repositories.llm import LLMConfigurationRepository
from frontier_radar.repositories.normalization import NormalizationRepository
from frontier_radar.repositories.ranking import RankingRepository
from frontier_radar.schemas.feedback import FeedbackDecision, FeedbackInput
from frontier_radar.schemas.interests import (
    InterestNameInput,
    InterestTerm,
    WeightedInterestInput,
)
from frontier_radar.schemas.llm import LLMConfiguration, LLMConfigurationInput
from frontier_radar.services.collection import CollectionService
from frontier_radar.services.curation import CurationService
from frontier_radar.services.feedback import FeedbackService
from frontier_radar.services.health import HealthService
from frontier_radar.services.interests import InterestService
from frontier_radar.services.llm import LLMConfigurationService
from frontier_radar.services.migrations import MigrationService
from frontier_radar.services.normalization import NormalizationService
from frontier_radar.services.ranking import RankingService
from frontier_radar.services.refresh import RefreshService

app = typer.Typer(help="Frontier Radar technology intelligence CLI.")
collect_app = typer.Typer(help="Collect public technology updates.")
interest_app = typer.Typer(help="Manage the default local interest profile.")
topic_app = typer.Typer(help="Manage weighted interest topics.")
keyword_app = typer.Typer(help="Manage weighted interest keywords.")
llm_app = typer.Typer(help="Configure the local curation model.")
feedback_app = typer.Typer(help="Record article feedback for the default profile.")
app.add_typer(collect_app, name="collect")
app.add_typer(interest_app, name="interest")
interest_app.add_typer(topic_app, name="topic")
interest_app.add_typer(keyword_app, name="keyword")
app.add_typer(llm_app, name="llm")
app.add_typer(feedback_app, name="feedback")


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


def get_normalization_service() -> NormalizationService:
    """Assemble dependencies used by the saved-snapshot normalization command."""
    settings = Settings()
    _, session_factory = create_engine_and_session_factory(settings)
    return NormalizationService(NormalizationRepository(session_factory))


def get_interest_service() -> InterestService:
    """Assemble dependencies used by default-profile interest commands."""
    settings = Settings()
    _, session_factory = create_engine_and_session_factory(settings)
    return InterestService(InterestRepository(session_factory))


def get_llm_configuration_service() -> LLMConfigurationService:
    """Assemble dependencies for non-secret curation-model configuration."""
    settings = Settings()
    _, session_factory = create_engine_and_session_factory(settings)
    return LLMConfigurationService(LLMConfigurationRepository(session_factory))


def get_curation_service() -> CurationService:
    """Assemble the configured model and the restricted local curation tools."""
    settings = Settings()
    _, session_factory = create_engine_and_session_factory(settings)
    profiles = InterestRepository(session_factory)
    repository = CurationRepository(session_factory)

    def agent_factory(configuration, api_key, limit):
        return CurationAgent(
            OpenAICompatibleCurationModelClient(configuration, api_key),
            ReadOnlyCurationTools(profiles, repository, limit),
        )

    return CurationService(
        LLMConfigurationService(LLMConfigurationRepository(session_factory)),
        profiles,
        repository,
        settings.llm_api_key,
        agent_factory,
    )


def get_ranking_service() -> RankingService:
    """Assemble dependencies used by deterministic default-profile ranking."""
    settings = Settings()
    _, session_factory = create_engine_and_session_factory(settings)
    return RankingService(
        InterestRepository(session_factory),
        RankingRepository(session_factory),
    )


def get_feedback_service() -> FeedbackService:
    """Assemble feedback writes and deterministic ranking recalculation."""
    settings = Settings()
    _, session_factory = create_engine_and_session_factory(settings)
    profiles = InterestRepository(session_factory)
    return FeedbackService(
        profiles,
        FeedbackRepository(session_factory),
        RankingService(profiles, RankingRepository(session_factory)),
    )


def get_refresh_service() -> RefreshService:
    """Assemble the existing fixed pipeline for the refresh command."""
    return RefreshService(
        get_collection_service(),
        get_normalization_service(),
        get_ranking_service(),
    )


def weighted_interest_input(name: str, weight: int) -> WeightedInterestInput:
    """Validate one CLI term and convert Pydantic errors into CLI usage errors."""
    try:
        return WeightedInterestInput(name=name, weight=weight)
    except ValidationError as error:
        raise typer.BadParameter(error.errors()[0]["msg"]) from error


def interest_name_input(name: str) -> InterestNameInput:
    """Validate one CLI term name and convert Pydantic errors into usage errors."""
    try:
        return InterestNameInput(name=name)
    except ValidationError as error:
        raise typer.BadParameter(error.errors()[0]["msg"]) from error


def feedback_input(article_id: int, decision: FeedbackDecision) -> FeedbackInput:
    """Validate an article feedback CLI argument before it reaches the service."""
    try:
        return FeedbackInput(article_id=article_id, decision=decision)
    except ValidationError as error:
        raise typer.BadParameter(error.errors()[0]["msg"]) from error


def llm_configuration_input(
    label: str,
    base_url: str,
    model: str,
    protocol: str,
) -> LLMConfigurationInput:
    """Validate non-secret CLI configuration without accepting an API key."""
    try:
        return LLMConfigurationInput(
            provider_id="custom",
            provider_label=label,
            base_url=base_url,
            model_name=model,
            api_protocol=protocol.replace("-", "_"),
        )
    except ValidationError as error:
        raise typer.BadParameter(error.errors()[0]["msg"]) from error


def echo_llm_configuration(configuration: LLMConfiguration) -> None:
    """Print only connection metadata that is safe for a terminal."""
    typer.echo(f"Provider: {configuration.provider_label}")
    typer.echo(f"Protocol: {configuration.api_protocol.replace('_', '-')}")
    typer.echo(f"Endpoint: {configuration.base_url}")
    typer.echo(f"Model: {configuration.model_name}")


def echo_saved_interest(label: str, term: InterestTerm) -> None:
    """Print a concise result for an added or updated weighted interest."""
    typer.echo(f"{label} saved: {term.name} (weight {term.weight}).")


def echo_interest_terms(label: str, terms: list[InterestTerm]) -> None:
    """Print a stable readable listing of one interest-term kind."""
    if not terms:
        typer.echo(f"{label}: none.")
        return
    typer.echo(f"{label}:")
    for term in terms:
        typer.echo(f"- {term.name} (weight {term.weight})")


def feedback_label(decision: FeedbackDecision) -> str:
    """Return concise past-tense terminal copy for one saved decision."""
    return "liked" if decision is FeedbackDecision.LIKE else "disliked"


def echo_feedback_list(feedback_items) -> None:
    """Print current profile feedback using its stable service ordering."""
    if not feedback_items:
        typer.echo("Feedback: none.")
        return
    typer.echo("Feedback:")
    for feedback in feedback_items:
        typer.echo(
            f"- {feedback.article_id} | {feedback_label(feedback.decision)} | "
            f"{feedback.recorded_at.isoformat()}"
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


@app.command("normalize")
def normalize() -> None:
    """Parse saved snapshots into traceable, deduplicated articles."""
    try:
        result = get_normalization_service().normalize()
    except Exception as error:
        typer.echo(f"Normalization failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Normalization: {result.snapshots_processed} snapshots processed; "
        f"{result.raw_items_parsed} raw items parsed; "
        f"{result.raw_items_created} raw items saved; "
        f"{result.articles_created} articles created; "
        f"{result.merged_items} items merged."
    )


@app.command("rank")
def rank() -> None:
    """Calculate and persist deterministic article relevance for the default profile."""
    try:
        result = get_ranking_service().rank_default_profile()
    except Exception as error:
        typer.echo(f"Ranking failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Ranking: {result.articles_scored} articles scored; "
        f"{len(result.rankings)} relevant articles."
    )
    for ranking in result.rankings:
        typer.echo(f"{ranking.score} | {ranking.article_id} | {ranking.title}")


@feedback_app.command("like")
def like_article(article_id: int) -> None:
    """Record that the default profile likes one currently ranked article."""
    _record_feedback(article_id, FeedbackDecision.LIKE)


@feedback_app.command("dislike")
def dislike_article(article_id: int) -> None:
    """Record explicit negative feedback for one currently ranked article."""
    _record_feedback(article_id, FeedbackDecision.SKIP)


def _record_feedback(article_id: int, decision: FeedbackDecision) -> None:
    """Delegate one validated feedback command to the service layer."""
    try:
        feedback = get_feedback_service().record(feedback_input(article_id, decision))
    except ValueError as error:
        typer.echo(f"Feedback failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Feedback saved: {feedback_label(feedback.decision)} "
        f"article {feedback.article_id}."
    )


@feedback_app.command("list")
def list_feedback() -> None:
    """List current default-profile feedback without changing it."""
    echo_feedback_list(get_feedback_service().list())


@app.command("refresh")
def refresh() -> None:
    """Collect sources, normalize snapshots, and rank default-profile articles."""
    try:
        result = get_refresh_service().refresh()
    except Exception as error:
        typer.echo(f"Refresh failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(f"Refresh: {len(result.collection_results)} source runs collected.")
    for collection_result in result.collection_results:
        echo_collection_result(collection_result)
    normalization = result.normalization
    typer.echo(
        f"Normalization: {normalization.snapshots_processed} snapshots processed; "
        f"{normalization.raw_items_parsed} raw items parsed; "
        f"{normalization.raw_items_created} raw items saved; "
        f"{normalization.articles_created} articles created; "
        f"{normalization.merged_items} items merged."
    )
    ranking = result.ranking
    typer.echo(
        f"Ranking: {ranking.articles_scored} articles scored; "
        f"{len(ranking.rankings)} relevant articles."
    )
    for article in ranking.rankings:
        typer.echo(f"{article.score} | {article.article_id} | {article.title}")


@topic_app.command("add")
def add_topic(
    name: str,
    weight: int = typer.Option(..., "--weight", help="Positive topic weight."),
) -> None:
    """Add or update a weighted topic in the default profile."""
    try:
        term = get_interest_service().add_topic(weighted_interest_input(name, weight))
    except ValueError as error:
        typer.echo(f"Interest failed: {error}")
        raise typer.Exit(code=1) from error
    echo_saved_interest("Topic", term)


@topic_app.command("list")
def list_topics() -> None:
    """List weighted topics in the default profile."""
    echo_interest_terms("Topics", get_interest_service().list_topics())


@topic_app.command("update")
def update_topic(
    name: str,
    weight: int = typer.Option(..., "--weight", help="Positive topic weight."),
) -> None:
    """Change the weight of an existing default-profile topic."""
    try:
        term = get_interest_service().update_topic(
            weighted_interest_input(name, weight)
        )
    except ValueError as error:
        typer.echo(f"Interest failed: {error}")
        raise typer.Exit(code=1) from error
    echo_saved_interest("Topic", term)


@topic_app.command("remove")
def remove_topic(name: str) -> None:
    """Remove an existing topic from the default profile."""
    try:
        term = get_interest_service().remove_topic(interest_name_input(name))
    except ValueError as error:
        typer.echo(f"Interest failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(f"Topic removed: {term.name}.")


@keyword_app.command("add")
def add_keyword(
    name: str,
    weight: int = typer.Option(..., "--weight", help="Positive keyword weight."),
) -> None:
    """Add or update a weighted keyword in the default profile."""
    try:
        term = get_interest_service().add_keyword(weighted_interest_input(name, weight))
    except ValueError as error:
        typer.echo(f"Interest failed: {error}")
        raise typer.Exit(code=1) from error
    echo_saved_interest("Keyword", term)


@keyword_app.command("list")
def list_keywords() -> None:
    """List weighted keywords in the default profile."""
    echo_interest_terms("Keywords", get_interest_service().list_keywords())


@keyword_app.command("update")
def update_keyword(
    name: str,
    weight: int = typer.Option(..., "--weight", help="Positive keyword weight."),
) -> None:
    """Change the weight of an existing default-profile keyword."""
    try:
        term = get_interest_service().update_keyword(
            weighted_interest_input(name, weight)
        )
    except ValueError as error:
        typer.echo(f"Interest failed: {error}")
        raise typer.Exit(code=1) from error
    echo_saved_interest("Keyword", term)


@keyword_app.command("remove")
def remove_keyword(name: str) -> None:
    """Remove an existing keyword from the default profile."""
    try:
        term = get_interest_service().remove_keyword(interest_name_input(name))
    except ValueError as error:
        typer.echo(f"Interest failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(f"Keyword removed: {term.name}.")


@llm_app.command("configure")
def configure_llm(
    label: str = typer.Option(..., "--label", help="Display name for this provider."),
    base_url: str = typer.Option(..., "--base-url", help="HTTPS model API endpoint."),
    model: str = typer.Option(..., "--model", help="Provider model identifier."),
    protocol: str = typer.Option(
        "openai-compatible",
        "--protocol",
        help="Supported model API protocol.",
    ),
) -> None:
    """Save non-secret custom OpenAI-compatible model metadata."""
    try:
        configuration = get_llm_configuration_service().configure(
            llm_configuration_input(label, base_url, model, protocol)
        )
    except ValueError as error:
        typer.echo(f"LLM configuration failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo("LLM configuration saved.")
    echo_llm_configuration(configuration)


@llm_app.command("show")
def show_llm() -> None:
    """Show saved non-secret curation-model metadata."""
    configuration = get_llm_configuration_service().show()
    if configuration is None:
        typer.echo("LLM configuration: none.")
        return
    echo_llm_configuration(configuration)


@app.command("digest")
def digest(
    limit: int = typer.Option(10, "--limit", min=1, max=20),
) -> None:
    """Create a structured, locally grounded Markdown daily brief."""
    try:
        result = get_curation_service().create_digest(limit)
    except Exception as error:
        typer.echo(f"Curation failed: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(result.markdown)
