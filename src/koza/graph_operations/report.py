"""
Graph reporting and analysis operations.

This module provides comprehensive reporting capabilities for KGX graphs,
including QC analysis, graph statistics, and schema compliance reporting.
"""

import time
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from koza.model.graph_operations import (
    BiolinkCompliance,
    CategoryStats,
    EdgeExamplesConfig,
    EdgeExamplesResult,
    EdgeReportConfig,
    EdgeReportResult,
    EdgeSourceReport,
    EdgeStats,
    FileSpec,
    GraphStatsConfig,
    GraphStatsReport,
    GraphStatsResult,
    KGXFileType,
    KGXFormat,
    NodeExamplesConfig,
    NodeExamplesResult,
    NodeReportConfig,
    NodeReportResult,
    NodeSourceReport,
    NodeStats,
    PredicateReport,
    PredicateStats,
    QCReport,
    QCReportConfig,
    QCReportResult,
    QCSummary,
    SchemaAnalysisReport,
    SchemaReportConfig,
    SchemaReportResult,
    TableSchema,
    TabularReportFormat,
)

from .utils import GraphDatabase


def generate_qc_report(config: QCReportConfig) -> QCReportResult:
    """
    Generate a comprehensive quality control report for a graph database.

    This operation analyzes a graph database and produces a detailed QC report
    including node/edge counts by source, duplicate detection, dangling edge
    analysis, and singleton node counts. The report can be grouped by different
    columns (e.g., provided_by, file_source).

    The QC report includes:
    - Summary: Total nodes, edges, duplicates, dangling edges, singletons
    - Nodes by source: Count and category breakdown per source
    - Edges by source: Count and predicate breakdown per source
    - Dangling edges by source: Edges pointing to non-existent nodes
    - Duplicate analysis: Nodes/edges with duplicate IDs

    Args:
        config: QCReportConfig containing:
            - database_path: Path to the DuckDB database to analyze
            - output_file: Optional path to write YAML report
            - group_by: Column to group statistics by (default: "provided_by")
            - quiet: Suppress console output

    Returns:
        QCReportResult containing:
            - qc_report: QCReport with all analysis data
            - output_file: Path where report was written (if specified)
            - total_time_seconds: Report generation duration

    Raises:
        FileNotFoundError: If database does not exist
        Exception: If database analysis fails
    """
    start_time = time.time()

    try:
        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")

        with GraphDatabase(config.database_path, read_only=True) as db:
            if not config.quiet:
                print(f"Generating QC report for {config.database_path.name}...")

            # Generate the QC report using existing functionality
            qc_report = _create_qc_report(db, group_by=config.group_by)

            # Write to output file if specified
            if config.output_file:
                _write_yaml_report(qc_report, config.output_file)
                if not config.quiet:
                    print(f"✓ QC report written to {config.output_file}")

            total_time = time.time() - start_time

            # Print summary if not quiet
            if not config.quiet:
                _print_qc_summary(qc_report, total_time)

            return QCReportResult(qc_report=qc_report, output_file=config.output_file, total_time_seconds=total_time)

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"QC report generation failed: {e}")

        if not config.quiet:
            print(f"QC report generation failed: {e}")

        raise


def generate_graph_stats(config: GraphStatsConfig) -> GraphStatsResult:
    """
    Generate comprehensive statistical analysis of a graph database.

    This operation produces detailed statistics about a graph's structure,
    including node category distributions, edge predicate distributions,
    degree statistics, and biolink model compliance analysis.

    The statistics report includes:
    - Node statistics: Total count, unique categories, category distribution
    - Edge statistics: Total count, unique predicates, predicate distribution
    - Predicate details: Subject/object category pairs for each predicate
    - Biolink compliance: Validation against biolink model categories/predicates

    Args:
        config: GraphStatsConfig containing:
            - database_path: Path to the DuckDB database to analyze
            - output_file: Optional path to write YAML report
            - quiet: Suppress console output

    Returns:
        GraphStatsResult containing:
            - stats_report: GraphStatsReport with all statistics
            - output_file: Path where report was written (if specified)
            - total_time_seconds: Report generation duration

    Raises:
        FileNotFoundError: If database does not exist
        Exception: If database analysis fails
    """
    start_time = time.time()

    try:
        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")

        with GraphDatabase(config.database_path, read_only=True) as db:
            if not config.quiet:
                print(f" Generating graph statistics for {config.database_path.name}...")

            # Generate comprehensive graph statistics
            stats_report = _create_graph_stats_report(db)

            # Write to output file if specified
            if config.output_file:
                _write_yaml_report(stats_report, config.output_file)
                if not config.quiet:
                    print(f"✓ Graph statistics written to {config.output_file}")

            total_time = time.time() - start_time

            # Print summary if not quiet
            if not config.quiet:
                _print_graph_stats_summary(stats_report, total_time)

            return GraphStatsResult(
                stats_report=stats_report, output_file=config.output_file, total_time_seconds=total_time
            )

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Graph statistics generation failed: {e}")

        if not config.quiet:
            print(f" Graph statistics generation failed: {e}")

        raise


def generate_schema_compliance_report(config: SchemaReportConfig) -> SchemaReportResult:
    """
    Generate a schema analysis and biolink compliance report.

    This operation analyzes the schema (columns and data types) of the nodes
    and edges tables, comparing them against expected biolink model properties
    and identifying any non-standard or missing columns.

    The schema report includes:
    - Table schemas: Column names and DuckDB data types for nodes/edges
    - Biolink compliance: Which columns match biolink model slots
    - Non-standard columns: Columns not in the biolink model
    - Data type analysis: Column type distributions and potential issues

    Args:
        config: SchemaReportConfig containing:
            - database_path: Path to the DuckDB database to analyze
            - output_file: Optional path to write YAML report
            - quiet: Suppress console output

    Returns:
        SchemaReportResult containing:
            - schema_report: SchemaAnalysisReport with all analysis
            - output_file: Path where report was written (if specified)
            - total_time_seconds: Report generation duration

    Raises:
        FileNotFoundError: If database does not exist
        Exception: If schema analysis fails
    """
    start_time = time.time()

    try:
        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")

        with GraphDatabase(config.database_path, read_only=True) as db:
            if not config.quiet:
                print(f" Generating schema report for {config.database_path.name}...")

            # Generate schema analysis report
            schema_report = _create_schema_analysis_report(
                db,
                include_biolink_compliance=config.include_biolink_compliance
            )

            # Write to output file if specified
            if config.output_file:
                _write_yaml_report(schema_report, config.output_file)
                if not config.quiet:
                    print(f"✓ Schema report written to {config.output_file}")

            total_time = time.time() - start_time

            # Print summary if not quiet
            if not config.quiet:
                _print_schema_summary(schema_report, total_time)

            return SchemaReportResult(
                schema_report=schema_report, output_file=config.output_file, total_time_seconds=total_time
            )

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Schema report generation failed: {e}")

        if not config.quiet:
            print(f" Schema report generation failed: {e}")

        raise


def _create_qc_report(db: GraphDatabase, group_by: str = "provided_by") -> QCReport:
    """Create QC report using DuckDB queries."""

    # Get basic counts
    try:
        total_nodes = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        total_edges = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        # Get dangling edges count if table exists
        dangling_edges = 0
        try:
            dangling_edges = db.conn.execute("SELECT COUNT(*) FROM dangling_edges").fetchone()[0]
        except:
            pass

        # Get duplicate nodes count if table exists
        duplicate_nodes = 0
        try:
            duplicate_nodes = db.conn.execute("SELECT COUNT(*) FROM duplicate_nodes").fetchone()[0]
        except:
            pass

        # Get singleton nodes count if table exists
        singleton_nodes = 0
        try:
            singleton_nodes = db.conn.execute("SELECT COUNT(*) FROM singleton_nodes").fetchone()[0]
        except:
            pass

    except Exception as e:
        logger.error(f"Failed to get basic counts: {e}")
        raise Exception(f"Failed to analyze database: {e}")

    # Get nodes report by group_by column
    nodes_by_source = _get_nodes_qc_report(db, group_by=group_by)

    # Get edges report by group_by column
    edges_by_source = _get_edges_qc_report(db, group_by=group_by)

    # Get dangling edges report by group_by column
    dangling_edges_by_source = _get_dangling_edges_qc_report(db, group_by=group_by)

    # Get duplicate nodes report by group_by column
    duplicate_nodes_by_source = _get_duplicate_nodes_qc_report(db, group_by=group_by)

    # Get duplicate edges report by group_by column
    duplicate_edges_by_source = _get_duplicate_edges_qc_report(db, group_by=group_by)

    # Create summary
    summary = QCSummary(
        total_nodes=total_nodes,
        total_edges=total_edges,
        dangling_edges=dangling_edges,
        duplicate_nodes=duplicate_nodes,
        singleton_nodes=singleton_nodes,
    )

    return QCReport(
        summary=summary,
        nodes=nodes_by_source,
        edges=edges_by_source,
        dangling_edges=dangling_edges_by_source,
        duplicate_nodes=duplicate_nodes_by_source,
        duplicate_edges=duplicate_edges_by_source,
    )


def _get_nodes_qc_report(db: GraphDatabase, group_by: str = "provided_by") -> list[NodeSourceReport]:
    """Create nodes section of QC report."""

    # Validate the group_by column exists
    try:
        db.conn.execute(f"SELECT {group_by} FROM nodes LIMIT 1").fetchone()
        source_column = group_by
    except Exception:
        logger.warning(f"Column {group_by} not found in nodes table")
        return []

    try:
        # Get sources
        sources = db.conn.execute(f"SELECT DISTINCT {source_column} FROM nodes ORDER BY {source_column}").fetchall()
    except Exception:
        logger.warning(f"Failed to get {source_column} sources from nodes table")
        return []

    nodes_report = []
    for (source,) in sources:
        if source is None:
            continue  # Skip NULL sources
        try:
            # Get stats for this source
            source_stats = db.conn.execute(
                f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT category) as category_count
                FROM nodes
                WHERE {source_column} = ?
            """,
                [source],
            ).fetchone()

            total, category_count = source_stats

            # Get categories for this source
            categories = db.conn.execute(
                f"""
                SELECT
                    CASE
                        WHEN category IS NULL THEN 'unknown'
                        WHEN typeof(category) = 'VARCHAR[]' THEN array_to_string(category, '|')
                        ELSE CAST(category AS VARCHAR)
                    END as category,
                    COUNT(*) as count
                FROM nodes
                WHERE {source_column} = ?
                GROUP BY category
                ORDER BY category
            """,
                [source],
            ).fetchall()

            # Get namespaces for this source
            namespaces = db.conn.execute(
                f"""
                SELECT
                    split_part(id, ':', 1) as namespace,
                    COUNT(*) as count
                FROM nodes
                WHERE {source_column} = ?
                GROUP BY split_part(id, ':', 1)
                ORDER BY namespace
            """,
                [source],
            ).fetchall()

            node_report = NodeSourceReport(
                name=source,
                total_number=total,
                categories=[cat for cat, _ in categories],
                namespaces=[ns for ns, _ in namespaces],
            )

            nodes_report.append(node_report)

        except Exception as e:
            logger.error(f"Failed to analyze nodes for source {source}: {e}")
            continue

    return nodes_report


def _get_edges_qc_report(db: GraphDatabase, group_by: str = "provided_by") -> list[EdgeSourceReport]:
    """Create edges section of QC report."""

    # Determine which column to use for source grouping
    # If group_by is specified and exists, use it; otherwise fall back
    source_column = None

    # First try the specified group_by column
    try:
        db.conn.execute(f"SELECT {group_by} FROM edges LIMIT 1").fetchone()
        source_column = group_by
    except Exception:
        # Fall back to provided_by or primary_knowledge_source
        for col in ["provided_by", "primary_knowledge_source"]:
            try:
                db.conn.execute(f"SELECT {col} FROM edges LIMIT 1").fetchone()
                source_column = col
                break
            except Exception:
                continue

    if source_column is None:
        logger.warning("No grouping column found in edges table")
        return []

    try:
        # Get sources
        sources = db.conn.execute(f"SELECT DISTINCT {source_column} FROM edges ORDER BY {source_column}").fetchall()
    except Exception as e:
        logger.warning(f"Failed to get edge sources: {e}")
        return []

    edges_report = []
    for (source,) in sources:
        if source is None:
            continue  # Skip NULL sources
        try:
            # Get basic stats for this source
            source_stats = db.conn.execute(
                f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT predicate) as predicate_count
                FROM edges
                WHERE {source_column} = ?
            """,
                [source],
            ).fetchone()

            total, predicate_count = source_stats

            # Get predicates for this source
            predicates = db.conn.execute(
                f"""
                SELECT
                    COALESCE(predicate, 'unknown') as predicate,
                    COUNT(*) as count
                FROM edges
                WHERE {source_column} = ?
                GROUP BY predicate
                ORDER BY predicate
            """,
                [source],
            ).fetchall()

            # Get subject/object namespaces
            namespaces = db.conn.execute(
                f"""
                SELECT namespace, SUM(count) as count FROM (
                    SELECT split_part(subject, ':', 1) as namespace, COUNT(*) as count
                    FROM edges
                    WHERE {source_column} = ?
                    GROUP BY split_part(subject, ':', 1)
                    UNION ALL
                    SELECT split_part(object, ':', 1) as namespace, COUNT(*) as count
                    FROM edges
                    WHERE {source_column} = ?
                    GROUP BY split_part(object, ':', 1)
                )
                GROUP BY namespace
                ORDER BY namespace
            """,
                [source, source],
            ).fetchall()

            predicate_reports = [PredicateReport(uri=pred, count=count) for pred, count in predicates]

            edge_report = EdgeSourceReport(
                name=source, total_number=total, predicates=predicate_reports, namespaces=[ns for ns, _ in namespaces]
            )

            edges_report.append(edge_report)

        except Exception as e:
            logger.error(f"Failed to analyze edges for source {source}: {e}")
            continue

    return edges_report


def _get_dangling_edges_qc_report(db: GraphDatabase, group_by: str = "provided_by") -> list[EdgeSourceReport]:
    """Create dangling edges section of QC report, grouped by source."""

    # Check if dangling_edges table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM dangling_edges").fetchone()
    except Exception:
        return []  # Table doesn't exist

    # Determine which column to use for source grouping
    source_column = None

    # First try the specified group_by column
    try:
        db.conn.execute(f"SELECT {group_by} FROM dangling_edges LIMIT 1").fetchone()
        source_column = group_by
    except Exception:
        # Fall back to provided_by or primary_knowledge_source
        for col in ["provided_by", "primary_knowledge_source"]:
            try:
                db.conn.execute(f"SELECT {col} FROM dangling_edges LIMIT 1").fetchone()
                source_column = col
                break
            except Exception:
                continue

    if source_column is None:
        logger.warning("No grouping column found in dangling_edges table")
        return []

    try:
        # Get sources
        sources = db.conn.execute(
            f"SELECT DISTINCT {source_column} FROM dangling_edges ORDER BY {source_column}"
        ).fetchall()
    except Exception as e:
        logger.warning(f"Failed to get dangling_edges sources: {e}")
        return []

    dangling_report = []
    for (source,) in sources:
        if source is None:
            continue  # Skip NULL sources
        try:
            # Get basic stats for this source
            source_stats = db.conn.execute(
                f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT predicate) as predicate_count
                FROM dangling_edges
                WHERE {source_column} = ?
            """,
                [source],
            ).fetchone()

            total, predicate_count = source_stats

            # Get predicates for this source
            predicates = db.conn.execute(
                f"""
                SELECT
                    COALESCE(predicate, 'unknown') as predicate,
                    COUNT(*) as count
                FROM dangling_edges
                WHERE {source_column} = ?
                GROUP BY predicate
                ORDER BY predicate
            """,
                [source],
            ).fetchall()

            # Get subject/object namespaces
            namespaces = db.conn.execute(
                f"""
                SELECT namespace, SUM(count) as count FROM (
                    SELECT split_part(subject, ':', 1) as namespace, COUNT(*) as count
                    FROM dangling_edges
                    WHERE {source_column} = ?
                    GROUP BY split_part(subject, ':', 1)
                    UNION ALL
                    SELECT split_part(object, ':', 1) as namespace, COUNT(*) as count
                    FROM dangling_edges
                    WHERE {source_column} = ?
                    GROUP BY split_part(object, ':', 1)
                )
                GROUP BY namespace
                ORDER BY namespace
            """,
                [source, source],
            ).fetchall()

            predicate_reports = [PredicateReport(uri=pred, count=count) for pred, count in predicates]

            edge_report = EdgeSourceReport(
                name=source, total_number=total, predicates=predicate_reports, namespaces=[ns for ns, _ in namespaces]
            )

            dangling_report.append(edge_report)

        except Exception as e:
            logger.error(f"Failed to analyze dangling_edges for source {source}: {e}")
            continue

    return dangling_report


def _get_duplicate_nodes_qc_report(db: GraphDatabase, group_by: str = "provided_by") -> list[NodeSourceReport]:
    """Create duplicate nodes section of QC report, grouped by source."""

    # Check if duplicate_nodes table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM duplicate_nodes").fetchone()
    except Exception:
        return []  # Table doesn't exist

    # Determine which column to use for source grouping
    source_column = None

    try:
        db.conn.execute(f"SELECT {group_by} FROM duplicate_nodes LIMIT 1").fetchone()
        source_column = group_by
    except Exception:
        # Fall back to provided_by
        try:
            db.conn.execute("SELECT provided_by FROM duplicate_nodes LIMIT 1").fetchone()
            source_column = "provided_by"
        except Exception:
            pass

    if source_column is None:
        logger.warning("No grouping column found in duplicate_nodes table")
        return []

    try:
        sources = db.conn.execute(
            f"SELECT DISTINCT {source_column} FROM duplicate_nodes ORDER BY {source_column}"
        ).fetchall()
    except Exception as e:
        logger.warning(f"Failed to get duplicate_nodes sources: {e}")
        return []

    duplicate_nodes_report = []
    for (source,) in sources:
        if source is None:
            continue
        try:
            total = db.conn.execute(
                f"SELECT COUNT(*) FROM duplicate_nodes WHERE {source_column} = ?", [source]
            ).fetchone()[0]

            categories = db.conn.execute(
                f"""
                SELECT
                    CASE
                        WHEN category IS NULL THEN 'unknown'
                        WHEN typeof(category) = 'VARCHAR[]' THEN array_to_string(category, '|')
                        ELSE CAST(category AS VARCHAR)
                    END as category,
                    COUNT(*) as count
                FROM duplicate_nodes
                WHERE {source_column} = ?
                GROUP BY category
                ORDER BY category
            """,
                [source],
            ).fetchall()

            namespaces = db.conn.execute(
                f"""
                SELECT
                    split_part(id, ':', 1) as namespace,
                    COUNT(*) as count
                FROM duplicate_nodes
                WHERE {source_column} = ?
                GROUP BY split_part(id, ':', 1)
                ORDER BY namespace
            """,
                [source],
            ).fetchall()

            node_report = NodeSourceReport(
                name=source,
                total_number=total,
                categories=[cat for cat, _ in categories],
                namespaces=[ns for ns, _ in namespaces],
            )

            duplicate_nodes_report.append(node_report)

        except Exception as e:
            logger.error(f"Failed to analyze duplicate_nodes for source {source}: {e}")
            continue

    return duplicate_nodes_report


def _get_duplicate_edges_qc_report(db: GraphDatabase, group_by: str = "provided_by") -> list[EdgeSourceReport]:
    """Create duplicate edges section of QC report, grouped by source."""

    # Check if duplicate_edges table exists
    try:
        db.conn.execute("SELECT COUNT(*) FROM duplicate_edges").fetchone()
    except Exception:
        return []  # Table doesn't exist

    # Determine which column to use for source grouping
    source_column = None

    try:
        db.conn.execute(f"SELECT {group_by} FROM duplicate_edges LIMIT 1").fetchone()
        source_column = group_by
    except Exception:
        for col in ["provided_by", "primary_knowledge_source"]:
            try:
                db.conn.execute(f"SELECT {col} FROM duplicate_edges LIMIT 1").fetchone()
                source_column = col
                break
            except Exception:
                continue

    if source_column is None:
        logger.warning("No grouping column found in duplicate_edges table")
        return []

    try:
        sources = db.conn.execute(
            f"SELECT DISTINCT {source_column} FROM duplicate_edges ORDER BY {source_column}"
        ).fetchall()
    except Exception as e:
        logger.warning(f"Failed to get duplicate_edges sources: {e}")
        return []

    duplicate_edges_report = []
    for (source,) in sources:
        if source is None:
            continue
        try:
            source_stats = db.conn.execute(
                f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT predicate) as predicate_count
                FROM duplicate_edges
                WHERE {source_column} = ?
            """,
                [source],
            ).fetchone()

            total, predicate_count = source_stats

            predicates = db.conn.execute(
                f"""
                SELECT
                    COALESCE(predicate, 'unknown') as predicate,
                    COUNT(*) as count
                FROM duplicate_edges
                WHERE {source_column} = ?
                GROUP BY predicate
                ORDER BY predicate
            """,
                [source],
            ).fetchall()

            namespaces = db.conn.execute(
                f"""
                SELECT namespace, SUM(count) as count FROM (
                    SELECT split_part(subject, ':', 1) as namespace, COUNT(*) as count
                    FROM duplicate_edges
                    WHERE {source_column} = ?
                    GROUP BY split_part(subject, ':', 1)
                    UNION ALL
                    SELECT split_part(object, ':', 1) as namespace, COUNT(*) as count
                    FROM duplicate_edges
                    WHERE {source_column} = ?
                    GROUP BY split_part(object, ':', 1)
                )
                GROUP BY namespace
                ORDER BY namespace
            """,
                [source, source],
            ).fetchall()

            predicate_reports = [PredicateReport(uri=pred, count=count) for pred, count in predicates]

            edge_report = EdgeSourceReport(
                name=source, total_number=total, predicates=predicate_reports, namespaces=[ns for ns, _ in namespaces]
            )

            duplicate_edges_report.append(edge_report)

        except Exception as e:
            logger.error(f"Failed to analyze duplicate_edges for source {source}: {e}")
            continue

    return duplicate_edges_report


def _create_graph_stats_report(db: GraphDatabase) -> GraphStatsReport:
    """Create comprehensive graph statistics report."""

    try:
        # Get total counts
        total_nodes = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        total_edges = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        # Build the comprehensive report structure
        node_stats = _generate_node_stats(db, total_nodes)
        edge_stats = _generate_edge_stats(db, total_edges)

        return GraphStatsReport(graph_name="Graph Statistics", node_stats=node_stats, edge_stats=edge_stats)

    except Exception as e:
        logger.error(f"Failed to generate graph statistics: {e}")
        raise Exception(f"Failed to analyze database: {e}")


def _generate_node_stats(db: GraphDatabase, total_nodes: int) -> NodeStats:
    """Generate comprehensive node statistics."""

    # Get node categories and their counts
    category_counts = db.conn.execute("""
        SELECT 
            CASE 
                WHEN category IS NULL THEN 'unknown'
                WHEN typeof(category) = 'VARCHAR[]' THEN array_to_string(category, '|')
                ELSE CAST(category AS VARCHAR)
            END as category,
            COUNT(*) as count
        FROM nodes
        GROUP BY category
        ORDER BY category
    """).fetchall()

    # Get ID prefixes and their counts
    id_prefix_counts = db.conn.execute("""
        SELECT 
            split_part(id, ':', 1) as prefix,
            COUNT(*) as count
        FROM nodes
        GROUP BY split_part(id, ':', 1)
        ORDER BY prefix
    """).fetchall()

    # Get provided_by sources
    try:
        provided_by_sources = db.conn.execute("""
            SELECT DISTINCT provided_by
            FROM nodes
            WHERE provided_by IS NOT NULL
            ORDER BY provided_by
        """).fetchall()
    except:
        provided_by_sources = []

    # Build count_by_category structure
    count_by_category = {}
    for category, count in category_counts:
        # Get provided_by breakdown for this category if column exists
        try:
            provided_by_breakdown = db.conn.execute(
                """
                SELECT provided_by, COUNT(*) as count
                FROM nodes
                WHERE CASE
                    WHEN category IS NULL THEN 'unknown'
                    WHEN typeof(category) = 'VARCHAR[]' THEN array_to_string(category, '|')
                    ELSE CAST(category AS VARCHAR)
                END = ?
                GROUP BY provided_by
                ORDER BY provided_by
            """,
                [category],
            ).fetchall()

            # Filter out NULL provided_by values
            provided_by_dict = {pb: {"count": c} for pb, c in provided_by_breakdown if pb is not None}
            count_by_category[category] = CategoryStats(count=count, provided_by=provided_by_dict)
        except:
            # No provided_by column
            count_by_category[category] = CategoryStats(count=count)

    # Build count_by_id_prefixes structure
    count_by_id_prefixes = {prefix: count for prefix, count in id_prefix_counts}

    return NodeStats(
        total_nodes=total_nodes,
        count_by_category=count_by_category,
        count_by_id_prefixes=count_by_id_prefixes,
        node_categories=[cat for cat, _ in category_counts],
        node_id_prefixes=[prefix for prefix, _ in id_prefix_counts],
        provided_by=[pb[0] for pb in provided_by_sources if pb[0] is not None],
    )


def _generate_edge_stats(db: GraphDatabase, total_edges: int) -> EdgeStats:
    """Generate comprehensive edge statistics."""

    # Get all predicates
    predicate_counts = db.conn.execute("""
        SELECT
            COALESCE(predicate, 'unknown') as predicate,
            COUNT(*) as count
        FROM edges
        GROUP BY predicate
        ORDER BY predicate
    """).fetchall()

    # Determine which column to use for source grouping
    # Try provided_by first, then fall back to primary_knowledge_source
    source_column = None
    for col in ["provided_by", "primary_knowledge_source"]:
        try:
            db.conn.execute(f"SELECT {col} FROM edges LIMIT 1").fetchone()
            source_column = col
            break
        except Exception:
            continue

    # Get all sources
    provided_by_sources = []
    if source_column:
        try:
            provided_by_sources = db.conn.execute(f"""
                SELECT DISTINCT {source_column}
                FROM edges
                WHERE {source_column} IS NOT NULL
                ORDER BY {source_column}
            """).fetchall()
        except:
            provided_by_sources = []

    # Build count_by_predicates structure
    count_by_predicates = {}
    for predicate, count in predicate_counts:
        # Get source breakdown for this predicate if column exists
        if source_column:
            try:
                provided_by_breakdown = db.conn.execute(
                    f"""
                    SELECT {source_column}, COUNT(*) as count
                    FROM edges
                    WHERE COALESCE(predicate, 'unknown') = ?
                    GROUP BY {source_column}
                    ORDER BY {source_column}
                """,
                    [predicate],
                ).fetchall()

                # Filter out NULL values
                provided_by_dict = {pb: {"count": c} for pb, c in provided_by_breakdown if pb is not None}
                count_by_predicates[predicate] = PredicateStats(count=count, provided_by=provided_by_dict)
            except:
                count_by_predicates[predicate] = PredicateStats(count=count)
        else:
            count_by_predicates[predicate] = PredicateStats(count=count)

    return EdgeStats(
        total_edges=total_edges,
        count_by_predicates=count_by_predicates,
        predicates=[pred for pred, _ in predicate_counts],
        provided_by=[pb[0] for pb in provided_by_sources if pb[0] is not None],
    )


def _create_schema_analysis_report(
    db: GraphDatabase,
    include_biolink_compliance: bool = True,
) -> SchemaAnalysisReport:
    """Create schema analysis report.

    Args:
        db: GraphDatabase instance to analyze
        include_biolink_compliance: Whether to run biolink compliance analysis

    Returns:
        SchemaAnalysisReport with table schemas and biolink compliance
    """

    try:
        # Get table schemas
        tables_info = db.conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name IN ('nodes', 'edges')
        """).fetchall()

        tables = {}

        for (table_name,) in tables_info:
            # Get column information
            columns = db.conn.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """).fetchall()

            # Get record count
            count = db.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            table_schema = TableSchema(
                columns=[{"name": col, "type": dtype} for col, dtype in columns],
                column_count=len(columns),
                record_count=count,
            )

            tables[table_name] = table_schema

        # Generate biolink compliance analysis
        if include_biolink_compliance:
            from .schema import analyze_biolink_compliance

            compliance_result = analyze_biolink_compliance(db)

            # Extract missing required fields from violations
            missing_fields = [
                f"{v['table']}.{v['slot_name']}"
                for v in compliance_result.get("violations", [])
                if v["constraint_type"] == "missing_column" and v["severity"] == "error"
            ]

            # Generate human-readable message
            status = compliance_result["status"]
            if status == "passed":
                message = "All biolink model constraints passed"
            elif status == "warnings":
                message = f"Passed with {compliance_result['warning_count']} warnings"
            elif status == "failed":
                message = f"{compliance_result['error_count']} errors, {compliance_result['warning_count']} warnings"
            else:
                message = compliance_result.get("message", "Analysis failed")

            biolink_compliance = BiolinkCompliance(
                status=status,
                message=message,
                compliance_percentage=compliance_result.get("compliance_percentage"),
                missing_fields=missing_fields,
                extension_fields=[],
            )
        else:
            biolink_compliance = BiolinkCompliance(
                status="skipped",
                message="Biolink compliance analysis was skipped",
            )

        return SchemaAnalysisReport(tables=tables, analysis={}, biolink_compliance=biolink_compliance)

    except Exception as e:
        logger.error(f"Failed to generate schema report: {e}")
        raise Exception(f"Failed to analyze schema: {e}")


def _write_yaml_report(report: Any, output_file: Path) -> None:
    """Write report to YAML file."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert Pydantic model to dict for YAML serialization
        if hasattr(report, "model_dump"):
            report_dict = report.model_dump()
        else:
            report_dict = report

        with open(output_file, "w") as f:
            yaml.dump(report_dict, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.error(f"Failed to write report to {output_file}: {e}")
        raise


def _print_qc_summary(qc_report: QCReport, total_time: float) -> None:
    """Print QC report summary to console."""

    summary = qc_report.summary
    print(f"✓ QC report generated successfully")
    print(f"  📊 Summary:")
    print(f"    - Total nodes: {summary.total_nodes:,}")
    print(f"    - Total edges: {summary.total_edges:,}")
    if summary.dangling_edges > 0:
        print(f"    - Dangling edges: {summary.dangling_edges:,}")
    if summary.duplicate_nodes > 0:
        print(f"    - Duplicate nodes: {summary.duplicate_nodes:,}")
    if summary.singleton_nodes > 0:
        print(f"    - Singleton nodes: {summary.singleton_nodes:,}")

    nodes_sources = len(qc_report.nodes)
    edges_sources = len(qc_report.edges)
    print(f"    - Node sources: {nodes_sources}")
    print(f"    - Edge sources: {edges_sources}")
    print(f"  ⏱️  Total time: {total_time:.2f}s")


def _print_graph_stats_summary(stats_report: GraphStatsReport, total_time: float) -> None:
    """Print graph statistics summary to console."""

    node_stats = stats_report.node_stats
    edge_stats = stats_report.edge_stats

    print(f"✓ Graph statistics generated successfully")
    print(f"  📈 Statistics:")
    print(f"    - Total nodes: {node_stats.total_nodes:,}")
    print(f"    - Total edges: {edge_stats.total_edges:,}")
    print(f"    - Node categories: {len(node_stats.node_categories)}")
    print(f"    - Edge predicates: {len(edge_stats.predicates)}")
    print(f"    - ID prefixes: {len(node_stats.node_id_prefixes)}")
    print(f"  ⏱️  Total time: {total_time:.2f}s")


def _print_schema_summary(schema_report: SchemaAnalysisReport, total_time: float) -> None:
    """Print schema report summary to console."""

    tables = schema_report.tables
    print(f"✓ Schema report generated successfully")
    print(f"  📋 Schema Analysis:")

    for table_name, table_info in tables.items():
        columns = table_info.column_count
        records = table_info.record_count
        print(f"    - {table_name}: {columns} columns, {records:,} records")

    print(f"  ⏱️  Total time: {total_time:.2f}s")


# Tabular Report Functions


def _ensure_denormalized_edges_view(db: GraphDatabase) -> str:
    """
    Check if denormalized_edges exists; if not, create a temp view.

    Returns the table/view name to use.
    """
    # Check if denormalized_edges table exists
    tables = db.conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name = 'denormalized_edges'"
    ).fetchall()

    if tables:
        return "denormalized_edges"

    # Create temp view joining edges to nodes twice
    db.conn.execute("""
        CREATE OR REPLACE TEMP VIEW denormalized_edges AS
        SELECT
            e.*,
            sn.category AS subject_category,
            sn.in_taxon AS subject_taxon,
            split_part(e.subject, ':', 1) AS subject_namespace,
            on_.category AS object_category,
            on_.in_taxon AS object_taxon,
            split_part(e.object, ':', 1) AS object_namespace
        FROM edges e
        LEFT JOIN nodes sn ON e.subject = sn.id
        LEFT JOIN nodes on_ ON e.object = on_.id
    """)
    return "denormalized_edges"


def _export_query_result(
    db: GraphDatabase, query: str, output_path: Path, format: TabularReportFormat
) -> int:
    """
    Export query result to specified format.

    Returns the number of rows exported.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == TabularReportFormat.TSV:
        db.conn.execute(f"COPY ({query}) TO '{output_path}' (HEADER, DELIMITER '\\t')")
    elif format == TabularReportFormat.PARQUET:
        db.conn.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)")
    elif format == TabularReportFormat.JSONL:
        db.conn.execute(f"COPY ({query}) TO '{output_path}' (FORMAT JSON)")
    else:
        raise ValueError(f"Unsupported format: {format}")

    # Get row count
    count_result = db.conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()
    return count_result[0] if count_result else 0


def _get_available_columns(db: GraphDatabase, table_name: str) -> set[str]:
    """Get the set of column names available in a table."""
    try:
        columns = db.conn.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
        ).fetchall()
        return {col[0] for col in columns}
    except Exception:
        return set()


def _load_files_to_database(
    db: GraphDatabase,
    node_file: FileSpec | None = None,
    edge_file: FileSpec | None = None,
) -> None:
    """Load node and/or edge files into the database."""
    from .utils import get_duckdb_read_statement

    if node_file:
        read_stmt = get_duckdb_read_statement(node_file)
        db.conn.execute(f"CREATE OR REPLACE TABLE nodes AS SELECT * FROM {read_stmt}")
        logger.info(f"Loaded nodes from {node_file.path}")

    if edge_file:
        read_stmt = get_duckdb_read_statement(edge_file)
        db.conn.execute(f"CREATE OR REPLACE TABLE edges AS SELECT * FROM {read_stmt}")
        logger.info(f"Loaded edges from {edge_file.path}")


def generate_node_report(config: NodeReportConfig) -> NodeReportResult:
    """
    Generate a tabular node report grouped by categorical columns.

    This operation creates a summary report of nodes grouped by specified
    categorical columns (e.g., category, provided_by, namespace), with counts
    for each unique combination. Useful for understanding the distribution
    and composition of nodes in a graph.

    Can operate on either an existing DuckDB database or load nodes directly
    from a KGX file into an in-memory database.

    Special handling:
    - "namespace" column: Extracts the CURIE prefix from the id column

    Args:
        config: NodeReportConfig containing:
            - database_path: Path to existing database (or None to load from file)
            - node_file: FileSpec for direct file loading (if no database_path)
            - categorical_columns: List of columns to group by (e.g., ["category", "provided_by"])
            - output_file: Path to write the report (TSV, CSV, or Parquet)
            - output_format: Format for output file
            - quiet: Suppress console output

    Returns:
        NodeReportResult containing:
            - output_file: Path where report was written
            - total_rows: Number of unique combinations in the report
            - total_time_seconds: Report generation duration

    Raises:
        ValueError: If no valid columns found for the report
        Exception: If database operations fail
    """
    start_time = time.time()

    try:
        # Determine if we're using existing database or loading from file
        if config.database_path:
            db = GraphDatabase(config.database_path, read_only=True)
        else:
            # Load file into in-memory database
            db = GraphDatabase(None)
            _load_files_to_database(db, node_file=config.node_file)

        with db:
            if not config.quiet:
                print(f"📊 Generating node report...")

            # Get available columns
            available_cols = _get_available_columns(db, "nodes")

            # Build SELECT clause with requested columns
            select_parts = []
            for col in config.categorical_columns:
                if col == "namespace":
                    # Special handling: extract namespace from id
                    select_parts.append("split_part(id, ':', 1) AS namespace")
                elif col in available_cols:
                    select_parts.append(col)
                else:
                    logger.warning(f"Column '{col}' not found in nodes table, skipping")

            if not select_parts:
                raise ValueError("No valid columns found for report")

            # Build query
            select_clause = ", ".join(select_parts)
            query = f"SELECT {select_clause}, count(*) as count FROM nodes GROUP BY ALL ORDER BY count DESC"

            # Export to file
            if config.output_file:
                total_rows = _export_query_result(db, query, config.output_file, config.output_format)

                if not config.quiet:
                    print(f"✓ Node report written to {config.output_file}")
                    print(f"  - {total_rows:,} rows")
            else:
                # Just count if no output file
                total_rows = db.conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

            total_time = time.time() - start_time

            if not config.quiet:
                print(f"  ⏱️  Total time: {total_time:.2f}s")

            return NodeReportResult(
                output_file=config.output_file,
                total_rows=total_rows,
                total_time_seconds=total_time,
            )

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Node report generation failed: {e}")

        if not config.quiet:
            print(f"❌ Node report generation failed: {e}")

        raise


def generate_edge_report(config: EdgeReportConfig) -> EdgeReportResult:
    """
    Generate a tabular edge report with denormalized node information.

    This operation creates a summary report of edges grouped by specified
    categorical columns, with counts for each unique combination. The report
    can include denormalized node information (subject_category, object_category)
    by joining edges with the nodes table.

    Creates a 'denormalized_edges' view that joins edges with nodes to provide
    subject and object category information alongside edge predicates.

    Special handling:
    - "subject_namespace" / "object_namespace": Extract CURIE prefixes from subject/object

    Args:
        config: EdgeReportConfig containing:
            - database_path: Path to existing database (or None to load from files)
            - node_file: FileSpec for node file (if no database_path)
            - edge_file: FileSpec for edge file (if no database_path)
            - categorical_columns: List of columns to group by
              (e.g., ["predicate", "subject_category", "object_category"])
            - output_file: Path to write the report (TSV, CSV, or Parquet)
            - output_format: Format for output file
            - quiet: Suppress console output

    Returns:
        EdgeReportResult containing:
            - output_file: Path where report was written
            - total_rows: Number of unique combinations in the report
            - total_time_seconds: Report generation duration

    Raises:
        ValueError: If no valid columns found for the report
        Exception: If database operations fail
    """
    start_time = time.time()

    try:
        # Determine if we're using existing database or loading from files
        if config.database_path:
            db = GraphDatabase(config.database_path, read_only=True)
        else:
            # Load files into in-memory database
            db = GraphDatabase(None)
            _load_files_to_database(db, node_file=config.node_file, edge_file=config.edge_file)

        with db:
            if not config.quiet:
                print(f"📊 Generating edge report...")

            # Ensure denormalized edges view exists
            denorm_table = _ensure_denormalized_edges_view(db)

            # Get available columns from denormalized view
            available_cols = _get_available_columns(db, denorm_table)

            # Build SELECT clause with requested columns
            select_parts = []
            for col in config.categorical_columns:
                if col in available_cols:
                    select_parts.append(col)
                else:
                    logger.warning(f"Column '{col}' not found in {denorm_table}, skipping")

            if not select_parts:
                raise ValueError("No valid columns found for report")

            # Build query
            select_clause = ", ".join(select_parts)
            query = f"SELECT {select_clause}, count(*) as count FROM {denorm_table} GROUP BY ALL ORDER BY count DESC"

            # Export to file
            if config.output_file:
                total_rows = _export_query_result(db, query, config.output_file, config.output_format)

                if not config.quiet:
                    print(f"✓ Edge report written to {config.output_file}")
                    print(f"  - {total_rows:,} rows")
            else:
                # Just count if no output file
                total_rows = db.conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

            total_time = time.time() - start_time

            if not config.quiet:
                print(f"  ⏱️  Total time: {total_time:.2f}s")

            return EdgeReportResult(
                output_file=config.output_file,
                total_rows=total_rows,
                total_time_seconds=total_time,
            )

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Edge report generation failed: {e}")

        if not config.quiet:
            print(f"❌ Edge report generation failed: {e}")

        raise


def generate_node_examples(config: NodeExamplesConfig) -> NodeExamplesResult:
    """
    Generate sample nodes for each node type (category) in the graph.

    This operation extracts N representative examples for each unique value
    of the specified type column (typically "category"). Useful for data
    exploration, QC review, and documentation purposes.

    Uses DuckDB window functions to efficiently sample N rows per type:
    ROW_NUMBER() OVER (PARTITION BY type_column ORDER BY id) <= sample_size

    Can operate on either an existing DuckDB database or load nodes directly
    from a KGX file into an in-memory database.

    Args:
        config: NodeExamplesConfig containing:
            - database_path: Path to existing database (or None to load from file)
            - node_file: FileSpec for direct file loading (if no database_path)
            - type_column: Column to partition by (default: "category")
            - sample_size: Number of examples per type (default: 5)
            - output_file: Path to write the examples (TSV, CSV, or Parquet)
            - output_format: Format for output file
            - quiet: Suppress console output

    Returns:
        NodeExamplesResult containing:
            - output_file: Path where examples were written
            - types_sampled: Number of unique types found
            - total_examples: Total number of example rows written
            - total_time_seconds: Report generation duration

    Raises:
        ValueError: If type_column not found in nodes table
        Exception: If database operations fail
    """
    start_time = time.time()

    try:
        # Determine if we're using existing database or loading from file
        if config.database_path:
            db = GraphDatabase(config.database_path, read_only=True)
        else:
            # Load file into in-memory database
            db = GraphDatabase(None)
            _load_files_to_database(db, node_file=config.node_file)

        with db:
            if not config.quiet:
                print(f"📊 Generating node examples ({config.sample_size} per type)...")

            # Verify type column exists
            available_cols = _get_available_columns(db, "nodes")
            if config.type_column not in available_cols:
                raise ValueError(f"Type column '{config.type_column}' not found in nodes table")

            # Build query using window function
            query = f"""
                SELECT * EXCLUDE (rn) FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY {config.type_column} ORDER BY id) as rn
                    FROM nodes
                ) WHERE rn <= {config.sample_size}
                ORDER BY {config.type_column}, id
            """

            # Get stats
            types_count = db.conn.execute(
                f"SELECT COUNT(DISTINCT {config.type_column}) FROM nodes"
            ).fetchone()[0]

            # Export to file
            if config.output_file:
                total_examples = _export_query_result(db, query, config.output_file, config.output_format)

                if not config.quiet:
                    print(f"✓ Node examples written to {config.output_file}")
                    print(f"  - {types_count:,} types sampled")
                    print(f"  - {total_examples:,} total examples")
            else:
                total_examples = db.conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

            total_time = time.time() - start_time

            if not config.quiet:
                print(f"  ⏱️  Total time: {total_time:.2f}s")

            return NodeExamplesResult(
                output_file=config.output_file,
                types_sampled=types_count,
                total_examples=total_examples,
                total_time_seconds=total_time,
            )

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Node examples generation failed: {e}")

        if not config.quiet:
            print(f"❌ Node examples generation failed: {e}")

        raise


def generate_edge_examples(config: EdgeExamplesConfig) -> EdgeExamplesResult:
    """
    Generate sample edges for each edge type pattern in the graph.

    This operation extracts N representative examples for each unique combination
    of (subject_category, predicate, object_category). Useful for data exploration,
    QC review, and understanding the relationship patterns in a knowledge graph.

    Creates a denormalized view joining edges with nodes to include subject and
    object category information, then uses DuckDB window functions to efficiently
    sample N rows per edge type pattern.

    Can operate on either an existing DuckDB database or load nodes and edges
    directly from KGX files into an in-memory database.

    Args:
        config: EdgeExamplesConfig containing:
            - database_path: Path to existing database (or None to load from files)
            - node_file: FileSpec for node file (if no database_path)
            - edge_file: FileSpec for edge file (if no database_path)
            - sample_size: Number of examples per edge type (default: 5)
            - output_file: Path to write the examples (TSV, CSV, or Parquet)
            - output_format: Format for output file
            - quiet: Suppress console output

    Returns:
        EdgeExamplesResult containing:
            - output_file: Path where examples were written
            - types_sampled: Number of unique edge type patterns found
            - total_examples: Total number of example rows written
            - total_time_seconds: Report generation duration

    Raises:
        Exception: If database operations fail
    """
    start_time = time.time()

    try:
        # Determine if we're using existing database or loading from files
        if config.database_path:
            db = GraphDatabase(config.database_path, read_only=True)
        else:
            # Load files into in-memory database
            db = GraphDatabase(None)
            _load_files_to_database(db, node_file=config.node_file, edge_file=config.edge_file)

        with db:
            if not config.quiet:
                print(f"📊 Generating edge examples ({config.sample_size} per type)...")

            # Ensure denormalized edges view exists
            denorm_table = _ensure_denormalized_edges_view(db)

            # Get available columns
            available_cols = _get_available_columns(db, denorm_table)

            # Verify type columns exist
            valid_type_cols = []
            for col in config.type_columns:
                if col in available_cols:
                    valid_type_cols.append(col)
                else:
                    logger.warning(f"Type column '{col}' not found in {denorm_table}, skipping")

            if not valid_type_cols:
                raise ValueError("No valid type columns found for edge examples")

            # Build partition clause
            partition_clause = ", ".join(valid_type_cols)

            # Build query using window function
            query = f"""
                SELECT * EXCLUDE (rn) FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY {partition_clause} ORDER BY subject, object) as rn
                    FROM {denorm_table}
                ) WHERE rn <= {config.sample_size}
                ORDER BY {partition_clause}, subject, object
            """

            # Get stats
            types_count = db.conn.execute(
                f"SELECT COUNT(*) FROM (SELECT DISTINCT {partition_clause} FROM {denorm_table})"
            ).fetchone()[0]

            # Export to file
            if config.output_file:
                total_examples = _export_query_result(db, query, config.output_file, config.output_format)

                if not config.quiet:
                    print(f"✓ Edge examples written to {config.output_file}")
                    print(f"  - {types_count:,} types sampled")
                    print(f"  - {total_examples:,} total examples")
            else:
                total_examples = db.conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

            total_time = time.time() - start_time

            if not config.quiet:
                print(f"  ⏱️  Total time: {total_time:.2f}s")

            return EdgeExamplesResult(
                output_file=config.output_file,
                types_sampled=types_count,
                total_examples=total_examples,
                total_time_seconds=total_time,
            )

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Edge examples generation failed: {e}")

        if not config.quiet:
            print(f"❌ Edge examples generation failed: {e}")

        raise
