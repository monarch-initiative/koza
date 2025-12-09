"""
Deduplicate operation for removing duplicate nodes and edges from graph data.

This operation:
1. Identifies duplicate nodes/edges by ID
2. Moves ALL duplicate rows to separate tables (duplicate_nodes, duplicate_edges)
3. Keeps only the first occurrence in the main tables (ordered by file_source)
"""

import time
from pathlib import Path

from loguru import logger

from koza.model.graph_operations import (
    DatabaseStats,
    DeduplicateConfig,
    DeduplicateResult,
    OperationSummary,
)

from .utils import GraphDatabase, print_operation_summary


def deduplicate_graph(config: DeduplicateConfig) -> DeduplicateResult:
    """
    Deduplicate nodes and edges in a graph database.

    This operation:
    1. Identifies nodes/edges with duplicate IDs
    2. Copies ALL duplicate rows to duplicate_nodes/duplicate_edges tables
    3. Keeps only the first occurrence in main tables (ordered by file_source)

    Args:
        config: DeduplicateConfig with database path and options

    Returns:
        DeduplicateResult with deduplication statistics
    """
    start_time = time.time()
    errors = []
    warnings = []

    duplicate_nodes_found = 0
    duplicate_nodes_removed = 0
    duplicate_edges_found = 0
    duplicate_edges_removed = 0

    try:
        with GraphDatabase(config.database_path) as db:
            # Deduplicate nodes
            if config.deduplicate_nodes:
                nodes_result = _deduplicate_nodes(db, config)
                duplicate_nodes_found = nodes_result["found"]
                duplicate_nodes_removed = nodes_result["removed"]

                if not config.quiet:
                    if duplicate_nodes_removed > 0:
                        print(f"  - Found {duplicate_nodes_found:,} duplicate node rows")
                        print(f"  - Removed {duplicate_nodes_removed:,} duplicate entries from nodes table")
                    else:
                        print("  - No duplicate nodes found")

            # Deduplicate edges
            if config.deduplicate_edges:
                edges_result = _deduplicate_edges(db, config)
                duplicate_edges_found = edges_result["found"]
                duplicate_edges_removed = edges_result["removed"]

                if not config.quiet:
                    if duplicate_edges_removed > 0:
                        print(f"  - Found {duplicate_edges_found:,} duplicate edge rows")
                        print(f"  - Removed {duplicate_edges_removed:,} duplicate entries from edges table")
                    else:
                        print("  - No duplicate edges found")

            # Get final stats
            final_stats = db.get_stats()
            total_time = time.time() - start_time

            # Create summary
            total_removed = duplicate_nodes_removed + duplicate_edges_removed
            if total_removed > 0:
                message = f"Removed {duplicate_nodes_removed:,} duplicate nodes, {duplicate_edges_removed:,} duplicate edges"
            else:
                message = "No duplicates found"

            summary = OperationSummary(
                operation="deduplicate",
                success=True,
                message=message,
                stats=final_stats,
                files_processed=0,
                total_time_seconds=total_time,
                warnings=warnings,
                errors=errors,
            )

            if not config.quiet:
                print_operation_summary(summary)

            return DeduplicateResult(
                success=True,
                duplicate_nodes_found=duplicate_nodes_found,
                duplicate_nodes_removed=duplicate_nodes_removed,
                duplicate_edges_found=duplicate_edges_found,
                duplicate_edges_removed=duplicate_edges_removed,
                final_stats=final_stats,
                total_time_seconds=total_time,
                summary=summary,
                errors=errors,
                warnings=warnings,
            )

    except Exception as e:
        total_time = time.time() - start_time
        error_msg = f"Deduplicate operation failed: {e}"
        errors.append(error_msg)
        logger.error(error_msg)

        summary = OperationSummary(
            operation="deduplicate",
            success=False,
            message=error_msg,
            stats=None,
            files_processed=0,
            total_time_seconds=total_time,
            warnings=warnings,
            errors=errors,
        )

        if not config.quiet:
            print_operation_summary(summary)

        return DeduplicateResult(
            success=False,
            duplicate_nodes_found=duplicate_nodes_found,
            duplicate_nodes_removed=duplicate_nodes_removed,
            duplicate_edges_found=duplicate_edges_found,
            duplicate_edges_removed=duplicate_edges_removed,
            final_stats=None,
            total_time_seconds=total_time,
            summary=summary,
            errors=errors,
            warnings=warnings,
        )


def _deduplicate_nodes(db: GraphDatabase, config: DeduplicateConfig) -> dict:
    """
    Deduplicate nodes table.

    1. Copy ALL rows with duplicate IDs to duplicate_nodes table
    2. Keep only first occurrence in nodes table (ordered by file_source)

    Returns dict with 'found' and 'removed' counts.
    """
    # Check if nodes table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM nodes LIMIT 1")
    except Exception:
        logger.debug("No nodes table found, skipping node deduplication")
        return {"found": 0, "removed": 0}

    # Get count before deduplication
    original_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    # Check which ordering column exists (file_source or provided_by)
    order_column = _get_order_column(db, "nodes")

    # Step 1: Create duplicate_nodes table with ALL rows that have duplicate IDs
    # This preserves all duplicates for QC tracking
    db.conn.execute("""
        CREATE OR REPLACE TABLE duplicate_nodes AS
        SELECT * FROM nodes
        WHERE id IN (
            SELECT id FROM nodes
            GROUP BY id
            HAVING COUNT(*) > 1
        )
    """)

    duplicate_rows = db.conn.execute("SELECT COUNT(*) FROM duplicate_nodes").fetchone()[0]

    if duplicate_rows == 0:
        logger.info("No duplicate nodes found")
        return {"found": 0, "removed": 0}

    # Count unique IDs that have duplicates
    duplicate_ids = db.conn.execute("""
        SELECT COUNT(DISTINCT id) FROM duplicate_nodes
    """).fetchone()[0]

    logger.info(f"Found {duplicate_rows} rows with {duplicate_ids} duplicate node IDs")

    # Step 2: Clean nodes table - keep first occurrence ordered by file_source/provided_by
    # Use CREATE OR REPLACE TABLE to avoid issues with temp table renaming in DuckDB
    db.conn.execute(f"""
        CREATE OR REPLACE TABLE nodes AS
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY {order_column}) as rn
            FROM nodes
        ) WHERE rn = 1
    """)

    # Get count after deduplication
    final_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    removed = original_count - final_count

    logger.info(f"Removed {removed} duplicate node rows (kept {final_count} unique nodes)")

    return {"found": duplicate_rows, "removed": removed}


def _deduplicate_edges(db: GraphDatabase, config: DeduplicateConfig) -> dict:
    """
    Deduplicate edges table.

    1. Copy ALL rows with duplicate IDs to duplicate_edges table
    2. Keep only first occurrence in edges table (ordered by file_source)

    Returns dict with 'found' and 'removed' counts.
    """
    # Check if edges table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM edges LIMIT 1")
    except Exception:
        logger.debug("No edges table found, skipping edge deduplication")
        return {"found": 0, "removed": 0}

    # Check if edges have an id column
    try:
        db.conn.execute("SELECT id FROM edges LIMIT 1")
        has_id_column = True
    except Exception:
        has_id_column = False

    if not has_id_column:
        logger.warning("Edges table has no 'id' column, skipping edge deduplication")
        return {"found": 0, "removed": 0}

    # Get count before deduplication
    original_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

    # Check which ordering column exists
    order_column = _get_order_column(db, "edges")

    # Step 1: Create duplicate_edges table with ALL rows that have duplicate IDs
    db.conn.execute("""
        CREATE OR REPLACE TABLE duplicate_edges AS
        SELECT * FROM edges
        WHERE id IN (
            SELECT id FROM edges
            GROUP BY id
            HAVING COUNT(*) > 1
        )
    """)

    duplicate_rows = db.conn.execute("SELECT COUNT(*) FROM duplicate_edges").fetchone()[0]

    if duplicate_rows == 0:
        logger.info("No duplicate edges found")
        return {"found": 0, "removed": 0}

    # Count unique IDs that have duplicates
    duplicate_ids = db.conn.execute("""
        SELECT COUNT(DISTINCT id) FROM duplicate_edges
    """).fetchone()[0]

    logger.info(f"Found {duplicate_rows} rows with {duplicate_ids} duplicate edge IDs")

    # Step 2: Clean edges table - keep first occurrence
    # Use CREATE OR REPLACE TABLE to avoid issues with temp table renaming in DuckDB
    db.conn.execute(f"""
        CREATE OR REPLACE TABLE edges AS
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY {order_column}) as rn
            FROM edges
        ) WHERE rn = 1
    """)

    # Get count after deduplication
    final_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    removed = original_count - final_count

    logger.info(f"Removed {removed} duplicate edge rows (kept {final_count} unique edges)")

    return {"found": duplicate_rows, "removed": removed}


def _get_order_column(db: GraphDatabase, table: str) -> str:
    """
    Determine which column to use for ordering when keeping first occurrence.

    Prefers file_source, falls back to provided_by, then uses a constant.
    """
    columns = db.conn.execute(f"DESCRIBE {table}").fetchall()
    column_names = {col[0] for col in columns}

    if "file_source" in column_names:
        return "file_source"
    elif "provided_by" in column_names:
        return "provided_by"
    else:
        # No ordering column available, use a constant (arbitrary but deterministic)
        return "1"
