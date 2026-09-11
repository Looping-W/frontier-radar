from collections.abc import Callable

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from frontier_radar.models.collection import (
    ArticleFeedbackRecord,
    ArticleRankingRecord,
    ArticleRecord,
    CollectionSnapshotRecord,
    RawItemRecord,
)
from frontier_radar.schemas.curation import (
    CurationArticleContext,
    CurationCandidate,
    CurationSource,
)


class CurationRepository:
    """Read saved rankings and source lineage without changing any record."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def list_ranked_candidates(
        self,
        profile_id: int,
        limit: int,
    ) -> list[CurationCandidate]:
        """Return stable, positively ranked canonical articles for one profile."""
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    ArticleRecord.id,
                    ArticleRecord.title,
                    ArticleRankingRecord.score,
                )
                .join(
                    ArticleRankingRecord,
                    ArticleRankingRecord.article_id == ArticleRecord.id,
                )
                .where(
                    ArticleRankingRecord.profile_id == profile_id,
                    ArticleRankingRecord.score > 0,
                    ~exists().where(
                        ArticleFeedbackRecord.profile_id == profile_id,
                        ArticleFeedbackRecord.article_id == ArticleRecord.id,
                    ),
                )
                .order_by(ArticleRankingRecord.score.desc(), ArticleRecord.id.asc())
                .limit(limit)
            )
            return [
                CurationCandidate(article_id=article_id, title=title, score=score)
                for article_id, title, score in rows
            ]

    def get_article_context(
        self,
        profile_id: int,
        article_id: int,
    ) -> CurationArticleContext | None:
        """Return local source lineage only when the profile ranks this article."""
        with self._session_factory() as session:
            candidate = session.execute(
                select(
                    ArticleRecord.id,
                    ArticleRecord.title,
                    ArticleRankingRecord.score,
                )
                .join(
                    ArticleRankingRecord,
                    ArticleRankingRecord.article_id == ArticleRecord.id,
                )
                .where(
                    ArticleRankingRecord.profile_id == profile_id,
                    ArticleRankingRecord.article_id == article_id,
                    ArticleRankingRecord.score > 0,
                    ~exists().where(
                        ArticleFeedbackRecord.profile_id == profile_id,
                        ArticleFeedbackRecord.article_id == ArticleRecord.id,
                    ),
                )
            ).one_or_none()
            if candidate is None:
                return None
            sources = session.execute(
                select(
                    RawItemRecord.id,
                    CollectionSnapshotRecord.id,
                    RawItemRecord.source,
                    RawItemRecord.url,
                    RawItemRecord.published_at,
                )
                .join(
                    CollectionSnapshotRecord,
                    CollectionSnapshotRecord.id == RawItemRecord.snapshot_id,
                )
                .where(RawItemRecord.article_id == article_id)
                .order_by(RawItemRecord.id.asc())
            )
            return CurationArticleContext(
                article_id=candidate.id,
                title=candidate.title,
                score=candidate.score,
                sources=[
                    CurationSource(
                        raw_item_id=raw_item_id,
                        snapshot_id=snapshot_id,
                        source=source,
                        url=url,
                        published_at=published_at,
                    )
                    for raw_item_id, snapshot_id, source, url, published_at in sources
                ],
            )
