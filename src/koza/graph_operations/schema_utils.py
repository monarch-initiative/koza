"""
Utilities for parsing LinkML schemas to identify multivalued fields.
Supports KGX format and Biolink Model schema definitions.
"""

import importlib.resources as ir
from typing import Optional, Set

from loguru import logger


class SchemaParser:
    """Parser for LinkML schemas to identify multivalued fields using SchemaView."""

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the schema parser.

        Args:
            schema_path: Path to LinkML YAML schema file. If None, uses the
                Biolink Model bundled with the `biolink-model` python package
                (pinned via pyproject.toml, no runtime fetch).
        """
        self.schema_path = schema_path
        self.schema_view = None

        try:
            from linkml_runtime.utils.schemaview import SchemaView

            if schema_path:
                self.schema_view = SchemaView(schema_path)
            else:
                with ir.as_file(
                    ir.files("biolink_model.schema") / "biolink_model.yaml"
                ) as p:
                    self.schema_view = SchemaView(str(p))
        except Exception as e:
            logger.debug(f"Could not load schema: {e}")
            self.schema_view = None

    def is_field_multivalued(self, field_name: str) -> bool:
        """
        Check if a field is defined as multivalued in the schema.

        Args:
            field_name: Field/slot name to check

        Returns:
            True if field is multivalued, False otherwise
        """
        if not self.schema_view:
            return False

        # Biolink uses spaces in slot names, convert underscores
        slot_name = field_name.replace("_", " ")

        # Try induced_slot with different class contexts
        # (association for edge properties, named thing for node properties)
        for class_name in ["association", "named thing"]:
            try:
                slot = self.schema_view.induced_slot(slot_name, class_name)
                if slot:
                    return slot.multivalued
            except Exception:
                continue

        # If not found in any class context, assume not multivalued
        return False

    def get_multivalued_fields_from_list(self, field_names: list[str]) -> Set[str]:
        """
        Filter a list of field names to only those that are multivalued.

        Args:
            field_names: List of field names to check

        Returns:
            Set of field names that are multivalued
        """
        return {field for field in field_names if self.is_field_multivalued(field)}


# koza preserves Biolink slot definitions by default. Collapsing a
# Biolink-multivalued slot to a scalar is opt-in per call via the
# `force_single_valued` argument; koza intentionally ships no built-in set of
# fields to collapse, so it carries no downstream-specific policy. Consumers
# that want a particular convention (e.g. monarch-app's scalar category /
# in_taxon / type) pass their own list.

# Global schema parser instance (lazy loaded)
_global_schema_parser: Optional[SchemaParser] = None


def get_schema_parser(schema_path: Optional[str] = None) -> SchemaParser:
    """
    Get a global schema parser instance (cached for performance).

    Args:
        schema_path: Path to schema file (if different from cached instance)

    Returns:
        SchemaParser instance
    """
    global _global_schema_parser

    if _global_schema_parser is None or (schema_path and schema_path != _global_schema_parser.schema_path):
        _global_schema_parser = SchemaParser(schema_path)

    return _global_schema_parser


def is_field_multivalued(
    field_name: str,
    schema_path: Optional[str] = None,
    force_single_valued: Optional[Set[str]] = None,
) -> bool:
    """
    Check if a field is multivalued, using schema if available or fallback list.

    Args:
        field_name: Field name to check
        schema_path: Optional schema path (uses cached parser if None)
        force_single_valued: Slot names the caller has explicitly opted into
            single-valued collapse. A field in this set is reported
            single-valued regardless of its Biolink definition. Default: none —
            Biolink slot definitions are preserved.

    Returns:
        True if field is multivalued, False otherwise
    """
    # Honor caller-requested single-valued overrides only.
    if force_single_valued and field_name in force_single_valued:
        return False

    parser = get_schema_parser(schema_path)
    if parser.schema_view:
        return parser.is_field_multivalued(field_name)

    return False


def get_multivalued_columns(
    column_names: list[str],
    schema_path: Optional[str] = None,
    force_single_valued: Optional[Set[str]] = None,
) -> Set[str]:
    """
    Identify which columns from a list are multivalued.

    Args:
        column_names: List of column names to check
        schema_path: Optional schema path
        force_single_valued: Slot names explicitly opted into single-valued
            collapse (excluded from the multivalued result).

    Returns:
        Set of column names that are multivalued
    """
    multivalued = set()

    for col in column_names:
        if is_field_multivalued(col, schema_path, force_single_valued):
            multivalued.add(col)

    return multivalued
