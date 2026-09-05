from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.normalization import NormalizationResult


def test_normalize_command_reports_saved_snapshot_processing_counts(monkeypatch):
    """Catches a CLI command that hides the normalization outcome from users."""

    class FakeService:
        def normalize(self) -> NormalizationResult:
            return NormalizationResult(
                snapshots_processed=32,
                raw_items_parsed=31,
                raw_items_created=31,
                articles_created=30,
                merged_items=1,
            )

    monkeypatch.setattr(cli_module, "get_normalization_service", lambda: FakeService())

    invocation = CliRunner().invoke(cli_module.app, ["normalize"])

    assert invocation.exit_code == 0
    assert (
        "Normalization: 32 snapshots processed; 31 raw items parsed; "
        "31 raw items saved; 30 articles created; 1 items merged."
    ) in invocation.output
