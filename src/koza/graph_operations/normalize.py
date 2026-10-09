"""
Normalize operation for applying SSSOM mappings to graph data.
"""

import time
from pathlib import Path
from typing import NamedTuple

from loguru import logger
from tqdm import tqdm

from koza.model.graph_operations import (
    MAPPING_PREDICATE_IRI_PREFIXES,
    FileLoadResult,
    FileSpec,
    KGXFormat,
    NormalizeConfig,
    NormalizeResult,
    OperationSummary,
)

from .graph_schema import ensure_slots
from .slots import edges
from .utils import GraphDatabase, print_operation_summary


# SSSOM predicates that assert identity. Everything else (closeMatch, broadMatch,
# narrowMatch, relatedMatch, ...) asserts something weaker and is only applied when the
# caller explicitly opts in via NormalizeConfig.use_match.
EXACT_MATCH_PREDICATES = frozenset({"skos:exactMatch"})


class MappingsTableSummary(NamedTuple):
    """Outcome of building the unified `mappings` table."""

    duplicate_count: int
    predicate_counts: dict[str | None, int]
    filtered_out_count: int
    has_predicate_column: bool
    # Rows from files that carry predicate_id which survived the use_match filter
    kept_with_predicate_count: int = 0


# Internal marker column recording, per row, whether its source file had a predicate_id column.
_HAS_PREDICATE_MARKER = "_koza_has_predicate_id"


DECLARED_OUTPUTS: dict[str, dict[str, dict]] = {
    "Association": {
        "original_subject": {
            "description": "Subject ID before normalization (SSSOM-applied).",
            "range": "string",
            "multivalued": False,
        },
        "original_object": {
            "description": "Object ID before normalization (SSSOM-applied).",
            "range": "string",
            "multivalued": False,
        },
    },
}


def _non_exact_predicate_warning(config: NormalizeConfig, summary: MappingsTableSummary) -> str | None:
    """
    Build the warning shown when non-exact mappings are applied as identities.

    Only fires when the caller did not set `use_match`: in that case every row is applied,
    so a `skos:closeMatch` or `skos:broadMatch` row rewires an edge endpoint exactly as an
    `skos:exactMatch` row does. Naming the per-predicate counts makes that visible without
    changing any output.
    """
    if config.use_match or not summary.has_predicate_column:
        return None

    non_exact = {
        predicate: count
        for predicate, count in summary.predicate_counts.items()
        if predicate is not None and predicate not in EXACT_MATCH_PREDICATES
    }
    if not non_exact:
        return None

    breakdown = ", ".join(f"{predicate}: {count:,}" for predicate, count in sorted(non_exact.items()))
    total = sum(non_exact.values())
    return (
        f"Applying {total:,} non-exact SSSOM mappings as identity rewrites because use_match is not set "
        f"({breakdown}). Set use_match=['skos:exactMatch'] to apply only exact matches."
    )


def _use_match_warnings(config: NormalizeConfig, summary: MappingsTableSummary) -> list[str]:
    """
    Diagnose a use_match filter that is likely misconfigured.

    Predicates are compared exactly (after contracting known IRIs), so a case slip such as
    `skos:exactmatch` silently matches nothing. Surface that, and the case where the filter
    removed every mapping that had a predicate_id, instead of quietly normalizing 0 edges.
    """
    if not config.use_match:
        return []

    if not summary.has_predicate_column:
        return [
            f"use_match={config.use_match} was requested but the loaded SSSOM mappings have no "
            f"predicate_id column; applying all mappings unfiltered."
        ]

    found = sorted(p for p in summary.predicate_counts if p is not None)
    messages = []
    unmatched = [p for p in config.use_match if p not in summary.predicate_counts]
    if unmatched:
        messages.append(
            f"use_match predicates {unmatched} matched no SSSOM mappings "
            f"(predicates present: {found or 'none'}). Predicate matching is exact and case-sensitive."
        )
    if summary.kept_with_predicate_count == 0 and summary.filtered_out_count > 0:
        messages.append(
            f"use_match={config.use_match} removed all {summary.filtered_out_count:,} SSSOM mappings "
            f"that carry a predicate_id; no such mappings will be applied."
        )
    return messages


def normalize_graph(config: NormalizeConfig) -> NormalizeResult:
    """
    Apply SSSOM mappings to normalize node identifiers in edge references.

    This operation uses SSSOM (Simple Standard for Sharing Ontological Mappings)
    files to replace node identifiers in the edges table with their canonical
    equivalents. This is useful for harmonizing identifiers from different sources
    to a common namespace.

    The normalization process:
    1. Loads SSSOM mapping files (TSV format with YAML header)
    2. Optionally filters mappings by predicate_id (see config.use_match)
    3. Creates a mappings table, deduplicating by object_id to prevent edge duplication
    4. Updates edge subject/object columns using the mappings (object_id -> subject_id)
    5. Preserves original identifiers in original_subject/original_object columns

    Note: Only edge references are normalized. Node IDs in the nodes table are
    not modified - use the mappings to update node IDs separately if needed.

    Args:
        config: NormalizeConfig containing:
            - database_path: Path to the DuckDB database to normalize
            - mapping_files: List of FileSpec objects for SSSOM mapping files
            - use_match: Optional list of SSSOM predicate CURIEs to apply, e.g.
              ["skos:exactMatch"]. When None (the default) every mapping row is applied
              regardless of predicate_id, and a warning names the non-exact predicates found.
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

                # Create final mappings table (filters by predicate_id, deduplicates by object_id)
                mappings_summary = _create_mappings_table(db, mappings_loaded, use_match=config.use_match)

                predicate_warnings = _use_match_warnings(config, mappings_summary)
                non_exact_warning = _non_exact_predicate_warning(config, mappings_summary)
                if non_exact_warning:
                    predicate_warnings.append(non_exact_warning)
                for predicate_warning in predicate_warnings:
                    warnings.append(predicate_warning)
                    logger.warning(predicate_warning)
                    if not config.quiet:
                        print(f"⚠️  {predicate_warning}")

                if mappings_summary.duplicate_count > 0:
                    warning_msg = (
                        f"Found {mappings_summary.duplicate_count} duplicate mappings "
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


def _create_mappings_table(
    db: GraphDatabase,
    mapping_results: list[FileLoadResult],
    use_match: list[str] | None = None,
) -> MappingsTableSummary:
    """
    Create a unified mappings table from all loaded SSSOM temporary tables.

    Combines all temporary mapping tables using UNION ALL BY NAME, optionally filters
    on `predicate_id`, and deduplicates by object_id to ensure each source identifier
    maps to exactly one target.

    Normalization rewrites an identifier to another identifier, which only makes sense
    for mapping predicates that assert identity. When `use_match` is provided, rows whose
    `predicate_id` is not listed are dropped before deduplication, so a `skos:broadMatch`
    row cannot collapse two distinct concepts. When `use_match` is None every row is
    applied, which is the historical behaviour.

    SSSOM mappings can have one-to-many relationships (one object_id mapping to
    multiple subject_id values). This would cause the normalization JOIN to create
    duplicate edges with the same UUID. To prevent this, we deduplicate mappings
    by object_id, keeping only one mapping per object_id (ordered by mapping_source
    and subject_id for determinism).

    Args:
        db: GraphDatabase instance with active connection
        mapping_results: List of FileLoadResult objects with temp_table_name set
        use_match: Optional list of SSSOM predicate CURIEs to keep, e.g.
            ["skos:exactMatch"]. Rows from files without a predicate_id column are always
            kept, so such files keep working unchanged. Rows from files that do have the
            column but leave it blank are dropped when use_match is set. Known skos/owl/
            rdfs/semapv predicate IRIs are contracted to CURIEs before comparison.

    Returns:
        MappingsTableSummary with the duplicate count, per-predicate row counts before
        filtering, the number of rows dropped by the predicate filter, and whether the
        loaded mappings had a predicate_id column at all

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

    # SSSOM files are not required to carry predicate_id. Record per file whether it does, so
    # that after the union a NULL predicate_id from a file without the column (kept: we cannot
    # filter what is not there) can be told apart from a blank cell in a file with the column.
    selects = []
    for table in mapping_tables:
        table_columns = {row[0] for row in db.conn.execute(f"DESCRIBE {table}").fetchall()}
        has_column = "predicate_id" in table_columns
        selects.append(f"SELECT *, {str(has_column).upper()} AS {_HAS_PREDICATE_MARKER} FROM {table}")

    # Create mappings table using UNION ALL BY NAME
    union_stmt = " UNION ALL BY NAME ".join(selects)
    db.conn.execute(f"CREATE OR REPLACE TABLE mappings_raw AS {union_stmt}")

    # UNION ALL BY NAME only produces the column if at least one input file had it.
    columns = {row[0] for row in db.conn.execute("DESCRIBE mappings_raw").fetchall()}
    has_predicate_column = "predicate_id" in columns

    predicate_counts: dict[str | None, int] = {}
    filtered_out_count = 0
    kept_with_predicate_count = 0

    if has_predicate_column:
        # Contract IRI-form predicates (e.g. http://www.w3.org/2004/02/skos/core#exactMatch)
        # to CURIEs so they compare equal to use_match entries and count correctly in warnings.
        for iri_prefix, curie_prefix in MAPPING_PREDICATE_IRI_PREFIXES.items():
            db.conn.execute(
                "UPDATE mappings_raw SET predicate_id = ? || substr(predicate_id, ?) "
                "WHERE starts_with(predicate_id, ?)",
                [curie_prefix, len(iri_prefix) + 1, iri_prefix],
            )

        predicate_counts = {
            row[0]: row[1]
            for row in db.conn.execute(
                "SELECT predicate_id, COUNT(*) AS n FROM mappings_raw GROUP BY predicate_id ORDER BY n DESC"
            ).fetchall()
        }

        if use_match:
            # Rows from a file without the column are left alone: dropping them would silently
            # discard the whole file. Rows from a file with the column but a blank predicate_id
            # do not assert any of the requested predicates, so they are dropped.
            rows_before = db.conn.execute("SELECT COUNT(*) FROM mappings_raw").fetchone()[0]
            db.conn.execute(
                f"DELETE FROM mappings_raw WHERE {_HAS_PREDICATE_MARKER} "
                "AND (predicate_id IS NULL OR NOT list_contains(?::VARCHAR[], predicate_id))",
                [list(use_match)],
            )
            rows_after = db.conn.execute("SELECT COUNT(*) FROM mappings_raw").fetchone()[0]
            filtered_out_count = rows_before - rows_after
            kept_with_predicate_count = db.conn.execute(
                f"SELECT COUNT(*) FROM mappings_raw WHERE {_HAS_PREDICATE_MARKER}"
            ).fetchone()[0]

            logger.info(
                f"Filtered SSSOM mappings to predicates {sorted(use_match)}: "
                f"kept {rows_after}, dropped {filtered_out_count}"
            )

    db.conn.execute(f"ALTER TABLE mappings_raw DROP COLUMN {_HAS_PREDICATE_MARKER}")

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

    return MappingsTableSummary(
        duplicate_count=duplicate_count,
        predicate_counts=predicate_counts,
        filtered_out_count=filtered_out_count,
        has_predicate_column=has_predicate_column,
        kept_with_predicate_count=kept_with_predicate_count,
    )


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
    # Guarantee the original_* columns exist before we reference them. After
    # this, the SQL has a single shape that preserves existing original values
    # (if non-NULL) and computes new ones only when normalization actually
    # changes the identifier.
    ensure_slots(db.conn, "edges", [edges.original_subject, edges.original_object])

    db.conn.execute(f"""
        CREATE TEMP TABLE edges_with_mappings AS
        SELECT
            e.*,
            e.{edges.subject} as current_subject,
            e.{edges.object} as current_object,
            COALESCE(m_subj.subject_id, e.{edges.subject}) as normalized_subject,
            COALESCE(m_obj.subject_id, e.{edges.object}) as normalized_object,
            CASE WHEN e.{edges.original_subject} IS NOT NULL THEN e.{edges.original_subject}
                 WHEN COALESCE(m_subj.subject_id, e.{edges.subject}) != e.{edges.subject} THEN e.{edges.subject}
                 ELSE NULL END as final_original_subject,
            CASE WHEN e.{edges.original_object} IS NOT NULL THEN e.{edges.original_object}
                 WHEN COALESCE(m_obj.subject_id, e.{edges.object}) != e.{edges.object} THEN e.{edges.object}
                 ELSE NULL END as final_original_object
        FROM edges e
        LEFT JOIN mappings m_subj ON e.{edges.subject} = m_subj.object_id
        LEFT JOIN mappings m_obj ON e.{edges.object} = m_obj.object_id
    """)

    edges_normalized = db.conn.execute("""
        SELECT COUNT(*) FROM edges_with_mappings
        WHERE normalized_subject != current_subject
           OR normalized_object != current_object
    """).fetchone()[0]

    db.conn.execute(f"""
        CREATE OR REPLACE TABLE edges AS
        SELECT
            * EXCLUDE ({edges.subject}, {edges.object}, {edges.original_subject}, {edges.original_object},
                       current_subject, current_object, normalized_subject, normalized_object,
                       final_original_subject, final_original_object),
            normalized_subject as {edges.subject},
            normalized_object as {edges.object},
            final_original_subject as {edges.original_subject},
            final_original_object as {edges.original_object}
        FROM edges_with_mappings
    """)

    logger.info(f"Normalized {edges_normalized} edge subject/object references")
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
