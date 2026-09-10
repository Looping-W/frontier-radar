from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.ranking import RankedArticle, RankingResult


def test_rank_command_reports_deterministically_sorted_relevant_articles(monkeypatch):
    """Catches a ranking command that hides the persisted relevance outcome."""

    class FakeService:
        def rank_default_profile(self) -> RankingResult:
            return RankingResult(
                articles_scored=4,
                rankings=[
                    RankedArticle(article_id=12, title="AI agent calls tools", score=5),
                    RankedArticle(article_id=10, title="AI Agent guide", score=3),
                ],
            )

    monkeypatch.setattr(cli_module, "get_ranking_service", lambda: FakeService())

    invocation = CliRunner().invoke(cli_module.app, ["rank"])

    assert invocation.exit_code == 0
    assert "Ranking: 4 articles scored; 2 relevant articles." in invocation.output
    assert "5 | 12 | AI agent calls tools" in invocation.output
    assert "3 | 10 | AI Agent guide" in invocation.output
