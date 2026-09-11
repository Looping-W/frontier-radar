from dataclasses import dataclass
from datetime import date

import pytest

from frontier_radar.schemas.curation import (
    CurationArticleContext,
    CurationDraft,
    CurationSelection,
    CurationSource,
)
from frontier_radar.schemas.llm import LLMConfiguration


@dataclass
class DefaultProfile:
    id: int


def test_service_renders_local_traceability_not_model_supplied_links():
    """Catches Markdown that permits a model to invent article URLs or scores."""
    from frontier_radar.services.curation import CurationService

    class Configurations:
        def show(self):
            return LLMConfiguration(
                id=1,
                provider_id="custom",
                provider_label="Test",
                api_protocol="openai_compatible",
                base_url="https://models.example.test/v1",
                model_name="test-model",
            )

    class Profiles:
        def get_default_profile(self):
            return DefaultProfile(id=7)

    class Repository:
        def get_article_context(self, profile_id, article_id):
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

    class Agent:
        def run(self):
            return CurationDraft(
                overview="Saved local updates emphasize practical agent tools.",
                articles=[
                    CurationSelection(
                        article_id=12,
                        summary="A saved summary.",
                        rationale="A saved rationale.",
                    )
                ],
            )

    result = CurationService(
        Configurations(), Profiles(), Repository(), "test-key", lambda *_: Agent()
    ).create_digest(limit=5, today=date(2026, 9, 11))

    assert "# Frontier Radar Daily Brief — 2026-09-11" in result.markdown
    assert "[Agent tools](https://example.test/agent-tools)" in result.markdown
    assert "Relevance score: 5" in result.markdown
    assert "raw item 20; snapshot 30" in result.markdown


def test_service_rejects_missing_configuration_before_model_creation():
    """Catches a digest that sends a request without a saved model configuration."""
    from frontier_radar.services.curation import CurationError, CurationService

    class Configurations:
        def show(self):
            return None

    with pytest.raises(CurationError, match="LLM configuration not found"):
        CurationService(
            Configurations(),
            object(),
            object(),
            "test-key",
            object(),
        ).create_digest(
            limit=5,
            today=date(2026, 9, 11),
        )


def test_service_rejects_a_missing_key_before_model_creation():
    """Catches an accidental provider call when the required runtime key is absent."""
    from frontier_radar.services.curation import CurationError, CurationService

    class Configurations:
        def show(self):
            return LLMConfiguration(
                id=1,
                provider_id="custom",
                provider_label="Test",
                api_protocol="openai_compatible",
                base_url="https://models.example.test/v1",
                model_name="test-model",
            )

    with pytest.raises(CurationError, match="LLM_API_KEY is not configured"):
        CurationService(
            Configurations(),
            object(),
            object(),
            None,
            object(),
        ).create_digest(limit=5, today=date(2026, 9, 11))
