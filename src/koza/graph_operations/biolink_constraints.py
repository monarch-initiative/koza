"""Biolink edge-type constraints for graph validation.

From a Biolink ``SchemaView`` this builds the legal
``(subject_category, predicate, object_category)`` space two ways, to support a
tiered validation of a graph's edges:

* **Association-class constraints** — for each ``association`` descendant class
  whose ``slot_usage`` pins ``subject.range`` / ``predicate.subproperty_of`` /
  ``object.range``, the descendant-expanded sets of valid subject categories,
  predicates, and object categories, keyed by the association class. KGX edges
  that *assert* their association class (the edge ``category`` slot) are validated
  against **their** class specifically — catching an edge that claims to be a
  ``GeneRegulatesGeneAssociation`` but points at a Disease object, which the
  permissive union below would wave through.

* **Union triples** — the flattened union of every predicate's
  ``domain × range`` product and every association class's
  ``subject × predicate × object`` product. This is the **fallback** for edges
  that assert no constrained class — e.g. an edge whose only ``category`` is the
  root ``biolink:Association``, or a graph (such as monarch-kg) whose ``edges``
  carry no association ``category`` slot at all.

Coverage caveats (treat fallback verdicts as advisory, not authoritative):

* Only a few dozen association classes pin all three slots, so most edges that
  don't assert a constrained class get only the union check.
* Many Biolink predicates declare no ``domain``/``range``, so the union has real
  holes — a biologically reasonable triple can be absent and thus look "illegal."

Consumers join these against a graph's denormalized edges. Category columns may
be **scalar** (monarch-kg forces single-valued ``category``) or **list-valued**
(translator ingests keep ``category`` multivalued); the SQL that consumes this
must handle both — see the validation operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EdgeTypeConstraints:
    """The Biolink-derived legal edge-type space.

    ``*_by_class`` map an association class CURIE to its descendant-expanded set
    of valid subject categories / predicates / object categories. ``union_triples``
    is the flattened set of all legal ``(subject_category, predicate,
    object_category)`` triples for the fallback check.
    """

    subject_by_class: dict[str, set[str]] = field(default_factory=dict)
    predicate_by_class: dict[str, set[str]] = field(default_factory=dict)
    object_by_class: dict[str, set[str]] = field(default_factory=dict)
    union_triples: set[tuple[str, str, str]] = field(default_factory=set)

    def constrained_classes(self) -> set[str]:
        """Association classes that pin all three slots (eligible for the strict check)."""
        return set(self.subject_by_class)

    def subject_rows(self) -> list[tuple[str, str]]:
        """``(association_class, subject_category)`` long-form rows."""
        return [(c, s) for c, vals in self.subject_by_class.items() for s in vals]

    def predicate_rows(self) -> list[tuple[str, str]]:
        """``(association_class, predicate)`` long-form rows."""
        return [(c, p) for c, vals in self.predicate_by_class.items() for p in vals]

    def object_rows(self) -> list[tuple[str, str]]:
        """``(association_class, object_category)`` long-form rows."""
        return [(c, o) for c, vals in self.object_by_class.items() for o in vals]

    def union_rows(self) -> list[tuple[str, str, str]]:
        """``(subject_category, predicate, object_category)`` long-form rows."""
        return list(self.union_triples)


def _has_full_slot_usage(slot_usage) -> bool:
    """True if an association class pins subject.range, predicate.subproperty_of,
    and object.range — the minimum to derive a constraint."""
    if not slot_usage:
        return False
    for key in ("subject", "predicate", "object"):
        if key not in slot_usage or slot_usage[key] is None:
            return False
    return (
        slot_usage["subject"].range is not None
        and slot_usage["predicate"].subproperty_of is not None
        and slot_usage["object"].range is not None
    )


def build_edge_type_constraints(sv) -> EdgeTypeConstraints:
    """Build :class:`EdgeTypeConstraints` from a Biolink ``SchemaView``.

    Mirrors the matrix-validator legal-edge-type generator (predicate
    domain×range product unioned with association-class slot_usage product), but
    additionally **keeps the per-association-class constraints** so edges that
    assert their class can be checked against that class specifically. Built from
    the graph's own pinned Biolink version (avoids skew with a checked-in table).
    """
    uri = sv.get_uri
    constraints = EdgeTypeConstraints()

    # Association-class constraints (and their contribution to the union).
    for class_name in sv.class_descendants("association"):
        slot_usage = sv.get_class(class_name).slot_usage
        if not _has_full_slot_usage(slot_usage):
            continue
        cls = uri(class_name)
        subjects = {uri(c) for c in sv.class_descendants(slot_usage["subject"].range)}
        predicates = {uri(p) for p in sv.slot_descendants(slot_usage["predicate"].subproperty_of)}
        objects = {uri(c) for c in sv.class_descendants(slot_usage["object"].range)}
        constraints.subject_by_class[cls] = subjects
        constraints.predicate_by_class[cls] = predicates
        constraints.object_by_class[cls] = objects
        for s in subjects:
            for p in predicates:
                for o in objects:
                    constraints.union_triples.add((s, p, o))

    # Predicate domain × range product (every related_to descendant that pins both).
    for predicate_name in sv.slot_descendants("related to"):
        slot = sv.get_slot(predicate_name)
        if not slot or slot.domain is None or slot.range is None:
            continue
        predicate = uri(predicate_name)
        subjects = [uri(c) for c in sv.class_descendants(slot.domain)]
        objects = [uri(c) for c in sv.class_descendants(slot.range)]
        for s in subjects:
            for o in objects:
                constraints.union_triples.add((s, predicate, o))

    return constraints
