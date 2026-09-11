from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module


def test_digest_command_prints_a_completed_markdown_brief(monkeypatch):
    """Catches a CLI command that hides the service-rendered daily brief."""
    from frontier_radar.schemas.curation import CurationDraft, CurationSelection
    from frontier_radar.services.curation import CurationResult

    class FakeService:
        def create_digest(self, limit):
            assert limit == 5
            return CurationResult(
                draft=CurationDraft(
                    overview="Saved local updates emphasize practical agent tools.",
                    articles=[
                        CurationSelection(
                            article_id=12,
                            summary="A saved summary.",
                            rationale="A saved rationale.",
                        )
                    ],
                ),
                markdown="# Frontier Radar Daily Brief — 2026-09-11\n",
            )

    monkeypatch.setattr(
        cli_module,
        "get_curation_service",
        lambda: FakeService(),
        raising=False,
    )
    invocation = CliRunner().invoke(cli_module.app, ["digest", "--limit", "5"])

    assert invocation.exit_code == 0
    assert invocation.output == "# Frontier Radar Daily Brief — 2026-09-11\n\n"
