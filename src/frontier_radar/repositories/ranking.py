from collections import defaultdict
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from frontier_radar.models.collection import (
    ArticleRankingRecord,
    ArticleRecord,
    InterestKeywordRecord,
    InterestTopicRecord,
    RawItemRecord,
)
from frontier_radar.schemas.ranking import (
    RankableArticle,
    RankedArticle,
    RankingRule,
)


class RankingRepository:
    """Read ranking inputs and persist deterministic per-profile article scores."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def list_rules(self, profile_id: int) -> list[RankingRule]:
        """Return all weighted topics and keywords in one stable order."""
        with self._session_factory() as session:
            topics = session.scalars(
                select(InterestTopicRecord)
                .where(InterestTopicRecord.profile_id == profile_id)
                .order_by(InterestTopicRecord.name_key, InterestTopicRecord.id)
            ).all()
            keywords = session.scalars(
                select(InterestKeywordRecord)
                .where(InterestKeywordRecord.profile_id == profile_id)
                .order_by(InterestKeywordRecord.name_key, InterestKeywordRecord.id)
            ).all()
            records = [*topics, *keywords]
            return [
                RankingRule(
                    name=record.name,
                    name_key=record.name_key,
                    weight=record.weight,
                )
                for record in records
            ]

    def list_articles(self) -> list[RankableArticle]:
        """Read canonical titles and raw-item titles without altering their lineage."""
        with self._session_factory() as session:
            articles = session.scalars(
                select(ArticleRecord).order_by(ArticleRecord.id)
            ).all()
            raw_titles_by_article: defaultdict[int, list[str]] = defaultdict(list)
            raw_titles = session.execute(
                select(RawItemRecord.article_id, RawItemRecord.title).order_by(
                    RawItemRecord.article_id,
                    RawItemRecord.id,
                )
            )
            for article_id, title in raw_titles:
                raw_titles_by_article[article_id].append(title)
            return [
                RankableArticle(
                    article_id=article.id,
                    title=article.title,
                    source_titles=raw_titles_by_article[article.id],
                )
                for article in articles
            ]

    def replace_rankings(
        self,
        profile_id: int,
        rankings: list[RankedArticle],
    ) -> None:
        """Upsert one current relevance score for every ranked profile/article pair."""
        with self._session_factory() as session:
            existing = {
                ranking.article_id: ranking
                for ranking in session.scalars(
                    select(ArticleRankingRecord).where(
                        ArticleRankingRecord.profile_id == profile_id
                    )
                )
            }
            for ranking in rankings:
                stored = existing.get(ranking.article_id)
                if stored is None:
                    session.add(
                        ArticleRankingRecord(
                            profile_id=profile_id,
                            article_id=ranking.article_id,
                            score=ranking.score,
                        )
                    )
                else:
                    stored.score = ranking.score
            session.commit()
