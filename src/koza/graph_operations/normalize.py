"""
Normalize operation for applying SSSOM mappings to graph data.
"""

import time
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from koza.model.graph_operations import (
    FileLoadResult,
    FileSpec,
    KGXFormat,
    NormalizeConfig,
    NormalizeResult,
    OperationSummary,
)

from .utils import GraphDatabase, print_operation_summary


def normalize_graph(config: NormalizeConfig) -> NormalizeResult:
    """
    Apply SSSOM mappings to normalize node identifiers in edge references.

    This operation uses SSSOM (Simple Standard for Sharing Ontological Mappings)
    files to replace node identifiers in the edges table with their canonical
    equivalents. This is useful for harmonizing identifiers from different sources
    to a common namespace.

    The normalization process:
    1. Loads SSSOM mapping files (TSV format with YAML header)
    2. Creates a mappings table, deduplicating by object_id to prevent edge duplication
    3. Updates edge subject/object columns using the mappings (object_id -> subject_id)
    4. Preserves original identifiers in original_subject/original_object columns

    Note: Only edge references are normalized. Node IDs in the nodes table are
    not modified - use the mappings to update node IDs separately if needed.

    Args:
        config: NormalizeConfig containing:
            - database_path: Path to the DuckDB database to normalize
            - mapping_files: List of FileSpec objects for SSSOM mapping files
            - quiet: Suppress console output
            - show_progress: Display progress bars during loading

    Returns:
        NormalizeResult containing:
            - success: Whether the operation completed successfully
            - mappings_loaded: List of FileLoadResult with per-file statistics
            - edges_normalized: Count of edge references that were updated
            - final_stats: DatabaseStats with node/edge counts
            - total_time_seconds: Operation duration
            - summary: OperationSummary with status and messages
            - errors: List of error messages if any
            - warnings: List of warnings (e.g., duplicate mappings found)

    Raises:
        ValueError: If no nodes/edges tables exist or no mapping files load
    """
    start_time = time.time()
    mappings_loaded: list[FileLoadResult] = []
    errors = []
    warnings = []

    try:
        # Connect to existing database
        with GraphDatabase(config.database_path) as db:
            # Verify tables exist
            tables_check = db.conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name IN ('nodes', 'edges')
            """).fetchall()

            existing_tables = {row[0] for row in tables_check}

            if "nodes" not in existing_tables and "edges" not in existing_tables:
                raise ValueError("No nodes or edges tables found in database. Run 'koza join' first.")

            # Load SSSOM mapping files
            if config.mapping_files:
                if config.show_progress:
                    mapping_progress = tqdm(config.mapping_files, desc="Loading mapping files", unit="file")
                else:
                    mapping_progress = config.mapping_files

                for file_spec in mapping_progress:
                    if config.show_progress:
                        mapping_progress.set_description(f"Loading {file_spec.path.name}")

                    result = _load_sssom_file(db, file_spec)
                    mappings_loaded.append(result)

                    if result.errors:
                        errors.extend(result.errors)

                    if not config.quiet and not config.show_progress:
                        print(
                            f"  - {file_spec.path.name}: {result.records_loaded:,} mappings "
                            f"({result.detected_format.value} format)"
                        )

                # Create final mappings table (deduplicates by object_id)
                duplicate_mappings = _create_mappings_table(db, mappings_loaded)

                if duplicate_mappings > 0:
                    warning_msg = (
                        f"Found {duplicate_mappings} duplicate mappings "
                        f"(one object_id mapped to multiple subject_ids). "
                        f"Keeping only one mapping per object_id to prevent edge duplication."
                    )
                    warnings.append(warning_msg)
                    if not config.quiet:
                        print(f"⚠️  {warning_msg}")

                if not config.quiet:
                    mappings_count = db.conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0]
                    print(f"✓ Loaded {mappings_count:,} unique mappings")

            # Apply normalization to edges table if it exists
            edges_normalized = 0
            if "edges" in existing_tables:
                edges_normalized = _normalize_edges_table(db, config)
                if not config.quiet:
                    print(f"✓ Normalized {edges_normalized:,} edge subject/object references")
            else:
                if not config.quiet:
                    print("⚠️  No edges table found - normalization only applies to edge references")

            # Get final database statistics
            final_stats = db.get_stats()
            total_time = time.time() - start_time

            # Create operation summary
            success_message = (
                f"Applied {len(mappings_loaded)} mapping files, normalized {edges_normalized:,} edge references"
            )

            summary = OperationSummary(
                operation="normalize",
                success=True,
                message=success_message,
                stats=final_stats,
                files_processed=len(mappings_loaded),
                total_time_seconds=total_time,
                warnings=warnings,
                errors=errors,
            )

            if not config.quiet:
                print_operation_summary(summary)

            return NormalizeResult(
                success=True,
                mappings_loaded=mappings_loaded,
                edges_normalized=edges_normalized,
                final_stats=final_stats,
                total_time_seconds=total_time,
                summary=summary,
                errors=errors,
                warnings=warnings,
            )

    except Exception as e:
        total_time = time.time() - start_time
        error_msg = f"Normalize operation failed: {e}"
        errors.append(error_msg)
        logger.error(error_msg)

        summary = OperationSummary(
            operation="normalize",
            success=False,
            message=error_msg,
            stats=None,
            files_processed=len(mappings_loaded),
            total_time_seconds=total_time,
            warnings=warnings,
            errors=errors,
        )

        if not config.quiet:
            print_operation_summary(summary)

        return NormalizeResult(
            success=False,
            mappings_loaded=mappings_loaded,
            edges_normalized=0,
            final_stats=None,
            total_time_seconds=total_time,
            summary=summary,
            errors=errors,
            warnings=warnings,
        )


def _load_sssom_file(db: GraphDatabase, file_spec: FileSpec) -> FileLoadResult:
    """
    Load an SSSOM mapping file into a temporary table.

    SSSOM files are TSV format with a YAML metadata header (lines starting with #).
    This function loads the file using DuckDB's read_csv with comment='#' to skip
    the header, and creates a temporary table for later merging.

    The key columns used from SSSOM files are:
    - subject_id: The canonical/target identifier
    - object_id: The source identifier to be mapped

    Args:
        db: GraphDatabase instance with active connection
        file_spec: FileSpec for the SSSOM file (path and source_name)

    Returns:
        FileLoadResult containing:
            - records_loaded: Number of mappings loaded
            - temp_table_name: Name of the temporary table created
            - errors: List of any errors encountered
    """
    start_time = time.time()
    errors = []

    try:
        if not file_spec.path.exists():
            raise FileNotFoundError(f"File not found: {file_spec.path}")

        # Create unique temp table name for this mapping file
        safe_filename = file_spec.path.stem.replace("-", "_").replace(".", "_")
        temp_table_name = f"temp_mapping_{safe_filename}_{id(file_spec)}"

        # Load SSSOM file with comment='#' to skip YAML header
        create_sql = f"""
            CREATE TEMP TABLE {temp_table_name} AS
            SELECT *, '{file_spec.source_name or file_spec.path.stem}' as mapping_source 
            FROM read_csv('{file_spec.path}', 
                         delim='\\t', 
                         header=true, 
                         all_varchar=true,
                         comment='#',
                         ignore_errors=true)
        """

        db.conn.execute(create_sql)

        # Get record count
        count_result = db.conn.execute(f"SELECT COUNT(*) FROM {temp_table_name}").fetchone()
        records_loaded = count_result[0] if count_result else 0

        load_time = time.time() - start_time

        logger.info(
            f"Loaded {records_loaded} mappings from {file_spec.path} "
            f"into temp table {temp_table_name} in {load_time:.2f}s"
        )

        return FileLoadResult(
            file_spec=file_spec,
            records_loaded=records_loaded,
            detected_format=KGXFormat.TSV,  # SSSOM files are always TSV
            load_time_seconds=load_time,
            errors=errors,
            temp_table_name=temp_table_name,
        )

    except Exception as e:
        load_time = time.time() - start_time
        error_msg = f"Failed to load {file_spec.path}: {e}"
        errors.append(error_msg)
        logger.error(error_msg)

        return FileLoadResult(
            file_spec=file_spec,
            records_loaded=0,
            detected_format=KGXFormat.TSV,
            load_time_seconds=load_time,
            errors=errors,
        )


def _create_mappings_table(db: GraphDatabase, mapping_results: list[FileLoadResult]) -> int:
    """
    Create a unified mappings table from all loaded SSSOM temporary tables.

    Combines all temporary mapping tables using UNION ALL BY NAME and deduplicates
    by object_id to ensure each source identifier maps to exactly one target.

    SSSOM mappings can have one-to-many relationships (one object_id mapping to
    multiple subject_id values). This would cause the normalization JOIN to create
    duplicate edges with the same UUID. To prevent this, we deduplicate mappings
    by object_id, keeping only one mapping per object_id (ordered by mapping_source
    and subject_id for determinism).

    Args:
        db: GraphDatabase instance with active connection
        mapping_results: List of FileLoadResult objects with temp_table_name set

    Returns:
        Number of duplicate mappings that were removed during deduplication

    Raises:
        ValueError: If no mapping files loaded successfully
    """
    # Get temp tables that loaded successfully
    mapping_tables = []
    for result in mapping_results:
        if result.temp_table_name and not result.errors:
            mapping_tables.append(result.temp_table_name)

    if not mapping_tables:
        raise ValueError("No mapping files loaded successfully")

    # Create mappings table using UNION ALL BY NAME
    union_stmt = " UNION ALL BY NAME ".join([f"SELECT * FROM {table}" for table in mapping_tables])
    db.conn.execute(f"CREATE OR REPLACE TABLE mappings_raw AS {union_stmt}")

    # Count total and unique mappings
    total_count = db.conn.execute("SELECT COUNT(*) FROM mappings_raw").fetchone()[0]
    unique_count = db.conn.execute("SELECT COUNT(DISTINCT object_id) FROM mappings_raw").fetchone()[0]
    duplicate_count = total_count - unique_count

    if duplicate_count > 0:
        logger.warning(
            f"Found {duplicate_count} duplicate mappings (one object_id mapped to multiple subject_ids). "
            f"Keeping only one mapping per object_id to prevent edge duplication."
        )

    # Deduplicate by object_id, keeping the first mapping encountered
    # This is consistent with how duplicate nodes/edges are handled elsewhere
    db.conn.execute("""
        CREATE OR REPLACE TABLE mappings AS
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY object_id ORDER BY mapping_source, subject_id) as rn
            FROM mappings_raw
        ) WHERE rn = 1
    """)

    # Clean up raw table
    db.conn.execute("DROP TABLE mappings_raw")

    # Clean up temp tables
    for result in mapping_results:
        if result.temp_table_name and not result.errors:
            try:
                db.conn.execute(f"DROP TABLE {result.temp_table_name}")
                logger.debug(f"Cleaned up temp table {result.temp_table_name}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp table {result.temp_table_name}: {e}")

    logger.info(f"Created mappings table from {len(mapping_tables)} temp tables ({unique_count} unique mappings)")

    return duplicate_count


def _normalize_edges_table(db: GraphDatabase, config: NormalizeConfig) -> int:
    """
    Apply SSSOM mappings to normalize edge subject/object references.

    Updates the edges table by replacing subject and object IDs with their
    canonical equivalents from the mappings table. The original identifiers
    are preserved in original_subject and original_object columns.

    If original_subject/original_object columns already exist (from a previous
    normalization), they are preserved rather than overwritten.

    The normalization uses a LEFT JOIN on the mappings table:
    - If a mapping exists for subject/object, replace with the mapping's subject_id
    - If no mapping exists, keep the original identifier

    Args:
        db: GraphDatabase instance with active connection and mappings table
        config: NormalizeConfig (used for quiet setting)

    Returns:
        Number of edge references (subject or object) that were actually changed
    """
    # Check if original_subject and original_object columns already exist
    edge_columns_result = db.conn.execute("DESCRIBE edges").fetchall()
    existing_columns = {col[0] for col in edge_columns_result}
    has_original_subject = "original_subject" in existing_columns
    has_original_object = "original_object" in existing_columns

    # Build the query to preserve existing original columns while applying mappings
    if has_original_subject and has_original_object:
        # Both original columns exist - preserve them, only update if they're NULL
        create_temp_query = """
            CREATE TEMP TABLE edges_with_mappings AS
            SELECT 
                e.*,
                e.subject as current_subject,
                e.object as current_object,
                COALESCE(m_subj.subject_id, e.subject) as normalized_subject,
                COALESCE(m_obj.subject_id, e.object) as normalized_object,
                -- Preserve existing original values, set new ones only if currently NULL
                CASE WHEN e.original_subject IS NOT NULL THEN e.original_subject
                     WHEN COALESCE(m_subj.subject_id, e.subject) != e.subject THEN e.subject
                     ELSE NULL END as final_original_subject,
                CASE WHEN e.original_object IS NOT NULL THEN e.original_object
                     WHEN COALESCE(m_obj.subject_id, e.object) != e.object THEN e.object
                     ELSE NULL END as final_original_object
            FROM edges e
            LEFT JOIN mappings m_subj ON e.subject = m_subj.object_id
            LEFT JOIN mappings m_obj ON e.object = m_obj.object_id
        """

        update_query = """
            CREATE OR REPLACE TABLE edges AS
            SELECT 
                * EXCLUDE (subject, object, original_subject, original_object,
                          current_subject, current_object, normalized_subject, normalized_object,
                          final_original_subject, final_original_object),
                normalized_subject as subject,
                normalized_object as object,
                final_original_subject as original_subject,
                final_original_object as original_object
            FROM edges_with_mappings
        """

    elif has_original_subject or has_original_object:
        # Only one original column exists - handle both cases
        original_subject_expr = (
            "CASE WHEN e.original_subject IS NOT NULL THEN e.original_subject"
            "     WHEN COALESCE(m_subj.subject_id, e.subject) != e.subject THEN e.subject"
            "     ELSE NULL END"
            if has_original_subject
            else "CASE WHEN COALESCE(m_subj.subject_id, e.subject) != e.subject THEN e.subject ELSE NULL END"
        )

        original_object_expr = (
            "CASE WHEN e.original_object IS NOT NULL THEN e.original_object"
            "     WHEN COALESCE(m_obj.subject_id, e.object) != e.object THEN e.object"
            "     ELSE NULL END"
            if has_original_object
            else "CASE WHEN COALESCE(m_obj.subject_id, e.object) != e.object THEN e.object ELSE NULL END"
        )

        create_temp_query = f"""
            CREATE TEMP TABLE edges_with_mappings AS
            SELECT 
                e.*,
                e.subject as current_subject,
                e.object as current_object,
                COALESCE(m_subj.subject_id, e.subject) as normalized_subject,
                COALESCE(m_obj.subject_id, e.object) as normalized_object,
                {original_subject_expr} as final_original_subject,
                {original_object_expr} as final_original_object
            FROM edges e
            LEFT JOIN mappings m_subj ON e.subject = m_subj.object_id
            LEFT JOIN mappings m_obj ON e.object = m_obj.object_id
        """

        exclude_cols = [
            "subject",
            "object",
            "current_subject",
            "current_object",
            "normalized_subject",
            "normalized_object",
            "final_original_subject",
            "final_original_object",
        ]
        if has_original_subject:
            exclude_cols.append("original_subject")
        if has_original_object:
            exclude_cols.append("original_object")

        update_query = f"""
            CREATE OR REPLACE TABLE edges AS
            SELECT 
                * EXCLUDE ({", ".join(exclude_cols)}),
                normalized_subject as subject,
                normalized_object as object,
                final_original_subject as original_subject,
                final_original_object as original_object
            FROM edges_with_mappings
        """

    else:
        # No original columns exist - use the original logic
        create_temp_query = """
            CREATE TEMP TABLE edges_with_mappings AS
            SELECT 
                e.*,
                e.subject as current_subject,
                e.object as current_object,
                COALESCE(m_subj.subject_id, e.subject) as normalized_subject,
                COALESCE(m_obj.subject_id, e.object) as normalized_object
            FROM edges e
            LEFT JOIN mappings m_subj ON e.subject = m_subj.object_id
            LEFT JOIN mappings m_obj ON e.object = m_obj.object_id
        """

        update_query = """
            CREATE OR REPLACE TABLE edges AS
            SELECT 
                * EXCLUDE (subject, object, current_subject, current_object,
                          normalized_subject, normalized_object),
                normalized_subject as subject,
                normalized_object as object,
                CASE WHEN normalized_subject != current_subject 
                     THEN current_subject ELSE NULL END as original_subject,
                CASE WHEN normalized_object != current_object 
                     THEN current_object ELSE NULL END as original_object
            FROM edges_with_mappings
        """

    # Execute the queries
    db.conn.execute(create_temp_query)

    # Count how many edge references will be normalized (only count actual changes)
    normalize_count_result = db.conn.execute("""
        SELECT COUNT(*) FROM edges_with_mappings 
        WHERE normalized_subject != current_subject 
           OR normalized_object != current_object
    """).fetchone()
    edges_normalized = normalize_count_result[0] if normalize_count_result else 0

    # Update edges table
    db.conn.execute(update_query)

    logger.info(f"Normalized {edges_normalized} edge subject/object references")
    if has_original_subject or has_original_object:
        logger.info("Preserved existing original_subject/original_object columns")

    return edges_normalized


def prepare_mapping_file_specs_from_paths(mapping_paths: list[Path], source_name: str | None = None) -> list[FileSpec]:
    """
    Convert a list of SSSOM mapping file paths to FileSpec objects.

    This CLI helper creates FileSpec objects for SSSOM mapping files, which are
    always in TSV format. Each file's stem is used as its source_name for
    tracking which mappings came from which file.

    Args:
        mapping_paths: List of Path objects pointing to SSSOM mapping files
        source_name: Optional source name to apply to all files (overrides per-file names)

    Returns:
        List of FileSpec objects configured for SSSOM mapping files

    Raises:
        FileNotFoundError: If any mapping file does not exist
    """
    file_specs = []

    for path in mapping_paths:
        if not path.exists():
            raise FileNotFoundError(f"Mapping file not found: {path}")

        # SSSOM files are always TSV format
        file_spec = FileSpec(
            path=path,
            format=KGXFormat.TSV,
            file_type=None,  # Mappings don't have a file type
            source_name=source_name or path.stem,
        )
        file_specs.append(file_spec)

    return file_specs
