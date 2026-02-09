"""
Test suite for merge graph operation using mocking to verify operation orchestration.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import duckdb

from koza.graph_operations.utils import GraphDatabase
from koza.graph_operations import merge_graphs, prepare_merge_config_from_paths
from koza.model.graph_operations import (
    DatabaseStats,
    FileSpec,
    JoinResult,
    KGXFileType,
    KGXFormat,
    MergeConfig,
    MergeResult,
    OperationSummary,
    NormalizeResult,
    DeduplicateResult,
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
def mock_deduplicate_result():
    """Create mock normalize result."""
    return DeduplicateResult(
        success=True,
        duplicate_nodes_found=5,
        duplicate_nodes_removed=5,
        duplicate_edges_found=20,
        duplicate_edges_removed=20,
        final_stats=DatabaseStats(nodes=95, edges=180),
        total_time_seconds=0.5,
        summary=OperationSummary(operation="deduplicate", success=True, message="Test", total_time_seconds=0.5),
        errors=[],
        warnings=[],
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
        success=True,
    )


class TestMergeOperationOrchestration:
    """Test merge operation orchestration with different configuration options."""

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.deduplicate_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_full_pipeline_all_operations(
        self,
        mock_graph_db,
        mock_prune,
        mock_deduplicate,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_deduplicate_result,
        mock_prune_result,
    ):
        """Test full pipeline with all operations enabled."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result
        mock_deduplicate.return_value = mock_deduplicate_result

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
                skip_deduplicate=False,
                skip_validation=True,  # Skip validation in mocked tests
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify all operations were called
            assert mock_join.called_exactly_once
            assert mock_normalize.called_exactly_once
            assert mock_deduplicate.called_exactly_once
            assert mock_prune.called_exactly_once

            # Verify result structure
            assert result.success is True
            assert result.join_result == mock_join_result
            assert result.normalize_result == mock_normalize_result
            assert result.prune_result == mock_prune_result
            assert set(result.operations_completed) == {"join", "deduplicate", "normalize", "prune"}
            assert result.operations_skipped == ["validate"]  # Validation skipped in mocked tests
            assert len(result.warnings) == 0
            assert len(result.errors) == 0

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
                skip_validation=True,  # Skip validation in mocked tests
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
            assert set(result.operations_skipped) == {"normalize", "validate"}

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
                skip_validation=True,  # Skip validation in mocked tests
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
            assert set(result.operations_skipped) == {"prune", "validate"}

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
                skip_validation=True,  # Skip validation in mocked tests
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
            assert set(result.operations_skipped) == {"normalize", "prune", "validate"}


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
            skip_validation=True,  # Skip validation in mocked tests
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
    def test_normalize_failure_can_stop_pipeline(
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
            errors=["SAMPLE NORMALIZE RESULT ERROR"],
        )
        mock_prune.return_value = mock_prune_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            # Create the database file to simulate successful join
            #tmp = GraphDatabase(output_db)
            #tmp.__init__()
            #output_db.touch()
            con = duckdb.connect(str(output_db))
            con.close()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_validation=True,  # Skip validation in mocked tests
                quiet=True,
                continue_on_pipeline_step_error=False, #THIS IS WHAT MAKES IT FAIL.
                handle_errors_silently=True,
            )

            caught_exception = None
            result = None
            try:
                result = merge_graphs(config)
            except Exception as e:
                caught_exception = e

            assert result.success is False
            assert caught_exception is None #Because "handle_errors_silently" is True, no Exceptions should be raised.
            assert "Merge pipeline failed: Normalization step failed. Aborting pipeline." in result.errors
            assert "SAMPLE NORMALIZE RESULT ERROR" in result.errors
            assert result.summary.message == "Merge pipeline failed: Normalization step failed. Aborting pipeline."
#            exit()

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
            errors=["SAMPLE NORMALIZE RESULT ERROR"],
        )
        mock_prune.return_value = mock_prune_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            conn = duckdb.connect(str(output_db))
            conn.close()
            # Create the database file to simulate successful join
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_validation=True,  # Skip validation in mocked tests
                quiet=True,
                continue_on_pipeline_step_error=True, #THIS IS WHAT MAKES IT KEEP RUNNING EVEN IF NORMALIZATION FAILS.
            )

            result = merge_graphs(config)

            # Verify pipeline continued despite normalize failure
            assert mock_join.called
            assert mock_normalize.called
            assert mock_prune.called
            # Verify warnings about normalization failure
            assert result.success is True  # Overall success despite normalize failure
            assert len(result.warnings) > 0
            assert "Deduplication failed but pipeline continued" not in result.warnings
            assert "Normalization failed but pipeline continued" in result.warnings
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


class TestPrepareMergeConfigFromPathsValidation:
    """Tests for prepare_merge_config_from_paths with validation arguments."""

    @patch("koza.graph_operations.join.prepare_file_specs_from_paths")
    @patch("koza.graph_operations.normalize.prepare_mapping_file_specs_from_paths")
    def test_accepts_skip_validation_arg(self, mock_prepare_mappings, mock_prepare_files, sample_file_specs):
        """Should accept skip_validation argument."""
        node_specs, edge_specs, mapping_specs = sample_file_specs
        mock_prepare_files.return_value = (node_specs, edge_specs)
        mock_prepare_mappings.return_value = mapping_specs

        config = prepare_merge_config_from_paths(
            node_files=[Path("nodes.tsv")],
            edge_files=[Path("edges.tsv")],
            mapping_files=[Path("mappings.sssom.tsv")],
            skip_validation=True,
        )

        assert config.skip_validation is True

    @patch("koza.graph_operations.join.prepare_file_specs_from_paths")
    @patch("koza.graph_operations.normalize.prepare_mapping_file_specs_from_paths")
    def test_accepts_validation_errors_halt_arg(self, mock_prepare_mappings, mock_prepare_files, sample_file_specs):
        """Should accept validation_errors_halt argument."""
        node_specs, edge_specs, mapping_specs = sample_file_specs
        mock_prepare_files.return_value = (node_specs, edge_specs)
        mock_prepare_mappings.return_value = mapping_specs

        config = prepare_merge_config_from_paths(
            node_files=[Path("nodes.tsv")],
            edge_files=[Path("edges.tsv")],
            mapping_files=[Path("mappings.sssom.tsv")],
            validation_errors_halt=True,
        )

        assert config.validation_errors_halt is True

    @patch("koza.graph_operations.join.prepare_file_specs_from_paths")
    @patch("koza.graph_operations.normalize.prepare_mapping_file_specs_from_paths")
    def test_accepts_validation_schema_path_arg(self, mock_prepare_mappings, mock_prepare_files, sample_file_specs):
        """Should accept validation_schema_path argument."""
        node_specs, edge_specs, mapping_specs = sample_file_specs
        mock_prepare_files.return_value = (node_specs, edge_specs)
        mock_prepare_mappings.return_value = mapping_specs

        config = prepare_merge_config_from_paths(
            node_files=[Path("nodes.tsv")],
            edge_files=[Path("edges.tsv")],
            mapping_files=[Path("mappings.sssom.tsv")],
            validation_schema_path="/custom/schema.yaml",
        )

        assert config.validation_schema_path == "/custom/schema.yaml"


class TestMergeConfigValidationFields:
    """Tests for validation-related fields in MergeConfig."""

    @pytest.fixture
    def minimal_merge_config_args(self):
        """Minimal args to create a valid MergeConfig."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            node_file = tmp_path / "test_nodes.tsv"
            node_file.write_text("id\tcategory\nHGNC:1234\tbiolink:Gene\n")
            mapping_file = tmp_path / "test_mappings.tsv"
            mapping_file.write_text("subject_id\tobject_id\n")
            yield {
                "node_files": [FileSpec(path=node_file)],
                "edge_files": [],
                "mapping_files": [FileSpec(path=mapping_file)],
            }

    def test_skip_validation_default_false(self, minimal_merge_config_args):
        """skip_validation should default to False."""
        config = MergeConfig(**minimal_merge_config_args)
        assert config.skip_validation is False

    def test_skip_validation_can_be_set_true(self, minimal_merge_config_args):
        """skip_validation can be set to True."""
        config = MergeConfig(**minimal_merge_config_args, skip_validation=True)
        assert config.skip_validation is True

    def test_validation_errors_halt_default_false(self, minimal_merge_config_args):
        """validation_errors_halt should default to False."""
        config = MergeConfig(**minimal_merge_config_args)
        assert config.validation_errors_halt is False

    def test_validation_errors_halt_can_be_set_true(self, minimal_merge_config_args):
        """validation_errors_halt can be set to True."""
        config = MergeConfig(**minimal_merge_config_args, validation_errors_halt=True)
        assert config.validation_errors_halt is True

    def test_validation_schema_path_default_none(self, minimal_merge_config_args):
        """validation_schema_path should default to None."""
        config = MergeConfig(**minimal_merge_config_args)
        assert config.validation_schema_path is None

    def test_validation_schema_path_can_be_set(self, minimal_merge_config_args):
        """validation_schema_path can be set to a path string."""
        config = MergeConfig(
            **minimal_merge_config_args,
            validation_schema_path="/path/to/custom-schema.yaml"
        )
        assert config.validation_schema_path == "/path/to/custom-schema.yaml"

    def test_validation_sample_limit_default_10(self, minimal_merge_config_args):
        """validation_sample_limit should default to 10."""
        config = MergeConfig(**minimal_merge_config_args)
        assert config.validation_sample_limit == 10


class TestMergeResultValidationField:
    """Tests for validation_result field in MergeResult."""

    def test_validation_result_default_none(self):
        """validation_result should default to None."""
        result = MergeResult(
            success=True,
            total_time_seconds=1.0,
            summary=OperationSummary(operation="merge", success=True, message="Test", total_time_seconds=1.0),
        )
        assert result.validation_result is None

    def test_validation_result_can_be_set(self):
        """validation_result can be assigned a ValidationResult."""
        from koza.model.graph_operations import ValidationReportModel, ValidationResult

        validation_result = ValidationResult(
            validation_report=ValidationReportModel(),
            total_time_seconds=0.5,
        )

        result = MergeResult(
            success=True,
            total_time_seconds=1.0,
            summary=OperationSummary(operation="merge", success=True, message="Test", total_time_seconds=1.0),
            validation_result=validation_result,
        )

        assert result.validation_result is not None
        assert result.validation_result.total_time_seconds == 0.5


class TestMergeWithValidation:
    """Tests for merge pipeline with validation step."""

    @pytest.fixture
    def mock_validation_result(self):
        """Create mock validation result."""
        from koza.model.graph_operations import ValidationReportModel, ValidationResult

        return ValidationResult(
            validation_report=ValidationReportModel(
                compliance_percentage=95.0,
                error_count=0,
                warning_count=2,
                tables_validated=["nodes", "edges"],
            ),
            total_time_seconds=0.3,
        )

    @pytest.fixture
    def mock_validation_result_with_errors(self):
        """Create mock validation result with errors."""
        from koza.model.graph_operations import ValidationReportModel, ValidationResult

        return ValidationResult(
            validation_report=ValidationReportModel(
                compliance_percentage=75.0,
                error_count=5,
                warning_count=2,
                tables_validated=["nodes", "edges"],
            ),
            total_time_seconds=0.3,
        )

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.deduplicate_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.validate_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_merge_includes_validation_step_by_default(
        self,
        mock_graph_db,
        mock_validate,
        mock_prune,
        mock_deduplicate,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_deduplicate_result,
        mock_prune_result,
        mock_validation_result,
    ):
        """Merge should include validation step when skip_validation=False (default)."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result
        mock_deduplicate.return_value = mock_deduplicate_result
        mock_validate.return_value = mock_validation_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify validation was called and included in results
            assert mock_validate.called
            assert result.success
            assert "validate" in result.operations_completed
            assert result.validation_result is not None

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.deduplicate_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.validate_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_merge_skips_validation_when_configured(
        self,
        mock_graph_db,
        mock_validate,
        mock_prune,
        mock_deduplicate,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_deduplicate_result,
        mock_prune_result,
    ):
        """Merge should skip validation when skip_validation=True."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result
        mock_deduplicate.return_value = mock_deduplicate_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                skip_validation=True,
                quiet=True,
            )

            result = merge_graphs(config)

            # Verify validation was NOT called
            assert not mock_validate.called
            assert result.success
            assert "validate" in result.operations_skipped
            assert "validate" not in result.operations_completed
            assert result.validation_result is None

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.deduplicate_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.validate_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_merge_validation_result_has_report(
        self,
        mock_graph_db,
        mock_validate,
        mock_prune,
        mock_deduplicate,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_deduplicate_result,
        mock_prune_result,
        mock_validation_result,
    ):
        """Validation result should contain a validation report."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result
        mock_deduplicate.return_value = mock_deduplicate_result
        mock_validate.return_value = mock_validation_result

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                quiet=True,
            )

            result = merge_graphs(config)

            assert result.validation_result is not None
            assert result.validation_result.validation_report is not None
            assert hasattr(result.validation_result.validation_report, "compliance_percentage")

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.deduplicate_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.validate_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_merge_halts_on_validation_errors_when_configured(
        self,
        mock_graph_db,
        mock_validate,
        mock_prune,
        mock_deduplicate,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_deduplicate_result,
        mock_prune_result,
        mock_validation_result_with_errors,
    ):
        """Merge should fail when validation_errors_halt=True and validation has errors."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result
        mock_deduplicate.return_value = mock_deduplicate_result
        mock_validate.return_value = mock_validation_result_with_errors

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                validation_errors_halt=True,
                quiet=True,
            )

            result = merge_graphs(config)

            # Should fail because validation_errors_halt=True and there are errors
            assert result.success is False
            assert any("Validation failed" in e for e in result.errors)

    @patch("koza.graph_operations.merge.join_graphs")
    @patch("koza.graph_operations.merge.normalize_graph")
    @patch("koza.graph_operations.merge.deduplicate_graph")
    @patch("koza.graph_operations.merge.prune_graph")
    @patch("koza.graph_operations.merge.validate_graph")
    @patch("koza.graph_operations.merge.GraphDatabase")
    def test_merge_continues_on_validation_errors_by_default(
        self,
        mock_graph_db,
        mock_validate,
        mock_prune,
        mock_deduplicate,
        mock_normalize,
        mock_join,
        sample_file_specs,
        mock_join_result,
        mock_normalize_result,
        mock_deduplicate_result,
        mock_prune_result,
        mock_validation_result_with_errors,
    ):
        """Merge should continue (with warnings) when validation has errors but halt=False."""
        node_specs, edge_specs, mapping_specs = sample_file_specs

        # Setup mocks
        mock_join.return_value = mock_join_result
        mock_normalize.return_value = mock_normalize_result
        mock_prune.return_value = mock_prune_result
        mock_deduplicate.return_value = mock_deduplicate_result
        mock_validate.return_value = mock_validation_result_with_errors

        # Mock database
        mock_db = MagicMock()
        mock_db.get_stats.return_value = DatabaseStats(nodes=95, edges=190)
        mock_graph_db.return_value.__enter__.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            output_db = Path(temp_dir) / "test.duckdb"
            output_db.touch()

            config = MergeConfig(
                node_files=node_specs,
                edge_files=edge_specs,
                mapping_files=mapping_specs,
                output_database=output_db,
                validation_errors_halt=False,  # Default
                quiet=True,
            )

            result = merge_graphs(config)

            # Should complete successfully even if validation found issues
            assert result.success
            assert "validate" in result.operations_completed


if __name__ == "__main__":
    pytest.main([__file__])
