from typing import Protocol

from frontier_radar.schemas.ranking import (
    FeedbackAdjustment,
    FeedbackRankableArticle,
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

    def list_feedback_articles(
        self, profile_id: int
    ) -> list[FeedbackRankableArticle]: ...

    def replace_feedback_adjustments(
        self,
        profile_id: int,
        adjustments: list[FeedbackAdjustment],
    ) -> None: ...

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
        feedback_articles = self._ranking_repository.list_feedback_articles(profile.id)
        adjustments = self._derive_adjustments(rules, feedback_articles)
        self._ranking_repository.replace_feedback_adjustments(profile.id, adjustments)
        adjustment_by_rule = {
            (adjustment.kind, adjustment.rule_id): adjustment.adjustment
            for adjustment in adjustments
        }
        effective_rules = [
            rule.model_copy(
                update={
                    "feedback_adjustment": adjustment_by_rule.get(
                        (rule.kind, rule.rule_id),
                        0,
                    )
                }
            )
            for rule in rules
        ]
        articles = self._ranking_repository.list_articles()
        rankings = sorted(
            [
                RankedArticle(
                    article_id=article.article_id,
                    title=article.title,
                    score=self._score_article(article, effective_rules),
                )
                for article in articles
            ],
            key=lambda ranking: (-ranking.score, ranking.article_id),
        )
        self._ranking_repository.replace_rankings(profile.id, rankings)
        seen_article_ids = {
            feedback.article_id for feedback in feedback_articles
        }
        return RankingResult(
            articles_scored=len(articles),
            rankings=[
                ranking
                for ranking in rankings
                if ranking.score > 0 and ranking.article_id not in seen_article_ids
            ],
        )

    @staticmethod
    def _derive_adjustments(
        rules: list[RankingRule],
        feedback_articles: list[FeedbackRankableArticle],
    ) -> list[FeedbackAdjustment]:
        """Aggregate each current feedback decision against the current rule set."""
        totals = {(rule.kind, rule.rule_id): 0 for rule in rules if rule.rule_id > 0}
        for article in feedback_articles:
            signal = 1 if article.decision == "like" else -1
            texts = (article.title, *article.source_titles)
            for rule in rules:
                key = (rule.kind, rule.rule_id)
                if key in totals and any(
                    RankingService._matches(text, rule.name_key) for text in texts
                ):
                    totals[key] += signal
        return [
            FeedbackAdjustment(
                rule_id=rule.rule_id,
                kind=rule.kind,
                adjustment=max(-2, min(2, totals[(rule.kind, rule.rule_id)])),
            )
            for rule in rules
            if rule.rule_id > 0
        ]

    @staticmethod
    def _score_article(article: RankableArticle, rules: list[RankingRule]) -> int:
        texts = (article.title, *article.source_titles)
        return sum(
            rule.effective_weight
            for rule in rules
            if any(RankingService._matches(text, rule.name_key) for text in texts)
        )

    @staticmethod
    def _matches(text: str, name_key: str) -> bool:
        return f" {name_key} " in f" {normalize_title(text)} "
