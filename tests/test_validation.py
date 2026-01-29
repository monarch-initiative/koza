"""
Test suite for validation infrastructure.

This module tests the core validation dataclasses and engine for
declarative validation of KGX graph data against biolink model constraints.
"""

from enum import Enum
from unittest.mock import MagicMock

import pytest

from koza.graph_operations.validation import (
    ClassConstraints,
    ConstraintType,
    SlotConstraint,
    ValidationEngine,
    ValidationReport,
    ValidationViolation,
    ViolationSample,
)
from koza.graph_operations.utils import GraphDatabase
from koza.graph_operations.schema_utils import SchemaParser


class TestConstraintType:
    """Test ConstraintType enum."""

    def test_constraint_type_is_enum(self):
        """Test that ConstraintType is an Enum."""
        assert issubclass(ConstraintType, Enum)

    def test_constraint_type_required(self):
        """Test REQUIRED constraint type exists."""
        assert hasattr(ConstraintType, "REQUIRED")
        assert ConstraintType.REQUIRED.value is not None

    def test_constraint_type_recommended(self):
        """Test RECOMMENDED constraint type exists."""
        assert hasattr(ConstraintType, "RECOMMENDED")
        assert ConstraintType.RECOMMENDED.value is not None

    def test_constraint_type_pattern(self):
        """Test PATTERN constraint type exists."""
        assert hasattr(ConstraintType, "PATTERN")
        assert ConstraintType.PATTERN.value is not None

    def test_constraint_type_enum(self):
        """Test ENUM constraint type exists."""
        assert hasattr(ConstraintType, "ENUM")
        assert ConstraintType.ENUM.value is not None

    def test_constraint_type_minimum_value(self):
        """Test MINIMUM_VALUE constraint type exists."""
        assert hasattr(ConstraintType, "MINIMUM_VALUE")
        assert ConstraintType.MINIMUM_VALUE.value is not None

    def test_constraint_type_maximum_value(self):
        """Test MAXIMUM_VALUE constraint type exists."""
        assert hasattr(ConstraintType, "MAXIMUM_VALUE")
        assert ConstraintType.MAXIMUM_VALUE.value is not None

    def test_constraint_type_identifier(self):
        """Test IDENTIFIER constraint type exists."""
        assert hasattr(ConstraintType, "IDENTIFIER")
        assert ConstraintType.IDENTIFIER.value is not None

    def test_constraint_type_multivalued(self):
        """Test MULTIVALUED constraint type exists."""
        assert hasattr(ConstraintType, "MULTIVALUED")
        assert ConstraintType.MULTIVALUED.value is not None

    def test_constraint_type_range_class(self):
        """Test RANGE_CLASS constraint type exists."""
        assert hasattr(ConstraintType, "RANGE_CLASS")
        assert ConstraintType.RANGE_CLASS.value is not None

    def test_constraint_type_missing_column(self):
        """Test MISSING_COLUMN constraint type exists."""
        assert hasattr(ConstraintType, "MISSING_COLUMN")
        assert ConstraintType.MISSING_COLUMN.value is not None

    def test_constraint_type_id_prefix(self):
        """Test ID_PREFIX constraint type exists."""
        assert hasattr(ConstraintType, "ID_PREFIX")
        assert ConstraintType.ID_PREFIX.value is not None

    def test_constraint_type_invalid_subproperty(self):
        """Test INVALID_SUBPROPERTY constraint type exists."""
        assert hasattr(ConstraintType, "INVALID_SUBPROPERTY")
        assert ConstraintType.INVALID_SUBPROPERTY.value is not None


class TestSlotConstraint:
    """Test SlotConstraint dataclass."""

    def test_slot_constraint_creation(self):
        """Test creating a SlotConstraint with required fields."""
        constraint = SlotConstraint(
            slot_name="id",
            constraint_type=ConstraintType.REQUIRED,
            value=None,
            class_context="Gene",
        )
        assert constraint.slot_name == "id"
        assert constraint.constraint_type == ConstraintType.REQUIRED
        assert constraint.value is None
        assert constraint.class_context == "Gene"

    def test_slot_constraint_default_severity(self):
        """Test that SlotConstraint has default severity of 'error'."""
        constraint = SlotConstraint(
            slot_name="name",
            constraint_type=ConstraintType.RECOMMENDED,
            value=None,
            class_context="Gene",
        )
        assert constraint.severity == "error"

    def test_slot_constraint_default_description(self):
        """Test that SlotConstraint has default empty description."""
        constraint = SlotConstraint(
            slot_name="name",
            constraint_type=ConstraintType.RECOMMENDED,
            value=None,
            class_context="Gene",
        )
        assert constraint.description == ""

    def test_slot_constraint_with_custom_severity(self):
        """Test creating SlotConstraint with custom severity."""
        constraint = SlotConstraint(
            slot_name="name",
            constraint_type=ConstraintType.RECOMMENDED,
            value=None,
            class_context="Gene",
            severity="warning",
        )
        assert constraint.severity == "warning"

    def test_slot_constraint_with_description(self):
        """Test creating SlotConstraint with description."""
        constraint = SlotConstraint(
            slot_name="id",
            constraint_type=ConstraintType.PATTERN,
            value=r"^[A-Z]+:\d+$",
            class_context="Gene",
            description="ID must be a valid CURIE",
        )
        assert constraint.description == "ID must be a valid CURIE"

    def test_slot_constraint_with_value(self):
        """Test creating SlotConstraint with a constraint value."""
        constraint = SlotConstraint(
            slot_name="category",
            constraint_type=ConstraintType.ENUM,
            value=["biolink:Gene", "biolink:Disease"],
            class_context="NamedThing",
        )
        assert constraint.value == ["biolink:Gene", "biolink:Disease"]


class TestClassConstraints:
    """Test ClassConstraints dataclass."""

    def test_class_constraints_creation(self):
        """Test creating a ClassConstraints instance."""
        constraints = ClassConstraints(
            class_name="Gene",
            table_mapping="nodes",
            slots={},
        )
        assert constraints.class_name == "Gene"
        assert constraints.table_mapping == "nodes"
        assert constraints.slots == {}

    def test_class_constraints_with_slots(self):
        """Test ClassConstraints with slot constraints."""
        slot_constraint = SlotConstraint(
            slot_name="id",
            constraint_type=ConstraintType.REQUIRED,
            value=None,
            class_context="Gene",
        )
        constraints = ClassConstraints(
            class_name="Gene",
            table_mapping="nodes",
            slots={"id": [slot_constraint]},
        )
        assert "id" in constraints.slots
        assert len(constraints.slots["id"]) == 1
        assert constraints.slots["id"][0].constraint_type == ConstraintType.REQUIRED

    def test_class_constraints_multiple_slot_constraints(self):
        """Test ClassConstraints with multiple constraints per slot."""
        required_constraint = SlotConstraint(
            slot_name="id",
            constraint_type=ConstraintType.REQUIRED,
            value=None,
            class_context="Gene",
        )
        pattern_constraint = SlotConstraint(
            slot_name="id",
            constraint_type=ConstraintType.PATTERN,
            value=r"^HGNC:\d+$",
            class_context="Gene",
        )
        constraints = ClassConstraints(
            class_name="Gene",
            table_mapping="nodes",
            slots={"id": [required_constraint, pattern_constraint]},
        )
        assert len(constraints.slots["id"]) == 2


class TestViolationSample:
    """Test ViolationSample dataclass."""

    def test_violation_sample_creation(self):
        """Test creating a ViolationSample."""
        sample = ViolationSample(
            values=["invalid_id_1", "invalid_id_2"],
            count=2,
        )
        assert sample.values == ["invalid_id_1", "invalid_id_2"]
        assert sample.count == 2

    def test_violation_sample_empty_values(self):
        """Test ViolationSample with empty values list."""
        sample = ViolationSample(
            values=[],
            count=0,
        )
        assert sample.values == []
        assert sample.count == 0


class TestValidationViolation:
    """Test ValidationViolation dataclass."""

    def test_validation_violation_creation(self):
        """Test creating a ValidationViolation."""
        sample = ViolationSample(values=["bad_id"], count=1)
        violation = ValidationViolation(
            constraint_type=ConstraintType.REQUIRED,
            slot_name="id",
            table="nodes",
            severity="error",
            description="Missing required field 'id'",
            violation_count=100,
            total_records=1000,
            violation_percentage=10.0,
            samples=[sample],
        )
        assert violation.constraint_type == ConstraintType.REQUIRED
        assert violation.slot_name == "id"
        assert violation.table == "nodes"
        assert violation.severity == "error"
        assert violation.description == "Missing required field 'id'"
        assert violation.violation_count == 100
        assert violation.total_records == 1000
        assert violation.violation_percentage == 10.0
        assert len(violation.samples) == 1

    def test_validation_violation_empty_samples(self):
        """Test ValidationViolation with no samples."""
        violation = ValidationViolation(
            constraint_type=ConstraintType.PATTERN,
            slot_name="category",
            table="nodes",
            severity="warning",
            description="Category does not match pattern",
            violation_count=50,
            total_records=500,
            violation_percentage=10.0,
            samples=[],
        )
        assert violation.samples == []


class TestValidationReport:
    """Test ValidationReport dataclass."""

    def test_validation_report_creation(self):
        """Test creating a ValidationReport."""
        report = ValidationReport(
            violations=[],
            total_violations=0,
            error_count=0,
            warning_count=0,
            info_count=0,
            compliance_percentage=100.0,
            tables_validated=2,
            constraints_checked=10,
        )
        assert report.violations == []
        assert report.total_violations == 0
        assert report.error_count == 0
        assert report.warning_count == 0
        assert report.info_count == 0
        assert report.compliance_percentage == 100.0
        assert report.tables_validated == 2
        assert report.constraints_checked == 10

    def test_validation_report_with_violations(self):
        """Test ValidationReport with violations."""
        violation = ValidationViolation(
            constraint_type=ConstraintType.REQUIRED,
            slot_name="id",
            table="nodes",
            severity="error",
            description="Missing required field 'id'",
            violation_count=100,
            total_records=1000,
            violation_percentage=10.0,
            samples=[],
        )
        report = ValidationReport(
            violations=[violation],
            total_violations=100,
            error_count=100,
            warning_count=0,
            info_count=0,
            compliance_percentage=90.0,
            tables_validated=1,
            constraints_checked=5,
        )
        assert len(report.violations) == 1
        assert report.total_violations == 100
        assert report.error_count == 100


class TestValidationEngine:
    """Test ValidationEngine class."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock GraphDatabase."""
        mock_db = MagicMock(spec=GraphDatabase)
        return mock_db

    def test_validation_engine_creation(self, mock_database):
        """Test creating a ValidationEngine with database."""
        engine = ValidationEngine(database=mock_database)
        assert engine.database == mock_database

    def test_validation_engine_with_schema_parser(self, mock_database):
        """Test creating ValidationEngine with optional SchemaParser."""
        from koza.graph_operations.schema_utils import SchemaParser

        mock_parser = MagicMock(spec=SchemaParser)
        engine = ValidationEngine(database=mock_database, schema_parser=mock_parser)
        assert engine.schema_parser == mock_parser

    def test_validation_engine_validate_returns_report(self, mock_database):
        """Test that validate() returns a ValidationReport."""
        engine = ValidationEngine(database=mock_database)
        report = engine.validate()
        assert isinstance(report, ValidationReport)

    def test_validation_engine_validate_empty_report(self, mock_database):
        """Test that validate() returns an empty report initially."""
        engine = ValidationEngine(database=mock_database)
        report = engine.validate()
        assert report.total_violations == 0
        assert report.violations == []


class TestSchemaParserConstraintExtraction:
    """Test SchemaParser constraint extraction extensions."""

    @pytest.fixture
    def schema_parser(self):
        """Create a SchemaParser with the Biolink Model."""
        return SchemaParser()

    @pytest.fixture
    def schema_parser_no_schema(self):
        """Create a SchemaParser without a schema (schema_view is None)."""
        parser = SchemaParser()
        parser.schema_view = None
        return parser

    # Tests for get_class_constraints

    def test_get_class_constraints_returns_class_constraints(self, schema_parser):
        """Test that get_class_constraints returns a ClassConstraints object."""
        result = schema_parser.get_class_constraints("named thing", "nodes")
        assert isinstance(result, ClassConstraints)

    def test_get_class_constraints_has_correct_class_name(self, schema_parser):
        """Test that get_class_constraints sets the correct class_name."""
        result = schema_parser.get_class_constraints("named thing", "nodes")
        assert result.class_name == "named thing"

    def test_get_class_constraints_has_correct_table_mapping(self, schema_parser):
        """Test that get_class_constraints sets the correct table_mapping."""
        result = schema_parser.get_class_constraints("named thing", "nodes")
        assert result.table_mapping == "nodes"

    def test_get_class_constraints_with_no_schema_returns_empty(self, schema_parser_no_schema):
        """Test that get_class_constraints returns empty ClassConstraints when schema_view is None."""
        result = schema_parser_no_schema.get_class_constraints("named thing", "nodes")
        assert isinstance(result, ClassConstraints)
        assert result.class_name == "named thing"
        assert result.table_mapping == "nodes"
        assert result.slots == {}

    def test_get_class_constraints_has_slots_dict(self, schema_parser):
        """Test that get_class_constraints returns ClassConstraints with slots dict."""
        result = schema_parser.get_class_constraints("named thing", "nodes")
        assert isinstance(result.slots, dict)

    # Tests for get_node_constraints

    def test_get_node_constraints_returns_class_constraints(self, schema_parser):
        """Test that get_node_constraints returns a ClassConstraints object."""
        result = schema_parser.get_node_constraints()
        assert isinstance(result, ClassConstraints)

    def test_get_node_constraints_has_named_thing_class(self, schema_parser):
        """Test that get_node_constraints has class_name 'named thing'."""
        result = schema_parser.get_node_constraints()
        assert result.class_name == "named thing"

    def test_get_node_constraints_has_nodes_table_mapping(self, schema_parser):
        """Test that get_node_constraints has table_mapping 'nodes'."""
        result = schema_parser.get_node_constraints()
        assert result.table_mapping == "nodes"

    # Tests for get_edge_constraints

    def test_get_edge_constraints_returns_class_constraints(self, schema_parser):
        """Test that get_edge_constraints returns a ClassConstraints object."""
        result = schema_parser.get_edge_constraints()
        assert isinstance(result, ClassConstraints)

    def test_get_edge_constraints_has_association_class(self, schema_parser):
        """Test that get_edge_constraints has class_name 'association'."""
        result = schema_parser.get_edge_constraints()
        assert result.class_name == "association"

    def test_get_edge_constraints_has_edges_table_mapping(self, schema_parser):
        """Test that get_edge_constraints has table_mapping 'edges'."""
        result = schema_parser.get_edge_constraints()
        assert result.table_mapping == "edges"

    # Tests for get_valid_categories

    def test_get_valid_categories_returns_set(self, schema_parser):
        """Test that get_valid_categories returns a set."""
        result = schema_parser.get_valid_categories()
        assert isinstance(result, set)

    def test_get_valid_categories_contains_biolink_format(self, schema_parser):
        """Test that get_valid_categories returns categories in biolink:ClassName format."""
        result = schema_parser.get_valid_categories()
        # Should contain at least one category in biolink: format
        assert len(result) > 0
        # Check that categories have the biolink: prefix
        sample_category = next(iter(result))
        assert sample_category.startswith("biolink:")

    def test_get_valid_categories_contains_gene(self, schema_parser):
        """Test that get_valid_categories includes biolink:Gene."""
        result = schema_parser.get_valid_categories()
        assert "biolink:Gene" in result

    def test_get_valid_categories_empty_when_no_schema(self, schema_parser_no_schema):
        """Test that get_valid_categories returns empty set when schema_view is None."""
        result = schema_parser_no_schema.get_valid_categories()
        assert isinstance(result, set)
        assert len(result) == 0

    # Tests for get_valid_predicates

    def test_get_valid_predicates_returns_set(self, schema_parser):
        """Test that get_valid_predicates returns a set."""
        result = schema_parser.get_valid_predicates()
        assert isinstance(result, set)

    def test_get_valid_predicates_contains_biolink_format(self, schema_parser):
        """Test that get_valid_predicates returns predicates in biolink:predicate_name format."""
        result = schema_parser.get_valid_predicates()
        # Should contain at least one predicate in biolink: format
        assert len(result) > 0
        # Check that predicates have the biolink: prefix
        sample_predicate = next(iter(result))
        assert sample_predicate.startswith("biolink:")

    def test_get_valid_predicates_contains_related_to(self, schema_parser):
        """Test that get_valid_predicates includes biolink:related_to."""
        result = schema_parser.get_valid_predicates()
        assert "biolink:related_to" in result

    def test_get_valid_predicates_empty_when_no_schema(self, schema_parser_no_schema):
        """Test that get_valid_predicates returns empty set when schema_view is None."""
        result = schema_parser_no_schema.get_valid_predicates()
        assert isinstance(result, set)
        assert len(result) == 0

    # Tests for get_class_id_prefixes

    def test_get_class_id_prefixes_returns_tuple(self, schema_parser):
        """Test that get_class_id_prefixes returns a tuple."""
        result = schema_parser.get_class_id_prefixes("gene")
        assert isinstance(result, tuple)

    def test_get_class_id_prefixes_tuple_has_list_and_bool(self, schema_parser):
        """Test that get_class_id_prefixes returns (list, bool) tuple."""
        prefixes, is_closed = schema_parser.get_class_id_prefixes("gene")
        assert isinstance(prefixes, list)
        assert isinstance(is_closed, bool)

    def test_get_class_id_prefixes_empty_when_no_schema(self, schema_parser_no_schema):
        """Test that get_class_id_prefixes returns empty list when schema_view is None."""
        prefixes, is_closed = schema_parser_no_schema.get_class_id_prefixes("gene")
        assert prefixes == []
        assert is_closed is False

    # Tests for get_all_valid_predicates_with_hierarchy

    def test_get_all_valid_predicates_with_hierarchy_returns_set(self, schema_parser):
        """Test that get_all_valid_predicates_with_hierarchy returns a set."""
        result = schema_parser.get_all_valid_predicates_with_hierarchy()
        assert isinstance(result, set)

    def test_get_all_valid_predicates_with_hierarchy_contains_predicates(self, schema_parser):
        """Test that get_all_valid_predicates_with_hierarchy contains predicates."""
        result = schema_parser.get_all_valid_predicates_with_hierarchy()
        assert len(result) > 0

    def test_get_all_valid_predicates_with_hierarchy_empty_when_no_schema(self, schema_parser_no_schema):
        """Test that get_all_valid_predicates_with_hierarchy returns empty set when schema_view is None."""
        result = schema_parser_no_schema.get_all_valid_predicates_with_hierarchy()
        assert isinstance(result, set)
        assert len(result) == 0

    # Tests for slot constraint extraction (via get_class_constraints)

    def test_slot_constraints_have_correct_slot_names(self, schema_parser):
        """Test that extracted slot constraints have correct slot names with underscores."""
        result = schema_parser.get_class_constraints("named thing", "nodes")
        # Check that slot names use underscores (not spaces)
        for slot_name in result.slots.keys():
            assert " " not in slot_name

    def test_slot_constraints_have_constraint_type(self, schema_parser):
        """Test that extracted slot constraints have valid constraint types."""
        result = schema_parser.get_class_constraints("named thing", "nodes")
        for slot_name, constraints in result.slots.items():
            for constraint in constraints:
                assert isinstance(constraint, SlotConstraint)
                assert isinstance(constraint.constraint_type, ConstraintType)


if __name__ == "__main__":
    pytest.main([__file__])
