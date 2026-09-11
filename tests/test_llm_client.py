from types import SimpleNamespace

from frontier_radar.schemas.llm import LLMConfiguration


def test_openai_compatible_client_maps_a_tool_call_from_configured_model():
    """Catches an adapter that ignores the saved endpoint/model or loses tool calls."""
    from frontier_radar.agents.contracts import ModelMessage, ToolDefinition
    from frontier_radar.agents.openai_compatible import (
        OpenAICompatibleCurationModelClient,
    )

    class FakeCompletions:
        def __init__(self) -> None:
            self.request: dict[str, object] | None = None

        def create(self, **kwargs: object) -> object:
            self.request = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=None,
                            tool_calls=[
                                SimpleNamespace(
                                    id="call_1",
                                    function=SimpleNamespace(
                                        name="list_ranked_articles",
                                        arguments='{"limit": 5}',
                                    ),
                                )
                            ],
                        )
                    )
                ]
            )

    completions = FakeCompletions()
    client = OpenAICompatibleCurationModelClient(
        configuration=LLMConfiguration(
            id=1,
            provider_id="custom",
            provider_label="Internal compatible service",
            api_protocol="openai_compatible",
            base_url="https://models.example.test/v1",
            model_name="team-curator-1",
        ),
        api_key="test-key",
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )

    reply = client.complete(
        [ModelMessage(role="user", content="Create a brief.")],
        [
            ToolDefinition(
                name="list_ranked_articles",
                description="List local candidates.",
                parameters={"type": "object", "properties": {}},
            )
        ],
    )

    assert reply.content is None
    assert [(call.name, call.arguments_json) for call in reply.tool_calls] == [
        ("list_ranked_articles", '{"limit": 5}')
    ]
    assert completions.request is not None
    assert completions.request["model"] == "team-curator-1"
