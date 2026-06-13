"""Tests for Biolink edge-type / node-prefix validation.

Covers the asserted-class strict check (the precision win), the union fallback
for edges with no asserted class, scalar-vs-list category + biolink: prefix
normalization (monarch-kg shape), and the multivalued-lenient prefix check.
"""

from __future__ import annotations

import duckdb
import pytest

from koza.graph_operations.validate import generate_validation_report
from koza.model.graph_operations import TabularReportFormat, ValidationConfig


def _build(path, nodes_sql, edges_sql):
    conn = duckdb.connect(str(path))
    conn.execute(f"CREATE TABLE nodes AS {nodes_sql}")
    conn.execute(f"CREATE TABLE edges AS {edges_sql}")
    conn.close()


def _run(db, tmp_path):
    out = tmp_path / "validation"
    generate_validation_report(
        ValidationConfig(database_path=db, output_dir=out, output_format=TabularReportFormat.PARQUET, quiet=True)
    )
    sub = duckdb.sql(f"SELECT * FROM '{out}/subobj_errors.parquet'").df()
    pre = duckdb.sql(f"SELECT * FROM '{out}/prefix_errors.parquet'").df()
    return sub, pre


def test_asserted_class_catches_bad_object(tmp_path):
    """An edge that ASSERTS GeneRegulatesGeneAssociation but points at a Disease
    object is flagged BAD_OBJECT (strict) — the union alone could not catch it."""
    db = tmp_path / "kg.duckdb"
    _build(
        db,
        """SELECT * FROM (VALUES
            ('GENE:1', ['biolink:Gene']),
            ('GENE:2', ['biolink:Gene']),
            ('MONDO:1', ['biolink:Disease'])) t(id, category)""",
        """SELECT * FROM (VALUES
            ('GENE:1','biolink:regulates','GENE:2', ['biolink:GeneRegulatesGeneAssociation']),
            ('GENE:1','biolink:regulates','MONDO:1',['biolink:GeneRegulatesGeneAssociation'])
          ) t(subject, predicate, object, category)""",
    )
    sub, _ = _run(db, tmp_path)
    # the good Gene→Gene edge is not a violation; only the Gene→Disease one is
    assert len(sub) == 1
    row = sub.iloc[0]
    assert row["verdict"] == "BAD_OBJECT"
    assert bool(row["strict_checked"]) is True
    assert int(row["count"]) == 1


def test_fallback_used_when_no_asserted_category(tmp_path):
    """Edges with no `category` column go through the union fallback (advisory)."""
    db = tmp_path / "kg.duckdb"
    _build(
        db,
        "SELECT * FROM (VALUES ('GENE:1', ['biolink:Gene']), ('GENE:2', ['biolink:Gene'])) t(id, category)",
        "SELECT * FROM (VALUES ('GENE:1','biolink:regulates','GENE:2')) t(subject, predicate, object)",
    )
    sub, _ = _run(db, tmp_path)
    # whatever the verdict, the fallback path must have been used (not strict)
    assert (~sub["strict_checked"].astype(bool)).all() if len(sub) else True


def test_scalar_category_and_biolink_normalization(tmp_path):
    """monarch-kg shape: scalar category, stored WITHOUT the biolink: prefix.
    Gene→related_to→Gene must normalize and not be flagged as illegal."""
    db = tmp_path / "kg.duckdb"
    _build(
        db,
        "SELECT * FROM (VALUES ('GENE:1','Gene'), ('GENE:2','Gene')) t(id, category)",  # scalar, bare
        "SELECT * FROM (VALUES ('GENE:1','biolink:related_to','GENE:2')) t(subject, predicate, object)",
    )
    sub, _ = _run(db, tmp_path)
    assert "NOT_IN_LEGAL_TYPES" not in set(sub["verdict"]) if len(sub) else True


def test_prefix_check_is_multivalued_lenient(tmp_path):
    """A node valid under ANY of its categories isn't flagged; a bogus prefix is."""
    db = tmp_path / "kg.duckdb"
    _build(
        db,
        """SELECT * FROM (VALUES
            ('NCBIGene:1', ['biolink:Gene','biolink:Protein']),
            ('BOGUS:1',    ['biolink:Gene'])) t(id, category)""",
        "SELECT * FROM (VALUES ('NCBIGene:1','biolink:related_to','BOGUS:1')) t(subject, predicate, object)",
    )
    _, pre = _run(db, tmp_path)
    prefixes = set(pre["prefix"])
    assert "BOGUS" in prefixes          # bogus prefix flagged
    assert "NCBIGene" not in prefixes   # valid-under-Gene node not flagged
