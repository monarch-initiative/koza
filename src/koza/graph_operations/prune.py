"""
Prune operation for cleaning up graph integrity issues.

Handles dangling edges (pointing to non-existent nodes) and singleton nodes
with configurable strategies for preservation or removal.
"""

import time

from loguru import logger

from koza.model.graph_operations import OperationSummary, PruneConfig, PruneResult

from .utils import GraphDatabase, print_operation_summary


def prune_graph(config: PruneConfig) -> PruneResult:
    """
    Prune graph by handling dangling edges and singleton nodes.

    Args:
        config: PruneConfig with database path and prune parameters

    Returns:
        PruneResult with operation statistics
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
    Identify and move dangling edges to separate table.

    Returns:
        Tuple of (edges_moved, edges_by_source, missing_nodes_by_source)
    """
    # Check if edges table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM edges LIMIT 1")
        edges_exists = True
    except Exception:
        edges_exists = False

    if not edges_exists:
        if not config.quiet:
            print("No edges table found - no dangling edges to process")
        return 0, {}, {}

    # Check if file_source or source column exists in edges table
    has_file_source = False
    has_source = False
    try:
        db.conn.execute("SELECT file_source FROM edges LIMIT 1")
        has_file_source = True
    except Exception:
        try:
            db.conn.execute("SELECT source FROM edges LIMIT 1")
            has_source = True
        except Exception:
            pass

    # Find dangling edges - edges where subject or object doesn't exist in nodes table
    if has_file_source:
        source_column = "COALESCE(e.file_source, 'unknown')"
    elif has_source:
        source_column = "COALESCE(e.source, 'unknown')"
    else:
        source_column = "'unknown'"

    dangling_query = f"""
    SELECT e.*, 
           CASE WHEN n1.id IS NULL THEN e.subject ELSE NULL END as missing_subject,
           CASE WHEN n2.id IS NULL THEN e.object ELSE NULL END as missing_object,
           {source_column} as source
    FROM edges e
    LEFT JOIN nodes n1 ON e.subject = n1.id
    LEFT JOIN nodes n2 ON e.object = n2.id
    WHERE n1.id IS NULL OR n2.id IS NULL
    """

    dangling_edges = db.conn.execute(dangling_query).fetchall()

    if not dangling_edges:
        if not config.quiet:
            print("No dangling edges found")
        return 0, {}, {}

    dangling_count = len(dangling_edges)

    if not config.quiet:
        print(f"Found {dangling_count} dangling edges, moving to dangling_edges table...")

    # Analyze dangling edges by source
    #TODO turn these into defaultdicts.
    dangling_by_source = {}
    missing_by_source = {}

    for edge in dangling_edges:
        source = edge[-1]  # source is last column
        if source not in dangling_by_source:
            dangling_by_source[source] = 0
            missing_by_source[source] = set()

        dangling_by_source[source] += 1

        # Track missing nodes
        #TODO, confirm this code actually works as expected. Turns the indexed edge tuples into variables.
        if edge[-3]:  # missing_subject
            missing_by_source[source].add(edge[-3])
        if edge[-2]:  # missing_object
            missing_by_source[source].add(edge[-2])

    # Convert sets to counts
    missing_by_source = {k: len(v) for k, v in missing_by_source.items()}

    # Move dangling edges to dangling_edges table
    # First, get the column structure (excluding our analysis columns)
    edge_columns_result = db.conn.execute("DESCRIBE edges").fetchall()
    edge_columns = [col[0] for col in edge_columns_result]
    columns_str = ", ".join(edge_columns)

    # Recreate dangling_edges table with current edges schema to handle schema changes from normalization
    db.conn.execute("DROP TABLE IF EXISTS dangling_edges")
    db.conn.execute("CREATE TABLE dangling_edges AS SELECT * FROM edges WHERE 1=0")

    # Insert dangling edges into dangling_edges table
    columns_with_prefix = ", ".join([f"e.{col}" for col in edge_columns])
    insert_query = f"""
    INSERT INTO dangling_edges ({columns_str})
    SELECT {columns_with_prefix} FROM edges e
    LEFT JOIN nodes n1 ON e.subject = n1.id
    LEFT JOIN nodes n2 ON e.object = n2.id
    WHERE n1.id IS NULL OR n2.id IS NULL
    """

    db.conn.execute(insert_query)

    # Remove dangling edges from main edges table
    # Use a more robust approach that works with or without an id column
    delete_query = """
    DELETE FROM edges
    WHERE EXISTS (
        SELECT 1 FROM (
            SELECT subject, object FROM edges e
            LEFT JOIN nodes n1 ON e.subject = n1.id
            LEFT JOIN nodes n2 ON e.object = n2.id
            WHERE n1.id IS NULL OR n2.id IS NULL
        ) dangling
        WHERE dangling.subject = edges.subject AND dangling.object = edges.object
    )
    """

    db.conn.execute(delete_query)

    logger.info(f"Moved {dangling_count} dangling edges to dangling_edges table")

    return dangling_count, dangling_by_source, missing_by_source


def _handle_singleton_nodes(db: GraphDatabase, config: PruneConfig) -> tuple[int, int]:
    """
    Handle singleton nodes based on configuration.

    Returns:
        Tuple of (nodes_moved, nodes_kept)
    """
    # Check if edges table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM edges LIMIT 1")
        edges_exists = True
    except Exception:
        edges_exists = False

    if not edges_exists:
        # If no edges table, all nodes are singletons
        try:
            singleton_nodes = db.conn.execute("SELECT * FROM nodes").fetchall()
        except Exception:
            # No nodes table either
            if not config.quiet:
                print("No nodes table found - no singleton nodes to process")
            return 0, 0
    else:
        # Find singleton nodes - nodes that don't appear as subject or object in any edge
        singleton_query = """
        SELECT n.* FROM nodes n
        LEFT JOIN edges e1 ON n.id = e1.subject
        LEFT JOIN edges e2 ON n.id = e2.object
        WHERE e1.subject IS NULL AND e2.object IS NULL
        """

        singleton_nodes = db.conn.execute(singleton_query).fetchall()
    singleton_count = len(singleton_nodes)

    if singleton_count == 0:
        if not config.quiet:
            print("No singleton nodes found")
        return 0, 0

    if config.keep_singletons:
        if not config.quiet:
            print(f"Keeping {singleton_count} singleton nodes (--keep-singletons)")
        return 0, singleton_count

    elif config.remove_singletons:
        if not config.quiet:
            print(f"Moving {singleton_count} singleton nodes to singleton_nodes table...")

        # Get node table structure
        node_columns_result = db.conn.execute("DESCRIBE nodes").fetchall()
        node_columns = [col[0] for col in node_columns_result]
        columns_str = ", ".join(node_columns)

        # Insert singleton nodes into singleton_nodes table
        columns_with_prefix = ", ".join([f"n.{col}" for col in node_columns])
        #TODO: Verify this query works. It might need to be "WHERE e1.object IS NULL AND e2.subject IS NULL".
        insert_query = f"""
        INSERT INTO singleton_nodes ({columns_str})
        SELECT {columns_with_prefix} FROM nodes n
        LEFT JOIN edges e1 ON n.id = e1.subject
        LEFT JOIN edges e2 ON n.id = e2.object
        WHERE e1.subject IS NULL AND e2.object IS NULL
        """

        db.conn.execute(insert_query)

        # Remove singleton nodes from main nodes table
        delete_query = """
        DELETE FROM nodes
        WHERE nodes.id IN (
            SELECT n.id FROM nodes n
            LEFT JOIN edges e1 ON n.id = e1.subject
            LEFT JOIN edges e2 ON n.id = e2.object
            WHERE e1.subject IS NULL AND e2.object IS NULL
        )
        """

        db.conn.execute(delete_query)

        logger.info(f"Moved {singleton_count} singleton nodes to singleton_nodes table.")

        return singleton_count, 0

    else:
        # Default behavior: keep singletons
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
