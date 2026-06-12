"""Tests for the schema-smart graph profile / shape report."""

from __future__ import annotations

import importlib.resources as ir

import duckdb
import pytest
from linkml_runtime.utils.schemaview import SchemaView

from koza.graph_operations.profile import (
    detect_categorical_columns,
    profile_graph,
    profile_table,
    render_profile,
)
from koza.model.graph_operations import ProfileConfig


@pytest.fixture(scope="module")
def sv() -> SchemaView:
    with ir.as_file(ir.files("biolink_model.schema") / "biolink_model.yaml") as p:
        return SchemaView(str(p))


@pytest.fixture
def kg(tmp_path):
    """A small graph exercising every detector branch:
    categorical (predicate, category, knowledge_level enum, negated boolean),
    identifiers (id, subject, object), free text (name), numeric (evidence_count),
    struct (sources), and a class-ranged-but-low-cardinality slot (in_taxon)."""
    db = tmp_path / "kg.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute("""
        CREATE TABLE edges AS
        SELECT
            'e' || i::VARCHAR                                   AS id,
            'GENE:' || i::VARCHAR                               AS subject,
            'MONDO:' || i::VARCHAR                              AS object,
            ['biolink:related_to','biolink:causes','biolink:treats'][(i % 3) + 1] AS predicate,
            'biolink:Association'                               AS category,
            ['knowledge_assertion','prediction'][(i % 2) + 1]   AS knowledge_level,
            (i % 2 = 0)                                         AS negated,
            'edge name ' || i::VARCHAR                          AS name,
            (i * 7)::BIGINT                                     AS evidence_count,
            (i % 4)::VARCHAR                                    AS has_count,
            ['a','b','c','d'][(i % 4) + 1]                       AS mystery,
            {'resource_id': 'infores:x', 'n': i}               AS sources
        FROM range(30) t(i);
        CREATE TABLE nodes AS
        SELECT
            'GENE:' || i::VARCHAR                               AS id,
            ['biolink:Gene','biolink:Disease'][(i % 2) + 1]     AS category,
            'node name ' || i::VARCHAR                          AS name,
            ['NCBITaxon:9606','NCBITaxon:10090'][(i % 2) + 1]   AS in_taxon
        FROM range(30) t(i);
    """)
    conn.close()
    return db


def _names(cats):
    return {c.name for c in cats}


def test_detect_edges_schema_smart(kg, sv):
    conn = duckdb.connect(str(kg), read_only=True)
    cats = detect_categorical_columns(conn, "edges", sv)
    names = _names(cats)
    # categorical
    assert {"predicate", "category", "knowledge_level", "negated"}.issubset(names)
    # excluded: identifiers, free text, numeric, struct
    assert "subject" not in names
    assert "object" not in names
    assert "id" not in names
    assert "name" not in names
    assert "evidence_count" not in names  # numeric
    assert "sources" not in names  # struct
    reasons = {c.name: c.reason for c in cats}
    assert reasons["category"] == "category"  # designates_type
    assert reasons["predicate"] == "predicate"
    assert reasons["knowledge_level"] == "enum"
    assert reasons["negated"] == "boolean"


def test_numeric_biolink_range_excluded_even_as_varchar(kg, sv):
    """has_count is range:integer in Biolink but stored as VARCHAR here — the
    schema range, not the column type, must exclude it as a measurement."""
    conn = duckdb.connect(str(kg), read_only=True)
    names = _names(detect_categorical_columns(conn, "edges", sv))
    assert "has_count" not in names


def test_max_distinct_ceiling_caps_probe(kg, sv):
    """A non-schema (probe) column above the ceiling is dropped, however low its
    ratio; the schema floor is exempt."""
    conn = duckdb.connect(str(kg), read_only=True)
    # `mystery` (4 distinct, non-Biolink) is categorical by default …
    assert "mystery" in _names(detect_categorical_columns(conn, "edges", sv))
    # … but excluded when the ceiling is below its distinct count.
    capped = _names(detect_categorical_columns(conn, "edges", sv, max_distinct_ceiling=3))
    assert "mystery" not in capped
    # schema-categoricals (predicate has 3 distinct) stay regardless of ceiling
    assert "predicate" in capped


def test_detect_nodes_includes_low_card_class_slot(kg, sv):
    conn = duckdb.connect(str(kg), read_only=True)
    names = _names(detect_categorical_columns(conn, "nodes", sv))
    assert "category" in names
    # in_taxon is class-ranged (organism taxon) but low-cardinality → probe keeps it
    assert "in_taxon" in names
    assert "name" not in names
    assert "id" not in names


def test_detect_without_schema_cardinality_only(kg):
    """sv=None → cardinality-only path still gives a sensible result.

    Non-constant categoricals are found by cardinality; subject (perfectly
    unique) and evidence_count (numeric) are excluded. The constant `category`
    is dropped here — without the schema there's no signal to keep a constant
    (the schema path keeps it via designates_type; see the edges test)."""
    conn = duckdb.connect(str(kg), read_only=True)
    names = _names(detect_categorical_columns(conn, "edges", sv=None))
    assert {"predicate", "knowledge_level", "negated"}.issubset(names)
    assert "subject" not in names  # perfectly unique → identifier-like
    assert "object" not in names
    assert "evidence_count" not in names  # numeric excluded by type


def test_profile_table_marginals(kg, sv):
    conn = duckdb.connect(str(kg), read_only=True)
    tp = profile_table(conn, "edges", sv, top_n=5)
    assert tp.row_count == 30
    pred = next(c for c in tp.columns if c.column == "predicate")
    assert pred.distinct_count == 3
    assert sum(count for _, count in pred.top_values) == 30
    assert all(isinstance(v, str) for v, _ in pred.top_values)


def test_columns_override(kg, sv):
    conn = duckdb.connect(str(kg), read_only=True)
    tp = profile_table(conn, "edges", sv, columns=["predicate", "subject"])
    cols = {c.column for c in tp.columns}
    assert cols == {"predicate", "subject"}  # override forces even high-card subject in


def test_profile_graph_and_render(kg, sv):
    result = profile_graph(ProfileConfig(database_path=kg, top_n=5, quiet=True))
    tables = {tp.table for tp in result.tables}
    assert {"edges", "nodes"}.issubset(tables)
    text = render_profile(result)
    assert "predicate" in text
    assert "edges — 30 rows" in text


def test_profile_output_file(kg, sv, tmp_path):
    out = tmp_path / "shape.tsv"
    result = profile_graph(ProfileConfig(database_path=kg, output_file=out, quiet=True))
    assert out.exists()
    conn = duckdb.connect()
    rows = conn.execute(
        f"SELECT DISTINCT column_name FROM read_csv_auto('{out}', sep='\t')"
    ).fetchall()
    cols = {r[0] for r in rows}
    assert "predicate" in cols
