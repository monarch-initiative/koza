"""
Merge operation - composite pipeline orchestrating join → normalize → prune operations.
"""

import tempfile
import time
from pathlib import Path

from loguru import logger

from koza.model.graph_operations import (
    JoinConfig,
    MergeConfig,
    MergeResult,
    NormalizeConfig,
    OperationSummary,
    PruneConfig,
)

from .join import join_graphs
from .normalize import normalize_graph
from .prune import prune_graph
from .utils import GraphDatabase, print_operation_summary


def merge_graphs(config: MergeConfig) -> MergeResult:
    """
    Execute the complete merge pipeline: join → normalize → prune.

    This composite operation orchestrates multiple graph operations in sequence
    to create a clean, normalized, and validated graph database.

    Args:
        config: MergeConfig with pipeline configuration

    Returns:
        MergeResult with complete pipeline statistics
    """
    start_time = time.time()
    errors = []
    warnings = []
    operations_completed = []
    operations_skipped = []

    # Individual operation results
    join_result = None
    normalize_result = None
    prune_result = None

    # Determine database path (temporary if not specified)
    if config.output_database:
        database_path = config.output_database
        using_temp_db = False
    else:
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        database_path = Path(temp_db.name)
        temp_db.close()
        using_temp_db = True

    try:
        if not config.quiet:
            print("🔄 Starting merge pipeline...")
            print(
                f"📊 Pipeline: join → {'normalize → ' if not config.skip_normalize else ''}{'prune' if not config.skip_prune else ''}"
            )
            if using_temp_db:
                print(f"💾 Using temporary database: {database_path}")
            else:
                print(f"💾 Output database: {database_path}")

        # Step 1: Join - Load all input files
        if not config.quiet:
            print("\n📥 Step 1: Join - Loading input files...")

        join_config = JoinConfig(
            node_files=config.node_files,
            edge_files=config.edge_files,
            output_database=database_path,
            schema_reporting=config.schema_reporting,
            quiet=config.quiet,
            show_progress=config.show_progress,
        )

        join_result = join_graphs(join_config)

        if not join_result or len(join_result.files_loaded) == 0:
            raise ValueError("Join operation failed - no files were loaded")

        # Ensure database file exists after join
        if not database_path.exists():
            raise ValueError(f"Database file was not created by join operation: {database_path}")

        operations_completed.append("join")

        if not config.quiet:
            files_count = len(join_result.files_loaded)
            nodes_count = join_result.final_stats.nodes
            edges_count = join_result.final_stats.edges
            print(f"✓ Join completed: {files_count} files → {nodes_count:,} nodes, {edges_count:,} edges")

        # Step 2: Normalize - Apply SSSOM mappings (if not skipped)
        if not config.skip_normalize:
            if not config.quiet:
                print("\n🔄 Step 2: Normalize - Applying SSSOM mappings...")

            normalize_config = NormalizeConfig(
                database_path=database_path,
                mapping_files=config.mapping_files,
                quiet=config.quiet,
                show_progress=config.show_progress,
            )

            normalize_result = normalize_graph(normalize_config)

            if not normalize_result.success:
                warnings.append("Normalization failed but pipeline continued")
                if normalize_result.errors:
                    errors.extend(normalize_result.errors)
            else:
                operations_completed.append("normalize")

                if not config.quiet:
                    mappings_count = len(normalize_result.mappings_loaded)
                    normalized_count = normalize_result.edges_normalized
                    print(
                        f"✓ Normalize completed: {mappings_count} mapping files → {normalized_count:,} edge references normalized"
                    )
        else:
            operations_skipped.append("normalize")
            if not config.quiet:
                print("\n⏭️  Step 2: Normalize - Skipped")

        # Step 3: Prune - Remove dangling edges and handle singletons (if not skipped)
        if not config.skip_prune:
            if not config.quiet:
                print("\n🧹 Step 3: Prune - Cleaning graph structure...")

            prune_config = PruneConfig(
                database_path=database_path,
                keep_singletons=config.keep_singletons,
                remove_singletons=config.remove_singletons,
                quiet=config.quiet,
                show_progress=config.show_progress,
            )

            prune_result = prune_graph(prune_config)

            if not prune_result:
                warnings.append("Pruning failed but pipeline continued")
            else:
                operations_completed.append("prune")

                if not config.quiet:
                    dangling_count = prune_result.dangling_edges_moved
                    singleton_count = prune_result.singleton_nodes_moved
                    print(
                        f"✓ Prune completed: {dangling_count:,} dangling edges moved, {singleton_count:,} singleton nodes handled"
                    )
        else:
            operations_skipped.append("prune")
            if not config.quiet:
                print("\n⏭️  Step 3: Prune - Skipped")

        # Get final database statistics
        with GraphDatabase(database_path) as db:
            final_stats = db.get_stats()

        # Step 4: Export final data (if requested)
        exported_files = []
        if config.export_final and config.export_directory:
            if not config.quiet:
                print(f"\n📤 Step 4: Export - Exporting to {config.export_directory}...")

            config.export_directory.mkdir(parents=True, exist_ok=True)

            with GraphDatabase(database_path) as db:
                # Check if we have data to export
                has_nodes = False
                has_edges = False
                try:
                    nodes_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                    has_nodes = nodes_count > 0
                except Exception:
                    pass  # Table might not exist

                try:
                    edges_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
                    has_edges = edges_count > 0
                except Exception:
                    pass  # Table might not exist

                if not has_nodes and not has_edges:
                    if not config.quiet:
                        print("⚠️  No data to export (no nodes or edges found)")
                else:
                    # Determine graph name
                    export_graph_name = config.graph_name or "merged_graph"

                    # Export based on archive option
                    if config.archive:
                        # Create archive filename
                        archive_ext = ".tar.gz" if config.compress else ".tar"
                        archive_file = config.export_directory / f"{export_graph_name}{archive_ext}"

                        # Export to archive
                        db.export_to_archive(
                            output_path=archive_file,
                            graph_name=export_graph_name,
                            format=config.output_format,
                            compress=config.compress,
                        )
                        exported_files.append(archive_file)

                        if not config.quiet:
                            archive_type = "compressed archive" if config.compress else "archive"
                            print(f"✓ Export completed: {archive_type} {archive_file}")
                    else:
                        # Export to loose files
                        nodes_file, edges_file = db.export_to_loose_files(
                            output_directory=config.export_directory,
                            graph_name=export_graph_name,
                            format=config.output_format,
                        )
                        exported_files.extend([nodes_file, edges_file])

                        if not config.quiet:
                            print(f"✓ Export completed: {len(exported_files)} files exported")

            if not exported_files and not config.quiet:
                print("⚠️  No files exported")

        # Create pipeline summary
        total_time = time.time() - start_time
        pipeline_summary = f"Pipeline completed: {' → '.join(operations_completed)}"
        if operations_skipped:
            pipeline_summary += f" (skipped: {', '.join(operations_skipped)})"

        summary = OperationSummary(
            operation="merge",
            success=True,
            message=pipeline_summary,
            stats=final_stats,
            files_processed=len(config.node_files) + len(config.edge_files) + len(config.mapping_files),
            total_time_seconds=total_time,
            warnings=warnings,
            errors=errors,
        )

        if not config.quiet:
            print(f"\n🎉 Merge pipeline completed successfully!")
            print_operation_summary(summary)

        # Clean up temporary database if used
        final_database_path = None if using_temp_db else database_path
        if using_temp_db:
            try:
                database_path.unlink()
            except Exception:
                pass  # Best effort cleanup

        return MergeResult(
            success=True,
            join_result=join_result,
            normalize_result=normalize_result,
            prune_result=prune_result,
            operations_completed=operations_completed,
            operations_skipped=operations_skipped,
            final_stats=final_stats,
            database_path=final_database_path,
            exported_files=exported_files,
            total_time_seconds=total_time,
            summary=summary,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        total_time = time.time() - start_time
        error_msg = f"Merge pipeline failed: {e}"
        errors.append(error_msg)
        logger.error(error_msg)

        # Clean up temporary database if used
        if using_temp_db:
            try:
                database_path.unlink()
            except Exception:
                pass  # Best effort cleanup

        summary = OperationSummary(
            operation="merge",
            success=False,
            message=error_msg,
            stats=None,
            files_processed=len(config.node_files) + len(config.edge_files) + len(config.mapping_files),
            total_time_seconds=total_time,
            warnings=warnings,
            errors=errors,
        )

        if not config.quiet:
            print(f"\n❌ Merge pipeline failed!")
            print_operation_summary(summary)

        return MergeResult(
            success=False,
            join_result=join_result,
            normalize_result=normalize_result,
            prune_result=prune_result,
            operations_completed=operations_completed,
            operations_skipped=operations_skipped,
            final_stats=None,
            database_path=None,
            exported_files=[],
            total_time_seconds=total_time,
            summary=summary,
            errors=errors,
            warnings=warnings,
        )


def prepare_merge_config_from_paths(
    node_files: list[Path],
    edge_files: list[Path],
    mapping_files: list[Path],
    output_database: Path | None = None,
    skip_normalize: bool = False,
    skip_prune: bool = False,
    **kwargs,
) -> MergeConfig:
    """
    Helper function to create MergeConfig from file paths.

    Args:
        node_files: List of node file paths
        edge_files: List of edge file paths
        mapping_files: List of SSSOM mapping file paths
        output_database: Optional output database path
        skip_normalize: Skip normalization step
        skip_prune: Skip pruning step
        **kwargs: Additional MergeConfig parameters

    Returns:
        MergeConfig object
    """
    from .join import prepare_file_specs_from_paths
    from .normalize import prepare_mapping_file_specs_from_paths

    # Prepare file specifications
    node_specs, edge_specs = prepare_file_specs_from_paths([str(f) for f in node_files], [str(f) for f in edge_files])

    mapping_specs = prepare_mapping_file_specs_from_paths(mapping_files) if mapping_files else []

    return MergeConfig(
        node_files=node_specs,
        edge_files=edge_specs,
        mapping_files=mapping_specs,
        output_database=output_database,
        skip_normalize=skip_normalize,
        skip_prune=skip_prune,
        **kwargs,
    )
