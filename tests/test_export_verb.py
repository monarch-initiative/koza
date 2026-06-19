"""Tests for the export / convert verbs.

export writes the canonical nodes/edges tables to single KGX files; convert is
load + export. The serialization policy matters for TSV: scalar lists become
|-delimited, nested object columns (sources, ...) become JSON-in-cell (a plain
`SELECT * COPY` would emit DuckDB struct-repr — neither JSON nor valid KGX).
"""

from __future__ import annotations

import duckdb
import pytest

from koza.graph_operations.export import convert_graph, export_graph
from koza.model.graph_operations import ConvertConfig, ExportConfig


@pytest.fixture
def graph_db(tmp_path):
    """A DuckDB graph whose edges carry a nested `sources` list-of-struct and a
    scalar `publications` list — the shapes the policy has to handle."""
    db = tmp_path / "g.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute(
        """
        CREATE TABLE nodes AS
        SELECT 'GENE:1' AS id, ['biolink:Gene','biolink:NamedThing'] AS category, 'g1' AS name;

        CREATE TABLE edges AS
        SELECT 'GENE:1' AS subject, 'biolink:treats' AS predicate, 'MONDO:1' AS object,
            ['PMID:1','PMID:2'] AS publications,
            [{'resource_id':'infores:medic','resource_role':'primary_knowledge_source'},
             {'resource_id':'infores:dailymed','resource_role':'supporting_data_source'}] AS sources;
        """
    )
    conn.close()
    return db


def _read_tsv(path):
    return duckdb.sql(f"SELECT * FROM read_csv('{path}', delim='\t', header=true, all_varchar=true)").df()


def test_export_tsv_serializes_nested_json_and_pipe_lists(graph_db, tmp_path):
    out = tmp_path / "out"
    result = export_graph(ExportConfig(database_path=graph_db, output_dir=out, output_format="tsv", quiet=True))
    assert {p.name for p in result.output_files} == {"nodes.tsv", "edges.tsv"}

    edges = _read_tsv(out / "edges.tsv")
    # scalar list -> KGX pipe-join
    assert edges["publications"].iloc[0] == "PMID:1|PMID:2"
    # nested list-of-struct -> JSON-in-cell, round-trippable
    src = edges["sources"].iloc[0]
    assert duckdb.sql(f"SELECT json_valid('{src}')").fetchone()[0]
    assert duckdb.sql(f"SELECT json_extract_string('{src}', '$[0].resource_id')").fetchone()[0] == "infores:medic"

    nodes = _read_tsv(out / "nodes.tsv")
    assert nodes["category"].iloc[0] == "biolink:Gene|biolink:NamedThing"


def test_export_jsonl_keeps_nested_structure(graph_db, tmp_path):
    out = tmp_path / "out"
    export_graph(ExportConfig(database_path=graph_db, output_dir=out, output_format="jsonl", quiet=True))
    row = duckdb.sql(
        f"SELECT sources, publications FROM read_json('{out / 'edges.jsonl'}', format='newline_delimited')"
    ).fetchone()
    assert row[0][0]["resource_id"] == "infores:medic"   # sources stays a list of structs
    assert list(row[1]) == ["PMID:1", "PMID:2"]


def test_export_parquet_preserves_types(graph_db, tmp_path):
    out = tmp_path / "out"
    export_graph(ExportConfig(database_path=graph_db, output_dir=out, output_format="parquet", quiet=True))
    types = {
        r[0]: r[1]
        for r in duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{out / 'edges.parquet'}')").fetchall()
    }
    assert "STRUCT" in types["sources"].upper()  # nested type preserved, not flattened


def test_export_skips_missing_tables(graph_db, tmp_path):
    out = tmp_path / "out"
    result = export_graph(
        ExportConfig(
            database_path=graph_db, output_dir=out, output_format="tsv",
            tables=["edges", "denormalized_edges"], quiet=True,
        )
    )
    assert [p.name for p in result.output_files] == ["edges.tsv"]  # denormalized_edges absent -> skipped


def test_convert_jsonl_to_tsv(tmp_path):
    """convert = load + export: a jsonl edge file with nested sources -> tsv with
    sources serialized as JSON."""
    edges = tmp_path / "edges.jsonl"
    edges.write_text(
        '{"subject":"GENE:1","predicate":"biolink:treats","object":"MONDO:1",'
        '"publications":["PMID:1"],'
        '"sources":[{"resource_id":"infores:medic","resource_role":"primary_knowledge_source"}]}\n'
    )
    out = tmp_path / "out"
    result = convert_graph(ConvertConfig(edge_files=[edges], output_dir=out, output_format="tsv", quiet=True))
    assert (out / "edges.tsv").exists()
    df = _read_tsv(out / "edges.tsv")
    src = df["sources"].iloc[0]
    assert duckdb.sql(f"SELECT json_extract_string('{src}', '$[0].resource_id')").fetchone()[0] == "infores:medic"
    assert int(result.row_counts["edges"]) == 1
