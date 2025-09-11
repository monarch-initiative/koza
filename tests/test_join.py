"""
Test suite for join graph operation.
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import join_graphs, prepare_file_specs_from_paths
from koza.model.graph_operations import FileSpec, JoinConfig, KGXFileType, KGXFormat


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_nodes_file(temp_dir):
    """Create a sample nodes TSV file."""
    nodes_content = """id	category	name
HGNC:123	biolink:Gene	gene1
HGNC:456	biolink:Gene	gene2
MONDO:001	biolink:Disease	disease1
"""
    nodes_file = temp_dir / "nodes.tsv"
    nodes_file.write_text(nodes_content)
    return nodes_file


@pytest.fixture
def sample_edges_file(temp_dir):
    """Create a sample edges TSV file."""
    edges_content = """subject	predicate	object	category
HGNC:123	biolink:related_to	MONDO:001	biolink:Association
HGNC:456	biolink:causes	MONDO:001	biolink:Association
"""
    edges_file = temp_dir / "edges.tsv"
    edges_file.write_text(edges_content)
    return edges_file


@pytest.fixture
def sample_jsonl_file(temp_dir):
    """Create a sample nodes JSONL file."""
    jsonl_content = """{"id": "CHEBI:123", "category": "biolink:ChemicalEntity", "name": "chemical1"}
{"id": "CHEBI:456", "category": "biolink:ChemicalEntity", "name": "chemical2"}
"""
    jsonl_file = temp_dir / "nodes.jsonl"
    jsonl_file.write_text(jsonl_content)
    return jsonl_file


class TestJoinOperation:
    """Test join operation functionality."""

    def test_join_single_nodes_file(self, sample_nodes_file, temp_dir):
        """Test joining a single nodes file."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 3
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 0
        assert output_db.exists()

    def test_join_nodes_and_edges(self, sample_nodes_file, sample_edges_file, temp_dir):
        """Test joining both nodes and edges files."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[FileSpec(path=sample_edges_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 2
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 2
        assert output_db.exists()

    def test_join_multiple_formats(self, sample_nodes_file, sample_jsonl_file, temp_dir):
        """Test joining files of different formats."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[
                FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES),
                FileSpec(path=sample_jsonl_file, format=KGXFormat.JSONL, file_type=KGXFileType.NODES),
            ],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 2
        # Should have 3 TSV nodes + 2 JSONL nodes = 5 total
        assert result.final_stats.nodes == 5
        assert result.final_stats.edges == 0

    def test_join_in_memory_database(self, sample_nodes_file):
        """Test joining with in-memory database (no output file)."""
        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=None,  # In-memory
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.final_stats.nodes == 3
        assert result.database_path is None  # In-memory

    def test_join_with_schema_reporting(self, sample_nodes_file, sample_edges_file, temp_dir):
        """Test join operation with schema reporting enabled."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[FileSpec(path=sample_edges_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=True,
        )

        result = join_graphs(config)

        assert result is not None
        assert result.schema_report is not None
        assert len(result.schema_report) > 0
        # Should have generated schema report file
        schema_file = output_db.parent / f"{output_db.stem}_schema_report.yaml"
        assert schema_file.exists()

    def test_join_empty_files_list(self, temp_dir):
        """Test join with empty files lists."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        # Should complete but with empty results
        assert result is not None
        assert len(result.files_loaded) == 0
        assert result.final_stats.nodes == 0
        assert result.final_stats.edges == 0

    def test_join_nonexistent_file(self, temp_dir):
        """Test join with nonexistent file."""
        output_db = temp_dir / "output.duckdb"
        nonexistent_file = temp_dir / "nonexistent.tsv"

        config = JoinConfig(
            node_files=[FileSpec(path=nonexistent_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        # Should handle gracefully with errors
        assert result is not None
        assert len(result.files_loaded) == 1
        assert len(result.files_loaded[0].errors) > 0
        assert result.files_loaded[0].records_loaded == 0


class TestJoinConfigValidation:
    """Test JoinConfig validation logic."""

    def test_database_path_set_from_output_database(self, temp_dir):
        """Test that database_path is set from output_database."""
        output_db = temp_dir / "test.duckdb"

        config = JoinConfig(node_files=[], edge_files=[], output_database=output_db)

        # Should set database_path from output_database
        assert config.database_path == output_db

    def test_database_path_none_when_output_database_none(self):
        """Test that database_path remains None when output_database is None."""
        config = JoinConfig(node_files=[], edge_files=[], output_database=None)

        # Should remain None for in-memory database
        assert config.database_path is None


class TestPrepareFileSpecsFromPaths:
    """Test prepare_file_specs_from_paths helper function."""

    def test_prepare_specs_from_file_paths(self, sample_nodes_file, sample_edges_file):
        """Test preparing file specs from file paths."""
        node_paths = [str(sample_nodes_file)]
        edge_paths = [str(sample_edges_file)]

        node_specs, edge_specs = prepare_file_specs_from_paths(node_paths, edge_paths)

        assert len(node_specs) == 1
        assert len(edge_specs) == 1

        assert node_specs[0].path == sample_nodes_file
        assert node_specs[0].format == KGXFormat.TSV
        assert node_specs[0].file_type == KGXFileType.NODES

        assert edge_specs[0].path == sample_edges_file
        assert edge_specs[0].format == KGXFormat.TSV
        assert edge_specs[0].file_type == KGXFileType.EDGES

    def test_prepare_specs_format_detection(self, temp_dir):
        """Test format detection in prepare_file_specs_from_paths."""
        # Create files with different extensions
        tsv_file = temp_dir / "data.tsv"
        jsonl_file = temp_dir / "data.jsonl"
        parquet_file = temp_dir / "data.parquet"

        tsv_file.touch()
        jsonl_file.touch()
        parquet_file.touch()

        node_paths = [str(tsv_file), str(jsonl_file), str(parquet_file)]

        node_specs, _ = prepare_file_specs_from_paths(node_paths, [])

        assert len(node_specs) == 3
        assert node_specs[0].format == KGXFormat.TSV
        assert node_specs[1].format == KGXFormat.JSONL
        assert node_specs[2].format == KGXFormat.PARQUET

    def test_prepare_specs_with_glob_patterns(self, temp_dir):
        """Test prepare_file_specs_from_paths with glob patterns."""
        # Create multiple files
        for i in range(3):
            (temp_dir / f"nodes_{i}.tsv").touch()
            (temp_dir / f"edges_{i}.tsv").touch()

        node_pattern = str(temp_dir / "nodes_*.tsv")
        edge_pattern = str(temp_dir / "edges_*.tsv")

        node_specs, edge_specs = prepare_file_specs_from_paths([node_pattern], [edge_pattern])

        assert len(node_specs) == 3
        assert len(edge_specs) == 3

        # All should be detected as TSV nodes/edges
        for spec in node_specs:
            assert spec.format == KGXFormat.TSV
            assert spec.file_type == KGXFileType.NODES

        for spec in edge_specs:
            assert spec.format == KGXFormat.TSV
            assert spec.file_type == KGXFileType.EDGES

    def test_prepare_specs_empty_lists(self):
        """Test prepare_file_specs_from_paths with empty lists."""
        node_specs, edge_specs = prepare_file_specs_from_paths([], [])

        assert len(node_specs) == 0
        assert len(edge_specs) == 0


class TestJoinOperationEdgeCases:
    """Test edge cases and error conditions for join operation."""

    def test_join_malformed_tsv_file(self, temp_dir):
        """Test join with malformed TSV file."""
        malformed_file = temp_dir / "malformed.tsv"
        malformed_content = """id	category	name
HGNC:123	biolink:Gene	gene1	extra_column
HGNC:456	biolink:Gene
"""  # Inconsistent columns
        malformed_file.write_text(malformed_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=malformed_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        # Should handle gracefully, may load partial data
        assert result is not None
        assert len(result.files_loaded) == 1
        # Might have some records loaded despite malformation
        assert result.files_loaded[0].records_loaded >= 0

    def test_join_empty_file(self, temp_dir):
        """Test join with empty file."""
        empty_file = temp_dir / "empty.tsv"
        empty_file.write_text("")

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=empty_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 0

    def test_join_header_only_file(self, temp_dir):
        """Test join with header-only file."""
        header_only_file = temp_dir / "header_only.tsv"
        header_only_file.write_text("id\tcategory\tname\n")

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=header_only_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 0
        assert result.final_stats.nodes == 0


if __name__ == "__main__":
    pytest.main([__file__])
