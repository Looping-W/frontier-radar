from pydantic import BaseModel

from frontier_radar.schemas.collection import CollectionResult
from frontier_radar.schemas.normalization import NormalizationResult
from frontier_radar.schemas.ranking import RankingResult


class RefreshResult(BaseModel):
    """Combined result from one fixed collect-normalize-rank refresh run."""

    collection_results: list[CollectionResult]
    normalization: NormalizationResult
    ranking: RankingResult
