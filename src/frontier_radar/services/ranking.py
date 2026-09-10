from typing import Protocol

from frontier_radar.schemas.ranking import (
    RankableArticle,
    RankedArticle,
    RankingResult,
    RankingRule,
)
from frontier_radar.services.normalization import normalize_title


class StoredProfile(Protocol):
    """The default-profile identity needed for a ranking run."""

    id: int


class DefaultProfilePersistence(Protocol):
    """Profile boundary retained separately for future multi-profile selection."""

    def get_default_profile(self) -> StoredProfile: ...


class RankingPersistence(Protocol):
    """Database boundary used by deterministic ranking orchestration."""

    def list_rules(self, profile_id: int) -> list[RankingRule]: ...

    def list_articles(self) -> list[RankableArticle]: ...

    def replace_rankings(
        self,
        profile_id: int,
        rankings: list[RankedArticle],
    ) -> None: ...


class RankingService:
    """Calculate and persist default-profile relevance without external calls."""

    def __init__(
        self,
        profile_repository: DefaultProfilePersistence,
        ranking_repository: RankingPersistence,
    ) -> None:
        self._profile_repository = profile_repository
        self._ranking_repository = ranking_repository

    def rank_default_profile(self) -> RankingResult:
        """Score all articles, persist all scores, and return relevant entries only."""
        profile = self._profile_repository.get_default_profile()
        rules = self._ranking_repository.list_rules(profile.id)
        articles = self._ranking_repository.list_articles()
        rankings = sorted(
            [
                RankedArticle(
                    article_id=article.article_id,
                    title=article.title,
                    score=self._score_article(article, rules),
                )
                for article in articles
            ],
            key=lambda ranking: (-ranking.score, ranking.article_id),
        )
        self._ranking_repository.replace_rankings(profile.id, rankings)
        return RankingResult(
            articles_scored=len(articles),
            rankings=[ranking for ranking in rankings if ranking.score > 0],
        )

    @staticmethod
    def _score_article(article: RankableArticle, rules: list[RankingRule]) -> int:
        texts = (article.title, *article.source_titles)
        return sum(
            rule.weight
            for rule in rules
            if any(RankingService._matches(text, rule.name_key) for text in texts)
        )

    @staticmethod
    def _matches(text: str, name_key: str) -> bool:
        return f" {name_key} " in f" {normalize_title(text)} "
