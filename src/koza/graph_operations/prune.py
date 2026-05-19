"""
Prune operation for cleaning up graph integrity issues.

Handles dangling edges (pointing to non-existent nodes) and singleton nodes
with configurable strategies for preservation or removal.
"""

import time
from collections import defaultdict

from loguru import logger

from koza.model.graph_operations import OperationSummary, PruneConfig, PruneResult

from .slots import edges, nodes
from .utils import GraphDatabase, print_operation_summary


def prune_graph(config: PruneConfig) -> PruneResult:
    """
    Clean up graph integrity issues by handling dangling edges and singleton nodes.

    This operation identifies and handles two common graph quality issues:
    - Dangling edges: Edges where subject or object IDs don't exist in the nodes table
    - Singleton nodes: Nodes that don't appear as subject or object in any edge

    The prune process:
    1. Identifies dangling edges and moves them to a 'dangling_edges' table
    2. Based on config, either keeps or moves singleton nodes to 'singleton_nodes' table
    3. Optionally filters by minimum connected component size (not yet implemented)

    Dangling edges and singleton nodes are preserved in separate tables for QC
    analysis rather than being deleted, allowing investigation of data issues.

    Args:
        config: PruneConfig containing:
            - database_path: Path to the DuckDB database to prune
            - keep_singletons: If True, preserve singleton nodes in main table (default)
            - remove_singletons: If True, move singleton nodes to singleton_nodes table
            - min_component_size: Minimum connected component size (not yet implemented)
            - quiet: Suppress console output
            - show_progress: Display progress during operations

    Returns:
        PruneResult containing:
            - database_path: Path to the pruned database
            - dangling_edges_moved: Count of edges moved to dangling_edges table
            - singleton_nodes_moved: Count of nodes moved to singleton_nodes table
            - singleton_nodes_kept: Count of singleton nodes preserved in main table
            - final_stats: DatabaseStats with final node/edge counts
            - dangling_edges_by_source: Breakdown of dangling edges by file_source
            - missing_nodes_by_source: Count of missing node IDs by source
            - total_time_seconds: Operation duration
            - success: Whether the operation completed successfully

    Raises:
        Exception: If database operations fail
    """
    start_time = time.time()

    try:
        # Connect to existing database
        with GraphDatabase(config.database_path) as db:
            # Step 1: Identify and move dangling edges
            if not config.quiet:
                print("Handling dangling edges.")

            dangling_edges_moved, dangling_by_source, missing_by_source = _handle_dangling_edges(db, config)

            # Step 2: Handle singleton nodes based on configuration
            singleton_nodes_moved, singleton_nodes_kept = _handle_singleton_nodes(db, config)

            # Step 3: Handle minimum component size if specified
            if config.min_component_size:
                _handle_small_components(db, config)

            # Get final statistics
            final_stats = db.get_stats()

        total_time = time.time() - start_time

        # Create result
        result = PruneResult(
            database_path=config.database_path,
            dangling_edges_moved=dangling_edges_moved,
            singleton_nodes_moved=singleton_nodes_moved,
            singleton_nodes_kept=singleton_nodes_kept,
            final_stats=final_stats,
            dangling_edges_by_source=dangling_by_source,
            missing_nodes_by_source=missing_by_source,
            total_time_seconds=total_time,
            success=True,
            errors = [] #TODO: Add some error handling to the intermediate steps.
        )

        # Print summary if not quiet
        if not config.quiet:
            _print_prune_summary(result)

        return result

    except Exception as e:
        total_time = time.time() - start_time

        if not config.quiet:
            summary = OperationSummary(
                operation="Prune",
                success=False,
                message=f"Operation failed: {e}",
                files_processed=0,
                total_time_seconds=total_time,
                errors=[str(e)],
            )
            print_operation_summary(summary)

        raise


def _handle_dangling_edges(db: GraphDatabase, config: PruneConfig) -> tuple[int, dict[str, int], dict[str, int]]:
    """
    Identify and move dangling edges to a separate table for QC tracking.

    A dangling edge is one where either the subject or object ID does not exist
    in the nodes table. This function finds all such edges, analyzes them by
    source file, and moves them to a 'dangling_edges' table.

    Args:
        db: GraphDatabase instance with active connection
        config: PruneConfig for quiet/progress settings

    Returns:
        Tuple of:
            - edges_moved: Total count of dangling edges moved
            - edges_by_source: Dict mapping file_source to count of dangling edges
            - missing_nodes_by_source: Dict mapping file_source to count of unique missing node IDs
    """
    try:
        db.conn.execute("SELECT COUNT(*) FROM edges LIMIT 1")
    except Exception:
        if not config.quiet:
            print("No edges table found - no dangling edges to process")
        return 0, {}, {}

    dangling_query = f"""
    SELECT
        CASE WHEN n1.{nodes.id} IS NULL THEN e.{edges.subject} ELSE NULL END as missing_subject,
        CASE WHEN n2.{nodes.id} IS NULL THEN e.{edges.object} ELSE NULL END as missing_object,
        COALESCE(e.{edges.file_source}, 'unknown') as source
    FROM edges e
    LEFT JOIN nodes n1 ON e.{edges.subject} = n1.{nodes.id}
    LEFT JOIN nodes n2 ON e.{edges.object} = n2.{nodes.id}
    WHERE n1.{nodes.id} IS NULL OR n2.{nodes.id} IS NULL
    """

    dangling_rows = db.conn.execute(dangling_query).fetchall()

    if not dangling_rows:
        if not config.quiet:
            print("No dangling edges found")
        return 0, {}, {}

    dangling_count = len(dangling_rows)

    if not config.quiet:
        print(f"Found {dangling_count} dangling edges, moving to dangling_edges table...")

    dangling_by_source: dict[str, int] = defaultdict(int)
    missing_by_source_sets: dict[str, set] = defaultdict(set)
    for missing_subject, missing_object, source in dangling_rows:
        dangling_by_source[source] += 1
        if missing_subject:
            missing_by_source_sets[source].add(missing_subject)
        if missing_object:
            missing_by_source_sets[source].add(missing_object)
    missing_by_source = {k: len(v) for k, v in missing_by_source_sets.items()}

    # Recreate dangling_edges with current edges schema so per-run column
    # evolution (e.g. normalize adding original_*) is reflected.
    db.conn.execute("DROP TABLE IF EXISTS dangling_edges")
    db.conn.execute("CREATE TABLE dangling_edges AS SELECT * FROM edges WHERE 1=0")

    db.conn.execute(f"""
        INSERT INTO dangling_edges
        SELECT e.* FROM edges e
        LEFT JOIN nodes n1 ON e.{edges.subject} = n1.{nodes.id}
        LEFT JOIN nodes n2 ON e.{edges.object} = n2.{nodes.id}
        WHERE n1.{nodes.id} IS NULL OR n2.{nodes.id} IS NULL
    """)

    db.conn.execute(f"""
        DELETE FROM edges
        WHERE EXISTS (
            SELECT 1 FROM (
                SELECT e.{edges.subject} AS s, e.{edges.object} AS o FROM edges e
                LEFT JOIN nodes n1 ON e.{edges.subject} = n1.{nodes.id}
                LEFT JOIN nodes n2 ON e.{edges.object} = n2.{nodes.id}
                WHERE n1.{nodes.id} IS NULL OR n2.{nodes.id} IS NULL
            ) dangling
            WHERE dangling.s = edges.{edges.subject} AND dangling.o = edges.{edges.object}
        )
    """)

    logger.info(f"Moved {dangling_count} dangling edges to dangling_edges table")

    return dangling_count, dict(dangling_by_source), missing_by_source


def _handle_singleton_nodes(db: GraphDatabase, config: PruneConfig) -> tuple[int, int]:
    """
    Handle singleton nodes based on configuration settings.

    A singleton node is one that does not appear as subject or object in any edge.
    Based on the config, singletons can either be:
    - Kept in the main nodes table (default behavior, or with keep_singletons=True)
    - Moved to a 'singleton_nodes' table (with remove_singletons=True)

    Args:
        db: GraphDatabase instance with active connection
        config: PruneConfig with keep_singletons/remove_singletons flags

    Returns:
        Tuple of:
            - nodes_moved: Count of singleton nodes moved to singleton_nodes table
            - nodes_kept: Count of singleton nodes kept in main nodes table
    """
    try:
        db.conn.execute("SELECT COUNT(*) FROM edges LIMIT 1")
        edges_exists = True
    except Exception:
        edges_exists = False

    if not edges_exists:
        try:
            singleton_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        except Exception:
            if not config.quiet:
                print("No nodes table found - no singleton nodes to process")
            return 0, 0
    else:
        singleton_count = db.conn.execute(f"""
            SELECT COUNT(*) FROM nodes n
            LEFT JOIN edges e1 ON n.{nodes.id} = e1.{edges.subject}
            LEFT JOIN edges e2 ON n.{nodes.id} = e2.{edges.object}
            WHERE e1.{edges.subject} IS NULL AND e2.{edges.object} IS NULL
        """).fetchone()[0]

    if singleton_count == 0:
        if not config.quiet:
            print("No singleton nodes found")
        return 0, 0

    if config.keep_singletons:
        if not config.quiet:
            print(f"Keeping {singleton_count} singleton nodes (--keep-singletons)")
        return 0, singleton_count

    if config.remove_singletons:
        if not config.quiet:
            print(f"Moving {singleton_count} singleton nodes to singleton_nodes table...")

        # Recreate to mirror the current nodes schema (operations may have
        # added columns since the last run).
        db.conn.execute("DROP TABLE IF EXISTS singleton_nodes")
        db.conn.execute("CREATE TABLE singleton_nodes AS SELECT * FROM nodes WHERE 1=0")

        db.conn.execute(f"""
            INSERT INTO singleton_nodes
            SELECT n.* FROM nodes n
            LEFT JOIN edges e1 ON n.{nodes.id} = e1.{edges.subject}
            LEFT JOIN edges e2 ON n.{nodes.id} = e2.{edges.object}
            WHERE e1.{edges.subject} IS NULL AND e2.{edges.object} IS NULL
        """)

        db.conn.execute(f"""
            DELETE FROM nodes
            WHERE nodes.{nodes.id} IN (
                SELECT n.{nodes.id} FROM nodes n
                LEFT JOIN edges e1 ON n.{nodes.id} = e1.{edges.subject}
                LEFT JOIN edges e2 ON n.{nodes.id} = e2.{edges.object}
                WHERE e1.{edges.subject} IS NULL AND e2.{edges.object} IS NULL
            )
        """)

        logger.info(f"Moved {singleton_count} singleton nodes to singleton_nodes table.")
        return singleton_count, 0

    if not config.quiet:
        print(f"Keeping {singleton_count} singleton nodes (default behavior).")
    return 0, singleton_count


def _handle_small_components(db: GraphDatabase, config: PruneConfig):
    """
    Handle connected components smaller than minimum size.

    This is a placeholder for advanced component analysis.
    """
    # TODO: Implement connected component analysis
    # This would require graph traversal algorithms
    logger.info(f"Component size filtering not yet implemented (min_component_size={config.min_component_size})")

    if not config.quiet:
        print(f"⚠️  Component size filtering not yet implemented (--min-component-size {config.min_component_size})")


def _print_prune_summary(result: PruneResult):
    """Print formatted prune summary."""
    print(f"Graph pruned successfully")

    print(f"{result.dangling_edges_moved} dangling edges moved to dangling_edges table.")

    print(f"{result.singleton_nodes_moved} singleton nodes moved to singleton_nodes table.")
    print(f"{result.singleton_nodes_kept} singleton nodes preserved.")

    print(f"   Final graph:")
    print(f"    - Nodes: {result.final_stats.nodes:,}")
    print(f"    - Edges: {result.final_stats.edges:,}")

    print(f"    - Dangling edges archived: {result.final_stats.dangling_edges:,}")
    print(f"    - Singleton nodes archived: {result.final_stats.singleton_nodes:,}")

    print(f"    - Database: {result.database_path} ({result.final_stats.database_size_mb:.1f} MB)")

    # Show dangling edges breakdown by source
    if result.dangling_edges_by_source:
        print(f" Dangling edges by source:")
        for source, count in sorted(result.dangling_edges_by_source.items()):
            missing_nodes = result.missing_nodes_by_source.get(source, 0)
            print(f"    - {source}: {count} edges (missing {missing_nodes} nodes)")

    print(f"⏱ Total time taken to prune: {result.total_time_seconds:.2f}s")
