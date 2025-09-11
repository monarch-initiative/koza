"""
Append operation for adding new KGX files to existing databases.

Handles schema evolution, incremental updates, and optional deduplication
while preserving existing graph structure.
"""

import time
from pathlib import Path
from typing import List, Dict, Set
from loguru import logger
from tqdm import tqdm

from koza.model.graph_operations import (
    AppendConfig, AppendResult, FileLoadResult, OperationSummary
)
from .utils import GraphDatabase, print_operation_summary, get_duckdb_read_statement
from .schema import generate_schema_report, write_schema_report_yaml, print_schema_summary


def append_graphs(config: AppendConfig) -> AppendResult:
    """
    Append new KGX files to an existing DuckDB database.
    
    Args:
        config: AppendConfig with database path and files to append
        
    Returns:
        AppendResult with operation statistics
    """
    start_time = time.time()
    files_loaded: List[FileLoadResult] = []
    schema_changes: List[str] = []
    new_columns_added = 0
    
    try:
        # Connect to existing database
        with GraphDatabase(config.database_path) as db:
            
            if not config.quiet:
                print(f"📂 Appending to existing database: {config.database_path}")
            
            # Get initial schema before appending
            initial_node_schema = _get_table_schema(db, "nodes")
            initial_edge_schema = _get_table_schema(db, "edges")
            initial_stats = db.get_stats()
            
            # Load node files
            if config.node_files:
                if not config.quiet:
                    print(f"📄 Loading {len(config.node_files)} node files...")
                
                files_loaded.extend(_append_files(
                    db, config.node_files, "nodes", config, initial_node_schema
                ))
            
            # Load edge files
            if config.edge_files:
                if not config.quiet:
                    print(f"🔗 Loading {len(config.edge_files)} edge files...")
                
                files_loaded.extend(_append_files(
                    db, config.edge_files, "edges", config, initial_edge_schema
                ))
            
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
                    print("🔄 Performing deduplication...")
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
            total_time_seconds=total_time
        )
        
        # Print summary if not quiet
        if not config.quiet:
            _print_append_summary(result, initial_stats)
            
            # Print schema report if available
            if result.schema_report:
                print_schema_summary(result.schema_report)
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
                errors=[str(e)]
            )
            print_operation_summary(summary)
        
        raise


def _get_table_schema(db: GraphDatabase, table_name: str) -> Dict[str, str]:
    """Get current schema of a table as {column_name: data_type}."""
    try:
        describe_result = db.conn.execute(f"DESCRIBE {table_name}").fetchall()
        return {col[0]: col[1] for col in describe_result}
    except Exception:
        # Table doesn't exist yet
        return {}


def _compare_schemas(table_name: str, old_schema: Dict[str, str], new_schema: Dict[str, str]) -> tuple[List[str], int]:
    """
    Compare schemas and return changes and new column count.
    
    Returns:
        Tuple of (change_descriptions, new_columns_count)
    """
    changes = []
    new_columns = set(new_schema.keys()) - set(old_schema.keys())
    
    if new_columns:
        changes.append(f"Added {len(new_columns)} new columns to {table_name}: {', '.join(sorted(new_columns))}")
    
    return changes, len(new_columns)


def _append_files(
    db: GraphDatabase, 
    file_specs: List, 
    table_type: str, 
    config: AppendConfig,
    existing_schema: Dict[str, str]
) -> List[FileLoadResult]:
    """Append files to existing table with schema evolution support."""
    
    files_loaded = []
    
    # Use progress bar if requested
    if config.show_progress:
        file_progress = tqdm(file_specs, desc=f"Loading {table_type} files", unit="file")
    else:
        file_progress = file_specs
    
    for file_spec in file_progress:
        if config.show_progress:
            file_progress.set_description(f"Loading {file_spec.path.name}")
        
        result = _append_single_file(db, file_spec, table_type, existing_schema)
        files_loaded.append(result)
        
        if not config.quiet and not config.show_progress:
            print(f"  - {file_spec.path.name}: {result.records_loaded:,} records "
                  f"({result.detected_format.value} format)")
    
    return files_loaded


def _append_single_file(
    db: GraphDatabase, 
    file_spec, 
    table_type: str, 
    existing_schema: Dict[str, str]
) -> FileLoadResult:
    """Append a single file with schema evolution support."""
    
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
        
        # Handle schema evolution - add missing columns to existing table
        if existing_schema:
            new_columns = set(file_columns.keys()) - set(existing_schema.keys())
            for col_name in new_columns:
                col_type = file_columns[col_name]
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
        
        logger.info(f"Appended {records_loaded} records from {file_spec.path} "
                   f"({file_spec.format.value} format) to {table_type} table in {load_time:.2f}s")
        
        return FileLoadResult(
            file_spec=file_spec,
            records_loaded=records_loaded,
            detected_format=file_spec.format,
            load_time_seconds=load_time,
            errors=errors
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
            errors=errors
        )


def _deduplicate_tables(db: GraphDatabase, config: AppendConfig) -> int:
    """
    Perform basic deduplication on nodes and edges tables.
    
    This is a simple implementation that removes exact duplicates by ID.
    More sophisticated deduplication strategies could be added later.
    """
    duplicates_removed = 0
    
    # Deduplicate nodes by ID (keep first occurrence)
    try:
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
        
    except Exception as e:
        logger.warning(f"Node deduplication failed: {e}")
    
    # Deduplicate edges by ID (keep first occurrence)
    try:
        edge_dupe_query = """
        CREATE TEMP TABLE edges_deduped AS
        SELECT DISTINCT ON (id) * FROM edges
        ORDER BY id
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
    print(f"    - Nodes: {initial_stats.nodes:,} → {result.final_stats.nodes:,} "
          f"(+{result.final_stats.nodes - initial_stats.nodes:,})")
    print(f"    - Edges: {initial_stats.edges:,} → {result.final_stats.edges:,} "
          f"(+{result.final_stats.edges - initial_stats.edges:,})")
    
    print(f"    - Database: {result.database_path} "
          f"({result.final_stats.database_size_mb:.1f} MB)")
    
    print(f"  ⏱️  Total time: {result.total_time_seconds:.2f}s")
    
    # Show any errors
    error_files = [f for f in result.files_loaded if f.errors]
    if error_files:
        print(f"  ⚠️  Files with errors:")
        for file_result in error_files:
            print(f"    - {file_result.file_spec.path.name}: {len(file_result.errors)} errors")