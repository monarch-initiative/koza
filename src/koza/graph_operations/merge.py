"""
Merge operation - composite pipeline orchestrating join → normalize → prune operations.
"""

import tempfile
import time
from pathlib import Path
from typing import Any

from loguru import logger

from koza.model.graph_operations import (
    DeduplicateConfig,
    JoinConfig,
    MergeConfig,
    MergeResult,
    NormalizeConfig,
    OperationSummary,
    PruneConfig,
)

from .deduplicate import deduplicate_graph
from .join import join_graphs
from .normalize import normalize_graph
from .prune import prune_graph
from .utils import GraphDatabase, print_operation_summary


def merge_graphs(config: MergeConfig) -> MergeResult:
    """
    Execute the complete merge pipeline: join → deduplicate → normalize → prune.

    This composite operation orchestrates multiple graph operations in sequence
    to create a clean, normalized, and validated graph database from multiple
    source files. It's the recommended way to build a production-ready knowledge
    graph from raw KGX files and SSSOM mappings.

    The pipeline steps:
    1. **Join**: Load all node/edge files into a unified DuckDB database
    2. **Deduplicate**: Remove duplicate nodes/edges by ID (optional, skip with skip_deduplicate)
    3. **Normalize**: Apply SSSOM mappings to harmonize identifiers (optional, skip with skip_normalize)
    4. **Prune**: Handle dangling edges and singleton nodes (optional, skip with skip_prune)
    5. **Export**: Optionally export final graph to TSV/JSONL/Parquet files or archive

    Each step can be skipped via config flags. If a step fails, the pipeline can
    either abort (default) or continue with remaining steps (continue_on_pipeline_step_error).

    Args:
        config: MergeConfig containing:
            - node_files: List of FileSpec objects for node files
            - edge_files: List of FileSpec objects for edge files
            - mapping_files: List of FileSpec objects for SSSOM mapping files
            - output_database: Path for output database (temp if not specified)
            - skip_deduplicate: Skip deduplication step
            - skip_normalize: Skip normalization step (also skipped if no mapping files)
            - skip_prune: Skip pruning step
            - keep_singletons/remove_singletons: Singleton node handling in prune step
            - export_final: Whether to export final graph to files
            - export_directory: Where to write exported files
            - output_format: Format for exported files (TSV, JSONL, Parquet)
            - archive: Create a tar archive instead of loose files
            - compress: Gzip compress the archive
            - graph_name: Name prefix for exported files
            - continue_on_pipeline_step_error: Continue pipeline if a step fails
            - schema_reporting: Generate schema analysis report
            - quiet: Suppress console output
            - show_progress: Display progress bars

    Returns:
        MergeResult containing:
            - success: Whether the full pipeline completed successfully
            - join_result/deduplicate_result/normalize_result/prune_result: Per-step results
            - operations_completed: List of steps that completed successfully
            - operations_skipped: List of steps that were skipped
            - final_stats: DatabaseStats with final node/edge counts
            - database_path: Path to output database (None if temp was used)
            - exported_files: List of paths to exported files
            - total_time_seconds: Total pipeline duration
            - summary: OperationSummary with overall status
            - errors: List of error messages from failed steps
            - warnings: List of warning messages
    """
    start_time = time.time()
    errors = []
    warnings = []
    operations_completed = []
    operations_skipped = []

    # Individual operation results
    join_result = None
    deduplicate_result = None
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
    #TODO: Test db for Duckdb.

    #TODO: break this try block out into a seperate _merge_graph function which can better handle the raising of errors instead of handling all of them.
    try:
        if not config.quiet:
            print("Starting merge pipeline...")
            pipeline_steps = ["join"]
            if not config.skip_deduplicate:
                pipeline_steps.append("deduplicate")
            if not config.skip_normalize:
                pipeline_steps.append("normalize")
            if not config.skip_prune:
                pipeline_steps.append("prune")
            print(f"Pipeline: {' → '.join(pipeline_steps)}")
            if using_temp_db:
                print(f"Using temporary database: {database_path}")
            else:
                print(f"Output database: {database_path}")
        # Step 0: Confirm output database works.

        # Step 1: Join - Load all input files
        if not config.quiet:
            print("Step 1: Join - Loading input files...")

        join_config = JoinConfig(
            node_files=config.node_files,
            edge_files=config.edge_files,
            output_database=database_path,
            schema_reporting=config.schema_reporting,
            quiet=config.quiet,
            show_progress=config.show_progress,
            generate_provided_by=config.generate_provided_by,
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
            print(f"Join completed: {files_count:,} files | {nodes_count:,} nodes | {edges_count:,} edges")

        # Step 2: Deduplicate - Remove duplicate nodes/edges (if not skipped)
        if not config.skip_deduplicate:
            if not config.quiet:
                print("Step 2: Deduplicate - Removing duplicate nodes/edges...")

            deduplicate_config = DeduplicateConfig(
                database_path=database_path,
                deduplicate_nodes=True,
                deduplicate_edges=True,
                quiet=config.quiet,
                show_progress=config.show_progress,
            )

            deduplicate_result = deduplicate_graph(deduplicate_config)

            if deduplicate_result.success:
                operations_completed.append("deduplicate")
                if not config.quiet:
                    nodes_removed = deduplicate_result.duplicate_nodes_removed
                    edges_removed = deduplicate_result.duplicate_edges_removed
                    print(f"Deduplicate completed: {nodes_removed:,} duplicate nodes, {edges_removed:,} duplicate edges removed")
            elif config.continue_on_pipeline_step_error:
                warnings.append("Deduplication failed but pipeline continued")
                if deduplicate_result.errors:
                    errors.extend(deduplicate_result.errors)
            else:
                errors.append("Deduplication step failed. Aborting pipeline.")
                raise ValueError("Deduplication step failed. Aborting pipeline.")
        else:
            operations_skipped.append("deduplicate")
            if not config.quiet:
                print("Step 2: Deduplicate - Skipped")

        # Step 3: Normalize - Apply SSSOM mappings (if not skipped)
        if not config.skip_normalize:
            if not config.quiet:
                print("Step 3: Normalize - Applying SSSOM mappings...")

            normalize_config = NormalizeConfig(
                database_path=database_path,
                mapping_files=config.mapping_files,
                quiet=config.quiet,
                show_progress=config.show_progress,
            )

            normalize_result = normalize_graph(normalize_config)

            if normalize_result.success:
                operations_completed.append("normalize")
                if not config.quiet:
                    mappings_count = len(normalize_result.mappings_loaded)
                    normalized_count = normalize_result.edges_normalized
                    print(
                        f"Normalize completed: {mappings_count:,} mapping files | {normalized_count:,} edge references normalized"
                    )
            elif config.continue_on_pipeline_step_error:
                warnings.append("Normalization failed but pipeline continued")
                if normalize_result.errors:
                    errors.extend(normalize_result.errors)
            else:
                if normalize_result.errors:
                    errors.extend(normalize_result.errors)
                raise ValueError("Normalization step failed. Aborting pipeline.")

        else:
            operations_skipped.append("normalize")
            if not config.quiet:
                print("Step 3: Normalize - Skipped")

        # Step 4: Prune - Remove dangling edges and handle singletons (if not skipped)
        if not config.skip_prune:
            if not config.quiet:
                print("Step 4: Prune - Cleaning graph structure...")

            prune_config = PruneConfig(
                database_path=database_path,
                keep_singletons=config.keep_singletons,
                remove_singletons=config.remove_singletons,
                quiet=config.quiet,
                show_progress=config.show_progress,
            )

            prune_result = prune_graph(prune_config)

            if prune_result.success:
                operations_completed.append("prune")
                if not config.quiet:
                    dangling_count = prune_result.dangling_edges_moved
                    singleton_count = prune_result.singleton_nodes_moved
                    print(f"Prune completed: {dangling_count:,} dangling edges moved | {singleton_count:,} singleton nodes handled")
            elif config.continue_on_pipeline_step_error:
                warnings.append("Pruning failed but pipeline continued")
                if prune_result.errors:
                    errors.extend(prune_result.errors)
            else:
                errors.append("Prune step failed. Aborting pipeline.")
                raise ValueError("Prune step failed. Aborting pipeline.")
             
        else:
            operations_skipped.append("prune")
            if not config.quiet:
                print("Step 4: Prune - Skipped")

        # Get final database statistics
        with GraphDatabase(database_path) as db:
            final_stats = db.get_stats()

        # Step 5: Export final data (if requested)
        exported_files = []
        if config.export_final and config.export_directory:
            if not config.quiet:
                print(f"Step 5: Export - Exporting to {config.export_directory}...")

            config.export_directory.mkdir(parents=True, exist_ok=True)

            with GraphDatabase(database_path) as db:
                # Check if we have data to export
                has_nodes = False
                has_edges = False
                try:
                    nodes_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                    has_nodes = nodes_count > 0
                except Exception:
                    print("Error occured trying to query Node table.")
                    raise  # Table might not exist

                #TODO: See if we should if this table doesn't exist.
                try:
                    edges_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
                    has_edges = edges_count > 0
                except Exception:
                    print("Error occured trying to query Edge table.")
                    raise  # Table might not exist

                if not has_nodes and not has_edges:
                    if not config.quiet:
                        print("  No data to export (no nodes or edges found)")
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
                            print(f"Export completed: {archive_type} {archive_file}")
                    else:
                        # Export to loose files
                        nodes_file, edges_file = db.export_to_loose_files(
                            output_directory=config.export_directory,
                            graph_name=export_graph_name,
                            format=config.output_format,
                        )
                        exported_files.extend([nodes_file, edges_file])

                        if not config.quiet:
                            print(f"Export completed: {len(exported_files)} files exported")

            if not exported_files and not config.quiet:
                print("Warning - No files exported.")

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
            print(f"Merge pipeline completed successfully!")
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
            deduplicate_result=deduplicate_result,
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
            print(f"Merge pipeline failed!")
            print_operation_summary(summary)
        return MergeResult(
            success=False,
            join_result=join_result,
            deduplicate_result=deduplicate_result,
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
    **kwargs: Any,
) -> MergeConfig:
    """
    Create a MergeConfig from file paths with automatic FileSpec generation.

    This CLI helper converts Path objects to FileSpec objects and assembles
    a complete MergeConfig. File formats are auto-detected from extensions,
    and file stems are used as source names for provenance tracking.

    Args:
        node_files: List of Path objects for node KGX files
        edge_files: List of Path objects for edge KGX files
        mapping_files: List of Path objects for SSSOM mapping files
        output_database: Optional path for persistent output database
        skip_normalize: If True, skip the normalization step
        skip_prune: If True, skip the pruning step
        **kwargs: Additional MergeConfig parameters (e.g., quiet, show_progress,
            export_final, export_directory, archive, compress, graph_name)

    Returns:
        Fully configured MergeConfig ready for merge_graphs()
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
