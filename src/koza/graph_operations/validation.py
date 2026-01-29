"""
Validation infrastructure for declarative validation of KGX graph data.

This module provides the core dataclasses and engine for validating
graph data against biolink model constraints and custom validation rules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .utils import GraphDatabase


class ConstraintType(Enum):
    """Types of validation constraints that can be applied to slots."""

    REQUIRED = "required"
    RECOMMENDED = "recommended"
    PATTERN = "pattern"
    ENUM = "enum"
    MINIMUM_VALUE = "minimum_value"
    MAXIMUM_VALUE = "maximum_value"
    IDENTIFIER = "identifier"
    MULTIVALUED = "multivalued"
    RANGE_CLASS = "range_class"
    MISSING_COLUMN = "missing_column"
    ID_PREFIX = "id_prefix"
    INVALID_SUBPROPERTY = "invalid_subproperty"


@dataclass
class SlotConstraint:
    """
    A constraint applied to a slot within a class context.

    Attributes:
        slot_name: Name of the slot being constrained
        constraint_type: Type of constraint to apply
        value: Value for the constraint (e.g., pattern regex, enum list)
        class_context: Class this constraint applies to
        severity: Severity level ('error', 'warning', 'info')
        description: Human-readable description of the constraint
    """

    slot_name: str
    constraint_type: ConstraintType
    value: Any
    class_context: str
    severity: str = "error"
    description: str = ""


@dataclass
class ClassConstraints:
    """
    Collection of constraints for a specific class.

    Attributes:
        class_name: Name of the class
        table_mapping: Which table this class maps to ('nodes' or 'edges')
        slots: Dictionary mapping slot names to their constraints
    """

    class_name: str
    table_mapping: str
    slots: dict[str, list[SlotConstraint]] = field(default_factory=dict)


@dataclass
class ViolationSample:
    """
    Sample of values that violate a constraint.

    Attributes:
        values: List of sample values that violated the constraint
        count: Number of values in this sample
    """

    values: list
    count: int


@dataclass
class ValidationViolation:
    """
    A single validation violation found during validation.

    Attributes:
        constraint_type: Type of constraint that was violated
        slot_name: Name of the slot with the violation
        table: Table where the violation occurred
        severity: Severity level of the violation
        description: Human-readable description of the violation
        violation_count: Number of records with this violation
        total_records: Total records checked
        violation_percentage: Percentage of records with this violation
        samples: Sample values illustrating the violation
    """

    constraint_type: ConstraintType
    slot_name: str
    table: str
    severity: str
    description: str
    violation_count: int
    total_records: int
    violation_percentage: float
    samples: list[ViolationSample] = field(default_factory=list)


@dataclass
class ValidationReport:
    """
    Complete validation report containing all violations and statistics.

    Attributes:
        violations: List of all validation violations found
        total_violations: Total count of all violations
        error_count: Number of error-severity violations
        warning_count: Number of warning-severity violations
        info_count: Number of info-severity violations
        compliance_percentage: Percentage of constraints that passed
        tables_validated: Number of tables that were validated
        constraints_checked: Number of constraints that were checked
    """

    violations: list[ValidationViolation] = field(default_factory=list)
    total_violations: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    compliance_percentage: float = 100.0
    tables_validated: int = 0
    constraints_checked: int = 0


class ValidationQueryGenerator:
    """Generates DuckDB SQL queries for LinkML constraint validation."""

    def __init__(self, schema_parser: Optional["SchemaParser"] = None):
        """
        Initialize the ValidationQueryGenerator.

        Args:
            schema_parser: SchemaParser instance for constraint extraction
        """
        self.schema_parser = schema_parser

    def generate_queries(
        self,
        constraints: ClassConstraints,
        available_columns: set[str],
        sample_limit: int = 10,
    ) -> list[tuple[SlotConstraint, str, str]]:
        """
        Generate SQL validation queries for constraints.

        Args:
            constraints: ClassConstraints containing slot constraints
            available_columns: Set of column names available in the table
            sample_limit: Maximum number of sample violations to return

        Returns:
            List of (constraint, count_query, sample_query) tuples
        """
        queries = []
        table = constraints.table_mapping

        for slot_name, slot_constraints in constraints.slots.items():
            if slot_name not in available_columns:
                continue

            for constraint in slot_constraints:
                count_query, sample_query = self._generate_query_pair(
                    constraint, table, sample_limit
                )
                if count_query:
                    queries.append((constraint, count_query, sample_query))

        return queries

    def _generate_query_pair(
        self,
        constraint: SlotConstraint,
        table: str,
        sample_limit: int,
    ) -> tuple[str | None, str | None]:
        """
        Generate count and sample queries for a single constraint.

        Args:
            constraint: SlotConstraint to generate queries for
            table: Table name to query
            sample_limit: Maximum number of samples to return

        Returns:
            Tuple of (count_query, sample_query) or (None, None) if not supported
        """
        slot = constraint.slot_name

        if constraint.constraint_type in (ConstraintType.REQUIRED, ConstraintType.RECOMMENDED):
            return self._required_queries(table, slot, sample_limit)

        # Add other constraint types later
        return None, None

    def _required_queries(self, table: str, slot: str, limit: int) -> tuple[str, str]:
        """
        Generate queries for required field validation.

        Args:
            table: Table name to query
            slot: Slot/column name to check
            limit: Maximum number of sample violations to return

        Returns:
            Tuple of (count_query, sample_query)
        """
        count_query = f"""
            SELECT COUNT(*) as violation_count
            FROM {table}
            WHERE "{slot}" IS NULL OR TRIM(CAST("{slot}" AS VARCHAR)) = ''
        """
        sample_query = f"""
            SELECT id, "{slot}"
            FROM {table}
            WHERE "{slot}" IS NULL OR TRIM(CAST("{slot}" AS VARCHAR)) = ''
            LIMIT {limit}
        """
        return count_query.strip(), sample_query.strip()


class ValidationEngine:
    """
    Engine for running validation against a graph database.

    The ValidationEngine takes a GraphDatabase and optional SchemaParser,
    and provides methods for validating the database contents against
    biolink model constraints.
    """

    def __init__(
        self,
        database: GraphDatabase,
        schema_parser: Optional["SchemaParser"] = None,
    ):
        """
        Initialize the ValidationEngine.

        Args:
            database: GraphDatabase instance to validate
            schema_parser: Optional SchemaParser for biolink model constraints
        """
        self.database = database
        self.schema_parser = schema_parser

    def validate(self) -> ValidationReport:
        """
        Run validation on the database and return a report.

        Returns:
            ValidationReport containing all violations found
        """
        # Skeleton implementation - returns empty report
        return ValidationReport(
            violations=[],
            total_violations=0,
            error_count=0,
            warning_count=0,
            info_count=0,
            compliance_percentage=100.0,
            tables_validated=0,
            constraints_checked=0,
        )
