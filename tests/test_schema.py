"""
Test suite for schema analysis and management operations.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from koza.graph_operations.schema import (
    analyze_biolink_compliance,
    generate_schema_report,
    print_schema_summary,
    write_schema_report_yaml,
)
from koza.graph_operations.report import generate_schema_compliance_report
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import SchemaReportConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_schema_report():
    """Create a sample schema report for testing."""
    return {
        "summary": {
            "nodes": {"file_count": 2, "unique_columns": 5, "total_records": 1000},
            "edges": {"file_count": 1, "unique_columns": 4, "total_records": 500},
        },
        "files": [
            {
                "filename": "nodes1.tsv",
                "table_type": "nodes",
                "column_count": 4,
                "columns": ["id", "category", "name", "description"],
                "sample_data": [
                    {"id": "HGNC:123", "category": "biolink:Gene", "name": "gene1"},
                    {"id": "HGNC:456", "category": "biolink:Gene", "name": "gene2"},
                ],
            },
            {
                "filename": "nodes2.tsv",
                "table_type": "nodes",
                "column_count": 5,
                "columns": ["id", "category", "name", "description", "source"],
                "sample_data": [
                    {"id": "MONDO:001", "category": "biolink:Disease", "name": "disease1", "source": "mondo"}
                ],
            },
            {
                "filename": "edges.tsv",
                "table_type": "edges",
                "column_count": 4,
                "columns": ["subject", "predicate", "object", "category"],
                "sample_data": [{"subject": "HGNC:123", "predicate": "biolink:related_to", "object": "MONDO:001"}],
            },
        ],
        "column_analysis": {
            "nodes": {
                "common_columns": ["id", "category", "name"],
                "optional_columns": ["description", "source"],
                "missing_standard_columns": [],
            },
            "edges": {
                "common_columns": ["subject", "predicate", "object"],
                "optional_columns": ["category"],
                "missing_standard_columns": [],
            },
        },
    }


@pytest.fixture
def mock_database():
    """Create a mock GraphDatabase."""
    mock_db = MagicMock(spec=GraphDatabase)
    return mock_db


class TestGenerateSchemaReport:
    """Test schema report generation."""

    def test_generate_schema_report(self, mock_database, sample_schema_report):
        """Test generating schema report from database."""
        mock_database.get_schema_report.return_value = sample_schema_report

        result = generate_schema_report(mock_database)

        assert result == sample_schema_report
        mock_database.get_schema_report.assert_called_once()

    def test_generate_schema_report_with_database_error(self, mock_database):
        """Test handling database errors during schema report generation."""
        mock_database.get_schema_report.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            generate_schema_report(mock_database)


class TestWriteSchemaReportYaml:
    """Test writing schema reports to YAML files."""

    def test_write_schema_report_to_directory(self, sample_schema_report, temp_dir):
        """Test writing schema report to directory."""
        output_dir = temp_dir

        write_schema_report_yaml(sample_schema_report, output_dir, "test_operation")

        # Check that YAML file was created
        yaml_file = output_dir / "test_operation_schema_report.yaml"
        assert yaml_file.exists()

        # Verify content
        with open(yaml_file) as f:
            content = yaml.safe_load(f)

        assert content["metadata"]["operation"] == "test_operation"
        assert content["metadata"]["report_version"] == "1.0"
        assert content["schema_analysis"] == sample_schema_report
        assert "generated_at" in content["metadata"]

    def test_write_schema_report_with_database_path(self, sample_schema_report, temp_dir):
        """Test writing schema report using database file path."""
        db_path = temp_dir / "test.duckdb"
        db_path.touch()  # Create dummy database file

        write_schema_report_yaml(sample_schema_report, db_path, "join")

        # Check that YAML file was created with database name
        yaml_file = temp_dir / "test_schema_report.yaml"
        assert yaml_file.exists()

        # Verify content
        with open(yaml_file) as f:
            content = yaml.safe_load(f)

        assert content["metadata"]["operation"] == "join"
        assert content["schema_analysis"] == sample_schema_report

    def test_write_schema_report_default_operation(self, sample_schema_report, temp_dir):
        """Test writing schema report with default operation name."""
        output_dir = temp_dir

        write_schema_report_yaml(sample_schema_report, output_dir)

        # Check that YAML file was created with default name
        yaml_file = output_dir / "join_schema_report.yaml"
        assert yaml_file.exists()

        # Verify content
        with open(yaml_file) as f:
            content = yaml.safe_load(f)

        assert content["metadata"]["operation"] == "join"

    def test_write_schema_report_error_handling(self, sample_schema_report):
        """Test error handling when writing schema report fails."""
        # Try to write to invalid path
        invalid_path = Path("/invalid/path/that/doesnt/exist")

        # Should not raise exception, but log error
        write_schema_report_yaml(sample_schema_report, invalid_path, "test")


class TestPrintSchemaSummary:
    """Test schema summary printing."""

    def test_print_schema_summary_success(self, sample_schema_report, capsys):
        """Test printing successful schema summary."""
        print_schema_summary(sample_schema_report)

        captured = capsys.readouterr()
        assert "Schema Analysis:" in captured.out
        assert "Nodes: 2 files, 5 unique columns" in captured.out
        assert "Edges: 1 files, 4 unique columns" in captured.out
        assert "Schema variations: 2 different column structures detected" in captured.out

    def test_print_schema_summary_consistent_schemas(self, capsys):
        """Test printing summary with consistent schemas."""
        consistent_report = {
            "summary": {"nodes": {"file_count": 2, "unique_columns": 4}},
            "files": [
                {"filename": "file1.tsv", "table_type": "nodes", "column_count": 4},
                {"filename": "file2.tsv", "table_type": "nodes", "column_count": 4},
            ],
        }

        print_schema_summary(consistent_report)

        captured = capsys.readouterr()
        assert "Schema consistency: All files have matching column structures" in captured.out

    def test_print_schema_summary_with_multiple_variations(self, capsys):
        """Test printing summary with many schema variations."""
        many_variations_report = {
            "summary": {"nodes": {"file_count": 5, "unique_columns": 8}},
            "files": [
                {"filename": "file1.tsv", "table_type": "nodes", "column_count": 3},
                {"filename": "file2.tsv", "table_type": "nodes", "column_count": 4},
                {"filename": "file3.tsv", "table_type": "nodes", "column_count": 5},
                {"filename": "file4.tsv", "table_type": "nodes", "column_count": 6},
                {"filename": "file5.tsv", "table_type": "nodes", "column_count": 7},
            ],
        }

        print_schema_summary(many_variations_report)

        captured = capsys.readouterr()
        assert "Schema variations: 5 different column structures detected" in captured.out
        assert "... and 2 more variations" in captured.out

    def test_print_schema_summary_with_error(self, capsys):
        """Test printing schema summary when report contains error."""
        error_report = {"error": "Failed to analyze schema: No data found"}

        print_schema_summary(error_report)

        captured = capsys.readouterr()
        assert "Schema analysis failed: Failed to analyze schema: No data found" in captured.out

    def test_print_schema_summary_missing_summary(self, capsys):
        """Test printing schema summary with missing summary section."""
        incomplete_report = {"files": [{"filename": "test.tsv", "table_type": "nodes", "column_count": 4}]}

        print_schema_summary(incomplete_report)

        captured = capsys.readouterr()
        assert "Schema Analysis:" in captured.out

    def test_print_schema_summary_exception_handling(self, capsys):
        """Test handling exceptions during schema summary printing."""
        # Pass invalid data that will cause exception
        invalid_report = {"files": [{"invalid": "data"}]}

        print_schema_summary(invalid_report)

        captured = capsys.readouterr()
        assert "Schema summary failed:" in captured.out


class TestAnalyzeBiolinkCompliance:
    """Tests for analyze_biolink_compliance function using ValidationEngine."""

    @pytest.fixture
    def sample_database(self, temp_dir):
        """Create a minimal test database with nodes and edges tables."""
        db_path = temp_dir / "test.duckdb"
        with GraphDatabase(db_path) as db:
            db.conn.execute("""
                CREATE TABLE nodes (
                    id VARCHAR PRIMARY KEY,
                    category VARCHAR,
                    name VARCHAR
                )
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
                INSERT INTO nodes VALUES
                ('HGNC:1234', 'biolink:Gene', 'BRCA1'),
                ('HGNC:5678', 'biolink:Gene', 'TP53')
            """)
            db.conn.execute("""
                INSERT INTO edges VALUES
                ('edge1', 'HGNC:1234', 'biolink:interacts_with', 'HGNC:5678')
            """)
        return db_path

    def test_returns_dict_with_required_keys(self, sample_database):
        """analyze_biolink_compliance should return dict with status, compliance_percentage, etc."""
        with GraphDatabase(sample_database, read_only=True) as db:
            result = analyze_biolink_compliance(db)

        assert isinstance(result, dict)
        assert "status" in result
        assert "compliance_percentage" in result
        assert "error_count" in result
        assert "warning_count" in result
        assert "violations" in result
        assert "tables_validated" in result

    def test_status_is_valid_value(self, sample_database):
        """Status should be one of: passed, failed, warnings, error."""
        with GraphDatabase(sample_database, read_only=True) as db:
            result = analyze_biolink_compliance(db)

        assert result["status"] in ["passed", "failed", "warnings", "error"]

    def test_tables_validated_includes_nodes_and_edges(self, sample_database):
        """Should validate both nodes and edges tables."""
        with GraphDatabase(sample_database, read_only=True) as db:
            result = analyze_biolink_compliance(db)

        assert "nodes" in result["tables_validated"]
        assert "edges" in result["tables_validated"]

    def test_violations_is_list(self, sample_database):
        """Violations should be a list of dicts."""
        with GraphDatabase(sample_database, read_only=True) as db:
            result = analyze_biolink_compliance(db)

        assert isinstance(result["violations"], list)

    def test_handles_empty_database(self, temp_dir):
        """Should handle database with empty tables gracefully."""
        db_path = temp_dir / "empty.duckdb"
        with GraphDatabase(db_path) as db:
            db.conn.execute("CREATE TABLE nodes (id VARCHAR)")
            db.conn.execute("CREATE TABLE edges (id VARCHAR)")

        with GraphDatabase(db_path, read_only=True) as db:
            result = analyze_biolink_compliance(db)

        assert result["status"] in ["passed", "failed", "warnings", "error"]
        assert isinstance(result["violations"], list)

    def test_compliance_percentage_is_number(self, sample_database):
        """Compliance percentage should be a number when analysis succeeds."""
        with GraphDatabase(sample_database, read_only=True) as db:
            result = analyze_biolink_compliance(db)

        if result["status"] != "error":
            assert isinstance(result["compliance_percentage"], (int, float))
            assert 0 <= result["compliance_percentage"] <= 100

    def test_accepts_optional_schema_path(self, sample_database):
        """analyze_biolink_compliance should accept optional schema_path parameter."""
        with GraphDatabase(sample_database, read_only=True) as db:
            # Should not raise when schema_path is passed
            result = analyze_biolink_compliance(db, schema_path=None)

        assert isinstance(result, dict)

    def test_accepts_optional_sample_limit(self, sample_database):
        """analyze_biolink_compliance should accept optional sample_limit parameter."""
        with GraphDatabase(sample_database, read_only=True) as db:
            # Should not raise when sample_limit is passed
            result = analyze_biolink_compliance(db, sample_limit=5)

        assert isinstance(result, dict)


class TestSchemaIntegration:
    """Test integration scenarios for schema operations."""

    @patch("koza.graph_operations.schema.GraphDatabase")
    def test_full_schema_workflow(self, mock_db_class, sample_schema_report, temp_dir):
        """Test complete schema analysis workflow."""
        # Setup mock database
        mock_db = MagicMock()
        mock_db.get_schema_report.return_value = sample_schema_report
        mock_db_class.return_value.__enter__.return_value = mock_db

        # Generate report
        report = generate_schema_report(mock_db)

        # Write to YAML
        write_schema_report_yaml(report, temp_dir, "test_workflow")

        # Verify YAML file exists and contains expected data
        yaml_file = temp_dir / "test_workflow_schema_report.yaml"
        assert yaml_file.exists()

        with open(yaml_file) as f:
            content = yaml.safe_load(f)

        assert content["metadata"]["operation"] == "test_workflow"
        assert content["schema_analysis"] == sample_schema_report

    def test_schema_operations_with_minimal_data(self, temp_dir):
        """Test schema operations with minimal data."""
        minimal_report = {
            "summary": {"nodes": {"file_count": 1, "unique_columns": 2}},
            "files": [{"filename": "minimal.tsv", "table_type": "nodes", "column_count": 2}],
        }

        # Should handle minimal data gracefully
        write_schema_report_yaml(minimal_report, temp_dir)

        yaml_file = temp_dir / "join_schema_report.yaml"
        assert yaml_file.exists()

    def test_schema_operations_with_large_data(self, temp_dir):
        """Test schema operations with large amounts of data."""
        # Create large schema report
        large_report = {
            "summary": {"nodes": {"file_count": 100, "unique_columns": 50}},
            "files": [
                {"filename": f"file_{i}.tsv", "table_type": "nodes", "column_count": i % 10 + 3} for i in range(100)
            ],
        }

        # Should handle large data efficiently
        write_schema_report_yaml(large_report, temp_dir, "large_test")

        yaml_file = temp_dir / "large_test_schema_report.yaml"
        assert yaml_file.exists()


class TestSchemaYamlFormat:
    """Test YAML format and structure."""

    def test_yaml_format_structure(self, sample_schema_report, temp_dir):
        """Test that generated YAML has correct structure."""
        write_schema_report_yaml(sample_schema_report, temp_dir, "format_test")

        yaml_file = temp_dir / "format_test_schema_report.yaml"

        with open(yaml_file) as f:
            content = yaml.safe_load(f)

        # Check top-level structure
        assert "metadata" in content
        assert "schema_analysis" in content

        # Check metadata structure
        metadata = content["metadata"]
        assert "operation" in metadata
        assert "generated_at" in metadata
        assert "report_version" in metadata

        # Check that schema_analysis matches original
        assert content["schema_analysis"] == sample_schema_report

    def test_yaml_format_readability(self, sample_schema_report, temp_dir):
        """Test that generated YAML is human-readable."""
        write_schema_report_yaml(sample_schema_report, temp_dir, "readable_test")

        yaml_file = temp_dir / "readable_test_schema_report.yaml"

        # Read as text to check formatting
        with open(yaml_file) as f:
            yaml_text = f.read()

        # Should not be flow style (compact)
        assert "{" not in yaml_text[:100]  # Flow style uses braces
        assert "metadata:" in yaml_text
        assert "schema_analysis:" in yaml_text


class TestSchemaComplianceReportIntegration:
    """Tests for schema compliance report with biolink compliance integration."""

    @pytest.fixture
    def sample_database(self, temp_dir):
        """Create a minimal test database."""
        db_path = temp_dir / "test.duckdb"
        with GraphDatabase(db_path) as db:
            db.conn.execute("""
                CREATE TABLE nodes (
                    id VARCHAR PRIMARY KEY,
                    category VARCHAR,
                    name VARCHAR
                )
            """)
            db.conn.execute("""
                CREATE TABLE edges (
                    id VARCHAR,
                    subject VARCHAR,
                    predicate VARCHAR,
                    object VARCHAR
                )
            """)
            db.conn.execute("INSERT INTO nodes VALUES ('HGNC:1234', 'biolink:Gene', 'BRCA1')")
            db.conn.execute("INSERT INTO edges VALUES ('edge1', 'HGNC:1234', 'biolink:related_to', 'HGNC:5678')")
        return db_path

    def test_biolink_compliance_not_placeholder(self, sample_database):
        """Biolink compliance should NOT be 'not_implemented'."""
        config = SchemaReportConfig(database_path=sample_database, quiet=True)
        result = generate_schema_compliance_report(config)

        assert result.schema_report.biolink_compliance.status != "not_implemented"

    def test_biolink_compliance_has_valid_status(self, sample_database):
        """Biolink compliance status should be passed/failed/warnings/skipped/error."""
        config = SchemaReportConfig(database_path=sample_database, quiet=True)
        result = generate_schema_compliance_report(config)

        assert result.schema_report.biolink_compliance.status in [
            "passed", "failed", "warnings", "skipped", "error"
        ]

    def test_biolink_compliance_has_percentage(self, sample_database):
        """Biolink compliance should include compliance_percentage."""
        config = SchemaReportConfig(database_path=sample_database, quiet=True)
        result = generate_schema_compliance_report(config)

        # Should be a number (not None) when analysis runs
        bc = result.schema_report.biolink_compliance
        if bc.status not in ["skipped", "error"]:
            assert bc.compliance_percentage is not None
            assert isinstance(bc.compliance_percentage, (int, float))

    def test_biolink_compliance_skipped_when_disabled(self, sample_database):
        """Biolink compliance should be 'skipped' when include_biolink_compliance=False."""
        config = SchemaReportConfig(
            database_path=sample_database,
            include_biolink_compliance=False,
            quiet=True
        )
        result = generate_schema_compliance_report(config)

        assert result.schema_report.biolink_compliance.status == "skipped"

    def test_biolink_compliance_message_is_meaningful(self, sample_database):
        """Biolink compliance message should not contain 'Phase 1' placeholder text."""
        config = SchemaReportConfig(database_path=sample_database, quiet=True)
        result = generate_schema_compliance_report(config)

        message = result.schema_report.biolink_compliance.message
        assert "Phase 1" not in message
        assert "not_implemented" not in message.lower()


if __name__ == "__main__":
    pytest.main([__file__])
