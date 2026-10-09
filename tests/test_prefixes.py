"""
Test suite for the prefix report and canonicalize graph operations.
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import canonicalize_graph, generate_prefix_report
from koza.graph_operations.prefixes import LOG_TABLE, REMOVED_TABLES, load_canonical_prefixes
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
    assert by_prefix["hgnc"].status == PrefixStatus.ALTERNATE_CASING
    assert by_prefix["hgnc"].canonical_prefix == "HGNC"
    assert by_prefix["mystery"].status == PrefixStatus.UNKNOWN
    assert report.alternate_casing == 1

    # counts are split by column
    assert by_prefix["hgnc"].node_ids == 2
    assert by_prefix["hgnc"].edge_subjects == 1
    assert by_prefix["hgnc"].edge_objects == 1


def test_prefix_report_writes_yaml(test_database, temp_dir):
    output = temp_dir / "prefixes.yaml"
    result = generate_prefix_report(PrefixReportConfig(database_path=test_database, output_file=output, quiet=True))
    assert result.output_file == output
    text = output.read_text()
    assert "status: alternate_casing" in text
    assert "!!python" not in text


def _columns(db_file, table):
    with GraphDatabase(db_file) as db:
        return {row[0] for row in db.conn.execute(f"DESCRIBE {table}").fetchall()}


def _tables(db_file):
    with GraphDatabase(db_file) as db:
        return {row[0] for row in db.conn.execute("SELECT table_name FROM information_schema.tables").fetchall()}


def _log(db_file):
    with GraphDatabase(db_file) as db:
        return db.conn.execute(f"""
            SELECT action, table_name, column_name, old_prefix, new_prefix, example_value, row_count
            FROM {LOG_TABLE} ORDER BY run_at, action, table_name, column_name
        """).fetchall()


def test_canonicalize_dry_run_changes_nothing(test_database):
    result = canonicalize_graph(
        CanonicalizeConfig(database_path=test_database, dry_run=True, deduplicate=True, quiet=True)
    )
    assert result.success
    assert result.repairs == {"hgnc": "HGNC"}
    # a dry run does the work and rolls it back, so the counts are a real preview
    assert result.node_ids_rewritten == 2
    assert result.nodes_removed == 1 and result.edges_removed == 1

    with GraphDatabase(test_database) as db:
        ids = [row[0] for row in db.conn.execute("SELECT id FROM nodes").fetchall()]
    assert "hgnc:746" in ids and len(ids) == 5
    tables = _tables(test_database)
    assert LOG_TABLE not in tables
    assert not set(REMOVED_TABLES.values()) & tables


def test_canonicalize_repairs_alternate_casing(test_database):
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))

    assert result.success
    assert result.repairs == {"hgnc": "HGNC"}
    assert result.node_ids_rewritten == 2
    assert result.edge_subjects_rewritten == 1
    assert result.edge_objects_rewritten == 1
    # hgnc:746 landed on the pre-existing HGNC:746 row
    assert result.node_id_collisions == 1
    assert result.nodes_removed == 0
    assert any("--deduplicate" in w for w in result.warnings)

    with GraphDatabase(test_database) as db:
        ids = [row[0] for row in db.conn.execute("SELECT id FROM nodes").fetchall()]
        edges = db.conn.execute("SELECT subject, object FROM edges").fetchall()

    assert "hgnc:746" not in ids and "hgnc:1100" not in ids
    assert ids.count("HGNC:746") == 2  # collision kept without --deduplicate
    assert ("HGNC:746", "MONDO:0000001") in edges
    # unknown prefix untouched
    assert ("mystery:42", "HGNC:1100") in edges


def test_canonicalize_writes_no_original_columns(test_database):
    canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    assert "original_id" not in _columns(test_database, "nodes")
    edge_cols = _columns(test_database, "edges")
    assert "original_subject" not in edge_cols and "original_object" not in edge_cols


def test_canonicalize_audit_log(test_database):
    canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    assert _log(test_database) == [
        ("rewrite", "edges", "object", "hgnc", "HGNC", "hgnc:1100", 1),
        ("rewrite", "edges", "subject", "hgnc", "HGNC", "hgnc:746", 1),
        ("rewrite", "nodes", "id", "hgnc", "HGNC", "hgnc:1100", 2),
    ]


def test_canonicalize_rerun_is_a_noop(test_database):
    canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    first_log = _log(test_database)
    second = canonicalize_graph(CanonicalizeConfig(database_path=test_database, deduplicate=True, quiet=True))

    assert second.success
    assert second.repairs == {}
    assert second.node_ids_rewritten == 0
    # --deduplicate only acts on rows rewritten in the same run: nothing here
    assert second.node_id_collisions == 0 and second.edge_collisions == 0
    assert second.nodes_removed == 0 and second.edges_removed == 0
    assert _log(test_database) == first_log
    with GraphDatabase(test_database) as db:
        assert db.conn.execute("SELECT COUNT(*) FROM nodes WHERE id = 'HGNC:746'").fetchone()[0] == 2


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
    assert LOG_TABLE not in _tables(db_file)


def test_canonicalize_counts_edge_collisions(test_database):
    # ('hgnc:746', causes, MONDO) becomes a copy of the existing ('HGNC:746', causes, MONDO)
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    assert result.edge_collisions == 1
    assert any("identical (apart from id)" in w for w in result.warnings)


def test_canonicalize_deduplicate_removes_collisions(test_database):
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, deduplicate=True, quiet=True))

    assert result.success
    assert result.node_id_collisions == 1 and result.edge_collisions == 1
    assert result.nodes_removed == 1 and result.edges_removed == 1
    assert not any("--deduplicate" in w for w in result.warnings)

    with GraphDatabase(test_database) as db:
        nodes = db.conn.execute("SELECT id, name FROM nodes WHERE id = 'HGNC:746'").fetchall()
        edge_count = db.conn.execute(
            "SELECT COUNT(*) FROM edges WHERE subject = 'HGNC:746' AND object = 'MONDO:0000001'"
        ).fetchone()[0]
        total_nodes = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    # the pre-existing canonical row wins over the rewritten one
    assert nodes == [("HGNC:746", "gene1-canonical")]
    assert edge_count == 1
    assert total_nodes == 4

    dedup_rows = [row for row in _log(test_database) if row[0] == "deduplicate"]
    assert dedup_rows == [
        ("deduplicate", "edges", "all columns except id", None, None, "HGNC:746", 1),
        ("deduplicate", "nodes", "id", None, None, "HGNC:746", 1),
    ]


def test_canonicalize_deduplicate_leaves_unrelated_duplicates(temp_dir):
    db_file = temp_dir / "unrelated.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes AS SELECT * FROM (VALUES
                ('hgnc:1', 'a'),
                ('MONDO:1', 'b'),
                ('MONDO:1', 'c')
            ) AS t(id, name)
        """)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, deduplicate=True, quiet=True))
    assert result.success
    assert result.node_id_collisions == 0
    assert result.nodes_removed == 0
    with GraphDatabase(db_file) as db:
        assert db.conn.execute("SELECT COUNT(*) FROM nodes WHERE id = 'MONDO:1'").fetchone()[0] == 2


def test_canonicalize_deduplicate_prefers_file_source(temp_dir):
    db_file = temp_dir / "file_source.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes AS SELECT * FROM (VALUES
                ('hgnc:1', 'b.tsv', 'second'),
                ('Hgnc:1', 'a.tsv', 'first')
            ) AS t(id, file_source, name)
        """)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, deduplicate=True, quiet=True))
    assert result.nodes_removed == 1
    with GraphDatabase(db_file) as db:
        assert db.conn.execute("SELECT name FROM nodes").fetchall() == [("first",)]


def test_canonicalize_only_restricts_repairs(temp_dir):
    db_file = temp_dir / "only.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes AS SELECT * FROM (VALUES
                ('hgnc:746',  'biolink:Gene'),
                ('mondo:0001', 'biolink:Disease')
            ) AS t(id, category)
        """)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, only=["HGNC"], quiet=True))
    assert result.success
    assert result.repairs == {"hgnc": "HGNC"}

    with GraphDatabase(db_file) as db:
        ids = {row[0] for row in db.conn.execute("SELECT id FROM nodes").fetchall()}
    assert ids == {"HGNC:746", "mondo:0001"}


def test_canonicalize_only_typo_is_an_error(test_database):
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, only=["hngc"], quiet=True))
    assert not result.success
    assert "hngc" in result.errors[0] and "did you mean: hgnc" in result.errors[0]
    with GraphDatabase(test_database) as db:
        assert db.conn.execute("SELECT COUNT(*) FROM nodes WHERE id LIKE 'hgnc:%'").fetchone()[0] == 2


def test_canonicalize_warns_about_derived_tables(test_database):
    with GraphDatabase(test_database) as db:
        db.conn.execute("CREATE TABLE closure AS SELECT 'hgnc:746' AS subject_id, 'HGNC:746' AS object_id")

    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, quiet=True))
    assert result.success
    derived = [w for w in result.warnings if "should be rebuilt" in w]
    assert derived and "closure" in derived[0]
    assert LOG_TABLE not in derived[0]


def test_canonicalize_edges_only_database(temp_dir):
    db_file = temp_dir / "edges_only.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE edges AS SELECT * FROM (VALUES
                ('hgnc:746', 'biolink:causes', 'MONDO:0000001')
            ) AS t(subject, predicate, object)
        """)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, deduplicate=True, quiet=True))
    assert result.success
    assert result.edge_subjects_rewritten == 1
    assert result.node_id_collisions == 0


def test_canonicalize_rolls_back_on_failure(test_database, monkeypatch):
    from koza.graph_operations import prefixes

    real = prefixes._remove_collisions

    def boom(db, table, log_params):
        real(db, table, log_params)  # sidecar written, rows deleted ...
        raise RuntimeError("injected failure")  # ... then fail

    monkeypatch.setattr(prefixes, "_remove_collisions", boom)
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, deduplicate=True, quiet=True))
    assert not result.success

    with GraphDatabase(test_database) as db:
        node_ids = [row[0] for row in db.conn.execute("SELECT id FROM nodes").fetchall()]
        subjects = {row[0] for row in db.conn.execute("SELECT subject FROM edges").fetchall()}
    assert "hgnc:746" in node_ids and len(node_ids) == 5
    assert "hgnc:746" in subjects
    tables = _tables(test_database)
    assert LOG_TABLE not in tables
    assert not set(REMOVED_TABLES.values()) & tables


def test_prefix_report_rejects_missing_database(temp_dir):
    missing = temp_dir / "nope.duckdb"
    with pytest.raises(ValueError):
        PrefixReportConfig(database_path=missing)
    assert not missing.exists()


def test_canonicalize_deduplicate_copies_removed_rows_to_sidecars(test_database):
    result = canonicalize_graph(CanonicalizeConfig(database_path=test_database, deduplicate=True, quiet=True))
    assert result.nodes_removed == 1 and result.edges_removed == 1

    with GraphDatabase(test_database) as db:
        removed_nodes = db.conn.execute(
            f"SELECT run_at IS NOT NULL, id, category, name FROM {REMOVED_TABLES['nodes']}"
        ).fetchall()
        removed_edges = db.conn.execute(
            f"SELECT run_at IS NOT NULL, subject, predicate, object FROM {REMOVED_TABLES['edges']}"
        ).fetchall()
    # the rewritten row is the one removed; it differed from the kept row in `name`
    assert removed_nodes == [(True, "HGNC:746", "biolink:Gene", "gene1")]
    assert removed_edges == [(True, "HGNC:746", "biolink:causes", "MONDO:0000001")]


def _repro_database(db_file):
    """Pre-existing canonical duplicates plus one alternately-cased node and edge."""
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes AS SELECT * FROM (VALUES
                ('HGNC:1',   'gene1',  'a.tsv'),
                ('HGNC:1',   'gene1b', 'b.tsv'),
                ('HGNC:746', 'canon',  'a.tsv'),
                ('hgnc:746', 'repair', 'c.tsv')
            ) AS t(id, name, file_source)
        """)
        db.conn.execute("""
            CREATE TABLE edges AS SELECT * FROM (VALUES
                ('e1', 'HGNC:1',   'biolink:causes', 'MONDO:1', 'infores:a', NULL),
                ('e2', 'HGNC:1',   'biolink:causes', 'MONDO:1', 'infores:a', NULL),
                ('e3', 'HGNC:1',   'biolink:causes', 'MONDO:1', 'infores:b', 'PATO:male'),
                ('e4', 'HGNC:746', 'biolink:causes', 'MONDO:2', 'infores:a', NULL),
                ('e5', 'hgnc:746', 'biolink:causes', 'MONDO:2', 'infores:a', NULL),
                ('e6', 'hgnc:746', 'biolink:causes', 'MONDO:2', 'infores:b', NULL),
                ('e7', 'HGNC:746', 'biolink:causes', 'MONDO:2', 'infores:c', 'PATO:male'),
                ('e8', 'hgnc:746', 'biolink:causes', 'MONDO:2', 'infores:c', 'PATO:female')
            ) AS t(id, subject, predicate, object, primary_knowledge_source, sex_qualifier)
        """)


def test_canonicalize_never_removes_preexisting_rows(temp_dir):
    db_file = temp_dir / "repro.duckdb"
    _repro_database(db_file)

    plain = canonicalize_graph(CanonicalizeConfig(database_path=db_file, quiet=True))
    assert plain.node_id_collisions == 1  # hgnc:746 onto HGNC:746; the HGNC:1 pair predates the run
    assert plain.edge_collisions == 1  # only e5 is identical (apart from id) to an existing edge
    assert any("run the repair itself with --deduplicate" in w for w in plain.warnings)

    # following up with --deduplicate does nothing: nothing was rewritten in this run
    followup = canonicalize_graph(CanonicalizeConfig(database_path=db_file, deduplicate=True, quiet=True))
    assert followup.nodes_removed == 0 and followup.edges_removed == 0
    with GraphDatabase(db_file) as db:
        assert db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == 4
        assert db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 8


def test_canonicalize_deduplicate_keeps_preexisting_and_distinct_edges(temp_dir):
    db_file = temp_dir / "repro.duckdb"
    _repro_database(db_file)

    result = canonicalize_graph(CanonicalizeConfig(database_path=db_file, deduplicate=True, quiet=True))
    assert result.nodes_removed == 1 and result.edges_removed == 1

    with GraphDatabase(db_file) as db:
        nodes = db.conn.execute("SELECT id, name FROM nodes ORDER BY id, name").fetchall()
        edge_ids = {row[0] for row in db.conn.execute("SELECT id FROM edges").fetchall()}
    # pre-existing duplicate HGNC:1 rows untouched; canonical HGNC:746 kept over the repaired row
    assert nodes == [("HGNC:1", "gene1"), ("HGNC:1", "gene1b"), ("HGNC:746", "canon")]
    # only e5 (identical to e4 apart from id) is removed; pre-existing e1/e2 duplicates stay,
    # and edges differing in source (e6) or qualifier (e8) are kept
    assert edge_ids == {"e1", "e2", "e3", "e4", "e6", "e7", "e8"}
