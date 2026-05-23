"""Tests for the graph_schema module — the seam between operations and the
LinkML-derived schema that lives in each koza-built DuckDB.

See decisions/0002-schema-lives-with-database.md.
"""

from __future__ import annotations

import importlib.resources as ir

import duckdb
import pytest
from linkml_runtime.utils.schemaview import SchemaView

from koza.graph_operations import prune_graph
from koza.graph_operations.graph_schema import (
    ASSOCIATION_ROOT,
    ENTITY_ROOT,
    UnknownSlotsError,
    current_schema,
    derive_schema,
    discover_declared_outputs,
    duckdb_columns_for_slots,
    ensure_slots,
    seed_schema,
    stored_biolink_yaml,
)
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import PruneConfig


@pytest.fixture(scope="module")
def biolink_schemaview() -> SchemaView:
    with ir.as_file(ir.files("biolink_model.schema") / "biolink_model.yaml") as p:
        return SchemaView(str(p))


def test_derive_schema_flattens_entity_class_from_node_headers(biolink_schemaview):
    schema = derive_schema(
        nodes_headers=["id", "category", "name"],
        edges_headers=["subject", "predicate", "object"],
        biolink_schemaview=biolink_schemaview,
    )

    entity_slots = set(schema.classes["Entity"].slots)
    assert {"id", "category", "name"}.issubset(entity_slots)


def test_file_source_is_injected_as_koza_extra(biolink_schemaview):
    """file_source is injected unconditionally by load_file; the schema must
    include it on both classes even when it is absent from file headers."""
    schema = derive_schema(
        nodes_headers=["id", "category", "name"],
        edges_headers=["subject", "predicate", "object"],
        biolink_schemaview=biolink_schemaview,
    )
    assert "file_source" in schema.classes["Entity"].slots
    assert "file_source" in schema.classes["Association"].slots


def test_operation_declared_outputs_are_valid_slots(biolink_schemaview):
    """Operations declare their output slots via DECLARED_OUTPUTS; the schema
    treats those as valid slots so files containing them are accepted even on a
    fresh graph where the producing operation has not yet run."""
    schema = derive_schema(
        nodes_headers=["id", "category"],
        edges_headers=["subject", "predicate", "object", "mapping_source"],
        biolink_schemaview=biolink_schemaview,
        declared_outputs={
            "Association": {
                "mapping_source": {
                    "description": "SSSOM mapping provenance.",
                    "range": "string",
                    "multivalued": False,
                },
            },
        },
    )
    assert "mapping_source" in schema.classes["Association"].slots


def test_file_source_in_headers_is_accepted_not_rejected(biolink_schemaview):
    """`load_file` always injects file_source, so when join seeds the schema
    against final-table headers the column is present. file_source must not
    trip strict-reject since it's a known koza extra."""
    schema = derive_schema(
        nodes_headers=["id", "category", "file_source"],
        edges_headers=["subject", "predicate", "object", "file_source"],
        biolink_schemaview=biolink_schemaview,
    )
    assert "file_source" in schema.classes["Entity"].slots
    assert "file_source" in schema.classes["Association"].slots


def test_derive_schema_rejects_unknown_columns(biolink_schemaview):
    with pytest.raises(UnknownSlotsError) as exc_info:
        derive_schema(
            nodes_headers=["id", "name", "bogus_column"],
            edges_headers=["subject", "predicate", "object"],
            biolink_schemaview=biolink_schemaview,
        )
    assert "bogus_column" in str(exc_info.value)


def test_derive_schema_permissive_records_unknowns_as_minimal_slots(biolink_schemaview):
    """With strict=False, unknown columns become VARCHAR slots so the
    derived schema reflects whatever's in the data — used by seed_schema
    to record an already-loaded graph rather than enforce validation."""
    schema = derive_schema(
        nodes_headers=["id", "name", "bogus_column"],
        edges_headers=["subject", "predicate", "object"],
        biolink_schemaview=biolink_schemaview,
        strict=False,
    )
    assert "bogus_column" in schema.classes["Entity"].slots


def test_seed_and_read_schema_round_trip(biolink_schemaview, tmp_path):
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category", "name"],
            edges_headers=["subject", "predicate", "object"],
            biolink_schemaview=biolink_schemaview,
        )
        schema = current_schema(conn)
    finally:
        conn.close()

    assert "Entity" in schema.classes
    assert "Association" in schema.classes
    assert "id" in schema.classes["Entity"].slots
    assert "subject" in schema.classes["Association"].slots


def test_biolink_yaml_stored_in_seeded_database(biolink_schemaview, tmp_path):
    """Per ADR-0002: Biolink is stored in the database at seed time so
    routine operations never need to re-read it from the environment."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            nodes_headers=["id"],
            edges_headers=["subject", "predicate", "object"],
            biolink_schemaview=biolink_schemaview,
        )
        biolink_yaml = stored_biolink_yaml(conn)
    finally:
        conn.close()

    assert biolink_yaml is not None
    assert "named thing" in biolink_yaml
    assert "association" in biolink_yaml


def test_ensure_slots_adds_column_and_updates_stored_schema(
    biolink_schemaview, tmp_path
):
    """ensure_slots materializes operation-declared slots: ALTER TABLEs the
    data table and updates the stored schema so subsequent reads see the new
    slot."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            nodes_headers=["id"],
            edges_headers=["subject", "predicate", "object"],
            biolink_schemaview=biolink_schemaview,
            declared_outputs={
                "Association": {
                    "original_subject": {
                        "description": "Subject ID before normalization.",
                        "range": "string",
                        "multivalued": False,
                    },
                }
            },
        )
        conn.execute(
            "CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR)"
        )

        ensure_slots(conn, "edges", ["original_subject"])

        cols = [r[0] for r in conn.execute("DESCRIBE edges").fetchall()]
        schema_after = current_schema(conn)
    finally:
        conn.close()

    assert "original_subject" in cols
    assert "original_subject" in schema_after.classes["Association"].slots


def test_ensure_slots_is_idempotent(biolink_schemaview, tmp_path):
    """Operations can safely call ensure_slots multiple times: the second
    call is a no-op, no error, no duplicate columns."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            nodes_headers=["id"],
            edges_headers=["subject", "predicate", "object"],
            biolink_schemaview=biolink_schemaview,
            declared_outputs={
                "Association": {
                    "original_subject": {
                        "description": "Subject ID before normalization.",
                        "range": "string",
                        "multivalued": False,
                    },
                }
            },
        )
        conn.execute(
            "CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR)"
        )

        ensure_slots(conn, "edges", ["original_subject"])
        ensure_slots(conn, "edges", ["original_subject"])

        cols = [r[0] for r in conn.execute("DESCRIBE edges").fetchall()]
    finally:
        conn.close()

    assert cols.count("original_subject") == 1


def test_discover_declared_outputs_unions_known_operations():
    """The hardcoded operation-module list in graph_schema gets walked and
    each module's DECLARED_OUTPUTS is unioned. normalize is the only
    operation that currently declares outputs (original_subject /
    original_object on Association)."""
    outputs = discover_declared_outputs()
    assert "Association" in outputs
    assert "original_subject" in outputs["Association"]
    assert "original_object" in outputs["Association"]


def test_ensure_slots_tolerates_unseeded_database(tmp_path):
    """ensure_slots should still work on a graph that predates the schema
    feature: ALTER TABLE happens, but the missing _koza_schema metadata
    table is silently ignored. The column type falls back to VARCHAR."""
    db_path = tmp_path / "legacy.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR)")

        ensure_slots(conn, "edges", ["original_subject"])

        cols = {r[0]: r[1] for r in conn.execute("DESCRIBE edges").fetchall()}
    finally:
        conn.close()

    assert "original_subject" in cols
    assert cols["original_subject"] == "VARCHAR"


def test_prune_against_seeded_database(biolink_schemaview, tmp_path):
    """Proof point. A graph seeded via the schema module satisfies prune's
    contract: file_source exists, so prune drops its DESCRIBE/try-except
    dance and trusts the slot registry. Dangling edges and their per-source
    breakdown are computed correctly end-to-end."""
    db_path = tmp_path / "seeded.duckdb"

    with GraphDatabase(db_path) as db:
        seed_schema(
            db.conn,
            nodes_headers=["id", "category", "name"],
            edges_headers=["subject", "predicate", "object"],
            biolink_schemaview=biolink_schemaview,
        )
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1', 'gene_info'),
                ('HGNC:456', 'biolink:Gene', 'gene2', 'gene_info');
        """)
        db.conn.execute("""
            CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            INSERT INTO edges VALUES
                ('HGNC:123', 'biolink:related_to', 'HGNC:456', 'gene_links'),
                ('HGNC:123', 'biolink:related_to', 'MISSING:001', 'gene_links'),
                ('MISSING:002', 'biolink:causes', 'HGNC:456', 'phenotype_links');
        """)
        db.conn.execute("CREATE TABLE duplicate_nodes (id VARCHAR);")

    result = prune_graph(
        PruneConfig(
            database_path=db_path,
            keep_singletons=True,
            remove_singletons=False,
            quiet=True,
            show_progress=False,
        )
    )

    assert result.dangling_edges_moved == 2
    assert result.dangling_edges_by_source == {
        "gene_links": 1,
        "phenotype_links": 1,
    }
    assert result.final_stats.edges == 1


# ---------------------------------------------------------------------------
# duckdb_columns_for_slots — LinkML-flag dispatch for explicit-schema JSONL.
# ---------------------------------------------------------------------------


def test_columns_for_primitive_scalar_slot(biolink_schemaview):
    cols = duckdb_columns_for_slots(["id", "name"], ENTITY_ROOT, biolink_schemaview)
    assert cols == {"id": "VARCHAR", "name": "VARCHAR"}


def test_columns_for_multivalued_primitive_slot(biolink_schemaview):
    # `category` is multivalued with range=uriorcurie (primitive) → VARCHAR[].
    cols = duckdb_columns_for_slots(["category"], ENTITY_ROOT, biolink_schemaview)
    assert cols == {"category": "VARCHAR[]"}


def test_columns_for_numeric_and_boolean_slots(biolink_schemaview):
    cols = duckdb_columns_for_slots(
        ["p_value", "evidence_count", "negated"],
        ASSOCIATION_ROOT,
        biolink_schemaview,
    )
    assert cols == {
        "p_value": "DOUBLE",
        "evidence_count": "BIGINT",
        "negated": "BOOLEAN",
    }


def test_columns_for_class_ref_scalar_slot(biolink_schemaview):
    # `subject` has class range (named thing) and is scalar → CURIE reference → VARCHAR.
    cols = duckdb_columns_for_slots(["subject"], ASSOCIATION_ROOT, biolink_schemaview)
    assert cols == {"subject": "VARCHAR"}


def test_columns_for_inlined_as_list_class_slot_uses_struct_array(biolink_schemaview):
    # `sources` is multivalued + inlined_as_list=True → STRUCT(...)[].
    cols = duckdb_columns_for_slots(["sources"], ASSOCIATION_ROOT, biolink_schemaview)
    t = cols["sources"]
    assert t.startswith("STRUCT(") and t.endswith(")[]")
    assert "resource_id" in t
    assert "resource_role" in t


def test_columns_for_inlined_class_slot_uses_map(biolink_schemaview):
    # `has_supporting_studies` is multivalued + inlined=True (no inlined_as_list)
    # → dict-keyed-by-id → MAP(VARCHAR, STRUCT(...)).
    cols = duckdb_columns_for_slots(
        ["has_supporting_studies"], ASSOCIATION_ROOT, biolink_schemaview
    )
    t = cols["has_supporting_studies"]
    assert t.startswith("MAP(VARCHAR, STRUCT(") and t.endswith("))")


def test_columns_for_multivalued_curie_refs(biolink_schemaview):
    # `publications` is multivalued with class range but neither inlined flag
    # set → list of CURIE references → VARCHAR[].
    cols = duckdb_columns_for_slots(
        ["publications"], ASSOCIATION_ROOT, biolink_schemaview
    )
    assert cols == {"publications": "VARCHAR[]"}


def test_columns_for_koza_extras_resolve_without_biolink(biolink_schemaview):
    cols = duckdb_columns_for_slots(
        ["file_source", "provided_by"], ENTITY_ROOT, biolink_schemaview
    )
    assert cols == {"file_source": "VARCHAR", "provided_by": "VARCHAR"}


def test_columns_for_declared_outputs(biolink_schemaview):
    cols = duckdb_columns_for_slots(
        ["mapping_source"],
        ASSOCIATION_ROOT,
        biolink_schemaview,
        declared_outputs={
            "mapping_source": {
                "description": "SSSOM mapping provenance.",
                "range": "string",
                "multivalued": False,
            },
        },
    )
    assert cols == {"mapping_source": "VARCHAR"}


def test_columns_strict_rejects_unknown_slot(biolink_schemaview):
    with pytest.raises(UnknownSlotsError, match="not_a_real_biolink_slot"):
        duckdb_columns_for_slots(
            ["id", "not_a_real_biolink_slot"], ENTITY_ROOT, biolink_schemaview
        )


def test_columns_permissive_admits_unknown_as_varchar(biolink_schemaview):
    cols = duckdb_columns_for_slots(
        ["id", "not_a_real_biolink_slot"],
        ENTITY_ROOT,
        biolink_schemaview,
        strict=False,
    )
    assert cols == {"id": "VARCHAR", "not_a_real_biolink_slot": "VARCHAR"}
