"""
Graph reporting and analysis operations.

This module provides comprehensive reporting capabilities for KGX graphs,
including QC analysis, graph statistics, and schema compliance reporting.
"""

import time
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

from koza.model.graph_operations import (
    QCReportConfig, QCReportResult, GraphStatsConfig, GraphStatsResult,
    SchemaReportConfig, SchemaReportResult, QCReport, QCSummary, 
    NodeSourceReport, EdgeSourceReport, PredicateReport, GraphStatsReport,
    NodeStats, EdgeStats, CategoryStats, PredicateStats, SchemaAnalysisReport,
    TableSchema, BiolinkCompliance
)
from .utils import GraphDatabase, print_operation_summary


def generate_qc_report(config: QCReportConfig) -> QCReportResult:
    """
    Generate comprehensive QC report for a graph database.
    
    Args:
        config: QCReportConfig with database and output parameters
        
    Returns:
        QCReportResult with QC analysis data
    """
    start_time = time.time()
    
    try:
        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")
        
        with GraphDatabase(config.database_path) as db:
            if not config.quiet:
                print(f"📊 Generating QC report for {config.database_path.name}...")
            
            # Generate the QC report using existing functionality
            qc_report = _create_qc_report(db)
            
            # Write to output file if specified
            if config.output_file:
                _write_yaml_report(qc_report, config.output_file)
                if not config.quiet:
                    print(f"✓ QC report written to {config.output_file}")
            
            total_time = time.time() - start_time
            
            # Print summary if not quiet
            if not config.quiet:
                _print_qc_summary(qc_report, total_time)
            
            return QCReportResult(
                qc_report=qc_report,
                output_file=config.output_file,
                total_time_seconds=total_time
            )
            
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"QC report generation failed: {e}")
        
        if not config.quiet:
            print(f"❌ QC report generation failed: {e}")
        
        raise


def generate_graph_stats(config: GraphStatsConfig) -> GraphStatsResult:
    """
    Generate comprehensive graph statistics report.
    
    Args:
        config: GraphStatsConfig with database and output parameters
        
    Returns:
        GraphStatsResult with graph statistics data
    """
    start_time = time.time()
    
    try:
        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")
        
        with GraphDatabase(config.database_path) as db:
            if not config.quiet:
                print(f"📈 Generating graph statistics for {config.database_path.name}...")
            
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
                stats_report=stats_report,
                output_file=config.output_file,
                total_time_seconds=total_time
            )
            
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Graph statistics generation failed: {e}")
        
        if not config.quiet:
            print(f"❌ Graph statistics generation failed: {e}")
        
        raise


def generate_schema_compliance_report(config: SchemaReportConfig) -> SchemaReportResult:
    """
    Generate schema analysis and compliance report.
    
    Args:
        config: SchemaReportConfig with database and output parameters
        
    Returns:
        SchemaReportResult with schema analysis data
    """
    start_time = time.time()
    
    try:
        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")
        
        with GraphDatabase(config.database_path) as db:
            if not config.quiet:
                print(f"📋 Generating schema report for {config.database_path.name}...")
            
            # Generate schema analysis report
            schema_report = _create_schema_analysis_report(db)
            
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
                schema_report=schema_report,
                output_file=config.output_file,
                total_time_seconds=total_time
            )
            
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Schema report generation failed: {e}")
        
        if not config.quiet:
            print(f"❌ Schema report generation failed: {e}")
        
        raise


def _create_qc_report(db: GraphDatabase) -> QCReport:
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
    
    # Get nodes report by provided_by
    nodes_by_source = _get_nodes_qc_report(db)
    
    # Get edges report by provided_by  
    edges_by_source = _get_edges_qc_report(db)
    
    # Create summary
    summary = QCSummary(
        total_nodes=total_nodes,
        total_edges=total_edges,
        dangling_edges=dangling_edges,
        duplicate_nodes=duplicate_nodes,
        singleton_nodes=singleton_nodes
    )
    
    return QCReport(
        summary=summary,
        nodes=nodes_by_source,
        edges=edges_by_source
    )


def _get_nodes_qc_report(db: GraphDatabase) -> List[NodeSourceReport]:
    """Create nodes section of QC report."""
    
    try:
        # Get provided_by sources
        sources = db.conn.execute("SELECT DISTINCT provided_by FROM nodes ORDER BY provided_by").fetchall()
    except Exception:
        logger.warning("No provided_by column found in nodes table")
        return []
    
    nodes_report = []
    for (source,) in sources:
        try:
            # Get stats for this source
            source_stats = db.conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT category) as category_count
                FROM nodes 
                WHERE provided_by = ?
            """, [source]).fetchone()
            
            total, category_count = source_stats
            
            # Get categories for this source
            categories = db.conn.execute("""
                SELECT 
                    CASE 
                        WHEN category IS NULL THEN 'unknown'
                        WHEN typeof(category) = 'VARCHAR[]' THEN array_to_string(category, '|')
                        ELSE CAST(category AS VARCHAR)
                    END as category,
                    COUNT(*) as count
                FROM nodes 
                WHERE provided_by = ?
                GROUP BY category
                ORDER BY category
            """, [source]).fetchall()
            
            # Get namespaces for this source
            namespaces = db.conn.execute("""
                SELECT 
                    split_part(id, ':', 1) as namespace,
                    COUNT(*) as count  
                FROM nodes
                WHERE provided_by = ?
                GROUP BY split_part(id, ':', 1)
                ORDER BY namespace
            """, [source]).fetchall()
            
            node_report = NodeSourceReport(
                name=source,
                total_number=total,
                categories=[cat for cat, _ in categories],
                namespaces=[ns for ns, _ in namespaces]
            )
            
            nodes_report.append(node_report)
            
        except Exception as e:
            logger.error(f"Failed to analyze nodes for source {source}: {e}")
            continue
    
    return nodes_report


def _get_edges_qc_report(db: GraphDatabase) -> List[EdgeSourceReport]:
    """Create edges section of QC report."""
    
    try:
        # Get provided_by sources
        sources = db.conn.execute("SELECT DISTINCT provided_by FROM edges ORDER BY provided_by").fetchall()
    except Exception:
        logger.warning("No provided_by column found in edges table")
        return []
    
    edges_report = []
    for (source,) in sources:
        try:
            # Get basic stats for this source
            source_stats = db.conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT predicate) as predicate_count
                FROM edges 
                WHERE provided_by = ?
            """, [source]).fetchone()
            
            total, predicate_count = source_stats
            
            # Get predicates for this source
            predicates = db.conn.execute("""
                SELECT 
                    COALESCE(predicate, 'unknown') as predicate,
                    COUNT(*) as count
                FROM edges 
                WHERE provided_by = ?
                GROUP BY predicate
                ORDER BY predicate
            """, [source]).fetchall()
            
            # Get subject/object namespaces
            namespaces = db.conn.execute("""
                SELECT namespace, SUM(count) as count FROM (
                    SELECT split_part(subject, ':', 1) as namespace, COUNT(*) as count 
                    FROM edges 
                    WHERE provided_by = ?
                    GROUP BY split_part(subject, ':', 1)
                    UNION ALL
                    SELECT split_part(object, ':', 1) as namespace, COUNT(*) as count 
                    FROM edges 
                    WHERE provided_by = ?
                    GROUP BY split_part(object, ':', 1)
                ) 
                GROUP BY namespace
                ORDER BY namespace
            """, [source, source]).fetchall()
            
            predicate_reports = [PredicateReport(uri=pred, count=count) for pred, count in predicates]
            
            edge_report = EdgeSourceReport(
                name=source,
                total_number=total,
                predicates=predicate_reports,
                namespaces=[ns for ns, _ in namespaces]
            )
            
            edges_report.append(edge_report)
            
        except Exception as e:
            logger.error(f"Failed to analyze edges for source {source}: {e}")
            continue
    
    return edges_report


def _create_graph_stats_report(db: GraphDatabase) -> GraphStatsReport:
    """Create comprehensive graph statistics report."""
    
    try:
        # Get total counts
        total_nodes = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        total_edges = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        
        # Build the comprehensive report structure
        node_stats = _generate_node_stats(db, total_nodes)
        edge_stats = _generate_edge_stats(db, total_edges)
        
        return GraphStatsReport(
            graph_name="Graph Statistics",
            node_stats=node_stats,
            edge_stats=edge_stats
        )
        
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
            ORDER BY provided_by
        """).fetchall()
    except:
        provided_by_sources = []
    
    # Build count_by_category structure
    count_by_category = {}
    for category, count in category_counts:
        # Get provided_by breakdown for this category if column exists
        try:
            provided_by_breakdown = db.conn.execute("""
                SELECT provided_by, COUNT(*) as count
                FROM nodes
                WHERE CASE 
                    WHEN category IS NULL THEN 'unknown'
                    WHEN typeof(category) = 'VARCHAR[]' THEN array_to_string(category, '|')
                    ELSE CAST(category AS VARCHAR)
                END = ?
                GROUP BY provided_by
                ORDER BY provided_by
            """, [category]).fetchall()
            
            provided_by_dict = {pb: {"count": c} for pb, c in provided_by_breakdown}
            count_by_category[category] = CategoryStats(
                count=count,
                provided_by=provided_by_dict
            )
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
        provided_by=[pb[0] for pb in provided_by_sources] if provided_by_sources else []
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
    
    # Get all provided_by sources
    try:
        provided_by_sources = db.conn.execute("""
            SELECT DISTINCT provided_by
            FROM edges
            ORDER BY provided_by
        """).fetchall()
    except:
        provided_by_sources = []
    
    # Build count_by_predicates structure
    count_by_predicates = {}
    for predicate, count in predicate_counts:
        # Get provided_by breakdown for this predicate if column exists
        try:
            provided_by_breakdown = db.conn.execute("""
                SELECT provided_by, COUNT(*) as count
                FROM edges
                WHERE COALESCE(predicate, 'unknown') = ?
                GROUP BY provided_by
                ORDER BY provided_by
            """, [predicate]).fetchall()
            
            provided_by_dict = {pb: {"count": c} for pb, c in provided_by_breakdown}
            count_by_predicates[predicate] = PredicateStats(
                count=count,
                provided_by=provided_by_dict
            )
        except:
            # No provided_by column
            count_by_predicates[predicate] = PredicateStats(count=count)
    
    return EdgeStats(
        total_edges=total_edges,
        count_by_predicates=count_by_predicates,
        predicates=[pred for pred, _ in predicate_counts],
        provided_by=[pb[0] for pb in provided_by_sources] if provided_by_sources else []
    )


def _create_schema_analysis_report(db: GraphDatabase) -> SchemaAnalysisReport:
    """Create schema analysis report."""
    
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
                record_count=count
            )
            
            tables[table_name] = table_schema
        
        # Add biolink compliance placeholder
        biolink_compliance = BiolinkCompliance(
            status="not_implemented",
            message="Biolink compliance analysis will be implemented in Phase 1"
        )
        
        return SchemaAnalysisReport(
            tables=tables,
            analysis={},
            biolink_compliance=biolink_compliance
        )
        
    except Exception as e:
        logger.error(f"Failed to generate schema report: {e}")
        raise Exception(f"Failed to analyze schema: {e}")


def _write_yaml_report(report: Any, output_file: Path) -> None:
    """Write report to YAML file."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert Pydantic model to dict for YAML serialization
        if hasattr(report, 'model_dump'):
            report_dict = report.model_dump()
        else:
            report_dict = report
            
        with open(output_file, 'w') as f:
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