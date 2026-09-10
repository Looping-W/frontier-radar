from datetime import UTC, datetime

from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.collection import CollectionResult, CollectionSnapshot
from frontier_radar.schemas.normalization import NormalizationResult
from frontier_radar.schemas.ranking import RankedArticle, RankingResult
from frontier_radar.schemas.refresh import RefreshResult


def snapshot(source: str, query: str | None = None) -> CollectionSnapshot:
    """Build one offline saved-snapshot result for CLI output verification."""
    return CollectionSnapshot(
        source=source,
        endpoint="test",
        query=query,
        fetched_at=datetime(2026, 9, 10, tzinfo=UTC),
        status_code=200,
        content_type="application/json",
        raw_body="{}",
    )


def test_refresh_command_reports_collection_normalization_and_ranking_summaries(
    monkeypatch,
):
    """Catches a shortcut command that hides one pipeline stage's outcome."""

    class FakeService:
        def refresh(self) -> RefreshResult:
            return RefreshResult(
                collection_results=[
                    CollectionResult(
                        source="hacker_news",
                        item_count=30,
                        snapshots=[snapshot("hacker_news")] * 31,
                    ),
                    CollectionResult(
                        source="arxiv",
                        query="AI agent",
                        item_count=50,
                        snapshots=[snapshot("arxiv", "AI agent")],
                    ),
                ],
                normalization=NormalizationResult(
                    snapshots_processed=32,
                    raw_items_parsed=31,
                    raw_items_created=31,
                    articles_created=30,
                    merged_items=1,
                ),
                ranking=RankingResult(
                    articles_scored=30,
                    rankings=[
                        RankedArticle(
                            article_id=10,
                            title="AI Agent guide",
                            score=5,
                        )
                    ],
                ),
            )

    monkeypatch.setattr(cli_module, "get_refresh_service", lambda: FakeService())

    invocation = CliRunner().invoke(cli_module.app, ["refresh"])

    assert invocation.exit_code == 0
    assert "Refresh: 2 source runs collected." in invocation.output
    assert (
        "Hacker News: 30 items collected; 31 raw responses saved."
        in invocation.output
    )
    assert "arXiv: 50 items collected; 1 raw responses saved." in invocation.output
    assert (
        "Normalization: 32 snapshots processed; 31 raw items parsed; "
        "31 raw items saved; 30 articles created; 1 items merged."
    ) in invocation.output
    assert "Ranking: 30 articles scored; 1 relevant articles." in invocation.output
    assert "5 | 10 | AI Agent guide" in invocation.output
