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
from koza.graph_operations.utils import GraphDatabase


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
        assert "📋 Schema Analysis:" in captured.out
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
        assert "⚠️  Schema analysis failed: Failed to analyze schema: No data found" in captured.out

    def test_print_schema_summary_missing_summary(self, capsys):
        """Test printing schema summary with missing summary section."""
        incomplete_report = {"files": [{"filename": "test.tsv", "table_type": "nodes", "column_count": 4}]}

        print_schema_summary(incomplete_report)

        captured = capsys.readouterr()
        assert "📋 Schema Analysis:" in captured.out

    def test_print_schema_summary_exception_handling(self, capsys):
        """Test handling exceptions during schema summary printing."""
        # Pass invalid data that will cause exception
        invalid_report = {"files": [{"invalid": "data"}]}

        print_schema_summary(invalid_report)

        captured = capsys.readouterr()
        assert "⚠️  Schema summary failed:" in captured.out


class TestAnalyzeBiolinkCompliance:
    """Test biolink compliance analysis."""

    def test_analyze_biolink_compliance_placeholder(self, sample_schema_report):
        """Test biolink compliance analysis placeholder."""
        result = analyze_biolink_compliance(sample_schema_report)

        assert result["status"] == "not_implemented"
        assert "Phase 1" in result["message"]

    def test_analyze_biolink_compliance_with_empty_report(self):
        """Test biolink compliance analysis with empty schema report."""
        empty_report = {}

        result = analyze_biolink_compliance(empty_report)

        assert result["status"] == "not_implemented"

    def test_analyze_biolink_compliance_with_error_report(self):
        """Test biolink compliance analysis with error in schema report."""
        error_report = {"error": "Schema analysis failed"}

        result = analyze_biolink_compliance(error_report)

        assert result["status"] == "not_implemented"


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


if __name__ == "__main__":
    pytest.main([__file__])
