from typing import Protocol

from frontier_radar.schemas.llm import LLMConfiguration, LLMConfigurationInput


class LLMConfigurationPersistence(Protocol):
    """Non-secret configuration persistence used by the CLI-facing service."""

    def upsert_default(
        self, configuration: LLMConfigurationInput
    ) -> LLMConfiguration: ...

    def get_default(self) -> LLMConfiguration | None: ...


class LLMConfigurationService:
    """Manage the one local model configuration without handling API keys."""

    def __init__(self, repository: LLMConfigurationPersistence) -> None:
        self._repository = repository

    def configure(self, configuration: LLMConfigurationInput) -> LLMConfiguration:
        """Save non-secret connection metadata for the next curation run."""
        return self._repository.upsert_default(configuration)

    def show(self) -> LLMConfiguration | None:
        """Return saved non-secret connection metadata when configured."""
        return self._repository.get_default()
