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
    ValidationContext,
    ValidationEngine,
    ValidationProfile,
    ValidationQueryGenerator,
    ValidationReport,
    ValidationViolation,
    ViolationSample,
)
from koza.graph_operations.utils import GraphDatabase
from koza.graph_operations.schema_utils import SchemaParser

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False


class TestConstraintType:
    """Test ConstraintType enum."""

    def test_constraint_type_is_enum(self):
        """Test that ConstraintType is an Enum with expected members."""
        assert issubclass(ConstraintType, Enum)
        # Verify the enum has members (actual member names are tested implicitly
        # through usage in other tests)
        assert len(ConstraintType) > 0


class TestValidationProfile:
    """Test ValidationProfile enum for controlling validation levels."""

    def test_validation_profile_is_enum(self):
        """Test that ValidationProfile is an Enum with expected members."""
        assert issubclass(ValidationProfile, Enum)
        assert len(ValidationProfile) > 0


class TestValidationContext:
    """Test ValidationContext dataclass for incremental validation."""

    def test_validation_context_has_categories_field(self):
        """Test that ValidationContext has categories field."""
        ctx = ValidationContext()
        assert hasattr(ctx, 'categories')
        assert ctx.categories is None

    def test_validation_context_has_profile_field(self):
        """Test that ValidationContext has profile field."""
        ctx = ValidationContext()
        assert hasattr(ctx, 'profile')
        assert ctx.profile == ValidationProfile.STANDARD

    def test_validation_context_has_parallel_field(self):
        """Test that ValidationContext has parallel field."""
        ctx = ValidationContext()
        assert hasattr(ctx, 'parallel')
        assert ctx.parallel is False

    def test_validation_context_custom_values(self):
        """Test ValidationContext with custom values."""
        ctx = ValidationContext(
            categories=["biolink:Gene", "biolink:Disease"],
            profile=ValidationProfile.FULL,
            parallel=True
        )
        assert ctx.categories == ["biolink:Gene", "biolink:Disease"]
        assert ctx.profile == ValidationProfile.FULL
        assert ctx.parallel is True


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
            tables_validated=["nodes", "edges"],
            constraints_checked=10,
        )
        assert report.violations == []
        assert report.total_violations == 0
        assert report.error_count == 0
        assert report.warning_count == 0
        assert report.info_count == 0
        assert report.compliance_percentage == 100.0
        assert report.tables_validated == ["nodes", "edges"]
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
            tables_validated=["nodes"],
            constraints_checked=5,
        )
        assert len(report.violations) == 1
        assert report.total_violations == 100
        assert report.error_count == 100


class TestValidationEngine:
    """Test ValidationEngine class."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock GraphDatabase with connection that simulates empty database."""
        import duckdb
        mock_db = MagicMock(spec=GraphDatabase)
        # Set up conn.execute to raise duckdb.Error for table checks (simulates no tables)
        mock_db.conn = MagicMock()
        mock_db.conn.execute.side_effect = duckdb.CatalogException("Table not found")
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

    # Phase 3: SchemaView support
    def test_validation_engine_accepts_schema_view(self, mock_database):
        """Test that ValidationEngine can be initialized with SchemaView directly."""
        mock_schema_view = MagicMock()
        mock_schema_view.all_classes.return_value = []

        engine = ValidationEngine(
            database=mock_database,
            schema_view=mock_schema_view,
            sample_limit=10
        )

        assert engine.schema_view is mock_schema_view

    def test_validation_engine_accepts_schema_path(self, mock_database):
        """Test that ValidationEngine can load SchemaView from path."""
        from unittest.mock import patch

        with patch('koza.graph_operations.validation.SchemaView') as mock_sv_class:
            mock_sv_instance = MagicMock()
            mock_sv_class.return_value = mock_sv_instance

            engine = ValidationEngine(
                database=mock_database,
                schema_path="https://example.com/schema.yaml",
                sample_limit=10
            )

            mock_sv_class.assert_called_once_with("https://example.com/schema.yaml")
            assert engine.schema_view is mock_sv_instance

    def test_validation_engine_schema_view_takes_precedence(self, mock_database):
        """Test that schema_view takes precedence over schema_parser."""
        from koza.graph_operations.schema_utils import SchemaParser

        mock_schema_view = MagicMock()
        mock_parser = MagicMock(spec=SchemaParser)

        engine = ValidationEngine(
            database=mock_database,
            schema_parser=mock_parser,
            schema_view=mock_schema_view
        )

        # schema_view should be set, schema_parser should still be accessible
        assert engine.schema_view is mock_schema_view
        assert engine.schema_parser == mock_parser

    # Phase 3: validate() with ValidationContext
    def test_validate_accepts_validation_context(self, mock_database):
        """Test that validate() accepts a ValidationContext."""
        engine = ValidationEngine(database=mock_database)

        ctx = ValidationContext(
            categories=["biolink:Gene"],
            profile=ValidationProfile.MINIMAL,
            parallel=False
        )

        report = engine.validate(context=ctx)
        assert isinstance(report, ValidationReport)

    def test_validate_with_category_filter(self, mock_database):
        """Test that validate() can filter by category."""
        # Mock database with category data
        mock_database.conn = MagicMock()
        mock_database.conn.execute.return_value.fetchall.return_value = []
        mock_database.conn.execute.return_value.fetchone.return_value = (0,)

        engine = ValidationEngine(database=mock_database)

        ctx = ValidationContext(categories=["biolink:Gene", "biolink:Disease"])

        report = engine.validate(context=ctx)
        assert isinstance(report, ValidationReport)


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


class TestValidationQueryGenerator:
    """Test ValidationQueryGenerator class."""

    @pytest.fixture
    def mock_schema_parser(self):
        """Create a mock SchemaParser."""
        return MagicMock(spec=SchemaParser)

    @pytest.fixture
    def query_generator(self, mock_schema_parser):
        """Create a ValidationQueryGenerator with mock schema parser."""
        return ValidationQueryGenerator(schema_parser=mock_schema_parser)

    @pytest.fixture
    def sample_constraints(self):
        """Create sample ClassConstraints for testing."""
        required_constraint = SlotConstraint(
            slot_name="id",
            constraint_type=ConstraintType.REQUIRED,
            value=True,
            class_context="named thing",
            severity="error",
            description="Field 'id' is required",
        )
        recommended_constraint = SlotConstraint(
            slot_name="name",
            constraint_type=ConstraintType.RECOMMENDED,
            value=True,
            class_context="named thing",
            severity="warning",
            description="Field 'name' is recommended",
        )
        return ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={
                "id": [required_constraint],
                "name": [recommended_constraint],
            },
        )

    # Tests for __init__

    def test_query_generator_stores_schema_parser(self, mock_schema_parser):
        """Test that ValidationQueryGenerator stores the schema_parser."""
        generator = ValidationQueryGenerator(schema_parser=mock_schema_parser)
        assert generator.schema_parser == mock_schema_parser

    # Tests for generate_queries

    def test_generate_queries_returns_list(self, query_generator, sample_constraints):
        """Test that generate_queries returns a list."""
        available_columns = {"id", "name", "category"}
        result = query_generator.generate_queries(sample_constraints, available_columns)
        assert isinstance(result, list)

    def test_generate_queries_returns_tuples(self, query_generator, sample_constraints):
        """Test that generate_queries returns tuples of (constraint, count_query, sample_query)."""
        available_columns = {"id", "name", "category"}
        result = query_generator.generate_queries(sample_constraints, available_columns)
        assert len(result) > 0
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 3
            constraint, count_query, sample_query = item
            assert isinstance(constraint, SlotConstraint)
            assert isinstance(count_query, str)
            assert isinstance(sample_query, str)

    def test_generate_queries_only_includes_available_columns(self, query_generator):
        """Test that generate_queries only generates queries for available columns."""
        constraint = SlotConstraint(
            slot_name="missing_field",
            constraint_type=ConstraintType.REQUIRED,
            value=True,
            class_context="named thing",
        )
        constraints = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={"missing_field": [constraint]},
        )
        available_columns = {"id", "name"}  # missing_field not available
        result = query_generator.generate_queries(constraints, available_columns)
        assert len(result) == 0

    def test_generate_queries_respects_sample_limit(self, query_generator, sample_constraints):
        """Test that generate_queries uses the provided sample_limit."""
        available_columns = {"id", "name"}
        result = query_generator.generate_queries(sample_constraints, available_columns, sample_limit=5)
        for constraint, count_query, sample_query in result:
            assert "LIMIT 5" in sample_query

    # Tests for _required_queries

    def test_required_queries_returns_tuple(self, query_generator):
        """Test that _required_queries returns a tuple of (count_query, sample_query)."""
        result = query_generator._required_queries("nodes", "id", 10)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_required_queries_count_query_has_select_count(self, query_generator):
        """Test that _required_queries count_query contains SELECT COUNT(*)."""
        count_query, sample_query = query_generator._required_queries("nodes", "id", 10)
        assert "SELECT COUNT(*)" in count_query

    def test_required_queries_count_query_checks_null(self, query_generator):
        """Test that _required_queries count_query checks for NULL values."""
        count_query, sample_query = query_generator._required_queries("nodes", "id", 10)
        assert "IS NULL" in count_query

    def test_required_queries_count_query_checks_empty_string(self, query_generator):
        """Test that _required_queries count_query checks for empty string."""
        count_query, sample_query = query_generator._required_queries("nodes", "id", 10)
        # Should check for trimmed empty string
        assert "TRIM" in count_query or "= ''" in count_query

    def test_required_queries_sample_query_has_limit(self, query_generator):
        """Test that _required_queries sample_query has LIMIT clause."""
        count_query, sample_query = query_generator._required_queries("nodes", "id", 10)
        assert "LIMIT 10" in sample_query

    def test_required_queries_sample_query_selects_id_and_field(self, query_generator):
        """Test that _required_queries sample_query selects id and the field."""
        count_query, sample_query = query_generator._required_queries("nodes", "name", 10)
        assert "SELECT" in sample_query
        assert "id" in sample_query
        assert '"name"' in sample_query

    def test_required_queries_uses_correct_table(self, query_generator):
        """Test that _required_queries uses the correct table name."""
        count_query, sample_query = query_generator._required_queries("edges", "subject", 5)
        assert "FROM edges" in count_query
        assert "FROM edges" in sample_query

    # Phase 3: Cardinality query generation tests
    def test_query_generator_minimum_cardinality(self, query_generator):
        """Test SQL query generation for minimum_cardinality constraint."""
        constraint = SlotConstraint(
            slot_name="publications",
            constraint_type=ConstraintType.MINIMUM_CARDINALITY,
            value=1,
            class_context="association",
            severity="error",
            description="Field 'publications' requires at least 1 value(s)"
        )

        count_query, sample_query = query_generator._generate_query_pair(
            constraint, "edges", sample_limit=10
        )

        assert count_query is not None
        assert "array_length" in count_query.lower()
        assert "< 1" in count_query
        assert sample_query is not None

    def test_query_generator_maximum_cardinality(self, query_generator):
        """Test SQL query generation for maximum_cardinality constraint."""
        constraint = SlotConstraint(
            slot_name="aliases",
            constraint_type=ConstraintType.MAXIMUM_CARDINALITY,
            value=5,
            class_context="named thing",
            severity="error",
            description="Field 'aliases' allows at most 5 value(s)"
        )

        count_query, sample_query = query_generator._generate_query_pair(
            constraint, "nodes", sample_limit=10
        )

        assert count_query is not None
        assert "array_length" in count_query.lower()
        assert "> 5" in count_query
        assert sample_query is not None

    def test_query_generator_exact_cardinality(self, query_generator):
        """Test SQL query generation for exact_cardinality constraint."""
        constraint = SlotConstraint(
            slot_name="coordinates",
            constraint_type=ConstraintType.EXACT_CARDINALITY,
            value=2,
            class_context="named thing",
            severity="error",
            description="Field 'coordinates' requires exactly 2 value(s)"
        )

        count_query, sample_query = query_generator._generate_query_pair(
            constraint, "nodes", sample_limit=10
        )

        assert count_query is not None
        assert "array_length" in count_query.lower()
        assert "!= 2" in count_query or "<> 2" in count_query
        assert sample_query is not None

    def test_query_generator_unique_key(self, query_generator):
        """Test SQL query generation for unique_key constraint."""
        constraint = SlotConstraint(
            slot_name="edge_triple",
            constraint_type=ConstraintType.UNIQUE_KEY,
            value=["subject", "object", "predicate"],
            class_context="association",
            severity="error",
            description="Combination must be unique"
        )

        count_query, sample_query = query_generator._generate_query_pair(
            constraint, "edges", sample_limit=10
        )

        assert count_query is not None
        assert "GROUP BY" in count_query
        assert "HAVING COUNT(*) > 1" in count_query
        assert '"subject"' in count_query
        assert '"object"' in count_query
        assert '"predicate"' in count_query
        assert sample_query is not None


class TestValidationQueryGeneratorIntegration:
    """Integration tests for ValidationQueryGenerator with real DuckDB."""

    @pytest.fixture
    def mock_schema_parser(self):
        """Create a mock SchemaParser."""
        return MagicMock(spec=SchemaParser)

    @pytest.fixture
    def query_generator(self, mock_schema_parser):
        """Create a ValidationQueryGenerator with mock schema parser."""
        return ValidationQueryGenerator(schema_parser=mock_schema_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_generated_queries_are_valid_duckdb_sql(self, query_generator):
        """Test that generated queries execute successfully in DuckDB."""
        conn = duckdb.connect(":memory:")

        # Create a test table
        conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)

        # Insert test data - some with NULL/empty values
        conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', NULL, 'biolink:Disease'),
            ('node3', '', 'biolink:Gene'),
            (NULL, 'Gene D', 'biolink:Gene')
        """)

        # Generate queries
        count_query, sample_query = query_generator._required_queries("nodes", "name", 10)

        # Execute count query - should not raise
        result = conn.execute(count_query).fetchone()
        assert result is not None
        violation_count = result[0]
        assert violation_count == 2  # NULL and empty string

        # Execute sample query - should not raise
        samples = conn.execute(sample_query).fetchall()
        assert len(samples) == 2  # Should get both violations

        conn.close()

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_generated_queries_with_full_workflow(self, query_generator):
        """Test full workflow: constraints -> queries -> execution -> results."""
        conn = duckdb.connect(":memory:")

        # Create a test table
        conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)

        # Insert test data
        conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Valid Name', 'biolink:Gene'),
            ('node2', NULL, 'biolink:Disease'),
            ('node3', '', 'biolink:Gene'),
            ('node4', '  ', 'biolink:Gene'),
            ('node5', 'Another Name', 'biolink:Protein')
        """)

        # Create constraints
        required_constraint = SlotConstraint(
            slot_name="name",
            constraint_type=ConstraintType.REQUIRED,
            value=True,
            class_context="named thing",
            severity="error",
        )
        constraints = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={"name": [required_constraint]},
        )

        # Generate queries
        available_columns = {"id", "name", "category"}
        queries = query_generator.generate_queries(constraints, available_columns, sample_limit=5)

        assert len(queries) == 1
        constraint, count_query, sample_query = queries[0]

        # Execute and verify
        result = conn.execute(count_query).fetchone()
        violation_count = result[0]
        # Should catch NULL, empty string, and whitespace-only
        assert violation_count == 3

        samples = conn.execute(sample_query).fetchall()
        assert len(samples) == 3

        conn.close()


class TestCardinalityConstraintExtraction:
    """Test cardinality constraint extraction from slots."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock GraphDatabase."""
        mock_db = MagicMock(spec=GraphDatabase)
        return mock_db

    def test_extract_cardinality_from_slot(self, mock_database):
        """Test extracting cardinality constraints directly from slot objects."""
        mock_schema_view = MagicMock()

        # Create mock slot with cardinality
        mock_slot = MagicMock()
        mock_slot.name = "publications"
        mock_slot.minimum_cardinality = 1
        mock_slot.maximum_cardinality = 10
        mock_slot.exact_cardinality = None
        mock_slot.multivalued = True
        mock_slot.required = False
        mock_slot.recommended = False
        mock_slot.pattern = None
        mock_slot.identifier = False
        mock_slot.subproperty_of = None

        mock_schema_view.class_induced_slots.return_value = [mock_slot]

        engine = ValidationEngine(database=mock_database, schema_view=mock_schema_view)

        constraints = engine._extract_slot_constraints(mock_slot, "association")

        # Should extract both min and max cardinality
        min_card = [c for c in constraints if c.constraint_type == ConstraintType.MINIMUM_CARDINALITY]
        max_card = [c for c in constraints if c.constraint_type == ConstraintType.MAXIMUM_CARDINALITY]

        assert len(min_card) == 1
        assert min_card[0].value == 1
        assert len(max_card) == 1
        assert max_card[0].value == 10

    def test_extract_exact_cardinality_from_slot(self, mock_database):
        """Test extracting exact_cardinality constraint from slot."""
        mock_schema_view = MagicMock()

        mock_slot = MagicMock()
        mock_slot.name = "coordinates"
        mock_slot.minimum_cardinality = None
        mock_slot.maximum_cardinality = None
        mock_slot.exact_cardinality = 3
        mock_slot.multivalued = True
        mock_slot.required = False
        mock_slot.recommended = False
        mock_slot.pattern = None
        mock_slot.identifier = False
        mock_slot.subproperty_of = None

        engine = ValidationEngine(database=mock_database, schema_view=mock_schema_view)

        constraints = engine._extract_slot_constraints(mock_slot, "named thing")

        exact_card = [c for c in constraints if c.constraint_type == ConstraintType.EXACT_CARDINALITY]
        assert len(exact_card) == 1
        assert exact_card[0].value == 3

    def test_extract_required_constraint_from_slot(self, mock_database):
        """Test extracting required constraint from slot."""
        mock_schema_view = MagicMock()

        mock_slot = MagicMock()
        mock_slot.name = "id"
        mock_slot.minimum_cardinality = None
        mock_slot.maximum_cardinality = None
        mock_slot.exact_cardinality = None
        mock_slot.multivalued = False
        mock_slot.required = True
        mock_slot.recommended = False
        mock_slot.pattern = None
        mock_slot.identifier = True
        mock_slot.subproperty_of = None

        engine = ValidationEngine(database=mock_database, schema_view=mock_schema_view)

        constraints = engine._extract_slot_constraints(mock_slot, "named thing")

        required = [c for c in constraints if c.constraint_type == ConstraintType.REQUIRED]
        assert len(required) == 1
        assert required[0].severity == "error"

    def test_extract_recommended_constraint_from_slot(self, mock_database):
        """Test extracting recommended constraint from slot."""
        mock_schema_view = MagicMock()

        mock_slot = MagicMock()
        mock_slot.name = "description"
        mock_slot.minimum_cardinality = None
        mock_slot.maximum_cardinality = None
        mock_slot.exact_cardinality = None
        mock_slot.multivalued = False
        mock_slot.required = False
        mock_slot.recommended = True
        mock_slot.pattern = None
        mock_slot.identifier = False
        mock_slot.subproperty_of = None

        engine = ValidationEngine(database=mock_database, schema_view=mock_schema_view)

        constraints = engine._extract_slot_constraints(mock_slot, "named thing")

        recommended = [c for c in constraints if c.constraint_type == ConstraintType.RECOMMENDED]
        assert len(recommended) == 1
        assert recommended[0].severity == "warning"

    def test_extract_subproperty_of_from_slot(self, mock_database):
        """Test extracting subproperty_of constraint from slot."""
        mock_schema_view = MagicMock()
        mock_schema_view.slot_descendants.return_value = ["object_closure", "object"]

        mock_slot = MagicMock()
        mock_slot.name = "object"
        mock_slot.minimum_cardinality = None
        mock_slot.maximum_cardinality = None
        mock_slot.exact_cardinality = None
        mock_slot.multivalued = False
        mock_slot.required = True
        mock_slot.recommended = False
        mock_slot.pattern = None
        mock_slot.identifier = False
        mock_slot.subproperty_of = "related to"

        engine = ValidationEngine(database=mock_database, schema_view=mock_schema_view)

        constraints = engine._extract_slot_constraints(mock_slot, "association")

        subprop = [c for c in constraints if c.constraint_type == ConstraintType.SUBPROPERTY_OF]
        assert len(subprop) == 1
        assert subprop[0].value == "related to"
        assert subprop[0].severity == "info"


class TestUniqueKeyExtraction:
    """Test unique key extraction from SchemaView."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock GraphDatabase."""
        mock_db = MagicMock(spec=GraphDatabase)
        return mock_db

    def test_get_unique_keys_from_schema_view(self, mock_database):
        """Test extracting unique_keys directly from SchemaView class definition."""
        mock_schema_view = MagicMock()

        # Mock class with unique_keys
        mock_class = MagicMock()
        mock_unique_key = MagicMock()
        mock_unique_key.unique_key_slots = ["subject", "object", "predicate"]
        mock_class.unique_keys = {"edge_triple": mock_unique_key}

        mock_schema_view.get_class.return_value = mock_class

        engine = ValidationEngine(database=mock_database, schema_view=mock_schema_view)

        unique_keys = engine._get_unique_keys("association")

        assert "edge_triple" in unique_keys
        assert unique_keys["edge_triple"] == ["subject", "object", "predicate"]

    def test_get_unique_keys_handles_missing(self, mock_database):
        """Test that _get_unique_keys handles classes without unique_keys."""
        mock_schema_view = MagicMock()

        mock_class = MagicMock()
        mock_class.unique_keys = None

        mock_schema_view.get_class.return_value = mock_class

        engine = ValidationEngine(database=mock_database, schema_view=mock_schema_view)

        unique_keys = engine._get_unique_keys("named thing")

        assert unique_keys == {}

    def test_get_unique_keys_handles_no_schema_view(self, mock_database):
        """Test that _get_unique_keys returns empty dict when no schema_view."""
        engine = ValidationEngine(database=mock_database, schema_view=None)

        unique_keys = engine._get_unique_keys("association")

        assert unique_keys == {}

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not available")
    def test_validate_unique_keys_finds_duplicates(self):
        """Test _validate_unique_keys detects duplicate key combinations."""
        conn = duckdb.connect(":memory:")
        conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                object VARCHAR,
                predicate VARCHAR
            )
        """)
        conn.execute("""
            INSERT INTO edges VALUES
                ('e1', 'GENE:1', 'DISEASE:1', 'biolink:associated_with'),
                ('e2', 'GENE:1', 'DISEASE:1', 'biolink:associated_with'),
                ('e3', 'GENE:2', 'DISEASE:2', 'biolink:causes')
        """)

        mock_db = MagicMock()
        mock_db.conn = conn

        mock_schema_view = MagicMock()
        mock_class = MagicMock()
        mock_uk = MagicMock()
        mock_uk.unique_key_slots = ["subject", "object", "predicate"]
        mock_class.unique_keys = {"edge_triple": mock_uk}
        mock_schema_view.get_class.return_value = mock_class

        engine = ValidationEngine(database=mock_db, schema_view=mock_schema_view)

        violations = engine._validate_unique_keys("edges", "association")

        assert len(violations) == 1
        assert violations[0].constraint_type == ConstraintType.UNIQUE_KEY
        assert violations[0].violation_count == 1  # 2 rows - 1 = 1 duplicate
        assert violations[0].severity == "error"

        conn.close()


class TestValidationEngineHelpers:
    """Test ValidationEngine helper methods with real DuckDB."""

    @pytest.fixture
    def db_with_data(self):
        """Create a GraphDatabase with test data."""
        db = GraphDatabase()
        # Create nodes table with test data
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', 'Gene B', 'biolink:Gene'),
            ('node3', NULL, 'biolink:Disease')
        """)
        # Create edges table with test data
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'node2', 'biolink:related_to', 'node3')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine(self, db_with_data):
        """Create a ValidationEngine with the test database."""
        mock_parser = MagicMock(spec=SchemaParser)
        return ValidationEngine(database=db_with_data, schema_parser=mock_parser)

    # Tests for _table_exists

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_table_exists_returns_true_for_existing_table(self, engine):
        """Test that _table_exists returns True for existing tables."""
        assert engine._table_exists("nodes") is True

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_table_exists_returns_false_for_nonexistent_table(self, engine):
        """Test that _table_exists returns False for non-existing tables."""
        assert engine._table_exists("nonexistent_table") is False

    # Tests for _get_table_columns

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_get_table_columns_returns_set(self, engine):
        """Test that _get_table_columns returns a set."""
        result = engine._get_table_columns("nodes")
        assert isinstance(result, set)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_get_table_columns_returns_correct_columns(self, engine):
        """Test that _get_table_columns returns the correct column names."""
        result = engine._get_table_columns("nodes")
        assert result == {"id", "name", "category"}

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_get_table_columns_returns_empty_for_nonexistent(self, engine):
        """Test that _get_table_columns returns empty set for non-existing table."""
        result = engine._get_table_columns("nonexistent_table")
        assert result == set()

    # Tests for _get_table_count

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_get_table_count_returns_int(self, engine):
        """Test that _get_table_count returns an int."""
        result = engine._get_table_count("nodes")
        assert isinstance(result, int)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_get_table_count_returns_correct_count(self, engine):
        """Test that _get_table_count returns the correct count."""
        result = engine._get_table_count("nodes")
        assert result == 3

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_get_table_count_returns_zero_for_nonexistent(self, engine):
        """Test that _get_table_count returns 0 for non-existing table."""
        result = engine._get_table_count("nonexistent_table")
        assert result == 0

    # Tests for _validate_schema_structure

    @pytest.fixture
    def db_missing_column(self):
        """Create a GraphDatabase with a table missing required columns."""
        db = GraphDatabase()
        # Create nodes table missing the 'name' column
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'biolink:Gene'),
            ('node2', 'biolink:Disease')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_real_parser(self, db_missing_column):
        """Create a ValidationEngine with real SchemaParser but missing columns."""
        # Use a mock parser that returns specific constraints
        mock_parser = MagicMock(spec=SchemaParser)
        # Return constraints that include required and recommended columns
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={
                "id": [SlotConstraint(
                    slot_name="id",
                    constraint_type=ConstraintType.REQUIRED,
                    value=True,
                    class_context="named thing",
                    severity="error",
                    description="Field 'id' is required",
                )],
                "name": [SlotConstraint(
                    slot_name="name",
                    constraint_type=ConstraintType.RECOMMENDED,
                    value=True,
                    class_context="named thing",
                    severity="warning",
                    description="Field 'name' is recommended",
                )],
                "category": [SlotConstraint(
                    slot_name="category",
                    constraint_type=ConstraintType.REQUIRED,
                    value=True,
                    class_context="named thing",
                    severity="error",
                    description="Field 'category' is required",
                )],
                "description": [SlotConstraint(
                    slot_name="description",
                    constraint_type=ConstraintType.REQUIRED,
                    value=True,
                    class_context="named thing",
                    severity="error",
                    description="Field 'description' is required",
                )],
            },
        )
        return ValidationEngine(database=db_missing_column, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_schema_structure_returns_list(self, engine_with_real_parser):
        """Test that _validate_schema_structure returns a list."""
        result = engine_with_real_parser._validate_schema_structure("nodes", "named thing")
        assert isinstance(result, list)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_schema_structure_returns_empty_when_all_columns_exist(self, engine):
        """Test that _validate_schema_structure returns empty list when all required columns exist."""
        # Configure mock to return constraints only for existing columns
        engine.schema_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={
                "id": [SlotConstraint(
                    slot_name="id",
                    constraint_type=ConstraintType.REQUIRED,
                    value=True,
                    class_context="named thing",
                    severity="error",
                    description="Field 'id' is required",
                )],
            },
        )
        result = engine._validate_schema_structure("nodes", "named thing")
        assert result == []

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_schema_structure_returns_violation_for_missing_required_column(self, engine_with_real_parser):
        """Test that _validate_schema_structure returns ValidationViolation when required column missing."""
        result = engine_with_real_parser._validate_schema_structure("nodes", "named thing")
        # Should have violations for 'name' (recommended) and 'description' (required)
        assert len(result) >= 1
        # Check that all results are ValidationViolation
        for violation in result:
            assert isinstance(violation, ValidationViolation)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_schema_structure_missing_required_has_error_severity(self, engine_with_real_parser):
        """Test that missing required column has severity='error'."""
        result = engine_with_real_parser._validate_schema_structure("nodes", "named thing")
        # Find the violation for 'description' (required column that's missing)
        description_violation = next((v for v in result if v.slot_name == "description"), None)
        assert description_violation is not None
        assert description_violation.severity == "error"
        assert description_violation.constraint_type == ConstraintType.MISSING_COLUMN

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_schema_structure_missing_recommended_has_warning_severity(self, engine_with_real_parser):
        """Test that missing recommended column has severity='warning'."""
        result = engine_with_real_parser._validate_schema_structure("nodes", "named thing")
        # Find the violation for 'name' (recommended column that's missing)
        name_violation = next((v for v in result if v.slot_name == "name"), None)
        assert name_violation is not None
        assert name_violation.severity == "warning"
        assert name_violation.constraint_type == ConstraintType.MISSING_COLUMN


class TestValidationEngineValidateTable:
    """Test ValidationEngine._validate_table method."""

    @pytest.fixture
    def db_with_violations(self):
        """Create a GraphDatabase with data that has validation violations."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', NULL, 'biolink:Disease'),
            ('node3', '', 'biolink:Gene'),
            ('node4', '  ', 'biolink:Protein'),
            ('node5', 'Valid Name', 'biolink:Gene')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_violations(self, db_with_violations):
        """Create a ValidationEngine with data that has violations."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={
                "id": [SlotConstraint(
                    slot_name="id",
                    constraint_type=ConstraintType.REQUIRED,
                    value=True,
                    class_context="named thing",
                    severity="error",
                    description="Field 'id' is required",
                )],
                "name": [SlotConstraint(
                    slot_name="name",
                    constraint_type=ConstraintType.REQUIRED,
                    value=True,
                    class_context="named thing",
                    severity="error",
                    description="Field 'name' is required",
                )],
            },
        )
        return ValidationEngine(database=db_with_violations, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_table_returns_list(self, engine_with_violations):
        """Test that _validate_table returns a list."""
        result = engine_with_violations._validate_table("nodes", "named thing")
        assert isinstance(result, list)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_table_returns_validation_violations(self, engine_with_violations):
        """Test that _validate_table returns list of ValidationViolation."""
        result = engine_with_violations._validate_table("nodes", "named thing")
        for item in result:
            assert isinstance(item, ValidationViolation)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_table_finds_null_required_fields(self, engine_with_violations):
        """Test that _validate_table finds violations for rows with NULL required fields."""
        result = engine_with_violations._validate_table("nodes", "named thing")
        # Find violation for 'name' field
        name_violation = next((v for v in result if v.slot_name == "name"), None)
        assert name_violation is not None
        # Should find 3 violations (NULL, empty string, whitespace-only)
        assert name_violation.violation_count == 3

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_table_includes_samples(self, engine_with_violations):
        """Test that _validate_table includes samples of violating records."""
        result = engine_with_violations._validate_table("nodes", "named thing")
        name_violation = next((v for v in result if v.slot_name == "name"), None)
        assert name_violation is not None
        assert len(name_violation.samples) > 0
        for sample in name_violation.samples:
            assert isinstance(sample, ViolationSample)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_table_calculates_violation_percentage(self, engine_with_violations):
        """Test that _validate_table calculates violation_percentage correctly."""
        result = engine_with_violations._validate_table("nodes", "named thing")
        name_violation = next((v for v in result if v.slot_name == "name"), None)
        assert name_violation is not None
        # 3 violations out of 5 records = 60%
        assert name_violation.violation_percentage == 60.0
        assert name_violation.total_records == 5
        assert name_violation.violation_count == 3


class TestReferentialIntegrityValidation:
    """Test ValidationEngine referential integrity validation."""

    @pytest.fixture
    def db_with_dangling_edges(self):
        """Create a GraphDatabase with edges referencing non-existent nodes."""
        db = GraphDatabase()
        # Create nodes table
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', 'Gene B', 'biolink:Gene'),
            ('node3', 'Disease C', 'biolink:Disease')
        """)
        # Create edges table - some edges reference non-existent nodes
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'node2', 'biolink:related_to', 'node3'),
            ('edge3', 'orphan_subject_1', 'biolink:interacts_with', 'node1'),
            ('edge4', 'orphan_subject_1', 'biolink:related_to', 'node2'),
            ('edge5', 'orphan_subject_2', 'biolink:causes', 'node3'),
            ('edge6', 'node1', 'biolink:treats', 'orphan_object_1'),
            ('edge7', 'node2', 'biolink:treats', 'orphan_object_1'),
            ('edge8', 'node3', 'biolink:treats', 'orphan_object_2')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_dangling_edges(self, db_with_dangling_edges):
        """Create a ValidationEngine with dangling edge references."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_dangling_edges, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_returns_list(self, engine_with_dangling_edges):
        """Test that _validate_referential_integrity returns a list."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        assert isinstance(result, list)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_returns_validation_violations(self, engine_with_dangling_edges):
        """Test that _validate_referential_integrity returns list of ValidationViolation."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        for item in result:
            assert isinstance(item, ValidationViolation)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_finds_dangling_subjects(self, engine_with_dangling_edges):
        """Test that _validate_referential_integrity finds edges with non-existent subjects."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        subject_violation = next((v for v in result if v.slot_name == "subject"), None)
        assert subject_violation is not None
        # 3 edges have orphan subjects (edge3, edge4, edge5)
        assert subject_violation.violation_count == 3

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_finds_dangling_objects(self, engine_with_dangling_edges):
        """Test that _validate_referential_integrity finds edges with non-existent objects."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        object_violation = next((v for v in result if v.slot_name == "object"), None)
        assert object_violation is not None
        # 3 edges have orphan objects (edge6, edge7, edge8)
        assert object_violation.violation_count == 3

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_has_range_class_constraint_type(self, engine_with_dangling_edges):
        """Test that violations have constraint_type=ConstraintType.RANGE_CLASS."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        for violation in result:
            assert violation.constraint_type == ConstraintType.RANGE_CLASS

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_has_error_severity(self, engine_with_dangling_edges):
        """Test that violations have severity='error'."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        for violation in result:
            assert violation.severity == "error"

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_includes_samples(self, engine_with_dangling_edges):
        """Test that violations include samples of orphan values with counts."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        subject_violation = next((v for v in result if v.slot_name == "subject"), None)
        assert subject_violation is not None
        assert len(subject_violation.samples) > 0
        # Check samples have orphan values with counts
        for sample in subject_violation.samples:
            assert isinstance(sample, ViolationSample)
            assert len(sample.values) == 1
            assert sample.count > 0

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_sample_counts_are_correct(self, engine_with_dangling_edges):
        """Test that sample counts match actual occurrences of orphan values."""
        result = engine_with_dangling_edges._validate_referential_integrity()
        subject_violation = next((v for v in result if v.slot_name == "subject"), None)
        assert subject_violation is not None
        # orphan_subject_1 appears 2 times, orphan_subject_2 appears 1 time
        sample_dict = {s.values[0]: s.count for s in subject_violation.samples}
        assert sample_dict.get("orphan_subject_1") == 2
        assert sample_dict.get("orphan_subject_2") == 1

    @pytest.fixture
    def db_with_valid_edges(self):
        """Create a GraphDatabase where all edge references are valid."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', 'Gene B', 'biolink:Gene')
        """)
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'node2', 'biolink:related_to', 'node1')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_valid_edges(self, db_with_valid_edges):
        """Create a ValidationEngine with all valid edge references."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_valid_edges, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_referential_integrity_empty_when_all_valid(self, engine_with_valid_edges):
        """Test that _validate_referential_integrity returns empty list when all references valid."""
        result = engine_with_valid_edges._validate_referential_integrity()
        assert result == []


class TestValidationEngineValidate:

    @pytest.fixture
    def db_full(self):
        """Create a GraphDatabase with both nodes and edges tables."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', NULL, 'biolink:Disease'),
            ('node3', 'Gene C', 'biolink:Gene')
        """)
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', NULL, 'biolink:related_to', 'node3')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_full(self, db_full):
        """Create a ValidationEngine with both tables."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.schema_view = None  # No schema view - disables ID prefix validation

        def mock_get_class_constraints(class_name, table_mapping):
            if class_name == "named thing":
                return ClassConstraints(
                    class_name="named thing",
                    table_mapping="nodes",
                    slots={
                        "id": [SlotConstraint(
                            slot_name="id",
                            constraint_type=ConstraintType.REQUIRED,
                            value=True,
                            class_context="named thing",
                            severity="error",
                            description="Field 'id' is required",
                        )],
                        "name": [SlotConstraint(
                            slot_name="name",
                            constraint_type=ConstraintType.REQUIRED,
                            value=True,
                            class_context="named thing",
                            severity="error",
                            description="Field 'name' is required",
                        )],
                    },
                )
            else:  # association
                return ClassConstraints(
                    class_name="association",
                    table_mapping="edges",
                    slots={
                        "subject": [SlotConstraint(
                            slot_name="subject",
                            constraint_type=ConstraintType.REQUIRED,
                            value=True,
                            class_context="association",
                            severity="error",
                            description="Field 'subject' is required",
                        )],
                        "predicate": [SlotConstraint(
                            slot_name="predicate",
                            constraint_type=ConstraintType.REQUIRED,
                            value=True,
                            class_context="association",
                            severity="error",
                            description="Field 'predicate' is required",
                        )],
                    },
                )

        mock_parser.get_class_constraints.side_effect = mock_get_class_constraints
        mock_parser.get_valid_categories.return_value = set()
        mock_parser.get_valid_predicates.return_value = set()
        return ValidationEngine(database=db_full, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_returns_validation_report(self, engine_full):
        """Test that validate() returns a ValidationReport."""
        result = engine_full.validate()
        assert isinstance(result, ValidationReport)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_validates_nodes_table(self, engine_full):
        """Test that validate() validates the nodes table when it exists."""
        result = engine_full.validate()
        # Should have validated nodes table
        assert "nodes" in result.tables_validated

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_validates_edges_table(self, engine_full):
        """Test that validate() validates the edges table when it exists."""
        result = engine_full.validate()
        # Should have validated edges table
        assert "edges" in result.tables_validated

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_computes_total_violations(self, engine_full):
        """Test that validate() computes total_violations correctly."""
        result = engine_full.validate()
        # Should have violations: 1 for nodes (NULL name), 1 for edges (NULL subject)
        assert result.total_violations == 2

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_computes_error_count(self, engine_full):
        """Test that validate() computes error_count correctly."""
        result = engine_full.validate()
        # All violations have severity="error"
        assert result.error_count == 2

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_computes_warning_count(self, engine_full):
        """Test that validate() computes warning_count correctly."""
        result = engine_full.validate()
        # No warnings in our test data
        assert result.warning_count == 0

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_sets_compliance_percentage(self, engine_full):
        """Test that validate() sets compliance_percentage correctly."""
        result = engine_full.validate()
        # 5 total records (3 nodes + 2 edges), 2 error violations
        # compliance = (5 - 2) / 5 * 100 = 60%
        assert result.compliance_percentage == 60.0


class TestBiolinkCategoryValidation:
    """Test ValidationEngine._validate_categories method."""

    @pytest.fixture
    def db_with_invalid_categories(self):
        """Create a GraphDatabase with nodes having invalid categories."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', 'Gene B', 'biolink:Gene'),
            ('node3', 'Disease C', 'biolink:Disease'),
            ('node4', 'Invalid D', 'biolink:InvalidCategory'),
            ('node5', 'Unknown E', 'biolink:MadeUpThing'),
            ('node6', 'Another F', 'biolink:InvalidCategory')
        """)
        yield db
        db.close()

    @pytest.fixture
    def db_with_valid_categories(self):
        """Create a GraphDatabase with all valid categories."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', 'Gene B', 'biolink:Gene'),
            ('node3', 'Disease C', 'biolink:Disease')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_invalid_categories(self, db_with_invalid_categories):
        """Create a ValidationEngine with invalid categories."""
        mock_parser = MagicMock(spec=SchemaParser)
        # Return a set of valid categories
        mock_parser.get_valid_categories.return_value = {
            "biolink:Gene",
            "biolink:Disease",
            "biolink:Protein",
            "biolink:NamedThing",
        }
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_invalid_categories, schema_parser=mock_parser)

    @pytest.fixture
    def engine_with_valid_categories(self, db_with_valid_categories):
        """Create a ValidationEngine with all valid categories."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.get_valid_categories.return_value = {
            "biolink:Gene",
            "biolink:Disease",
            "biolink:Protein",
            "biolink:NamedThing",
        }
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_valid_categories, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_categories_returns_list(self, engine_with_invalid_categories):
        """Test that _validate_categories returns a list."""
        result = engine_with_invalid_categories._validate_categories()
        assert isinstance(result, list)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_categories_returns_empty_when_all_valid(self, engine_with_valid_categories):
        """Test that _validate_categories returns empty list when all categories valid."""
        result = engine_with_valid_categories._validate_categories()
        assert result == []

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_categories_detects_invalid_categories(self, engine_with_invalid_categories):
        """Test that _validate_categories detects invalid categories."""
        result = engine_with_invalid_categories._validate_categories()
        assert len(result) == 1
        # Should find 3 violations (node4, node5, node6)
        assert result[0].violation_count == 3

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_categories_has_enum_constraint_type(self, engine_with_invalid_categories):
        """Test that violations have constraint_type=ConstraintType.ENUM."""
        result = engine_with_invalid_categories._validate_categories()
        assert len(result) == 1
        assert result[0].constraint_type == ConstraintType.ENUM

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_categories_has_warning_severity(self, engine_with_invalid_categories):
        """Test that violations have severity='warning'."""
        result = engine_with_invalid_categories._validate_categories()
        assert len(result) == 1
        assert result[0].severity == "warning"

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_categories_includes_samples_with_counts(self, engine_with_invalid_categories):
        """Test that violations include samples showing invalid values with counts."""
        result = engine_with_invalid_categories._validate_categories()
        assert len(result) == 1
        assert len(result[0].samples) > 0
        # Check samples have the invalid categories with counts
        sample_dict = {s.values[0]: s.count for s in result[0].samples}
        # biolink:InvalidCategory appears twice, biolink:MadeUpThing appears once
        assert sample_dict.get("biolink:InvalidCategory") == 2
        assert sample_dict.get("biolink:MadeUpThing") == 1


class TestIdPrefixValidation:
    """Test ValidationEngine ID prefix validation."""

    @pytest.fixture
    def db_with_mixed_prefixes(self):
        """Create a GraphDatabase with nodes having various ID prefixes."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('HGNC:1234', 'Gene A', 'biolink:Gene'),
            ('NCBIGene:5678', 'Gene B', 'biolink:Gene'),
            ('INVALID:9999', 'Gene C', 'biolink:Gene'),
            ('MONDO:0001234', 'Disease A', 'biolink:Disease'),
            ('HP:0000001', 'Disease B', 'biolink:Disease'),
            ('BADPREFIX:123', 'Disease C', 'biolink:Disease')
        """)
        yield db
        db.close()

    @pytest.fixture
    def db_with_valid_prefixes(self):
        """Create a GraphDatabase with all valid ID prefixes."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                name VARCHAR,
                category VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO nodes VALUES
            ('HGNC:1234', 'Gene A', 'biolink:Gene'),
            ('NCBIGene:5678', 'Gene B', 'biolink:Gene'),
            ('MONDO:0001234', 'Disease A', 'biolink:Disease')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_mixed_prefixes(self, db_with_mixed_prefixes):
        """Create a ValidationEngine with mixed ID prefixes."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.schema_view = MagicMock()

        # Mock all_classes to return Gene and Disease
        mock_parser.schema_view.all_classes.return_value = ["Gene", "Disease"]

        # Mock get_class_id_prefixes
        def mock_get_prefixes(class_name):
            if class_name == "Gene":
                return (["HGNC", "NCBIGene", "ENSEMBL"], True)  # closed list
            elif class_name == "Disease":
                return (["MONDO", "OMIM", "DOID"], True)  # closed list
            return ([], False)

        mock_parser.get_class_id_prefixes.side_effect = mock_get_prefixes
        mock_parser.get_valid_categories.return_value = {"biolink:Gene", "biolink:Disease"}
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_mixed_prefixes, schema_parser=mock_parser)

    @pytest.fixture
    def engine_with_valid_prefixes(self, db_with_valid_prefixes):
        """Create a ValidationEngine with all valid ID prefixes."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.schema_view = MagicMock()
        mock_parser.schema_view.all_classes.return_value = ["Gene", "Disease"]

        def mock_get_prefixes(class_name):
            if class_name == "Gene":
                return (["HGNC", "NCBIGene", "ENSEMBL"], True)
            elif class_name == "Disease":
                return (["MONDO", "OMIM", "DOID"], True)
            return ([], False)

        mock_parser.get_class_id_prefixes.side_effect = mock_get_prefixes
        mock_parser.get_valid_categories.return_value = {"biolink:Gene", "biolink:Disease"}
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_valid_prefixes, schema_parser=mock_parser)

    @pytest.fixture
    def engine_with_open_prefixes(self, db_with_mixed_prefixes):
        """Create a ValidationEngine where prefixes are NOT closed (open list)."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.schema_view = MagicMock()
        mock_parser.schema_view.all_classes.return_value = ["Gene", "Disease"]

        def mock_get_prefixes(class_name):
            if class_name == "Gene":
                return (["HGNC", "NCBIGene"], False)  # open list - should NOT validate
            elif class_name == "Disease":
                return (["MONDO"], False)  # open list - should NOT validate
            return ([], False)

        mock_parser.get_class_id_prefixes.side_effect = mock_get_prefixes
        mock_parser.get_valid_categories.return_value = {"biolink:Gene", "biolink:Disease"}
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_mixed_prefixes, schema_parser=mock_parser)

    @pytest.fixture
    def engine_no_prefixes(self, db_with_mixed_prefixes):
        """Create a ValidationEngine with no id_prefixes defined."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.schema_view = None  # No schema loaded
        mock_parser.get_class_id_prefixes.return_value = ([], False)
        mock_parser.get_valid_categories.return_value = set()
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="named thing",
            table_mapping="nodes",
            slots={},
        )
        return ValidationEngine(database=db_with_mixed_prefixes, schema_parser=mock_parser)

    # Tests for _validate_id_prefixes

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_returns_list(self, engine_with_mixed_prefixes):
        """Test that _validate_id_prefixes returns a list."""
        result = engine_with_mixed_prefixes._validate_id_prefixes()
        assert isinstance(result, list)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_returns_empty_when_no_prefixes_defined(self, engine_no_prefixes):
        """Test that _validate_id_prefixes returns empty list when no id_prefixes defined."""
        result = engine_no_prefixes._validate_id_prefixes()
        assert result == []

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_returns_empty_when_all_valid(self, engine_with_valid_prefixes):
        """Test that _validate_id_prefixes returns empty list when all IDs match prefixes."""
        result = engine_with_valid_prefixes._validate_id_prefixes()
        assert result == []

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_detects_invalid_prefixes(self, engine_with_mixed_prefixes):
        """Test that _validate_id_prefixes detects IDs with invalid prefixes."""
        result = engine_with_mixed_prefixes._validate_id_prefixes()
        assert len(result) > 0

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_has_id_prefix_constraint_type(self, engine_with_mixed_prefixes):
        """Test that violations have constraint_type=ConstraintType.ID_PREFIX."""
        result = engine_with_mixed_prefixes._validate_id_prefixes()
        for violation in result:
            assert violation.constraint_type == ConstraintType.ID_PREFIX

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_has_warning_severity(self, engine_with_mixed_prefixes):
        """Test that violations have severity='warning'."""
        result = engine_with_mixed_prefixes._validate_id_prefixes()
        for violation in result:
            assert violation.severity == "warning"

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_only_validates_closed_lists(self, engine_with_open_prefixes):
        """Test that _validate_id_prefixes only validates categories with is_closed=True."""
        result = engine_with_open_prefixes._validate_id_prefixes()
        # Should return empty because all prefixes are open (not closed)
        assert result == []

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_id_prefixes_includes_samples_with_id_and_prefix(self, engine_with_mixed_prefixes):
        """Test that violations include samples showing ID and extracted prefix."""
        result = engine_with_mixed_prefixes._validate_id_prefixes()
        assert len(result) > 0
        for violation in result:
            assert len(violation.samples) > 0
            for sample in violation.samples:
                assert isinstance(sample, ViolationSample)
                # Sample should have ID and prefix
                assert len(sample.values) >= 1

    # Tests for _build_category_prefix_map

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_build_category_prefix_map_returns_dict(self, engine_with_mixed_prefixes):
        """Test that _build_category_prefix_map returns a dict."""
        result = engine_with_mixed_prefixes._build_category_prefix_map()
        assert isinstance(result, dict)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_build_category_prefix_map_maps_category_to_prefixes(self, engine_with_mixed_prefixes):
        """Test that _build_category_prefix_map maps category to (prefixes, is_closed) tuple."""
        result = engine_with_mixed_prefixes._build_category_prefix_map()
        # Should have Gene and Disease mappings
        assert "biolink:Gene" in result
        prefixes, is_closed = result["biolink:Gene"]
        assert isinstance(prefixes, list)
        assert isinstance(is_closed, bool)
        assert "HGNC" in prefixes

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_build_category_prefix_map_empty_when_no_schema(self, engine_no_prefixes):
        """Test that _build_category_prefix_map returns empty dict when no schema."""
        result = engine_no_prefixes._build_category_prefix_map()
        assert result == {}


class TestPredicateHierarchyValidation:
    """Test ValidationEngine._validate_predicate_hierarchy method."""

    @pytest.fixture
    def db_with_invalid_hierarchy_predicates(self):
        """Create a GraphDatabase with edges having predicates not in Biolink slot hierarchy."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'node2', 'biolink:related_to', 'node3'),
            ('edge3', 'node3', 'biolink:not_a_real_predicate', 'node1'),
            ('edge4', 'node1', 'biolink:totally_fake_relation', 'node3'),
            ('edge5', 'node2', 'biolink:not_a_real_predicate', 'node1')
        """)
        yield db
        db.close()

    @pytest.fixture
    def db_with_valid_hierarchy_predicates(self):
        """Create a GraphDatabase with all predicates in Biolink slot hierarchy."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'node2', 'biolink:related_to', 'node3')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_invalid_hierarchy_predicates(self, db_with_invalid_hierarchy_predicates):
        """Create a ValidationEngine with predicates not in hierarchy."""
        mock_parser = MagicMock(spec=SchemaParser)
        # Return a set of valid predicates from hierarchy (includes subproperty_of relationships)
        mock_parser.get_all_valid_predicates_with_hierarchy.return_value = {
            "biolink:related_to",
            "biolink:interacts_with",
            "biolink:causes",
            "biolink:treats",
            "biolink:affects",
        }
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="association",
            table_mapping="edges",
            slots={},
        )
        return ValidationEngine(database=db_with_invalid_hierarchy_predicates, schema_parser=mock_parser)

    @pytest.fixture
    def engine_with_valid_hierarchy_predicates(self, db_with_valid_hierarchy_predicates):
        """Create a ValidationEngine with all predicates in hierarchy."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.get_all_valid_predicates_with_hierarchy.return_value = {
            "biolink:related_to",
            "biolink:interacts_with",
            "biolink:causes",
            "biolink:treats",
        }
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="association",
            table_mapping="edges",
            slots={},
        )
        return ValidationEngine(database=db_with_valid_hierarchy_predicates, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicate_hierarchy_returns_list(self, engine_with_invalid_hierarchy_predicates):
        """Test that _validate_predicate_hierarchy returns a list."""
        result = engine_with_invalid_hierarchy_predicates._validate_predicate_hierarchy()
        assert isinstance(result, list)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicate_hierarchy_returns_empty_when_all_valid(self, engine_with_valid_hierarchy_predicates):
        """Test that _validate_predicate_hierarchy returns empty list when all predicates in hierarchy."""
        result = engine_with_valid_hierarchy_predicates._validate_predicate_hierarchy()
        assert result == []

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicate_hierarchy_detects_invalid_predicates(self, engine_with_invalid_hierarchy_predicates):
        """Test that _validate_predicate_hierarchy detects predicates not in Biolink slot hierarchy."""
        result = engine_with_invalid_hierarchy_predicates._validate_predicate_hierarchy()
        assert len(result) == 1
        # Should find 3 violations (edge3, edge4, edge5)
        assert result[0].violation_count == 3

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicate_hierarchy_has_invalid_subproperty_constraint_type(self, engine_with_invalid_hierarchy_predicates):
        """Test that violations have constraint_type=ConstraintType.INVALID_SUBPROPERTY."""
        result = engine_with_invalid_hierarchy_predicates._validate_predicate_hierarchy()
        assert len(result) == 1
        assert result[0].constraint_type == ConstraintType.INVALID_SUBPROPERTY

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicate_hierarchy_has_warning_severity(self, engine_with_invalid_hierarchy_predicates):
        """Test that violations have severity='warning'."""
        result = engine_with_invalid_hierarchy_predicates._validate_predicate_hierarchy()
        assert len(result) == 1
        assert result[0].severity == "warning"

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicate_hierarchy_includes_samples_with_counts(self, engine_with_invalid_hierarchy_predicates):
        """Test that violations include samples showing invalid predicate values with counts."""
        result = engine_with_invalid_hierarchy_predicates._validate_predicate_hierarchy()
        assert len(result) == 1
        assert len(result[0].samples) > 0
        # Check samples have the invalid predicates with counts
        sample_dict = {s.values[0]: s.count for s in result[0].samples}
        # biolink:not_a_real_predicate appears twice, biolink:totally_fake_relation appears once
        assert sample_dict.get("biolink:not_a_real_predicate") == 2
        assert sample_dict.get("biolink:totally_fake_relation") == 1


class TestBiolinkPredicateValidation:
    """Test ValidationEngine._validate_predicates method."""

    @pytest.fixture
    def db_with_invalid_predicates(self):
        """Create a GraphDatabase with edges having invalid predicates."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'node2', 'biolink:related_to', 'node3'),
            ('edge3', 'node3', 'biolink:invalid_predicate', 'node1'),
            ('edge4', 'node1', 'biolink:made_up_relation', 'node3'),
            ('edge5', 'node2', 'biolink:invalid_predicate', 'node1')
        """)
        yield db
        db.close()

    @pytest.fixture
    def db_with_valid_predicates(self):
        """Create a GraphDatabase with all valid predicates."""
        db = GraphDatabase()
        db.conn.execute("""
            CREATE TABLE edges (
                id VARCHAR,
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR
            )
        """)
        db.conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'node2', 'biolink:related_to', 'node3')
        """)
        yield db
        db.close()

    @pytest.fixture
    def engine_with_invalid_predicates(self, db_with_invalid_predicates):
        """Create a ValidationEngine with invalid predicates."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.get_valid_predicates.return_value = {
            "biolink:related_to",
            "biolink:interacts_with",
            "biolink:causes",
            "biolink:treats",
        }
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="association",
            table_mapping="edges",
            slots={},
        )
        return ValidationEngine(database=db_with_invalid_predicates, schema_parser=mock_parser)

    @pytest.fixture
    def engine_with_valid_predicates(self, db_with_valid_predicates):
        """Create a ValidationEngine with all valid predicates."""
        mock_parser = MagicMock(spec=SchemaParser)
        mock_parser.get_valid_predicates.return_value = {
            "biolink:related_to",
            "biolink:interacts_with",
            "biolink:causes",
            "biolink:treats",
        }
        mock_parser.get_class_constraints.return_value = ClassConstraints(
            class_name="association",
            table_mapping="edges",
            slots={},
        )
        return ValidationEngine(database=db_with_valid_predicates, schema_parser=mock_parser)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicates_returns_list(self, engine_with_invalid_predicates):
        """Test that _validate_predicates returns a list."""
        result = engine_with_invalid_predicates._validate_predicates()
        assert isinstance(result, list)

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicates_returns_empty_when_all_valid(self, engine_with_valid_predicates):
        """Test that _validate_predicates returns empty list when all predicates valid."""
        result = engine_with_valid_predicates._validate_predicates()
        assert result == []

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicates_detects_invalid_predicates(self, engine_with_invalid_predicates):
        """Test that _validate_predicates detects invalid predicates."""
        result = engine_with_invalid_predicates._validate_predicates()
        assert len(result) == 1
        # Should find 3 violations (edge3, edge4, edge5)
        assert result[0].violation_count == 3

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicates_has_enum_constraint_type(self, engine_with_invalid_predicates):
        """Test that violations have constraint_type=ConstraintType.ENUM."""
        result = engine_with_invalid_predicates._validate_predicates()
        assert len(result) == 1
        assert result[0].constraint_type == ConstraintType.ENUM

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicates_has_warning_severity(self, engine_with_invalid_predicates):
        """Test that violations have severity='warning'."""
        result = engine_with_invalid_predicates._validate_predicates()
        assert len(result) == 1
        assert result[0].severity == "warning"

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_predicates_includes_samples_with_counts(self, engine_with_invalid_predicates):
        """Test that violations include samples showing invalid values with counts."""
        result = engine_with_invalid_predicates._validate_predicates()
        assert len(result) == 1
        assert len(result[0].samples) > 0
        # Check samples have the invalid predicates with counts
        sample_dict = {s.values[0]: s.count for s in result[0].samples}
        # biolink:invalid_predicate appears twice, biolink:made_up_relation appears once
        assert sample_dict.get("biolink:invalid_predicate") == 2
        assert sample_dict.get("biolink:made_up_relation") == 1


class TestViolationSamplePydanticModel:
    """Test ViolationSampleModel Pydantic model."""

    def test_violation_sample_model_is_pydantic_base_model(self):
        """Test that ViolationSampleModel is a Pydantic BaseModel."""
        from koza.model.graph_operations import ViolationSampleModel
        from pydantic import BaseModel
        assert issubclass(ViolationSampleModel, BaseModel)

    def test_violation_sample_model_creation_with_defaults(self):
        """Test creating ViolationSampleModel with default values."""
        from koza.model.graph_operations import ViolationSampleModel
        sample = ViolationSampleModel()
        assert sample.values == []
        assert sample.count == 0

    def test_violation_sample_model_creation_with_values(self):
        """Test creating ViolationSampleModel with provided values."""
        from koza.model.graph_operations import ViolationSampleModel
        sample = ViolationSampleModel(
            values=["invalid_id_1", "invalid_id_2"],
            count=2,
        )
        assert sample.values == ["invalid_id_1", "invalid_id_2"]
        assert sample.count == 2

    def test_violation_sample_model_json_serialization(self):
        """Test that ViolationSampleModel can be serialized to JSON."""
        from koza.model.graph_operations import ViolationSampleModel
        sample = ViolationSampleModel(values=["test"], count=1)
        json_data = sample.model_dump_json()
        assert '"values"' in json_data
        assert '"count"' in json_data


class TestValidationViolationPydanticModel:
    """Test ValidationViolationModel Pydantic model."""

    def test_validation_violation_model_is_pydantic_base_model(self):
        """Test that ValidationViolationModel is a Pydantic BaseModel."""
        from koza.model.graph_operations import ValidationViolationModel
        from pydantic import BaseModel
        assert issubclass(ValidationViolationModel, BaseModel)

    def test_validation_violation_model_creation(self):
        """Test creating ValidationViolationModel with required fields."""
        from koza.model.graph_operations import ValidationViolationModel, ViolationSampleModel
        sample = ViolationSampleModel(values=["bad_id"], count=1)
        violation = ValidationViolationModel(
            constraint_type="REQUIRED",
            slot_name="id",
            table="nodes",
            severity="error",
            description="Missing required field 'id'",
            violation_count=100,
            total_records=1000,
            violation_percentage=10.0,
            samples=[sample],
        )
        assert violation.constraint_type == "REQUIRED"
        assert violation.slot_name == "id"
        assert violation.table == "nodes"
        assert violation.severity == "error"
        assert violation.description == "Missing required field 'id'"
        assert violation.violation_count == 100
        assert violation.total_records == 1000
        assert violation.violation_percentage == 10.0
        assert len(violation.samples) == 1

    def test_validation_violation_model_default_samples(self):
        """Test ValidationViolationModel with default empty samples."""
        from koza.model.graph_operations import ValidationViolationModel
        violation = ValidationViolationModel(
            constraint_type="PATTERN",
            slot_name="category",
            table="nodes",
            severity="warning",
            description="Category does not match pattern",
            violation_count=50,
            total_records=500,
            violation_percentage=10.0,
        )
        assert violation.samples == []

    def test_validation_violation_model_json_serialization(self):
        """Test that ValidationViolationModel can be serialized to JSON."""
        from koza.model.graph_operations import ValidationViolationModel
        violation = ValidationViolationModel(
            constraint_type="REQUIRED",
            slot_name="id",
            table="nodes",
            severity="error",
            description="Test",
            violation_count=1,
            total_records=10,
            violation_percentage=10.0,
        )
        json_data = violation.model_dump_json()
        assert '"constraint_type"' in json_data
        assert '"slot_name"' in json_data


class TestValidationReportPydanticModel:
    """Test ValidationReportModel Pydantic model."""

    def test_validation_report_model_is_pydantic_base_model(self):
        """Test that ValidationReportModel is a Pydantic BaseModel."""
        from koza.model.graph_operations import ValidationReportModel
        from pydantic import BaseModel
        assert issubclass(ValidationReportModel, BaseModel)

    def test_validation_report_model_creation_with_defaults(self):
        """Test creating ValidationReportModel with default values."""
        from koza.model.graph_operations import ValidationReportModel
        report = ValidationReportModel()
        assert report.violations == []
        assert report.total_violations == 0
        assert report.error_count == 0
        assert report.warning_count == 0
        assert report.info_count == 0
        assert report.compliance_percentage == 100.0
        assert report.tables_validated == []
        assert report.constraints_checked == 0

    def test_validation_report_model_with_violations(self):
        """Test ValidationReportModel with violations."""
        from koza.model.graph_operations import ValidationReportModel, ValidationViolationModel
        violation = ValidationViolationModel(
            constraint_type="REQUIRED",
            slot_name="id",
            table="nodes",
            severity="error",
            description="Missing required field 'id'",
            violation_count=100,
            total_records=1000,
            violation_percentage=10.0,
        )
        report = ValidationReportModel(
            violations=[violation],
            total_violations=100,
            error_count=100,
            warning_count=0,
            info_count=0,
            compliance_percentage=90.0,
            tables_validated=["nodes"],
            constraints_checked=5,
        )
        assert len(report.violations) == 1
        assert report.total_violations == 100
        assert report.error_count == 100

    def test_validation_report_model_json_serialization(self):
        """Test that ValidationReportModel can be serialized to JSON."""
        from koza.model.graph_operations import ValidationReportModel
        report = ValidationReportModel(
            tables_validated=["nodes", "edges"],
            constraints_checked=10,
        )
        json_data = report.model_dump_json()
        assert '"violations"' in json_data
        assert '"total_violations"' in json_data


class TestValidationConfigPydanticModel:
    """Test ValidationConfig Pydantic model."""

    def test_validation_config_is_pydantic_base_model(self):
        """Test that ValidationConfig is a Pydantic BaseModel."""
        from koza.model.graph_operations import ValidationConfig
        from pydantic import BaseModel
        assert issubclass(ValidationConfig, BaseModel)

    def test_validation_config_creation_with_required_fields(self):
        """Test creating ValidationConfig with required database_path."""
        from pathlib import Path
        from koza.model.graph_operations import ValidationConfig
        config = ValidationConfig(database_path=Path("/tmp/test.db"))
        assert config.database_path == Path("/tmp/test.db")

    def test_validation_config_default_values(self):
        """Test ValidationConfig default values."""
        from pathlib import Path
        from koza.model.graph_operations import ValidationConfig
        config = ValidationConfig(database_path=Path("/tmp/test.db"))
        assert config.output_file is None
        assert config.schema_path is None
        assert config.sample_limit == 10
        assert config.include_warnings is True
        assert config.include_info is False
        assert config.quiet is False

    def test_validation_config_with_all_fields(self):
        """Test ValidationConfig with all fields specified."""
        from pathlib import Path
        from koza.model.graph_operations import ValidationConfig
        config = ValidationConfig(
            database_path=Path("/tmp/test.db"),
            output_file=Path("/tmp/report.json"),
            schema_path="custom_schema.yaml",
            sample_limit=20,
            include_warnings=False,
            include_info=True,
            quiet=True,
        )
        assert config.database_path == Path("/tmp/test.db")
        assert config.output_file == Path("/tmp/report.json")
        assert config.schema_path == "custom_schema.yaml"
        assert config.sample_limit == 20
        assert config.include_warnings is False
        assert config.include_info is True
        assert config.quiet is True

    def test_validation_config_json_serialization(self):
        """Test that ValidationConfig can be serialized to JSON."""
        from pathlib import Path
        from koza.model.graph_operations import ValidationConfig
        config = ValidationConfig(database_path=Path("/tmp/test.db"))
        json_data = config.model_dump_json()
        assert '"database_path"' in json_data
        assert '"sample_limit"' in json_data


class TestValidationResultPydanticModel:
    """Test ValidationResult Pydantic model."""

    def test_validation_result_is_pydantic_base_model(self):
        """Test that ValidationResult is a Pydantic BaseModel."""
        from koza.model.graph_operations import ValidationResult
        from pydantic import BaseModel
        assert issubclass(ValidationResult, BaseModel)

    def test_validation_result_creation(self):
        """Test creating ValidationResult with required validation_report."""
        from koza.model.graph_operations import ValidationResult, ValidationReportModel
        report = ValidationReportModel()
        result = ValidationResult(validation_report=report)
        assert result.validation_report == report

    def test_validation_result_default_values(self):
        """Test ValidationResult default values."""
        from koza.model.graph_operations import ValidationResult, ValidationReportModel
        report = ValidationReportModel()
        result = ValidationResult(validation_report=report)
        assert result.output_file is None
        assert result.total_time_seconds == 0.0

    def test_validation_result_with_all_fields(self):
        """Test ValidationResult with all fields specified."""
        from pathlib import Path
        from koza.model.graph_operations import ValidationResult, ValidationReportModel
        report = ValidationReportModel(
            total_violations=5,
            compliance_percentage=95.0,
        )
        result = ValidationResult(
            validation_report=report,
            output_file=Path("/tmp/report.json"),
            total_time_seconds=1.5,
        )
        assert result.validation_report.total_violations == 5
        assert result.validation_report.compliance_percentage == 95.0
        assert result.output_file == Path("/tmp/report.json")
        assert result.total_time_seconds == 1.5

    def test_validation_result_json_serialization(self):
        """Test that ValidationResult can be serialized to JSON."""
        from koza.model.graph_operations import ValidationResult, ValidationReportModel
        report = ValidationReportModel()
        result = ValidationResult(validation_report=report, total_time_seconds=2.5)
        json_data = result.model_dump_json()
        assert '"validation_report"' in json_data
        assert '"total_time_seconds"' in json_data


class TestValidateCLI:
    """Test validate CLI command and related functions."""

    # Test that validate_graph function exists

    def test_validate_graph_function_exists(self):
        """Test that validate_graph function exists in graph_operations module."""
        from koza.graph_operations import validate_graph
        assert callable(validate_graph)

    def test_validate_graph_accepts_validation_config(self):
        """Test that validate_graph accepts a ValidationConfig parameter."""
        import inspect
        from koza.graph_operations import validate_graph
        sig = inspect.signature(validate_graph)
        assert "config" in sig.parameters

    def test_validate_graph_returns_validation_result(self, tmp_path):
        """Test that validate_graph returns a ValidationResult."""
        from koza.graph_operations import validate_graph
        from koza.model.graph_operations import ValidationConfig, ValidationResult
        import duckdb

        # Create a proper duckdb file directly
        temp_db_path = tmp_path / "test.duckdb"
        conn = duckdb.connect(str(temp_db_path))
        conn.execute("""
            CREATE TABLE nodes (id VARCHAR, name VARCHAR, category VARCHAR)
        """)
        conn.execute("""
            INSERT INTO nodes VALUES ('node1', 'Test', 'biolink:Gene')
        """)
        conn.close()

        config = ValidationConfig(database_path=temp_db_path)
        result = validate_graph(config)
        assert isinstance(result, ValidationResult)

    # Test that it creates a ValidationEngine and runs validation

    @pytest.fixture
    def temp_db_with_data(self, tmp_path):
        """Create a temporary DuckDB database with test data."""
        import duckdb
        db_path = tmp_path / "test_validate.duckdb"
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE nodes (id VARCHAR, name VARCHAR, category VARCHAR)
        """)
        conn.execute("""
            INSERT INTO nodes VALUES
            ('node1', 'Gene A', 'biolink:Gene'),
            ('node2', NULL, 'biolink:Disease'),
            ('node3', 'Gene C', 'biolink:Gene')
        """)
        conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR)
        """)
        conn.execute("""
            INSERT INTO edges VALUES
            ('edge1', 'node1', 'biolink:interacts_with', 'node2'),
            ('edge2', 'orphan_subject', 'biolink:related_to', 'node3')
        """)
        conn.close()
        return db_path

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_graph_creates_engine_and_validates(self, temp_db_with_data):
        """Test that validate_graph creates a ValidationEngine and runs validation."""
        from koza.graph_operations import validate_graph
        from koza.model.graph_operations import ValidationConfig

        config = ValidationConfig(database_path=temp_db_with_data)
        result = validate_graph(config)

        # Should have run validation and found violations
        assert result.validation_report is not None
        assert result.validation_report.tables_validated == ["nodes", "edges"]

    # Test YAML output writing

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_graph_writes_yaml_output(self, temp_db_with_data, tmp_path):
        """Test that validate_graph writes YAML output when output_file is provided."""
        from koza.graph_operations import validate_graph
        from koza.model.graph_operations import ValidationConfig
        import yaml

        output_file = tmp_path / "validation_report.yaml"
        config = ValidationConfig(
            database_path=temp_db_with_data,
            output_file=output_file,
        )
        result = validate_graph(config)

        # Check output file was written
        assert output_file.exists()
        assert result.output_file == output_file

        # Check YAML content structure
        with open(output_file) as f:
            report_data = yaml.safe_load(f)

        assert "metadata" in report_data
        assert "summary" in report_data
        assert "violations" in report_data
        assert report_data["metadata"]["database"] == str(temp_db_with_data)

    # Test filtering warnings when errors_only

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_graph_filters_warnings_when_errors_only(self, temp_db_with_data):
        """Test that validate_graph filters out warnings when include_warnings=False."""
        from koza.graph_operations import validate_graph
        from koza.model.graph_operations import ValidationConfig

        # Run with warnings included
        config_with_warnings = ValidationConfig(
            database_path=temp_db_with_data,
            include_warnings=True,
        )
        result_with_warnings = validate_graph(config_with_warnings)

        # Run without warnings
        config_errors_only = ValidationConfig(
            database_path=temp_db_with_data,
            include_warnings=False,
        )
        result_errors_only = validate_graph(config_errors_only)

        # Errors-only should have no warning violations
        for v in result_errors_only.validation_report.violations:
            assert v.severity != "warning"

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_graph_filters_info_by_default(self, temp_db_with_data):
        """Test that validate_graph filters out info severity by default."""
        from koza.graph_operations import validate_graph
        from koza.model.graph_operations import ValidationConfig

        config = ValidationConfig(
            database_path=temp_db_with_data,
            include_info=False,  # default
        )
        result = validate_graph(config)

        # Should have no info violations
        for v in result.validation_report.violations:
            assert v.severity != "info"

    # Test total_time_seconds is populated

    @pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB not installed")
    def test_validate_graph_sets_total_time(self, temp_db_with_data):
        """Test that validate_graph sets total_time_seconds in result."""
        from koza.graph_operations import validate_graph
        from koza.model.graph_operations import ValidationConfig

        config = ValidationConfig(database_path=temp_db_with_data)
        result = validate_graph(config)

        assert result.total_time_seconds > 0


class TestPrintValidationSummary:
    """Test _print_validation_summary helper function."""

    def test_print_validation_summary_exists_in_main(self):
        """Test that _print_validation_summary function exists in main module."""
        from koza.main import _print_validation_summary
        assert callable(_print_validation_summary)

    def test_print_validation_summary_accepts_validation_result(self):
        """Test that _print_validation_summary accepts a ValidationResult parameter."""
        import inspect
        from koza.main import _print_validation_summary
        sig = inspect.signature(_print_validation_summary)
        assert "result" in sig.parameters

    def test_print_validation_summary_outputs_to_console(self, capsys):
        """Test that _print_validation_summary prints to console."""
        from koza.main import _print_validation_summary
        from koza.model.graph_operations import ValidationResult, ValidationReportModel

        report = ValidationReportModel(
            compliance_percentage=95.0,
            error_count=5,
            warning_count=10,
            tables_validated=["nodes", "edges"],
        )
        result = ValidationResult(validation_report=report)

        _print_validation_summary(result)

        captured = capsys.readouterr()
        assert "Compliance:" in captured.out or "compliance" in captured.out.lower()
        assert "Errors:" in captured.out or "5" in captured.out
        assert "Warnings:" in captured.out or "10" in captured.out

    def test_print_validation_summary_shows_top_violations(self, capsys):
        """Test that _print_validation_summary shows top violations."""
        from koza.main import _print_validation_summary
        from koza.model.graph_operations import (
            ValidationResult,
            ValidationReportModel,
            ValidationViolationModel,
        )

        violation = ValidationViolationModel(
            constraint_type="REQUIRED",
            slot_name="name",
            table="nodes",
            severity="error",
            description="Missing required field",
            violation_count=100,
            total_records=1000,
            violation_percentage=10.0,
        )
        report = ValidationReportModel(
            violations=[violation],
            compliance_percentage=90.0,
            error_count=100,
            warning_count=0,
            tables_validated=["nodes"],
        )
        result = ValidationResult(validation_report=report)

        _print_validation_summary(result)

        captured = capsys.readouterr()
        # Should mention the violation slot name and count
        assert "name" in captured.out or "100" in captured.out


class TestValidateCLICommand:
    """Test the validate CLI command in main.py."""

    def test_validate_command_exists(self):
        """Test that validate command exists in typer_app."""
        from koza.main import typer_app
        # Get command names from the typer app's registered commands
        # Commands may have callback attributes with __name__
        command_names = []
        for cmd in typer_app.registered_commands:
            if hasattr(cmd, "callback") and cmd.callback is not None:
                command_names.append(cmd.callback.__name__)
            elif hasattr(cmd, "name") and cmd.name is not None:
                command_names.append(cmd.name)
        assert "validate" in command_names


if __name__ == "__main__":
    pytest.main([__file__])
