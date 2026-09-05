import importlib

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex


def load_models() -> tuple[type, type]:
    """Return Phase 2 persistence models or fail with the missing contract."""
    module = importlib.import_module("frontier_radar.models.collection")
    raw_item = getattr(module, "RawItemRecord", None)
    article = getattr(module, "ArticleRecord", None)
    if raw_item is None or article is None:
        pytest.fail("Phase 2 raw item and article models have not been implemented")
    return raw_item, article


def test_raw_item_records_retain_snapshot_and_canonical_article_traceability():
    """Catches parsed rows that cannot be traced back to a snapshot or article."""
    raw_item, _ = load_models()

    snapshot_foreign_keys = raw_item.__table__.c.snapshot_id.foreign_keys
    article_foreign_keys = raw_item.__table__.c.article_id.foreign_keys

    assert {foreign_key.target_fullname for foreign_key in snapshot_foreign_keys} == {
        "collection_snapshots.id"
    }
    assert {foreign_key.target_fullname for foreign_key in article_foreign_keys} == {
        "articles.id"
    }


def test_raw_item_records_are_idempotent_per_snapshot_and_source_item():
    """Catches a repeat normalization run that would duplicate one parsed item."""
    raw_item, _ = load_models()

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in raw_item.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("snapshot_id", "source_item_id") in unique_columns


def test_article_records_expose_normalized_fields_needed_for_deduplication():
    """Catches canonical articles that cannot be compared by URL or title key."""
    _, article = load_models()

    assert {"title", "title_key", "normalized_url"} <= set(article.__table__.c.keys())


def test_article_records_index_normalized_urls_for_deduplication_lookup():
    """Catches URL deduplication that would scan every canonical article."""
    _, article = load_models()

    indexed_columns = {
        tuple(column.name for column in index.columns)
        for index in article.__table__.indexes
    }

    assert ("normalized_url",) in indexed_columns


def test_normalized_url_indexes_fit_mysql_utf8mb4_key_length_limit():
    """Catches full URL indexes that exceed MySQL's InnoDB key-size limit."""
    raw_item, article = load_models()

    for record in (article, raw_item):
        normalized_url_index = next(
            index
            for index in record.__table__.indexes
            if tuple(column.name for column in index.columns) == ("normalized_url",)
        )
        statement = str(
            CreateIndex(normalized_url_index).compile(dialect=mysql.dialect())
        )

        assert "normalized_url(768)" in statement
