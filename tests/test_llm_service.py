from frontier_radar.schemas.llm import LLMConfiguration, LLMConfigurationInput


def test_service_configures_a_custom_provider_without_a_secret_value():
    """Catches the service bypassing the repository or adding key-like data."""
    from frontier_radar.services.llm import LLMConfigurationService

    class FakeRepository:
        def __init__(self) -> None:
            self.saved: LLMConfigurationInput | None = None

        def upsert_default(
            self, configuration: LLMConfigurationInput
        ) -> LLMConfiguration:
            self.saved = configuration
            return LLMConfiguration(id=1, **configuration.model_dump())

    repository = FakeRepository()
    service = LLMConfigurationService(repository)
    configured = service.configure(
        LLMConfigurationInput(
            provider_id="custom",
            provider_label="Internal compatible service",
            base_url="https://models.example.test/v1",
            model_name="team-curator-1",
        )
    )

    assert configured.model_name == "team-curator-1"
    assert repository.saved is not None
    assert "api_key" not in repository.saved.model_dump()
