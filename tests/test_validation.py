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


if __name__ == "__main__":
    pytest.main([__file__])
