from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDefinition:
    """One future-selectable provider/protocol entry for the CLI wizard."""

    provider_id: str
    api_protocol: str
    requires_api_key: bool


class ProviderCatalog:
    """Resolve persisted provider IDs without coupling services to vendors."""

    def __init__(self, providers: list[ProviderDefinition]) -> None:
        self._providers = {provider.provider_id: provider for provider in providers}

    @classmethod
    def initial(cls) -> "ProviderCatalog":
        """Return the Phase 4 catalog, ready for later preset registrations."""
        return cls(
            [
                ProviderDefinition(
                    provider_id="custom",
                    api_protocol="openai_compatible",
                    requires_api_key=True,
                )
            ]
        )

    def resolve(self, provider_id: str) -> ProviderDefinition:
        """Return a supported provider definition or report an invalid selection."""
        try:
            return self._providers[provider_id]
        except KeyError as error:
            raise ValueError(f"Unsupported LLM provider: {provider_id}") from error
