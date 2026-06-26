"""Single-pass load on the explicit-columns path.

With `--slots-file`, the read schema is known up front, so the loader skips the
collision-detection DESCRIBE and touches each input exactly once. That makes a
load readable from a non-seekable stream (a FIFO fed by `tar -xO …`), so a
compressed release can be loaded without first extracting its multi-GB JSONL.

These tests would hang (caught by the join-timeout) if the loader regressed to
re-reading the input.
"""

from __future__ import annotations

import os
import threading

import duckdb
import pytest

from koza.graph_operations import load_graph, prepare_load_config_from_paths


def _feed_fifo(path, text: str) -> threading.Thread:
    """Write `text` into a FIFO from a daemon thread (open-for-write blocks until
    the loader opens the read end)."""

    def run():
        with open(path, "w") as f:
            f.write(text)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def _run_with_timeout(cfg, seconds=30):
    box = {}

    def run():
        try:
            box["result"] = load_graph(cfg)
        except BaseException as exc:  # noqa: BLE001 - re-raised on the main thread below
            box["error"] = exc

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=seconds)
    assert not t.is_alive(), "load_graph hung on the FIFO — it re-read a non-seekable input"
    if "error" in box:
        raise box["error"]
    return box["result"]


@pytest.fixture
def slots_file(tmp_path):
    p = tmp_path / "slots.yaml"
    # edges declares file_source so we can check the slots-based collision exclude
    p.write_text(
        "nodes: [id, category, name]\n"
        "edges: [id, subject, predicate, object, file_source]\n"
    )
    return p


requires_fifo = pytest.mark.skipif(
    not hasattr(os, "mkfifo"), reason="os.mkfifo is not available on this platform"
)


@requires_fifo
def test_load_streams_from_fifo_single_pass(tmp_path, slots_file):
    nodes_fifo = tmp_path / "nodes.jsonl"
    edges_fifo = tmp_path / "edges.jsonl"
    os.mkfifo(nodes_fifo)
    os.mkfifo(edges_fifo)

    nodes_txt = "".join(
        f'{{"id":"GENE:{i}","category":["biolink:Gene"],"name":"g{i}"}}\n' for i in range(5)
    )
    edges_txt = "".join(
        f'{{"id":"e{i}","subject":"GENE:{i}","predicate":"biolink:related_to",'
        f'"object":"GENE:{(i + 1) % 5}","file_source":"upstream"}}\n'
        for i in range(5)
    )
    _feed_fifo(nodes_fifo, nodes_txt)
    _feed_fifo(edges_fifo, edges_txt)

    db = tmp_path / "g.duckdb"
    cfg = prepare_load_config_from_paths(
        [nodes_fifo], [edges_fifo], output_database=db, slots_file=slots_file,
        quiet=True, show_progress=False,
    )
    result = _run_with_timeout(cfg)

    assert result.final_stats.nodes == 5
    assert result.final_stats.edges == 5
    # the input's own file_source was excluded (slots-based, no read) and koza's
    # injected one kept — exactly one file_source column, no auto-renamed dup
    con = duckdb.connect(str(db), read_only=True)
    cols = [r[0] for r in con.execute("DESCRIBE edges").fetchall()]
    assert cols.count("file_source") == 1
    assert "file_source_1" not in cols


def _write_tsv(path, header, rows):
    lines = ["\t".join(header)]
    lines += ["\t".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")


def test_tsv_with_slots_excludes_input_file_source(tmp_path):
    """A slots file is set on every input regardless of format, but for TSV the
    read schema is the file's real columns — not the slots. The collision exclude
    must therefore come from a DESCRIBE, otherwise the input's own file_source
    survives and koza's injected one auto-renames to file_source_1."""
    slots = tmp_path / "slots.yaml"
    # edges slots OMIT file_source even though the TSV header carries it
    slots.write_text(
        "nodes: [id, category, name]\n"
        "edges: [id, subject, predicate, object]\n"
    )
    nodes = tmp_path / "nodes.tsv"
    edges = tmp_path / "edges.tsv"
    _write_tsv(nodes, ["id", "category", "name"], [[f"GENE:{i}", "biolink:Gene", f"g{i}"] for i in range(3)])
    _write_tsv(
        edges,
        ["id", "subject", "predicate", "object", "file_source"],
        [[f"e{i}", f"GENE:{i}", "biolink:related_to", f"GENE:{(i + 1) % 3}", "upstream"] for i in range(3)],
    )

    db = tmp_path / "g.duckdb"
    cfg = prepare_load_config_from_paths(
        [nodes], [edges], output_database=db, slots_file=slots, quiet=True, show_progress=False,
    )
    result = load_graph(cfg)

    assert result.final_stats.edges == 3
    con = duckdb.connect(str(db), read_only=True)
    cols = [r[0] for r in con.execute("DESCRIBE edges").fetchall()]
    assert cols.count("file_source") == 1
    assert "file_source_1" not in cols


def test_tsv_with_slots_naming_absent_column_loads(tmp_path):
    """Slots may name a column the TSV file does not have (e.g. file_source). The
    single-pass path would build an EXCLUDE for that column and DuckDB raises a
    Binder Error; the DESCRIBE-based path excludes only columns that exist."""
    slots = tmp_path / "slots.yaml"
    # edges slots INCLUDE file_source, but the TSV header below has no such column
    slots.write_text(
        "nodes: [id, category, name]\n"
        "edges: [id, subject, predicate, object, file_source]\n"
    )
    nodes = tmp_path / "nodes.tsv"
    edges = tmp_path / "edges.tsv"
    _write_tsv(nodes, ["id", "category", "name"], [[f"GENE:{i}", "biolink:Gene", f"g{i}"] for i in range(3)])
    _write_tsv(
        edges,
        ["id", "subject", "predicate", "object"],
        [[f"e{i}", f"GENE:{i}", "biolink:related_to", f"GENE:{(i + 1) % 3}"] for i in range(3)],
    )

    db = tmp_path / "g.duckdb"
    cfg = prepare_load_config_from_paths(
        [nodes], [edges], output_database=db, slots_file=slots, quiet=True, show_progress=False,
    )
    result = load_graph(cfg)

    assert result.final_stats.edges == 3
    con = duckdb.connect(str(db), read_only=True)
    cols = [r[0] for r in con.execute("DESCRIBE edges").fetchall()]
    assert cols.count("file_source") == 1
