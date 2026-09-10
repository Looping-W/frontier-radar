import importlib

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, UniqueConstraint

from frontier_radar.schemas.interests import WeightedInterestInput


def load_models() -> tuple[type, type, type, type]:
    """Return Phase 3 models or clearly report the missing contracts."""
    module = importlib.import_module("frontier_radar.models.collection")
    names = (
        "InterestProfileRecord",
        "InterestTopicRecord",
        "InterestKeywordRecord",
        "ArticleRankingRecord",
    )
    models = tuple(getattr(module, name, None) for name in names)
    if any(model is None for model in models):
        pytest.fail("Phase 3 interest and ranking models have not been implemented")
    return models  # type: ignore[return-value]


def unique_column_sets(record: type) -> set[tuple[str, ...]]:
    """Return each table-level uniqueness contract by column name."""
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in record.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_interest_records_belong_to_a_profile_with_normalized_name_uniqueness():
    """Catches terms that could collide or exist without an owning profile."""
    profile, topic, keyword, _ = load_models()

    assert profile.__table__.c.slug.unique is True
    for record in (topic, keyword):
        foreign_keys = record.__table__.c.profile_id.foreign_keys
        assert {key.target_fullname for key in foreign_keys} == {"interest_profiles.id"}
        assert ("profile_id", "name_key") in unique_column_sets(record)
        assert {"name", "name_key", "weight"} <= set(record.__table__.c.keys())


def test_article_rankings_link_one_profile_to_each_canonical_article():
    """Catches ranking rows that lose profile isolation or article lineage."""
    _, _, _, ranking = load_models()

    profile_keys = ranking.__table__.c.profile_id.foreign_keys
    article_keys = ranking.__table__.c.article_id.foreign_keys

    assert {key.target_fullname for key in profile_keys} == {"interest_profiles.id"}
    assert {key.target_fullname for key in article_keys} == {"articles.id"}
    assert ("profile_id", "article_id") in unique_column_sets(ranking)
    assert "score" in ranking.__table__.c


def test_weighted_interest_input_accepts_only_the_one_to_five_scale():
    """Catches CLI/service validation that permits an unintelligible priority scale."""
    assert WeightedInterestInput(name="AI Agent", weight=1).weight == 1
    assert WeightedInterestInput(name="AI Agent", weight=5).weight == 5

    with pytest.raises(ValidationError, match="less than or equal to 5"):
        WeightedInterestInput(name="AI Agent", weight=6)


def test_interest_weight_columns_enforce_the_one_to_five_scale_in_the_database():
    """Catches direct database writes that bypass the Pydantic command boundary."""
    _, topic, keyword, _ = load_models()

    for record in (topic, keyword):
        constraints = {
            str(constraint.sqltext)
            for constraint in record.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        assert "weight >= 1 AND weight <= 5" in constraints
