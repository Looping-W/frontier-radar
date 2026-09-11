from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelMessage:
    """One provider-neutral chat message passed to a model client."""

    role: str
    content: str | None
    tool_call_id: str | None = None
    tool_calls: list["ToolCall"] | None = None

    def as_openai_payload(self) -> dict[str, object]:
        """Return the subset of message fields used by the compatible adapter."""
        payload = {"role": self.role, "content": self.content}
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            payload["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.arguments_json,
                    },
                }
                for tool_call in self.tool_calls
            ]
        return payload


@dataclass(frozen=True)
class ToolDefinition:
    """One local function exposed to the compatible model protocol."""

    name: str
    description: str
    parameters: dict[str, object]

    def as_openai_payload(self) -> dict[str, object]:
        """Wrap a local function schema in the compatible tools format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(frozen=True)
class ToolCall:
    """One model request to invoke an allowlisted local function."""

    id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ModelReply:
    """Normalized final text and/or local tool calls from one model turn."""

    content: str | None
    tool_calls: list[ToolCall]


class CurationModelClient(Protocol):
    """Provider-independent model transport used by the curation agent."""

    def complete(
        self,
        messages: list[ModelMessage],
        tools: list[ToolDefinition],
    ) -> ModelReply: ...
