"""
Normalize operation for applying SSSOM mappings to graph data.
"""

import time
from pathlib import Path
from typing import List, Optional
from loguru import logger
from tqdm import tqdm

from koza.model.graph_operations import (
    NormalizeConfig, NormalizeResult, FileSpec, FileLoadResult,
    OperationSummary, DatabaseStats, KGXFormat
)
from .utils import GraphDatabase, print_operation_summary


def normalize_graph(config: NormalizeConfig) -> NormalizeResult:
    """
    Apply SSSOM mappings to normalize node identifiers in graph data.
    
    Args:
        config: NormalizeConfig with mapping files and options
        
    Returns:
        NormalizeResult with operation statistics
    """
    start_time = time.time()
    mappings_loaded: List[FileLoadResult] = []
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
            
            if 'nodes' not in existing_tables and 'edges' not in existing_tables:
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
                        print(f"  - {file_spec.path.name}: {result.records_loaded:,} mappings "
                              f"({result.detected_format.value} format)")
                
                # Create final mappings table
                _create_mappings_table(db, mappings_loaded)
                
                if not config.quiet:
                    mappings_count = db.conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0]
                    print(f"✓ Loaded {mappings_count:,} total mappings")
            
            # Apply normalization to edges table if it exists  
            edges_normalized = 0
            if 'edges' in existing_tables:
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
            success_message = f"Applied {len(mappings_loaded)} mapping files, normalized {edges_normalized:,} edge references"
            
            summary = OperationSummary(
                operation="normalize",
                success=True,
                message=success_message,
                stats=final_stats,
                files_processed=len(mappings_loaded),
                total_time_seconds=total_time,
                warnings=warnings,
                errors=errors
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
                warnings=warnings
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
            errors=errors
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
            warnings=warnings
        )


def _load_sssom_file(db: GraphDatabase, file_spec: FileSpec) -> FileLoadResult:
    """
    Load an SSSOM file with proper header handling.
    
    Args:
        db: GraphDatabase instance
        file_spec: FileSpec for the SSSOM file
        
    Returns:
        FileLoadResult with load statistics
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
        
        logger.info(f"Loaded {records_loaded} mappings from {file_spec.path} "
                   f"into temp table {temp_table_name} in {load_time:.2f}s")
        
        return FileLoadResult(
            file_spec=file_spec,
            records_loaded=records_loaded,
            detected_format=KGXFormat.TSV,  # SSSOM files are always TSV
            load_time_seconds=load_time,
            errors=errors,
            temp_table_name=temp_table_name
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
            errors=errors
        )


def _create_mappings_table(db: GraphDatabase, mapping_results: List[FileLoadResult]):
    """Create final mappings table from temp tables."""
    # Get temp tables that loaded successfully
    mapping_tables = []
    for result in mapping_results:
        if result.temp_table_name and not result.errors:
            mapping_tables.append(result.temp_table_name)
    
    if not mapping_tables:
        raise ValueError("No mapping files loaded successfully")
    
    # Create mappings table using UNION ALL BY NAME
    union_stmt = " UNION ALL BY NAME ".join([f"SELECT * FROM {table}" for table in mapping_tables])
    db.conn.execute(f"CREATE OR REPLACE TABLE mappings AS {union_stmt}")
    
    logger.info(f"Created mappings table from {len(mapping_tables)} temp tables")
    
    # Clean up temp tables
    for result in mapping_results:
        if result.temp_table_name and not result.errors:
            try:
                db.conn.execute(f"DROP TABLE {result.temp_table_name}")
                logger.debug(f"Cleaned up temp table {result.temp_table_name}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp table {result.temp_table_name}: {e}")


def _normalize_edges_table(db: GraphDatabase, config: NormalizeConfig) -> int:
    """
    Apply SSSOM mappings to normalize edge subject/object references.
    
    Preserves existing original_subject and original_object columns if they exist.
    
    Returns:
        Number of edge references that were normalized
    """
    # Check if original_subject and original_object columns already exist
    edge_columns_result = db.conn.execute("DESCRIBE edges").fetchall()
    existing_columns = {col[0] for col in edge_columns_result}
    has_original_subject = 'original_subject' in existing_columns
    has_original_object = 'original_object' in existing_columns
    
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
            if has_original_subject else
            "CASE WHEN COALESCE(m_subj.subject_id, e.subject) != e.subject THEN e.subject ELSE NULL END"
        )
        
        original_object_expr = (
            "CASE WHEN e.original_object IS NOT NULL THEN e.original_object"
            "     WHEN COALESCE(m_obj.subject_id, e.object) != e.object THEN e.object"
            "     ELSE NULL END"
            if has_original_object else
            "CASE WHEN COALESCE(m_obj.subject_id, e.object) != e.object THEN e.object ELSE NULL END"
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
        
        exclude_cols = ["subject", "object", "current_subject", "current_object", 
                       "normalized_subject", "normalized_object", "final_original_subject", "final_original_object"]
        if has_original_subject:
            exclude_cols.append("original_subject")
        if has_original_object:
            exclude_cols.append("original_object")
            
        update_query = f"""
            CREATE OR REPLACE TABLE edges AS
            SELECT 
                * EXCLUDE ({', '.join(exclude_cols)}),
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


def prepare_mapping_file_specs_from_paths(mapping_paths: List[Path], 
                                        source_name: Optional[str] = None) -> List[FileSpec]:
    """
    Convert list of mapping file paths to FileSpec objects.
    
    Args:
        mapping_paths: List of paths to SSSOM mapping files
        source_name: Optional source name for all files
        
    Returns:
        List of FileSpec objects for mapping files
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
            source_name=source_name or path.stem
        )
        file_specs.append(file_spec)
    
    return file_specs