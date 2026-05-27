"""
Test suite for split graph operation.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from koza.graph_operations import split_graph
from koza.model.graph_operations import FileSpec, KGXFileType, KGXFormat, SplitConfig, SplitResult


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_nodes_file(temp_dir):
    """Create a sample nodes TSV file with data suitable for splitting."""
    nodes_content = """id\tcategory\tname\tsource
HGNC:123\tbiolink:Gene\tgene1\thgnc
HGNC:456\tbiolink:Gene\tgene2\thgnc
MONDO:001\tbiolink:Disease\tdisease1\tmondo
MONDO:002\tbiolink:Disease\tdisease2\tmondo
CHEBI:111\tbiolink:ChemicalEntity\tchemical1\tchebi
"""
    nodes_file = temp_dir / "test_nodes.tsv"
    nodes_file.write_text(nodes_content)
    return nodes_file


@pytest.fixture
def sample_edges_file(temp_dir):
    """Create a sample edges TSV file with data suitable for splitting."""
    edges_content = """subject\tpredicate\tobject\tcategory\tsource
HGNC:123\tbiolink:related_to\tMONDO:001\tbiolink:Association\tstring
HGNC:456\tbiolink:causes\tMONDO:002\tbiolink:Association\tstring
CHEBI:111\tbiolink:interacts_with\tHGNC:123\tbiolink:Association\tctd
"""
    edges_file = temp_dir / "test_edges.tsv"
    edges_file.write_text(edges_content)
    return edges_file


class TestSplitOperation:
    """Test split operation functionality."""

    def test_split_nodes_by_category(self, sample_nodes_file, temp_dir):
        """Test splitting nodes file by category."""
        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
            remove_prefixes=False,
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)
        assert result.input_file == file_spec
        assert len(result.output_files) == 3  # Gene, Disease, ChemicalEntity
        assert result.total_records_split == 5
        assert len(result.split_values) == 3

        # Verify output files exist
        for output_file in result.output_files:
            assert output_file.exists()

        # Verify output directory was created
        assert output_dir.exists()

    def test_split_edges_by_source(self, sample_edges_file, temp_dir):
        """Test splitting edges file by source."""
        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=sample_edges_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)

        config = SplitConfig(
            input_file=file_spec, split_fields=["source"], output_directory=output_dir, quiet=True, show_progress=False
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)
        assert len(result.output_files) == 2  # string, ctd
        assert result.total_records_split == 3
        assert len(result.split_values) == 2

    def test_split_by_multiple_fields(self, sample_nodes_file, temp_dir):
        """Test splitting by multiple fields."""
        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category", "source"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)
        # Should have one file per unique category-source combination
        assert len(result.output_files) == 3  # 3 unique category-source combinations
        assert result.total_records_split == 5

    def test_split_with_format_conversion_to_jsonl(self, sample_nodes_file, temp_dir):
        """Test splitting with format conversion to JSONL."""
        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            output_format=KGXFormat.JSONL,
            quiet=True,
            show_progress=False,
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)

        # Verify all output files have .jsonl extension
        for output_file in result.output_files:
            assert output_file.suffix == ".jsonl"
            assert output_file.exists()

    def test_split_with_format_conversion_to_parquet(self, sample_nodes_file, temp_dir):
        """Test splitting with format conversion to Parquet."""
        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["source"],
            output_directory=output_dir,
            output_format=KGXFormat.PARQUET,
            quiet=True,
            show_progress=False,
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)

        # Verify all output files have .parquet extension
        for output_file in result.output_files:
            assert output_file.suffix == ".parquet"
            assert output_file.exists()

    def test_split_with_prefix_removal(self, temp_dir):
        """Test splitting with prefix removal in filenames."""
        # Create test file with prefixed values
        nodes_content = """id\tcategory\tname
HGNC:123\tbiolink:Gene\tgene1
MONDO:001\tbiolink:Disease\tdisease1
"""
        nodes_file = temp_dir / "test_nodes.tsv"
        nodes_file.write_text(nodes_content)

        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            remove_prefixes=True,
            quiet=True,
            show_progress=False,
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)

        # Check that filenames have prefixes removed
        filenames = [f.name for f in result.output_files]
        assert any("Gene_nodes.tsv" in name for name in filenames)
        assert any("Disease_nodes.tsv" in name for name in filenames)

    def test_split_nonexistent_file(self, temp_dir):
        """Test splitting nonexistent file."""
        nonexistent_file = temp_dir / "nonexistent.tsv"
        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=nonexistent_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
        )

        with pytest.raises(FileNotFoundError):
            split_graph(config)

    def test_split_empty_file(self, temp_dir):
        """Test splitting empty file."""
        empty_file = temp_dir / "empty.tsv"
        empty_file.write_text("")

        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=empty_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
        )

        # Should handle gracefully
        with pytest.raises(Exception):  # DuckDB will error on empty file
            split_graph(config)

    def test_split_header_only_file(self, temp_dir):
        """Test splitting file with only headers."""
        header_only_file = temp_dir / "header_only.tsv"
        header_only_file.write_text("id\tcategory\tname\n")

        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=header_only_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)
        assert len(result.output_files) == 0  # No data to split
        assert result.total_records_split == 0

    def test_split_with_null_values(self, temp_dir):
        """Test splitting with NULL values in split fields."""
        nodes_content = """id\tcategory\tname\tsource
HGNC:123\tbiolink:Gene\tgene1\thgnc
HGNC:456\t\tgene2\thgnc
MONDO:001\tbiolink:Disease\tdisease1\t
"""
        nodes_file = temp_dir / "test_nodes.tsv"
        nodes_file.write_text(nodes_content)

        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
        )

        result = split_graph(config)

        assert isinstance(result, SplitResult)
        # Should handle NULL/empty values
        assert len(result.output_files) >= 1
        assert result.total_records_split == 3


class TestSplitFilenameGeneration:
    """Test filename generation logic."""

    def test_filename_generation_basic(self, temp_dir):
        """Test basic filename generation."""
        from koza.graph_operations.split import _generate_filename

        original_path = temp_dir / "test_nodes.tsv"
        values_dict = {"category": "biolink:Gene"}

        filename = _generate_filename(original_path, values_dict, KGXFormat.TSV, remove_prefixes=False)

        assert filename == "test_Gene_nodes.tsv"

    def test_filename_generation_with_prefix_removal(self, temp_dir):
        """Test filename generation with prefix removal."""
        from koza.graph_operations.split import _generate_filename

        original_path = temp_dir / "test_edges.jsonl"
        values_dict = {"category": "biolink:Association"}

        filename = _generate_filename(original_path, values_dict, KGXFormat.JSONL, remove_prefixes=True)

        assert filename == "test_Association_edges.jsonl"

    def test_filename_generation_multiple_values(self, temp_dir):
        """Test filename generation with multiple split values."""
        from koza.graph_operations.split import _generate_filename

        original_path = temp_dir / "data.tsv"
        values_dict = {"category": "biolink:Gene", "source": "hgnc"}

        filename = _generate_filename(original_path, values_dict, KGXFormat.PARQUET, remove_prefixes=False)

        assert filename == "data_Gene_hgnc.parquet"

    def test_filename_generation_special_characters(self, temp_dir):
        """Test filename generation with special characters."""
        from koza.graph_operations.split import _generate_filename

        original_path = temp_dir / "test.tsv"
        values_dict = {"category": "biolink:Gene Product"}

        filename = _generate_filename(original_path, values_dict, KGXFormat.TSV, remove_prefixes=False)

        # Should replace spaces and special characters
        assert "Gene_Product" in filename
        assert filename.endswith(".tsv")


class TestSplitExportData:
    """Test data export functionality."""

    @patch("koza.graph_operations.split.GraphDatabase")
    def test_export_split_data_tsv(self, mock_db_class):
        """Test exporting split data to TSV format."""
        from koza.graph_operations.split import _export_split_data

        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db

        output_path = Path("/tmp/test.tsv")

        _export_split_data(mock_db, "nodes", "category = 'biolink:Gene'", output_path, KGXFormat.TSV)

        # Verify correct SQL was executed
        mock_db.conn.execute.assert_called_once()
        sql_call = mock_db.conn.execute.call_args[0][0]
        assert "COPY (" in sql_call
        assert "WHERE category = 'biolink:Gene'" in sql_call
        assert "HEADER, DELIMITER '\\t'" in sql_call

    @patch("koza.graph_operations.split.GraphDatabase")
    def test_export_split_data_jsonl(self, mock_db_class):
        """Test exporting split data to JSONL format."""
        from koza.graph_operations.split import _export_split_data

        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db

        output_path = Path("/tmp/test.jsonl")

        _export_split_data(mock_db, "edges", "source = 'string'", output_path, KGXFormat.JSONL)

        # Verify correct SQL was executed
        mock_db.conn.execute.assert_called_once()
        sql_call = mock_db.conn.execute.call_args[0][0]
        assert "FORMAT JSON" in sql_call

    @patch("koza.graph_operations.split.GraphDatabase")
    def test_export_split_data_parquet(self, mock_db_class):
        """Test exporting split data to Parquet format."""
        from koza.graph_operations.split import _export_split_data

        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db

        output_path = Path("/tmp/test.parquet")

        _export_split_data(mock_db, "nodes", "category = 'biolink:Disease'", output_path, KGXFormat.PARQUET)

        # Verify correct SQL was executed
        mock_db.conn.execute.assert_called_once()
        sql_call = mock_db.conn.execute.call_args[0][0]
        assert "FORMAT PARQUET" in sql_call


class TestSplitErrorHandling:
    """Test error handling in split operations."""

    def test_split_with_invalid_split_field(self, sample_nodes_file, temp_dir):
        """Test splitting with invalid split field."""
        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["nonexistent_field"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
        )

        with pytest.raises(Exception):  # DuckDB will error on invalid column
            split_graph(config)

    @patch("koza.graph_operations.split._export_split_data")
    def test_split_with_export_failure(self, mock_export, sample_nodes_file, temp_dir):
        """Test handling of export failures."""
        mock_export.side_effect = Exception("Export failed")

        output_dir = temp_dir / "split_output"

        file_spec = FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)

        config = SplitConfig(
            input_file=file_spec,
            split_fields=["category"],
            output_directory=output_dir,
            quiet=True,
            show_progress=False,
        )

        with pytest.raises(Exception):
            split_graph(config)


if __name__ == "__main__":
    pytest.main([__file__])
