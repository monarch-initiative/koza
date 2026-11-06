"""Tests for edge examples: N full-width sample rows per edge type."""

from __future__ import annotations

import duckdb
import pytest

from koza.graph_operations.report import generate_edge_examples
from koza.model.graph_operations import EdgeExamplesConfig, TabularReportFormat


def _make_kg(path, with_id=True, duplicate_edges=False):
    conn = duckdb.connect(str(path))
    id_col = "'e' || i::VARCHAR AS id," if with_id else ""
    conn.execute(
        f"""
        CREATE TABLE nodes AS
        SELECT 'GENE:' || i::VARCHAR AS id, 'biolink:Gene' AS category FROM range(10) t(i)
        UNION ALL
        SELECT 'MONDO:' || i::VARCHAR, 'biolink:Disease' FROM range(10) t(i);

        CREATE TABLE edges AS
        SELECT
            {id_col}
            'GENE:' || (i % 10)::VARCHAR AS subject,
            ['biolink:causes', 'biolink:contributes_to'][(i % 2) + 1] AS predicate,
            'MONDO:' || ((i // 10) % 10)::VARCHAR AS object,
            'infores:test' AS primary_knowledge_source,
            ['PMID:' || i::VARCHAR] AS publications
        FROM range(100) t(i);
        """
    )
    if duplicate_edges:
        # Every edge repeated: identical keys must not inflate the per-type sample.
        conn.execute("INSERT INTO edges SELECT * FROM edges")
    conn.close()
    return path


def _run(db, tmp_path, sample_size=3):
    out = tmp_path / "examples.parquet"
    result = generate_edge_examples(
        EdgeExamplesConfig(
            database_path=db,
            output_file=out,
            output_format=TabularReportFormat.PARQUET,
            sample_size=sample_size,
            quiet=True,
        )
    )
    return result, duckdb.sql(f"SELECT * FROM '{out}'").df()


@pytest.mark.parametrize("with_id", [True, False])
def test_samples_capped_per_type_with_full_rows(tmp_path, with_id):
    db = _make_kg(tmp_path / "kg.duckdb", with_id=with_id)
    result, df = _run(db, tmp_path)

    assert result.types_sampled == 2
    assert result.total_examples == 6
    assert len(df) == 6
    assert df.groupby("predicate").size().to_dict() == {"biolink:causes": 3, "biolink:contributes_to": 3}
    # Full edge width plus the denormalized category columns, not just the keys.
    assert {"primary_knowledge_source", "publications", "subject_category", "object_category"} <= set(df.columns)
    assert (df["subject_category"] == "biolink:Gene").all()


def test_samples_are_first_by_subject_object(tmp_path):
    db = _make_kg(tmp_path / "kg.duckdb")
    _, df = _run(db, tmp_path)
    causes = df[df["predicate"] == "biolink:causes"]
    assert list(zip(causes["subject"], causes["object"], strict=True)) == [
        ("GENE:0", "MONDO:0"),
        ("GENE:0", "MONDO:1"),
        ("GENE:0", "MONDO:2"),
    ]


def test_duplicate_edges_without_id_stay_capped(tmp_path):
    db = _make_kg(tmp_path / "kg.duckdb", with_id=False, duplicate_edges=True)
    result, df = _run(db, tmp_path)
    assert result.total_examples == 6
    assert df.groupby("predicate").size().max() == 3


def test_count_without_output_file(tmp_path):
    db = _make_kg(tmp_path / "kg.duckdb")
    result = generate_edge_examples(EdgeExamplesConfig(database_path=db, sample_size=2, quiet=True))
    assert result.total_examples == 4
