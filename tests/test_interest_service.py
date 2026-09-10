import importlib
from dataclasses import dataclass

import pytest


@dataclass
class DefaultProfile:
    """Minimal persisted-profile shape used by the service boundary test."""

    id: int


def test_service_adds_a_normalized_weighted_topic_to_the_default_profile():
    """Catches ranking terms saved without stable matching keys or profile ownership."""
    try:
        schema_module = importlib.import_module("frontier_radar.schemas.interests")
        service_module = importlib.import_module("frontier_radar.services.interests")
    except ModuleNotFoundError:
        pytest.fail("Phase 3 interest service contracts have not been implemented")
    InterestTerm = schema_module.InterestTerm
    WeightedInterestInput = schema_module.WeightedInterestInput
    InterestService = service_module.InterestService

    class FakeInterestRepository:
        """In-memory persistence boundary that records normalized service inputs."""

        def __init__(self) -> None:
            self.saved_topics: list[tuple[int, str, str, int]] = []

        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

        def upsert_topic(
            self,
            profile_id: int,
            name: str,
            name_key: str,
            weight: int,
        ) -> object:
            self.saved_topics.append((profile_id, name, name_key, weight))
            return InterestTerm(id=3, name=name, weight=weight)

    repository = FakeInterestRepository()
    service = InterestService(repository)

    saved = service.add_topic(WeightedInterestInput(name="  AI-Agent  ", weight=3))

    assert saved == InterestTerm(id=3, name="AI-Agent", weight=3)
    assert repository.saved_topics == [(7, "AI-Agent", "ai agent", 3)]


def test_service_manages_keywords_and_existing_terms_in_the_default_profile():
    """Catches service paths that bypass the default profile or lose normalized lookup.

    The default profile is the only profile currently exposed by the CLI.
    """
    schema_module = importlib.import_module("frontier_radar.schemas.interests")
    service_module = importlib.import_module("frontier_radar.services.interests")
    InterestNameInput = getattr(schema_module, "InterestNameInput", None)
    if InterestNameInput is None:
        pytest.fail("Phase 3 term-name validation has not been implemented")
    InterestTerm = schema_module.InterestTerm
    WeightedInterestInput = schema_module.WeightedInterestInput
    InterestService = service_module.InterestService

    class FakeInterestRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

        def upsert_keyword(
            self,
            profile_id: int,
            name: str,
            name_key: str,
            weight: int,
        ) -> object:
            self.calls.append(("add-keyword", profile_id, name, name_key, weight))
            return InterestTerm(id=4, name=name, weight=weight)

        def list_topics(self, profile_id: int) -> list[object]:
            self.calls.append(("list-topics", profile_id))
            return [InterestTerm(id=1, name="AI Agent", weight=2)]

        def update_topic(
            self,
            profile_id: int,
            name_key: str,
            weight: int,
        ) -> object:
            self.calls.append(("update-topic", profile_id, name_key, weight))
            return InterestTerm(id=1, name="AI Agent", weight=weight)

        def delete_topic(self, profile_id: int, name_key: str) -> object:
            self.calls.append(("delete-topic", profile_id, name_key))
            return InterestTerm(id=1, name="AI Agent", weight=5)

    repository = FakeInterestRepository()
    service = InterestService(repository)

    keyword = service.add_keyword(WeightedInterestInput(name="Tool calling", weight=3))
    topics = service.list_topics()
    updated = service.update_topic(WeightedInterestInput(name="AI-Agent", weight=5))
    deleted = service.remove_topic(InterestNameInput(name=" AI Agent "))

    assert keyword == InterestTerm(id=4, name="Tool calling", weight=3)
    assert topics == [InterestTerm(id=1, name="AI Agent", weight=2)]
    assert updated == InterestTerm(id=1, name="AI Agent", weight=5)
    assert deleted == InterestTerm(id=1, name="AI Agent", weight=5)
    assert repository.calls == [
        ("add-keyword", 7, "Tool calling", "tool calling", 3),
        ("list-topics", 7),
        ("update-topic", 7, "ai agent", 5),
        ("delete-topic", 7, "ai agent"),
    ]


def test_service_lists_updates_and_removes_existing_default_profile_keywords():
    """Catches keyword operations that differ from the established topic behavior."""
    schema_module = importlib.import_module("frontier_radar.schemas.interests")
    service_module = importlib.import_module("frontier_radar.services.interests")
    InterestNameInput = schema_module.InterestNameInput
    InterestTerm = schema_module.InterestTerm
    WeightedInterestInput = schema_module.WeightedInterestInput
    InterestService = service_module.InterestService

    class FakeInterestRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def get_default_profile(self) -> DefaultProfile:
            return DefaultProfile(id=7)

        def list_keywords(self, profile_id: int) -> list[object]:
            self.calls.append(("list-keywords", profile_id))
            return [InterestTerm(id=4, name="Tool calling", weight=3)]

        def update_keyword(
            self,
            profile_id: int,
            name_key: str,
            weight: int,
        ) -> object:
            self.calls.append(("update-keyword", profile_id, name_key, weight))
            return InterestTerm(id=4, name="Tool calling", weight=weight)

        def delete_keyword(self, profile_id: int, name_key: str) -> object:
            self.calls.append(("delete-keyword", profile_id, name_key))
            return InterestTerm(id=4, name="Tool calling", weight=5)

    repository = FakeInterestRepository()
    service = InterestService(repository)

    keywords = service.list_keywords()
    updated = service.update_keyword(
        WeightedInterestInput(name="Tool-Calling", weight=5)
    )
    deleted = service.remove_keyword(InterestNameInput(name=" tool calling "))

    assert keywords == [InterestTerm(id=4, name="Tool calling", weight=3)]
    assert updated == InterestTerm(id=4, name="Tool calling", weight=5)
    assert deleted == InterestTerm(id=4, name="Tool calling", weight=5)
    assert repository.calls == [
        ("list-keywords", 7),
        ("update-keyword", 7, "tool calling", 5),
        ("delete-keyword", 7, "tool calling"),
    ]
