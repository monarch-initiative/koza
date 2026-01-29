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
        tables_validated: List of tables that were validated
        constraints_checked: Number of constraints that were checked
    """

    violations: list[ValidationViolation] = field(default_factory=list)
    total_violations: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    compliance_percentage: float = 100.0
    tables_validated: list[str] = field(default_factory=list)
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
        sample_limit: int = 10,
    ):
        """
        Initialize the ValidationEngine.

        Args:
            database: GraphDatabase instance to validate
            schema_parser: Optional SchemaParser for biolink model constraints
            sample_limit: Maximum number of sample violations to return per constraint
        """
        self.database = database
        self.schema_parser = schema_parser
        self.sample_limit = sample_limit
        self.query_generator = ValidationQueryGenerator(self.schema_parser)

    def validate(self) -> ValidationReport:
        """
        Run validation on the database and return a report.

        Returns:
            ValidationReport containing all violations found
        """
        report = ValidationReport()

        # Phase 1: Schema structure validation (missing columns)
        if self._table_exists("nodes"):
            schema_violations = self._validate_schema_structure("nodes", "named thing")
            report.violations.extend(schema_violations)

        if self._table_exists("edges"):
            schema_violations = self._validate_schema_structure("edges", "association")
            report.violations.extend(schema_violations)

        # Phase 2: Value-level validation
        if self._table_exists("nodes"):
            node_violations = self._validate_table("nodes", "named thing")
            report.violations.extend(node_violations)
            report.tables_validated.append("nodes")

        if self._table_exists("edges"):
            edge_violations = self._validate_table("edges", "association")
            report.violations.extend(edge_violations)
            report.tables_validated.append("edges")

        # Phase 3: Referential integrity
        if self._table_exists("nodes") and self._table_exists("edges"):
            ref_violations = self._validate_referential_integrity()
            report.violations.extend(ref_violations)

        # Phase 4: Biolink-specific validations (warnings)
        if self._table_exists("nodes"):
            category_violations = self._validate_categories()
            report.violations.extend(category_violations)

            id_prefix_violations = self._validate_id_prefixes()
            report.violations.extend(id_prefix_violations)

        if self._table_exists("edges"):
            predicate_violations = self._validate_predicates()
            report.violations.extend(predicate_violations)

        self._compute_summary(report)
        return report

    def _table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if the table exists, False otherwise
        """
        try:
            self.database.conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
            return True
        except Exception:
            return False

    def _get_table_columns(self, table_name: str) -> set[str]:
        """
        Get the column names for a table.

        Args:
            table_name: Name of the table

        Returns:
            Set of column names
        """
        try:
            result = self.database.conn.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """).fetchall()
            return {row[0] for row in result}
        except Exception:
            return set()

    def _get_table_count(self, table_name: str) -> int:
        """
        Get the number of records in a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of records
        """
        try:
            result = self.database.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except Exception:
            return 0

    def _validate_schema_structure(self, table_name: str, class_name: str) -> list[ValidationViolation]:
        """
        Validate that required/recommended columns exist in the table.

        Args:
            table_name: Name of the table to validate
            class_name: Name of the class to validate against

        Returns:
            List of ValidationViolation for missing columns
        """
        violations = []

        if self.schema_parser is None:
            return violations

        constraints = self.schema_parser.get_class_constraints(class_name, table_name)
        available_columns = self._get_table_columns(table_name)
        total_records = self._get_table_count(table_name)

        for slot_name, slot_constraints in constraints.slots.items():
            if slot_name in available_columns:
                continue

            is_required = any(c.constraint_type == ConstraintType.REQUIRED for c in slot_constraints)
            is_recommended = any(c.constraint_type == ConstraintType.RECOMMENDED for c in slot_constraints)

            if is_required:
                violations.append(ValidationViolation(
                    constraint_type=ConstraintType.MISSING_COLUMN,
                    slot_name=slot_name,
                    table=table_name,
                    severity="error",
                    description=f"Required column '{slot_name}' does not exist in table",
                    violation_count=total_records,
                    total_records=total_records,
                    violation_percentage=100.0,
                    samples=[],
                ))
            elif is_recommended:
                violations.append(ValidationViolation(
                    constraint_type=ConstraintType.MISSING_COLUMN,
                    slot_name=slot_name,
                    table=table_name,
                    severity="warning",
                    description=f"Recommended column '{slot_name}' does not exist in table",
                    violation_count=total_records,
                    total_records=total_records,
                    violation_percentage=100.0,
                    samples=[],
                ))

        return violations

    def _validate_table(self, table_name: str, class_name: str) -> list[ValidationViolation]:
        """
        Validate a table against class constraints.

        Args:
            table_name: Name of the table to validate
            class_name: Name of the class to validate against

        Returns:
            List of ValidationViolation for value-level violations
        """
        violations = []

        if self.schema_parser is None:
            return violations

        constraints = self.schema_parser.get_class_constraints(class_name, table_name)
        available_columns = self._get_table_columns(table_name)
        total_records = self._get_table_count(table_name)

        queries = self.query_generator.generate_queries(
            constraints, available_columns, self.sample_limit
        )

        for constraint, count_query, sample_query in queries:
            try:
                count_result = self.database.conn.execute(count_query).fetchone()
                violation_count = count_result[0] if count_result and count_result[0] else 0

                if violation_count > 0:
                    samples = []
                    if sample_query:
                        sample_results = self.database.conn.execute(sample_query).fetchall()
                        samples = [ViolationSample(values=list(row), count=1) for row in sample_results]

                    violation = ValidationViolation(
                        constraint_type=constraint.constraint_type,
                        slot_name=constraint.slot_name,
                        table=table_name,
                        severity=constraint.severity,
                        description=constraint.description,
                        violation_count=violation_count,
                        total_records=total_records,
                        violation_percentage=(violation_count / total_records * 100) if total_records > 0 else 0,
                        samples=samples,
                    )
                    violations.append(violation)
            except Exception as e:
                from loguru import logger
                logger.warning(f"Validation query failed for {constraint.slot_name}: {e}")

        return violations

    def _validate_referential_integrity(self) -> list[ValidationViolation]:
        """
        Validate that edge subjects/objects exist in nodes.

        Returns:
            List of ValidationViolation for dangling edge references
        """
        violations = []
        total_edges = self._get_table_count("edges")

        # Check subjects
        subject_count_query = """
            SELECT COUNT(*) as violation_count
            FROM edges e
            WHERE e.subject NOT IN (SELECT id FROM nodes)
        """
        subject_sample_query = """
            SELECT e.subject as value, COUNT(*) as count
            FROM edges e
            WHERE e.subject NOT IN (SELECT id FROM nodes)
            GROUP BY e.subject
            ORDER BY count DESC
            LIMIT 10
        """

        try:
            count_result = self.database.conn.execute(subject_count_query).fetchone()
            violation_count = count_result[0] if count_result else 0

            if violation_count > 0:
                sample_results = self.database.conn.execute(subject_sample_query).fetchall()
                samples = [ViolationSample(values=[row[0]], count=row[1]) for row in sample_results]

                violations.append(ValidationViolation(
                    constraint_type=ConstraintType.RANGE_CLASS,
                    slot_name="subject",
                    table="edges",
                    severity="error",
                    description="Edge subject references non-existent node",
                    violation_count=violation_count,
                    total_records=total_edges,
                    violation_percentage=(violation_count / total_edges * 100) if total_edges > 0 else 0,
                    samples=samples,
                ))
        except Exception as e:
            from loguru import logger
            logger.warning(f"Referential integrity check failed for subject: {e}")

        # Check objects
        object_count_query = """
            SELECT COUNT(*) as violation_count
            FROM edges e
            WHERE e.object NOT IN (SELECT id FROM nodes)
        """
        object_sample_query = """
            SELECT e.object as value, COUNT(*) as count
            FROM edges e
            WHERE e.object NOT IN (SELECT id FROM nodes)
            GROUP BY e.object
            ORDER BY count DESC
            LIMIT 10
        """

        try:
            count_result = self.database.conn.execute(object_count_query).fetchone()
            violation_count = count_result[0] if count_result else 0

            if violation_count > 0:
                sample_results = self.database.conn.execute(object_sample_query).fetchall()
                samples = [ViolationSample(values=[row[0]], count=row[1]) for row in sample_results]

                violations.append(ValidationViolation(
                    constraint_type=ConstraintType.RANGE_CLASS,
                    slot_name="object",
                    table="edges",
                    severity="error",
                    description="Edge object references non-existent node",
                    violation_count=violation_count,
                    total_records=total_edges,
                    violation_percentage=(violation_count / total_edges * 100) if total_edges > 0 else 0,
                    samples=samples,
                ))
        except Exception as e:
            from loguru import logger
            logger.warning(f"Referential integrity check failed for object: {e}")

        return violations

    def _validate_categories(self) -> list[ValidationViolation]:
        """Validate node categories against Biolink model."""
        violations = []

        if self.schema_parser is None:
            return violations

        valid_categories = self.schema_parser.get_valid_categories()

        if not valid_categories:
            return violations

        total_nodes = self._get_table_count("nodes")

        # Build SQL with valid categories (limit to first 100 for query size)
        categories_list = ",".join([f"'{c}'" for c in list(valid_categories)[:100]])

        count_query = f"""
            SELECT COUNT(*) as violation_count
            FROM nodes
            WHERE category IS NOT NULL
              AND category NOT IN ({categories_list})
        """

        sample_query = f"""
            SELECT category as value, COUNT(*) as count
            FROM nodes
            WHERE category IS NOT NULL
              AND category NOT IN ({categories_list})
            GROUP BY category
            ORDER BY count DESC
            LIMIT {self.sample_limit}
        """

        try:
            count_result = self.database.conn.execute(count_query).fetchone()
            violation_count = count_result[0] if count_result else 0

            if violation_count > 0:
                sample_results = self.database.conn.execute(sample_query).fetchall()
                samples = [ViolationSample(values=[row[0]], count=row[1]) for row in sample_results]

                violations.append(ValidationViolation(
                    constraint_type=ConstraintType.ENUM,
                    slot_name="category",
                    table="nodes",
                    severity="warning",
                    description="Node category not in Biolink model",
                    violation_count=violation_count,
                    total_records=total_nodes,
                    violation_percentage=(violation_count / total_nodes * 100) if total_nodes > 0 else 0,
                    samples=samples,
                ))
        except Exception as e:
            from loguru import logger
            logger.warning(f"Category validation failed: {e}")

        return violations

    def _build_category_prefix_map(self) -> dict[str, tuple[list[str], bool]]:
        """Build mapping of category -> (prefixes, is_closed)."""
        category_prefixes = {}

        if not self.schema_parser or not self.schema_parser.schema_view:
            return category_prefixes

        try:
            for cls_name in self.schema_parser.schema_view.all_classes():
                prefixes, is_closed = self.schema_parser.get_class_id_prefixes(cls_name)
                if prefixes:
                    category = f"biolink:{cls_name.replace(' ', '')}"
                    category_prefixes[category] = (prefixes, is_closed)
        except Exception as e:
            from loguru import logger
            logger.warning(f"Failed to build category prefix map: {e}")

        return category_prefixes

    def _validate_id_prefixes(self) -> list[ValidationViolation]:
        """
        Validate node IDs match expected prefixes for their category.

        Uses id_prefixes defined on Biolink classes to check that IDs
        use appropriate prefixes (e.g., Gene IDs should start with HGNC:, NCBIGene:, etc.)
        """
        violations = []
        category_prefixes = self._build_category_prefix_map()

        if not category_prefixes:
            return violations

        total_nodes = self._get_table_count("nodes")

        # Validate each category with closed prefix lists
        for category, (prefixes, is_closed) in category_prefixes.items():
            if not prefixes or not is_closed:
                continue  # Only validate closed prefix lists

            # Build regex pattern for valid prefixes
            prefix_pattern = "|".join([f"^{p}:" for p in prefixes])

            count_query = f"""
                SELECT COUNT(*) as violation_count
                FROM nodes
                WHERE category = '{category}'
                  AND id IS NOT NULL
                  AND NOT regexp_matches(id, '{prefix_pattern}')
            """

            sample_query = f"""
                SELECT id, split_part(id, ':', 1) as prefix
                FROM nodes
                WHERE category = '{category}'
                  AND id IS NOT NULL
                  AND NOT regexp_matches(id, '{prefix_pattern}')
                LIMIT {self.sample_limit}
            """

            try:
                count_result = self.database.conn.execute(count_query).fetchone()
                violation_count = count_result[0] if count_result else 0

                if violation_count > 0:
                    sample_results = self.database.conn.execute(sample_query).fetchall()
                    samples = [ViolationSample(values=list(row), count=1) for row in sample_results]

                    violations.append(ValidationViolation(
                        constraint_type=ConstraintType.ID_PREFIX,
                        slot_name="id",
                        table="nodes",
                        severity="warning",
                        description=f"ID prefix not in allowed list for {category}: {prefixes}",
                        violation_count=violation_count,
                        total_records=total_nodes,
                        violation_percentage=(violation_count / total_nodes * 100) if total_nodes > 0 else 0,
                        samples=samples,
                    ))
            except Exception as e:
                from loguru import logger
                logger.warning(f"ID prefix validation failed for {category}: {e}")

        return violations

    def _validate_predicates(self) -> list[ValidationViolation]:
        """Validate edge predicates against Biolink model."""
        violations = []

        if self.schema_parser is None:
            return violations

        valid_predicates = self.schema_parser.get_valid_predicates()

        if not valid_predicates:
            return violations

        total_edges = self._get_table_count("edges")

        # Build SQL with valid predicates (limit to first 100 for query size)
        predicates_list = ",".join([f"'{p}'" for p in list(valid_predicates)[:100]])

        count_query = f"""
            SELECT COUNT(*) as violation_count
            FROM edges
            WHERE predicate IS NOT NULL
              AND predicate NOT IN ({predicates_list})
        """

        sample_query = f"""
            SELECT predicate as value, COUNT(*) as count
            FROM edges
            WHERE predicate IS NOT NULL
              AND predicate NOT IN ({predicates_list})
            GROUP BY predicate
            ORDER BY count DESC
            LIMIT {self.sample_limit}
        """

        try:
            count_result = self.database.conn.execute(count_query).fetchone()
            violation_count = count_result[0] if count_result else 0

            if violation_count > 0:
                sample_results = self.database.conn.execute(sample_query).fetchall()
                samples = [ViolationSample(values=[row[0]], count=row[1]) for row in sample_results]

                violations.append(ValidationViolation(
                    constraint_type=ConstraintType.ENUM,
                    slot_name="predicate",
                    table="edges",
                    severity="warning",
                    description="Edge predicate not in Biolink model",
                    violation_count=violation_count,
                    total_records=total_edges,
                    violation_percentage=(violation_count / total_edges * 100) if total_edges > 0 else 0,
                    samples=samples,
                ))
        except Exception as e:
            from loguru import logger
            logger.warning(f"Predicate validation failed: {e}")

        return violations

    def _compute_summary(self, report: ValidationReport) -> None:
        """
        Compute summary statistics for the report.

        Args:
            report: ValidationReport to update with summary statistics
        """
        report.total_violations = sum(v.violation_count for v in report.violations)
        report.error_count = sum(v.violation_count for v in report.violations if v.severity == "error")
        report.warning_count = sum(v.violation_count for v in report.violations if v.severity == "warning")
        report.info_count = sum(v.violation_count for v in report.violations if v.severity == "info")
        report.constraints_checked = len(report.violations)

        total_records = sum(self._get_table_count(table) for table in report.tables_validated)
        if total_records > 0:
            report.compliance_percentage = (total_records - report.error_count) / total_records * 100
