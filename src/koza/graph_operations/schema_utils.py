"""
Utilities for parsing LinkML schemas to identify multivalued fields.
Supports KGX format and Biolink Model schema definitions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Set, Tuple

from loguru import logger

if TYPE_CHECKING:
    from .validation import ClassConstraints, SlotConstraint


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

    def get_class_constraints(self, class_name: str, table_mapping: str) -> ClassConstraints:
        """
        Get all constraints for a specific class.

        Args:
            class_name: Name of the class (e.g., "named thing", "association")
            table_mapping: Which table this class maps to ("nodes" or "edges")

        Returns:
            ClassConstraints object with all extracted constraints
        """
        # Import here to avoid circular import
        from .validation import ClassConstraints, SlotConstraint

        if not self.schema_view:
            return ClassConstraints(
                class_name=class_name,
                table_mapping=table_mapping,
                slots={},
            )

        slots_dict: dict[str, list[SlotConstraint]] = {}

        try:
            induced_slots = self.schema_view.class_induced_slots(class_name)
            for slot in induced_slots:
                constraints = self._extract_slot_constraints(slot, class_name)
                if constraints:
                    # Convert slot name spaces to underscores
                    slot_name = slot.name.replace(" ", "_")
                    slots_dict[slot_name] = constraints
        except Exception as e:
            logger.debug(f"Could not get induced slots for {class_name}: {e}")

        return ClassConstraints(
            class_name=class_name,
            table_mapping=table_mapping,
            slots=slots_dict,
        )

    def _extract_slot_constraints(self, slot, class_name: str) -> list[SlotConstraint]:
        """
        Extract constraints from a slot definition.

        Args:
            slot: Slot definition from LinkML schema
            class_name: Class context for the slot

        Returns:
            List of SlotConstraint objects
        """
        # Import here to avoid circular import
        from .validation import ConstraintType, SlotConstraint

        constraints = []
        slot_name = slot.name.replace(" ", "_")

        # Required constraint
        if getattr(slot, "required", False):
            constraints.append(
                SlotConstraint(
                    slot_name=slot_name,
                    constraint_type=ConstraintType.REQUIRED,
                    value=True,
                    class_context=class_name,
                    severity="error",
                    description=f"Field '{slot_name}' is required",
                )
            )

        # Recommended constraint
        if getattr(slot, "recommended", False):
            constraints.append(
                SlotConstraint(
                    slot_name=slot_name,
                    constraint_type=ConstraintType.RECOMMENDED,
                    value=True,
                    class_context=class_name,
                    severity="warning",
                    description=f"Field '{slot_name}' is recommended",
                )
            )

        # Pattern constraint
        pattern = getattr(slot, "pattern", None)
        if pattern:
            constraints.append(
                SlotConstraint(
                    slot_name=slot_name,
                    constraint_type=ConstraintType.PATTERN,
                    value=pattern,
                    class_context=class_name,
                    severity="error",
                    description=f"Field '{slot_name}' must match pattern: {pattern}",
                )
            )

        # Enum constraint (check if range is an enum)
        slot_range = getattr(slot, "range", None)
        if slot_range and self.schema_view:
            try:
                enum_def = self.schema_view.get_enum(slot_range)
                if enum_def and hasattr(enum_def, "permissible_values"):
                    enum_values = list(enum_def.permissible_values.keys())
                    constraints.append(
                        SlotConstraint(
                            slot_name=slot_name,
                            constraint_type=ConstraintType.ENUM,
                            value=enum_values,
                            class_context=class_name,
                            severity="warning",
                            description=f"Field '{slot_name}' must be one of: {enum_values}",
                        )
                    )
            except Exception:
                pass

        # Minimum value constraint
        minimum_value = getattr(slot, "minimum_value", None)
        if minimum_value is not None:
            constraints.append(
                SlotConstraint(
                    slot_name=slot_name,
                    constraint_type=ConstraintType.MINIMUM_VALUE,
                    value=minimum_value,
                    class_context=class_name,
                    severity="error",
                    description=f"Field '{slot_name}' must be >= {minimum_value}",
                )
            )

        # Maximum value constraint
        maximum_value = getattr(slot, "maximum_value", None)
        if maximum_value is not None:
            constraints.append(
                SlotConstraint(
                    slot_name=slot_name,
                    constraint_type=ConstraintType.MAXIMUM_VALUE,
                    value=maximum_value,
                    class_context=class_name,
                    severity="error",
                    description=f"Field '{slot_name}' must be <= {maximum_value}",
                )
            )

        # Identifier constraint
        if getattr(slot, "identifier", False):
            constraints.append(
                SlotConstraint(
                    slot_name=slot_name,
                    constraint_type=ConstraintType.IDENTIFIER,
                    value=True,
                    class_context=class_name,
                    severity="error",
                    description=f"Field '{slot_name}' is the identifier",
                )
            )

        # Multivalued constraint
        if getattr(slot, "multivalued", False):
            constraints.append(
                SlotConstraint(
                    slot_name=slot_name,
                    constraint_type=ConstraintType.MULTIVALUED,
                    value=True,
                    class_context=class_name,
                    severity="info",
                    description=f"Field '{slot_name}' is multivalued",
                )
            )

        return constraints

    def get_node_constraints(self) -> ClassConstraints:
        """
        Get constraints for the "named thing" class, mapped to the "nodes" table.

        Returns:
            ClassConstraints for nodes
        """
        return self.get_class_constraints("named thing", "nodes")

    def get_edge_constraints(self) -> ClassConstraints:
        """
        Get constraints for the "association" class, mapped to the "edges" table.

        Returns:
            ClassConstraints for edges
        """
        return self.get_class_constraints("association", "edges")

    def get_valid_categories(self) -> Set[str]:
        """
        Get all valid biolink categories (descendants of NamedThing).

        Returns:
            Set of category names in biolink:ClassName format
        """
        if not self.schema_view:
            return set()

        categories = set()
        try:
            # Get all descendants of NamedThing
            descendants = self.schema_view.class_descendants("named thing")
            for class_name in descendants:
                # Convert to CamelCase and add biolink prefix
                camel_case = "".join(word.capitalize() for word in class_name.split())
                categories.add(f"biolink:{camel_case}")
        except Exception as e:
            logger.debug(f"Could not get valid categories: {e}")

        return categories

    def get_valid_predicates(self) -> Set[str]:
        """
        Get all valid biolink predicates.

        Returns:
            Set of predicate names in biolink:predicate_name format
        """
        if not self.schema_view:
            return set()

        predicates = set()
        try:
            # Get the slot for "related to" which is the root predicate
            root_slot = self.schema_view.get_slot("related to")
            if root_slot:
                predicates.add("biolink:related_to")

            # Get all slots and filter for those that are predicates
            all_slots = self.schema_view.all_slots()
            for slot_name, slot_def in all_slots.items():
                # Check if slot is a subproperty of related_to or has is_a relationship
                if hasattr(slot_def, "is_a") and slot_def.is_a:
                    # Convert to snake_case format
                    predicate_name = slot_name.replace(" ", "_")
                    predicates.add(f"biolink:{predicate_name}")
        except Exception as e:
            logger.debug(f"Could not get valid predicates: {e}")

        return predicates

    def get_class_id_prefixes(self, class_name: str) -> Tuple[List[str], bool]:
        """
        Get the valid ID prefixes for a class.

        Args:
            class_name: Name of the class

        Returns:
            Tuple of (list of valid prefixes, is_closed flag)
        """
        if not self.schema_view:
            return ([], False)

        try:
            class_def = self.schema_view.get_class(class_name)
            if class_def:
                prefixes = getattr(class_def, "id_prefixes", []) or []
                is_closed = getattr(class_def, "id_prefixes_are_closed", False) or False
                return (list(prefixes), bool(is_closed))
        except Exception as e:
            logger.debug(f"Could not get ID prefixes for {class_name}: {e}")

        return ([], False)

    def get_all_valid_predicates_with_hierarchy(self) -> Set[str]:
        """
        Get all valid predicates including the full hierarchy.

        Returns:
            Set of all valid predicate names in biolink:predicate_name format
        """
        if not self.schema_view:
            return set()

        predicates = set()
        try:
            # Get all slots
            all_slots = self.schema_view.all_slots()
            for slot_name, slot_def in all_slots.items():
                # Include all slots that could be predicates (have is_a or are the root)
                predicate_name = slot_name.replace(" ", "_")
                predicates.add(f"biolink:{predicate_name}")
        except Exception as e:
            logger.debug(f"Could not get all valid predicates: {e}")

        return predicates


# Fields that should be treated as single-valued regardless of schema definition
# (e.g., category, in_taxon, and type are multivalued in biolink but we treat them as single-valued)
FORCE_SINGLE_VALUED_FIELDS: Set[str] = {
    "category",
    "in_taxon",
    "type",
}

# Fallback multivalued fields for KGX format (used only when schema unavailable)
KGX_MULTIVALUED_FIELDS_FALLBACK: Set[str] = {
    # Node properties
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
    # Check if field is forced to be single-valued
    if field_name in FORCE_SINGLE_VALUED_FIELDS:
        return False

    # Try to get from schema first
    parser = get_schema_parser(schema_path)
    if parser.schema_view:
        return parser.is_field_multivalued(field_name)

    # Fall back to hardcoded list only if schema unavailable
    return field_name in KGX_MULTIVALUED_FIELDS_FALLBACK


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
