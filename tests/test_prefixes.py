"""
Test suite for the prefix report and canonicalize graph operations.
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import canonicalize_graph, generate_prefix_report
from koza.graph_operations.prefixes import load_canonical_prefixes
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import (
    CanonicalizeConfig,
    PrefixReportConfig,
    PrefixStatus,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_database(temp_dir):
    """A database mixing canonical, case-variant, and unknown prefixes."""
    db_file = temp_dir / "test.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes AS SELECT * FROM (VALUES
                ('hgnc:746',      'biolink:Gene',    'gene1'),
                ('hgnc:1100',     'biolink:Gene',    'gene2'),
                ('HGNC:746',      'biolink:Gene',    'gene1-canonical'),
                ('MONDO:0000001', 'biolink:Disease', 'disease1'),
                ('mystery:42',    'biolink:NamedThing', 'unknown-prefix')
            ) AS t(id, category, name)
        """)
        db.conn.execute("""
            CREATE TABLE edges AS SELECT * FROM (VALUES
                ('hgnc:746',  'biolink:causes',     'MONDO:0000001'),
                ('HGNC:746',  'biolink:causes',     'MONDO:0000001'),
                ('mystery:42', 'biolink:related_to', 'hgnc:1100')
            ) AS t(subject, predicate, object)
        """)
    return db_file


def test_load_canonical_prefixes_case_lookup():
    lookup = load_canonical_prefixes("merged")
    assert lookup["hgnc"] == "HGNC"
    assert lookup["mondo"] == "MONDO"


def test_prefix_report_classifies_statuses(test_database):
    result = generate_prefix_report(PrefixReportConfig(database_path=test_database, quiet=True))
    report = result.prefix_report
    by_prefix = {u.prefix: u for u in report.prefixes}

    assert by_prefix["HGNC"].status == PrefixStatus.CANONICAL
    assert by_prefix["MONDO"].status == PrefixStatus.CANONICAL
    assert by_prefix["hgnc"].status == PrefixStatus.CASE_VARIANT
    assert by_prefix["hgnc"].canonical_prefix == "HGNC"
    assert by_prefix["mystery"].status == PrefixStatus.UNKNOWN
    assert report.case_variants == 1

    # counts are split by column
    assert by_prefix["hgnc"].node_ids == 2
    assert by_prefix["hgnc"].edge_subjects == 1
    assert by_prefix["hgnc"].edge_objects == 1


def test_prefix_report_writes_yaml(test_database, temp_dir):
    output = temp_dir / "prefixes.yaml"
    result = generate_prefix_report(PrefixReportConfig(database_path=test_database, output_file=output, quiet=True))
    assert result.output_file == output
    assert "case_variant" in output.read_text()


def test_canonicalize_dry_run_changes_nothing(test_database):
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, dry_run=True, quiet=True))
    assert result.success
    assert result.repairs == {"hgnc": "HGNC"}
    assert result.node_ids_rewritten == 0

    with GraphDatabase(test_database) as db:
        ids = {row[0] for row in db.conn.execute("SELECT id FROM nodes").fetchall()}
    assert "hgnc:746" in ids


def test_canonicalize_repairs_case_variants(test_database):
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))

    assert result.success
    assert result.repairs == {"hgnc": "HGNC"}
    assert result.node_ids_rewritten == 2
    assert result.edge_subjects_rewritten == 1
    assert result.edge_objects_rewritten == 1
    # hgnc:746 landed on the pre-existing HGNC:746 row
    assert result.node_id_collisions == 1
    assert result.warnings

    with GraphDatabase(test_database) as db:
        nodes = db.conn.execute("SELECT id, original_id FROM nodes ORDER BY id").fetchall()
        edges = db.conn.execute("SELECT subject, object, original_subject, original_object FROM edges").fetchall()

    ids = [row[0] for row in nodes]
    assert "hgnc:746" not in ids and "hgnc:1100" not in ids
    assert ids.count("HGNC:746") == 2  # collision retained for dedup to fold
    originals = {row[1] for row in nodes if row[1] is not None}
    assert originals == {"hgnc:746", "hgnc:1100"}

    subjects = {row[0] for row in edges}
    objects = {row[1] for row in edges}
    assert "hgnc:746" not in subjects and "hgnc:1100" not in objects
    assert ("HGNC:746", "MONDO:0000001", "hgnc:746", None) in edges
    # unknown prefix untouched
    assert ("mystery:42", "HGNC:1100", None, "hgnc:1100") in edges


def test_canonicalize_is_idempotent(test_database):
    canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    second = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))

    assert second.success
    assert second.repairs == {}
    assert second.node_ids_rewritten == 0

    # originals from the first pass were not overwritten
    with GraphDatabase(test_database) as db:
        originals = {
            row[0] for row in db.conn.execute("SELECT original_id FROM nodes WHERE original_id IS NOT NULL").fetchall()
        }
    assert originals == {"hgnc:746", "hgnc:1100"}


def test_canonicalize_all_canonical_graph(temp_dir):
    db_file = temp_dir / "clean.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes AS SELECT * FROM (VALUES
                ('HGNC:746', 'biolink:Gene', 'gene1')
            ) AS t(id, category, name)
        """)
        db.conn.execute("""
            CREATE TABLE edges AS SELECT * FROM (VALUES
                ('HGNC:746', 'biolink:related_to', 'HGNC:746')
            ) AS t(subject, predicate, object)
        """)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, quiet=True))
    assert result.success
    assert result.repairs == {}


def test_canonicalize_counts_edge_collisions(test_database):
    # ('hgnc:746', causes, MONDO) becomes a copy of the existing ('HGNC:746', causes, MONDO)
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    assert result.edge_collisions == 1
    assert any("subject/predicate/object" in w for w in result.warnings)


def test_canonicalize_rerun_still_reports_collisions(test_database):
    canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    second = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))

    assert second.repairs == {}
    assert second.node_id_collisions == 1
    assert second.edge_collisions == 1
    assert second.warnings


def test_canonicalize_only_restricts_repairs(temp_dir):
    db_file = temp_dir / "only.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes AS SELECT * FROM (VALUES
                ('hgnc:746',  'biolink:Gene'),
                ('mondo:0001', 'biolink:Disease')
            ) AS t(id, category)
        """)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, only=["HGNC", "chebi"], quiet=True))
    assert result.success
    assert result.repairs == {"hgnc": "HGNC"}
    # a requested prefix with nothing to repair is called out
    assert any("chebi" in w for w in result.warnings)

    with GraphDatabase(db_file) as db:
        ids = {row[0] for row in db.conn.execute("SELECT id FROM nodes").fetchall()}
    assert ids == {"HGNC:746", "mondo:0001"}


def test_canonicalize_warns_about_derived_tables(test_database):
    with GraphDatabase(test_database) as db:
        db.conn.execute("CREATE TABLE closure AS SELECT 'hgnc:746' AS subject_id, 'HGNC:746' AS object_id")

    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    assert result.success
    assert any("closure" in w for w in result.warnings)


def test_canonicalize_edges_only_database(temp_dir):
    db_file = temp_dir / "edges_only.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE edges AS SELECT * FROM (VALUES
                ('hgnc:746', 'biolink:causes', 'MONDO:0000001')
            ) AS t(subject, predicate, object)
        """)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, quiet=True))
    assert result.success
    assert result.edge_subjects_rewritten == 1
    assert result.node_id_collisions == 0


def test_canonicalize_rolls_back_on_failure(test_database, monkeypatch):
    from koza.graph_operations import prefixes

    def boom(db):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(prefixes, "_count_collisions", boom)
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    assert not result.success

    with GraphDatabase(test_database) as db:
        node_ids = {row[0] for row in db.conn.execute("SELECT id FROM nodes").fetchall()}
        subjects = {row[0] for row in db.conn.execute("SELECT subject FROM edges").fetchall()}
        node_cols = {row[0] for row in db.conn.execute("DESCRIBE nodes").fetchall()}
    assert "hgnc:746" in node_ids
    assert "hgnc:746" in subjects
    assert "original_id" not in node_cols


def test_prefix_report_rejects_missing_database(temp_dir):
    missing = temp_dir / "nope.duckdb"
    with pytest.raises(ValueError):
        PrefixReportConfig(database_path=missing)
    assert not missing.exists()
