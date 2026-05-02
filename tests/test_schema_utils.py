"""
Tests for koza.graph_operations.schema_utils — multivalued field detection.
"""

from koza.graph_operations.schema_utils import (
    FORCE_MULTIVALUED_FIELDS,
    FORCE_SINGLE_VALUED_FIELDS,
    is_field_multivalued,
)


def test_force_single_valued_overrides_schema():
    # `category` is multivalued in Biolink Model but we treat it as single-valued
    assert "category" in FORCE_SINGLE_VALUED_FIELDS
    assert is_field_multivalued("category") is False


def test_force_multivalued_overrides_schema():
    # `subsets` is not defined in Biolink Model on named_thing/association,
    # so the schema lookup returns False. The override forces True.
    assert "subsets" in FORCE_MULTIVALUED_FIELDS
    assert is_field_multivalued("subsets") is True


def test_biolink_multivalued_field_detected():
    # Sanity check that schema-driven detection still works
    assert is_field_multivalued("xref") is True


def test_unknown_field_is_not_multivalued():
    assert is_field_multivalued("definitely_not_a_real_slot_xyz") is False
