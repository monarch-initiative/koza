"""Tests for the Biolink edge-type constraint generator.

Asserted-class precision is the point: an edge claiming a specific association
class is validated against THAT class's domain/range, which the permissive union
can't do. These assertions pin that behavior against the pinned Biolink model.
"""

from __future__ import annotations

import pytest

from koza.graph_operations.biolink_constraints import (
    EdgeTypeConstraints,
    build_category_rollup,
    build_edge_type_constraints,
)
from koza.graph_operations.graph_schema import load_biolink_schemaview


@pytest.fixture(scope="module")
def constraints() -> EdgeTypeConstraints:
    return build_edge_type_constraints(load_biolink_schemaview())


def test_gene_regulates_gene_association_constraints(constraints):
    """The asserted-class check that the union can't do: GeneRegulatesGene admits
    a Gene subject but NOT a Disease object."""
    cls = "biolink:GeneRegulatesGeneAssociation"
    assert cls in constraints.constrained_classes()
    assert "biolink:Gene" in constraints.subject_by_class[cls]
    assert "biolink:Disease" not in constraints.object_by_class[cls]
    assert "biolink:regulates" in constraints.predicate_by_class[cls]


def test_constraint_sets_are_descendant_expanded(constraints):
    """Ranges are expanded to descendants, not just the declared class."""
    cls = "biolink:GeneRegulatesGeneAssociation"
    # gene-or-gene-product range pulls in several concrete subclasses
    assert len(constraints.subject_by_class[cls]) > 1


def test_union_triples_populated_and_curie_formatted(constraints):
    """The fallback union is non-empty and uses biolink: CURIEs."""
    assert len(constraints.union_triples) > 100_000
    s, p, o = next(iter(constraints.union_triples))
    assert s.startswith("biolink:") and p.startswith("biolink:") and o.startswith("biolink:")


def test_long_form_rows_round_trip(constraints):
    """Long-form row helpers match the per-class set sizes (for DuckDB loading)."""
    cls = "biolink:GeneRegulatesGeneAssociation"
    subj_rows = [r for r in constraints.subject_rows() if r[0] == cls]
    assert len(subj_rows) == len(constraints.subject_by_class[cls])
    assert len(constraints.union_rows()) == len(constraints.union_triples)


def test_category_rollup_collapses_to_high_priority():
    """Concrete subclasses collapse to their high-priority class; unrelated ones
    map to themselves at consume time (absent from the map)."""
    rollup = build_category_rollup(load_biolink_schemaview())
    assert rollup.get("biolink:Protein") == "biolink:GeneOrGeneProduct"
    assert rollup.get("biolink:Disease") == "biolink:DiseaseOrPhenotypicFeature"
    # the high-priority classes map to themselves
    assert rollup.get("biolink:ChemicalEntity") == "biolink:ChemicalEntity"
    # something outside the three high-priority families isn't in the map
    assert "biolink:Publication" not in rollup
