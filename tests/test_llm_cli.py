from typer.testing import CliRunner

from frontier_radar.cli import app as cli_module
from frontier_radar.schemas.llm import LLMConfiguration


def test_llm_configure_prints_only_saved_nonsecret_metadata(monkeypatch):
    """Catches a command that accepts or exposes an API key while configuring."""

    class FakeService:
        def configure(self, configuration: object) -> LLMConfiguration:
            return LLMConfiguration(
                id=1,
                provider_id="custom",
                provider_label="Internal compatible service",
                api_protocol="openai_compatible",
                base_url="https://models.example.test/v1",
                model_name="team-curator-1",
            )

    monkeypatch.setattr(
        cli_module,
        "get_llm_configuration_service",
        lambda: FakeService(),
        raising=False,
    )

    invocation = CliRunner().invoke(
        cli_module.app,
        [
            "llm",
            "configure",
            "--label",
            "Internal compatible service",
            "--base-url",
            "https://models.example.test/v1",
            "--model",
            "team-curator-1",
        ],
    )

    assert invocation.exit_code == 0
    assert "Provider: Internal compatible service" in invocation.output
    assert "Endpoint: https://models.example.test/v1" in invocation.output
    assert "Model: team-curator-1" in invocation.output
    assert "API key" not in invocation.output


def test_llm_configure_rejects_an_api_key_option(monkeypatch):
    """Catches accidental addition of a secret-bearing command-line option."""
    monkeypatch.setattr(
        cli_module,
        "get_llm_configuration_service",
        lambda: object(),
        raising=False,
    )

    invocation = CliRunner().invoke(
        cli_module.app,
        [
            "llm",
            "configure",
            "--label",
            "Internal compatible service",
            "--base-url",
            "https://models.example.test/v1",
            "--model",
            "team-curator-1",
            "--api-key",
            "secret-value",
        ],
    )

    assert invocation.exit_code != 0
    assert "No such option: --api-key" in invocation.output
