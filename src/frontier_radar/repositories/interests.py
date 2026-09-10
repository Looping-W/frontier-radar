from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from frontier_radar.models.collection import (
    InterestKeywordRecord,
    InterestProfileRecord,
    InterestTopicRecord,
)
from frontier_radar.schemas.interests import InterestTerm

DEFAULT_PROFILE_NAME = "Default"
DEFAULT_PROFILE_SLUG = "default"


class InterestRepository:
    """Persist and retrieve local interest-profile records."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def get_default_profile(self) -> InterestProfileRecord:
        """Return the stable default profile, creating it on first use."""
        with self._session_factory() as session:
            profile = session.scalar(
                select(InterestProfileRecord).where(
                    InterestProfileRecord.slug == DEFAULT_PROFILE_SLUG
                )
            )
            if profile is None:
                profile = InterestProfileRecord(
                    name=DEFAULT_PROFILE_NAME,
                    slug=DEFAULT_PROFILE_SLUG,
                )
                session.add(profile)
                session.commit()
                session.refresh(profile)
            session.expunge(profile)
            return profile

    def upsert_topic(
        self,
        profile_id: int,
        name: str,
        name_key: str,
        weight: int,
    ) -> InterestTerm:
        """Create or update one topic identified by its profile-scoped key."""
        with self._session_factory() as session:
            topic = session.scalar(
                select(InterestTopicRecord).where(
                    InterestTopicRecord.profile_id == profile_id,
                    InterestTopicRecord.name_key == name_key,
                )
            )
            if topic is None:
                topic = InterestTopicRecord(
                    profile_id=profile_id,
                    name=name,
                    name_key=name_key,
                    weight=weight,
                )
                session.add(topic)
            else:
                topic.name = name
                topic.weight = weight
            session.commit()
            session.refresh(topic)
            return InterestTerm(id=topic.id, name=topic.name, weight=topic.weight)

    def list_topics(self, profile_id: int) -> list[InterestTerm]:
        """List profile topics by their stable normalized names."""
        with self._session_factory() as session:
            topics = session.scalars(
                select(InterestTopicRecord)
                .where(InterestTopicRecord.profile_id == profile_id)
                .order_by(InterestTopicRecord.name_key, InterestTopicRecord.id)
            )
            return [
                InterestTerm(id=topic.id, name=topic.name, weight=topic.weight)
                for topic in topics
            ]

    def update_topic(
        self,
        profile_id: int,
        name_key: str,
        weight: int,
    ) -> InterestTerm | None:
        """Change an existing topic's weight without creating a new term."""
        with self._session_factory() as session:
            topic = session.scalar(
                select(InterestTopicRecord).where(
                    InterestTopicRecord.profile_id == profile_id,
                    InterestTopicRecord.name_key == name_key,
                )
            )
            if topic is None:
                return None
            topic.weight = weight
            session.commit()
            session.refresh(topic)
            return InterestTerm(id=topic.id, name=topic.name, weight=topic.weight)

    def delete_topic(
        self,
        profile_id: int,
        name_key: str,
    ) -> InterestTerm | None:
        """Delete one existing topic identified by its normalized name."""
        with self._session_factory() as session:
            topic = session.scalar(
                select(InterestTopicRecord).where(
                    InterestTopicRecord.profile_id == profile_id,
                    InterestTopicRecord.name_key == name_key,
                )
            )
            if topic is None:
                return None
            result = InterestTerm(id=topic.id, name=topic.name, weight=topic.weight)
            session.delete(topic)
            session.commit()
            return result

    def upsert_keyword(
        self,
        profile_id: int,
        name: str,
        name_key: str,
        weight: int,
    ) -> InterestTerm:
        """Create or update one keyword identified by its profile-scoped key."""
        with self._session_factory() as session:
            keyword = session.scalar(
                select(InterestKeywordRecord).where(
                    InterestKeywordRecord.profile_id == profile_id,
                    InterestKeywordRecord.name_key == name_key,
                )
            )
            if keyword is None:
                keyword = InterestKeywordRecord(
                    profile_id=profile_id,
                    name=name,
                    name_key=name_key,
                    weight=weight,
                )
                session.add(keyword)
            else:
                keyword.name = name
                keyword.weight = weight
            session.commit()
            session.refresh(keyword)
            return InterestTerm(
                id=keyword.id,
                name=keyword.name,
                weight=keyword.weight,
            )

    def list_keywords(self, profile_id: int) -> list[InterestTerm]:
        """List profile keywords by their stable normalized names."""
        with self._session_factory() as session:
            keywords = session.scalars(
                select(InterestKeywordRecord)
                .where(InterestKeywordRecord.profile_id == profile_id)
                .order_by(InterestKeywordRecord.name_key, InterestKeywordRecord.id)
            )
            return [
                InterestTerm(id=keyword.id, name=keyword.name, weight=keyword.weight)
                for keyword in keywords
            ]

    def update_keyword(
        self,
        profile_id: int,
        name_key: str,
        weight: int,
    ) -> InterestTerm | None:
        """Change an existing keyword's weight without creating a new term."""
        with self._session_factory() as session:
            keyword = session.scalar(
                select(InterestKeywordRecord).where(
                    InterestKeywordRecord.profile_id == profile_id,
                    InterestKeywordRecord.name_key == name_key,
                )
            )
            if keyword is None:
                return None
            keyword.weight = weight
            session.commit()
            session.refresh(keyword)
            return InterestTerm(
                id=keyword.id,
                name=keyword.name,
                weight=keyword.weight,
            )

    def delete_keyword(
        self,
        profile_id: int,
        name_key: str,
    ) -> InterestTerm | None:
        """Delete one existing keyword identified by its normalized name."""
        with self._session_factory() as session:
            keyword = session.scalar(
                select(InterestKeywordRecord).where(
                    InterestKeywordRecord.profile_id == profile_id,
                    InterestKeywordRecord.name_key == name_key,
                )
            )
            if keyword is None:
                return None
            result = InterestTerm(
                id=keyword.id,
                name=keyword.name,
                weight=keyword.weight,
            )
            session.delete(keyword)
            session.commit()
            return result
