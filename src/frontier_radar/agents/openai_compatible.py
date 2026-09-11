from typing import Any

from frontier_radar.agents.contracts import (
    ModelMessage,
    ModelReply,
    ToolCall,
    ToolDefinition,
)
from frontier_radar.schemas.llm import LLMConfiguration


class OpenAICompatibleCurationModelClient:
    """Adapter for user-configured OpenAI-compatible model endpoints."""

    def __init__(
        self,
        configuration: LLMConfiguration,
        api_key: str,
        client: Any | None = None,
    ) -> None:
        if configuration.api_protocol != "openai_compatible":
            raise ValueError(
                f"Unsupported model protocol: {configuration.api_protocol}"
            )
        self._configuration = configuration
        self._client = client or self._create_client(
            api_key=api_key,
            base_url=configuration.base_url,
        )

    @staticmethod
    def _create_client(api_key: str, base_url: str) -> Any:
        from openai import OpenAI

        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30.0,
            max_retries=2,
        )

    def complete(
        self,
        messages: list[ModelMessage],
        tools: list[ToolDefinition],
    ) -> ModelReply:
        """Run one compatible chat-completions turn without logging secrets."""
        response = self._client.chat.completions.create(
            model=self._configuration.model_name,
            messages=[message.as_openai_payload() for message in messages],
            tools=[tool.as_openai_payload() for tool in tools],
        )
        message = response.choices[0].message
        return ModelReply(
            content=message.content,
            tool_calls=[
                ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments_json=tool_call.function.arguments,
                )
                for tool_call in (message.tool_calls or [])
            ],
        )
