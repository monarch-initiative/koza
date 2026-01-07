"""
Utilities for parsing LinkML schemas to identify multivalued fields.
Supports KGX format and Biolink Model schema definitions.
"""

from typing import Optional, Set

from loguru import logger


class SchemaParser:
    """Parser for LinkML schemas to identify multivalued fields using SchemaView."""

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the schema parser.

        Args:
            schema_path: Path to LinkML YAML schema file. If None, uses latest Biolink Model.
        """
        self.schema_path = schema_path
        self.schema_view = None

        try:
            from linkml_runtime.utils.schemaview import SchemaView

            if schema_path:
                self.schema_view = SchemaView(schema_path)
            else:
                # Default to latest Biolink Model
                self.schema_view = SchemaView(
                    "https://raw.githubusercontent.com/biolink/biolink-model/master/biolink-model.yaml"
                )
        except Exception as e:
            logger.debug(f"Could not load schema: {e}")
            self.schema_view = None

    def is_field_multivalued(self, field_name: str) -> bool:
        """
        Check if a field is defined as multivalued in the schema.
        Uses induced_slot to get the base slot definition.

        Args:
            field_name: Field/slot name to check

        Returns:
            True if field is multivalued, False otherwise
        """
        if not self.schema_view:
            return False

        try:
            # Use induced_slot to get the complete slot definition
            slot = self.schema_view.induced_slot(field_name)
            return slot.multivalued if slot else False
        except Exception:
            # If slot doesn't exist or other error, assume not multivalued
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


# Known multivalued fields for KGX format (fallback when schema unavailable)
KGX_MULTIVALUED_FIELDS: Set[str] = {
    # Node properties
    "category",
    "type",
    "xref",
    "synonym",
    "in_taxon",
    "in_taxon_label",
    "provided_by",
    "publications",
    "same_as",
    # Edge properties
    "qualifiers",
    "knowledge_source",
    "aggregator_knowledge_source",
    "primary_knowledge_source",
    "supporting_data_source",
    "has_evidence",
    "supporting_studies",
    "supporting_study_method_types",
    "publications_from_studies",
    # Additional common multivalued fields
    "xrefs",
    "synonyms",
    "categories",
    "types",
}


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


def is_field_multivalued(field_name: str, schema_path: Optional[str] = None) -> bool:
    """
    Check if a field is multivalued, using schema if available or fallback list.

    Args:
        field_name: Field name to check
        schema_path: Optional schema path (uses cached parser if None)

    Returns:
        True if field is multivalued, False otherwise
    """
    # First check the fallback list (fast path for known fields)
    if field_name in KGX_MULTIVALUED_FIELDS:
        return True

    # Then check the schema if available
    parser = get_schema_parser(schema_path)
    return parser.is_field_multivalued(field_name)


def get_multivalued_columns(column_names: list[str], schema_path: Optional[str] = None) -> Set[str]:
    """
    Identify which columns from a list are multivalued.

    Args:
        column_names: List of column names to check
        schema_path: Optional schema path

    Returns:
        Set of column names that are multivalued
    """
    multivalued = set()

    for col in column_names:
        if is_field_multivalued(col, schema_path):
            multivalued.add(col)

    return multivalued
