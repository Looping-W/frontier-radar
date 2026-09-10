from typing import Protocol

from frontier_radar.schemas.interests import (
    InterestNameInput,
    InterestTerm,
    WeightedInterestInput,
)
from frontier_radar.services.normalization import normalize_title


class StoredProfile(Protocol):
    """The profile identity required by the interest-management service."""

    id: int


class InterestPersistence(Protocol):
    """Database boundary used by the default-profile interest service."""

    def get_default_profile(self) -> StoredProfile: ...

    def upsert_topic(
        self,
        profile_id: int,
        name: str,
        name_key: str,
        weight: int,
    ) -> InterestTerm: ...

    def upsert_keyword(
        self,
        profile_id: int,
        name: str,
        name_key: str,
        weight: int,
    ) -> InterestTerm: ...

    def list_topics(self, profile_id: int) -> list[InterestTerm]: ...

    def update_topic(
        self,
        profile_id: int,
        name_key: str,
        weight: int,
    ) -> InterestTerm | None: ...

    def delete_topic(
        self,
        profile_id: int,
        name_key: str,
    ) -> InterestTerm | None: ...

    def list_keywords(self, profile_id: int) -> list[InterestTerm]: ...

    def update_keyword(
        self,
        profile_id: int,
        name_key: str,
        weight: int,
    ) -> InterestTerm | None: ...

    def delete_keyword(
        self,
        profile_id: int,
        name_key: str,
    ) -> InterestTerm | None: ...


class InterestService:
    """Manage weighted terms for the single current local profile."""

    def __init__(self, repository: InterestPersistence) -> None:
        self._repository = repository

    def add_topic(self, interest: WeightedInterestInput) -> InterestTerm:
        """Save one normalized topic under the current default profile."""
        name_key = self._name_key(interest.name)
        profile = self._repository.get_default_profile()
        return self._repository.upsert_topic(
            profile.id,
            interest.name,
            name_key,
            interest.weight,
        )

    def add_keyword(self, interest: WeightedInterestInput) -> InterestTerm:
        """Save one normalized keyword under the current default profile."""
        name_key = self._name_key(interest.name)
        profile = self._repository.get_default_profile()
        return self._repository.upsert_keyword(
            profile.id,
            interest.name,
            name_key,
            interest.weight,
        )

    def list_topics(self) -> list[InterestTerm]:
        """List the default profile's topics in repository-defined stable order."""
        profile = self._repository.get_default_profile()
        return self._repository.list_topics(profile.id)

    def update_topic(self, interest: WeightedInterestInput) -> InterestTerm:
        """Change one existing default-profile topic's positive weight."""
        profile = self._repository.get_default_profile()
        topic = self._repository.update_topic(
            profile.id,
            self._name_key(interest.name),
            interest.weight,
        )
        if topic is None:
            raise ValueError(f"Topic not found: {interest.name}")
        return topic

    def remove_topic(self, interest: InterestNameInput) -> InterestTerm:
        """Remove one existing default-profile topic."""
        profile = self._repository.get_default_profile()
        topic = self._repository.delete_topic(
            profile.id,
            self._name_key(interest.name),
        )
        if topic is None:
            raise ValueError(f"Topic not found: {interest.name}")
        return topic

    def list_keywords(self) -> list[InterestTerm]:
        """List the default profile's keywords in repository-defined stable order."""
        profile = self._repository.get_default_profile()
        return self._repository.list_keywords(profile.id)

    def update_keyword(self, interest: WeightedInterestInput) -> InterestTerm:
        """Change one existing default-profile keyword's positive weight."""
        profile = self._repository.get_default_profile()
        keyword = self._repository.update_keyword(
            profile.id,
            self._name_key(interest.name),
            interest.weight,
        )
        if keyword is None:
            raise ValueError(f"Keyword not found: {interest.name}")
        return keyword

    def remove_keyword(self, interest: InterestNameInput) -> InterestTerm:
        """Remove one existing default-profile keyword."""
        profile = self._repository.get_default_profile()
        keyword = self._repository.delete_keyword(
            profile.id,
            self._name_key(interest.name),
        )
        if keyword is None:
            raise ValueError(f"Keyword not found: {interest.name}")
        return keyword

    @staticmethod
    def _name_key(name: str) -> str:
        name_key = normalize_title(name)
        if not name_key:
            raise ValueError("Interest name must contain at least one letter or number")
        return name_key
