import pytest
from pydantic import ValidationError


def test_configuration_input_accepts_portable_custom_provider_values():
    """Catches a configuration boundary that hard-codes a vendor or model."""
    from frontier_radar.schemas.llm import LLMConfigurationInput

    configuration = LLMConfigurationInput(
        provider_id="custom",
        provider_label="Internal compatible service",
        base_url="https://models.example.test/v1/",
        model_name="team-curator-1",
    )

    assert configuration.model_dump() == {
        "provider_id": "custom",
        "provider_label": "Internal compatible service",
        "api_protocol": "openai_compatible",
        "base_url": "https://models.example.test/v1",
        "model_name": "team-curator-1",
    }


def test_configuration_input_rejects_a_non_https_endpoint():
    """Catches an endpoint that would transmit an API key over an insecure URL."""
    from frontier_radar.schemas.llm import LLMConfigurationInput

    with pytest.raises(ValidationError, match="absolute HTTPS URL"):
        LLMConfigurationInput(
            provider_id="custom",
            provider_label="Local test service",
            base_url="http://models.example.test/v1",
            model_name="team-curator-1",
        )


def test_llm_configuration_record_persists_only_resolved_nonsecret_metadata():
    """Catches a persisted configuration that stores an API key or lacks provider ID."""
    from frontier_radar.models.collection import LLMConfigurationRecord

    record = LLMConfigurationRecord(
        slug="default",
        provider_id="custom",
        provider_label="Internal compatible service",
        api_protocol="openai_compatible",
        base_url="https://models.example.test/v1",
        model_name="team-curator-1",
    )

    assert record.slug == "default"
    assert record.provider_id == "custom"
    assert set(record.__table__.c.keys()) == {
        "id",
        "slug",
        "provider_id",
        "provider_label",
        "api_protocol",
        "base_url",
        "model_name",
    }
