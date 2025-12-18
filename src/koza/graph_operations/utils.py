"""
Shared utilities for graph operations using DuckDB.
"""

import time
from pathlib import Path

import duckdb
from loguru import logger

from koza.model.graph_operations import (
    DatabaseStats,
    FileLoadResult,
    FileSpec,
    KGXFileType,
    KGXFormat,
    OperationSummary,
)


def get_duckdb_read_statement(file_spec: FileSpec, sample_size: int | None = None) -> str:
    """
    Generate DuckDB read statement for the given file spec.

    Args:
        file_spec: FileSpec with path and format information
        sample_size: Optional sample size for JSONL schema inference (-1 for full scan)

    Returns:
        DuckDB read statement string
    """
    file_path_str = str(file_spec.path)
    format_type = file_spec.format

    if format_type == KGXFormat.TSV:
        return f"read_csv('{file_path_str}', delim='\\t', header=true, all_varchar=true)"
    elif format_type == KGXFormat.JSONL:
        if sample_size is not None:
            return f"read_json('{file_path_str}', format='newline_delimited', sample_size={sample_size})"
        return f"read_json('{file_path_str}', format='newline_delimited')"
    elif format_type == KGXFormat.PARQUET:
        return f"read_parquet('{file_path_str}')"
    else:
        raise ValueError(f"Unsupported format: {format_type}")


class GraphDatabase:
    """
    DuckDB connection manager for graph operations using Pydantic models.
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize GraphDatabase.

        Args:
            db_path: Path to persistent database file. If None, uses in-memory database.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path) if db_path else ":memory:")
        self._setup_database()

    def _setup_database(self):
        """Setup initial database - QC tables only, main tables created dynamically."""
        # Note: Main nodes/edges tables are created dynamically during file loading
        # to handle varying schemas using UNION ALL BY NAME

        # Create QC and archive tables (will be populated later)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS file_schemas (
                filename VARCHAR,
                table_type VARCHAR,
                column_name VARCHAR,
                data_type VARCHAR,
                file_source VARCHAR
            )
        """)

        logger.info("Database schema initialized (main tables created dynamically)")

    def load_file(self, file_spec: FileSpec, generate_provided_by: bool = True) -> FileLoadResult:
        """
        Load a KGX file into a temporary table for schema analysis.

        Args:
            file_spec: FileSpec describing the file to load
            generate_provided_by: If True, add provided_by column from filename (like cat-merge)

        Returns:
            FileLoadResult with load statistics
        """
        start_time = time.time()
        errors = []

        try:
            if not file_spec.path.exists():
                raise FileNotFoundError(f"File not found: {file_spec.path}")

            read_stmt = get_duckdb_read_statement(file_spec)

            # Create unique temp table name for this file
            safe_filename = file_spec.path.stem.replace("-", "_").replace(".", "_")
            temp_table_name = f"temp_{file_spec.file_type.value}_{safe_filename}_{id(file_spec)}"

            # Build column additions
            source_name = file_spec.source_name or file_spec.path.stem
            extra_columns = []
            extra_columns.append(f"'{source_name}' as file_source")
            if generate_provided_by:
                extra_columns.append(f"'{source_name}' as provided_by")

            # Load into temp table with source tracking and optional provided_by
            extra_cols_str = ", " + ", ".join(extra_columns) if extra_columns else ""
            create_sql = f"""
                CREATE TEMP TABLE {temp_table_name} AS
                SELECT *{extra_cols_str}
                FROM {read_stmt}
            """

            # Execute table creation
            try:
                self.conn.execute(create_sql)
            except duckdb.InvalidInputException as e:
                error_msg = str(e)
                # Catch specific JSONL schema inference failure:
                # "Invalid Input Error: JSON transform error ... has unknown key ..."
                if (
                    "unknown key" in error_msg
                    and "JSON transform error" in error_msg
                    and file_spec.format == KGXFormat.JSONL
                ):
                    logger.warning(
                        f"Schema inference failed for {file_spec.path}, retrying with full scan..."
                    )
                    read_stmt = get_duckdb_read_statement(file_spec, sample_size=-1)
                    create_sql = f"""
                        CREATE TEMP TABLE {temp_table_name} AS
                        SELECT *{extra_cols_str}
                        FROM {read_stmt}
                    """
                    self.conn.execute(create_sql)
                else:
                    raise

            # Get record count
            count_result = self.conn.execute(f"SELECT COUNT(*) FROM {temp_table_name}").fetchone()
            records_loaded = count_result[0] if count_result else 0

            # Analyze schema and store metadata
            self._analyze_file_schema(file_spec, temp_table_name)

            load_time = time.time() - start_time

            logger.info(
                f"Loaded {records_loaded} records from {file_spec.path} "
                f"into temp table {temp_table_name} ({file_spec.format.value} format) in {load_time:.2f}s"
            )

            return FileLoadResult(
                file_spec=file_spec,
                records_loaded=records_loaded,
                detected_format=file_spec.format,
                load_time_seconds=load_time,
                errors=errors,
                temp_table_name=temp_table_name,  # Store temp table name for later union
            )

        except Exception as e:
            load_time = time.time() - start_time
            error_msg = f"Failed to load {file_spec.path}: {e}"
            errors.append(error_msg)
            logger.error(error_msg)

            return FileLoadResult(
                file_spec=file_spec,
                records_loaded=0,
                detected_format=file_spec.format,
                load_time_seconds=load_time,
                errors=errors,
            )

    def _analyze_file_schema(self, file_spec: FileSpec, temp_table_name: str):
        """Analyze and store schema information for a loaded file."""
        try:
            # Get column information from temp table
            describe_result = self.conn.execute(f"DESCRIBE {temp_table_name}").fetchall()

            # Store schema metadata
            for column_name, data_type, *_ in describe_result:
                # Skip our added file_source column in analysis
                if column_name == "file_source":
                    continue

                self.conn.execute(
                    """
                    INSERT INTO file_schemas (filename, table_type, column_name, data_type, file_source)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    [
                        str(file_spec.path),
                        file_spec.file_type.value,
                        column_name,
                        data_type,
                        file_spec.source_name or file_spec.path.stem,
                    ],
                )

            logger.debug(f"Analyzed schema for {file_spec.path}: {len(describe_result)} columns")

        except Exception as e:
            logger.warning(f"Failed to analyze schema for {file_spec.path}: {e}")

    def create_final_tables(self, file_results: list[FileLoadResult]):
        """Create final nodes/edges tables using UNION ALL BY NAME from temp tables."""
        # Group temp tables by type
        nodes_tables = []
        edges_tables = []

        for result in file_results:
            if result.temp_table_name and not result.errors:
                if result.file_spec.file_type == KGXFileType.NODES:
                    nodes_tables.append(result.temp_table_name)
                elif result.file_spec.file_type == KGXFileType.EDGES:
                    edges_tables.append(result.temp_table_name)

        # Create nodes table if we have node files
        if nodes_tables:
            union_stmt = " UNION ALL BY NAME ".join([f"SELECT * FROM {table}" for table in nodes_tables])
            self.conn.execute(f"CREATE OR REPLACE TABLE nodes AS {union_stmt}")
            logger.info(f"Created nodes table from {len(nodes_tables)} temp tables")

            # Create QC tables based on final nodes schema
            self.conn.execute("CREATE OR REPLACE TABLE duplicate_nodes AS SELECT * FROM nodes WHERE 1=0")
            self.conn.execute("CREATE OR REPLACE TABLE singleton_nodes AS SELECT * FROM nodes WHERE 1=0")

        # Create edges table if we have edge files
        if edges_tables:
            union_stmt = " UNION ALL BY NAME ".join([f"SELECT * FROM {table}" for table in edges_tables])
            self.conn.execute(f"CREATE OR REPLACE TABLE edges AS {union_stmt}")
            logger.info(f"Created edges table from {len(edges_tables)} temp tables")

            # Create QC tables based on final edges schema
            self.conn.execute("CREATE OR REPLACE TABLE dangling_edges AS SELECT * FROM edges WHERE 1=0")

        # Clean up temp tables if using persistent database
        if self.db_path:
            for result in file_results:
                if result.temp_table_name and not result.errors:
                    try:
                        self.conn.execute(f"DROP TABLE {result.temp_table_name}")
                        logger.debug(f"Cleaned up temp table {result.temp_table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp table {result.temp_table_name}: {e}")

    def get_schema_report(self) -> dict:
        """Generate schema analysis report from loaded files."""
        try:
            # Get schema summary by table type
            schema_query = """
            SELECT 
                table_type,
                COUNT(DISTINCT filename) as file_count,
                COUNT(DISTINCT column_name) as unique_columns,
                STRING_AGG(DISTINCT column_name, ', ' ORDER BY column_name) as all_columns
            FROM file_schemas 
            GROUP BY table_type
            """
            schema_results = self.conn.execute(schema_query).fetchall()

            # Get per-file column counts
            file_query = """
            SELECT 
                filename,
                table_type,
                COUNT(column_name) as column_count,
                STRING_AGG(column_name, ', ' ORDER BY column_name) as columns
            FROM file_schemas
            GROUP BY filename, table_type
            ORDER BY filename
            """
            file_results = self.conn.execute(file_query).fetchall()

            return {
                "summary": {
                    result[0]: {
                        "file_count": result[1],
                        "unique_columns": result[2],
                        "all_columns": result[3].split(", ") if result[3] else [],
                    }
                    for result in schema_results
                },
                "files": [
                    {
                        "filename": result[0],
                        "table_type": result[1],
                        "column_count": result[2],
                        "columns": result[3].split(", ") if result[3] else [],
                    }
                    for result in file_results
                ],
            }

        except Exception as e:
            logger.error(f"Failed to generate schema report: {e}")
            return {"error": str(e)}

    def get_stats(self) -> DatabaseStats:
        """Get database statistics."""
        stats_dict = {}

        # Get counts for each table
        for table in ["nodes", "edges", "dangling_edges", "duplicate_nodes", "singleton_nodes"]:
            try:
                result = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                stats_dict[table] = result[0] if result else 0
            except Exception:
                stats_dict[table] = 0

        # Get database size if persistent
        database_size_mb = None
        if self.db_path and self.db_path.exists():
            size_bytes = self.db_path.stat().st_size
            database_size_mb = size_bytes / (1024 * 1024)

        return DatabaseStats(
            nodes=stats_dict["nodes"],
            edges=stats_dict["edges"],
            dangling_edges=stats_dict["dangling_edges"],
            duplicate_nodes=stats_dict["duplicate_nodes"],
            singleton_nodes=stats_dict["singleton_nodes"],
            database_size_mb=database_size_mb,
        )

    def export_to_format(self, table_name: str, output_path: Path, format_type: KGXFormat):
        """
        Export a table to the specified format.

        Args:
            table_name: Name of the table to export
            output_path: Path for output file
            format_type: Target format
        """
        if format_type == KGXFormat.TSV:
            copy_sql = f"COPY {table_name} TO '{output_path}' (HEADER, DELIMITER '\\t')"
        elif format_type == KGXFormat.PARQUET:
            copy_sql = f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)"
        elif format_type == KGXFormat.JSONL:
            copy_sql = f"COPY {table_name} TO '{output_path}' (FORMAT JSON)"
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

        self.conn.execute(copy_sql)
        logger.info(f"Exported {table_name} to {output_path} ({format_type.value} format)")

    def export_to_archive(self, output_path: Path, graph_name: str, format: KGXFormat, compress: bool = False) -> None:
        """
        Export database tables to tar or tar.gz archive with standardized filenames.

        Args:
            output_path: Path for output archive file
            graph_name: Name to use for files inside archive
            format: Export format for the data files
            compress: If True, create tar.gz; if False, create tar
        """
        import tarfile
        import tempfile

        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Generate standardized filenames
            nodes_filename, edges_filename = _generate_archive_filenames(graph_name, format)
            nodes_temp_file = temp_path / nodes_filename
            edges_temp_file = temp_path / edges_filename

            # Export database tables to temporary files
            self.export_to_format("nodes", nodes_temp_file, format)
            self.export_to_format("edges", edges_temp_file, format)

            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create archive
            mode = "w:gz" if compress else "w"
            with tarfile.open(output_path, mode) as tar:
                tar.add(nodes_temp_file, arcname=nodes_filename)
                tar.add(edges_temp_file, arcname=edges_filename)

            logger.info(f"Exported database to {'compressed ' if compress else ''}archive {output_path}")

    def export_to_loose_files(self, output_directory: Path, graph_name: str, format: KGXFormat) -> tuple[Path, Path]:
        """
        Export database tables to individual files with standardized filenames.

        Args:
            output_directory: Directory for output files
            graph_name: Name to use for files
            format: Export format for the data files

        Returns:
            Tuple of (nodes_file_path, edges_file_path)
        """
        # Generate standardized filenames
        nodes_filename, edges_filename = _generate_archive_filenames(graph_name, format)
        nodes_file = output_directory / nodes_filename
        edges_file = output_directory / edges_filename

        # Create output directory if needed
        output_directory.mkdir(parents=True, exist_ok=True)

        # Export database tables
        self.export_to_format("nodes", nodes_file, format)
        self.export_to_format("edges", edges_file, format)

        logger.info(f"Exported database to loose files in {output_directory}")

        return nodes_file, edges_file

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _get_file_extension(format: KGXFormat) -> str:
    """Get file extension for the given format."""
    extension_map = {KGXFormat.TSV: ".tsv", KGXFormat.JSONL: ".jsonl", KGXFormat.PARQUET: ".parquet"}
    return extension_map[format]


def _generate_archive_filenames(graph_name: str, format: KGXFormat) -> tuple[str, str]:
    """
    Generate standardized filenames for archive export.

    Args:
        graph_name: Base name for the graph
        format: Export format

    Returns:
        Tuple of (nodes_filename, edges_filename)
    """
    ext = _get_file_extension(format)
    nodes_filename = f"{graph_name}_nodes{ext}"
    edges_filename = f"{graph_name}_edges{ext}"
    return nodes_filename, edges_filename


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def print_operation_summary(summary: OperationSummary):
    """Print formatted operation summary to console."""
    if summary.success:
        print(f"✓ {summary.operation} completed successfully")
    else:
        print(f"✗ {summary.operation} failed")

    print(f"  {summary.message}")

    if summary.stats:
        print(f"  📊 Final stats:")
        print(f"    - Nodes: {summary.stats.nodes:,}")
        print(f"    - Edges: {summary.stats.edges:,}")
        if summary.stats.dangling_edges > 0:
            print(f"    - Dangling edges: {summary.stats.dangling_edges:,}")
        if summary.stats.database_size_mb:
            print(f"    - Database size: {summary.stats.database_size_mb:.1f} MB")

    if summary.files_processed > 0:
        print(f"  📁 Files processed: {summary.files_processed}")

    print(f"  ⏱️  Total time: {summary.total_time_seconds:.2f}s")

    if summary.warnings:
        print(f"  ⚠️  Warnings:")
        for warning in summary.warnings:
            print(f"    - {warning}")

    if summary.errors:
        print(f"  ❌ Errors:")
        for error in summary.errors:
            print(f"    - {error}")
