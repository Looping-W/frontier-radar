import json
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class DefaultProfile:
    id: int


def test_agent_validates_a_fixture_final_json_after_local_tool_calls():
    """Catches an agent that emits unvalidated output before reading local data."""
    from frontier_radar.agents.contracts import ModelReply, ToolCall
    from frontier_radar.agents.curation_agent import CurationAgent
    from frontier_radar.agents.curation_tools import ReadOnlyCurationTools
    from frontier_radar.schemas.curation import (
        CurationArticleContext,
        CurationCandidate,
        CurationSource,
    )

    transcript = json.loads(
        (
            Path(__file__).parent / "fixtures" / "curation_agent_transcript.json"
        ).read_text(encoding="utf-8")
    )

    class TranscriptClient:
        def __init__(self) -> None:
            self.turn = 0
            self.second_turn_messages = None

        def complete(self, messages, tools):
            if self.turn == 1:
                self.second_turn_messages = messages
            reply = transcript[self.turn]
            self.turn += 1
            return ModelReply(
                content=reply.get("content"),
                tool_calls=[ToolCall(**call) for call in reply.get("tool_calls", [])],
            )

    class Profiles:
        def get_default_profile(self):
            return DefaultProfile(id=7)

    class Repository:
        def list_ranked_candidates(self, profile_id, limit):
            return [CurationCandidate(article_id=12, title="Agent tools", score=5)]

        def get_article_context(self, profile_id, article_id):
            return CurationArticleContext(
                article_id=12,
                title="Agent tools",
                score=5,
                sources=[CurationSource(raw_item_id=20, snapshot_id=30, source="hn")],
            )

    client = TranscriptClient()
    draft = CurationAgent(
        client,
        ReadOnlyCurationTools(Profiles(), Repository(), limit=5),
    ).run()

    assert [article.article_id for article in draft.articles] == [12]
    assert client.second_turn_messages is not None
    assert client.second_turn_messages[-2].role == "assistant"
    assert client.second_turn_messages[-2].tool_calls[0].name == "list_ranked_articles"
    assert client.second_turn_messages[-1].role == "tool"
    assert client.second_turn_messages[-1].tool_call_id == "call_1"


def test_agent_rejects_a_final_article_not_listed_by_local_tool():
    """Catches a model response that fabricates an article identity."""
    from frontier_radar.agents.contracts import ModelReply, ToolCall
    from frontier_radar.agents.curation_agent import CurationAgent, CurationAgentError

    class Client:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return ModelReply(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_1",
                            name="list_ranked_articles",
                            arguments_json='{"limit": 5}',
                        )
                    ],
                )
            return ModelReply(
                content=(
                    '{"overview":"A sufficiently long saved update overview.",'
                    '"articles":[{"article_id":999,"summary":"Saved summary.",'
                    '"rationale":"Saved rationale."}]}'
                ),
                tool_calls=[],
            )

    class Tools:
        def definitions(self):
            return []

        def execute(self, name, arguments_json):
            return '[{"article_id":12,"title":"Agent tools","score":5}]'

    with pytest.raises(CurationAgentError, match="not a listed candidate"):
        CurationAgent(Client(), Tools()).run()
