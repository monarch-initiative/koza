"""Tests for the annotation-information-content operation: information content
with annotated entities as the corpus (oaklib's `information-content
--use-associations`), written to a named table.

IC(t) = -log2(n(t) / N), where n(t) is the number of distinct annotated entities
with an annotation to t or any closure descendant of t, and N is the number of
distinct annotated entities. The fixture is small enough to check by hand.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from koza.graph_operations import compute_annotation_information_content
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import AnnotationInformationContentConfig

GENE_CAT = "biolink:GeneToPhenotypicFeatureAssociation"
GENOTYPE_CAT = "biolink:GenotypeToPhenotypicFeatureAssociation"

CLOSURE_SQL = """
    CREATE TABLE closure (subject_id VARCHAR, predicate_id VARCHAR, object_id VARCHAR);
    INSERT INTO closure VALUES
        -- HP:1 -> HP:0 -> HP:ROOT and HP:2 -> HP:OTHER -> HP:ROOT, reflexive
        ('HP:1', 'rdfs:subClassOf', 'HP:1'),
        ('HP:1', 'rdfs:subClassOf', 'HP:0'),
        ('HP:1', 'rdfs:subClassOf', 'HP:ROOT'),
        ('HP:0', 'rdfs:subClassOf', 'HP:0'),
        ('HP:0', 'rdfs:subClassOf', 'HP:ROOT'),
        ('HP:2', 'rdfs:subClassOf', 'HP:2'),
        ('HP:2', 'rdfs:subClassOf', 'HP:OTHER'),
        ('HP:2', 'rdfs:subClassOf', 'HP:ROOT'),
        ('HP:OTHER', 'rdfs:subClassOf', 'HP:OTHER'),
        ('HP:OTHER', 'rdfs:subClassOf', 'HP:ROOT'),
        ('HP:ROOT', 'rdfs:subClassOf', 'HP:ROOT'),
        ('MP:1', 'rdfs:subClassOf', 'MP:1'),
        -- a non-subClassOf row that must not count as ancestry
        ('HP:1', 'BFO:0000050', 'GO:1');
"""

EDGE_ROWS = [
    # GENE:1 -> HP:1, twice (two sources): must count once
    ("e1", "GENE:1", "HP:1", GENE_CAT, "False"),
    ("e2", "GENE:1", "HP:1", GENE_CAT, "False"),
    ("e3", "GENE:2", "HP:2", GENE_CAT, None),
    # negated: excluded unless include_negated
    ("e4", "GENE:3", "HP:1", GENE_CAT, "True"),
    # other subject prefix on the same object prefix (e.g. rat genes on MP)
    ("e5", "RAT:1", "HP:1", GENE_CAT, "False"),
    # same subject prefix, other category (e.g. MGI genotypes)
    ("e6", "GENE:9", "HP:2", GENOTYPE_CAT, "False"),
    # same subject, other object prefix
    ("e7", "GENE:4", "MP:1", GENE_CAT, "False"),
]


def _write_edges(conn, array_category: bool):
    cat_type = "VARCHAR[]" if array_category else "VARCHAR"
    conn.execute(f"""CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR,
                     object VARCHAR, category {cat_type}, negated VARCHAR)""")
    for eid, s, o, cat, neg in EDGE_ROWS:
        conn.execute(
            "INSERT INTO edges VALUES (?, ?, 'biolink:has_phenotype', ?, ?, ?)",
            [eid, s, o, [cat] if array_category else cat, neg],
        )


@pytest.fixture(params=[False, True], ids=["scalar-category", "array-category"])
def kg(tmp_path, request):
    db_path = tmp_path / "kg.duckdb"
    with GraphDatabase(db_path) as db:
        db.conn.execute(CLOSURE_SQL)
        _write_edges(db.conn, array_category=request.param)
    return db_path


def _config(db_path, **kw):
    base = dict(
        database_path=db_path,
        output_table="ic_gene_hp",
        association_categories=[GENE_CAT],
        subject_prefixes=["GENE"],
        object_prefixes=["HP"],
        quiet=True,
    )
    base.update(kw)
    return AnnotationInformationContentConfig(**base)


def _ic(db_path, table="ic_gene_hp"):
    with GraphDatabase(db_path) as db:
        return dict(db.conn.execute(f"SELECT term, ic FROM {table}").fetchall())


def test_ic_counts_distinct_annotated_entities(kg):
    result = compute_annotation_information_content(_config(kg))
    assert result.success
    # corpus: GENE:1 (HP:1, duplicated), GENE:2 (HP:2) -> N = 2
    assert result.entity_count == 2
    assert result.association_count == 2  # distinct (entity, term) pairs
    ic = _ic(kg)
    assert ic == pytest.approx({
        "HP:1": -math.log2(1 / 2),
        "HP:0": -math.log2(1 / 2),
        "HP:2": -math.log2(1 / 2),
        "HP:OTHER": -math.log2(1 / 2),
        "HP:ROOT": 0.0,  # both entities reach the root
    })
    assert result.term_count == 5
    assert "GO:1" not in ic  # non-subClassOf ancestry ignored


def test_include_negated(kg):
    result = compute_annotation_information_content(_config(kg, include_negated=True))
    assert result.entity_count == 3  # GENE:3 joins via its negated HP:1 edge
    ic = _ic(kg)
    assert ic["HP:1"] == pytest.approx(-math.log2(2 / 3))  # GENE:1, GENE:3
    assert ic["HP:2"] == pytest.approx(-math.log2(1 / 3))


def test_without_subject_prefix_filter_other_species_join(kg):
    result = compute_annotation_information_content(_config(kg, subject_prefixes=None))
    assert result.entity_count == 3  # RAT:1 now counted
    assert _ic(kg)["HP:1"] == pytest.approx(-math.log2(2 / 3))


def test_category_filter_excludes_genotypes(kg):
    result = compute_annotation_information_content(
        _config(kg, association_categories=[GENE_CAT, GENOTYPE_CAT]))
    assert result.entity_count == 3  # GENE:9 genotype edge now counted
    assert _ic(kg)["HP:2"] == pytest.approx(-math.log2(2 / 3))


def test_object_prefix_filter(kg):
    result = compute_annotation_information_content(_config(kg, object_prefixes=["MP"]))
    assert result.entity_count == 1  # GENE:4 -> MP:1
    assert _ic(kg) == pytest.approx({"MP:1": 0.0})


def test_idempotent_and_leaves_other_tables(kg):
    with GraphDatabase(kg) as db:
        db.conn.execute("CREATE TABLE information_content (term VARCHAR, ic DOUBLE)")
        db.conn.execute("INSERT INTO information_content VALUES ('HP:1', 9.9)")
    first = compute_annotation_information_content(_config(kg))
    second = compute_annotation_information_content(_config(kg))
    assert first.term_count == second.term_count
    assert _ic(kg, "information_content") == {"HP:1": 9.9}  # untouched


def test_rejects_unsafe_table_name(tmp_path):
    db_path = tmp_path / "x.duckdb"
    db_path.touch()
    with pytest.raises(ValidationError):
        _config(db_path, output_table="ic; DROP TABLE edges")


def test_missing_closure_fails(tmp_path):
    db_path = tmp_path / "no_closure.duckdb"
    with GraphDatabase(db_path) as db:
        _write_edges(db.conn, array_category=False)
    with pytest.raises(Exception, match="closure"):
        compute_annotation_information_content(_config(db_path))
