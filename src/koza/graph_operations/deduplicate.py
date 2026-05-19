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

from .slots import edges, nodes
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
    Deduplicate the nodes table by ID with QC tracking.

    This function:
    1. Identifies all rows with duplicate IDs
    2. Copies ALL duplicate rows to a 'duplicate_nodes' table (for QC analysis)
    3. Keeps only the first occurrence in the main nodes table

    The first occurrence is determined by ordering on file_source or provided_by
    column (if available), ensuring deterministic results.

    Args:
        db: GraphDatabase instance with active connection
        config: DeduplicateConfig (used for quiet setting)

    Returns:
        Dict with:
            - 'found': Total count of rows that had duplicate IDs
            - 'removed': Count of duplicate rows removed from main table
    """
    # Check if nodes table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM nodes LIMIT 1")
    except Exception:
        logger.debug("No nodes table found, skipping node deduplication")
        return {"found": 0, "removed": 0}

    # Get count before deduplication
    original_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    db.conn.execute(f"""
        CREATE OR REPLACE TABLE duplicate_nodes AS
        SELECT * FROM nodes
        WHERE {nodes.id} IN (
            SELECT {nodes.id} FROM nodes
            GROUP BY {nodes.id}
            HAVING COUNT(*) > 1
        )
    """)

    duplicate_rows = db.conn.execute("SELECT COUNT(*) FROM duplicate_nodes").fetchone()[0]

    if duplicate_rows == 0:
        logger.info("No duplicate nodes found")
        return {"found": 0, "removed": 0}

    duplicate_ids = db.conn.execute(f"""
        SELECT COUNT(DISTINCT {nodes.id}) FROM duplicate_nodes
    """).fetchone()[0]

    logger.info(f"Found {duplicate_rows} rows with {duplicate_ids} duplicate node IDs")

    db.conn.execute(f"""
        CREATE OR REPLACE TABLE nodes AS
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY {nodes.id} ORDER BY {nodes.file_source}) as rn
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
    Deduplicate the edges table by ID with QC tracking.

    This function:
    1. Identifies all rows with duplicate IDs
    2. Copies ALL duplicate rows to a 'duplicate_edges' table (for QC analysis)
    3. Keeps only the first occurrence in the main edges table

    The first occurrence is determined by ordering on file_source or provided_by
    column (if available), ensuring deterministic results.

    Note: Requires edges table to have an 'id' column. If no 'id' column exists,
    edge deduplication is skipped with a warning.

    Args:
        db: GraphDatabase instance with active connection
        config: DeduplicateConfig (used for quiet setting)

    Returns:
        Dict with:
            - 'found': Total count of rows that had duplicate IDs
            - 'removed': Count of duplicate rows removed from main table
    """
    # Check if edges table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM edges LIMIT 1")
    except Exception:
        logger.debug("No edges table found, skipping edge deduplication")
        return {"found": 0, "removed": 0}

    # Edges may legitimately lack an id column — KGX files often key on
    # (subject, predicate, object) instead. Skip dedup in that case.
    try:
        db.conn.execute("SELECT id FROM edges LIMIT 1")
    except Exception:
        logger.warning("Edges table has no 'id' column, skipping edge deduplication")
        return {"found": 0, "removed": 0}

    original_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

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

    duplicate_ids = db.conn.execute("""
        SELECT COUNT(DISTINCT id) FROM duplicate_edges
    """).fetchone()[0]

    logger.info(f"Found {duplicate_rows} rows with {duplicate_ids} duplicate edge IDs")

    db.conn.execute(f"""
        CREATE OR REPLACE TABLE edges AS
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY {edges.file_source}) as rn
            FROM edges
        ) WHERE rn = 1
    """)

    # Get count after deduplication
    final_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    removed = original_count - final_count

    logger.info(f"Removed {removed} duplicate edge rows (kept {final_count} unique edges)")

    return {"found": duplicate_rows, "removed": removed}


