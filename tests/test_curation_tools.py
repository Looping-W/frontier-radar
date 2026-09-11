import json
from dataclasses import dataclass

import pytest

from frontier_radar.schemas.curation import (
    CurationArticleContext,
    CurationCandidate,
    CurationSource,
)


@dataclass
class DefaultProfile:
    """Minimal profile identity returned by the established profile boundary."""

    id: int


def test_tools_allow_only_local_list_then_listed_article_context():
    """Catches tools that can query arbitrary database records or skip ranking."""
    from frontier_radar.agents.curation_tools import ReadOnlyCurationTools

    class FakeProfiles:
        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

    class FakeRepository:
        def list_ranked_candidates(
            self, profile_id: int, limit: int
        ) -> list[CurationCandidate]:
            assert (profile_id, limit) == (7, 5)
            return [CurationCandidate(article_id=12, title="Agent tools", score=5)]

        def get_article_context(
            self, profile_id: int, article_id: int
        ) -> CurationArticleContext:
            assert (profile_id, article_id) == (7, 12)
            return CurationArticleContext(
                article_id=12,
                title="Agent tools",
                score=5,
                sources=[
                    CurationSource(
                        raw_item_id=20,
                        snapshot_id=30,
                        source="hacker_news",
                        url="https://example.test/agent-tools",
                    )
                ],
            )

    tools = ReadOnlyCurationTools(FakeProfiles(), FakeRepository(), limit=5)

    candidates = json.loads(tools.execute("list_ranked_articles", '{"limit": 20}'))
    context = json.loads(tools.execute("get_article_context", '{"article_id": 12}'))

    assert candidates == [{"article_id": 12, "title": "Agent tools", "score": 5}]
    assert context["sources"][0]["snapshot_id"] == 30


def test_tools_reject_unknown_and_out_of_scope_requests():
    """Catches an Agent tool executor that permits collection or arbitrary reads."""
    from frontier_radar.agents.curation_tools import (
        CurationToolError,
        ReadOnlyCurationTools,
    )

    tools = ReadOnlyCurationTools(object(), object(), limit=5)

    with pytest.raises(CurationToolError, match="Unsupported curation tool"):
        tools.execute("collect_articles", "{}")
    with pytest.raises(CurationToolError, match="List ranked articles first"):
        tools.execute("get_article_context", '{"article_id": 12}')
