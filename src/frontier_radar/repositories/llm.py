from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from frontier_radar.models.collection import LLMConfigurationRecord
from frontier_radar.schemas.llm import LLMConfiguration, LLMConfigurationInput

DEFAULT_LLM_CONFIGURATION_SLUG = "default"


class LLMConfigurationRepository:
    """Persist the single current non-secret model configuration."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def upsert_default(
        self, configuration: LLMConfigurationInput
    ) -> LLMConfiguration:
        """Create or replace the stable default configuration metadata."""
        with self._session_factory() as session:
            record = session.scalar(
                select(LLMConfigurationRecord).where(
                    LLMConfigurationRecord.slug == DEFAULT_LLM_CONFIGURATION_SLUG
                )
            )
            if record is None:
                record = LLMConfigurationRecord(
                    slug=DEFAULT_LLM_CONFIGURATION_SLUG,
                    **configuration.model_dump(),
                )
                session.add(record)
            else:
                for field, value in configuration.model_dump().items():
                    setattr(record, field, value)
            session.commit()
            session.refresh(record)
            return self._as_schema(record)

    def get_default(self) -> LLMConfiguration | None:
        """Return the saved default metadata without creating a configuration."""
        with self._session_factory() as session:
            record = session.scalar(
                select(LLMConfigurationRecord).where(
                    LLMConfigurationRecord.slug == DEFAULT_LLM_CONFIGURATION_SLUG
                )
            )
            return None if record is None else self._as_schema(record)

    @staticmethod
    def _as_schema(record: LLMConfigurationRecord) -> LLMConfiguration:
        return LLMConfiguration(
            id=record.id,
            provider_id=record.provider_id,
            provider_label=record.provider_label,
            api_protocol=record.api_protocol,
            base_url=record.base_url,
            model_name=record.model_name,
        )
