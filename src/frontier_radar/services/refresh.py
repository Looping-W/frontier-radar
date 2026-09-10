from typing import Protocol

from frontier_radar.schemas.collection import CollectionResult
from frontier_radar.schemas.normalization import NormalizationResult
from frontier_radar.schemas.ranking import RankingResult
from frontier_radar.schemas.refresh import RefreshResult


class RefreshCollection(Protocol):
    """Collection boundary used by the fixed refresh workflow."""

    def collect_all(self) -> list[CollectionResult]: ...


class RefreshNormalization(Protocol):
    """Normalization boundary used by the fixed refresh workflow."""

    def normalize(self) -> NormalizationResult: ...


class RefreshRanking(Protocol):
    """Ranking boundary used by the fixed refresh workflow."""

    def rank_default_profile(self) -> RankingResult: ...


class RefreshService:
    """Run the current fixed collection, normalization, and ranking pipeline."""

    def __init__(
        self,
        collection_service: RefreshCollection,
        normalization_service: RefreshNormalization,
        ranking_service: RefreshRanking,
    ) -> None:
        self._collection_service = collection_service
        self._normalization_service = normalization_service
        self._ranking_service = ranking_service

    def refresh(self) -> RefreshResult:
        """Collect default sources, normalize saved snapshots, then rank articles."""
        collection_results = self._collection_service.collect_all()
        normalization = self._normalization_service.normalize()
        ranking = self._ranking_service.rank_default_profile()
        return RefreshResult(
            collection_results=collection_results,
            normalization=normalization,
            ranking=ranking,
        )
