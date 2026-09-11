from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMConfigurationInput(BaseModel):
    """Non-secret model connection settings supplied by the local CLI."""

    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: str = Field(min_length=1, max_length=128)
    provider_label: str = Field(min_length=1, max_length=128)
    api_protocol: Literal["openai_compatible"] = "openai_compatible"
    base_url: str = Field(min_length=8, max_length=2048)
    model_name: str = Field(min_length=1, max_length=255)

    @field_validator("base_url")
    @classmethod
    def require_https(cls, value: str) -> str:
        """Reject endpoints that would send the runtime key over plain HTTP."""
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTPS URL")
        return value.rstrip("/")


class LLMConfiguration(LLMConfigurationInput):
    """One saved non-secret model configuration safe to return to callers."""

    id: int = Field(gt=0)
