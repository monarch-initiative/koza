"""
Test suite for merge graph operation using mocking to verify operation orchestration.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from koza.graph_operations import merge_graphs, prepare_merge_config_from_paths
from koza.model.graph_operations import (
    DatabaseStats,
    FileSpec,
    JoinResult,
    KGXFileType,
    KGXFormat,
    MergeConfig,
    NormalizeResult,
    OperationSummary,
    PruneResult,
)


@pytest.fixture
def sample_file_specs():
    """Create sample file specifications."""
    node_specs = [
        FileSpec(path=Path("nodes1.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.NODES),
        FileSpec(path=Path("nodes2.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.NODES),
    ]
    edge_specs = [FileSpec(path=Path("edges1.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.EDGES)]
    mapping_specs = [FileSpec(path=Path("mappings.sssom.tsv"), format=KGXFormat.TSV, file_type=None)]
    return node_specs, edge_specs, mapping_specs


@pytest.fixture
def mock_join_result():
    """Create mock join result."""
    from koza.model.graph_operations import FileLoadResult

    mock_file_load = FileLoadResult(
        file_spec=FileSpec(path=Path("test.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.NODES),
        records_loaded=100,
        detected_format=KGXFormat.TSV,
        load_time_seconds=0.1,
    )
    return JoinResult(
        files_loaded=[mock_file_load],  # Need at least one file loaded
        final_stats=DatabaseStats(nodes=100, edges=200),
        total_time_seconds=1.0,
        database_path=Path("test.duckdb"),
    )


@pytest.fixture
def mock_normalize_result():
    """Create mock normalize result."""
    return NormalizeResult(
        success=True,
        mappings_loaded=[],
        edges_normalized=50,
        final_stats=DatabaseStats(nodes=100, edges=200),
        total_time_seconds=0.5,
        summary=OperationSummary(operation="normalize", success=True, message="Test", total_time_seconds=0.5),
    )


@pytest.fixture
def mock_prune_result():
    """Create mock prune result."""
    return PruneResult(
        database_path=Path("test.duckdb"),
        dangling_edges_moved=10,
        singleton_nodes_moved=5,
        singleton_nodes_kept=0,
        final_stats=DatabaseStats(nodes=95, edges=190, dangling_edges=10),
        dangling_edges_by_source={},
        missing_nodes_by_source={},
        total_time_seconds=0.2,
    )


class TestMergeOperationOrchestration:
    """Test merge operation orchestration with different configuration options."""

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_full_pipeline_all_operations(
        self,
        mock_graph_db,
        mock_prune,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_prune_result,
    ):
        """Test full pipeline with all operations enabled."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_normalize=False,
                skip_prune=False,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify all operations were called
            assert mock_join.called
            assert mock_normalize.called
            assert mock_prune.called

            # Verify result structure
            assert result.success is True
            assert result.join_result == mock_join_result
            assert result.normalize_result == mock_normalize_result
            assert result.prune_result == mock_prune_result
            assert set(result.operations_completed) == {"join", "normalize", "prune"}
            assert len(result.operations_skipped) == 0

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_skip_normalize_only_join_and_prune(
        self,
        mock_graph_db,
        mock_prune,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_prune_result,
    ):
        """Test pipeline with normalization skipped."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_prune.return_value = mock_prune_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_normalize=True,
                skip_prune=False,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify only join and prune were called
            assert mock_join.called
            assert not mock_normalize.called
            assert mock_prune.called

            # Verify result structure
            assert result.success is True
            assert result.join_result == mock_join_result
            assert result.normalize_result is None
            assert result.prune_result == mock_prune_result
            assert set(result.operations_completed) == {"join", "prune"}
            assert result.operations_skipped == ["normalize"]

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_skip_prune_only_join_and_normalize(
        self,
        mock_graph_db,
        mock_prune,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
    ):
        """Test pipeline with pruning skipped."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=100, edges=200)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_normalize=False,
                skip_prune=True,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify only join and normalize were called
            assert mock_join.called
            assert mock_normalize.called
            assert not mock_prune.called

            # Verify result structure
            assert result.success is True
            assert result.join_result == mock_join_result
            assert result.normalize_result == mock_normalize_result
            assert result.prune_result is None
            assert set(result.operations_completed) == {"join", "normalize"}
            assert result.operations_skipped == ["prune"]

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_skip_both_normalize_and_prune_only_join(
        self, mock_graph_db, mock_prune, mock_normalize, mock_join, sample_file_specs, mock_join_result
    ):
        """Test pipeline with both normalization and pruning skipped."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=100, edges=200)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_normalize=True,
                skip_prune=True,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify only join was called
            assert mock_join.called
            assert not mock_normalize.called
            assert not mock_prune.called

            # Verify result structure
            assert result.success is True
            assert result.join_result == mock_join_result
            assert result.normalize_result is None
            assert result.prune_result is None
            assert result.operations_completed == ["join"]
            assert set(result.operations_skipped) == {"normalize", "prune"}


class TestMergeOperationConfiguration:
    """Test merge operation configuration passing to individual operations."""

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_configuration_passed_to_operations(
        self,
        mock_graph_db,
        mock_prune,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_prune_result,
    ):
        """Test that configuration is correctly passed to individual operations."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_normalize=False,
                skip_prune=False,
                keep_singletons=False,
                remove_singletons=True,
                quiet=True,
                show_progress=False,
                schema_reporting=False,
            )

            result = merge_graphs(config)

            # Verify join configuration
            join_call_args = mock_join.call_args[0][0]  # First positional argument (JoinConfig)
            assert join_call_args.node_files == node_specs
            assert join_call_args.edge_files == edge_specs
            assert join_call_args.database_path == output_db
            assert join_call_args.quiet is True
            assert join_call_args.show_progress is False
            assert join_call_args.schema_reporting is False

            # Verify normalize configuration
            normalize_call_args = mock_normalize.call_args[0][0]  # First positional argument (NormalizeConfig)
            assert normalize_call_args.database_path == output_db
            assert normalize_call_args.mapping_files == mapping_specs
            assert normalize_call_args.quiet is True
            assert normalize_call_args.show_progress is False

            # Verify prune configuration
            prune_call_args = mock_prune.call_args[0][0]  # First positional argument (PruneConfig)
            assert prune_call_args.database_path == output_db
            assert prune_call_args.keep_singletons is False
            assert prune_call_args.remove_singletons is True
            assert prune_call_args.quiet is True
            assert prune_call_args.show_progress is False

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_temporary_database_when_no_output_specified(
        self, mock_graph_db, mock_join, sample_file_specs, mock_join_result
    ):
        """Test that temporary database is used when no output database is specified."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=100, edges=200)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        config = MergeConfig(
            node_files=node_specs,
            edge_files=edge_specs,
            mapping_files=mapping_specs,
            output_database=None,  # No output database specified
            skip_normalize=True,
            skip_prune=True,
            quiet=True,
        )

        result = merge_graphs(config)

        # Verify join was called with a temporary database path
        join_call_args = mock_join.call_args[0][0]
        assert join_call_args.database_path is not None
        assert str(join_call_args.database_path).endswith(".duckdb")

        # Verify result indicates temporary database was used
        assert result.database_path is None  # Should be None for temporary databases
        assert result.success is True


class TestMergeOperationErrorHandling:
    """Test error handling in merge operations."""

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_join_failure_stops_pipeline(self, mock_graph_db, mock_join, sample_file_specs):
        """Test that join failure stops the entire pipeline."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks - join raises exception
        mock_join.side_effect = Exception("Join failed")

        # Mock database
        mock_db = MagicMock()
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify pipeline failed
            assert result.success is False
            assert "Join failed" in result.summary.message
            assert len(result.errors) > 0
            assert result.join_result is None
            assert result.normalize_result is None
            assert result.prune_result is None

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_normalize_failure_continues_to_prune(
        self,
        mock_graph_db,
        mock_prune,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_prune_result,
    ):
        """Test that normalize failure continues to prune with warnings."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks - normalize fails but returns failed result
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = NormalizeResult(
            success=False,
            mappings_loaded=[],
            edges_normalized=0,
            final_stats=None,
            total_time_seconds=0.1,
            summary=OperationSummary(
                operation="normalize", success=False, message="Normalize failed", total_time_seconds=0.1
            ),
            errors=["Normalize failed"],
        )
        mock_prune.return_value = mock_prune_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify pipeline continued despite normalize failure
            assert mock_join.called
            assert mock_normalize.called
            assert mock_prune.called

            # Verify warnings about normalization failure
            assert result.success is True  # Overall success despite normalize failure
            assert len(result.warnings) > 0
            assert "Normalization failed" in result.warnings[0]
            assert result.normalize_result.success is False


class TestMergeConfigValidation:
    """Test MergeConfig validation."""

    def test_validation_requires_input_files(self):
        """Test that validation requires at least some input files."""
        with pytest.raises(ValueError, match="Must provide at least one node or edge file"):
            MergeConfig(node_files=[], edge_files=[], mapping_files=[])

    def test_validation_requires_mappings_when_normalize_enabled(self, sample_file_specs):
        """Test that validation requires mapping files when normalize is enabled."""
        node_specs, edge_specs, _ = sample_file_specs

        with pytest.raises(ValueError, match="Must provide mapping files or set skip_normalize=True"):
            MergeConfig(node_files=node_specs, edge_files=edge_specs, mapping_files=[], skip_normalize=False)

    def test_validation_allows_empty_mappings_when_normalize_skipped(self, sample_file_specs):
        """Test that validation allows empty mappings when normalize is skipped."""
        node_specs, edge_specs, _ = sample_file_specs

        # Should not raise
        config = MergeConfig(node_files=node_specs, edge_files=edge_specs, mapping_files=[], skip_normalize=True)
        assert config.skip_normalize is True

    def test_validation_singleton_options_conflict(self, sample_file_specs):
        """Test that validation prevents conflicting singleton options."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        with pytest.raises(ValueError, match="Cannot both keep and remove singletons"):
            MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                keep_singletons=True,
                remove_singletons=True,
            )

    def test_validation_export_requires_directory(self, sample_file_specs):
        """Test that validation requires export directory when export is enabled."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        with pytest.raises(ValueError, match="Must provide export_directory when export_final=True"):
            MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                export_final=True,
                export_directory=None,
            )


class TestMergeHelperFunctions:
    """Test helper functions for merge operation."""

    @patch("koza.graph_operations.join.prepare_file_specs_from_paths")
    @patch("koza.graph_operations.normalize.prepare_mapping_file_specs_from_paths")
    def test_prepare_merge_config_from_paths(self, mock_prepare_mappings, mock_prepare_files, sample_file_specs):
        """Test prepare_merge_config_from_paths helper function."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_prepare_files.return_value = (node_specs, edge_specs)
        mock_prepare_mappings.return_value = mapping_specs

        node_paths = [Path("nodes1.tsv"), Path("nodes2.tsv")]
        edge_paths = [Path("edges1.tsv")]
        mapping_paths = [Path("mappings.sssom.tsv")]
        output_db = Path("output.duckdb")

        config = prepare_merge_config_from_paths(
            node_files=node_paths,
            edge_files=edge_paths,
            mapping_files=mapping_paths,
            output_database=output_db,
            skip_normalize=True,
            skip_prune=False,
            quiet=True,
        )

        # Verify helper functions were called correctly
        mock_prepare_files.assert_called_once_with(["nodes1.tsv", "nodes2.tsv"], ["edges1.tsv"])
        mock_prepare_mappings.assert_called_once_with(mapping_paths)

        # Verify configuration
        assert config.node_files == node_specs
        assert config.edge_files == edge_specs
        assert config.mapping_files == mapping_specs
        assert config.output_database == output_db
        assert config.skip_normalize is True
        assert config.skip_prune is False
        assert config.quiet is True


if __name__ == "__main__":
    pytest.main([__file__])
