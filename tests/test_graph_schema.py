"""Tests for the graph_schema module — the seam between operations and the
LinkML-derived schema that lives in each koza-built DuckDB.

See decisions/0002-schema-lives-with-database.md.
"""

from __future__ import annotations

import importlib.resources as ir

import duckdb
import pytest
import yaml
from linkml_runtime.utils.schemaview import SchemaView

from koza.graph_operations import prune_graph
from koza.graph_operations.graph_schema import (
    ASSOCIATION_ROOT,
    _canonical_slot_order,
    _column_slot,
    ENTITY_ROOT,
    UnknownSlotsError,
    current_schema,
    derive_schema,
    discover_declared_outputs,
    duckdb_columns_for_slots,
    ensure_slots,
    export_schema,
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


def test_derived_slots_reference_their_biolink_origin(biolink_schemaview):
    """Each slot flattened from Biolink carries a semantic reference back to
    the Biolink slot it came from: slot_uri (Biolink's canonical predicate URI)
    plus an exact_mapping pinning the Biolink slot identity."""
    schema = derive_schema(
        nodes_headers=["id", "category", "name"],
        edges_headers=["subject", "predicate", "object"],
        biolink_schemaview=biolink_schemaview,
    )

    # slot_uri reflects Biolink's own mapping — biolink: for most, rdfs:/rdf:
    # for the slots Biolink maps elsewhere.
    assert schema.slots["category"].slot_uri == "biolink:category"
    assert schema.slots["name"].slot_uri == "rdfs:label"
    assert schema.slots["subject"].slot_uri == "rdf:subject"

    # exact_mappings always pin the originating Biolink slot identity.
    assert schema.slots["category"].exact_mappings == ["biolink:category"]
    assert schema.slots["name"].exact_mappings == ["biolink:name"]
    assert schema.slots["subject"].exact_mappings == ["biolink:subject"]

    # Koza extras are not Biolink-derived and carry no Biolink reference.
    assert not schema.slots["file_source"].exact_mappings


def test_derived_slots_carry_their_biolink_range(biolink_schemaview):
    """Biolink-typed slots carry Biolink's range, captured at derive time so it
    persists in the stored schema rather than defaulting to string at export."""
    schema = derive_schema(
        nodes_headers=["id", "category", "name"],
        edges_headers=["subject", "predicate", "object", "negated", "has_count", "has_percentage"],
        biolink_schemaview=biolink_schemaview,
    )

    assert schema.slots["has_count"].range == "integer"
    assert schema.slots["has_percentage"].range == "double"
    assert schema.slots["negated"].range == "boolean"
    # Full scope: string-ish ranges are emitted explicitly too, not left to default.
    assert schema.slots["category"].range == "uriorcurie"


def test_derived_ranges_reduce_to_standalone_primitives(biolink_schemaview):
    """Class-, enum-, and type-valued Biolink ranges are reduced to LinkML
    primitives so the released schema (which imports only `linkml:types`) has no
    dangling range references — the contract linkml-solr's create-schema needs.
    """
    schema = derive_schema(
        nodes_headers=["id", "name", "in_taxon", "has_attribute"],
        edges_headers=["subject", "predicate", "object", "knowledge_level"],
        biolink_schemaview=biolink_schemaview,
    )

    # Biolink type whose typeof chain bottoms out at string (`label type`).
    assert schema.slots["name"].range == "string"
    # Biolink class-valued slots hold CURIE references → uriorcurie.
    assert schema.slots["in_taxon"].range == "uriorcurie"
    assert schema.slots["subject"].range == "uriorcurie"
    assert schema.slots["object"].range == "uriorcurie"
    # Biolink enum-valued slot serializes permissible values as strings.
    assert schema.slots["knowledge_level"].range == "string"

    # Every emitted range resolves against linkml:types alone — no Biolink
    # class/enum/type names leak into the standalone schema.
    standalone = {
        "string", "integer", "boolean", "float", "double", "decimal",
        "date", "datetime", "time", "uriorcurie", "uri",
    }
    from jsonasobj2 import items

    for name, slot in items(schema.slots):
        assert slot.range is None or slot.range in standalone, (
            f"slot {name!r} has non-primitive range {slot.range!r}"
        )


def test_export_declares_prefixes_for_slot_references(biolink_schemaview, tmp_path):
    """The exported schema must declare every prefix its slot references use so
    it stays standalone-loadable for CURIE expansion."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category", "name"],
            edges_headers=["subject", "predicate", "object"],
            biolink_schemaview=biolink_schemaview,
        )
        exported = export_schema(conn, project_denormalized=False)
    finally:
        conn.close()

    assert "biolink: https://w3id.org/biolink/vocab/" in exported
    assert "rdfs: http://www.w3.org/2000/01/rdf-schema#" in exported
    assert "rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#" in exported
    assert "slot_uri: rdfs:label" in exported
    assert "biolink:name" in exported

    # The actual contract: the exported schema loads standalone and its
    # CURIEs resolve — not just that the text appears.
    reloaded = SchemaView(exported)
    assert reloaded.expand_curie("rdfs:label") == "http://www.w3.org/2000/01/rdf-schema#label"
    assert reloaded.expand_curie("biolink:name") == "https://w3id.org/biolink/vocab/name"


def test_export_recovers_range_for_computed_scalar_columns(biolink_schemaview, tmp_path):
    """Computed, non-Biolink scalar columns (e.g. has_phenotype_count) get their
    range from the DuckDB column type, so they don't fall back to string."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category", "name"],
            edges_headers=["subject", "predicate", "object", "has_phenotype_count"],
            biolink_schemaview=biolink_schemaview,
        )
        # has_phenotype_count isn't a Biolink slot — its only type signal is the
        # DuckDB column. (The denormalized views are what export introspects.)
        conn.execute(
            "CREATE TABLE denormalized_edges "
            "(subject VARCHAR, predicate VARCHAR, object VARCHAR, has_phenotype_count BIGINT)"
        )
        exported = export_schema(conn, project_denormalized=False)
    finally:
        conn.close()

    reloaded = SchemaView(exported)
    assert reloaded.get_slot("has_phenotype_count").range == "integer"


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


def test_canonical_slot_order_leads_with_identity_slots():
    """Identity slots come first in a fixed order; everything else follows
    alphabetically. A plain sort would lead with `broad_synonym` and bury `id`."""
    assert _canonical_slot_order(["xref", "name", "broad_synonym", "id", "category"]) == [
        "id",
        "category",
        "name",
        "broad_synonym",
        "xref",
    ]
    # Absent lead slots are simply skipped, not invented.
    assert _canonical_slot_order(["object", "subject", "provided_by"]) == [
        "subject",
        "object",
        "provided_by",
    ]


def test_export_is_ordered_deterministically(biolink_schemaview, tmp_path):
    """The released schema must be byte-stable across builds, so a diff between
    two releases carries only real change (issue #253).

    Prefixes previously came off a set — whose iteration order Python randomizes
    per process via PYTHONHASHSEED — and class slot lists followed DuckDB column
    order, so semantically identical builds serialized differently. Asserting
    sorted order here is what makes the output independent of both.
    """
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            # Deliberately unsorted, with `id` late, so input order can't be
            # mistaken for canonical order.
            nodes_headers=["name", "id", "category", "xref", "description"],
            edges_headers=["object", "subject", "predicate", "knowledge_source"],
            biolink_schemaview=biolink_schemaview,
        )
        exported = export_schema(conn, project_denormalized=False)
    finally:
        conn.close()

    doc = yaml.safe_load(exported)

    assert list(doc["prefixes"]) == sorted(doc["prefixes"])
    assert list(doc["slots"]) == sorted(doc["slots"])
    assert list(doc["classes"]) == sorted(doc["classes"])

    # Identity slots lead each class, in _LEAD_SLOTS order, ahead of the
    # alphabetical tail — this is what reaches users as CLI/TSV column order.
    for class_name, class_def in doc["classes"].items():
        slots = class_def["slots"]
        assert slots == _canonical_slot_order(slots), f"{class_name} slots not canonical"

    assert doc["classes"]["Entity"]["slots"][:3] == ["id", "category", "name"]
    assert doc["classes"]["Association"]["slots"][:3] == ["subject", "predicate", "object"]


def _export_projected_after_closurize(biolink_schemaview, db_path, node_cols, edge_cols):
    """Seed, simulate closurize's denormalized views with the given column order,
    evolve the schema as closurize does, and export via the default projected path."""
    from koza.graph_operations.closurize import _evolve_schema_for_denormalized

    conn = duckdb.connect(str(db_path))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category", "name", "xref"],
            edges_headers=["subject", "predicate", "object", "knowledge_source"],
            biolink_schemaview=biolink_schemaview,
        )
        conn.execute(f"CREATE TABLE denormalized_nodes ({', '.join(node_cols)})")
        conn.execute(f"CREATE TABLE denormalized_edges ({', '.join(edge_cols)})")
        _evolve_schema_for_denormalized(conn)
        return export_schema(conn)  # project_denormalized=True, as released
    finally:
        conn.close()


def test_projected_export_is_independent_of_denormalized_column_order(biolink_schemaview, tmp_path):
    """The released artifact goes through the projected path, where Entity /
    Association take their slot lists from DESCRIBE of the denormalized views.
    Two builds whose views differ only in column order must export identically."""
    node_cols = [
        "id VARCHAR",
        "category VARCHAR",
        "name VARCHAR",
        "xref VARCHAR[]",
        "has_phenotype VARCHAR[]",
        "has_phenotype_count BIGINT",
    ]
    edge_cols = [
        "subject VARCHAR",
        "predicate VARCHAR",
        "object VARCHAR",
        "knowledge_source VARCHAR",
        "subject_closure VARCHAR[]",
        "object_label VARCHAR",
    ]

    first = _export_projected_after_closurize(biolink_schemaview, tmp_path / "a.duckdb", node_cols, edge_cols)
    second = _export_projected_after_closurize(
        biolink_schemaview,
        tmp_path / "b.duckdb",
        list(reversed(node_cols)),
        edge_cols[3:] + edge_cols[:3],
    )
    assert first == second

    doc = yaml.safe_load(first)
    assert set(doc["classes"]) == {"Entity", "Association"}
    assert doc["classes"]["Entity"]["slots"] == [
        "id",
        "category",
        "name",
        "has_phenotype",
        "has_phenotype_count",
        "xref",
    ]
    assert doc["classes"]["Association"]["slots"] == [
        "subject",
        "predicate",
        "object",
        "knowledge_source",
        "object_label",
        "subject_closure",
    ]


# --- inlined class slots (issue #261) ---------------------------------------

_SOURCES_STRUCT_LIST = (
    "STRUCT(category VARCHAR[], id VARCHAR, resource_id VARCHAR, "
    "resource_role VARCHAR, source_record_urls VARCHAR[])[]"
)


def test_column_slot_applies_class_level_slot_usage(biolink_schemaview):
    """Biolink's `association` declares `sources` inlined_as_list via
    slot_usage; the global slot doesn't. The column shape must see it."""
    assert not biolink_schemaview.get_slot("sources").inlined_as_list
    shape = _column_slot(biolink_schemaview, "sources", ASSOCIATION_ROOT)
    assert shape.multivalued and shape.inlined_as_list


def test_column_slot_range_is_broadest_across_descendants(biolink_schemaview):
    """Subclasses narrow `object` to their own ranges; one column holds all of
    them, so its shape keeps the root's range."""
    assert _column_slot(biolink_schemaview, "object", ASSOCIATION_ROOT).range == "named thing"


def test_struct_list_column_declares_inlined_class(biolink_schemaview):
    schema = derive_schema(
        nodes_headers=["id", "category"],
        edges_headers=["subject", "predicate", "object", "sources"],
        biolink_schemaview=biolink_schemaview,
        edges_column_types={"sources": _SOURCES_STRUCT_LIST},
    )
    sources = schema.slots["sources"]
    assert sources.range == "RetrievalSource"
    assert sources.multivalued and sources.inlined and sources.inlined_as_list

    retrieval_source = schema.classes["RetrievalSource"]
    assert retrieval_source.class_uri == "biolink:RetrievalSource"
    attrs = retrieval_source.attributes
    assert set(attrs) == {"category", "id", "resource_id", "resource_role", "source_record_urls"}
    assert attrs["resource_id"].range == "uriorcurie"
    assert attrs["resource_role"].range == "string"  # enum → string
    assert attrs["source_record_urls"].multivalued
    assert not attrs["resource_id"].multivalued


def test_class_slot_with_reference_column_stays_curie(biolink_schemaview):
    """A class-valued slot stored as CURIEs (VARCHAR[]) is a reference, not
    inlined — the column type is the evidence, not Biolink's flag alone."""
    for column_types in ({"sources": "VARCHAR[]"}, None):
        schema = derive_schema(
            nodes_headers=["id", "category"],
            edges_headers=["subject", "predicate", "object", "sources"],
            biolink_schemaview=biolink_schemaview,
            edges_column_types=column_types,
        )
        assert schema.slots["sources"].range == "uriorcurie"
        assert not schema.slots["sources"].inlined
        assert "RetrievalSource" not in schema.classes


def test_export_with_inlined_class_loads_standalone(biolink_schemaview, tmp_path):
    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category"],
            edges_headers=["subject", "predicate", "object", "sources"],
            biolink_schemaview=biolink_schemaview,
            edges_column_types={"sources": _SOURCES_STRUCT_LIST},
        )
        conn.execute(
            "CREATE TABLE denormalized_edges (subject VARCHAR, predicate VARCHAR, "
            f"object VARCHAR, sources {_SOURCES_STRUCT_LIST})"
        )
        exported = export_schema(conn, project_denormalized=False)
    finally:
        conn.close()

    reloaded = SchemaView(exported)
    sources = reloaded.induced_slot("sources", "Association")
    assert sources.range == "RetrievalSource"
    assert sources.multivalued and sources.inlined_as_list
    assert reloaded.induced_slot("resource_id", "RetrievalSource").range == "uriorcurie"


def test_export_multivalued_follows_outer_column_type(biolink_schemaview, tmp_path):
    """Only a list column is multivalued: a scalar STRUCT with a list field is
    one record, any `<type>[]` or fixed-size `<type>[n]` is a list, and a slot
    stored multivalued whose column is a scalar is exported single-valued."""
    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category", "flags"],
            edges_headers=["subject", "predicate", "object", "record", "counts", "pair"],
            biolink_schemaview=biolink_schemaview,
            declared_outputs={"Entity": {"flags": {"range": "string", "multivalued": True}}},
        )
        assert current_schema(conn).slots["flags"].multivalued
        conn.execute("CREATE TABLE denormalized_nodes (id VARCHAR, category VARCHAR, flags VARCHAR)")
        conn.execute(
            "CREATE TABLE denormalized_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, "
            "record STRUCT(urls VARCHAR[]), counts BIGINT[], pair VARCHAR[2])"
        )
        exported = yaml.safe_load(export_schema(conn, project_denormalized=False))
    finally:
        conn.close()

    slots = exported["slots"]
    assert not slots["record"].get("multivalued")
    assert slots["counts"]["multivalued"] is True
    assert slots["pair"]["multivalued"] is True
    assert not slots["flags"].get("multivalued")


def test_slot_on_nodes_and_edges_gets_one_shape_covering_both(biolink_schemaview):
    """Nodes and edges share one slot namespace. A records list on one table and
    a single record on the other must stay inlined_as_list, not become
    multivalued+inlined (a dict keyed by identifier)."""
    struct = "STRUCT(attribute_name VARCHAR, has_attribute_type VARCHAR)"
    schema = derive_schema(
        nodes_headers=["id", "category", "has_attribute"],
        edges_headers=["subject", "predicate", "object", "has_attribute"],
        biolink_schemaview=biolink_schemaview,
        nodes_column_types={"has_attribute": f"{struct}[]"},
        edges_column_types={"has_attribute": struct},
    )
    slot = schema.slots["has_attribute"]
    assert slot.range == "Attribute"
    assert slot.multivalued and slot.inlined and slot.inlined_as_list


def test_records_beat_curie_references_across_tables(biolink_schemaview):
    schema = derive_schema(
        nodes_headers=["id", "category", "has_attribute"],
        edges_headers=["subject", "predicate", "object", "has_attribute"],
        biolink_schemaview=biolink_schemaview,
        nodes_column_types={"has_attribute": "STRUCT(attribute_name VARCHAR)[]"},
        edges_column_types={"has_attribute": "VARCHAR[]"},
    )
    slot = schema.slots["has_attribute"]
    assert slot.range == "Attribute" and slot.inlined_as_list


def test_inlined_class_field_widens_across_columns(biolink_schemaview):
    """A class reached from several columns gets each field widened to cover
    all of them, not the first column's shape."""
    schema = derive_schema(
        nodes_headers=["id", "category", "has_attribute"],
        edges_headers=["subject", "predicate", "object", "has_attribute"],
        biolink_schemaview=biolink_schemaview,
        nodes_column_types={"has_attribute": "STRUCT(has_attribute_type VARCHAR)[]"},
        edges_column_types={"has_attribute": "STRUCT(has_attribute_type VARCHAR[])[]"},
    )
    assert schema.classes["Attribute"].attributes["has_attribute_type"].multivalued


def test_fixed_size_struct_array_is_inlined_as_list(biolink_schemaview):
    schema = derive_schema(
        nodes_headers=["id", "category"],
        edges_headers=["subject", "predicate", "object", "sources"],
        biolink_schemaview=biolink_schemaview,
        edges_column_types={"sources": "STRUCT(resource_id VARCHAR)[2]"},
    )
    assert schema.slots["sources"].inlined_as_list


def test_export_single_record_and_curie_list_is_inlined_as_list(biolink_schemaview, tmp_path):
    """A single STRUCT on nodes and a CURIE list on edges: the merged slot is
    inlined and single-valued at seed time, and export makes it multivalued from
    the list column, so it must also set inlined_as_list (never a dict)."""
    struct = "STRUCT(attribute_name VARCHAR)"
    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category", "has_attribute"],
            edges_headers=["subject", "predicate", "object", "has_attribute"],
            biolink_schemaview=biolink_schemaview,
            nodes_column_types={"has_attribute": struct},
            edges_column_types={"has_attribute": "VARCHAR[]"},
        )
        conn.execute(f"CREATE TABLE denormalized_nodes (id VARCHAR, category VARCHAR, has_attribute {struct})")
        conn.execute(
            "CREATE TABLE denormalized_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, "
            "has_attribute VARCHAR[])"
        )
        exported = yaml.safe_load(export_schema(conn, project_denormalized=False))
    finally:
        conn.close()

    slot = exported["slots"]["has_attribute"]
    assert slot["range"] == "Attribute"
    assert slot["multivalued"] is True and slot["inlined"] is True and slot["inlined_as_list"] is True


@pytest.mark.parametrize("order", ["varchar_first", "integer_first"])
def test_non_biolink_struct_field_widens_to_string(biolink_schemaview, order):
    """A non-Biolink struct field that is VARCHAR in one column and INTEGER in
    another holds strings somewhere, so the class field is `string`."""
    types = ["STRUCT(attribute_name VARCHAR, extra VARCHAR)[]", "STRUCT(attribute_name VARCHAR, extra INTEGER)[]"]
    if order == "integer_first":
        types.reverse()
    schema = derive_schema(
        nodes_headers=["id", "category", "has_attribute"],
        edges_headers=["subject", "predicate", "object", "has_attribute"],
        biolink_schemaview=biolink_schemaview,
        nodes_column_types={"has_attribute": types[0]},
        edges_column_types={"has_attribute": types[1]},
    )
    assert schema.classes["Attribute"].attributes["extra"].range == "string"


def test_explicit_single_valued_survives_node_edge_merge(biolink_schemaview, tmp_path):
    """Koza extras are declared multivalued: false on both tables; merging the
    two must keep that explicit false rather than dropping it."""
    schema = derive_schema(
        nodes_headers=["id", "category"],
        edges_headers=["subject", "predicate", "object"],
        biolink_schemaview=biolink_schemaview,
    )
    assert schema.slots["provided_by"].multivalued is False
    assert schema.slots["file_source"].multivalued is False



@pytest.mark.parametrize("order", ["bigint_first", "double_first"])
def test_non_biolink_struct_field_widens_integer_to_float(biolink_schemaview, order):
    """BIGINT vs DOUBLE on a field of a class reached from two columns: the
    float range holds both, whichever column comes first."""
    from koza.graph_operations.graph_schema import _inline_class, _list_element, _parse_duckdb_type

    pair = ["STRUCT(resource_id VARCHAR, extra BIGINT)[]", "STRUCT(resource_id VARCHAR, extra DOUBLE)[]"]
    if order == "double_first":
        pair.reverse()
    classes = {}
    for col_type in pair:
        element, _ = _list_element(_parse_duckdb_type(col_type))
        _inline_class(biolink_schemaview, "retrieval source", element, classes)
    assert classes["RetrievalSource"].attributes["extra"].range == "float"


def test_export_clears_inlined_as_list_when_column_is_single_valued(biolink_schemaview, tmp_path):
    """Seeded as a list of records, but a single record in the denormalized
    view: exported single-valued, with no leftover inlined_as_list."""
    struct = "STRUCT(resource_id VARCHAR)"
    conn = duckdb.connect(str(tmp_path / "test.duckdb"))
    try:
        seed_schema(
            conn,
            nodes_headers=["id", "category"],
            edges_headers=["subject", "predicate", "object", "sources"],
            biolink_schemaview=biolink_schemaview,
            edges_column_types={"sources": f"{struct}[]"},
        )
        assert current_schema(conn).slots["sources"].inlined_as_list
        conn.execute("CREATE TABLE denormalized_nodes (id VARCHAR, category VARCHAR)")
        conn.execute(
            "CREATE TABLE denormalized_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, "
            f"sources {struct})"
        )
        exported = yaml.safe_load(export_schema(conn, project_denormalized=False))
    finally:
        conn.close()
    sources = exported["slots"]["sources"]
    assert not sources.get("multivalued")
    assert not sources.get("inlined_as_list")
    assert sources["inlined"] is True
