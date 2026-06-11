"""Tests for the load operation — a faithful single-step load of KGX node/edge
files into a DuckDB, as opposed to the cat-merge-style `join`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest

from koza.graph_operations import join_graphs, load_graph, prepare_load_config_from_paths
from koza.model.graph_operations import (
    FileSpec,
    JoinConfig,
    KGXFileType,
    KGXFormat,
    LoadConfig,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def kg_with_provided_by(temp_dir):
    """A KG already carrying its own `provided_by` provenance — the case where
    `join`'s filename-stamping would clobber it but `load` should preserve it."""
    nodes = temp_dir / "mykg_nodes.jsonl"
    nodes.write_text(
        '{"id": "HGNC:1", "category": "biolink:Gene", "name": "g1", "provided_by": "upstream_source"}\n'
        '{"id": "MONDO:1", "category": "biolink:Disease", "name": "d1", "provided_by": "upstream_source"}\n'
    )
    edges = temp_dir / "mykg_edges.jsonl"
    edges.write_text(
        '{"id": "e1", "subject": "HGNC:1", "predicate": "biolink:related_to", '
        '"object": "MONDO:1", "category": "biolink:Association", "provided_by": "upstream_source"}\n'
    )
    return nodes, edges


def _provided_by(db_path, table):
    """Distinct provided_by values as a flat set. `provided_by` is Biolink
    multivalued, so a preserved value can land as a 1-element array; flatten so
    the test compares value content, not array/scalar wrapping."""
    with duckdb.connect(str(db_path), read_only=True) as c:
        cols = [r[0] for r in c.execute(f"DESCRIBE {table}").fetchall()]
        if "provided_by" not in cols:
            return None
        rows = [r[0] for r in c.execute(f"SELECT DISTINCT provided_by FROM {table}").fetchall()]
    flat = set()
    for v in rows:
        if isinstance(v, list):
            flat.update(v)
        elif v is not None:
            flat.add(v)
    return flat


def test_load_creates_nodes_and_edges(kg_with_provided_by, temp_dir):
    nodes, edges = kg_with_provided_by
    db = temp_dir / "out.duckdb"
    result = load_graph(LoadConfig(
        node_files=[FileSpec(path=nodes, format=KGXFormat.JSONL, file_type=KGXFileType.NODES)],
        edge_files=[FileSpec(path=edges, format=KGXFormat.JSONL, file_type=KGXFileType.EDGES)],
        output_database=db, quiet=True, show_progress=False,
    ))
    assert result.final_stats.nodes == 2
    assert result.final_stats.edges == 1
    with duckdb.connect(str(db), read_only=True) as c:
        tables = {r[0] for r in c.execute("SHOW TABLES").fetchall()}
    assert {"nodes", "edges"}.issubset(tables)


def test_load_preserves_provided_by(kg_with_provided_by, temp_dir):
    """load defaults to generate_provided_by=False — existing provided_by survives."""
    nodes, edges = kg_with_provided_by
    db = temp_dir / "load.duckdb"
    load_graph(LoadConfig(
        node_files=[FileSpec(path=nodes, format=KGXFormat.JSONL, file_type=KGXFileType.NODES)],
        edge_files=[FileSpec(path=edges, format=KGXFormat.JSONL, file_type=KGXFileType.EDGES)],
        output_database=db, quiet=True, show_progress=False,
    ))
    assert _provided_by(db, "nodes") == {"upstream_source"}
    assert _provided_by(db, "edges") == {"upstream_source"}


def test_join_clobbers_provided_by_load_does_not(kg_with_provided_by, temp_dir):
    """Contrast: join (generate_provided_by=True) overwrites provided_by with the
    source filename stem; load preserves the original."""
    nodes, edges = kg_with_provided_by
    join_db = temp_dir / "join.duckdb"
    join_graphs(JoinConfig(
        node_files=[FileSpec(path=nodes, format=KGXFormat.JSONL, file_type=KGXFileType.NODES)],
        edge_files=[FileSpec(path=edges, format=KGXFormat.JSONL, file_type=KGXFileType.EDGES)],
        output_database=join_db, quiet=True, show_progress=False,
    ))
    # join stamps provided_by from the filename stem
    assert _provided_by(join_db, "nodes") == {"mykg_nodes"}

    load_db = temp_dir / "load2.duckdb"
    load_graph(LoadConfig(
        node_files=[FileSpec(path=nodes, format=KGXFormat.JSONL, file_type=KGXFileType.NODES)],
        edge_files=[FileSpec(path=edges, format=KGXFormat.JSONL, file_type=KGXFileType.EDGES)],
        output_database=load_db, quiet=True, show_progress=False,
    ))
    assert _provided_by(load_db, "nodes") == {"upstream_source"}


def test_load_generate_provided_by_opt_in(kg_with_provided_by, temp_dir):
    """Passing generate_provided_by=True restores the cat-merge stamping."""
    nodes, edges = kg_with_provided_by
    db = temp_dir / "stamped.duckdb"
    load_graph(LoadConfig(
        node_files=[FileSpec(path=nodes, format=KGXFormat.JSONL, file_type=KGXFileType.NODES)],
        edge_files=[FileSpec(path=edges, format=KGXFormat.JSONL, file_type=KGXFileType.EDGES)],
        output_database=db, generate_provided_by=True, quiet=True, show_progress=False,
    ))
    assert _provided_by(db, "nodes") == {"mykg_nodes"}


def test_prepare_load_config_from_paths(kg_with_provided_by, temp_dir):
    """The paths helper builds a LoadConfig (faithful defaults) and load_graph runs it."""
    nodes, edges = kg_with_provided_by
    db = temp_dir / "viahelper.duckdb"
    config = prepare_load_config_from_paths(
        node_files=[nodes], edge_files=[edges], output_database=db,
        quiet=True, show_progress=False,
    )
    assert isinstance(config, LoadConfig)
    assert config.generate_provided_by is False
    assert config.schema_reporting is False
    result = load_graph(config)
    assert result.final_stats.nodes == 2
    assert _provided_by(db, "edges") == {"upstream_source"}
