"""Tests for the information-content operation — computes the `information_content`
and `closure_size` precompute tables for an already-closurized graph database.

The fixture writes the `closure` and `edges` tables directly (the shape
`closurize` produces) so the math is hand-checkable.
"""

from __future__ import annotations

import math

import pytest

from koza.graph_operations import compute_information_content
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import InformationContentConfig


@pytest.fixture
def closurized_kg(tmp_path):
    """A tiny closurized graph: a reflexive rdfs:subClassOf closure over five
    HP terms (two small chains under a shared root), one non-subClassOf closure
    row that must be ignored, and three has_phenotype associations (one negated,
    one in a non-matching category)."""
    db_path = tmp_path / "kg.duckdb"
    with GraphDatabase(db_path) as db:
        db.conn.execute("""
            CREATE TABLE closure (subject_id VARCHAR, predicate_id VARCHAR, object_id VARCHAR);
            INSERT INTO closure VALUES
                -- chain: HP:1 -> HP:0 -> HP:ROOT (reflexive)
                ('HP:1', 'rdfs:subClassOf', 'HP:1'),
                ('HP:1', 'rdfs:subClassOf', 'HP:0'),
                ('HP:1', 'rdfs:subClassOf', 'HP:ROOT'),
                ('HP:0', 'rdfs:subClassOf', 'HP:0'),
                ('HP:0', 'rdfs:subClassOf', 'HP:ROOT'),
                -- chain: HP:2 -> HP:OTHER -> HP:ROOT (reflexive)
                ('HP:2', 'rdfs:subClassOf', 'HP:2'),
                ('HP:2', 'rdfs:subClassOf', 'HP:OTHER'),
                ('HP:2', 'rdfs:subClassOf', 'HP:ROOT'),
                ('HP:OTHER', 'rdfs:subClassOf', 'HP:OTHER'),
                ('HP:OTHER', 'rdfs:subClassOf', 'HP:ROOT'),
                ('HP:ROOT', 'rdfs:subClassOf', 'HP:ROOT'),
                -- a non-subClassOf row that must be excluded from IC
                ('HP:1', 'biolink:part_of', 'GO:1');
        """)
        db.conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR,
                                category VARCHAR, negated BOOLEAN);
            INSERT INTO edges VALUES
                ('e1', 'GENE:1', 'biolink:has_phenotype', 'HP:1',
                 'biolink:GeneToPhenotypicFeatureAssociation', false),
                -- negated: excluded unless include_negated
                ('e2', 'GENE:1', 'biolink:has_phenotype', 'HP:2',
                 'biolink:GeneToPhenotypicFeatureAssociation', true),
                ('e3', 'DISEASE:1', 'biolink:has_phenotype', 'HP:0',
                 'biolink:DiseaseToPhenotypicFeatureAssociation', false),
                -- non-matching category: always excluded
                ('e4', 'GENE:2', 'biolink:has_phenotype', 'HP:1',
                 'biolink:GeneToGeneAssociation', false);
        """)
    return db_path


def test_information_content_matches_ic_formula(closurized_kg):
    result = compute_information_content(InformationContentConfig(database_path=closurized_kg, quiet=True))
    assert result.success
    # N = 5 distinct subClassOf objects (GO:1 is part_of, excluded).
    assert result.ic_term_count == 5

    with GraphDatabase(closurized_kg) as db:
        ic = dict(db.conn.execute("SELECT term, ic FROM information_content").fetchall())

    # freq(term) / N, N = 5
    assert ic["HP:1"] == pytest.approx(-math.log2(1 / 5))
    assert ic["HP:0"] == pytest.approx(-math.log2(2 / 5))
    assert ic["HP:OTHER"] == pytest.approx(-math.log2(2 / 5))
    assert ic["HP:ROOT"] == pytest.approx(0.0)  # root appears under every term
    assert "GO:1" not in ic  # the part_of object must not leak in


def test_closure_size_excludes_negated_and_other_categories(closurized_kg):
    result = compute_information_content(InformationContentConfig(database_path=closurized_kg, quiet=True))
    assert result.success
    # GENE:1 (HP:1 only) and DISEASE:1 (HP:0); GENE:2 dropped (category),
    # GENE:1's HP:2 dropped (negated).
    assert result.closure_size_entity_count == 2

    with GraphDatabase(closurized_kg) as db:
        size = dict(db.conn.execute("SELECT entity, size FROM closure_size").fetchall())

    assert size == {"GENE:1": 3, "DISEASE:1": 2}  # {HP:1,HP:0,HP:ROOT} / {HP:0,HP:ROOT}


def test_closure_size_include_negated(closurized_kg):
    compute_information_content(
        InformationContentConfig(database_path=closurized_kg, include_negated=True, quiet=True)
    )
    with GraphDatabase(closurized_kg) as db:
        size = dict(db.conn.execute("SELECT entity, size FROM closure_size").fetchall())

    # GENE:1 now also gets HP:2 -> adds {HP:2, HP:OTHER}: union is all five terms.
    assert size["GENE:1"] == 5
    assert size["DISEASE:1"] == 2


def test_information_content_is_idempotent(closurized_kg):
    """CREATE OR REPLACE means re-running just rebuilds the tables."""
    first = compute_information_content(InformationContentConfig(database_path=closurized_kg, quiet=True))
    second = compute_information_content(InformationContentConfig(database_path=closurized_kg, quiet=True))
    assert first.ic_term_count == second.ic_term_count
    assert first.closure_size_entity_count == second.closure_size_entity_count

    with GraphDatabase(closurized_kg) as db:
        tables = {r[0] for r in db.conn.execute("SHOW TABLES").fetchall()}
    assert {"information_content", "closure_size"}.issubset(tables)


def test_information_content_custom_closure_predicate(closurized_kg):
    """With only the part_of predicate selected, IC is built from the single
    GO:1 row (N = 1) and no subClassOf terms appear."""
    result = compute_information_content(
        InformationContentConfig(
            database_path=closurized_kg, closure_predicates=["biolink:part_of"], quiet=True
        )
    )
    assert result.ic_term_count == 1
    with GraphDatabase(closurized_kg) as db:
        terms = {r[0] for r in db.conn.execute("SELECT term FROM information_content").fetchall()}
    assert terms == {"GO:1"}
