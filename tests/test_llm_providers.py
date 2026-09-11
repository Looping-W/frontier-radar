from frontier_radar.schemas.llm import LLMConfiguration


def test_initial_catalog_resolves_the_saved_custom_provider_protocol():
    """Catches selection logic that cannot evolve beyond a hard-coded provider."""
    from frontier_radar.agents.providers import ProviderCatalog

    configuration = LLMConfiguration(
        id=1,
        provider_id="custom",
        provider_label="Internal compatible service",
        api_protocol="openai_compatible",
        base_url="https://models.example.test/v1",
        model_name="team-curator-1",
    )

    provider = ProviderCatalog.initial().resolve(configuration.provider_id)

    assert provider.provider_id == "custom"
    assert provider.api_protocol == configuration.api_protocol
    assert provider.requires_api_key is True
