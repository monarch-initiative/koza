"""
Append operation for adding new KGX files to existing databases.

Handles schema evolution, incremental updates, and optional deduplication
while preserving existing graph structure.
"""

import time

from loguru import logger
from tqdm import tqdm

from koza.model.graph_operations import AppendConfig, AppendResult, FileLoadResult, KGXFormat, OperationSummary

from .schema import generate_schema_report, print_schema_summary, write_schema_report_yaml
from .utils import GraphDatabase, get_duckdb_read_statement, print_operation_summary


def append_graphs(config: AppendConfig) -> AppendResult:
    """
    Append new KGX files to an existing DuckDB database with schema evolution.

    This operation adds records from new KGX files to an existing database,
    automatically handling schema differences. New columns in the input files
    are added to the existing tables, allowing incremental updates to a graph
    without re-processing all source files.

    The append process:
    1. Connects to an existing DuckDB database
    2. Records the initial schema and statistics
    3. For each new file, loads into a temp table and compares schema
    4. Adds any new columns to the main table (schema evolution)
    5. Inserts records using UNION ALL BY NAME for schema compatibility
    6. Optionally deduplicates after appending
    7. Generates a schema report if requested

    Args:
        config: AppendConfig containing:
            - database_path: Path to the existing DuckDB database
            - node_files: List of FileSpec objects for new node files
            - edge_files: List of FileSpec objects for new edge files
            - deduplicate: Whether to remove duplicates after appending
            - schema_reporting: Whether to generate schema analysis report
            - quiet: Suppress console output
            - show_progress: Display progress bars during loading

    Returns:
        AppendResult containing:
            - database_path: Path to the updated database
            - files_loaded: List of FileLoadResult with per-file statistics
            - records_added: Net change in record count (nodes + edges)
            - new_columns_added: Count of new columns added via schema evolution
            - schema_changes: List of descriptions of schema changes
            - final_stats: DatabaseStats with updated counts
            - schema_report: Optional schema analysis if enabled
            - duplicates_handled: Count of duplicates removed (if deduplication enabled)
            - total_time_seconds: Operation duration

    Raises:
        Exception: If database connection fails or file operations error
    """
    start_time = time.time()
    files_loaded: list[FileLoadResult] = []
    schema_changes: list[str] = []
    new_columns_added = 0

    try:
        # Connect to existing database
        with GraphDatabase(config.database_path) as db:
            if not config.quiet:
                print(f" Appending to existing database: {config.database_path}")

            # Get initial schema before appending
            initial_node_schema = _get_table_schema(db, "nodes")
            initial_edge_schema = _get_table_schema(db, "edges")
            initial_stats = db.get_stats()

            # Load node files
            if config.node_files:
                if not config.quiet:
                    print(f" Loading {len(config.node_files)} node files...")

                files_loaded.extend(_append_files(db, config.node_files, "nodes", config))

            # Load edge files
            if config.edge_files:
                if not config.quiet:
                    print(f" Loading {len(config.edge_files)} edge files...")

                files_loaded.extend(_append_files(db, config.edge_files, "edges", config))

            # Detect schema changes
            final_node_schema = _get_table_schema(db, "nodes")
            final_edge_schema = _get_table_schema(db, "edges")

            node_changes, node_new_cols = _compare_schemas("nodes", initial_node_schema, final_node_schema)
            edge_changes, edge_new_cols = _compare_schemas("edges", initial_edge_schema, final_edge_schema)

            schema_changes.extend(node_changes)
            schema_changes.extend(edge_changes)
            new_columns_added = node_new_cols + edge_new_cols

            # Handle deduplication if requested
            duplicates_handled = 0
            if config.deduplicate:
                if not config.quiet:
                    print(" Performing deduplication...")
                duplicates_handled = _deduplicate_tables(db, config)

            # Generate schema report if requested
            schema_report = None
            if config.schema_reporting:
                schema_report = generate_schema_report(db)

            # Get final statistics
            final_stats = db.get_stats()

        total_time = time.time() - start_time

        # Calculate records added
        records_added = final_stats.nodes + final_stats.edges - (initial_stats.nodes + initial_stats.edges)

        # Create result
        result = AppendResult(
            database_path=config.database_path,
            files_loaded=files_loaded,
            records_added=records_added,
            new_columns_added=new_columns_added,
            schema_changes=schema_changes,
            final_stats=final_stats,
            schema_report=schema_report,
            duplicates_handled=duplicates_handled,
            total_time_seconds=total_time,
        )

        # Print summary if not quiet
        if not config.quiet:
            _print_append_summary(result, initial_stats)

            # Print schema report if available
            if result.schema_report:
                print_schema_summary(result.schema_report)

        # Write schema report file if requested (regardless of quiet mode)
        if result.schema_report:
            write_schema_report_yaml(result.schema_report, result.database_path, "append")

        return result

    except Exception as e:
        total_time = time.time() - start_time

        if not config.quiet:
            summary = OperationSummary(
                operation="Append",
                success=False,
                message=f"Operation failed: {e}",
                files_processed=len(files_loaded),
                total_time_seconds=total_time,
                errors=[str(e)],
            )
            print_operation_summary(summary)

        raise


def _get_table_schema(db: GraphDatabase, table_name: str) -> dict[str, str]:
    """
    Get the current schema of a table as a column name to type mapping.

    Args:
        db: GraphDatabase instance with active connection
        table_name: Name of the table to describe ("nodes" or "edges")

    Returns:
        Dict mapping column names to their DuckDB data types, or empty dict if table doesn't exist
    """
    try:
        describe_result = db.conn.execute(f"DESCRIBE {table_name}").fetchall()
        return {col[0]: col[1] for col in describe_result}
    except Exception:
        # Table doesn't exist yet
        return {}


def _compare_schemas(table_name: str, old_schema: dict[str, str], new_schema: dict[str, str]) -> tuple[list[str], int]:
    """
    Compare old and new schemas to identify added columns.

    Args:
        table_name: Name of the table being compared (for human-readable output)
        old_schema: Dict of column names to types before append
        new_schema: Dict of column names to types after append

    Returns:
        Tuple of:
            - change_descriptions: List of human-readable descriptions of changes
            - new_columns_count: Number of columns that were added
    """
    changes = []
    new_columns = set(new_schema.keys()) - set(old_schema.keys())

    if new_columns:
        changes.append(f"Added {len(new_columns)} new columns to {table_name}: {', '.join(sorted(new_columns))}")

    return changes, len(new_columns)


def _append_files(db: GraphDatabase, file_specs: list, table_type: str, config: AppendConfig) -> list[FileLoadResult]:
    """
    Append multiple files to an existing table with schema evolution support.

    Iterates through the provided file specs, loading each into the target table.
    New columns discovered in the files are automatically added to the existing
    table schema.

    Args:
        db: GraphDatabase instance with active connection
        file_specs: List of FileSpec objects for files to append
        table_type: Target table name ("nodes" or "edges")
        config: AppendConfig for quiet/progress settings

    Returns:
        List of FileLoadResult objects with per-file load statistics
    """

    files_loaded = []

    # Use progress bar if requested
    if config.show_progress:
        file_progress = tqdm(file_specs, desc=f"Loading {table_type} files", unit="file")
    else:
        file_progress = file_specs

    for file_spec in file_progress:
        if config.show_progress:
            file_progress.set_description(f"Loading {file_spec.path.name}")

        result = _append_single_file(db, file_spec, table_type)
        files_loaded.append(result)

        if not config.quiet and not config.show_progress:
            print(
                f"  - {file_spec.path.name}: {result.records_loaded:,} records ({result.detected_format.value} format)"
            )

    return files_loaded


def _is_list_type(duckdb_type: str) -> bool:
    """Whether a DuckDB type string denotes a LIST (e.g. `VARCHAR[]`)."""
    return duckdb_type.strip().upper().endswith("[]")


def _is_json_type(duckdb_type: str) -> bool:
    """Whether a DuckDB type string is `JSON` — what `read_json` infers for a
    column whose rows mix scalars and arrays."""
    return duckdb_type.strip().upper() == "JSON"


def _is_nested_type(duckdb_type: str) -> bool:
    """Whether a value of this type cannot be rendered as a plain scalar
    (a list, struct, map or JSON value)."""
    upper = duckdb_type.strip().upper()
    return _is_list_type(upper) or upper == "JSON" or upper.startswith(("STRUCT", "MAP", "UNION"))


def _json_column_as_list(db: GraphDatabase, temp_table_name: str, col_name: str, source: str) -> str:
    """SQL rendering a mixed scalar/array `JSON` column as a `VARCHAR[]`.

    A JSON scalar becomes a one-element list, an array its (string) elements,
    and a JSON `null` or SQL NULL becomes NULL. Objects and nested arrays have no
    faithful flat rendering, so they are rejected rather than stringified.
    """
    quoted = f'"{col_name}"'
    bad = db.conn.execute(
        f"SELECT COUNT(*) FROM {temp_table_name} WHERE json_type({quoted}) = 'OBJECT' "
        f"OR (json_type({quoted}) = 'ARRAY' "
        f"AND list_has_any(json_type({quoted}, '$[*]'), ['ARRAY', 'OBJECT']))"
    ).fetchone()
    if bad and bad[0]:
        raise ValueError(
            f"{source}: column '{col_name}' holds JSON objects or nested arrays in {bad[0]:,} row(s); "
            f"refusing to insert them as strings"
        )
    return (
        f"CASE WHEN {quoted} IS NULL OR json_type({quoted}) = 'NULL' THEN NULL "
        f"WHEN json_type({quoted}) = 'ARRAY' THEN json_extract_string({quoted}, '$[*]') "
        f"ELSE [json_extract_string({quoted}, '$')] END"
    )


def _conform_temp_table_types(
    db: GraphDatabase,
    temp_table_name: str,
    file_columns: dict[str, str],
    existing_schema: dict[str, str],
    source: str,
    split_pipes: bool = False,
) -> dict[str, str]:
    """Reconcile LIST-vs-scalar mismatches between an incoming file and the target table.

    `UNION ALL BY NAME` casts a `VARCHAR[]` into a `VARCHAR` column by taking
    DuckDB's list representation, so a KGX jsonl `["biolink:Procedure"]` lands as
    the literal string `['biolink:Procedure']` — a value no category filter or
    grouping will ever match, inserted without a warning (issue #247).

    Conform each shared column to the target's shape instead:

    - LIST value into a scalar column: keep the first non-NULL element, matching
      merge's `force_single_valued` semantics, and warn about rows where that
      discards data.
    - scalar value into a LIST column: for TSV input (`split_pipes`), split the
      KGX pipe-delimited value into its items (trimmed, empties dropped), as join
      does; otherwise wrap in a one-element list. NULL stays NULL.
    - `JSON` column (jsonl mixing scalars and arrays in one field): render each row
      as a list first, then conform as above.
    - nested values (lists of lists, JSON objects) with no flat rendering raise
      `ValueError` instead of being inserted as repr strings.

    Returns the temp table's column types after conforming.
    """
    projections: list[str] = []
    collapsed: list[str] = []
    wrapped: list[str] = []
    multi_value_checks: list[tuple[str, str]] = []

    for col_name, file_type in file_columns.items():
        target_type = existing_schema.get(col_name)
        quoted = f'"{col_name}"'

        if target_type is None or _is_json_type(target_type) or file_type == target_type:
            projections.append(quoted)
            continue

        target_is_list = _is_list_type(target_type)

        if _is_json_type(file_type):
            list_expr = _json_column_as_list(db, temp_table_name, col_name, source)
        elif _is_list_type(file_type):
            if _is_nested_type(file_type.strip()[:-2]):
                raise ValueError(
                    f"{source}: column '{col_name}' is {file_type} but the target column is "
                    f"{target_type}; refusing to insert nested values as strings"
                )
            if target_is_list:
                # Same (flat) shape; let the insert cast the element type.
                projections.append(quoted)
                continue
            list_expr = quoted
        else:
            if not target_is_list:
                projections.append(quoted)
                continue
            # Scalar → list. NULL stays NULL rather than becoming [NULL].
            element_type = target_type.strip()[:-2]
            if split_pipes and file_type.strip().upper() == "VARCHAR":
                projections.append(
                    f"CASE WHEN {quoted} IS NULL OR trim({quoted}) = '' THEN NULL "
                    f"ELSE CAST(list_filter(list_transform(string_split({quoted}, '|'), x -> trim(x)), "
                    f"x -> x != '') AS {target_type}) END AS {quoted}"
                )
            else:
                projections.append(
                    f"CASE WHEN {quoted} IS NULL THEN NULL ELSE [CAST({quoted} AS {element_type})] END AS {quoted}"
                )
            wrapped.append(col_name)
            continue

        # List-shaped source (a LIST column, or a JSON column rendered as one).
        if target_is_list:
            projections.append(f"CAST({list_expr} AS {target_type}) AS {quoted}")
            wrapped.append(col_name)
        else:
            # List → scalar: first non-NULL element (DuckDB lists are 1-indexed;
            # an empty list yields NULL), cast to whatever the target column holds.
            non_null = f"list_filter({list_expr}, x -> x IS NOT NULL)"
            projections.append(f"CAST({non_null}[1] AS {target_type}) AS {quoted}")
            multi_value_checks.append((col_name, non_null))
            collapsed.append(col_name)

    if not collapsed and not wrapped:
        return file_columns

    for col_name, non_null in multi_value_checks:
        lost = db.conn.execute(f"SELECT COUNT(*) FROM {temp_table_name} WHERE len({non_null}) > 1").fetchone()
        lost = lost[0] if lost else 0
        if lost:
            logger.warning(
                f"append: {source} supplies multiple values for '{col_name}', but the "
                f"target column is scalar ({existing_schema[col_name]}) — keeping the first "
                f"element discards data in {lost:,} row(s)."
            )

    if collapsed:
        logger.info(f"append: collapsed list column(s) to scalar for {source}: {', '.join(sorted(collapsed))}")
    if wrapped:
        logger.info(f"append: conformed column(s) to the target's list type for {source}: {', '.join(sorted(wrapped))}")

    db.conn.execute(
        f"CREATE OR REPLACE TEMP TABLE {temp_table_name} AS SELECT {', '.join(projections)} FROM {temp_table_name}"
    )

    return {col[0]: col[1] for col in db.conn.execute(f"DESCRIBE {temp_table_name}").fetchall()}


def _append_single_file(db: GraphDatabase, file_spec, table_type: str) -> FileLoadResult:
    """
    Append a single file to an existing table with schema evolution.

    Loads the file into a temporary table, compares its schema to the existing
    table, adds any new columns via ALTER TABLE, then inserts the records using
    UNION ALL BY NAME for compatibility.

    Args:
        db: GraphDatabase instance with active connection
        file_spec: FileSpec object for the file to append
        table_type: Target table name ("nodes" or "edges")

    Returns:
        FileLoadResult with load statistics and any errors encountered
    """

    start_time = time.time()
    errors = []

    try:
        if not file_spec.path.exists():
            raise FileNotFoundError(f"File not found: {file_spec.path}")

        read_stmt = get_duckdb_read_statement(file_spec)

        # For append, we'll use a simpler approach similar to join but insert into existing table
        # Create a unique temp table name for this file
        safe_filename = file_spec.path.stem.replace("-", "_").replace(".", "_")
        temp_table_name = f"temp_append_{table_type}_{safe_filename}_{int(time.time())}"

        # Load into temp table first (like join operation)
        if file_spec.source_name:
            create_sql = f"""
                CREATE TEMP TABLE {temp_table_name} AS
                SELECT *, '{file_spec.source_name}' as file_source 
                FROM {read_stmt}
            """
        else:
            create_sql = f"""
                CREATE TEMP TABLE {temp_table_name} AS
                SELECT * FROM {read_stmt}
            """

        db.conn.execute(create_sql)

        # Get record count
        count_result = db.conn.execute(f"SELECT COUNT(*) FROM {temp_table_name}").fetchone()
        records_loaded = count_result[0] if count_result else 0

        # Get file schema from temp table
        file_describe = db.conn.execute(f"DESCRIBE {temp_table_name}").fetchall()
        file_columns = {col[0]: col[1] for col in file_describe}

        # Reconcile LIST-vs-scalar shape against the target table before the
        # insert below, which would otherwise cast a list to its string repr.
        # Read the target schema now, not once per append: an earlier file in
        # this same append may have added columns this file must conform to.
        existing_schema = _get_table_schema(db, table_type)
        if existing_schema:
            file_columns = _conform_temp_table_types(
                db,
                temp_table_name,
                file_columns,
                existing_schema,
                str(file_spec.path),
                split_pipes=file_spec.format == KGXFormat.TSV,
            )

        # Handle schema evolution - add missing columns to existing table
        if existing_schema:
            new_columns = set(file_columns.keys()) - set(existing_schema.keys())
            for col_name in new_columns:
                col_type = file_columns[col_name]
                # Checks if the name of the column is somewhere in the set of columns.
                # This is fairly likely to happen if you have multiple tables which all share the same incorrect schema.
                col_already_in_db = col_name in set(
                    db.conn.execute(f"PRAGMA table_info ('{table_type}')").fetchdf()["name"]
                )
                if not col_already_in_db:
                    alter_sql = f"ALTER TABLE {table_type} ADD COLUMN {col_name} {col_type}"
                    db.conn.execute(alter_sql)
                    logger.info(f"Added new column {col_name} ({col_type}) to {table_type} table")

        # Insert data from temp table to main table using UNION ALL BY NAME for schema compatibility
        # This handles cases where temp table has different columns than main table
        insert_sql = f"""
            INSERT INTO {table_type} 
            SELECT * FROM (
                SELECT * FROM {table_type} WHERE 1=0
                UNION ALL BY NAME
                SELECT * FROM {temp_table_name}
            ) 
            WHERE EXISTS (SELECT * FROM {temp_table_name})
        """

        # Execute the insertion
        db.conn.execute(insert_sql)

        # Clean up temp table
        db.conn.execute(f"DROP TABLE {temp_table_name}")

        load_time = time.time() - start_time

        logger.info(
            f"Appended {records_loaded} records from {file_spec.path} "
            f"({file_spec.format.value} format) to {table_type} table in {load_time:.2f}s"
        )

        return FileLoadResult(
            file_spec=file_spec,
            records_loaded=records_loaded,
            detected_format=file_spec.format,
            load_time_seconds=load_time,
            errors=errors,
        )

    except Exception as e:
        load_time = time.time() - start_time
        error_msg = f"Failed to append {file_spec.path}: {e}"
        errors.append(error_msg)
        logger.error(error_msg)

        return FileLoadResult(
            file_spec=file_spec,
            records_loaded=0,
            detected_format=file_spec.format,
            load_time_seconds=load_time,
            errors=errors,
        )


def _deduplicate_tables(db: GraphDatabase, config: AppendConfig) -> int:
    """
    Perform basic deduplication on nodes and edges tables after append.

    Removes duplicate records by ID (for both nodes and edges). For edges without
    an 'id' column, deduplicates on (subject, predicate, object) tuple. Uses
    DISTINCT ON to keep the first occurrence.

    Note: For more sophisticated deduplication with QC tracking, use the
    deduplicate_graph operation instead.

    Args:
        db: GraphDatabase instance with active connection
        config: AppendConfig (currently unused but reserved for future options)

    Returns:
        Total count of duplicate records removed (nodes + edges)
    """
    duplicates_removed = 0

    # Deduplicate nodes by ID (keep first occurrence)
    try:
        # Check if nodes table exists
        nodes_exists = False
        try:
            db.conn.execute("SELECT COUNT(*) FROM nodes LIMIT 1")
            nodes_exists = True
        except Exception:
            nodes_exists = False

        if nodes_exists:
            node_dupe_query = """
            CREATE TEMP TABLE nodes_deduped AS
            SELECT DISTINCT ON (id) * FROM nodes
            ORDER BY id
            """
            db.conn.execute(node_dupe_query)

            # Get counts
            original_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            deduped_count = db.conn.execute("SELECT COUNT(*) FROM nodes_deduped").fetchone()[0]
            node_dupes = original_count - deduped_count

            if node_dupes > 0:
                # Replace original table
                db.conn.execute("DROP TABLE nodes")
                db.conn.execute("ALTER TABLE nodes_deduped RENAME TO nodes")
                duplicates_removed += node_dupes
                logger.info(f"Removed {node_dupes} duplicate nodes")
            else:
                db.conn.execute("DROP TABLE nodes_deduped")
        else:
            logger.debug("No nodes table found, skipping node deduplication")

    except Exception as e:
        logger.warning(f"Node deduplication failed: {e}")

    # Deduplicate edges (only if edges table exists and has appropriate columns)
    try:
        # Check if edges table exists
        edges_exists = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edges'").fetchone()
        if not edges_exists:
            # Try DuckDB syntax
            try:
                db.conn.execute("SELECT COUNT(*) FROM edges LIMIT 1")
                edges_exists = True
            except Exception:
                edges_exists = False

        if edges_exists:
            # Check if edges table has an id column
            try:
                db.conn.execute("SELECT id FROM edges LIMIT 1")
                has_id_column = True
            except Exception:
                has_id_column = False

            if has_id_column:
                edge_dupe_query = """
                CREATE TEMP TABLE edges_deduped AS
                SELECT DISTINCT ON (id) * FROM edges
                ORDER BY id
                """
            else:
                # If no id column, deduplicate on subject, predicate, object
                edge_dupe_query = """
                CREATE TEMP TABLE edges_deduped AS
                SELECT DISTINCT ON (subject, predicate, object) * FROM edges
                ORDER BY subject, predicate, object
                """

            db.conn.execute(edge_dupe_query)

            # Get counts
            original_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            deduped_count = db.conn.execute("SELECT COUNT(*) FROM edges_deduped").fetchone()[0]
            edge_dupes = original_count - deduped_count

            if edge_dupes > 0:
                # Replace original table
                db.conn.execute("DROP TABLE edges")
                db.conn.execute("ALTER TABLE edges_deduped RENAME TO edges")
                duplicates_removed += edge_dupes
                logger.info(f"Removed {edge_dupes} duplicate edges")
            else:
                db.conn.execute("DROP TABLE edges_deduped")
        else:
            logger.debug("No edges table found, skipping edge deduplication")

    except Exception as e:
        logger.warning(f"Edge deduplication failed: {e}")

    return duplicates_removed


def _print_append_summary(result: AppendResult, initial_stats):
    """Print formatted append summary."""
    print(f"✓ Append completed successfully")

    total_files = len(result.files_loaded)
    successful_loads = len([f for f in result.files_loaded if not f.errors])

    print(f"  📁 Files processed: {total_files} ({successful_loads} successful)")
    print(f"  📊 Records added: {result.records_added:,}")

    if result.new_columns_added > 0:
        print(f"  🔄 Schema evolution: {result.new_columns_added} new columns added")
        for change in result.schema_changes:
            print(f"    - {change}")

    if result.duplicates_handled > 0:
        print(f"  🔧 Duplicates removed: {result.duplicates_handled:,}")

    print(f"  📈 Database growth:")
    print(
        f"    - Nodes: {initial_stats.nodes:,} → {result.final_stats.nodes:,} "
        f"(+{result.final_stats.nodes - initial_stats.nodes:,})"
    )
    print(
        f"    - Edges: {initial_stats.edges:,} → {result.final_stats.edges:,} "
        f"(+{result.final_stats.edges - initial_stats.edges:,})"
    )

    print(f"    - Database: {result.database_path} ({result.final_stats.database_size_mb:.1f} MB)")

    print(f"  ⏱️  Total time: {result.total_time_seconds:.2f}s")

    # Show any errors
    error_files = [f for f in result.files_loaded if f.errors]
    if error_files:
        print(f"  ⚠️  Files with errors:")
        for file_result in error_files:
            print(f"    - {file_result.file_spec.path.name}: {len(file_result.errors)} errors")
