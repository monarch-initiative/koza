"""
Join operation for combining multiple KGX files into a unified DuckDB database.
"""

import time
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from koza.model.graph_operations import FileLoadResult, FileSpec, JoinConfig, JoinResult, KGXFileType, OperationSummary

from .schema import generate_schema_report, print_schema_summary, write_schema_report_yaml
from .utils import GraphDatabase, print_operation_summary


def join_graphs(config: JoinConfig) -> JoinResult:
    """
    Join multiple KGX files into a unified DuckDB database.

    This operation loads node and edge files from various formats (TSV, JSONL, Parquet)
    into a single DuckDB database, combining them using UNION ALL BY NAME to handle
    schema differences across files. Each file's records are tagged with a source
    identifier for provenance tracking.

    The join process:
    1. Creates or opens a DuckDB database (in-memory if no path specified)
    2. Loads each node file into a temporary table with format auto-detection
    3. Loads each edge file into a temporary table with format auto-detection
    4. Optionally generates a schema report analyzing column types and values
    5. Combines all temporary tables into final 'nodes' and 'edges' tables

    Args:
        config: JoinConfig containing:
            - node_files: List of FileSpec objects for node files
            - edge_files: List of FileSpec objects for edge files
            - database_path: Optional path for persistent database (None for in-memory)
            - schema_reporting: Whether to generate schema analysis report
            - generate_provided_by: Whether to add provided_by column from source names
            - quiet: Suppress console output
            - show_progress: Display progress bars during loading

    Returns:
        JoinResult containing:
            - files_loaded: List of FileLoadResult with per-file statistics
            - final_stats: DatabaseStats with node/edge counts and database size
            - schema_report: Optional schema analysis if schema_reporting enabled
            - total_time_seconds: Operation duration
            - database_path: Path to the created database

    Raises:
        Exception: If file loading fails or database operations error
    """
    start_time = time.time()
    files_loaded: list[FileLoadResult] = []

    try:
        # Initialize database
        with GraphDatabase(config.database_path) as db:
            # Load node files
            if config.show_progress:
                node_progress = tqdm(config.node_files, desc="Loading node files", unit="file")
            else:
                node_progress = config.node_files

            for file_spec in node_progress:
                if config.show_progress:
                    node_progress.set_description(f"Loading {file_spec.path.name}")

                result = db.load_file(file_spec, generate_provided_by=config.generate_provided_by)
                files_loaded.append(result)

                if not config.quiet and not config.show_progress:
                    print(
                        f"  - {file_spec.path.name}: {result.records_loaded:,} records "
                        f"({result.detected_format.value} format)"
                    )

            # Load edge files
            if config.show_progress:
                edge_progress = tqdm(config.edge_files, desc="Loading edge files", unit="file")
            else:
                edge_progress = config.edge_files

            for file_spec in edge_progress:
                if config.show_progress:
                    edge_progress.set_description(f"Loading {file_spec.path.name}")

                result = db.load_file(file_spec, generate_provided_by=config.generate_provided_by)
                files_loaded.append(result)

                if not config.quiet and not config.show_progress:
                    print(
                        f"  - {file_spec.path.name}: {result.records_loaded:,} records "
                        f"({result.detected_format.value} format)"
                    )

            # Generate schema report BEFORE creating final tables (which cleans up temp tables)
            schema_report = None
            if config.schema_reporting:
                schema_report = generate_schema_report(db)
                logger.info(f"Generated schema report: {len(schema_report) if schema_report else 0} entries")

            # Create final tables using UNION ALL BY NAME
            db.create_final_tables(files_loaded)

            # Get final statistics
            final_stats = db.get_stats()

        total_time = time.time() - start_time

        # Create result
        result = JoinResult(
            files_loaded=files_loaded,
            final_stats=final_stats,
            schema_report=schema_report,
            total_time_seconds=total_time,
            database_path=config.database_path,
        )

        # Print summary if not quiet
        if not config.quiet:
            _print_join_summary(result)

        # Write schema report file if requested (regardless of quiet mode)
        if result.schema_report and result.database_path:
            write_schema_report_yaml(result.schema_report, result.database_path, "join")

        return result

    except Exception as e:
        total_time = time.time() - start_time

        if not config.quiet:
            summary = OperationSummary(
                operation="Join",
                success=False,
                message=f"Operation failed: {e}",
                files_processed=len(files_loaded),
                total_time_seconds=total_time,
                errors=[str(e)],
            )
            print_operation_summary(summary)

        raise


def _print_join_summary(result: JoinResult):
    """Print formatted join summary."""
    total_files = len(result.files_loaded)
    successful_loads = len([f for f in result.files_loaded if not f.errors])

    print(f"✓ Join completed successfully")
    print(f"  📁 Files processed: {total_files} ({successful_loads} successful)")

    # Group files by format
    format_counts = {}
    for file_result in result.files_loaded:
        format_str = file_result.detected_format.value
        if format_str not in format_counts:
            format_counts[format_str] = 0
        format_counts[format_str] += 1

    format_summary = ", ".join([f"{count} {fmt}" for fmt, count in format_counts.items()])
    print(f"  📊 Format distribution: {format_summary}")

    print(f"  📈 Final database:")
    print(f"    - Nodes: {result.final_stats.nodes:,}")
    print(f"    - Edges: {result.final_stats.edges:,}")

    if result.database_path:
        print(f"    - Database: {result.database_path} ({result.final_stats.database_size_mb:.1f} MB)")
    else:
        print(f"    - Database: in-memory")

    print(f"  ⏱️  Total time: {result.total_time_seconds:.2f}s")

    # Show schema analysis if available
    if result.schema_report:
        print_schema_summary(result.schema_report)

    # Show any errors
    error_files = [f for f in result.files_loaded if f.errors]
    if error_files:
        print(f"  ⚠️  Files with errors:")
        for file_result in error_files:
            print(f"    - {file_result.file_spec.path.name}: {len(file_result.errors)} errors")


# CLI helper function
def prepare_file_specs_from_paths(
    node_paths: list[str], edge_paths: list[str]
) -> tuple[list[FileSpec], list[FileSpec]]:
    """
    Convert file paths to FileSpec objects with format auto-detection.

    This CLI helper expands glob patterns and creates FileSpec objects for each
    matched file. The file format (TSV, JSONL, Parquet) is auto-detected from
    the file extension. Each file's stem is used as its source_name for
    provenance tracking.

    Args:
        node_paths: List of node file paths or glob patterns (e.g., "data/*.tsv")
        edge_paths: List of edge file paths or glob patterns (e.g., "data/*_edges.jsonl")

    Returns:
        Tuple of (node_file_specs, edge_file_specs) with FileSpec objects
        configured for the appropriate file type (NODES or EDGES)
    """
    import glob

    node_specs = []
    for path_str in node_paths:
        # Check if this is a glob pattern
        if "*" in path_str or "?" in path_str:
            # Expand glob pattern
            expanded_paths = glob.glob(path_str)
            for expanded_path in sorted(expanded_paths):
                path = Path(expanded_path)
                spec = FileSpec(
                    path=path,
                    file_type=KGXFileType.NODES,
                    source_name=path.stem,  # Use filename as source name
                )
                node_specs.append(spec)
        else:
            # Regular path
            path = Path(path_str)
            spec = FileSpec(
                path=path,
                file_type=KGXFileType.NODES,
                source_name=path.stem,  # Use filename as source name
            )
            node_specs.append(spec)

    edge_specs = []
    for path_str in edge_paths:
        # Check if this is a glob pattern
        if "*" in path_str or "?" in path_str:
            # Expand glob pattern
            expanded_paths = glob.glob(path_str)
            for expanded_path in sorted(expanded_paths):
                path = Path(expanded_path)
                spec = FileSpec(
                    path=path,
                    file_type=KGXFileType.EDGES,
                    source_name=path.stem,  # Use filename as source name
                )
                edge_specs.append(spec)
        else:
            # Regular path
            path = Path(path_str)
            spec = FileSpec(
                path=path,
                file_type=KGXFileType.EDGES,
                source_name=path.stem,  # Use filename as source name
            )
            edge_specs.append(spec)

    return node_specs, edge_specs
