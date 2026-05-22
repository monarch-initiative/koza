"""Tests for the closurize operation — wraps `closurizer.add_closure` and
evolves the stored graph schema to include the denormalized classes.
"""

from __future__ import annotations

import importlib.resources as ir

import duckdb
import pytest
from linkml_runtime.utils.schemaview import SchemaView

from koza.graph_operations import closurize_graph
from koza.graph_operations.graph_schema import current_schema, seed_schema
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import ClosurizeConfig


@pytest.fixture(scope="module")
def biolink_schemaview() -> SchemaView:
    with ir.as_file(ir.files("biolink_model.schema") / "biolink_model.yaml") as p:
        return SchemaView(str(p))


@pytest.fixture
def synthetic_kg(tmp_path):
    """A tiny graph that's just big enough for closurize to do something
    meaningful: 4 nodes, 3 edges (one has_phenotype, two subclass_of), a
    closure file connecting the phenotype to two ancestors."""
    db_path = tmp_path / "kg.duckdb"
    closure_path = tmp_path / "phenio-relation-filtered.tsv"
    closure_path.write_text(
        "MP:0001\tbiolink:subclass_of\tMP:0001\n"
        "MP:0001\tbiolink:subclass_of\tMP:0\n"
        "MP:0001\tbiolink:subclass_of\tBFO:0000001\n"
        "MGI:1\tbiolink:subclass_of\tMGI:1\n"
        "DISEASE:1\tbiolink:subclass_of\tDISEASE:1\n"
    )

    with GraphDatabase(db_path) as db:
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR,
                                in_taxon VARCHAR, in_taxon_label VARCHAR,
                                file_source VARCHAR);
            INSERT INTO nodes VALUES
                ('MGI:1', 'biolink:Gene', 'gene1', 'NCBITaxon:10090', 'mouse', 'mgi_gene'),
                ('MP:0001', 'biolink:PhenotypicFeature', 'phenotype1', NULL, NULL, 'mp'),
                ('MP:0', 'biolink:PhenotypicFeature', 'phenotype-root', NULL, NULL, 'mp'),
                ('DISEASE:1', 'biolink:Disease', 'disease1', NULL, NULL, 'mondo');
        """)
        db.conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR,
                                category VARCHAR, has_evidence VARCHAR[], publications VARCHAR[],
                                negated BOOLEAN, file_source VARCHAR, namespace VARCHAR);
            INSERT INTO edges VALUES
                ('e1', 'MGI:1', 'biolink:has_phenotype', 'MP:0001', 'biolink:Association',
                 ['ECO:1'], ['PMID:1'], false, 'mgi_assoc', 'MGI'),
                ('e2', 'MGI:1', 'biolink:related_to', 'DISEASE:1', 'biolink:Association',
                 NULL, NULL, false, 'mgi_assoc', 'MGI');
        """)

    return db_path, closure_path


def test_closurize_produces_denormalized_tables(synthetic_kg, biolink_schemaview):
    db_path, closure_path = synthetic_kg

    # Seed the schema first so closurize has _koza_schema to evolve.
    with GraphDatabase(db_path) as db:
        seed_schema(
            db.conn,
            nodes_headers=["id", "category", "name", "in_taxon", "in_taxon_label"],
            edges_headers=["id", "subject", "predicate", "object", "category",
                           "has_evidence", "publications", "negated", "namespace"],
            biolink_schemaview=biolink_schemaview,
        )

    result = closurize_graph(
        ClosurizeConfig(
            database_path=db_path,
            closure_file=closure_path,
            node_fields=["has_phenotype"],
            edge_fields=["subject", "object"],
            evidence_fields=["has_evidence", "publications"],
            grouping_fields=["subject", "negated", "predicate", "object"],
            quiet=True,
        )
    )

    assert result.success
    assert result.denormalized_edges_count == 2
    assert result.denormalized_nodes_count == 4

    with GraphDatabase(db_path) as db:
        e_cols = {r[0] for r in db.conn.execute("DESCRIBE denormalized_edges").fetchall()}
        assert {"subject_label", "subject_closure", "object_label", "object_closure"}.issubset(e_cols)

        n_cols = {r[0] for r in db.conn.execute("DESCRIBE denormalized_nodes").fetchall()}
        assert {"has_phenotype", "has_phenotype_label", "has_phenotype_closure",
                "has_descendant", "has_descendant_count"}.issubset(n_cols)


def test_closurize_evolves_stored_schema_to_four_classes(synthetic_kg, biolink_schemaview):
    db_path, closure_path = synthetic_kg

    with GraphDatabase(db_path) as db:
        seed_schema(
            db.conn,
            nodes_headers=["id", "category", "name", "in_taxon", "in_taxon_label"],
            edges_headers=["id", "subject", "predicate", "object", "category",
                           "has_evidence", "publications", "negated", "namespace"],
            biolink_schemaview=biolink_schemaview,
        )

    closurize_graph(
        ClosurizeConfig(
            database_path=db_path,
            closure_file=closure_path,
            node_fields=["has_phenotype"],
            edge_fields=["subject", "object"],
            quiet=True,
        )
    )

    with GraphDatabase(db_path) as db:
        schema = current_schema(db.conn)

    assert "Entity" in schema.classes
    assert "Association" in schema.classes
    assert "DenormalizedEntity" in schema.classes
    assert "DenormalizedAssociation" in schema.classes
    assert schema.classes["DenormalizedEntity"].is_a == "Entity"
    assert schema.classes["DenormalizedAssociation"].is_a == "Association"

    da_slots = set(schema.classes["DenormalizedAssociation"].slots)
    assert {"subject_label", "subject_closure", "object_label", "object_closure"}.issubset(da_slots)


def test_closurize_tolerates_unseeded_database(synthetic_kg):
    """If `_koza_schema` is absent (graphs from before the schema feature),
    closurize still produces the denormalized tables, it just skips the
    schema-evolution step. Matches the tolerant-ensure_slots contract."""
    db_path, closure_path = synthetic_kg

    result = closurize_graph(
        ClosurizeConfig(
            database_path=db_path,
            closure_file=closure_path,
            node_fields=["has_phenotype"],
            edge_fields=["subject", "object"],
            quiet=True,
        )
    )

    assert result.success
    with GraphDatabase(db_path) as db:
        tables = {r[0] for r in db.conn.execute("SHOW TABLES").fetchall()}
        assert "denormalized_edges" in tables
        assert "denormalized_nodes" in tables
        assert "_koza_schema" not in tables
